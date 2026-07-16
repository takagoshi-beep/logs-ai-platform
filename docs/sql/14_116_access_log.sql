-- 14.116 社内利用状況(ページ閲覧・相談内容)の記録
-- Supabaseのダッシュボード → SQL Editor で、このSQLをそのまま実行してください。
-- (既存の app_traces / app_api_usage 等と同じ、record(JSONB) 1カラムのシンプルな構成)

CREATE TABLE IF NOT EXISTS app_access_log (
    id BIGSERIAL PRIMARY KEY,
    record JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
