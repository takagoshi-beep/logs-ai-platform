"""
sync_logsys_excel.py — ログシス Excel → Supabase 同期スクリプト

2026-07-10（14.66、Noritsuguの指定）: 元は logsys-chat リポジトリの
sync.py（旧・別アプリの本体）だったものを、logs-ai-platform に一本化
するために移植した。ロジック自体は変更していない（動作実績のある
スクリプトのため、移植に伴うリスクを避け、そのまま持ってきている）。

移植の経緯: これまでlogsys-chatが「ログシス本体Excel→Supabase」の同期
を担い、その同期完了後にrepository_dispatchでlogs-ai-platform側の
「生産管理データ同期」(scripts/sync_production_data.py)を呼び出す
という2リポジトリ構成だった。logsys-chatのStreamlitチャット機能は
logs-ai-platformの「相談」機能に置き換わったため、logsys-chatリポジトリ
自体を廃止し、この同期スクリプトだけをこちらに移植して一本化した。
以後は.github/workflows/sync_logsys_excel.ymlから、このスクリプトの
実行→生産管理データ同期の実行、を同じワークフロー内で連続実行する
（別リポジトリを経由しないため、repository_dispatch用のPAT
（PRODUCTION_SYNC_PAT）も不要になった）。

使い方:
  ローカル: python scripts/sync_logsys_excel.py
  GitHub Actions: .github/workflows/sync_logsys_excel.yml（workflow_dispatch）

【環境変数】
  SUPABASE_DB_URL      : SupabaseのDirect接続URL（sync_production_data.pyと共通）
  GOOGLE_SA_KEY_JSON   : Service AccountのJSONキー（文字列、sync_production_data.pyと共通）
  GDRIVE_FOLDER_ID     : Google DriveのフォルダID
  EXCEL_FILENAME       : Excelファイル名（省略時は自動検索）
"""

import io
import os
import re
import sys
import json
import time
import tempfile
import pandas as pd
import psycopg2
from urllib.parse import urlparse
from sqlalchemy import create_engine, text

# =============================
# 設定
# =============================
SUPABASE_URL     = os.environ.get("SUPABASE_DB_URL", "")
SA_KEY_JSON      = os.environ.get("GOOGLE_SA_KEY_JSON", "")
GDRIVE_FOLDER_ID = os.environ.get("GDRIVE_FOLDER_ID", "1ptYjFOzJcBopyk4AAIodep1fnLAbgBaB")
EXCEL_FILENAME   = os.environ.get("EXCEL_FILENAME", "")   # 空なら.xlsxを自動検索

# ローカル実行用フォールバック
LOCAL_EXCEL_PATH = os.environ.get("EXCEL_PATH", "")

STAFF_SHEET_ID           = "1Xbxc-Jz6ifcrXZZlpxBFUCoeXrKjy6l9lNbA_GiR4Rs"
BUDGET_FORECAST_SHEET_ID = "15zLcbkrwsrqkQumQ9YH9CwZP6DXsdqKZTEyPxbxcgNA"
# COST_SHEET_ID は不要（予算予定シートに05_費用が既に含まれているため）
# COST_SHEET_ID = "1vQemmGzVx6e-2glMchR-vSFen8A8R219_MZHaoXK0qA" 

SHEET_TABLE_MAP = {
    "売上":     "sales",
    "顧客":     "customers",
    "顧客担当者": "customer_contacts",
    "商品":     "products",
    "仕入":     "purchases",
    "発注依頼":  "purchase_orders",
    "取引先":   "suppliers",
    "仕入諸掛":  "purchase_surcharges",
    "コード":   "code_master",
}


# =============================
# Google Drive からExcelを取得
# =============================
def download_excel_from_drive() -> str:
    """Google DriveからExcelをダウンロードして一時ファイルパスを返す"""
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseDownload
    except ImportError:
        print("❌ google-api-python-client が未インストールです。")
        print("   pip install google-api-python-client google-auth")
        sys.exit(1)

    print("🔑 Google Drive に接続中...")
    sa_info = json.loads(SA_KEY_JSON)
    creds = service_account.Credentials.from_service_account_info(
        sa_info,
        scopes=["https://www.googleapis.com/auth/drive.readonly"],
    )
    service = build("drive", "v3", credentials=creds)

    # フォルダ内のxlsxファイルを検索
    query = (
        f"'{GDRIVE_FOLDER_ID}' in parents"
        " and mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'"
        " and trashed=false"
    )
    if EXCEL_FILENAME:
        query += f" and name='{EXCEL_FILENAME}'"

    results = service.files().list(
        q=query,
        fields="files(id, name, modifiedTime)",
        orderBy="modifiedTime desc",
    ).execute()

    files = results.get("files", [])
    if not files:
        print(f"❌ Google DriveフォルダにExcelファイルが見つかりません。")
        print(f"   フォルダID: {GDRIVE_FOLDER_ID}")
        sys.exit(1)

    # 最新のファイルを使用
    target = files[0]
    print(f"  ✓ ファイル発見: {target['name']} (更新: {target['modifiedTime']})")

    # ダウンロード
    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    request = service.files().get_media(fileId=target["id"])
    downloader = MediaIoBaseDownload(tmp, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    tmp.close()
    print(f"  ✓ ダウンロード完了: {tmp.name}")
    return tmp.name


def get_excel_path() -> str:
    """ExcelファイルのパスをDriveまたはローカルから取得"""
    if SA_KEY_JSON:
        return download_excel_from_drive()
    elif LOCAL_EXCEL_PATH and os.path.exists(LOCAL_EXCEL_PATH):
        print(f"  ✓ ローカルファイルを使用: {LOCAL_EXCEL_PATH}")
        return LOCAL_EXCEL_PATH
    else:
        # カレントディレクトリのxlsxを自動検索
        xlsxfiles = [f for f in os.listdir(".") if f.endswith(".xlsx")]
        if xlsxfiles:
            print(f"  ✓ ローカルファイルを使用: {xlsxfiles[0]}")
            return xlsxfiles[0]
        print("❌ Excelファイルが見つかりません。")
        print("   GOOGLE_SA_KEY_JSON または EXCEL_PATH を設定してください。")
        sys.exit(1)


# =============================
# データ処理
# =============================
def clean_column_name(col: str) -> str:
    replacements = {
        "（": "", "）": "", "(": "", ")": "",
        "　": "_", " ": "_", "／": "_", "/": "_",
        "：": "_", ":": "_", "・": "_", "、": "",
        "#": "num", "②": "2",
    }
    for k, v in replacements.items():
        col = col.replace(k, v)
    return col.strip("_")


def load_sheet(xl: pd.ExcelFile, sheet_name: str) -> pd.DataFrame:
    df = pd.read_excel(xl, sheet_name=sheet_name)
    df.columns = [clean_column_name(c) for c in df.columns]
    for col in df.select_dtypes(include=["datetime64[us, UTC]", "datetimetz"]).columns:
        df[col] = df[col].dt.tz_localize(None)
    if "メモ" in df.columns:
        df = df[~df["メモ"].astype(str).str.contains("ダミーデータ", na=False)]
    return df


# 商品名キーワード → 商品分類コードの対応表
CATEGORY_KEYWORDS = {
    1: ["hat", "cap", "帽子", "beret", "beanie", "bucket hat", "snapback", "trucker",
        "casquette", "visor", "safari", "straw hat", "knit cap", "watch cap"],
    2: ["bag", "バッグ", "tote", "backpack", "rucksack", "handbag", "shoulder", "clutch",
        "pouch", "sacoche", "satchel", "duffel", "トート", "リュック", "ショルダー", "ナップサック"],
    3: ["wallet", "財布", "purse", "card case", "小物", "ポーチ", "pouch", "coin",
        "key case", "キーケース", "パスケース"],
    4: ["sunglasses", "glasses", "サングラス", "メガネ", "eyewear", "goggle"],
    5: ["scarf", "stole", "muffler", "マフラー", "スカーフ", "ストール", "バンダナ",
        "bandana", "neckerchief", "snood", "手ぬぐい"],
    6: ["t-shirt", "tee", "shirt", "jacket", "coat", "pants", "dress", "tops",
        "アパレル", "tシャツ", "ジャケット", "コート", "パンツ", "ワンピース", "hoodie",
        "sweat", "sweater", "knit", "ニット", "ブルゾン", "ベスト"],
    7: ["belt", "ベルト"],
    8: ["shoes", "sneaker", "boots", "sandal", "loafer", "靴", "スニーカー",
        "ブーツ", "サンダル", "履物", "socks", "ソックス", "stocking"],
    9: ["necklace", "bracelet", "ring", "earring", "accessory", "アクセサリー",
        "ネックレス", "ブレスレット", "リング", "ピアス", "brooch", "charm"],
}


def guess_category_from_name(name: str) -> int | None:
    """商品名のキーワードから商品分類コードを類推する"""
    if not isinstance(name, str):
        return None
    name_lower = name.lower()
    for cat_code, keywords in CATEGORY_KEYWORDS.items():
        if any(kw.lower() in name_lower for kw in keywords):
            return cat_code
    return None


def enrich_purchases(df_purchases: pd.DataFrame, df_products: pd.DataFrame) -> pd.DataFrame:
    """
    purchasesに商品分類を追加（app.pyのJOINレス化）
    ① 商品マスタIDでJOIN（型を数値に統一）
    ② 商品分類=10（その他）または未設定の場合、商品名キーワードで補完
    """
    if "商品分類" not in df_products.columns:
        print("  ⚠ productsに商品分類カラムが見つかりません。enrichスキップ。")
        return df_purchases

    # 型を数値に統一してJOIN
    df_prod_slim = df_products[["ID", "商品分類", "商品名"]].copy()
    df_prod_slim["ID"] = pd.to_numeric(df_prod_slim["ID"], errors="coerce")
    df_prod_slim["商品分類"] = pd.to_numeric(df_prod_slim["商品分類"], errors="coerce")
    df_prod_slim = df_prod_slim.rename(columns={"ID": "商品マスタID", "商品名": "商品名_master"})

    df_purchases = df_purchases.copy()
    df_purchases["商品マスタID"] = pd.to_numeric(df_purchases["商品マスタID"], errors="coerce")

    df_merged = df_purchases.merge(df_prod_slim, on="商品マスタID", how="left")

    if "商品分類_x" in df_merged.columns:
        df_merged["商品分類"] = df_merged["商品分類_y"].combine_first(df_merged["商品分類_x"])
        df_merged = df_merged.drop(columns=["商品分類_x", "商品分類_y"])

    matched_before = df_merged["商品分類"].notna().sum()

    # 商品分類が未設定または10（その他）の場合、商品名キーワードで補完
    mask = df_merged["商品分類"].isna() | (df_merged["商品分類"] == 10)
    for idx in df_merged[mask].index:
        guessed = guess_category_from_name(df_merged.at[idx, "商品名"])
        if guessed is None and "商品名_master" in df_merged.columns:
            guessed = guess_category_from_name(df_merged.at[idx, "商品名_master"])
        if guessed is not None:
            df_merged.at[idx, "商品分類"] = guessed

    # 商品名_masterカラムは不要なので削除
    if "商品名_master" in df_merged.columns:
        df_merged = df_merged.drop(columns=["商品名_master"])

    matched_after = df_merged["商品分類"].notna().sum()
    補完件数 = matched_after - matched_before
    print(f"  ✓ purchases に商品分類を追加")
    print(f"    マスタJOIN: {matched_before:,}件マッチ → キーワード補完: +{補完件数:,}件 → 合計: {matched_after:,}/{len(df_merged):,}件")
    return df_merged


# =============================
# DB同期（COPY方式）
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
    """COPY方式で高速同期（INSERTの10〜50倍速）"""
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


def create_views(engine):
    views = {
        "v_sales_summary": """
            CREATE OR REPLACE VIEW v_sales_summary AS
            SELECT
                期 AS fiscal_period,
                "ID" AS invoice_id,
                納品伝票日 AS delivery_date,
                得意先名 AS customer_name,
                ブランド名 AS brand_name,
                営業担当者名 AS sales_rep,
                売上合計金額 AS total_sales,
                粗利 AS gross_profit,
                粗利率 AS gross_margin_rate,
                売上確定フラグ AS is_confirmed,
                ステータス AS status_code
            FROM sales
        """,
        "v_product_master": """
            CREATE OR REPLACE VIEW v_product_master AS
            SELECT
                "ID" AS product_id,
                "LOGS_CODE" AS logs_code,
                "Sample_CODE" AS sample_code,
                商品名 AS product_name,
                型番 AS model_no,
                仕入先名 AS supplier_name,
                CASE 商品分類
                    WHEN 1 THEN '帽子' WHEN 2 THEN 'バッグ' WHEN 3 THEN '財布/小物'
                    WHEN 4 THEN 'サングラス/メガネ' WHEN 5 THEN '巻物' WHEN 6 THEN 'アパレル'
                    WHEN 7 THEN 'ベルト' WHEN 8 THEN '履物' WHEN 9 THEN 'アクセサリー'
                    ELSE 'その他' END AS category,
                CASE 事業分類
                    WHEN 1 THEN 'OEM' WHEN 2 THEN '商品仕入れ(海外)' WHEN 3 THEN '商品仕入れ(国内)'
                    END AS business_type,
                論理在庫数量 AS logical_stock,
                論理在庫金額 AS logical_stock_value,
                通常売価 AS standard_price,
                発注単価 AS order_unit_price
            FROM products
        """,
        "v_customer_master": """
            CREATE OR REPLACE VIEW v_customer_master AS
            SELECT
                "ID" AS customer_id,
                顧客名称 AS customer_name,
                顧客カナ AS customer_kana,
                営業担当者名 AS sales_rep,
                CASE 顧客分類
                    WHEN 1 THEN 'セレクトショップ' WHEN 2 THEN '量販店' WHEN 3 THEN 'D2C'
                    WHEN 4 THEN 'その他小売店' WHEN 5 THEN 'メーカー業' WHEN 6 THEN '仲間卸'
                    WHEN 7 THEN 'グッズ制作' WHEN 8 THEN 'その他業界企業' ELSE 'その他'
                    END AS customer_category,
                住所 AS address,
                電話番号 AS phone,
                CASE 決済方法
                    WHEN 1 THEN '売掛' WHEN 2 THEN 'NP掛け払い' WHEN 3 THEN '代引'
                    WHEN 4 THEN '仮出庫' WHEN 5 THEN '入金後発送' WHEN 6 THEN '現金'
                    END AS payment_method
            FROM customers
        """,
        # 2026-07-10（14.68追加、Noritsuguが実際のエラーで発見）: このビュー
        # はlogsys-chatのsync.pyには元々無く、logs-ai-platform側で14.32
        # （docs/architecture.md）に追加したもの。salesテーブルはこの
        # 関数の直前でDROP→再作成されるため、依存するこのビューも一緒に
        # 消えてしまう。以前はこのcreate_views()にこのビューが含まれて
        # いなかったため、同期を実行するたびにv_sales_enrichedが消失し、
        # 「相談」機能のget_sales_lines等が"relation does not exist"エラー
        # で失敗する不具合が起きていた。ここに追加することで、同期の
        # たびに自動的に再作成されるようにした。
        # 定義はdocs/migrations/2026-07-09_v_sales_enriched.sqlと完全に
        # 一致させている（変更する際は両方直すこと）。
        "v_sales_enriched": """
            CREATE OR REPLACE VIEW v_sales_enriched AS
            SELECT
                s.*,
                CASE p."商品分類"
                    WHEN 1 THEN '帽子' WHEN 2 THEN 'バッグ' WHEN 3 THEN '財布/小物'
                    WHEN 4 THEN 'サングラス/メガネ' WHEN 5 THEN '巻物' WHEN 6 THEN 'アパレル'
                    WHEN 7 THEN 'ベルト' WHEN 8 THEN '履物' WHEN 9 THEN 'アクセサリー'
                    ELSE 'その他'
                    END AS "product_category",
                CASE c."顧客分類"
                    WHEN 1 THEN 'セレクトショップ' WHEN 2 THEN '量販店' WHEN 3 THEN 'D2C'
                    WHEN 4 THEN 'その他小売店' WHEN 5 THEN 'メーカー業' WHEN 6 THEN '仲間卸'
                    WHEN 7 THEN 'グッズ制作' WHEN 8 THEN 'その他業界企業' ELSE 'その他'
                    END AS "customer_category",
                c."事業規模" AS "customer_business_scale",
                c."取引傾向分類" AS "customer_trade_tendency",
                sup."生産管理担当者名" AS "supplier_production_staff",
                sr."メールアドレス" AS "sales_rep_email",
                sr."Slack ID" AS "sales_rep_slack_id",
                adm."メールアドレス" AS "sales_admin_email",
                adm."Slack ID" AS "sales_admin_slack_id",
                acc."メールアドレス" AS "accounting_email",
                acc."Slack ID" AS "accounting_slack_id"
            FROM sales s
            LEFT JOIN products p ON s."LOGS_CODE"::text = p."LOGS_CODE"::text
            LEFT JOIN customers c ON s."得意先ID"::text = c."ID"::text
            LEFT JOIN suppliers sup ON s."仕入先ID"::text = sup."ID"::text
            LEFT JOIN staff sr ON s."営業担当者ID"::text = sr."ID（編集禁止）"::text
            LEFT JOIN staff adm ON s."事務処理担当者ID"::text = adm."ID（編集禁止）"::text
            LEFT JOIN staff acc ON s."経理担当者ID"::text = acc."ID（編集禁止）"::text
        """,
    }
    with engine.begin() as conn:
        for view_name, ddl in views.items():
            conn.execute(text(ddl))
            print(f"  ✓ view: {view_name}")


def load_staff_from_sheets() -> pd.DataFrame | None:
    """Google Sheetsから社員マスタを取得"""
    if not SA_KEY_JSON:
        print("  ⚠ GOOGLE_SA_KEY_JSON未設定。社員マスタスキップ。")
        return None
    try:
        import gspread
        from google.oauth2 import service_account
        sa_info = json.loads(SA_KEY_JSON)
        creds = service_account.Credentials.from_service_account_info(
            sa_info,
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets.readonly",
                "https://www.googleapis.com/auth/drive.readonly",
            ],
        )
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(STAFF_SHEET_ID)
        ws = sh.get_worksheet(0)
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        # 退職者を除外
        if "退職者フラグ" in df.columns:
            df = df[df["退職者フラグ"].astype(str) != "1"]
        print(f"  ✓ 社員マスタ（Google Sheets）: {len(df):,} 件")
        return df
    except Exception as e:
        import traceback
        print(f"  ⚠ 社員マスタ取得失敗: {type(e).__name__}: {e}")
        print(traceback.format_exc())
        return None


def normalize_year(v) -> str | None:
    """年カラムの値を '2026' 形式に正規化。取れない場合はNone。"""
    s = str(v).strip()
    m = re.search(r'(20\d{2}|19\d{2})', s)
    return m.group(1) if m else None


def normalize_month(v) -> str | None:
    """月カラムの値を '06月' 形式に正規化。取れない場合はNone。"""
    s = str(v).strip()
    m = re.search(r'(\d{1,2})', s)
    if m:
        month_num = int(m.group(1))
        if 1 <= month_num <= 12:
            return f"{month_num:02d}月"
    return None


def clean_budget_df(df: pd.DataFrame, source_label: str) -> pd.DataFrame:
    """
    budget_forecast / 費用データ共通のクレンジング処理:
    - 分類が空の行を除去
    - #REF! 等のエラー値を含む行を除去
    - 年・月カラムを正規化
    - 数値カラムの型変換
    """
    # 空行を除去（分類が空の行）
    if "分類" in df.columns:
        df = df[df["分類"].astype(str).str.strip() != ""]

    # #REF! 等スプレッドシートのエラー値を含む行を除去
    error_pattern = r'#(REF|VALUE|NAME|DIV/0|N/A|NULL|NUM)!'
    if "分類" in df.columns:
        before = len(df)
        df = df[~df["分類"].astype(str).str.contains(error_pattern, regex=True, na=False)]
        excluded = before - len(df)
        if excluded > 0:
            print(f"    [{source_label}] エラー値除外: {excluded:,}行")

    # 年カラムの正規化（空・1899等を除外し '2026' 形式に統一）
    if "年" in df.columns:
        before = len(df)
        df["年"] = df["年"].apply(normalize_year)
        df = df[df["年"].notna()].copy()
        excluded = before - len(df)
        if excluded > 0:
            print(f"    [{source_label}] 年クレンジング: {excluded:,}行除外（空・不正値）")

    # 月カラムの正規化（'06月' 形式に統一）
    if "月" in df.columns:
        before = len(df)
        df["月"] = df["月"].apply(normalize_month)
        df = df[df["月"].notna()].copy()
        excluded = before - len(df)
        if excluded > 0:
            print(f"    [{source_label}] 月クレンジング: {excluded:,}行除外（空・不正値）")

    # 数値カラムの型変換（カラム名はスプレッドシートの実際の名称）
    num_cols = ["案件売上", "案件粗利", "案件粗利率",
                "①二次加工費（副資材単価、資材等運送含む）", "②検品（検針、検査含む）",
                "③サンプル費用", "④その他販売経費"]
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", ""), errors="coerce")

    return df


def load_sheet_data(gc, sheet_id: str, label: str) -> pd.DataFrame | None:
    """指定シートIDの1シート目を取得してDataFrameで返す"""
    try:
        sh = gc.open_by_key(sheet_id)
        ws = sh.get_worksheet(0)
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        print(f"  ✓ {label}（Google Sheets）: {len(df):,} 件（クレンジング前）")
        return df
    except Exception as e:
        import traceback
        print(f"  ⚠ {label}取得失敗: {type(e).__name__}: {e}")
        print(traceback.format_exc())
        return None


def load_budget_forecast_from_sheets() -> pd.DataFrame | None:
    """
    Google Sheetsから予算・予定データと費用データを取得して結合する。
    - 予算予定シート (BUDGET_FORECAST_SHEET_ID): 01_予算/02_予定/03_発注/04_実績
    - 費用シート     (COST_SHEET_ID):            05_費用
    両シートは同じフォーマット。クレンジング後にpd.concatで結合。
    """
    if not SA_KEY_JSON:
        print("  ⚠ GOOGLE_SA_KEY_JSON未設定。予算データスキップ。")
        return None
    try:
        import gspread
        from google.oauth2 import service_account
        sa_info = json.loads(SA_KEY_JSON)
        creds = service_account.Credentials.from_service_account_info(
            sa_info,
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets.readonly",
                "https://www.googleapis.com/auth/drive.readonly",
            ],
        )
        gc = gspread.authorize(creds)

        # 予算予定シート取得・クレンジング
        df_budget = load_sheet_data(gc, BUDGET_FORECAST_SHEET_ID, "予算・予定データ")
        if df_budget is not None and not df_budget.empty:
            df_budget = clean_budget_df(df_budget, "予算予定")
        else:
            df_budget = None

        # 費用データは予算予定シートに含まれているため別途読み込み不要
        if df_budget is None or df_budget.empty:
            print("  ⚠ 予算・予定データが取得できませんでした。")
            return None

        return df_budget

    except Exception as e:
        import traceback
        print(f"  ⚠ 予算・予定データ取得失敗: {type(e).__name__}: {e}")
        print(traceback.format_exc())
        return None


def create_schema_comment(engine):
    schema_info = [
        ("sales",             "売上明細",   "納品伝票ベースの売上トランザクション。1伝票=複数行。商品分類はproductsテーブルと商品IDでJOINして取得（LEFT JOIN products p ON s.\"商品ID\"::text = p.\"ID\"::text）"),
        ("customers",         "顧客マスタ", "取引先（得意先）情報。顧客名称・顧客分類・営業担当者名・住所など"),
        ("customer_contacts", "顧客担当者", "顧客ごとの担当者連絡先。担当者氏名・メールアドレス・電話番号など"),
        ("products",          "商品マスタ", "SKUレベルの商品情報。商品名・型番・商品分類・仕入先・在庫数量・売価など"),
        ("purchases",         "仕入明細",   "仕入トランザクション。仕入先・仕入金額・諸掛込金額・商品分類（products結合済み）など"),
        ("purchase_orders",   "発注依頼",   "POの発行から納品・輸送・検品スケジュールまで管理。案件名・発注金額・売上金額・粗利など"),
        ("suppliers",         "取引先マスタ", "仕入先・検品所・倉庫など取引先情報。取引先名・取引通貨・支払条件など"),
        ("code_master",       "コードマスタ", "各テーブルの数値コードを名称に変換するマスタ。コードID・コード値・コード名"),
        ("purchase_surcharges", "仕入諸掛明細", "仕入ID単位の輸入経費明細。諸掛区分ID: 1=関税, 2=国内手数料(税抜), 3=国内手数料消費税額, 4=運賃, 5=輸入消費税(地方), 6=輸入消費税(内国), 7=燃料サーチャージ, 8=通関料他。消費税は3・5・6。輸入経費合計はNOT IN(3,5,6)でフィルタ。金額(円)カラムを集計に使用。JOINキー: 仕入ID = purchasesの仕入ID"),
        ("budget_forecast",   "予算・予定・費用データ", "営業担当者×顧客×期×月単位の予算/予定/発注/実績/費用データ。分類カラムで01_予算/02_予定/03_発注/04_実績/05_費用を区別。チーム・商品分類・顧客詳細分類も含む。年はtext型('2026')・月はtext型('06月')。"),
        ("v_product_master",  "商品マスタビュー", "productsから主要項目を抽出しカテゴリ名称変換済み"),
        ("v_customer_master", "顧客マスタビュー", "customersから主要項目を抽出し分類名称変換済み"),
    ]
    df = pd.DataFrame(schema_info, columns=["table_name", "table_label", "description"])
    df.to_sql("_schema_info", engine, if_exists="replace", index=False)
    print("  ✓ _schema_info テーブル作成")


# =============================
# メイン
# =============================
def main():
    if not SUPABASE_URL:
        print("❌ SUPABASE_DB_URL が設定されていません。")
        sys.exit(1)

    print(f"\n📂 Excelファイルを取得中...")
    excel_path = get_excel_path()

    engine = create_engine(
        SUPABASE_URL,
        pool_pre_ping=True,
        connect_args={"options": "-c statement_timeout=0 -c lock_timeout=0"},
    )

    xl = pd.ExcelFile(excel_path)
    total_start = time.time()

    print("\n📖 Excelシート読み込み中...")
    loaded = {}
    for sheet_name, table_name in SHEET_TABLE_MAP.items():
        if sheet_name not in xl.sheet_names:
            print(f"  ⚠ シート '{sheet_name}' が見つかりません。スキップします。")
            continue
        loaded[table_name] = load_sheet(xl, sheet_name)
        print(f"  ✓ {sheet_name} → {table_name}: {len(loaded[table_name]):,} 行")

    if "purchases" in loaded and "products" in loaded:
        print("\n🔗 purchases に商品分類を付与中...")
        loaded["purchases"] = enrich_purchases(loaded["purchases"], loaded["products"])

    print("\n📤 Supabaseへ同期中（COPY方式・高速）...")
    for table_name, df in loaded.items():
        t = time.time()
        sync_table_copy(SUPABASE_URL, df, table_name)
        print(f"    ({time.time()-t:.1f}秒)")

    print("\n📊 予算・予定・費用データ同期中（Google Sheets）...")
    df_budget = load_budget_forecast_from_sheets()
    if df_budget is not None and not df_budget.empty:
        t = time.time()
        sync_table_copy(SUPABASE_URL, df_budget, "budget_forecast")
        print(f"    ({time.time()-t:.1f}秒)")

    print("\n👥 社員マスタ同期中（Google Sheets）...")
    df_staff = load_staff_from_sheets()
    if df_staff is not None and not df_staff.empty:
        t = time.time()
        sync_table_copy(SUPABASE_URL, df_staff, "staff")
        print(f"    ({time.time()-t:.1f}秒)")

    print("\n🔧 ビュー作成中...")
    create_views(engine)

    print("\n📋 スキーマ情報テーブル作成中...")
    create_schema_comment(engine)

    elapsed = time.time() - total_start
    print(f"\n✅ 同期完了！ 合計 {elapsed:.0f}秒")
    print("   チャットアプリに最新データが反映されました。\n")


if __name__ == "__main__":
    main()
