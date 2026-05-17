import streamlit as st
import requests

def is_supabase_enabled() -> bool:
    """Check if Supabase credentials are configured in Streamlit Secrets."""
    try:
        return "supabase" in st.secrets and "url" in st.secrets["supabase"] and "key" in st.secrets["supabase"]
    except Exception:
        return False

class SupabaseRESTClient:
    def __init__(self, url, key):
        self.url = url.rstrip("/")
        self.key = key
        self.headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }

    def table(self, table_name):
        return SupabaseTable(self, table_name)

class SupabaseTable:
    def __init__(self, client, table_name):
        self.client = client
        self.table_name = table_name
        self.endpoint = f"{self.client.url}/rest/v1/{table_name}"
        self.params = {}

    def select(self, columns="*"):
        self.params["select"] = columns
        return self

    def order(self, column, desc=False):
        self.params["order"] = f"{column}.{'desc' if desc else 'asc'}"
        return self

    def eq(self, column, value):
        self.params[column] = f"eq.{value}"
        return self

    def execute(self):
        res = requests.get(self.endpoint, headers=self.client.headers, params=self.params)
        res.raise_for_status()
        class Result:
            def __init__(self, data):
                self.data = data
        return Result(res.json())

    def insert(self, data):
        res = requests.post(self.endpoint, headers=self.client.headers, json=data)
        res.raise_for_status()
        return res.json()

    def update(self, data):
        headers = self.client.headers.copy()
        # Must have a filter applied before calling update, usually eq()
        res = requests.patch(self.endpoint, headers=headers, params=self.params, json=data)
        res.raise_for_status()
        return res.json()

    def delete(self):
        res = requests.delete(self.endpoint, headers=self.client.headers, params=self.params)
        res.raise_for_status()
        # Delete often returns 204 No Content
        return True

@st.cache_resource
def get_supabase_client():
    """Get the cached Supabase REST client instance if enabled, otherwise return None."""
    if not is_supabase_enabled():
        return None
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return SupabaseRESTClient(url, key)
    except Exception as e:
        print(f"[Supabase Connect Error] Failed to connect: {e}")
        return None
