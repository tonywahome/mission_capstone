-- Links land_plots back to the registration_requests row that spawned them,
-- and adds a status so the dashboard can distinguish a plot that only exists
-- because a steward registered it from one that has actually been scanned.
-- Run this in the Supabase SQL Editor.

ALTER TABLE land_plots
ADD COLUMN IF NOT EXISTS registration_request_id UUID REFERENCES registration_requests(id);

ALTER TABLE land_plots
ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'pending_scan';

ALTER TABLE land_plots
DROP CONSTRAINT IF EXISTS land_plots_status_check;

ALTER TABLE land_plots
ADD CONSTRAINT land_plots_status_check CHECK (status IN ('pending_scan', 'scanned'));

CREATE INDEX IF NOT EXISTS idx_land_plots_registration_request_id ON land_plots(registration_request_id);

-- Backfill: any plot that already has a scan_results row is not "pending_scan".
UPDATE land_plots
SET status = 'scanned'
WHERE id IN (SELECT DISTINCT plot_id FROM scan_results WHERE plot_id IS NOT NULL);
