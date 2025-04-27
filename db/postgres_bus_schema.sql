-- Postgres schema for Uno EventBus/CommandBus durability and NOTIFY/LISTEN integration

CREATE TABLE IF NOT EXISTS uno_events (
    id SERIAL PRIMARY KEY,
    payload JSONB NOT NULL,
    processed BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS uno_commands (
    id SERIAL PRIMARY KEY,
    payload JSONB NOT NULL,
    processed BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for fast polling of unprocessed events/commands
CREATE INDEX IF NOT EXISTS idx_uno_events_processed ON uno_events (processed, created_at);
CREATE INDEX IF NOT EXISTS idx_uno_commands_processed ON uno_commands (processed, created_at);

-- Grant privileges as needed for your app user
-- GRANT INSERT, SELECT, UPDATE ON uno_events, uno_commands TO your_app_user;
