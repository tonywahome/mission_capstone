-- Migration: allow carbon_credits.status = 'withdrawn'
-- Run this in Supabase SQL Editor, after migration_capstone_rescope.sql
-- (and after migration_close_schema_gaps.sql if you also run that one —
-- see note below).
--
-- backend/routers/landowner.py's new unsubmit_scan_record endpoint lets a
-- steward withdraw their own not-yet-reviewed submission, writing
-- status = 'withdrawn'. No prior migration's CHECK constraint allows that
-- value yet.
--
-- NOTE: this restates the FULL known status list (not just adding
-- 'withdrawn' to whatever is live) because migration_close_schema_gaps.sql
-- drops and recreates this same constraint with only the legacy marketplace
-- values ('pending_approval', 'approved', 'listed', 'sold', 'retired',
-- 'rejected') — missing 'pending_review', 'verified', 'flagged', and
-- 'pending' from migration_capstone_rescope.sql. Run this migration last
-- (or re-run it) to guarantee the constraint stays wide enough regardless
-- of what order the other migration files were applied in.

ALTER TABLE carbon_credits
DROP CONSTRAINT IF EXISTS carbon_credits_status_check;

ALTER TABLE carbon_credits
ADD CONSTRAINT carbon_credits_status_check
CHECK (status IN (
  'pending_review', 'verified', 'flagged', 'withdrawn',                    -- current verification-flow values
  'pending_approval', 'approved', 'listed', 'sold', 'retired', 'rejected', -- legacy marketplace values
  'pending'                                                                -- original schema.sql default
));

COMMENT ON COLUMN carbon_credits.status IS
'Verification-flow status (capstone re-scope): pending_review/pending_approval (awaiting a verifier_analyst), verified (confirmed, in the audit trail), flagged (queried/excluded), withdrawn (steward pulled back their own submission before review). Remaining values (approved/listed/sold/retired/rejected/pending) are legacy marketplace-era statuses, retained for backward compatibility.';
