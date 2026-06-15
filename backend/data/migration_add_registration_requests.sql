-- Add registration_requests table
-- Run this in the Supabase SQL Editor

CREATE TABLE IF NOT EXISTS registration_requests (
  id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  owner_name        TEXT NOT NULL,
  owner_email       TEXT NOT NULL,
  land_location     TEXT NOT NULL,
  land_size         TEXT NOT NULL,
  land_type         TEXT NOT NULL,
  coordinates       JSONB,
  boundaries        JSONB,
  geometry          JSONB,
  additional_info   TEXT,
  status            TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
  created_at        TIMESTAMPTZ DEFAULT now(),
  processed_at      TIMESTAMPTZ,
  processed_by      UUID REFERENCES users(id),
  notes             TEXT
);

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_registration_requests_status ON registration_requests(status);
CREATE INDEX IF NOT EXISTS idx_registration_requests_owner_email ON registration_requests(owner_email);
CREATE INDEX IF NOT EXISTS idx_registration_requests_created_at ON registration_requests(created_at DESC);

-- Enable Row Level Security
ALTER TABLE registration_requests ENABLE ROW LEVEL SECURITY;

-- Policy: Admins can view all requests
CREATE POLICY "Admins can view all registration requests"
  ON registration_requests
  FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM users
      WHERE users.id = auth.uid()
      AND users.role = 'admin'
    )
  );

-- Policy: Admins can update requests
CREATE POLICY "Admins can update registration requests"
  ON registration_requests
  FOR UPDATE
  USING (
    EXISTS (
      SELECT 1 FROM users
      WHERE users.id = auth.uid()
      AND users.role = 'admin'
    )
  );

-- Policy: Landowners can insert their own requests
CREATE POLICY "Landowners can create registration requests"
  ON registration_requests
  FOR INSERT
  WITH CHECK (true);

-- Policy: Users can view their own requests
CREATE POLICY "Users can view their own registration requests"
  ON registration_requests
  FOR SELECT
  USING (owner_email = (SELECT email FROM users WHERE id = auth.uid()));
