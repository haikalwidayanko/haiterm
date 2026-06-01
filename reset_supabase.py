from db_client import get_supabase_client
import time

def clear_journal():
    client = get_supabase_client()
    if not client:
        return
        
    res = client.table("trade_journal").select("id").execute()
    ids = [item["id"] for item in res.data]
    
    print(f"Deleting {len(ids)} records from Supabase...")
    for idx, trade_id in enumerate(ids):
        client.table("trade_journal").eq("id", trade_id).delete()
        time.sleep(0.1)
    print("Done clearing Supabase.")

if __name__ == "__main__":
    clear_journal()
