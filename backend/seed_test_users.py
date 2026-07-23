#!/usr/bin/env python3
"""Simple script to seed test users with password hashes into the database."""

import hashlib
from datetime import datetime
from database import get_admin_client

def hash_password(password: str) -> str:
    """Hash password using SHA256 (matches auth.py implementation)."""
    return hashlib.sha256(password.encode()).hexdigest()

def seed_test_users():
    db = get_admin_client()

    test_users = [
        {
            "email": "stephenwahome@gmail.com",
            "password": "password123",
            "full_name": "Stephen Wahome",
            "role": "steward",
        },
        {
            "email": "verifier@terrafoma.local",
            "password": "password123",
            "full_name": "Verifier Analyst",
            "role": "analyst",
        },
        {
            "email": "admin@terrafoma.local",
            "password": "password123",
            "full_name": "Research Admin",
            "role": "research_admin",
        },
    ]

    print("Seeding test users...")
    for user in test_users:
        try:
            # Check if user already exists
            existing = db.table("users").select("*").eq("email", user["email"]).execute()

            user_data = {
                "email": user["email"],
                "password_hash": hash_password(user["password"]),
                "full_name": user["full_name"],
                "role": user["role"],
                "company_name": None,
                "created_at": datetime.now().isoformat(),
            }

            if existing.data:
                # Update existing user
                db.table("users").update(user_data).eq("email", user["email"]).execute()
                print(f"[+] Updated: {user['email']} (role: {user['role']})")
            else:
                # Insert new user
                db.table("users").insert(user_data).execute()
                print(f"[+] Created: {user['email']} (role: {user['role']})")

        except Exception as e:
            print(f"[-] Error creating {user['email']}: {e}")

    print("\nTest users seeded successfully!")
    print("You can now login with:")
    for user in test_users:
        print(f"  Email: {user['email']}")
        print(f"  Password: {user['password']}")

if __name__ == "__main__":
    seed_test_users()
