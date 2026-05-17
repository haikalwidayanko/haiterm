import json
from db_client import get_supabase_client
import sys

def migrate_users():
    client = get_supabase_client()
    if not client:
        print("Supabase client not ready.")
        return
        
    try:
        with open("users_db.json", "r") as f:
            local_db = json.load(f)
    except Exception as e:
        print(f"Failed to read users_db.json: {e}")
        return
        
    print(f"Found {len(local_db)} users in local JSON. Migrating to Supabase...")
    
    for username, data in local_db.items():
        try:
            res = client.table("users").insert({
                "username": username,
                "password": data["password"],
                "role": data.get("role", "contributor"),
                "market_access": data.get("market_access", "ALL"),
                "can_access_journal": data.get("can_access_journal", True)
            })
            print(f"Successfully migrated: {username}")
        except Exception as e:
            print(f"Failed to migrate {username} (might already exist): {e}")

if __name__ == "__main__":
    migrate_users()
