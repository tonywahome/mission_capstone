-- Migration: Capstone Re-scope (Bugesera & Rulindo AGB research prototype)
-- Run this in the Supabase SQL Editor
-- Date: June 26, 2026
--
-- Purpose: additively patch the existing marketplace-era schema (schema.sql
-- + migration_add_auth.sql + migration_approval_workflow.sql) to support
-- the revised ALU capstone research proposal's re-scoped roles, districts,
-- and ethical safeguards (Section 3.6), WITHOUT dropping or renaming any
-- existing column, table, or constraint value. Every change below is
-- additive: widened CHECK constraints keep every legacy value, new columns
-- are nullable (or default to the least-permissive value), and new tables
-- use IF NOT EXISTS. This lets already-running marketplace-era data — and
-- the still-present backend/legacy/ + frontend/legacy/ code, kept for the
-- separate TerraFoma LTD commercial product, not this academic prototype —
-- continue to validate against the schema unchanged.
--
-- This file has NOT been executed against any database by the assistant
-- that wrote it. Review and run it yourself in the Supabase SQL Editor.
-- Apply it AFTER schema.sql, migration_add_auth.sql, and
-- migration_approval_workflow.sql.
--
-- NOTE on experiment tracking (Section 3.7): per-run provenance records
-- (dataset version, feature stack, hyperparameters, random seed, spatial-
-- block split IDs, evaluation metrics, output artifact path) are logged as
-- flat JSON/CSV files under backend/ml/experiment_runs/ by
-- backend/services/experiment_tracker.py, NOT in this database — that
-- logger runs from a standalone training script that shouldn't require
-- live DB credentials. No table is created for it here.

-- ── 1. Roles (Section 3.4 actors: Steward, Verifier/Analyst, plus the
--      Research-Administrator backend tier) ─────────────────────────────
-- Widen the CHECK constraint to accept both the new role names and every
-- legacy value already in use (landowner/buyer/admin from schema.sql,
-- 'business' from later application code that pre-dates this constraint —
-- see backend/routers/auth.py's LEGACY_ROLE_MAP / ROLE_DB_FALLBACK).
ALTER TABLE users
DROP CONSTRAINT IF EXISTS users_role_check;

ALTER TABLE users
ADD CONSTRAINT users_role_check
CHECK (role IN (
  'steward', 'verifier_analyst', 'research_admin',           -- proposal roles
  'landowner', 'buyer', 'admin', 'business'                   -- legacy values
));

COMMENT ON COLUMN users.role IS
'Capstone roles: steward (was landowner), verifier_analyst (was buyer/business), research_admin (was admin). Legacy values retained for backward compatibility with TerraFoma LTD (backend/legacy/) and pre-rescope rows.';

-- ── 2. Section 3.6 ethical safeguards ────────────────────────────────────

-- Safeguard 2 (role-based access): district a verifier_analyst is scoped
-- to for audit purposes. NULL = unscoped (sees all districts) — see the
-- documented fallback behaviour in backend/routers/landowner.py's
-- /verification-queue endpoint.
ALTER TABLE users
ADD COLUMN IF NOT EXISTS assigned_district TEXT;

COMMENT ON COLUMN users.assigned_district IS
'District a verifier_analyst is scoped to (e.g. Bugesera, Rulindo) for the audit queue in routers/landowner.py. NULL means unscoped/all-districts. Not meaningful for steward or research_admin rows.';

-- Safeguard 3 (separate, explicit consent for precise-location storage).
-- The Pydantic models (models/user.py, models/land_plot.py) already define
-- this field; this column makes it persistable. Defaults to FALSE — the
-- least-permissive value — so existing rows are not retroactively treated
-- as having consented.
ALTER TABLE users
ADD COLUMN IF NOT EXISTS precise_location_consent BOOLEAN NOT NULL DEFAULT FALSE;

COMMENT ON COLUMN users.precise_location_consent IS
'Explicit, separate consent for storing this user''s plot coordinates at full (unrounded) precision in the research database. See backend/services/privacy.py for how full-precision access is gated at read time regardless of this flag.';

-- Safeguard 4 (defined retention period: capstone duration + 12 months for
-- identifying data). Nullable — set at account creation / consent time by
-- application code once that workflow is implemented; this migration only
-- adds the column.
ALTER TABLE users
ADD COLUMN IF NOT EXISTS data_retention_until TIMESTAMPTZ;

COMMENT ON COLUMN users.data_retention_until IS
'Date after which this user''s identifying data (precise coordinates, contact info) should be purged or anonymised, per proposal Section 3.6 safeguard 4. NULL until a retention-period workflow sets it; no automatic enforcement exists yet (see README "Known Limitations").';

-- ── 3. Districts (Section 1.5/3.3.1: Bugesera + Rulindo validation
--      strata, replacing the earlier Kigali City sample) ────────────────
ALTER TABLE land_plots
ADD COLUMN IF NOT EXISTS district TEXT;

COMMENT ON COLUMN land_plots.district IS
'Rwandan district the plot falls in. The capstone''s active field-validation sample covers Bugesera (grassland/savanna) and Rulindo (agroforestry) only; other values are accepted for plots outside the active sample (e.g. demo/illustrative data, or future expansion).';

CREATE INDEX IF NOT EXISTS idx_land_plots_district ON land_plots(district);

-- land_plots.land_use already accepts 'agroforestry' and 'grassland'
-- (schema.sql's original CHECK constraint) — no change needed here.

-- ── 4. Verification status values (Section 3.4 entity: Verification) ────
-- carbon_credits.status was last constrained by
-- migration_approval_workflow.sql to ('pending_approval', 'approved',
-- 'listed', 'sold', 'retired', 'rejected') — which does NOT include
-- 'verified', 'flagged', or 'pending_review', all three of which
-- backend/routers/landowner.py's verify_scan_record already writes. This
-- widens the constraint to include them, alongside every previously
-- accepted value, so existing rows and in-flight requests keep validating.
ALTER TABLE carbon_credits
DROP CONSTRAINT IF EXISTS carbon_credits_status_check;

ALTER TABLE carbon_credits
ADD CONSTRAINT carbon_credits_status_check
CHECK (status IN (
  'pending_review', 'verified', 'flagged',                              -- current verification-flow values
  'pending_approval', 'approved', 'listed', 'sold', 'retired', 'rejected', -- legacy marketplace values
  'pending'                                                             -- original schema.sql default
));

COMMENT ON COLUMN carbon_credits.status IS
'Verification-flow status (capstone re-scope): pending_review/pending_approval (awaiting a verifier_analyst), verified (confirmed, in the audit trail), flagged (queried/excluded). Remaining values (approved/listed/sold/retired/rejected/pending) are legacy marketplace-era statuses, retained for backward compatibility — this capstone has no secondary market or credit issuance.';

-- ── 5. Verification entity scaffold (Section 3.4 class diagram) ─────────
-- The running app still uses carbon_credits as the de facto verification
-- record (see backend/routers/landowner.py) rather than this dedicated
-- table — introducing it here is schema-only groundwork for a future
-- migration that actually moves verification data over, not a live
-- dependency of any current endpoint.
CREATE TABLE IF NOT EXISTS verifications (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  credit_id     UUID REFERENCES carbon_credits(id) ON DELETE CASCADE,
  plot_id       UUID REFERENCES land_plots(id),
  verifier_id   UUID REFERENCES users(id),
  district      TEXT,
  decision      TEXT CHECK (decision IN ('verified', 'flagged')),
  notes         TEXT,
  reviewed_at   TIMESTAMPTZ DEFAULT now(),
  created_at    TIMESTAMPTZ DEFAULT now()
);

COMMENT ON TABLE verifications IS
'Section 3.4 Verification entity scaffold. Not yet written to by the application — backend/routers/landowner.py currently records verification outcomes directly on carbon_credits.status/updated_at. Reserved for a future migration that formalises a one-credit-to-many-verifications audit history.';

-- ── 6. Index to support the new district-scoped verifier query ──────────
CREATE INDEX IF NOT EXISTS idx_users_assigned_district ON users(assigned_district);

-- carbon_credits(status) is already indexed by migration_approval_workflow.sql
-- (idx_carbon_credits_status) — no new index needed for the widened CHECK.
