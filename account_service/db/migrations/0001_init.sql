-- Account Service initial schema (PostgreSQL)
-- Recreated migration: accounts and holds tables

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- accounts: user profiles + current balance
CREATE TABLE IF NOT EXISTS accounts (
    user_id        uuid        PRIMARY KEY,
    password_hash  text        NOT NULL,
    balance        numeric     NOT NULL,
    username       text        NOT NULL UNIQUE,
    full_name      text        NOT NULL,
    phone_number   text        NOT NULL,
    email          text        NOT NULL UNIQUE
);

-- holds: amount reservations for payments
CREATE TABLE IF NOT EXISTS holds (
    hold_id     uuid        PRIMARY KEY,
    user_id     uuid        NOT NULL REFERENCES accounts(user_id) ON DELETE CASCADE,
    amount      numeric     NOT NULL CHECK (amount > 0),
    expires_at  timestamptz NOT NULL,
    status      text        NOT NULL, -- HELD | RELEASED | CAPTURED
    payment_id  text        NOT NULL UNIQUE
);

-- Helpful indexes
CREATE INDEX IF NOT EXISTS idx_accounts_user_balance ON accounts(user_id, balance);
CREATE INDEX IF NOT EXISTS idx_holds_user_status ON holds(user_id, status);

