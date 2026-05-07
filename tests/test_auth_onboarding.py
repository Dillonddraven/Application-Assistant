"""Tests for the multi-user web layer: auth + onboarding + JOB_APPLY_ROOT
override. No Streamlit involvement (Streamlit testing is heavyweight)."""
from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

from job_apply.ui import auth, onboarding


@pytest.fixture
def users_root(tmp_path, monkeypatch):
    monkeypatch.setenv("JOB_APPLY_USERS_ROOT", str(tmp_path / "users"))
    return tmp_path / "users"


# ---------- auth ----------

def test_signup_creates_user_and_dir(users_root):
    user = auth.signup("alice", "password1234")
    assert user.username == "alice"
    assert (users_root / "_users.json").exists()
    assert (users_root / "alice").exists()
    assert (users_root / "alice" / "profile").exists()


def test_signup_normalizes_username_to_lowercase(users_root):
    user = auth.signup("Alice", "password1234")
    assert user.username == "alice"


def test_signup_rejects_invalid_username(users_root):
    for bad in ("ab", "xx" * 20, "Has Space", "with.dot", "1!@", "_leading"):
        with pytest.raises(ValueError, match="Username"):
            auth.signup(bad, "password1234")


def test_signup_rejects_short_password(users_root):
    with pytest.raises(ValueError, match="Password"):
        auth.signup("alice", "short")


def test_signup_rejects_duplicate_username(users_root):
    auth.signup("alice", "password1234")
    with pytest.raises(ValueError, match="already exists"):
        auth.signup("alice", "password5678")


def test_login_succeeds_with_correct_password(users_root):
    auth.signup("alice", "password1234")
    user = auth.login("alice", "password1234")
    assert user.username == "alice"
    assert user.last_login is not None


def test_login_fails_with_wrong_password(users_root):
    auth.signup("alice", "password1234")
    with pytest.raises(ValueError, match="Invalid"):
        auth.login("alice", "wrongpassword")


def test_login_fails_with_unknown_username(users_root):
    with pytest.raises(ValueError, match="Invalid"):
        auth.login("nobody", "password1234")


def test_password_is_bcrypt_hashed(users_root):
    """Spot-check: never store plaintext."""
    auth.signup("alice", "password1234")
    raw = (users_root / "_users.json").read_text()
    assert "password1234" not in raw
    assert "$2b$" in raw   # bcrypt prefix


def test_user_dir_resolves_under_users_root(users_root):
    auth.signup("alice", "password1234")
    assert auth.user_dir("alice").resolve() == (users_root / "alice").resolve()


def test_has_profile_returns_false_until_onboarding(users_root):
    auth.signup("alice", "password1234")
    assert auth.has_profile("alice") is False


def test_session_token_is_unique():
    a, b = auth.issue_session_token(), auth.issue_session_token()
    assert a != b
    assert len(a) >= 32


# ---------- onboarding ----------

def test_to_profile_yaml_round_trip():
    a = onboarding.OnboardingAnswers(
        full_name="Jane Doe", email="jane@example.com",
        phone="555-1234", address_city="Tulsa", address_state="OK",
        schools=[{"id": "edu_1", "school": "TU", "degree": "BS CIS",
                  "status": "in_progress", "start": "2022-08",
                  "expected_end": "2026-05"}],
        certifications=[{"id": "cert_1", "name": "CompTIA Security+",
                          "issued": "2025-12"}],
        most_recent_role_company="Dillard's",
        most_recent_role_title="Information Security Intern",
        most_recent_role_summary="PCI audit support and SAST.",
        most_recent_role_start="2025-05",
        most_recent_role_end="2025-08",
        most_recent_role_type="internship",
        technical_skills=["Python", "Linux"],
        security_skills=["Vulnerability management"],
        target_roles=["Cybersecurity Analyst", "GRC Analyst"],
        workplace_modes=["remote", "hybrid", "in-person"],
        locations=["Tulsa, OK"],
        willing_to_relocate=True,
        industries_avoid=["military", "defense"],
    )
    text = onboarding.to_profile_yaml(a)
    parsed = yaml.safe_load(text)
    assert parsed["identity"]["full_name"] == "Jane Doe"
    assert parsed["identity"]["citizenship"] == "US Citizen"
    # PII fields are NOT in the profile (they go to secrets.yaml)
    assert "phone" not in parsed["identity"]
    assert "email" not in parsed["identity"]
    assert parsed["education"][0]["school"] == "TU"
    assert parsed["education"][0]["status"] == "in_progress"
    assert parsed["certifications"][0]["name"] == "CompTIA Security+"
    assert parsed["experience"][0]["company"] == "Dillard's"
    assert parsed["experience"][0]["role_type"] == "internship"
    assert "Python" in parsed["skills"]["technical"]
    assert "Cybersecurity Analyst" in parsed["preferences"]["target_roles"]
    assert parsed["preferences"]["remote_ok"] is True
    assert parsed["preferences"]["hybrid_ok"] is True
    assert parsed["preferences"]["onsite_ok"] is True
    assert parsed["preferences"]["industries_avoid"] == ["military", "defense"]
    assert parsed["preferences"]["visa_sponsorship_needed"] is False


def test_to_secrets_yaml_only_pii():
    a = onboarding.OnboardingAnswers(
        full_name="Jane Doe", email="jane@example.com",
        phone="555-1234", linkedin_url="https://linkedin.com/in/jane")
    text = onboarding.to_secrets_yaml(a)
    parsed = yaml.safe_load(text)
    assert parsed["email"] == "jane@example.com"
    assert parsed["phone"] == "555-1234"
    assert parsed["linkedin_url"] == "https://linkedin.com/in/jane"
    # Career data does NOT leak into secrets.yaml
    assert "full_name" not in parsed
    assert "target_roles" not in parsed


def test_to_secrets_yaml_drops_empty_fields():
    a = onboarding.OnboardingAnswers(email="jane@example.com")
    parsed = yaml.safe_load(onboarding.to_secrets_yaml(a))
    assert list(parsed.keys()) == ["email"]


def test_write_profile_creates_files(users_root):
    auth.signup("alice", "password1234")
    a = onboarding.OnboardingAnswers(
        full_name="Alice", email="alice@example.com",
        target_roles=["Cybersecurity Analyst"])
    pp, sp = onboarding.write_profile(auth.user_dir("alice"), a)
    assert pp.exists() and sp.exists()
    assert auth.has_profile("alice") is True


# ---------- JOB_APPLY_ROOT override ----------

def test_job_apply_root_env_overrides_config_root(tmp_path, monkeypatch):
    """When JOB_APPLY_ROOT is set, config.ROOT should resolve to it.
    Importing config fresh inside the patched env exercises the resolver."""
    target = tmp_path / "user_alice"
    target.mkdir()
    monkeypatch.setenv("JOB_APPLY_ROOT", str(target))
    # Force re-evaluation of config module's path constants
    import importlib
    import job_apply.config as cfg
    importlib.reload(cfg)
    try:
        assert cfg.ROOT == target.resolve()
        assert cfg.PROFILE_PATH == target.resolve() / "profile" / "master_profile.yaml"
        assert cfg.OUTPUTS_DIR == target.resolve() / "outputs"
    finally:
        # Restore for other tests in the run
        monkeypatch.delenv("JOB_APPLY_ROOT", raising=False)
        importlib.reload(cfg)
