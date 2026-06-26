-- Migration: Add authentication support to TerraFoma
-- Adds password_hash to users table and creates sessions table

-- Update users table to add password_hash column
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS password_hash TEXT;

-- Update role check to match new roles (landowner, business)
ALTER TABLE users 
DROP CONSTRAINT IF EXISTS users_role_check;

ALTER TABLE users 
ADD CONSTRAINT users_role_check 
CHECK (role IN ('landowner', 'business', 'admin'));

-- Create sessions table for authentication tokens
CREATE TABLE IF NOT EXISTS sessions (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id       UUID REFERENCES users(id) ON DELETE CASCADE,
  token         TEXT UNIQUE NOT NULL,
  created_at    TIMESTAMPTZ DEFAULT now(),
  expires_at    TIMESTAMPTZ DEFAULT (now() + INTERVAL '30 days')
);

-- Create index on token for fast lookups
CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);

-- Add index on email for login lookups
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- Comment describing the tables
COMMENT ON TABLE users IS 'User accounts with role-based access (landowner, business, admin)';
COMMENT ON TABLE sessions IS 'Active user sessions with bearer tokens';
COMMENT ON COLUMN users.password_hash IS 'SHA256 hashed password (use bcrypt in production)';
COMMENT ON COLUMN users.role IS 'User role: landowner (sells credits), business (buys credits), admin';
