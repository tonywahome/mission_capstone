-- Migration: Add Landowner Approval Workflow
-- Run this in Supabase SQL Editor
-- Date: March 7, 2026

-- 1. Update carbon_credits status to include 'pending_approval'
ALTER TABLE carbon_credits 
DROP CONSTRAINT IF EXISTS carbon_credits_status_check;

ALTER TABLE carbon_credits 
ADD CONSTRAINT carbon_credits_status_check 
CHECK (status IN ('pending_approval', 'approved', 'listed', 'sold', 'retired', 'rejected'));

-- 2. Add coordinates and boundaries to registration_requests
ALTER TABLE registration_requests
ADD COLUMN IF NOT EXISTS coordinates JSONB,
ADD COLUMN IF NOT EXISTS boundaries JSONB,
ADD COLUMN IF NOT EXISTS scan_id UUID REFERENCES scan_results(id),
ADD COLUMN IF NOT EXISTS credit_id UUID REFERENCES carbon_credits(id),
ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS rejected_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS rejection_reason TEXT;

-- 3. Create notifications table for landowner alerts
CREATE TABLE IF NOT EXISTS notifications (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  type TEXT NOT NULL CHECK (type IN ('scan_complete', 'credit_approved', 'credit_sold', 'system')),
  title TEXT NOT NULL,
  message TEXT NOT NULL,
  data JSONB,
  read BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_read ON notifications(user_id, read);
CREATE INDEX IF NOT EXISTS idx_registration_requests_scan_id ON registration_requests(scan_id);
CREATE INDEX IF NOT EXISTS idx_carbon_credits_status ON carbon_credits(status);

-- 4. Add comment for clarity
COMMENT ON COLUMN carbon_credits.status IS 
'Credit status: pending_approval (waiting landowner), approved (landowner accepted), listed (on marketplace), sold (purchased), retired (offset), rejected (landowner declined)';

-- 5. Update existing 'verified' or 'pending' credits to 'listed' (they are already approved)
UPDATE carbon_credits 
SET status = 'listed' 
WHERE status IN ('verified', 'pending');

COMMENT ON TABLE notifications IS 
'User notifications for scan completion, credit approvals, sales, etc.';
