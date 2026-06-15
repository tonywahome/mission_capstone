"""Seed Supabase with Auth users and land plots.

Usage:
    python data/seed.py --users users.json
    python data/seed.py --users users.json --plots sample_plots.geojson

users.json format:
    [
        {
            "email": "user@example.com",
            "password": "SecurePass123!",
            "full_name": "Full Name",
            "role": "landowner" | "buyer" | "admin",
            "company_name": "Optional Company",

            // buyer-only fields (optional)
            "industry_sector": "...",
            "annual_emissions_tco2": 0.0,
            "energy_kwh_monthly": 0.0,
            "fuel_litres_monthly": 0.0,
            "employees": 0,
            "offset_target_pct": 0.0
        }
    ]
"""

import argparse
import json
import uuid
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database import get_admin_client


def create_or_get_auth_user(admin, user: dict) -> str:
    """Create a Supabase Auth user and return their UUID.
    If the user already exists, fetch and return their existing UUID."""
    try:
        response = admin.auth.admin.create_user(
            {
                "email": user["email"],
                "password": user["password"],
                "email_confirm": True,
                "user_metadata": {
                    "full_name": user["full_name"],
                    "role": user["role"],
                },
            }
        )
        return response.user.id
    except Exception as e:
        err = str(e).lower()
        if "already been registered" in err or "already exists" in err or "duplicate" in err:
            page = admin.auth.admin.list_users()
            for u in page:
                if hasattr(u, "email") and u.email == user["email"]:
                    return u.id
            raise RuntimeError(
                f"User {user['email']} exists but could not be retrieved: {e}"
            )
        raise


def seed_users(admin, db, users: list) -> list:
    print(f"\n[1/3] Creating {len(users)} Auth user(s)...")
    seeded = []
    for user in users:
        try:
            auth_id = create_or_get_auth_user(admin, user)
            profile = {
                "id": auth_id,
                "email": user["email"],
                "full_name": user["full_name"],
                "role": user["role"],
                "company_name": user.get("company_name"),
            }
            db.table("users").upsert(profile).execute()
            seeded.append({**user, "id": auth_id})
            print(f"  + {user['role']:10s}  {user['full_name']:20s}  {user['email']}")
        except Exception as e:
            print(f"  ! Failed for {user['email']}: {e}")
    return seeded


def seed_industrial_profiles(db, seeded_users: list):
    buyers = [u for u in seeded_users if u["role"] == "buyer"]
    if not buyers:
        return
    print(f"\n[2/3] Creating {len(buyers)} industrial profile(s)...")
    for user in buyers:
        try:
            profile = {
                "id": str(uuid.uuid4()),
                "user_id": user["id"],
                "company_name": user.get("company_name"),
                "industry_sector": user.get("industry_sector"),
                "annual_emissions_tco2": user.get("annual_emissions_tco2"),
                "energy_kwh_monthly": user.get("energy_kwh_monthly"),
                "fuel_litres_monthly": user.get("fuel_litres_monthly"),
                "employees": user.get("employees"),
                "offset_target_pct": user.get("offset_target_pct", 0),
            }
            db.table("industrial_profiles").upsert(profile, on_conflict="user_id").execute()
            print(f"  + {user.get('company_name', user['email'])}")
        except Exception as e:
            print(f"  ! {user.get('company_name', user['email'])}: {e}")


def seed_plots(db, geojson_path: str, seeded_users: list):
    landowner_ids = [u["id"] for u in seeded_users if u["role"] == "landowner"]
    if not landowner_ids:
        print("\n[3/3] Skipping plots — no landowners in the user list.")
        return

    with open(geojson_path) as f:
        geojson = json.load(f)

    features = geojson.get("features", [])
    print(f"\n[3/3] Seeding {len(features)} land plot(s)...")
    inserted = 0
    for i, feature in enumerate(features):
        props = feature["properties"]
        plot = {
            "id": str(uuid.uuid4()),
            "owner_id": landowner_ids[i % len(landowner_ids)],
            "name": props["name"],
            "geometry": feature["geometry"],
            "area_hectares": props["area_hectares"],
            "region": props.get("region", ""),
            "land_use": props.get("land_use", "forest"),
        }
        try:
            db.table("land_plots").insert(plot).execute()
            inserted += 1
            print(
                f"  + {props['name']:35s}  "
                f"{props['area_hectares']:5.1f} ha  "
                f"{props.get('land_use', '')}"
            )
        except Exception as e:
            print(f"  ! {props['name']}: {e}")
    print(f"  {inserted}/{len(features)} plots inserted.")


def seed(users_file: str, plots_file: str):
    admin = get_admin_client()
    db = admin  # service role key bypasses RLS

    print("=" * 60)
    print("TerraFoma – Supabase Seeder")
    print("=" * 60)

    with open(users_file) as f:
        users = json.load(f)

    seeded_users = seed_users(admin, db, users)
    seed_industrial_profiles(db, seeded_users)
    seed_plots(db, plots_file, seeded_users)

    print("\n" + "=" * 60)
    print(f"Done.  {len(seeded_users)} users seeded.")


if __name__ == "__main__":
    default_plots = os.path.join(os.path.dirname(__file__), "sample_plots.geojson")

    parser = argparse.ArgumentParser(description="Seed TerraFoma Supabase database")
    parser.add_argument(
        "--users",
        required=True,
        help="Path to a JSON file containing the list of users to create",
    )
    parser.add_argument(
        "--plots",
        default=default_plots,
        help=f"Path to a GeoJSON file of land plots (default: {default_plots})",
    )
    args = parser.parse_args()

    if not os.path.exists(args.users):
        print(f"Error: users file not found: {args.users}")
        sys.exit(1)
    if not os.path.exists(args.plots):
        print(f"Error: plots file not found: {args.plots}")
        sys.exit(1)

    seed(args.users, args.plots)
