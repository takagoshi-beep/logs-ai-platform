-- 案件の担当者絞り込み（scope=mine, docs/architecture.md 14.28）で
-- 使用するWHERE句を高速化するためのインデックス。
-- 追加のみで既存データ・既存クエリへの影響はありません。
-- Supabase SQL Editor で1回実行してください。

CREATE INDEX IF NOT EXISTS idx_purchase_orders_sales_rep
    ON purchase_orders ("営業担当者名");

CREATE INDEX IF NOT EXISTS idx_purchase_orders_sales_admin
    ON purchase_orders ("営業事務担当者名");
