-- Migration: rename role 'verifier_analyst' -> 'analyst'
-- Run this in Supabase SQL Editor.
--
-- The capstone proposal's "Verifier-Analyst" role is now referred to
-- strictly as "analyst" across the app (frontend labels, backend
-- VALID_ROLES/require_role() calls). The authoritative role value lives in
-- auth.users.raw_app_meta_data (Supabase Auth), set by
-- backend/routers/auth.py's /set-role.
--
-- NOTE: an earlier version of this migration also updated a legacy
-- public.users table (pre-Supabase-Auth). That table does not exist in
-- this project (confirmed via a failed `relation "users" does not exist`
-- run) — the app fully migrated to Supabase Auth, so there's nothing there
-- to update. Removed to keep this script runnable as-is.

-- Live Supabase Auth accounts: flip any existing app_metadata.role from
-- 'verifier_analyst' to 'analyst' so already-created accounts keep
-- working against the renamed require_role("analyst", ...) checks.
UPDATE auth.users
SET raw_app_meta_data = jsonb_set(raw_app_meta_data, '{role}', '"analyst"')
WHERE raw_app_meta_data->>'role' = 'verifier_analyst';
