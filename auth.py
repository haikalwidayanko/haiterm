import json
import os
import hashlib
import uuid
import streamlit as st

DB_FILE = "users_db.json"
SESSION_FILE = "sessions_db.json"

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def _load_db() -> dict:
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, "r") as f:
        try:
            return json.load(f)
        except:
            return {}

def _save_db(data: dict):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

def init_db():
    db = _load_db()
    if not db:
        # Create default admin
        db["admin"] = {
            "password": hash_password("admin123"),
            "role": "admin",
            "market_access": "ALL",
            "can_access_journal": True
        }
        _save_db(db)

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

def add_user(username, password, role, market_access, can_access_journal):
    db = _load_db()
    if username in db:
        return False, "User already exists"
    db[username] = {
        "password": hash_password(password),
        "role": role,
        "market_access": market_access,
        "can_access_journal": can_access_journal
    }
    _save_db(db)
    return True, "User created successfully"

def update_user(username, role, market_access, can_access_journal):
    db = _load_db()
    if username not in db:
        return False, "User not found"
    db[username]["role"] = role
    db[username]["market_access"] = market_access
    db[username]["can_access_journal"] = can_access_journal
    _save_db(db)
    return True, "User updated successfully"

def delete_user(username):
    db = _load_db()
    # Ensure there's at least one admin
    if db.get(username, {}).get("role") == "admin":
        admins = [u for u, d in db.items() if d.get("role") == "admin"]
        if len(admins) <= 1:
            return False, "Cannot delete the last admin user"
    if username in db:
        del db[username]
        _save_db(db)
        return True, "User deleted successfully"
    return False, "User not found"

def change_password(username, new_password):
    db = _load_db()
    if username in db:
        db[username]["password"] = hash_password(new_password)
        _save_db(db)
        return True, "Password updated successfully"
    return False, "User not found"

def has_pair_access(username, pair_name):
    # Backward compatibility if needed, though we filter in UI now
    return True
