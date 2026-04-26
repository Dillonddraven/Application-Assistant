"""Paths and environment loading.

Env order (later wins): ~/.openclaw/.env, then ./.env if present, then real
environment. We use setdefault semantics so a value already in os.environ wins
over file values — that lets tests inject keys cleanly.
"""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

PROFILE_DIR = ROOT / "profile"
PROFILE_PATH = PROFILE_DIR / "master_profile.yaml"
SECRETS_PATH = PROFILE_DIR / "secrets.yaml"
SAMPLE_PROFILE_PATH = PROFILE_DIR / "samples" / "master_profile.example.yaml"
SAMPLE_SECRETS_PATH = PROFILE_DIR / "samples" / "secrets.example.yaml"

JOBS_DIR = ROOT / "jobs"
RAW_POSTS_DIR = JOBS_DIR / "raw_posts"
ANALYZED_DIR = JOBS_DIR / "analyzed"
INPUT_URLS_FILE = JOBS_DIR / "input_urls.txt"

OUTPUTS_DIR = ROOT / "outputs"

OPENCLAW_ENV = Path.home() / ".openclaw" / ".env"
LOCAL_ENV = ROOT / ".env"


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if "=" not in s:
            continue
        key, _, val = s.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        # First file to set a key wins; existing env wins over both.
        os.environ.setdefault(key, val)


_loaded = False


def load_env() -> None:
    """Idempotently load env vars from the openclaw + local .env files."""
    global _loaded
    if _loaded:
        return
    _load_env_file(OPENCLAW_ENV)
    _load_env_file(LOCAL_ENV)
    _loaded = True


def ensure_dirs() -> None:
    for d in (RAW_POSTS_DIR, ANALYZED_DIR, OUTPUTS_DIR):
        d.mkdir(parents=True, exist_ok=True)
