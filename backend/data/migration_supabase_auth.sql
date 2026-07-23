-- Migration: Real Supabase Auth + server-side authorization
-- Run this in the Supabase SQL Editor
--
-- Purpose: replace the hand-rolled `public.users` (SHA-256 password_hash) +
-- `public.sessions` (opaque token) auth system with real Supabase Auth
-- (auth.users, GoTrue-managed sessions). `role` and `assigned_district` move
-- to auth.users.app_metadata (service-role-only writable, embedded in every
-- JWT the backend verifies via backend/services/auth_deps.py). Everything
-- else that used to live on `users` moves to a new `public.profiles` table
-- FK'd to auth.users.id.
--
-- DESTRUCTIVE BY DESIGN: the 10 existing rows in `users` (and everything
-- that cascades from them — land_plots, scan_results indirectly via
-- land_plots, carbon_credits, transactions, audit_log, industrial_profiles,
-- notifications, registration_requests, verifications) are test/seed data
-- from before this app had any working auth. There is nothing here worth
-- preserving independently of the accounts it belongs to, and none of those
-- accounts' passwords are recoverable (SHA-256, no reset flow ever existed).
-- Every user must re-signup through the new Supabase Auth flow after this
-- migration runs.

-- ── 1. Wipe existing auth data + everything that depends on it ──────────
TRUNCATE TABLE sessions, users CASCADE;

-- ── 2. Drop the hand-rolled session table — GoTrue owns sessions now ─────
DROP TABLE IF EXISTS sessions CASCADE;

-- ── 3. Repurpose `users` as `public.profiles`, FK'd to auth.users ───────
-- Renaming in place (rather than drop+recreate) preserves every incoming FK
-- constraint automatically (land_plots.owner_id, carbon_credits.owner_id,
-- transactions.buyer_id/seller_id, audit_log.performed_by,
-- industrial_profiles.user_id, notifications.user_id,
-- registration_requests.processed_by, verifications.verifier_id) — they now
-- point at `profiles` with zero further changes needed.
ALTER TABLE users RENAME TO profiles;

ALTER TABLE profiles DROP CONSTRAINT IF EXISTS users_role_check;
ALTER TABLE profiles DROP COLUMN IF EXISTS password_hash;
ALTER TABLE profiles DROP COLUMN IF EXISTS role;               -- now auth.users.app_metadata only
ALTER TABLE profiles DROP COLUMN IF EXISTS assigned_district;  -- now auth.users.app_metadata only

-- id is no longer self-generated — a profile row must always be inserted
-- explicitly by the backend (routers/auth.py's /set-role) with
-- id = the corresponding auth.users.id.
ALTER TABLE profiles ALTER COLUMN id DROP DEFAULT;
ALTER TABLE profiles
  ADD CONSTRAINT profiles_id_fkey FOREIGN KEY (id) REFERENCES auth.users(id) ON DELETE CASCADE;

COMMENT ON TABLE profiles IS
'Non-authorization-critical profile fields for a Supabase Auth user (id == auth.users.id). role and assigned_district live in auth.users.app_metadata instead — service-role-only writable, embedded in every JWT — so authorization never depends on a row in this table existing or being in sync.';

-- ── 4. Indexes ────────────────────────────────────────────────────────────
DROP INDEX IF EXISTS idx_users_email;
DROP INDEX IF EXISTS idx_sessions_token;
DROP INDEX IF EXISTS idx_sessions_user_id;
DROP INDEX IF EXISTS idx_users_assigned_district;  -- column dropped above
CREATE INDEX IF NOT EXISTS idx_profiles_email ON profiles(email);

-- ── 5. registration_requests RLS: drop and disable ───────────────────────
-- These policies referenced `users.role` (column just dropped) and
-- `auth.uid()` — but auth.uid() has never actually matched anything,
-- because nothing before this migration created a real Supabase Auth
-- session, so these policies have been dead code since the day they were
-- written. Dropping rather than rewriting: every router uses
-- get_admin_client() (service-role key), which bypasses RLS entirely
-- regardless of what policies exist — real authorization now lives
-- exclusively in the FastAPI dependency layer (backend/services/auth_deps.py
-- + each router's Depends()), not in RLS. If any future code path ever
-- queries Supabase with a non-admin (anon-key) client directly, note that it
-- would currently have ZERO RLS protection on any table in this schema —
-- intentional for now, but worth knowing before adding such a code path.
DROP POLICY IF EXISTS "Admins can view all registration requests" ON registration_requests;
DROP POLICY IF EXISTS "Admins can update registration requests" ON registration_requests;
DROP POLICY IF EXISTS "Landowners can create registration requests" ON registration_requests;
DROP POLICY IF EXISTS "Users can view their own registration requests" ON registration_requests;
ALTER TABLE registration_requests DISABLE ROW LEVEL SECURITY;
