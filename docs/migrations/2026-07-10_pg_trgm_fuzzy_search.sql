-- 2026-07-10（14.65、Noritsuguの指定）: あいまい検索（表記ゆれ・
-- スペルミスへの対応）用にpg_trgm拡張を有効化する。
--
-- これまでの検索は全て LIKE '%キーワード%'（部分一致）のみで、
-- 「たかはし」と「タカハシ」のような表記ゆれや、スペルミス・
-- 曖昧な入力には対応できなかった。pg_trgmのsimilarity()関数を使うと、
-- 「入力文字列に最も近い実データ」を類似度スコア付きで返せるように
-- なる（backend/services/data_providers.py の find_similar_name
-- ツールで使用）。

CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- トライグラム類似度検索を高速化するGINインデックス。
-- 対象: 顧客名（顧客マスタでの名寄せ用）、社員氏名（担当者名検索用）。
CREATE INDEX IF NOT EXISTS idx_customers_name_trgm
    ON customers USING gin ("顧客名称" gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_staff_name_trgm
    ON staff USING gin ("社員氏名" gin_trgm_ops);
