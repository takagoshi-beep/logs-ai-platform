-- salesを軸に、商品分類・顧客分類・担当者のメール/Slack・仕入先の生産管理
-- 担当者を結合したビュー (docs/architecture.md 14.32)。
-- 既存の v_customer_master / v_product_master と同じ「分類コードは
-- ビュー側でCASE式により名称に変換する」方針を踏襲している。
--
-- 顧客分類の対応表は既存の v_customer_master ビュー定義
-- (reference/02_database/sync/sync.py) と完全に一致させている。
-- 事業規模・取引傾向分類は、既存コードベースのどこにも対応表が
-- 見つからなかったため、コード値をそのまま渡している（架空の対応表を
-- 作らない）。
--
-- staffテーブルの主キー列名は実際には "ID（編集禁止）"（全角括弧付きの
-- まま）。reference/02_database/sync/sync.pyのclean_column_nameでは
-- 括弧を除去する想定だったが、staffテーブルは別の同期経路のため
-- そのクレンジングが適用されていなかった（2026-07-09、実際に
-- information_schema.columnsで確認して判明）。
--
-- テーブルをまたぐID列はbigint/textが揺れているため（実際に
-- staff."ID（編集禁止）"がtextでsales."営業担当者ID"がbigintという
-- 不一致が発生した）、結合キーは全て::textに明示キャストしている。
--
-- Supabase SQL Editor で1回実行してください。

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
LEFT JOIN staff acc ON s."経理担当者ID"::text = acc."ID（編集禁止）"::text;
