#!/bin/bash
# Quick script to check users in Supabase

cd /Users/cococe/Desktop/terrafoma/backend
source ../.venv/bin/activate

python << 'EOF'
from database import get_admin_client
from datetime import datetime

db = get_admin_client()

print("\n🌳 TERRAFOMA USERS IN SUPABASE\n")
print("=" * 60)

# Get all users
try:
    users = db.table('users').select('*').execute()
    print(f"\n✅ Found {len(users.data)} users:\n")
    
    for i, user in enumerate(users.data, 1):
        print(f"{i}. {user['email']}")
        print(f"   Role: {user['role']}")
        print(f"   Name: {user['full_name']}")
        if user.get('company_name'):
            print(f"   Company: {user['company_name']}")
        print(f"   Created: {user['created_at'][:10]}")
        print()
        
except Exception as e:
    print(f"❌ Error: {e}")

# Get active sessions
try:
    sessions = db.table('sessions').select('*').execute()
    print(f"\n🔑 Active Sessions: {len(sessions.data)}")
    
except Exception as e:
    print(f"❌ Error getting sessions: {e}")

print("=" * 60)
print("\n💡 To view in Supabase dashboard:")
print("   https://app.supabase.com/project/mozrcszdqinkjnnopkio/editor")
print()

EOF
