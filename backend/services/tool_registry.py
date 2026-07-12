"""Claude tool-use definitions mapping to `backend/`'s existing, already
real, already tested Provider `.fetch()` methods (docs/architecture.md
14.21).

No new data-access logic lives here. Every tool below is a thin,
schema-only wrapper around functionality already built and tested this
session (`data_providers.py`'s `LogsysProvider`/`ProductionProvider`,
`production_data.py`). This module's only job is translating between
Claude's tool-call format and those existing functions — the actual SQL,
business-rule filters (e.g. sales status/payment-method exclusions),
and error handling all stay exactly where they already were.
"""
from __future__ import annotations

import json
from typing import Any

from services.knowledge_loader import load_section

# 2026-07-10（14.62、Noritsuguの指定）: 用語・業務ルールの定義は
# knowledge/配下のMarkdownを唯一の正とし、ツール説明文はそこから動的に
# 読み込んで組み込む（手で書き写して二重管理にしない）。knowledge/の
# 内容を直せば、ツール説明文にも自動で反映される。
#
# load_sectionが空文字列を返す場合（ファイル未整備・見出し変更等）に
# 備えて、フォールバック文言を必ず用意する（Claudeへの説明が完全に
# 空になることを避けるため）。
_IMPORT_COST_RATIO_DEFINITION = load_section("semantic/purchase.md", "## 輸入経費率") or (
    "輸入経費率の定義はknowledge/semantic/purchase.mdを確認すること"
    "（読み込みに失敗したため、この場では詳細を表示できない）。"
)

TOOLS: list[dict[str, Any]] = [
    {
        "name": "get_sales_lines",
        "description": (
            "実際の売上明細を取得する。有効な受注のみを対象とする標準フィルタ"
            "（ステータス・決済方法）が既に適用済み。"
            "商品分類（product_category）・顧客分類（customer_category）は既に"
            "名称に変換済みで、そのまま使ってよい（get_code_masterで確認する"
            "必要はない）。商品分類・顧客分類ごとの合計が知りたい場合は、"
            "records/aggregateではなくget_sales_by_categoryを使うこと"
            "（分類は数種類しかないため200件の壁に引っかからず、正確に集計できる）。"
            "【合計金額・件数は必ず結果の`aggregate`フィールド（件数・売上金額合計・"
            "粗利合計）を使うこと。`records`を自分で合計・カウントしてはいけない —"
            "`records`は件数が多い場合に先頭200件だけに切り捨てられる（`truncated: "
            "true`）ことがあるが、`aggregate`は指定した条件（期間・顧客名・担当者名）"
            "全体に対してSQL側で正確に計算した値であり、切り捨ての影響を受けない】"
            "件数が多くなりやすいため、可能な限りperiod_start/period_endで"
            "期間を絞り込んで呼び出すこと（「今月」なら今月の初日〜末日を指定する）。"
            "取得した行には「事業分類」という数値コード列が含まれるが、"
            "その意味を推測してはいけない。get_code_masterで実際の意味を確認すること。"
            "「〇〇さんの売上/伝票」のように担当者で絞り込みたい場合はsales_rep_keywordを使う"
            "（営業担当者・営業事務・経理担当・伝票作成者のいずれかに一致すればヒットする。"
            "架空の担当者名で検索しても0件になるだけなので、実在するか不安な場合は"
            "get_customer_master等で事前確認する必要はない。0件ならそのまま正直に伝えること）。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "period_start": {"type": "string", "description": "期間開始日（YYYY-MM-DD形式）"},
                "period_end": {"type": "string", "description": "期間終了日（YYYY-MM-DD形式）"},
                "customer_keyword": {"type": "string", "description": "顧客名の部分一致キーワード"},
                "sales_rep_keyword": {"type": "string", "description": "担当者名の部分一致キーワード（営業担当者・営業事務・経理担当・伝票作成者のいずれかに一致すればヒット）。0件、または名前の一致が不確かな場合はfind_similar_name（domain=\"staff\"）で正式名称を確認してから呼び直すこと。"},
            },
        },
    },
    {
        "name": "get_sales_by_category",
        "description": (
            "商品分類、顧客分類、事業分類、または顧客(個別)ごとの売上"
            "（件数・合計金額・粗利）を、SQL側でGROUP BY集計して返す。"
            "「商品分類がバッグの売上は？」「顧客分類（D2C/量販店等）ごとの"
            "売上を教えて」「今月のOEMの売上は？」「〇〇さんの顧客ランキングを"
            "教えて」のような質問に使う。事業分類（business_type）は「OEM」"
            "「商品仕入れ（海外）」「商品仕入れ（国内）」の3区分（各行の"
            "`事業分類名`フィールドが既にラベル変換済みなので、get_code_master"
            "で確認する必要はない）。"
            "顧客ランキング・顧客ごとの売上比較が必要な場合は、必ず"
            "group_by=\"customer\"を使うこと — get_sales_linesは200件で"
            "records が切り捨てられるため、それだけで顧客ごとの合計を"
            "手計算すると、実際の順位や金額と異なる不正確な結果になる"
            "（2026-07-13、実際にこの誤りが発生した実例あり）。"
            "product_category/customer_category/business_typeは分類数が"
            "少ないため常に全件が返るが、customerは顧客数が多い場合200件で"
            "切り捨てられることがある（ただし売上金額の大きい順に返るため、"
            "上位の順位・金額自体は正確）。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "group_by": {
                    "type": "string",
                    "enum": ["product_category", "customer_category", "business_type", "customer"],
                    "description": "集計軸。product_category=商品分類別、customer_category=顧客分類別、business_type=事業分類別（OEM/商品仕入れ海外/商品仕入れ国内）、customer=顧客(個別)別。既定はproduct_category。",
                },
                "period_start": {"type": "string", "description": "期間開始日（YYYY-MM-DD形式）"},
                "period_end": {"type": "string", "description": "期間終了日（YYYY-MM-DD形式）"},
                "sales_rep_keyword": {"type": "string", "description": "担当者名の部分一致キーワード（営業担当者・営業事務・経理担当・伝票作成者のいずれかに一致すればヒット）。0件、または名前の一致が不確かな場合はfind_similar_name（domain=\"staff\"）で正式名称を確認してから呼び直すこと。"},
            },
        },
    },
    {
        "name": "get_purchase_lines",
        "description": (
            "実際の仕入明細（諸掛り込み金額）を取得する。仕入原価の分析に使う。"
            "【合計金額・件数・輸入経費率は必ず結果の`aggregate`フィールド（件数・仕入金額合計・"
            "諸掛込金額合計・輸入経費率）を使うこと。`records`は件数が多い場合に先頭200件だけに"
            "切り捨てられることがあるが、`aggregate`は指定した条件全体に対して"
            "SQL側で正確に計算した値なので、切り捨ての影響を受けない】\n\n"
            "【輸入経費率の定義（knowledge/semantic/purchase.mdより）】\n"
            f"{_IMPORT_COST_RATIO_DEFINITION}\n\n"
            "また、1ドル=◯◯円のような仮定の為替レートを使った架空の計算例・推奨値を"
            "作ってはいけない — 実データに基づかない数値は提示しないこと。"
            "回答内で具体的な仕入明細を引用する場合は、`POnum`（PO番号）・`LOGS_CODE`も"
            "併記し、実データであることが検証できるようにすること。"
            "輸入経費率の変動要因を説明する際は、取得したrecordsに実在する列（輸送方法・"
            "通貨・為替等）の値を実際に見て言及すること（含まれていない要因を推測で"
            "挙げてはいけない）。"
            "件数が多くなりやすいため、可能な限りperiod_start/period_endで期間を絞り込むこと。"
            "「〇〇さんの仕入」のように営業担当者で絞り込みたい場合はsales_rep_keywordを使う"
            "（明細レベルの担当者を優先し、空欄の場合のみ伝票レベルの担当者を採用済み）。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "period_start": {"type": "string", "description": "期間開始日（YYYY-MM-DD形式）"},
                "period_end": {"type": "string", "description": "期間終了日（YYYY-MM-DD形式）"},
                "sales_rep_keyword": {"type": "string", "description": "営業担当者名の部分一致キーワード"},
            },
        },
    },
    {
        "name": "get_import_cost_estimate",
        "description": (
            "「バッグ100個×5ドルの場合の輸入経費は？」のような仮定の質問に対して、"
            "輸送方法別の実データ集計表（伝票単位、直近1年）を返す。"
            "商品分類・数量帯（指定数量の0.5〜1.5倍）で対象を絞り込み、輸送方法ごとに"
            "件数・数量範囲・経費率の範囲（最小・推奨=中央値・最大）・推定金額を集計する。"
            "為替レートは実際の直近の仕入データから取得する（架空の為替レートは使わない）。"
            "【使い方】get_purchase_linesで少数の実例を選んで散文で外挿するのではなく、"
            "このツールが返す集計結果（records、輸送方法ごとの行）をそのまま提示すること。"
            "【表示形式】箇条書きではなく、必ずMarkdownの表形式で提示すること（見やすさの"
            "ため）。列の例: 輸送方法・伝票数・対象数量（`対象数量_平均`個、"
            "`対象数量_最小`〜`対象数量_最大`）・推奨経費率・経費率範囲（`経費率_最小`〜"
            "`経費率_最大`）・推定諸掛込原価・1個あたり原価・主な仕入先。"
            "`対象数量`（数量の情報）を省略してはいけない — 以前、数量を示さず経費率だけ"
            "答えてしまった事例があった。"
            "各行の`主な仕入先`に無い属性（仕入先の国籍・所在地等）を作り話してはいけない"
            "（実例: 実在しない仕入先を「HAEDONG TRADING Co., LTD（韓国）」のように国籍を"
            "付けて説明してしまった事例があった。取得したデータに含まれていない情報を"
            "推測で付け加えないこと）。"
            "`データ不足`がTrueの行は伝票数が3件未満のため、参考値である旨を必ず伝えること。"
            "NEWHATTANブランドの仕入先は既定で除外される（include_newhattan=Trueで含める）。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "quantity": {"type": "number", "description": "想定数量（個）"},
                "unit_price_usd": {"type": "number", "description": "想定単価（USD）"},
                "category_code": {
                    "type": "integer",
                    "description": "商品分類コード（1=帽子, 2=バッグ, 3=財布/小物, 4=サングラス/メガネ, 5=巻物, 6=アパレル, 7=ベルト, 8=履物, 9=アクセサリー）",
                },
                "include_newhattan": {"type": "boolean", "description": "NEWHATTANブランドの仕入先を含めるか（既定false）"},
            },
            "required": ["quantity", "unit_price_usd", "category_code"],
        },
    },
    {
        "name": "get_projects",
        "description": (
            "案件（PO）情報を、案件名または顧客名のキーワードで検索する。"
            "納品済みかどうかで絞り込みたい場合はdelivery_statusを使うこと"
            "（POの「顧客納品日」列は入力予定日であり、実際に納品されたかどうかとは"
            "無関係なので、納品判定に使ってはいけない。実際の納品有無はhas_sales"
            "（同じLOGS_CODEでsalesに売上実データがあるか）またはproduction_closed"
            "（生産管理『量産』シートの表示フラグ=0か）で判定済みで、各行にその"
            "2つのフィールドが含まれる）。"
            "【件数は必ず結果の`aggregate`フィールドを使うこと。`records`は件数が"
            "多い場合に先頭200件だけに切り捨てられることがあるが、`aggregate`は"
            "指定した条件（キーワード・納品状況）全体に対して正確な件数】"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "keyword": {"type": "string", "description": "案件名または顧客名の部分一致キーワード"},
                "delivery_status": {
                    "type": "string",
                    "enum": ["delivered", "undelivered"],
                    "description": "納品状況で絞り込む。delivered=納品済み、undelivered=未納品（既定は絞り込みなし）",
                },
            },
        },
    },
    {
        "name": "get_customer_master",
        "description": (
            "顧客マスタを検索する。顧客名の表記ゆれ確認・名寄せ・営業担当者の確認に使う"
            "（営業担当者名列を含む）。keywordが0件、または一致するか不確かな場合は、"
            "先にfind_similar_name（domain=\"customer\"）で類似度の高い候補を確認してから、"
            "確認できた正式名称でこちらを呼び直すこと。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "keyword": {"type": "string", "description": "顧客名の部分一致キーワード"},
            },
        },
    },
    {
        "name": "find_similar_name",
        "description": (
            "あいまい検索。入力文字列（表記ゆれ・スペルミス・曖昧な入力を含む）に"
            "最も近い実在の顧客名・社員氏名を、類似度でランキングして返す"
            "（LIKE部分一致では見つからない「たかはし」と「タカハシ」のような表記ゆれにも対応）。"
            "get_sales_lines・get_purchase_linesのsales_rep_keyword・customer_keywordで"
            "0件、または該当が不確かな場合は、まずこのツールで実在する正式名称を確認し、"
            "「『（入力された名前）』を『（確認できた正式名称）』として検索しました」と"
            "回答の中で明示してから、本来のツールを実際の名称で呼び直すこと。"
            "候補が複数返り、どれが正解か判断できない場合は、ユーザーに確認すること。"
            "架空の名前・存在しない候補で検索を続けてはいけない。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "term": {"type": "string", "description": "検索したい名前（表記ゆれ・不確かな入力でよい）"},
                "domain": {"type": "string", "enum": ["customer", "staff"], "description": "customer=顧客名、staff=社員氏名"},
            },
            "required": ["term", "domain"],
        },
    },
    {
        "name": "get_code_master",
        "description": (
            "各テーブルの数値コード（事業分類、ステータス、決済方法、諸掛区分ID等）が"
            "実際に何を意味するかを確認する、コードマスタの全件を取得する。"
            "数値コードの意味を一般常識や推測で判断してはいけない。"
            "「事業分類=1」「ステータス=2」のような数値コードが出てきたら、"
            "回答する前に必ずこのツールで実際の意味を確認すること。"
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_product_master",
        "description": (
            "商品マスタの全件を取得する。LOGS_CODE、Sample_CODE、商品名、型番、"
            "仕入先名、商品分類名（数値コードではなく既に名称に変換済み。"
            "get_code_masterで確認する必要はない）を含む。"
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_cancelled_sales",
        "description": "仮出庫（未確定出荷）の売上を取得する。正式な売上集計には含めるべきではないデータ。",
        "input_schema": {
            "type": "object",
            "properties": {
                "period_start": {"type": "string", "description": "期間開始日（YYYY-MM-DD形式）"},
                "period_end": {"type": "string", "description": "期間終了日（YYYY-MM-DD形式）"},
            },
        },
    },
    {
        "name": "get_returns",
        "description": "返品（赤伝）を取得する。除外対象ではなく、マイナス計上すべき正規取引として扱うこと。",
        "input_schema": {
            "type": "object",
            "properties": {
                "period_start": {"type": "string", "description": "期間開始日（YYYY-MM-DD形式）"},
                "period_end": {"type": "string", "description": "期間終了日（YYYY-MM-DD形式）"},
            },
        },
    },
    {
        "name": "get_budget_forecast",
        "description": (
            "予算・売上予定・費用データ（budget_forecastテーブル）を取得する"
            "（2026-07-13、14.85）。「〇〇さんの予算/売上予定を教えて」"
            "「今期の予算達成率は」のような質問に使う。1行=1案件（顧客×担当者×"
            "期×月×分類）。categoryは budget=予算、forecast=売上予定、"
            "expense=費用の3種類のみ（発注・実績データはここには無い —"
            "発注はget_projects、売上実績はget_sales_linesを使うこと）。"
            "期の形式は「LGS 10期」のようにLGS+スペース+数字+期"
            "（get_sales_linesが対象とするsalesテーブルの「LOGS10期」とは"
            "表記が異なるので注意）。expenseカテゴリの金額はマイナスで"
            "入力されている仕様のため、提示時は絶対値に変換すること。"
            "【重要】このツールが返す実際のレコードの生の列名（丸数字を含む"
            "費用の内訳列等）をそのまま使い、列名を推測で書き換えないこと。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["budget", "forecast", "expense"],
                    "description": "budget=予算(01_予算)、forecast=売上予定(02_予定)、expense=費用(05_費用)",
                },
                "period": {"type": "string", "description": "期（例: \"LGS 10期\"）。year/monthの代わりに指定してもよい。"},
                "year": {"type": "string", "description": "年（例: \"2026\"）。text型のため文字列で指定。"},
                "month": {"type": "string", "description": "月（例: \"6\"または\"06月\"。自動で\"06月\"形式に正規化される）"},
                "customer_keyword": {"type": "string", "description": "顧客名の部分一致キーワード"},
                "sales_rep_keyword": {"type": "string", "description": "社員名（担当者）の部分一致キーワード"},
            },
        },
    },
    {
        "name": "get_purchase_surcharges",
        "description": (
            "仕入の諸掛（輸入経費）内訳を、仕入明細（purchases）とJOINして"
            "取得する（2026-07-13、14.85、区分ラベルは14.86で確定）。"
            "「関税はいくら」「諸掛の内訳を教えて」のような質問に使う。"
            "各行の「諸掛区分名」（関税・国内手数料（税抜）・国内手数料"
            "消費税額・運賃・輸入消費税（地方）・輸入消費税（内国）・"
            "燃料サーチャージ・通関料他の8種類）は既にラベル変換済みなので、"
            "get_code_masterで確認する必要はない。消費税に該当するのは"
            "国内手数料消費税額・輸入消費税（地方）・輸入消費税（内国）の"
            "3区分。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "period_start": {"type": "string", "description": "期間開始日（YYYY-MM-DD形式、仕入の伝票日基準）"},
                "period_end": {"type": "string", "description": "期間終了日（YYYY-MM-DD形式、仕入の伝票日基準）"},
                "po_number": {"type": "string", "description": "PO番号で絞り込む"},
                "logs_code": {"type": "string", "description": "LOGS_CODEで絞り込む"},
            },
        },
    },
    {
        "name": "get_customer_contacts",
        "description": (
            "顧客担当者の連絡先（customer_contactsテーブル: 担当者氏名・"
            "メールアドレス・電話番号等）を取得する（2026-07-13、14.85）。"
            "「〇〇社の担当者の連絡先は」のような質問に使う。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_keyword": {"type": "string", "description": "顧客名の部分一致キーワード"},
            },
        },
    },
    {
        "name": "get_sample_staff_names",
        "description": (
            "サンプル依頼対応の生産担当（回答者）の実在する名前一覧を取得する。"
            "get_ongoing_samples_by_staffを呼ぶ前に、まずこれで名前が実在するか確認すること。"
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_ongoing_samples_by_staff",
        "description": (
            "指定した生産担当が対応中（未通知）のサンプル依頼を、仕入先・商品名とともに取得する。"
            "到着予定日（ETD/ETA/納品日）などのスケジュール情報はこのデータに含まれない"
            "（生産管理チームがその項目を運用していないため）。到着日を聞かれても、"
            "このツールでは分からないと正直に答えること。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "staff_name": {"type": "string", "description": "生産担当の氏名（get_sample_staff_namesで確認した実在の名前）"},
            },
            "required": ["staff_name"],
        },
    },
    {
        "name": "get_production_mass_status",
        "description": "指定したPO番号の量産の生産進捗（工場・PP/TOP日程・ETD/ETA等）を取得する。",
        "input_schema": {
            "type": "object",
            "properties": {
                "po_number": {"type": "string", "description": "PO番号（例: 914-20260626_1）"},
            },
            "required": ["po_number"],
        },
    },
    {
        "name": "search_gmail",
        "description": (
            "ログインユーザー自身のGmailを検索する。Gmail検索構文"
            "（from:, to:, subject:, after:YYYY/MM/DD, is:unread 等）が使える。"
            "件名・差出人・日時・スニペットのみを返す（本文全体はget_gmail_messageで取得すること）。"
            "'unavailable' が返ってきた場合はGmail未連携ということなので、"
            "設定画面からのGmail連携を案内すること。架空のメール内容を作ってはいけない。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Gmail検索クエリ"},
                "max_results": {"type": "integer", "description": "取得件数（既定10、最大25）"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_gmail_message",
        "description": "search_gmailで見つけたmessage_idを指定して、そのメールの本文全体を取得する。",
        "input_schema": {
            "type": "object",
            "properties": {
                "message_id": {"type": "string", "description": "search_gmailの結果に含まれるmessage_id"},
            },
            "required": ["message_id"],
        },
    },
    {
        "name": "search_slack",
        "description": (
            "ログインユーザー自身が参加しているSlackのチャンネル・DMからメッセージを検索する。"
            "Slack検索構文が使える: from:@ユーザー名, in:#チャンネル名, "
            "before:YYYY-MM-DD, after:YYYY-MM-DD, on:YYYY-MM-DD（日付は必ずハイフン区切り。"
            "Gmailのafter:YYYY/MM/DDとは書式が異なるので混同しないこと）。"
            "'unavailable' が返ってきた場合はSlack未連携ということなので、"
            "設定画面からのSlack連携を案内すること。架空のメッセージ内容を作ってはいけない。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Slack検索クエリ"},
                "max_results": {"type": "integer", "description": "取得件数（既定10、最大25）"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_my_projects",
        "description": (
            "ログインユーザー自身が「営業担当者」または「営業事務担当者」になっている"
            "案件（PO）を取得する。「自分の案件」「私が担当している案件」「自分の残タスク」"
            "のような質問に使う。ログイン中のメールアドレスが社員マスタの氏名と一致しない"
            "場合は取得できない（'unavailable'）ので、その場合は正直に担当者名を特定できな"
            "かった旨を伝えること。架空の案件を作ってはいけない。"
            "status_badgesは複数付くことがある（例:「売上未確定」と「原価未確定」は同時に"
            "成立しうる）。「完了」は売上・仕入とも入力済みの意味で、「納品完了（生産管理）」"
            "は生産管理側の別軸の判定（売上・仕入の入力状況とは無関係）。"
            "「PO発行済み」「PO未発行」は常にどちらか一方が付く。"
            "delivery_month_bucketは納品予定月（this_month=今月、next_month=来月、"
            "month_after_next_or_later=再来月以降）で、既に納期を過ぎている場合はnull。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "取得件数（既定20）"},
            },
        },
    },
    {
        "name": "get_my_products",
        "description": (
            "ログインユーザー自身に直接・間接的に関連する商品（LOGS_CODE）を取得する。"
            "関連の判定: 商品マスタの作成者本人（直接）、PO/売上/仕入の担当者・"
            "仕入先の生産管理担当者・サンプル対応の回答者/依頼元のいずれかが本人"
            "（間接）。「自分が関わった商品」「自分の商品」のような質問に使う。"
            "ログイン中のメールアドレスが社員マスタの氏名と一致しない場合は取得"
            "できない（'unavailable'）。架空の商品を作ってはいけない。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "取得件数（既定20）"},
            },
        },
    },
    {
        "name": "report_capability_gap",
        "description": (
            "現在のツール群では正確に答えられない「機能そのものの不足」に"
            "気づいた場合に呼び出す（2026-07-13、14.82）。「データが存在しない/"
            "見つからない」（＝そのケースはget_XXXツールが返すstatus:"
            "\"unavailable\"で十分）とは異なり、こちらは「絞り込み・集計の"
            "手段自体がツールに用意されていない」ケース専用（例:"
            "「今月のOEMの売上は？」で、事業分類による絞り込み手段が"
            "get_sales_linesにもget_sales_by_categoryにも無かった実例）。"
            "呼び出しても回答自体は変わらない — 正直に「現状のツールでは"
            "できません」と説明した上で、この不足を記録するために呼ぶ。"
            "本当に機能不足の場合のみ呼ぶこと（データが単に無い/0件だった"
            "だけの場合には呼ばない）。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "何が正確に答えられなかったか（質問の内容と、どこで詰まったか）",
                },
                "requested_capability": {
                    "type": "string",
                    "description": "あれば解決できたであろう機能（例: 「get_sales_by_categoryのgroup_byにbusiness_typeを追加」）",
                },
            },
            "required": ["description"],
        },
    },
]


_MAX_RECORDS_FOR_CLAUDE = 200


def _cap_records(result: dict[str, Any]) -> dict[str, Any]:
    """ツール結果のrecordsが多すぎる場合、Claudeへ渡す前に件数を制限する。

    2026-07-06に実際のブラウザ操作で発見: "今月のOEM事業の粗利を教えて"
    のような、期間指定なしでも呼び出せてしまう質問に対し、Claudeが
    get_sales_lines を period_start/period_end なしで呼んだ結果、
    sales テーブル全件（約20万件）がそのままツール結果としてClaudeに
    返され、Anthropic APIの1リクエストあたりの上限（20万トークン）を
    超えてエラーになった（実際のエラー: "prompt is too long: 228537
    tokens > 200000 maximum"）。

    evidence_interpreter.py の _DISPLAY_LIMIT（表示は代表サンプルに
    絞り、全件はrecord_countで件数のみ伝える）と同じ考え方を、Claudeに
    渡すツール結果にも適用する。Claude側に「件数が多いため絞り込んで
    ほしい」ことを伝え、次のターンで期間や顧客名を指定した再検索を
    促せるようにする。
    """
    records = result.get("records")
    if not isinstance(records, list) or len(records) <= _MAX_RECORDS_FOR_CLAUDE:
        return result

    total = len(records)
    capped = dict(result)
    capped["records"] = records[:_MAX_RECORDS_FOR_CLAUDE]
    capped["truncated"] = True
    capped["total_record_count"] = total
    original_summary = result.get("summary", "")
    capped["summary"] = (
        f"{original_summary}（件数が多いため先頭{_MAX_RECORDS_FOR_CLAUDE}件のみ返却。"
        f"全{total}件。期間や顧客名などで絞り込んで再度呼び出してください）"
    )
    return capped


def execute_tool(tool_name: str, tool_input: dict[str, Any], user_email: str | None = None) -> str:
    """ツール呼び出しを実行し、Claudeへ返すJSON文字列を返す。

    どんな失敗（未知のツール名、DB接続エラー等）でも例外を投げず、
    Claudeが読める形のエラー情報を返す — そうすることでClaude自身が
    「このデータは取得できなかった」と認識して、次の判断（別のツールを
    試す、正直に分からないと答える等）ができるようにするため。

    user_email: 今チャットしている本人のメールアドレス（ログインセッション
    由来）。Gmail/Slackのような「本人自身のデータ」を扱うツールにのみ
    必要で、それ以外の全社共通データ系ツールでは使わない。
    """
    from services.data_providers import _PROVIDERS

    try:
        if tool_name == "get_sales_lines":
            result = _PROVIDERS["logsys"].fetch("sales_lines", tool_input)
        elif tool_name == "get_sales_by_category":
            result = _PROVIDERS["logsys"].fetch("sales_by_category", tool_input)
        elif tool_name == "get_purchase_lines":
            result = _PROVIDERS["logsys"].fetch("purchase_lines", tool_input)
        elif tool_name == "get_import_cost_estimate":
            result = _PROVIDERS["logsys"].fetch("import_cost_estimate", tool_input)
        elif tool_name == "find_similar_name":
            result = _PROVIDERS["logsys"].fetch("find_similar_name", tool_input)
        elif tool_name == "get_projects":
            result = _PROVIDERS["logsys"].fetch("projects", tool_input)
        elif tool_name == "get_customer_master":
            result = _PROVIDERS["logsys"].fetch("customer_master", tool_input)
        elif tool_name == "get_product_master":
            result = _PROVIDERS["logsys"].fetch("product_master", tool_input)
        elif tool_name == "get_code_master":
            result = _PROVIDERS["logsys"].fetch("code_master", tool_input)
        elif tool_name == "get_cancelled_sales":
            result = _PROVIDERS["logsys"].fetch("cancelled_sales", tool_input)
        elif tool_name == "get_returns":
            result = _PROVIDERS["logsys"].fetch("returns", tool_input)
        elif tool_name == "get_budget_forecast":
            result = _PROVIDERS["logsys"].fetch("budget_forecast", tool_input)
        elif tool_name == "get_purchase_surcharges":
            result = _PROVIDERS["logsys"].fetch("purchase_surcharges", tool_input)
        elif tool_name == "get_customer_contacts":
            result = _PROVIDERS["logsys"].fetch("customer_contacts", tool_input)
        elif tool_name == "get_sample_staff_names":
            result = _PROVIDERS["production"].fetch("sample_staff_master", tool_input)
        elif tool_name == "get_ongoing_samples_by_staff":
            result = _PROVIDERS["production"].fetch("ongoing_samples_by_staff", tool_input)
        elif tool_name == "get_production_mass_status":
            from services.production_data import get_production_mass_status
            rows = get_production_mass_status(tool_input.get("po_number", ""))
            result = {
                "status": "ok" if rows else "unavailable",
                "records": rows,
                "summary": f"{len(rows)}件取得",
            }
        elif tool_name == "search_gmail":
            if not user_email:
                result = {"status": "unavailable", "summary": "ユーザーが特定できないため、Gmail検索はできません。", "records": []}
            else:
                from services import gmail_service
                result = gmail_service.search_messages(
                    user_email, tool_input.get("query", ""), tool_input.get("max_results", 10)
                )
        elif tool_name == "get_gmail_message":
            if not user_email:
                result = {"status": "unavailable", "summary": "ユーザーが特定できないため、メール取得はできません。", "records": []}
            else:
                from services import gmail_service
                result = gmail_service.get_message(user_email, tool_input.get("message_id", ""))
        elif tool_name == "search_slack":
            if not user_email:
                result = {"status": "unavailable", "summary": "ユーザーが特定できないため、Slack検索はできません。", "records": []}
            else:
                from services import slack_service
                result = slack_service.search_messages(
                    user_email, tool_input.get("query", ""), tool_input.get("max_results", 10)
                )
        elif tool_name == "get_my_projects":
            if not user_email:
                result = {"status": "unavailable", "summary": "ユーザーが特定できないため取得できません。", "records": []}
            else:
                from services.auth_service import get_staff_name_by_email
                from services.project_service import ProjectService

                owner_name = get_staff_name_by_email(user_email)
                if not owner_name:
                    result = {
                        "status": "unavailable",
                        "summary": "ログイン中のメールアドレスが社員マスタの氏名と一致しないため、担当案件を特定できません。",
                        "records": [],
                    }
                else:
                    service = ProjectService()
                    limit = tool_input.get("limit", 20)
                    project_ids = service._query_projects_from_db(limit=limit, owner_name=owner_name)
                    ids = [p["id"] for p in project_ids if p.get("id")]
                    records = []
                    for agg in service.build_project_aggregates_bulk(ids):
                        # 2026-07-09（14.58修正）: 以前は単一のstate（14.39で
                        # status_badgesに置き換える前の古い概念）を返して
                        # いたが、実際の判定ロジック自体は最新のまま
                        # （このツールはbuild_project_aggregates_bulk()を
                        # そのまま呼んでいるため）で、取り出すフィールドだけ
                        # 古くなっていた。status_badges（複数可、完了/売上
                        # 未確定/原価未確定/納品完了(生産管理)/PO発行済み・
                        # 未発行）とdelivery_month_bucket（納品予定月）に
                        # 更新した。
                        records.append({
                            "project_id": agg.project_id,
                            "po_number": agg.po_number,
                            "project_name": agg.data.project_name,
                            "customer": agg.data.customer_name,
                            "status_badges": agg.status_badges,
                            "delivery_month_bucket": agg.delivery_month_bucket,
                            "actions_count": len(agg.actions),
                        })
                    result = {
                        "status": "ok" if records else "unavailable",
                        "summary": f"{owner_name}さんが担当する案件を{len(records)}件取得しました。" if records else f"{owner_name}さんが担当する案件は見つかりませんでした。",
                        "records": records,
                    }
        elif tool_name == "get_my_products":
            if not user_email:
                result = {"status": "unavailable", "summary": "ユーザーが特定できないため取得できません。", "records": []}
            else:
                from services.auth_service import get_staff_name_by_email
                from services.product_service import _format_logs_code, get_products_master_batch, get_related_product_ids, sample_code_sort_key

                owner_name = get_staff_name_by_email(user_email)
                if not owner_name:
                    result = {
                        "status": "unavailable",
                        "summary": "ログイン中のメールアドレスが社員マスタの氏名と一致しないため、関連商品を特定できません。",
                        "records": [],
                    }
                else:
                    limit = tool_input.get("limit", 20)
                    product_ids = get_related_product_ids(owner_name, limit=limit)
                    master_map = get_products_master_batch(product_ids)
                    records = []
                    for pid in product_ids:
                        m = master_map.get(pid)
                        if m:
                            records.append({
                                "product_id": pid,
                                "logs_code": _format_logs_code(m.get("LOGS_CODE")),
                                "product_name": m.get("商品名"),
                                "model_no": m.get("型番"),
                                "supplier_name": m.get("仕入先名"),
                                "sample_code": m.get("Sample_CODE"),
                            })
                    records.sort(key=lambda r: sample_code_sort_key(r["sample_code"]), reverse=True)
                    result = {
                        "status": "ok" if records else "unavailable",
                        "summary": f"{owner_name}さんに関連する商品を{len(records)}件取得しました。" if records else f"{owner_name}さんに関連する商品は見つかりませんでした。",
                        "records": records,
                    }
        elif tool_name == "report_capability_gap":
            # データ取得ではなく、chat_agent._record_tool_gaps_as_learningが
            # Learning候補として拾うための「機能不足の申告」専用ツール
            # （14.82）。Providerを経由せず、ここで直接応答を作る。
            result = {
                "status": "capability_gap_reported",
                "summary": "機能不足として記録しました。",
                "description": tool_input.get("description", ""),
                "requested_capability": tool_input.get("requested_capability", ""),
            }
        else:
            result = {"status": "unavailable", "summary": f"未知のツール: {tool_name}", "records": []}
    except Exception as e:
        # 2026-07-10（14.67修正）: data_providers.py側と同じ理由で、
        # ここも例外を無言で握りつぶしていた。get_my_projects等の直接
        # 実装分岐（LogsysProvider.fetchを経由しない）で起きた例外は
        # ここでしか捕まらないため、同様にログへ出力する。
        import traceback
        print(f"[ERROR] execute_tool({tool_name!r}, {tool_input!r}) failed: {e}")
        traceback.print_exc()
        result = {"status": "error", "summary": f"データ取得中にエラーが発生しました: {e}", "records": []}

    result = _cap_records(result)
    return json.dumps(result, ensure_ascii=False, default=str)