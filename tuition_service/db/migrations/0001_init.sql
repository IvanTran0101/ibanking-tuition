-- Tuition Service initial schema (PostgreSQL)
-- Creates students and tuitions tables based on your diagram

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- students: master data of student identities
CREATE TABLE IF NOT EXISTS students (
    student_id text  PRIMARY KEY,
    full_name  text NOT NULL
);

-- tuitions: per-student tuition per term
CREATE TABLE IF NOT EXISTS tuitions (
    tuition_id uuid        PRIMARY KEY,
    student_id text         NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    term_no    smallint    NOT NULL,
    amount_due numeric     NOT NULL,
    status     text        NOT NULL DEFAULT 'UNLOCKED', -- UNLOCKED | LOCKED
    expires_at timestamptz NOT NULL,
    payment_id text        NOT NULL UNIQUE
);

-- A student can have at most one tuition per term
CREATE UNIQUE INDEX IF NOT EXISTS uq_tuitions_student_term ON tuitions(student_id, term_no);

CREATE INDEX IF NOT EXISTS idx_tuitions_status ON tuitions(status);

