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
        self._operation = None  # "select", "insert", "update", "delete"
        self._payload = None

    def select(self, columns="*"):
        self.params["select"] = columns
        self._operation = "select"
        return self

    def order(self, column, desc=False):
        self.params["order"] = f"{column}.{'desc' if desc else 'asc'}"
        return self

    def eq(self, column, value):
        self.params[column] = f"eq.{value}"
        return self

    def insert(self, data):
        self._operation = "insert"
        self._payload = data
        return self

    def update(self, data):
        self._operation = "update"
        self._payload = data
        return self

    def delete(self):
        self._operation = "delete"
        return self

    def execute(self):
        class Result:
            def __init__(self, data):
                self.data = data

        op = self._operation or "select"

        if op == "insert":
            res = requests.post(self.endpoint, headers=self.client.headers, json=self._payload)
            res.raise_for_status()
            data = res.json() if res.content else []
            return Result(data if isinstance(data, list) else [data])

        elif op == "update":
            # Supabase requires at least one filter for PATCH to avoid full-table update
            filter_params = {k: v for k, v in self.params.items() if k != "select"}
            if not filter_params:
                raise ValueError("[db_client] update() called without any eq() filter — refused to prevent full-table update")
            res = requests.patch(self.endpoint, headers=self.client.headers, params=filter_params, json=self._payload)
            res.raise_for_status()
            data = res.json() if res.content else []
            return Result(data if isinstance(data, list) else [data])

        elif op == "delete":
            filter_params = {k: v for k, v in self.params.items() if k != "select"}
            if not filter_params:
                raise ValueError("[db_client] delete() called without any eq() filter — refused to prevent full-table delete")
            res = requests.delete(self.endpoint, headers=self.client.headers, params=filter_params)
            res.raise_for_status()
            return Result([])

        else:  # select
            res = requests.get(self.endpoint, headers=self.client.headers, params=self.params)
            res.raise_for_status()
            return Result(res.json())

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
