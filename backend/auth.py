import hashlib
import json
from typing import Optional
from pathlib import Path

USERS_FILE = Path("backend/users.json")

def hash_password(password: str) -> str:
    """Hash password using SHA-256 (simple auth)"""
    return hashlib.sha256(password.encode()).hexdigest()

def init_users_file():
    """Create users file if not exists"""
    if not USERS_FILE.exists():
        USERS_FILE.write_text(json.dumps({}))

def verify_user(username: str, password: str) -> bool:
    """Verify user credentials"""
    init_users_file()
    users = json.loads(USERS_FILE.read_text())

    if username not in users:
        return False

    return users[username] == hash_password(password)

def add_user(username: str, password: str) -> bool:
    """Add new user (returns False if exists)"""
    init_users_file()
    users = json.loads(USERS_FILE.read_text())

    if username in users:
        return False

    users[username] = hash_password(password)
    USERS_FILE.write_text(json.dumps(users, indent=2))
    return True