"""
sync_production_data.py — 生産管理チーム Googleスプレッドシート → Supabase 同期スクリプト

logsys-chat リポジトリの sync.py と同じ設計方針(全件DROP→COPYで置き換え、
psycopg2のCOPYで高速投入)を踏襲するが、データソースは Excel ファイルではなく
Google スプレッドシート(サンプル/量産の2タブ)である点が異なる。

【対象テーブル】
  サンプル タブ → production_samples
  量産     タブ → production_mass

これらは既存の purchase_orders テーブルとは別の新規テーブルとして同期する
(重複させない・既存データを壊さないため)。量産タブの "PO#" 列は
purchase_orders."PO_No" と同じ体系の値が入っているはずだが、テーブルとしては
結合せず、案件を横断的に見たいときは PO# / PO_No をキーに問い合わせ時に
JOINする、という考え方(sync.py の purchases⇔products の関係と同じ)。

【環境変数】
  SUPABASE_DB_URL    : SupabaseのDirect接続URL(logsys-chatと同じ値でよい)
  GOOGLE_SA_KEY_JSON  : Service AccountのJSONキー（文字列）
  PRODUCTION_SHEET_ID : 生産管理チームのGoogleスプレッドシートID

使い方:
  ローカル: python sync_production_data.py
  GitHub Actions: 自動実行（workflow_dispatch、または他リポジトリからの呼び出し）
"""
from __future__ import annotations

import io
import json
import os
import sys
import time
from urllib.parse import urlparse

import pandas as pd
import psycopg2
from sqlalchemy import create_engine, text

# =============================
# 設定
# =============================
SUPABASE_URL = os.environ.get("SUPABASE_DB_URL", "")
SA_KEY_JSON = os.environ.get("GOOGLE_SA_KEY_JSON", "")
PRODUCTION_SHEET_ID = os.environ.get(
    "PRODUCTION_SHEET_ID", "1722vOB9mNUqFTjDkbPO3A6nz-WOsW0PSME2Voor5Iy8"
)

# タブ名 → 同期先テーブル名
SHEET_TABLE_MAP = {
    "サンプル": "production_samples",
    "量産": "production_mass",
}


# =============================
# Google スプレッドシートから取得
# =============================
def _gspread_client():
    import gspread
    from google.oauth2 import service_account

    if not SA_KEY_JSON:
        print("❌ GOOGLE_SA_KEY_JSON が設定されていません。")
        sys.exit(1)
    sa_info = json.loads(SA_KEY_JSON)
    creds = service_account.Credentials.from_service_account_info(
        sa_info,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets.readonly",
            "https://www.googleapis.com/auth/drive.readonly",
        ],
    )
    return gspread.authorize(creds)


def _dedupe_and_clean_columns(raw_headers: list[str]) -> list[str]:
    """列名を一意かつDBカラム名として安全な形にする。

    元データには「同名列が2つ(SlackID×2)」「見出しが空欄の列」が
    実在する — get_all_records() 相当の素朴な辞書変換だと、同名列は
    後勝ちでデータが消え、空欄列は KeyError の原因になる。ここでは
    get_all_values() で取得した生の行として扱い、列名を機械的に
    一意化してから DataFrame 化することで、この2つの実データ上の
    問題を安全に吸収する。
    """
    replacements = {
        "（": "", "）": "", "(": "", ")": "",
        "　": "_", " ": "_", "／": "_", "/": "_",
        "：": "_", ":": "_", "・": "_", "、": "",
        "#": "num", "＃": "num", "②": "2",
        "\n": "_", "\r": "",
    }

    def _base_clean(raw: str, idx: int) -> str:
        name = (raw or "").strip()
        if not name:
            return f"col_{idx + 1}"
        for k, v in replacements.items():
            name = name.replace(k, v)
        return name.strip("_") or f"col_{idx + 1}"

    base_names = [_base_clean(h, i) for i, h in enumerate(raw_headers)]
    counts: dict[str, int] = {}
    for name in base_names:
        counts[name] = counts.get(name, 0) + 1

    cleaned: list[str] = []
    seen: dict[str, int] = {}
    for i, name in enumerate(base_names):
        if counts[name] > 1:
            # 同名列が複数ある場合(例: SlackIDが2つ)、直前の列名を手がかりに
            # 両方を区別できる名前にする。それでも衝突するなら連番で確実に一意化する。
            prev_name = base_names[i - 1] if i > 0 else ""
            candidate = f"{name}_{prev_name}" if prev_name else name
            seen[candidate] = seen.get(candidate, 0) + 1
            if seen[candidate] > 1:
                candidate = f"{name}_{seen[candidate]}"
            name = candidate
        cleaned.append(name)
    return cleaned


def load_production_sheet(gc, sheet_id: str, tab_name: str) -> pd.DataFrame:
    sh = gc.open_by_key(sheet_id)
    ws = sh.worksheet(tab_name)
    values = ws.get_all_values()
    if not values:
        print(f"  ⚠ '{tab_name}' タブにデータがありません。")
        return pd.DataFrame()

    raw_headers, rows = values[0], values[1:]
    columns = _dedupe_and_clean_columns(raw_headers)
    df = pd.DataFrame(rows, columns=columns)
    print(f"  ✓ '{tab_name}'（Google Sheets）: {len(df):,} 行（フィルタ前）")
    return df


def filter_real_rows(df: pd.DataFrame, label: str) -> pd.DataFrame:
    """「行番号(num)列が空欄でなく、かつ '例' という説明用マーカーでもない」
    行だけを実データとして残す。

    当初は「numが正の整数であること」を基準にしていたが、実データを
    精査したところ、本来は正しい依頼データなのに num 列に誤って商品コード
    (例:'SLG-05182')や記号(例:'。。')が入力されている行が実在することが
    判明した — 厳密な数値判定だとこれらの実データまで誤って除外してしまう。
    「空欄かどうか」「'例'という既知の説明行マーカーと一致するか」という、
    より緩やかだが取りこぼしのない基準に変更した。
    """
    before = len(df)
    if "num" not in df.columns:
        print(f"    ⚠ [{label}] 行番号列 'num' が見つからないため、フィルタをスキップします。")
        return df
    stripped = df["num"].astype(str).str.strip()
    df = df[(stripped != "") & (stripped != "例")].copy()
    excluded = before - len(df)
    print(f"    [{label}] 実データ判定: {len(df):,}行を採用（{excluded:,}行を例示・空白として除外）")
    return df


# =============================
# DB同期（COPY方式、sync.py と同じ方式）
# =============================
def get_psycopg2_conn(url: str):
    parsed = urlparse(url)
    return psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        dbname=parsed.path.lstrip("/"),
        user=parsed.username,
        password=parsed.password,
        options="-c statement_timeout=0 -c lock_timeout=0",
        connect_timeout=30,
    )


def sync_table_copy(url: str, df: pd.DataFrame, table_name: str):
    """COPY方式で高速同期（sync.py と同一ロジック）。毎回DROP→全件COPYで
    置き換えるため、再実行しても重複せず、常にスプレッドシートの最新内容と
    一致する状態になる。"""
    engine = create_engine(
        url,
        pool_pre_ping=True,
        connect_args={"options": "-c statement_timeout=0 -c lock_timeout=0"},
    )
    with engine.begin() as conn:
        conn.execute(text(f'DROP TABLE IF EXISTS "{table_name}" CASCADE'))
    df.head(0).to_sql(table_name, engine, if_exists="replace", index=False)

    conn_pg = get_psycopg2_conn(url)
    try:
        cur = conn_pg.cursor()
        buf = io.StringIO()
        df.to_csv(buf, index=False, na_rep="\\N")
        buf.seek(0)
        col_list = ", ".join(f'"{c}"' for c in df.columns)
        cur.execute(f'TRUNCATE TABLE "{table_name}"')
        cur.copy_expert(
            f"""COPY "{table_name}" ({col_list})
                FROM STDIN WITH (FORMAT CSV, HEADER TRUE, NULL '\\N')""",
            buf,
        )
        conn_pg.commit()
    finally:
        conn_pg.close()

    print(f"  ✓ {table_name}: {len(df):,} 行")


def report_po_match_rate(engine, df_mass: pd.DataFrame) -> None:
    """量産タブの PO# が、既存 purchase_orders."PO_No" とどれだけ一致するかを
    毎回レポートする（同期をブロックはしない・情報提供のみ）。
    突き合わせがうまくいかなくなった場合の早期発見が目的。"""
    po_col = "POnum" if "POnum" in df_mass.columns else None
    if po_col is None:
        print("  ⚠ 量産データにPO番号列が見つからないため、突合レポートをスキップします。")
        return
    try:
        with engine.begin() as conn:
            result = conn.execute(text('SELECT DISTINCT "PO_No" FROM purchase_orders'))
            known_po_numbers = {row[0] for row in result}
    except Exception as e:
        print(f"  ⚠ purchase_orders との突合チェックに失敗しました（同期は続行）: {e}")
        return

    po_values = df_mass[po_col].dropna()
    po_values = po_values[po_values.str.strip() != ""]
    if len(po_values) == 0:
        return
    matched = po_values.isin(known_po_numbers).sum()
    rate = matched / len(po_values) * 100
    print(f"  📊 量産タブのPO#とpurchase_ordersの一致率: {matched:,}/{len(po_values):,} 件（{rate:.1f}%）")
    if rate < 80:
        unmatched_sample = po_values[~po_values.isin(known_po_numbers)].head(5).tolist()
        print(f"    ⚠ 一致率が低下しています。未一致の例: {unmatched_sample}")


# =============================
# メイン
# =============================
def main():
    if not SUPABASE_URL:
        print("❌ SUPABASE_DB_URL が設定されていません。")
        sys.exit(1)

    print("\n📂 生産管理スプレッドシートに接続中...")
    gc = _gspread_client()

    engine = create_engine(
        SUPABASE_URL,
        pool_pre_ping=True,
        connect_args={"options": "-c statement_timeout=0 -c lock_timeout=0"},
    )

    total_start = time.time()
    loaded: dict[str, pd.DataFrame] = {}

    print("\n📖 スプレッドシート読み込み中...")
    for tab_name, table_name in SHEET_TABLE_MAP.items():
        df = load_production_sheet(gc, PRODUCTION_SHEET_ID, tab_name)
        if df.empty:
            continue
        df = filter_real_rows(df, tab_name)
        loaded[table_name] = df

    print("\n📤 Supabaseへ同期中（COPY方式・高速）...")
    for table_name, df in loaded.items():
        t = time.time()
        sync_table_copy(SUPABASE_URL, df, table_name)
        print(f"    ({time.time() - t:.1f}秒)")

    if "production_mass" in loaded:
        print("\n🔗 既存 purchase_orders との突合状況を確認中...")
        report_po_match_rate(engine, loaded["production_mass"])

    elapsed = time.time() - total_start
    print(f"\n✅ 生産管理データ同期完了！ 合計 {elapsed:.0f}秒\n")


if __name__ == "__main__":
    main()