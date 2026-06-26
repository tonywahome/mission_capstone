#!/usr/bin/env python3
"""
Create registration_requests table in Supabase
"""
import os
from database import get_admin_client

def create_registration_requests_table():
    """Create the registration_requests table"""
    db = get_admin_client()
    
    # Read the migration SQL
    with open('data/migration_add_registration_requests.sql', 'r') as f:
        sql = f.read()
    
    # Execute via Supabase REST API
    # Note: For complex SQL with policies, better to run directly in Supabase SQL Editor
    print("SQL Migration Script:")
    print("=" * 80)
    print(sql)
    print("=" * 80)
    print("\nPlease run this SQL in your Supabase SQL Editor:")
    print("1. Go to https://supabase.com/dashboard/project/YOUR_PROJECT/sql")
    print("2. Copy and paste the SQL above")
    print("3. Click 'Run'")
    print("\nAlternatively, create the table via Python:")
    
    try:
        # Try to create via direct SQL (may not work for all statements)
        from supabase import create_client
        
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", os.getenv("SUPABASE_KEY"))
        
        if not url or not key:
            print("\nError: SUPABASE_URL or SUPABASE_KEY not set in environment")
            return
        
        supabase = create_client(url, key)
        
        # Check if table exists by trying to query it
        try:
            result = supabase.table('registration_requests').select('id').limit(1).execute()
            print("\n✅ Table 'registration_requests' already exists!")
            return
        except Exception as e:
            print(f"\nTable doesn't exist yet. Error: {e}")
            print("Please run the SQL migration in Supabase SQL Editor")
            
    except Exception as e:
        print(f"\nError checking table: {e}")
        print("Please run the SQL migration manually in Supabase SQL Editor")

if __name__ == "__main__":
    create_registration_requests_table()
