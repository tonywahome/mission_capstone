-- Migration: Add admin role and registration requests table

-- Update role check to include current app roles
ALTER TABLE users 
DROP CONSTRAINT IF EXISTS users_role_check;

ALTER TABLE users 
ADD CONSTRAINT users_role_check 
CHECK (role IN ('steward', 'verifier_analyst', 'research_admin'));

-- Create registration_requests table
CREATE TABLE IF NOT EXISTS registration_requests (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  owner_name    TEXT NOT NULL,
  owner_email   TEXT NOT NULL,
  land_location TEXT NOT NULL,
  land_size     TEXT NOT NULL,
  land_type     TEXT NOT NULL CHECK (land_type IN ('forest', 'grassland', 'cropland', 'wetland', 'agroforestry', 'bareland')),
  additional_info TEXT,
  status        TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
  created_at    TIMESTAMPTZ DEFAULT now(),
  processed_at  TIMESTAMPTZ,
  processed_by  UUID REFERENCES users(id),
  notes         TEXT
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_registration_requests_status ON registration_requests(status);
CREATE INDEX IF NOT EXISTS idx_registration_requests_email ON registration_requests(owner_email);
CREATE INDEX IF NOT EXISTS idx_registration_requests_created ON registration_requests(created_at DESC);

-- Add comments
COMMENT ON TABLE registration_requests IS 'Land registration requests from landowners to be processed by admin';
COMMENT ON COLUMN registration_requests.status IS 'pending: awaiting processing, approved: scanned and issued, rejected: declined';
COMMENT ON COLUMN registration_requests.processed_by IS 'Admin user who processed this request';

-- Create research admin user with hashed password
-- Password: Papertrail.444 (SHA256 hashed)
-- To change password later, hash your new password and run:
-- UPDATE users SET password_hash = '<new_hashed_password>' WHERE email = 'antonomics101@gmail.com';
INSERT INTO users (email, password_hash, full_name, role, created_at)
VALUES (
  'antonomics101@gmail.com',
  '62bb616110e3a2d740af9f3cc46d7d2d347c34047c48e012ab1caf82fd503fd1', -- SHA256 hash of 'Papertrail.444'
  'Admin User',
  'research_admin',
  now()
)
ON CONFLICT (email) DO UPDATE
SET role = 'research_admin', password_hash = '62bb616110e3a2d740af9f3cc46d7d2d347c34047c48e012ab1caf82fd503fd1';
