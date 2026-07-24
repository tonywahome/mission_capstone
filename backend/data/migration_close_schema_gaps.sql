-- Migration: Close live-schema gaps discovered during post-Supabase-Auth bug-fix verification
-- Run this in Supabase SQL Editor
-- Adapted 2026-07-22
--
-- Several migration files under backend/data/ were apparently never run
-- against this project. This is a single, consolidated, additive-only
-- script that closes every gap found while verifying the auth-migration
-- bug fixes: notifications table, registration_requests columns, the
-- carbon_credits status CHECK, scan_results uncertainty columns, and
-- land_plots registration-link columns. It deliberately excludes every
-- data-mutating UPDATE/INSERT and every reference to the old (renamed)
-- `users` table — those are called out explicitly at the bottom instead
-- of being silently run.
--
-- Safe to run once. Every statement is CREATE TABLE IF NOT EXISTS /
-- ADD COLUMN IF NOT EXISTS / DROP CONSTRAINT IF EXISTS (immediately
-- followed by an equivalent-or-wider ADD CONSTRAINT) — no data is deleted
-- or altered by this file.

-- ── 1. carbon_credits status CHECK: add 'pending_approval' ──────────────
ALTER TABLE carbon_credits
DROP CONSTRAINT IF EXISTS carbon_credits_status_check;

ALTER TABLE carbon_credits
ADD CONSTRAINT carbon_credits_status_check
CHECK (status IN ('pending_approval', 'approved', 'listed', 'sold', 'retired', 'rejected'));

-- ── 2. registration_requests: add approval-workflow columns ─────────────
ALTER TABLE registration_requests
ADD COLUMN IF NOT EXISTS coordinates JSONB,
ADD COLUMN IF NOT EXISTS boundaries JSONB,
ADD COLUMN IF NOT EXISTS scan_id UUID REFERENCES scan_results(id),
ADD COLUMN IF NOT EXISTS credit_id UUID REFERENCES carbon_credits(id),
ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS rejected_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS rejection_reason TEXT;

-- ── 3. notifications table (user_id -> profiles, not the old users) ─────
CREATE TABLE IF NOT EXISTS notifications (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
  type TEXT NOT NULL CHECK (type IN ('scan_complete', 'credit_approved', 'credit_sold', 'system')),
  title TEXT NOT NULL,
  message TEXT NOT NULL,
  data JSONB,
  read BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_read ON notifications(user_id, read);
CREATE INDEX IF NOT EXISTS idx_registration_requests_scan_id ON registration_requests(scan_id);
CREATE INDEX IF NOT EXISTS idx_carbon_credits_status ON carbon_credits(status);

COMMENT ON COLUMN carbon_credits.status IS
'Credit status: pending_approval (waiting landowner), approved (landowner accepted), listed (on marketplace), sold (purchased), retired (offset), rejected (landowner declined)';
COMMENT ON TABLE notifications IS
'User notifications for scan completion, credit approvals, sales, etc.';

-- ── 4. scan_results: uncertainty + model-metadata columns ───────────────
ALTER TABLE scan_results
ADD COLUMN IF NOT EXISTS biomass_lower_90 FLOAT,
ADD COLUMN IF NOT EXISTS biomass_upper_90 FLOAT,
ADD COLUMN IF NOT EXISTS biomass_uncertainty_pct FLOAT,
ADD COLUMN IF NOT EXISTS model_type TEXT,
ADD COLUMN IF NOT EXISTS model_r2 FLOAT,
ADD COLUMN IF NOT EXISTS sensors_used JSONB;

-- ── 5. land_plots: registration-request link + status ───────────────────
ALTER TABLE land_plots
ADD COLUMN IF NOT EXISTS registration_request_id UUID REFERENCES registration_requests(id);

ALTER TABLE land_plots
ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'pending_scan';

ALTER TABLE land_plots
DROP CONSTRAINT IF EXISTS land_plots_status_check;

ALTER TABLE land_plots
ADD CONSTRAINT land_plots_status_check CHECK (status IN ('pending_scan', 'scanned'));

CREATE INDEX IF NOT EXISTS idx_land_plots_registration_request_id ON land_plots(registration_request_id);

-- ── 6. audit_log: add the `details` column the app writes to ────────────
-- Not present in any prior migration file — scan.py's audit-trail insert
-- (backend/routers/scan.py) has always written a `details` JSONB field
-- that the live table never had a column for.
ALTER TABLE audit_log
ADD COLUMN IF NOT EXISTS details JSONB;

-- ── 7. monitoring_reports table ──────────────────────────────────────────
-- Needed by GET /api/plots/owner/{owner_id} and the monitoring dashboard
-- (backend/routers/monitoring.py, backend/routers/plots.py). Not created
-- by any prior migration file in this repo — defined here from the
-- columns backend/routers/monitoring.py and plots.py actually read/write.
--
-- NOTE (see migration_fix_monitoring_reports.sql): the column list below
-- was originally written against an earlier draft of the monitoring
-- pipeline. ml/monitor_biomass.py's analyze_plot_monitoring_data() and
-- routers/monitoring.py's _run_plot_check() were later rewritten to
-- produce a different report shape (current_ndvi/baseline_ndvi/delta_ndvi/
-- z_score/classification/cause/explanation/recommendation/spectral_context/
-- data_quality) without this CREATE TABLE being updated to match, so on
-- any database where this migration already ran, every monitoring-report
-- insert silently fails schema validation (caught by the router's broad
-- try/except) and /api/monitoring/plots/{id}/latest|history never returns
-- data. Fixed here for fresh installs; migration_fix_monitoring_reports.sql
-- ALTERs already-migrated databases additively (no columns dropped).
CREATE TABLE IF NOT EXISTS monitoring_reports (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  plot_id UUID REFERENCES land_plots(id) ON DELETE CASCADE,
  check_date TIMESTAMPTZ DEFAULT now(),
  current_ndvi FLOAT,
  baseline_ndvi FLOAT,
  delta_ndvi FLOAT,
  z_score FLOAT,
  classification TEXT,
  alert_level TEXT,
  cause TEXT,
  explanation TEXT,
  recommendation TEXT,
  spectral_context JSONB,
  data_quality TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_monitoring_reports_plot_id ON monitoring_reports(plot_id);
CREATE INDEX IF NOT EXISTS idx_monitoring_reports_check_date ON monitoring_reports(check_date);

-- ═══════════════════════════════════════════════════════════════════════
-- EXPLICITLY NOT INCLUDED — run these separately and deliberately, only
-- if you want the behavior described, since they mutate existing rows:
-- ═══════════════════════════════════════════════════════════════════════
--
-- -- Backfill: mark already-scanned plots as 'scanned' rather than the
-- -- 'pending_scan' default just added above.
-- UPDATE land_plots
-- SET status = 'scanned'
-- WHERE id IN (SELECT DISTINCT plot_id FROM scan_results WHERE plot_id IS NOT NULL);
--
-- -- Repricing / relisting existing credits — from migration_approval_workflow.sql
-- -- and update_carbon_prices.sql. Not run here; this project currently has
-- -- 0 carbon_credits rows in production use, so there is nothing to backfill.
-- UPDATE carbon_credits SET status = 'listed' WHERE status IN ('verified', 'pending');
