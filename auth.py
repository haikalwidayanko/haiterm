import json
import os
import hashlib
import uuid
import streamlit as st

from db_client import get_supabase_client

DB_FILE = "users_db.json"
SESSION_FILE = "sessions_db.json"

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def _load_db() -> dict:
    client = get_supabase_client()
    if client:
        try:
            res = client.table("users").select("*").execute()
            db = {}
            for row in res.data:
                db[row["username"]] = {
                    "password": row["password"],
                    "role": row["role"],
                    "market_access": row["market_access"],
                    "can_access_journal": row["can_access_journal"],
                    "telegram_chat_id": row.get("telegram_chat_id", "")
                }
            return db
        except Exception as e:
            print(f"[Supabase] _load_db error: {e}")

    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, "r") as f:
        try:
            return json.load(f)
        except:
            return {}

def _save_local_db(data: dict):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

def init_db():
    db = _load_db()
    if not db:
        # Create default admin
        add_user("admin", "admin123", "admin", "ALL", True, "")

def authenticate(username, password):
    db = _load_db()
    user = db.get(username)
    if user and user["password"] == hash_password(password):
        return True
    return False

def _load_sessions() -> dict:
    if not os.path.exists(SESSION_FILE):
        return {}
    with open(SESSION_FILE, "r") as f:
        try:
            return json.load(f)
        except:
            return {}

def _save_sessions(data: dict):
    with open(SESSION_FILE, "w") as f:
        json.dump(data, f, indent=4)

def create_session(username: str) -> str:
    token = str(uuid.uuid4())
    sessions = _load_sessions()
    sessions[token] = username
    _save_sessions(sessions)
    return token

def get_session_user(token: str):
    sessions = _load_sessions()
    return sessions.get(token)

def destroy_session(token: str):
    sessions = _load_sessions()
    if token in sessions:
        del sessions[token]
        _save_sessions(sessions)

def get_user_role(username):
    db = _load_db()
    return db.get(username, {}).get("role", "contributor")

def get_user_config(username):
    db = _load_db()
    user = db.get(username, {})
    return {
        "market_access": user.get("market_access", "ALL"),
        "can_access_journal": user.get("can_access_journal", True)
    }

def get_all_users():
    return _load_db()

def get_all_telegram_ids():
    """Returns a list of all non-empty telegram chat IDs from all users."""
    db = _load_db()
    ids = []
    for uname, data in db.items():
        chat_id = data.get("telegram_chat_id", "").strip()
        if chat_id:
            ids.append(chat_id)
    return list(set(ids))

def add_user(username, password, role, market_access, can_access_journal, telegram_chat_id=""):
    db = _load_db()
    if username in db:
        return False, "User already exists"
    
    hashed = hash_password(password)
    client = get_supabase_client()
    if client:
        try:
            client.table("users").insert({
                "username": username,
                "password": hashed,
                "role": role,
                "market_access": market_access,
                "can_access_journal": can_access_journal,
                "telegram_chat_id": telegram_chat_id
            })
        except Exception as e:
            print(f"[Supabase] add_user error: {e}")
            # Check if error is due to missing telegram_chat_id column
            is_missing_tg = False
            if hasattr(e, 'response') and e.response is not None:
                try:
                    err_json = e.response.json()
                    if "telegram_chat_id" in err_json.get("message", ""):
                        is_missing_tg = True
                except:
                    pass
            
            if is_missing_tg:
                print("[Supabase] telegram_chat_id column missing. Retrying without it...")
                try:
                    client.table("users").insert({
                        "username": username,
                        "password": hashed,
                        "role": role,
                        "market_access": market_access,
                        "can_access_journal": can_access_journal
                    })
                except Exception as retry_err:
                    print(f"[Supabase] Retry add_user error: {retry_err}")
                    return False, f"Supabase error: {retry_err}"
            else:
                return False, f"Supabase error: {e}"
            
    db[username] = {
        "password": hashed,
        "role": role,
        "market_access": market_access,
        "can_access_journal": can_access_journal,
        "telegram_chat_id": telegram_chat_id
    }
    _save_local_db(db)
    return True, "User created successfully"

def update_user(username, role, market_access, can_access_journal, telegram_chat_id=""):
    db = _load_db()
    if username not in db:
        return False, "User not found"
        
    client = get_supabase_client()
    if client:
        try:
            client.table("users").eq("username", username).update({
                "role": role,
                "market_access": market_access,
                "can_access_journal": can_access_journal,
                "telegram_chat_id": telegram_chat_id
            })
        except Exception as e:
            print(f"[Supabase] update_user error: {e}")
            # Check if error is due to missing telegram_chat_id column
            is_missing_tg = False
            if hasattr(e, 'response') and e.response is not None:
                try:
                    err_json = e.response.json()
                    if "telegram_chat_id" in err_json.get("message", ""):
                        is_missing_tg = True
                except:
                    pass
            
            if is_missing_tg:
                print("[Supabase] telegram_chat_id column missing. Retrying without it...")
                try:
                    client.table("users").eq("username", username).update({
                        "role": role,
                        "market_access": market_access,
                        "can_access_journal": can_access_journal
                    })
                except Exception as retry_err:
                    print(f"[Supabase] Retry update_user error: {retry_err}")
                    return False, f"Supabase error: {retry_err}"
            else:
                return False, f"Supabase error: {e}"
            
    db[username]["role"] = role
    db[username]["market_access"] = market_access
    db[username]["can_access_journal"] = can_access_journal
    db[username]["telegram_chat_id"] = telegram_chat_id
    _save_local_db(db)
    return True, "User updated successfully"

def delete_user(username):
    db = _load_db()
    if db.get(username, {}).get("role") == "admin":
        admins = [u for u, d in db.items() if d.get("role") == "admin"]
        if len(admins) <= 1:
            return False, "Cannot delete the last admin user"
            
    if username in db:
        client = get_supabase_client()
        if client:
            try:
                client.table("users").eq("username", username).delete()
            except Exception as e:
                print(f"[Supabase] delete_user error: {e}")
                return False, f"Supabase error: {e}"
                
        del db[username]
        _save_local_db(db)
        return True, "User deleted successfully"
    return False, "User not found"

def change_password(username, new_password):
    db = _load_db()
    if username in db:
        hashed = hash_password(new_password)
        client = get_supabase_client()
        if client:
            try:
                client.table("users").eq("username", username).update({
                    "password": hashed
                })
            except Exception as e:
                print(f"[Supabase] change_password error: {e}")
                return False, f"Supabase error: {e}"
                
        db[username]["password"] = hashed
        _save_local_db(db)
        return True, "Password updated successfully"
    return False, "User not found"

def has_pair_access(username, pair_name):
    # Backward compatibility if needed, though we filter in UI now
    return True
