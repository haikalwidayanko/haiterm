import json
from db_client import get_supabase_client
import sys

def migrate_journal():
    client = get_supabase_client()
    if not client:
        print("Supabase client not ready.")
        return
        
    try:
        with open("trade_journal.json", "r") as f:
            local_db = json.load(f)
    except Exception as e:
        print(f"Failed to read trade_journal.json: {e}")
        return
        
    print(f"Found {len(local_db)} trades in local JSON. Migrating to Supabase...")
    
    for data in local_db:
        try:
            db_entry = data.copy()
            if "rr" in db_entry:
                del db_entry["rr"]
            if "opened_at_iso" in db_entry:
                del db_entry["opened_at_iso"]
            res = client.table("trade_journal").insert(db_entry)
            print(f"Successfully migrated trade: {data['ticker']}")
        except Exception as e:
            print(f"Failed to migrate trade {data['ticker']}: {e}")

if __name__ == "__main__":
    migrate_journal()
