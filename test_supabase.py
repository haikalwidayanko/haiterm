import streamlit as st
from db_client import get_supabase_client
import sys

def test():
    client = get_supabase_client()
    if not client:
        print("Client not initialized. Check if secrets are configured.")
        return
        
    try:
        print("Attempting to insert test user...")
        res = client.table("users").insert({
            "username": "test_script",
            "password": "123",
            "role": "contributor",
            "market_access": "ALL",
            "can_access_journal": True
        })
        print(f"Success! Result: {res}")
    except Exception as e:
        print(f"Error during insert: {e}")

if __name__ == "__main__":
    test()
