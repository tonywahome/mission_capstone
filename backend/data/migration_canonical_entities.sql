-- Migration: Canonical Entity Views (Section 3.4 class diagram)
-- Run this in the Supabase SQL Editor
-- Date: June 26, 2026
--
-- Purpose: the revised ALU capstone proposal's Section 3.4 class diagram
-- defines exactly four domain entities — Project, Steward, BiomassModel,
-- Verification. The underlying physical schema (schema.sql) predates the
-- re-scope and is organised around marketplace-era tables instead:
-- land_plots, users, scan_results, carbon_credits/verifications.
--
-- Rather than dropping or renaming those physical tables — which would
-- violate this project's additive-only migration philosophy and risk
-- breaking backend/legacy/ + frontend/legacy/ code still serving the
-- separate TerraFoma LTD commercial product — this migration adds four
-- read-only SQL VIEWs named exactly after the proposal's entities. Each
-- view re-projects and renames columns from an existing table onto the
-- proposal's vocabulary, without altering, dropping, or renaming anything
-- underneath it. CREATE OR REPLACE VIEW never touches the base tables, so
-- this file can be re-run safely and carries zero risk to existing rows
-- or running application code (backend/routers/*.py keep reading/writing
-- the physical tables directly; nothing currently queries these views).
--
-- This file has NOT been executed against any database by the assistant
-- that wrote it. Review and run it yourself in the Supabase SQL Editor.
-- Apply it AFTER schema.sql, migration_add_auth.sql,
-- migration_approval_workflow.sql, and migration_capstone_rescope.sql —
-- it reads columns (district, assigned_district, precise_location_consent,
-- data_retention_until) and the verifications table that only exist once
-- migration_capstone_rescope.sql has been applied.

-- ── 1. Project (Section 3.4) — wraps land_plots ──────────────────────────
-- One row per registered plot. "steward_id" is land_plots.owner_id renamed
-- to match the proposal's actor name; the underlying column is untouched.
CREATE OR REPLACE VIEW project AS
SELECT
  id,
  owner_id      AS steward_id,
  name,
  geometry,
  area_hectares,
  region,
  district,
  land_use,
  created_at
FROM land_plots;

COMMENT ON VIEW project IS
'Section 3.4 Project entity. Read-only re-projection of land_plots with owner_id renamed to steward_id. The physical table name (land_plots) is unchanged — see plots.py, models/land_plot.py for the code that actually reads/writes it.';

-- ── 2. Steward (Section 3.4) — wraps users, filtered to land-steward rows
-- Excludes verifier_analyst / research_admin rows so this view matches the
-- proposal's "Steward" actor 1:1. Legacy 'landowner' rows (pre-rescope
-- role name) are included since they are the same actor under the old name.
CREATE OR REPLACE VIEW steward AS
SELECT
  id,
  full_name,
  email,
  assigned_district,
  precise_location_consent,
  data_retention_until,
  created_at
FROM users
WHERE role IN ('steward', 'landowner');

COMMENT ON VIEW steward IS
'Section 3.4 Steward entity. Read-only re-projection of users filtered to role IN (steward, landowner) — landowner is the pre-rescope name for the same actor. The physical table name (users) is unchanged.';

-- ── 3. BiomassModel (Section 3.4) — wraps scan_results ───────────────────
-- Renames scan_results columns onto the proposal's AGB-estimation
-- vocabulary. uncertainty_pct is an honest NULL placeholder, NOT a
-- fabricated value: scan_results has no per-scan prediction-interval /
-- confidence-bound column yet (see README "Validation Geography and Model
-- Status" — the trained model is v1/legacy, pending a real Rulindo
-- retrain). Populate this column from genuine model output once the
-- retrained pipeline produces an uncertainty estimate; do not backfill it
-- with placeholder numbers.
CREATE OR REPLACE VIEW biomass_model AS
SELECT
  id,
  plot_id           AS project_id,
  mean_ndvi,
  mean_evi,
  estimated_biomass AS agb_estimate_t_ha,
  estimated_tco2e   AS carbon_stock_tco2e,
  carbon_density,
  integrity_score,
  model_version,
  NULL::FLOAT       AS uncertainty_pct,
  created_at        AS run_at
FROM scan_results;

COMMENT ON VIEW biomass_model IS
'Section 3.4 BiomassModel entity. Read-only re-projection of scan_results with AGB-estimation column names. uncertainty_pct is a deliberate NULL placeholder (no real per-scan uncertainty value exists yet) — see the column comment in this migration for why it is not fabricated. The physical table name (scan_results) is unchanged.';

-- ── 4. Verification (Section 3.4) — aliases the verifications table ─────
-- migration_capstone_rescope.sql already created a `verifications` table
-- matching this entity (plural/snake_case). This view is a simple
-- exact-name alias so all four canonical entities can be queried with the
-- proposal's exact naming, without renaming the underlying table (which
-- backend/routers/landowner.py does not yet write to — see that table's
-- own COMMENT for the current state of the verification-recording flow).
CREATE OR REPLACE VIEW verification AS
SELECT * FROM verifications;

COMMENT ON VIEW verification IS
'Section 3.4 Verification entity. Read-only alias for the verifications table added by migration_capstone_rescope.sql. Not yet written to by the application — backend/routers/landowner.py currently records verification outcomes directly on carbon_credits.status/updated_at.';
