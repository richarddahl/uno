-- Postgres schema for Uno durable saga state store

CREATE TABLE IF NOT EXISTS uno_sagas (
    saga_id TEXT PRIMARY KEY,
    saga_type TEXT NOT NULL,
    status TEXT NOT NULL,
    data JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_uno_sagas_status ON uno_sagas (status);
