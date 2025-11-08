-- Payment Service initial schema (PostgreSQL)
-- Creates payments table based on your diagram

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS payments (
    payment_id uuid        PRIMARY KEY,
    tuition_id uuid        NOT NULL,
    user_id    uuid        NOT NULL,
    amount     numeric     NOT NULL CHECK (amount > 0),
    expires_at timestamptz NOT NULL,
    complete_at timestamptz NULL,
    status     text        NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_payments_user ON payments(user_id);
CREATE INDEX IF NOT EXISTS idx_payments_tuition ON payments(tuition_id);
CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);
