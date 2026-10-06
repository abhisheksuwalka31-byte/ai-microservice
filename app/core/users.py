"""
In-memory user store for demo purposes.
In production, replace with a real database (PostgreSQL via SQLAlchemy, etc.)
"""
from typing import Dict, Optional
from datetime import datetime, timezone
from app.core.security import get_password_hash, verify_password

# Schema: {username: {id, username, email, hashed_password, created_at}}
_USERS: Dict[str, dict] = {}
_ID_COUNTER = {"val": 0}


def _next_id() -> int:
    _ID_COUNTER["val"] += 1
    return _ID_COUNTER["val"]


def create_user(username: str, email: str, password: str) -> dict:
    if username in _USERS:
        return None
    user = {
        "id": _next_id(),
        "username": username,
        "email": email,
        "hashed_password": get_password_hash(password),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    _USERS[username] = user
    return user


def get_user_by_username(username: str) -> Optional[dict]:
    return _USERS.get(username)


def get_user_by_id(user_id: int) -> Optional[dict]:
    for u in _USERS.values():
        if u["id"] == user_id:
            return u
    return None


def authenticate_user(username: str, password: str) -> Optional[dict]:
    user = get_user_by_username(username)
    if not user:
        return None
    if not verify_password(password, user["hashed_password"]):
        return None
    return user
