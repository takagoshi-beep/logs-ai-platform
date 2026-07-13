-- 14.105 Claude APIの利用量・概算コストの記録
-- Supabaseのダッシュボード → SQL Editor で、このSQLをそのまま実行してください。
-- (既存の app_traces 等と同じ、record(JSONB) 1カラムのシンプルな構成)

CREATE TABLE IF NOT EXISTS app_api_usage (
    id BIGSERIAL PRIMARY KEY,
    record JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
