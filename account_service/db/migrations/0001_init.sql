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

CREATE INDEX IF NOT EXISTS idx_accounts_user_balance ON accounts(user_id, balance);
