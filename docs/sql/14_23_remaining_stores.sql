-- 14.23 Web化準備 (2/2): 残り6モジュール分のテーブル作成
-- Supabaseのダッシュボード → SQL Editor で、このSQLをそのまま実行してください。
-- (14_23_document_formats.sql を既に実行済みの前提です)

CREATE TABLE IF NOT EXISTS app_governance_approvals (
    id BIGSERIAL PRIMARY KEY,
    record JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS app_governance_audit (
    id BIGSERIAL PRIMARY KEY,
    record JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS app_capability_executions (
    id BIGSERIAL PRIMARY KEY,
    record JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS app_conversations (
    id BIGSERIAL PRIMARY KEY,
    record JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS app_traces (
    id BIGSERIAL PRIMARY KEY,
    record JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS app_events (
    id BIGSERIAL PRIMARY KEY,
    record JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Learning Domain（5テーブル）
CREATE TABLE IF NOT EXISTS app_learning_candidates (
    id BIGSERIAL PRIMARY KEY,
    record JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS app_learning_operational_memory (
    id BIGSERIAL PRIMARY KEY,
    record JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS app_learning_approval_queue (
    id BIGSERIAL PRIMARY KEY,
    record JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS app_learning_policy_memory (
    id BIGSERIAL PRIMARY KEY,
    record JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS app_learning_activity_feed (
    id BIGSERIAL PRIMARY KEY,
    record JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
