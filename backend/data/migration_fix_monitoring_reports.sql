-- Fixes a schema/code drift bug in monitoring_reports.
--
-- migration_close_schema_gaps.sql originally created monitoring_reports
-- with columns (mean_ndvi, mean_evi, vegetation_cover_pct, biomass_estimate,
-- change_detected, change_type, change_magnitude_pct, notes) matching an
-- earlier draft of the monitoring pipeline. ml/monitor_biomass.py's
-- analyze_plot_monitoring_data() and routers/monitoring.py's
-- _run_plot_check() were since rewritten to build a different report shape
-- and were never reconciled with the live table — every insert into
-- monitoring_reports has been silently failing (PostgREST error PGRST204,
-- "Could not find the 'baseline_ndvi' column ..."), caught by the router's
-- broad try/except, so GET /api/monitoring/plots/{id}/latest|history and
-- /api/monitoring/summary have never returned real data on any database
-- where the original migration already ran.
--
-- Additive only, per this project's migration philosophy (see
-- migration_capstone_rescope.sql's header) — adds the columns the code
-- actually writes; does not drop the stale columns from the original
-- CREATE TABLE, in case anything external still reads them.

ALTER TABLE monitoring_reports ADD COLUMN IF NOT EXISTS current_ndvi FLOAT;
ALTER TABLE monitoring_reports ADD COLUMN IF NOT EXISTS baseline_ndvi FLOAT;
ALTER TABLE monitoring_reports ADD COLUMN IF NOT EXISTS delta_ndvi FLOAT;
ALTER TABLE monitoring_reports ADD COLUMN IF NOT EXISTS z_score FLOAT;
ALTER TABLE monitoring_reports ADD COLUMN IF NOT EXISTS classification TEXT;
ALTER TABLE monitoring_reports ADD COLUMN IF NOT EXISTS cause TEXT;
ALTER TABLE monitoring_reports ADD COLUMN IF NOT EXISTS explanation TEXT;
ALTER TABLE monitoring_reports ADD COLUMN IF NOT EXISTS recommendation TEXT;
ALTER TABLE monitoring_reports ADD COLUMN IF NOT EXISTS spectral_context JSONB;
ALTER TABLE monitoring_reports ADD COLUMN IF NOT EXISTS data_quality TEXT;
-- alert_level, plot_id, check_date, id, created_at already exist from the
-- original CREATE TABLE.
