-- Add geometry column to registration_requests table if it doesn't exist
-- Run this in Supabase SQL Editor

-- Add geometry column (will safely skip if already exists)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'registration_requests' 
        AND column_name = 'geometry'
    ) THEN
        ALTER TABLE registration_requests ADD COLUMN geometry JSONB;
        RAISE NOTICE 'Added geometry column to registration_requests';
    ELSE
        RAISE NOTICE 'Geometry column already exists in registration_requests';
    END IF;
END $$;

-- Verify the column was added
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'registration_requests' 
AND column_name IN ('geometry', 'boundaries', 'coordinates')
ORDER BY column_name;
