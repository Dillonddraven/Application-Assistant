"""Simple bcrypt-hashed user store for the multi-user web UI.

User records are kept in `users/_users.json`. Each user gets a per-user
data dir at `users/<username>/` containing profile/, jobs/, outputs/,
applications.xlsx, etc. -- the same layout the CLI uses, just rooted
at the user's dir via the JOB_APPLY_ROOT env var.

This is NOT enterprise-grade auth. It's a thin slice for hosting the
service for a small group of friends. Don't use it for sensitive data
or expose it widely without a real auth layer.
"""
from __future__ import annotations

import json
import os
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import bcrypt


# users root is configurable so tests + multi-tenant deploys can override.
def users_root() -> Path:
    p = os.environ.get("JOB_APPLY_USERS_ROOT")
    if p:
        return Path(p).resolve()
    # Default: <repo_root>/users  (gitignored)
    repo_root = Path(__file__).resolve().parents[3]
    return repo_root / "users"


def _users_file() -> Path:
    return users_root() / "_users.json"


# Username constraints: keep it filesystem-safe (we use it as a dir name).
USERNAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{2,30}$")


@dataclass
class User:
    username: str
    created_at: str
    last_login: str | None = None


# --- store ---

def _read_store() -> dict:
    f = _users_file()
    if not f.exists():
        return {}
    return json.loads(f.read_text(encoding="utf-8"))


def _write_store(data: dict) -> None:
    root = users_root()
    root.mkdir(parents=True, exist_ok=True)
    f = _users_file()
    f.write_text(json.dumps(data, indent=2), encoding="utf-8")


# --- public API ---

def list_users() -> list[str]:
    return sorted(_read_store().keys())


def signup(username: str, password: str) -> User:
    """Create a new user. Raises ValueError if username invalid or taken,
    or password too short."""
    username = (username or "").strip().lower()
    if not USERNAME_RE.match(username):
        raise ValueError(
            "Username must be 3-31 chars: lowercase letters, digits, "
            "underscore, or hyphen. Must start with a letter or digit."
        )
    if len(password or "") < 8:
        raise ValueError("Password must be at least 8 characters.")
    store = _read_store()
    if username in store:
        raise ValueError(f"User {username!r} already exists. Try logging in.")
    pw_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    store[username] = {
        "password_hash": pw_hash.decode("utf-8"),
        "created_at": now,
        "last_login": None,
    }
    _write_store(store)
    # Pre-create the user's data dir
    user_dir(username).mkdir(parents=True, exist_ok=True)
    (user_dir(username) / "profile").mkdir(parents=True, exist_ok=True)
    return User(username=username, created_at=now)


def login(username: str, password: str) -> User:
    """Verify credentials. Raises ValueError on bad credentials. Returns
    the User record on success and updates last_login."""
    username = (username or "").strip().lower()
    store = _read_store()
    rec = store.get(username)
    if not rec:
        raise ValueError("Invalid username or password.")
    pw_hash = rec["password_hash"].encode("utf-8")
    if not bcrypt.checkpw((password or "").encode("utf-8"), pw_hash):
        raise ValueError("Invalid username or password.")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rec["last_login"] = now
    _write_store(store)
    return User(username=username, created_at=rec["created_at"],
                 last_login=now)


def user_dir(username: str) -> Path:
    """Per-user data root. Used as JOB_APPLY_ROOT for that session."""
    return users_root() / username


def has_profile(username: str) -> bool:
    return (user_dir(username) / "profile" / "master_profile.yaml").exists()


def issue_session_token() -> str:
    """Random token used as a server-side session id (kept in
    Streamlit's per-session state). Never sent to disk."""
    return secrets.token_urlsafe(32)
