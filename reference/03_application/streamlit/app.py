"""
app.py — ログシス社内チャットアプリ
起動: streamlit run app.py
"""

import re
import json
from datetime import datetime, timedelta, timezone
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from anthropic import Anthropic

st.set_page_config(
    page_title="ログシス データ問い合わせ",
    page_icon="📊",
    layout="wide",
)

def check_password() -> bool:
    if st.session_state.get("authenticated"):
        return True
    st.title("📊 ログシス データ問い合わせ")
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("### ログイン")
        password = st.text_input("パスワード", type="password", key="pw_input")
        if st.button("ログイン", use_container_width=True):
            if password == st.secrets["APP_PASSWORD"]:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("パスワードが違います")
    return False


@st.cache_resource
def get_engine():
    return create_engine(st.secrets["SUPABASE_DB_URL"], pool_pre_ping=True)


@st.cache_data(ttl=300)
def get_schema_info() -> str:
    engine = get_engine()
    with engine.connect() as conn:
        schema_df = pd.read_sql(text("SELECT * FROM _schema_info"), conn)
        col_info = pd.read_sql(text("""
            SELECT table_name, column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'public'
            ORDER BY table_name, ordinal_position
        """), conn)
    lines = ["=== ログシス データベース スキーマ ===\n"]
    for _, row in schema_df.iterrows():
        lines.append(f"【{row['table_name']}】{row['table_label']}: {row['description']}")
        cols = col_info[col_info["table_name"] == row["table_name"]]
        col_list = ", ".join(f"{r['column_name']}({r['data_type'][:10]})" for _, r in cols.iterrows())
        lines.append(f"  カラム: {col_list}\n")
    return "\n".join(lines)


def run_sql(sql: str) -> pd.DataFrame:
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn)


def save_question_log(question: str, query_type: str, generated_sql: str | None,
                      row_count: int | None, answer: str) -> int | None:
    """質問ログをDBに保存してIDを返す"""
    try:
        engine = get_engine()
        with engine.begin() as conn:
            result = conn.execute(text("""
                INSERT INTO questions_log
                    (question, query_type, generated_sql, row_count, answer)
                VALUES
                    (:question, :query_type, :generated_sql, :row_count, :answer)
                RETURNING id
            """), {
                "question": question,
                "query_type": query_type,
                "generated_sql": generated_sql,
                "row_count": row_count,
                "answer": answer,
            })
            return int(result.fetchone()[0])
    except Exception:
        return None


def save_feedback(log_id: int, feedback: int, note: str = ""):
    """フィードバック（👍/👎）をDBに保存。成功時True、失敗時エラー文字列を返す"""
    try:
        from urllib.parse import urlparse
        import psycopg2
        url = st.secrets["SUPABASE_DB_URL"]
        parsed = urlparse(url)
        conn = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            dbname=parsed.path.lstrip("/"),
            user=parsed.username,
            password=parsed.password,
            options="-c statement_timeout=0",
            connect_timeout=10,
        )
        cur = conn.cursor()
        # 型を明示的にPython intに変換（numpy.int64対策）
        cur.execute(
            "UPDATE questions_log SET feedback = %s, feedback_note = %s WHERE id = %s",
            (int(feedback), str(note), int(log_id))
        )
        affected = cur.rowcount
        conn.commit()
        cur.close()
        conn.close()
        if affected == 0:
            return f"UPDATE成功だが対象行なし (id={log_id}, type={type(log_id).__name__})"
        return True
    except Exception as e:
        return str(e)


def extract_sql(text_content: str) -> str | None:
    match = re.search(r"```sql\s*(.*?)\s*```", text_content, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    match = re.search(r"(SELECT\s.+?)(?:;|$)", text_content, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None



TRANSPORT_LABELS = {
    1: "OCEAN_CY",
    2: "OCEAN_CFS",
    3: "SKI EXPRESS",
    4: "FERRY_CFS",
    5: "FERRY_CY",
    6: "AIR",
    7: "DHL",
    8: "FEDEX",
    9: "Score Japan",
    10: "S.F.EXPRESS",
    11: "LOCAL DELIVERY",
    12: "その他",
    13: "OCS",
}

# NEWHATTANブランドの仕入先キーワード（デフォルト除外）
NEWHATTAN_KEYWORDS = ["NEWHATTAN", "NEW HATTAN"]

def run_import_cost_estimate(question: str, schema: str, override_params: dict = None) -> dict:
    """
    輸入経費推定：輸送方法別比較表を返す。
    - デフォルトでNEWHATTAN系仕入先を除外
    - 質問に「NEWHATTAN」が含まれる場合のみ含める
    """
    import json
    import pandas as pd
    from anthropic import Anthropic

    client = Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])

    # ── ① パラメータ抽出 ──────────────────────────────
    CAT_NAMES = {
        1: "帽子", 2: "バッグ", 3: "財布/小物", 4: "サングラス/メガネ",
        5: "巻物", 6: "アパレル", 7: "ベルト", 8: "履物", 9: "アクセサリー",
    }

    # override_paramsがある場合（確認返答後の再実行）はスキップ
    if override_params:
        qty      = override_params["qty"]
        unit_usd = override_params["unit_usd"]
        cat_code = override_params["cat_code"]
        cat_name = override_params["cat_name"]
        cat_name_extracted = override_params.get("cat_name_extracted", cat_name)
        params   = override_params
    else:
        system_extract = """ユーザーの質問から輸入経費推定に必要なパラメータを抽出してください。
以下のJSONのみ返してください（他のテキスト不要）:
{
  "数量": 数値 or null,
  "単価_USD": 数値 or null,
  "商品分類コード": 数値 or null,
  "商品分類名_抽出": "質問に含まれる商品の呼び方をそのまま記載",
  "confidence": "high" or "low"
}

商品分類コードの対応:
1=帽子(キャップ/ハット/ベレー/ニット帽/バケットハット等含む)
2=バッグ(トートバッグ/リュック/ショルダーバッグ/サコッシュ/ポーチ以外のバッグ類)
3=財布/小物(財布/ポーチ/カードケース/キーケース/コインケース等)
4=サングラス/メガネ
5=巻物(マフラー/スカーフ/ストール/バンダナ等)
6=アパレル(Tシャツ/ジャケット/パンツ/ワンピース等の衣類)
7=ベルト
8=履物(靴/スニーカー/ブーツ/サンダル/ソックス等)
9=アクセサリー(ネックレス/ブレスレット/リング/ピアス等)

confidenceの判定基準:
- high: 商品が明確にいずれかの分類に対応する
- low: 商品名が曖昧、複数の分類に当てはまる可能性がある、または商品が不明

数量・単価・商品分類のいずれかが不明な場合はnullを返してください。"""

        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=200,
            system=system_extract,
            messages=[{"role": "user", "content": question}],
        )
        try:
            raw = resp.content[0].text.strip()
            if raw.startswith("```"):
                raw = re.sub(r"```json?\s*|\s*```", "", raw).strip()
            params = json.loads(raw)
        except Exception:
            return {
                "type": "no_sql",
                "answer": "質問の解析に失敗しました。「帽子100個、5ドルの場合の輸入経費は？」のように数量・単価・商品を含めて質問してください。",
            }

        # 必須パラメータのいずれかがnullなら補完待ちとして保存
        qty      = params.get("数量")
        unit_usd = params.get("単価_USD")
        cat_code = params.get("商品分類コード")
        cat_name_extracted = params.get("商品分類名_抽出", "")
        confidence = params.get("confidence", "high")

        if cat_code is None:
            st.session_state["pending_estimate_params"] = {
                "qty": qty, "unit_usd": unit_usd,
                "cat_code": None, "cat_name": None,
                "cat_name_extracted": cat_name_extracted,
                "waiting_for": "cat_code",
            }
            return {
                "type": "no_sql",
                "answer": f"「{cat_name_extracted}」がどの商品分類に該当するか判断できませんでした。\n\n以下のいずれかで指定してください：\n帽子 / バッグ / 財布・小物 / サングラス / 巻物 / アパレル / ベルト / 履物 / アクセサリー",
            }

        cat_name = CAT_NAMES.get(cat_code, "不明")

        if qty is None or unit_usd is None:
            missing = []
            if qty is None: missing.append("数量（個数）")
            if unit_usd is None: missing.append("単価（USD）")
            waiting_for = "qty" if qty is None else "unit_usd"
            # 判明している情報をsession_stateに保存
            st.session_state["pending_estimate_params"] = {
                "qty": qty, "unit_usd": unit_usd,
                "cat_code": cat_code, "cat_name": cat_name,
                "cat_name_extracted": cat_name_extracted,
                "waiting_for": waiting_for,
            }
            missing_str = "・".join(missing)
            return {
                "type": "no_sql",
                "answer": f"**{cat_name}**の経費推定に、以下の情報が不足しています：**{missing_str}**\n\n{'数量を教えてください。（例：200個）' if qty is None else '単価（USD）を教えてください。（例：8ドル）'}",
            }

        if confidence == "low":
            # session_stateに保存して確認を求める
            st.session_state["pending_estimate_params"] = {
                "qty": qty, "unit_usd": unit_usd,
                "cat_code": cat_code, "cat_name": cat_name,
                "cat_name_extracted": cat_name_extracted,
                "waiting_for": "confirm",
            }
            return {
                "type": "no_sql",
                "answer": f"「{cat_name_extracted}」は **{cat_name}（コード{cat_code}）** として計算しようとしていますが、合っていますか？\n\n合っていれば「あってます」と送ってください。\n違う場合は正しい商品分類を指定してください。",
            }

    # ── 共通処理 ──────────────────────────────────────
    qty_min  = qty * 0.5
    qty_max  = qty * 1.5

    # NEWHATTANを含めるか（質問に明示された場合のみ）
    include_newhattan = any(kw.upper() in question.upper() for kw in NEWHATTAN_KEYWORDS)

    # ── ② 最新為替レートを取得 ────────────────────────
    fx_sql = """
        SELECT "為替" FROM purchases
        WHERE "為替" > 1
        ORDER BY "ID" DESC LIMIT 1
    """
    try:
        df_fx = run_sql(fx_sql)
        latest_fx = float(df_fx.iloc[0]["為替"]) if not df_fx.empty else 150.0
    except Exception:
        latest_fx = 150.0

    # ── ③ 全データを1回取得 ───────────────────────────
    base_sql = f"""
        SELECT
            p."伝票番号",
            p."伝票日",
            p."輸送方法",
            p."仕入先名",
            p."仕入数量pcs",
            p."仕入金額円",
            p."諸掛込金額円",
            inv_total."伝票合計数量pcs"
        FROM purchases p
        JOIN (
            SELECT "伝票番号", SUM("仕入数量pcs") AS "伝票合計数量pcs"
            FROM purchases
            WHERE "ステータス" IN (2, 3)
            GROUP BY "伝票番号"
        ) inv_total ON inv_total."伝票番号" = p."伝票番号"
        WHERE p."ステータス" IN (2, 3)
          AND p."商品分類" = {cat_code}
          AND p."仕入金額円" > 0
          AND p."諸掛込金額円" > p."仕入金額円"
          AND p."伝票日" >= CURRENT_DATE - INTERVAL '1 year'
          AND EXISTS (
            SELECT 1 FROM purchase_surcharges ps
            WHERE ps."仕入ID" = p."ID"
              AND ps."諸掛区分ID" IN (1, 3)
              AND ps."金額円" > 0
          )
    """

    try:
        df_raw = run_sql(base_sql)
    except Exception as e:
        return {"type": "sql_error", "sql": base_sql,
                "answer": f"データ取得中にエラーが発生しました: {str(e)}"}

    if df_raw.empty:
        return {"type": "empty", "sql": base_sql,
                "answer": "条件に一致するデータが見つかりませんでした。"}

    # ── ④ NEWHATTANフィルタ ───────────────────────────
    if not include_newhattan:
        mask_newhattan = df_raw["仕入先名"].str.upper().apply(
            lambda x: any(kw.upper() in str(x) for kw in NEWHATTAN_KEYWORDS)
        )
        df_raw = df_raw[~mask_newhattan]

    # ── ⑤ 伝票単位に集計 ─────────────────────────────
    df_inv = (
        df_raw.groupby("伝票番号")
        .agg(
            輸送方法=("輸送方法", "first"),
            仕入先名=("仕入先名", "first"),
            合計数量pcs=("仕入数量pcs", "sum"),
            伝票合計数量pcs=("伝票合計数量pcs", "first"),
            合計仕入金額円=("仕入金額円", "sum"),
            合計諸掛込金額円=("諸掛込金額円", "sum"),
        )
        .reset_index()
    )
    df_inv["経費率"] = (
        df_inv["合計諸掛込金額円"] / df_inv["合計仕入金額円"].replace(0, float("nan"))
    )

    # ── ⑥ 数量範囲でフィルタ ──────────────────────────
    df_filtered = df_inv[
        (df_inv["合計数量pcs"] >= qty_min) &
        (df_inv["合計数量pcs"] <= qty_max)
    ].copy()

    # ── ⑦ 輸送方法別に集計 ───────────────────────────
    buy_jpy = qty * unit_usd * latest_fx

    results = []
    for transport_code, label in TRANSPORT_LABELS.items():
        df_t = df_filtered[df_filtered["輸送方法"] == transport_code]
        if len(df_t) == 0:
            results.append({
                "輸送方法": label,
                "伝票数": 0,
                "対象数量": "-",
                "伝票合計数量": "-",
                "推奨経費率": "-",
                "経費率(範囲)": "-",
                "推定仕入金額": "-",
                "推定輸入経費": "-",
                "推定諸掛込原価": "-",
                "原価幅": "-",
                "1個原価": "-",
                "主な仕入先": "-",
            })
            continue

        rate_med = df_t["経費率"].median()
        rate_min = df_t["経費率"].min()
        rate_max = df_t["経費率"].max()
        landed   = buy_jpy * rate_med
        cost     = landed - buy_jpy

        suppliers = df_t["仕入先名"].value_counts().head(3).index.tolist()
        sup_str   = "、".join(suppliers)
        low_data  = "⚠️" if len(df_t) < 3 else ""

        qty_avg = int(df_t["合計数量pcs"].mean())
        qty_min_val = int(df_t["合計数量pcs"].min())
        qty_max_val = int(df_t["合計数量pcs"].max())
        inv_qty_avg = int(df_t["伝票合計数量pcs"].mean())
        inv_qty_min_val = int(df_t["伝票合計数量pcs"].min())
        inv_qty_max_val = int(df_t["伝票合計数量pcs"].max())

        # 質問条件（数量・単価・為替）で推定金額を計算
        est_buy     = qty * unit_usd * latest_fx          # 仕入金額
        est_landed  = est_buy * rate_med                   # 諸掛込原価（中央値）
        est_cost    = est_landed - est_buy                 # 輸入経費
        est_per_pcs = est_landed / qty                     # 1個あたり原価
        # 幅（最小〜最大経費率）
        est_landed_min = est_buy * rate_min
        est_landed_max = est_buy * rate_max

        # 見積もりツール用推奨経費率（中央値を推奨値として使用）
        est_rate_low  = round(rate_min + (rate_med - rate_min) * 0.25, 3)  # 25パーセンタイル相当
        est_rate_high = round(rate_med + (rate_max - rate_med) * 0.75, 3)  # 75パーセンタイル相当

        results.append({
            "輸送方法": label,
            "伝票数": f"{len(df_t)}{low_data}",
            "対象数量": f"{qty_avg}個({qty_min_val}〜{qty_max_val})",
            "伝票合計数量": f"{inv_qty_avg}個({inv_qty_min_val}〜{inv_qty_max_val})",
            "推奨経費率": f"{rate_med:.3f}",
            "経費率(範囲)": f"{round(rate_min,3)}〜{round(rate_max,3)}",
            "推定仕入金額": f"{int(est_buy):,}円",
            "推定輸入経費": f"{int(est_cost):,}円",
            "推定諸掛込原価": f"{int(est_landed):,}円",
            "原価幅": f"{int(est_landed_min):,}〜{int(est_landed_max):,}円",
            "1個原価": f"{round(est_per_pcs,0):.0f}円",
            "主な仕入先": sup_str,
        })

    df_result = pd.DataFrame(results)
    # 件数0の輸送方法を除外
    df_result = df_result[df_result["伝票数"] != 0].copy()
    # 件数降順ソート（伝票数から数値部分を抽出して比較）
    df_result["_sort_key"] = df_result["伝票数"].apply(
        lambda x: int(str(x).replace("⚠️", "").strip()) if str(x).replace("⚠️", "").strip().isdigit() else 0
    )
    df_result = df_result.sort_values("_sort_key", ascending=False).drop(columns=["_sort_key"]).reset_index(drop=True)

    # ── ⑧ 回答文生成 ─────────────────────────────────
    newhattan_note = "NEWHATTAN除外" if not include_newhattan else "NEWHATTAN含む"
    buy_jpy_fmt = f"{int(buy_jpy):,}"

    system_answer = """あなたはログズ株式会社の社内データアナリストです。
以下のフォーマットで1行だけ出力してください。それ以外は一切出力しないこと。
フォーマット: 「参照条件: 商品=XXX・数量XXX〜XXX個・為替XXX円・直近1年・NEWHATTAN除外/含む」"""

    resp_answer = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=100,
        system=system_answer,
        messages=[{"role": "user", "content": f"""
商品: {cat_name}（{cat_name_extracted}）
数量: {qty}個（参照範囲: {int(qty_min)}〜{int(qty_max)}個）
為替: {latest_fx}円/USD
{newhattan_note}
"""}],
    )

    answer_text = resp_answer.content[0].text
    log_id = save_question_log(question, "estimate", base_sql, len(df_result), answer_text)
    return {
        "type": "success",
        "sql": base_sql,
        "df": df_result,
        "answer": answer_text,
        "row_count": len(df_result),
        "params": params,
        "is_estimate": True,
        "log_id": log_id,
    }


def ask_claude(question: str, schema: str, history: list) -> dict:
    client = Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])

    pending = st.session_state.get("pending_estimate_params")

    # ── 補完返答の処理 ────────────────────────────────
    if pending:
        waiting_for = pending.get("waiting_for", "confirm")

        if waiting_for in ("unit_usd", "qty"):
            # Claude APIで数値を抽出
            resp_num = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=50,
                system="ユーザーの返答から数値を1つだけ抽出してください。数値のみ返してください（単位・説明不要）。数値がない場合は'null'を返してください。",
                messages=[{"role": "user", "content": question}],
            )
            extracted = resp_num.content[0].text.strip()
            try:
                value = float(extracted)
            except Exception:
                value = None

            if value is None:
                return {
                    "type": "no_sql",
                    "answer": f"数値が読み取れませんでした。{'数量' if waiting_for == 'qty' else '単価（USD）'}を数字で教えてください。（例：{'200' if waiting_for == 'qty' else '8'}）",
                }

            # 補完してパラメータを完成させる
            if waiting_for == "unit_usd":
                pending["unit_usd"] = value
            else:
                pending["qty"] = int(value)

            # まだ不足がある場合は次の補完待ちへ
            if pending["unit_usd"] is None:
                pending["waiting_for"] = "unit_usd"
                st.session_state["pending_estimate_params"] = pending
                return {
                    "type": "no_sql",
                    "answer": f"次に単価（USD）を教えてください。（例：8ドル）",
                }
            if pending["qty"] is None:
                pending["waiting_for"] = "qty"
                st.session_state["pending_estimate_params"] = pending
                return {
                    "type": "no_sql",
                    "answer": f"次に数量（個数）を教えてください。（例：200個）",
                }

            # 全部揃ったので計算実行
            st.session_state.pop("pending_estimate_params", None)
            return run_import_cost_estimate(question, schema, override_params=pending)

        elif waiting_for == "cat_code":
            # 商品分類の補完: ClaudeAPIで分類コードを抽出
            CAT_NAMES_INV = {
                "帽子": 1, "バッグ": 2, "財布": 3, "小物": 3, "財布・小物": 3, "財布/小物": 3,
                "サングラス": 4, "メガネ": 4, "巻物": 5, "マフラー": 5, "スカーフ": 5,
                "アパレル": 6, "服": 6, "衣類": 6, "ベルト": 7, "履物": 8, "靴": 8, "アクセサリー": 9,
            }
            cat_code = next((v for k, v in CAT_NAMES_INV.items() if k in question), None)

            if cat_code is None:
                # ClaudeAPIで抽出
                resp_cat = client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=10,
                    system="以下の商品分類コードのみ返してください（数字1文字）。該当なしは'null'。\n1=帽子 2=バッグ 3=財布/小物 4=サングラス 5=巻物 6=アパレル 7=ベルト 8=履物 9=アクセサリー",
                    messages=[{"role": "user", "content": question}],
                )
                try:
                    cat_code = int(resp_cat.content[0].text.strip())
                except Exception:
                    cat_code = None

            if cat_code is None:
                return {
                    "type": "no_sql",
                    "answer": f"商品分類が判断できませんでした。以下のいずれかで指定してください：\n帽子 / バッグ / 財布・小物 / サングラス / 巻物 / アパレル / ベルト / 履物 / アクセサリー",
                }

            CAT_NAMES = {1:"帽子", 2:"バッグ", 3:"財布/小物", 4:"サングラス/メガネ",
                         5:"巻物", 6:"アパレル", 7:"ベルト", 8:"履物", 9:"アクセサリー"}
            pending["cat_code"] = cat_code
            pending["cat_name"] = CAT_NAMES.get(cat_code, "不明")

            # 数量・単価が揃っていれば計算実行
            if pending.get("qty") and pending.get("unit_usd"):
                st.session_state.pop("pending_estimate_params", None)
                return run_import_cost_estimate(question, schema, override_params=pending)
            elif pending.get("unit_usd") is None:
                pending["waiting_for"] = "unit_usd"
                st.session_state["pending_estimate_params"] = pending
                return {"type": "no_sql", "answer": f"単価（USD）を教えてください。（例：8ドル）"}
            else:
                pending["waiting_for"] = "qty"
                st.session_state["pending_estimate_params"] = pending
                return {"type": "no_sql", "answer": f"数量（個数）を教えてください。（例：200個）"}

        elif waiting_for == "confirm":
            confirm_keywords = ["あってます", "あってる", "はい", "yes", "ok", "OK", "そうです", "正しい",
                                "合ってます", "合ってる", "合っています", "で計算して", "で頼む",
                                "それで", "それでいい", "それでお願い", "問題ない", "大丈夫"]
            # 「ありがとう」系は誤検知しないよう除外
            false_positives = ["ありがとう", "ありがと", "thank"]
            is_false = any(k in question for k in false_positives)
            if not is_false and any(k in question for k in confirm_keywords):
                st.session_state.pop("pending_estimate_params", None)
                return run_import_cost_estimate(question, schema, override_params=pending)
            elif is_false:
                # 「ありがとう」はpendingをそのまま維持して通常返答
                return {"type": "no_sql", "answer": "どういたしまして！他に確認したいことがあればお気軽にどうぞ。"}
            else:
                # 否定された場合はキャンセル
                st.session_state.pop("pending_estimate_params", None)

    # 輸入経費推定の質問かどうか判定
    estimate_keywords = ["経費", "輸入", "いくら", "推定", "ドル", "USD", "CFS", "CY", "AIR", "DHL", "FEDEX"]
    is_estimate = any(k in question for k in estimate_keywords) and ("個" in question or "pcs" in question.lower() or "円" in question)

    if is_estimate:
        return run_import_cost_estimate(question, schema)

    system_sql = f"""あなたはPostgreSQLの専門家です。
ユーザーの日本語の質問を受け取り、以下のスキーマに基づいてSQLクエリを生成してください。

{schema}

ルール:
- 必ずSELECT文のみ生成（INSERT/UPDATE/DELETE/DROPは絶対禁止）
- SQLは ```sql ``` で囲む
- 金額は日本円（円）
- 日付フィルタは納品伝票日や作成日時を使う
- 結果は最大500行に制限（LIMIT 500）
- カラム名はわかりやすいASエイリアスをつける
- 「期」の形式はテーブルによって異なる:
  - salesテーブル: 'LOGS10期' 形式（LOGSを使用）
  - budget_forecastテーブル: 'LGS 10期' 形式（LGS + スペース + 数字 + 期）
  - 現在の最新期はLOGS10期 / LGS 10期（2025年8月〜2026年7月）

【最重要】salesテーブルの正しい集計ルール:
salesテーブルは「1伝票 = 複数明細行」の構造で、伝票ヘッダー情報が全明細行に繰り返し格納されている。
以下のカラムは伝票単位の値が明細行数分だけ重複するため絶対に使用禁止:
  禁止カラム: "売上合計金額", "粗利", "粗利率", "請求合計金額", "請求合計金額(税込)"

正しい明細レベルのカラムを必ず使うこと:
  売上金額の集計 → SUM("売上金額")
  粗利の集計   → SUM("明細粗利")
  粗利率の計算  → SUM("明細粗利") / NULLIF(SUM("売上金額"), 0)
  数量の集計   → SUM("数量(pcs)")
  顧客別・期別集計 → "得意先名"や"期"でGROUP BYし上記カラムをSUM

【売上集計時の必須フィルタ条件】
売上金額・粗利を集計する際は必ず以下の2条件をWHERE句に含めること:
  条件1: "ステータス" IN (2, 3, 4, 5)
  条件2: "決済方法" != '4'
  まとめると: WHERE "ステータス" IN (2, 3, 4, 5) AND "決済方法" != '4'

【仕入集計時の必須フィルタ条件】
  "ステータス" IN (2, 3)

【発注依頼集計時の必須フィルタ条件】
  "ステータス" = 4

【輸入経費率の定義】
ログズの輸入経費率は 1.xx 形式（倍率）。表示は小数点2桁。
予定経費率（発注依頼）: ROUND(CAST((SUM("発注金額") + SUM("発注金額" * ("輸入経費率" - 1))) / NULLIF(SUM("発注金額"), 0) AS numeric), 2)
実績経費率（仕入）: ROUND(CAST(SUM("諸掛込金額円") / NULLIF(SUM("仕入金額円"), 0) AS numeric), 2)
※輸入経費ありのみ: "諸掛込金額円" > "仕入金額円"

【ログズ社ドメイン知識】

■ 数量帯（「数量ごと」「ロット別」「数量帯」という表現はこの区切りでGROUP BY）
  99以下 / 100〜299 / 300〜499 / 500〜999 / 1000以上
  例: CASE WHEN 数量 < 100 THEN '99以下' WHEN 数量 < 300 THEN '100〜299' WHEN 数量 < 500 THEN '300〜499' WHEN 数量 < 1000 THEN '500〜999' ELSE '1000以上' END

■ 期間の解釈
  - 「期」は8/1始まり7/31終わり（例: LOGS10期 = 2025/8/1〜2026/7/31）
  - 「最近」「直近」= 直近3ヶ月
  - 「前期比」= 当期値 / 前期値（前年同期比は使わない）
  - 上半期・Q1等の表現は使わない

■ 金額・原価の解釈
  - 「原価」= 諸掛込金額（輸入経費込みコスト）
  - 「商品原価」「発注単価」= productsテーブルの発注単価
  - 経費率は1.xx形式の倍率で表示する

■ 顧客の検索
  - 「顧客」「得意先」「取引先」はすべて同義（salesの得意先名、customersの顧客名称）
  - 担当者は名字のみで検索（例: LIKE '%石川%'）
  - 顧客は略称で質問されることがある → 部分一致（LIKE）で対応
  - 「請求先でまとめて」と明示された場合のみ customersの請求先ID・請求先名でGROUP BY

■ 商品の検索優先順位
  1. LOGS_CODE（productsテーブル）
  2. Sample_CODE（SLG-XXXXXのような形式）
  3. 商品名の部分一致（LIKE）

■ 集計の粒度
  - 時間粒度は月次まで（日次・週次は不要）
  - 典型的なドリルダウン順: 全体 → カテゴリ別 → 営業担当者別 → ブランド（得意先）別
  - 担当者の部署・種別での集計はstaffテーブルの所属部署名・権限IDを使う
  - 担当者検索はstaffテーブルとLIKEで突合してもよい

■ チームの定義
  staffテーブルの「チーム」カラムで定義: メンズ / レディース / 問屋 / 管理 / 経理 など
  salesとstaffのJOIN: LEFT JOIN staff st ON s."営業担当者名" LIKE '%' || split_part(st."社員氏名", ' ', 1) || '%'
  チーム別集計時はst."チーム"でGROUP BY

■ ETD・納品日の扱い
  purchase_ordersの"ETD"カラム = 輸出地出港予定日（船積み日）であり納品予定日ではない
  「納品予定日」「納品日」= purchase_ordersの"顧客納品日"カラムを使うこと
  「ETD以降」「船積み済み」の文脈では"ETD"を使用
  「納品予定」「納品スケジュール」の文脈では"顧客納品日"を使用

■ 輸送方法コード（purchasesテーブルの"輸送方法"カラム）
  1=OCEAN(CY), 2=OCEAN(CFS), 3=SKI EXPRESS, 4=FERRY(CFS), 5=FERRY(CY),
  6=AIR, 7=DHL, 8=FEDEX, 9=Score Japan, 10=S.F.EXPRESS,
  11=LOCAL DELIVERY, 12=その他, 13=OCS

■ 予算・予定データ（budget_forecastテーブル）
  1行 = 1案件（顧客×担当者×期×月×分類）の伝票単位
  分類の値: 01_予算 / 02_予定 / 05_費用 のみ（03_発注・04_実績は存在しない）
  主要カラム: 分類・顧客名・社員名・案件売上・案件粗利・案件粗利率・チーム・商品分類・顧客詳細分類・期・年・月
  費用カラム: ①二次加工費（副資材単価、資材等運送含む）・②検品（検針、検査含む）・③サンプル費用・④その他販売経費

  【重要】発注・実績データの取得先
  - 03_発注・04_実績はbudget_forecastに存在しない
  - 発注実績 → purchase_ordersテーブル（明細単位・logsys連携）
  - 売上実績 → salesテーブル（明細単位・logsys連携）
  - 「予算・予定・発注・実績を横並びで見たい」場合は以下のようにサブクエリで結合すること:

  SELECT
    bf.社員名,
    SUM(CASE WHEN bf.分類 = '01_予算' THEN bf.案件売上 ELSE 0 END) AS 予算売上,
    SUM(CASE WHEN bf.分類 = '02_予定' THEN bf.案件売上 ELSE 0 END) AS 予定売上,
    COALESCE(po.発注売上, 0) AS 発注売上,
    COALESCE(s.実績売上, 0) AS 実績売上
  FROM budget_forecast bf
  LEFT JOIN (
    SELECT "営業担当者名" AS 社員名, SUM("売上金額") AS 発注売上
    FROM purchase_orders
    WHERE "ステータス" = 4
      AND "顧客納品日" >= '2026-06-01' AND "顧客納品日" < '2026-07-01'
    GROUP BY "営業担当者名"
  ) po ON bf.社員名 LIKE '%' || split_part(po.社員名, ' ', 1) || '%'
  LEFT JOIN (
    SELECT "営業担当者名" AS 社員名, SUM("売上金額") AS 実績売上
    FROM sales
    WHERE "ステータス" IN (2,3,4,5) AND "決済方法" != '4'
      AND "納品伝票日" >= '2026-06-01' AND "納品伝票日" < '2026-07-01'
    GROUP BY "営業担当者名"
  ) s ON bf.社員名 LIKE '%' || split_part(s.社員名, ' ', 1) || '%'
  WHERE bf."年" = '2026' AND bf."月" = '06月'
  GROUP BY bf.社員名, po.発注売上, s.実績売上

  【予算達成率の計算例】（実績はsalesテーブルから取得）:
  SELECT
    bf.社員名,
    SUM(CASE WHEN bf.分類 = '01_予算' THEN bf.案件売上 ELSE 0 END) AS 予算売上,
    COALESCE(s.実績売上, 0) AS 実績売上,
    ROUND(CAST(
      COALESCE(s.実績売上, 0) /
      NULLIF(SUM(CASE WHEN bf.分類 = '01_予算' THEN bf.案件売上 ELSE 0 END), 0) * 100
    AS numeric), 1) AS 予算達成率
  FROM budget_forecast bf
  LEFT JOIN (
    SELECT "営業担当者名" AS 社員名, SUM("売上金額") AS 実績売上
    FROM sales
    WHERE "ステータス" IN (2,3,4,5) AND "決済方法" != '4'
      AND 期 = 'LOGS10期'
    GROUP BY "営業担当者名"
  ) s ON bf.社員名 LIKE '%' || split_part(s.社員名, ' ', 1) || '%'
  WHERE bf.期 = 'LGS 10期'
  GROUP BY bf.社員名, s.実績売上

  【05_費用の注意事項】
  - 費用の値はマイナスで入力されている（仕様）→ 集計時はABS()で絶対値に変換して表示すること
  - 費用行の案件売上・案件粗利はNULL（費用データに売上情報はない）
  - 費用は全て「①二次加工費（副資材単価、資材等運送含む）」カラムに集約されている（②③④はNULL）
  - 期フィルタを必ず指定すること（指定しないと複数期が合算されて数値が大きくなる）
  - 月別表示は期の開始月（08月）から翌年7月の順に並べること:
    ORDER BY "年" ASC, "月" ASC が正しい（文字列ソートで08月→09月→...→12月→01月→...→07月の順になる）
  - 今期（LGS 10期）の費用を集計する例:
    SELECT 年, 月, 社員名, ABS(SUM("①二次加工費（副資材単価、資材等運送含む）")) AS 費用合計
    FROM budget_forecast
    WHERE 分類 = '05_費用' AND 期 = 'LGS 10期'
    GROUP BY 年, 月, 社員名
    ORDER BY 年 ASC, 月 ASC

  【重要】budget_forecastの期カラム形式:
  - 'LGS 10期' 形式（LGS + スペース + 数字 + 期）※salesの'LOGS10期'とは異なる
  - 現在の最新期: 'LGS 10期'（2025年8月〜2026年7月）
  - 例: LGS 06期 / LGS 07期 / LGS 08期 / LGS 09期 / LGS 10期 / LGS 11期

  【重要】年・月カラムの形式:
  - 年: text型（例: '2026'）→ "年" = '2026'
  - 月: text型で「XX月」形式（例: '06月'）→ "月" = '06月'
  - 「今月」= 現在の年月に合わせて変換すること
    例: 今月が2026年6月なら → "年" = '2026' AND "月" = '06月'
  - 月は必ず2桁ゼロ埋め+'月'（'01月'〜'12月'）

  注意: logsys実績（salesテーブル）とbudget_forecastの実績は別データ。
  「予算vs実績」の質問はbudget_forecastテーブルのみで完結する。
  salesテーブルの実績と比較したい場合は明示的に両テーブルを使う。


各テーブルの商品分類コード: 1=帽子, 2=バッグ, 3=財布/小物, 4=サングラス/メガネ, 5=巻物, 6=アパレル, 7=ベルト, 8=履物, 9=アクセサリー, 10=その他

■ purchase_surcharges（仕入諸掛明細テーブル）
  仕入ID単位で輸入経費の内訳が格納されている。purchasesテーブルとJOINして使う。
  JOINキー: ps."仕入ID" = p."ID"  ※purchasesの主キー"ID"カラムと結合

  諸掛区分IDの実際の対応（コードマスタとは異なる。logsys画面の実データに基づく）:
    1=国内手数料（税抜）, 2=国内手数料消費税額（消費税）,
    3=運賃, 6=関税,
    7=輸入消費税（地方）（消費税）, 8=輸入消費税（内国）（消費税）

  消費税に該当する区分: 2, 7, 8
  輸入経費（消費税除く）= "諸掛区分ID" NOT IN (2, 7, 8)
  関税 = "諸掛区分ID" = 6
  集計カラム: "金額円"（円換算済み。元カラム名"金額(円)"がclean_column_nameで変換されたもの）

  【重要】purchase_surchargesとpurchasesのJOINに関する注意】
  purchase_surchargesは1つの仕入ID（purchases."ID"）に対して複数行存在する（諸掛区分IDごとに1行）。
  直接JOINすると purchases."仕入金額円" が行数分だけ重複加算されるため、
  purchases側は仕入IDで先に集計してからJOINすること。

  【検証済み】消費税除く諸掛合計（区分2・7・8を除く）は purchases の輸入経費合計と一致する。

  【関税率の計算例（商品分類別）】
  -- 分子: purchase_surchargesの関税額（区分ID=6）を仕入IDごとに集計
  -- 分母: purchasesの仕入金額円を仕入IDごとに集計
  -- 重複加算を防ぐため両者をサブクエリで先に集計してからJOIN
  SELECT
    p_agg."商品分類",
    SUM(p_agg."仕入金額合計") AS 仕入金額合計_円,
    SUM(ps_agg."関税額") AS 関税額合計_円,
    ROUND(CAST(SUM(ps_agg."関税額") / NULLIF(SUM(p_agg."仕入金額合計"), 0) * 100 AS numeric), 2) AS 関税率_pct
  FROM (
    SELECT "ID", "商品分類", SUM("仕入金額円") AS 仕入金額合計
    FROM purchases
    WHERE "ステータス" IN (2, 3)
    GROUP BY "ID", "商品分類"
  ) p_agg
  JOIN (
    SELECT "仕入ID", SUM(CASE WHEN "諸掛区分ID" = 6 THEN "金額円" ELSE 0 END) AS 関税額
    FROM purchase_surcharges
    GROUP BY "仕入ID"
  ) ps_agg ON ps_agg."仕入ID" = p_agg."ID"
  GROUP BY p_agg."商品分類"
  ORDER BY 関税率_pct DESC

  【関税率の計算例（輸送方法別など他の軸で集計する場合）】
  -- GROUP BYしたい軸（輸送方法・仕入先など）はp_aggのサブクエリに含めること
  SELECT
    p_agg."輸送方法",
    p_agg."商品分類",
    SUM(p_agg."仕入金額合計") AS 仕入金額合計_円,
    SUM(ps_agg."関税額") AS 関税額合計_円,
    ROUND(CAST(SUM(ps_agg."関税額") / NULLIF(SUM(p_agg."仕入金額合計"), 0) * 100 AS numeric), 2) AS 関税率_pct
  FROM (
    SELECT "ID", "輸送方法", "商品分類", SUM("仕入金額円") AS 仕入金額合計
    FROM purchases
    WHERE "ステータス" IN (2, 3)
    GROUP BY "ID", "輸送方法", "商品分類"
  ) p_agg
  JOIN (
    SELECT "仕入ID", SUM(CASE WHEN "諸掛区分ID" = 6 THEN "金額円" ELSE 0 END) AS 関税額
    FROM purchase_surcharges
    GROUP BY "仕入ID"
  ) ps_agg ON ps_agg."仕入ID" = p_agg."ID"
  GROUP BY p_agg."輸送方法", p_agg."商品分類"
  ORDER BY 関税率_pct DESC

  【輸入経費の費目別内訳（消費税除く）】
  SELECT
    CASE ps."諸掛区分ID"
      WHEN 1 THEN '国内手数料（税抜）' WHEN 3 THEN '運賃'
      WHEN 6 THEN '関税' ELSE 'その他'
    END AS 費目,
    SUM(ps."金額円") AS 金額合計_円
  FROM purchase_surcharges ps
  JOIN purchases p ON p."ID" = ps."仕入ID"
  WHERE p."ステータス" IN (2, 3)
    AND ps."諸掛区分ID" NOT IN (2, 7, 8)
  GROUP BY ps."諸掛区分ID"
  ORDER BY 金額合計_円 DESC

■ purchases → "商品分類"カラムが直接存在する（JOINは不要）

■ purchase_orders → "商品分類"カラムが直接存在する（JOINは不要）

■ sales → 商品分類カラムはなし。必ずproductsテーブルとJOINして取得すること:
  LEFT JOIN products p ON s."商品ID"::text = p."ID"::text
  商品分類: p."商品分類"
  商品名:   p."商品名"
  商品分類でGROUP BYする場合も p."商品分類" を使う。
  商品分類名に変換: CASE p."商品分類" WHEN 1 THEN '帽子' WHEN 2 THEN 'バッグ' WHEN 3 THEN '財布/小物' WHEN 4 THEN 'サングラス/メガネ' WHEN 5 THEN '巻物' WHEN 6 THEN 'アパレル' WHEN 7 THEN 'ベルト' WHEN 8 THEN '履物' WHEN 9 THEN 'アクセサリー' ELSE 'その他' END

【PostgreSQL固有の注意事項】
- ROUND()はdouble precision型に使えない。ROUND(CAST(... AS numeric), 2) とキャストすること
- 文字列の部分一致は LIKE '%石川%' とすること
- text型と数値の比較はシングルクォートで囲む（例: "決済方法" != '4'）
"""

    messages_for_sql = [{"role": "user", "content": question}]
    response_sql = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        system=system_sql,
        messages=messages_for_sql,
    )
    sql_text = response_sql.content[0].text
    sql = extract_sql(sql_text)

    if not sql:
        return {"type": "no_sql", "answer": "申し訳ありません、この質問からSQLを生成できませんでした。より具体的に質問してみてください。"}

    try:
        df = run_sql(sql)
    except Exception as e:
        return {"type": "sql_error", "sql": sql, "answer": f"データ取得中にエラーが発生しました: {str(e)}"}

    if df.empty:
        return {"type": "empty", "sql": sql, "answer": "条件に一致するデータが見つかりませんでした。"}

    result_preview = df.head(20).to_markdown(index=False)
    row_count = len(df)

    system_answer = """あなたはログズ株式会社の社内データアナリストです。
SQLの実行結果をもとに、ビジネス担当者向けにわかりやすく日本語で回答してください。
- 数字は読みやすくフォーマット（例: 1,234,567円）
- 重要な数字・順位・傾向を強調する
- データに基づいた簡潔なインサイトを1〜2文添える
- 「データ取得成功」などの技術的な言及は不要
"""

    messages_for_answer = history + [
        {"role": "user", "content": f"""質問: {question}
実行結果（{row_count}件）:
{result_preview}
{"（上位20件を表示）" if row_count > 20 else ""}
この結果をもとに回答してください。"""}
    ]

    response_answer = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        system=system_answer,
        messages=messages_for_answer,
    )

    answer_text = response_answer.content[0].text
    log_id = save_question_log(question, "normal", sql, row_count, answer_text)
    return {
        "type": "success",
        "sql": sql,
        "df": df,
        "answer": answer_text,
        "row_count": row_count,
        "log_id": log_id,
    }


def render_feedback_buttons(log_id: int, msg_index: int):
    """👍/👎フィードバックをst.formで確実に保存"""
    if log_id is None:
        return

    fb_key  = f"fb_{msg_index}"
    lid_key = f"lid_{msg_index}"
    if lid_key not in st.session_state:
        st.session_state[lid_key] = int(log_id)

    state = st.session_state.get(fb_key)

    if state == "done":
        st.caption("✅ フィードバックありがとうございます")
        return

    if state == "bad_note":
        # 👎後のコメント入力フォーム
        with st.form(key=f"fb_note_form_{msg_index}"):
            note = st.text_input("どこが問題でしたか？（任意）")
            submitted = st.form_submit_button("送信")
            if submitted:
                result = save_feedback(st.session_state[lid_key], 0, note)
                if result is True:
                    st.session_state[fb_key] = "done"
                else:
                    st.error(f"保存失敗: {result}")
        return

    # 👍👎選択フォーム（2つ別々のフォームにしてEnter誤送信を防ぐ）
    col1, col2, _ = st.columns([1, 1, 8])
    with col1:
        with st.form(key=f"fb_good_form_{msg_index}"):
            if st.form_submit_button("👍"):
                result = save_feedback(st.session_state[lid_key], 1, "")
                if result is True:
                    st.session_state[fb_key] = "done"
                    st.rerun()
                else:
                    st.error(f"保存失敗: {result}")
    with col2:
        with st.form(key=f"fb_bad_form_{msg_index}"):
            if st.form_submit_button("👎"):
                st.session_state[fb_key] = "bad_note"
                st.rerun()


def main():
    if not check_password():
        return

    with st.sidebar:
        st.markdown("### 📊 データ問い合わせ")
        st.markdown("ログシスのデータに日本語で質問できます。")
        st.markdown("---")

        st.markdown("**質問例**")
        examples = [
            "今期の売上上位10顧客は？",
            "石川さんの今月の売上合計は？",
            "商品カテゴリ別の在庫数量は？",
            "NEWHATTAN製品の今期仕入金額は？",
            "仕入先ごとの今期輸入経費率（予定vs実績）は？",
            "期別の売上金額と粗利の推移",
            "帽子1000個5ドルをCFSで輸入する場合の経費は？",
        ]
        for ex in examples:
            if st.button(ex, key=ex, use_container_width=True):
                st.session_state.pending_question = ex

        st.markdown("---")
        if st.button("🗑 会話をリセット", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

        st.markdown("---")
        st.caption("データは sync.py 実行時点のものです")

    st.title("📊 ログシス データ問い合わせ")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for i, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if "df" in msg:
                with st.expander(f"📋 データ詳細（{msg['row_count']}件）"):
                    st.dataframe(msg["df"], use_container_width=True)
            if "sql" in msg:
                with st.expander("🔍 実行SQL"):
                    st.code(msg["sql"], language="sql")
            if msg["role"] == "assistant" and msg.get("log_id"):
                render_feedback_buttons(msg["log_id"], i)

    if "pending_question" in st.session_state:
        question = st.session_state.pop("pending_question")
    else:
        question = st.chat_input("例: 今期の売上上位10顧客は？")

    if question:
        with st.chat_message("user"):
            st.markdown(question)
        st.session_state.messages.append({"role": "user", "content": question})

        with st.chat_message("assistant"):
            with st.spinner("データを調べています..."):
                schema = get_schema_info()
                history = [
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages[:-1]
                    if m["role"] in ("user", "assistant")
                ]
                result = ask_claude(question, schema, history)

            st.markdown(result["answer"])

            assistant_msg = {
                "role": "assistant",
                "content": result["answer"],
            }

            if result["type"] == "success":
                if result.get("is_estimate"):
                    df_disp = result["df"].copy()
                    def style_rate(df):
                        styles = pd.DataFrame("", index=df.index, columns=df.columns)
                        if "推奨経費率" in df.columns:
                            styles["推奨経費率"] = "font-weight: bold; font-size: 1.15em; color: #d04000;"
                        return styles
                    st.dataframe(
                        df_disp.style.apply(style_rate, axis=None),
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "推奨経費率": st.column_config.TextColumn(
                                "推奨経費率 ★",
                                help="中央値の経費率（倍率）",
                                width="small",
                            ),
                        },
                    )
                    with st.expander("🔍 実行SQL"):
                        st.code(result["sql"], language="sql")
                else:
                    with st.expander(f"📋 データ詳細（{result['row_count']}件）"):
                        st.dataframe(result["df"], use_container_width=True)
                    with st.expander("🔍 実行SQL"):
                        st.code(result["sql"], language="sql")
                assistant_msg["df"] = result["df"]
                assistant_msg["sql"] = result["sql"]
                assistant_msg["row_count"] = result["row_count"]
            elif "sql" in result:
                with st.expander("🔍 実行SQL（エラー）"):
                    st.code(result["sql"], language="sql")

            # log_idは全ケースで保持
            assistant_msg["log_id"] = result.get("log_id")

            # 新しい回答へのフィードバックボタン
            new_msg_index = len(st.session_state.messages)
            render_feedback_buttons(result.get("log_id"), new_msg_index)

        st.session_state.messages.append(assistant_msg)


if __name__ == "__main__":
    main()
