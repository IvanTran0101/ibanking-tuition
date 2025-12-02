-- Tuition Service initial schema (PostgreSQL)
-- Stores per-student tuition per term (students embedded inside tuitions table)

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS tuitions (
    tuition_id uuid        PRIMARY KEY,
    student_id text        NOT NULL,
    student_full_name text NOT NULL,
    term_no    smallint    NOT NULL,
    amount_due numeric     NOT NULL,
    status     text        NOT NULL DEFAULT 'UNLOCKED', -- UNLOCKED | LOCKED | PAID
    expires_at timestamptz,
    payment_id text        UNIQUE
);

-- A student can have at most one tuition per term
CREATE UNIQUE INDEX IF NOT EXISTS uq_tuitions_student_term ON tuitions(student_id, term_no);

CREATE INDEX IF NOT EXISTS idx_tuitions_status ON tuitions(status);
