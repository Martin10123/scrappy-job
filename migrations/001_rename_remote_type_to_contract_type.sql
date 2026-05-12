-- Migration: rename remote_type to contract_type and add the new location fields.
-- Run this once against an existing PostgreSQL database.

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'jobs'
          AND column_name = 'remote_type'
    ) AND NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'jobs'
          AND column_name = 'contract_type'
    ) THEN
        ALTER TABLE jobs RENAME COLUMN remote_type TO contract_type;
    END IF;
END $$;

ALTER TABLE jobs
    ADD COLUMN IF NOT EXISTS location_text VARCHAR;

ALTER TABLE jobs
    ADD COLUMN IF NOT EXISTS work_mode VARCHAR;

ALTER TABLE jobs
    ADD COLUMN IF NOT EXISTS english_required BOOLEAN;
