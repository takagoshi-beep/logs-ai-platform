-- 14.23 Web化準備: 帳票フォーマット定義の保存先をSupabaseに移行
-- Supabaseのダッシュボード → SQL Editor で、このSQLをそのまま実行してください。

CREATE TABLE IF NOT EXISTS app_document_formats (
    id BIGSERIAL PRIMARY KEY,
    record JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
