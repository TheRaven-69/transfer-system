-- Remove idempotency columns from transactions table (Redis-only idempotency).
-- PostgreSQL / SQLite (3.35+) compatible syntax.
ALTER TABLE transactions DROP COLUMN IF EXISTS idempotency_key;
ALTER TABLE transactions DROP COLUMN IF EXISTS request_hash;
