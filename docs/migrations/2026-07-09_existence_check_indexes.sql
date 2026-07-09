-- 案件一覧・今日のタスクの高速化 (docs/architecture.md 14.37)。
-- project_service.py の _attach_existence_data が sales/purchases/
-- production_mass に対して WHERE "LOGS_CODE" = ANY(%s) / WHERE "POnum"
-- = ANY(%s) で問い合わせるようになった（1行ごとの相関サブクエリから、
-- まとめて引く方式に変更）。バッチ化しても、これらの列にインデックスが
-- 無いとテーブルスキャンになるため、インデックスを追加しておく。
--
-- Supabase SQL Editor で1回実行してください。

CREATE INDEX IF NOT EXISTS idx_sales_logs_code ON sales ("LOGS_CODE");
CREATE INDEX IF NOT EXISTS idx_purchases_logs_code ON purchases ("LOGS_CODE");
CREATE INDEX IF NOT EXISTS idx_production_mass_ponum ON production_mass ("POnum");
