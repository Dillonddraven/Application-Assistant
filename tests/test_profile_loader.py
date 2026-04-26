from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from job_apply import profile_loader as pl


def _good_profile() -> dict:
    return {
        "identity": {
            "full_name": "Test User",
            "citizenship": "US Citizen",
            "work_auth": "Authorized to work in the US",
        },
        "education": [
            {"id": "bs_cis", "school": "X", "degree": "BA CIS", "status": "in_progress"},
        ],
        "preferences": {
            "target_roles": ["Security Analyst"],
            "industries_avoid": ["military"],
        },
    }


def test_load_missing_profile_raises(workspace: Path):
    with pytest.raises(pl.ProfileError, match="profile not found"):
        pl.load_profile()


def test_load_valid_profile(workspace: Path):
    p = workspace / "profile" / "master_profile.yaml"
    p.write_text(yaml.safe_dump(_good_profile()))
    prof = pl.load_profile()
    assert prof.full_name == "Test User"
    assert prof.industries_avoid == ["military"]


def test_top_level_pii_rejected(workspace: Path):
    bad = _good_profile()
    bad["phone"] = "555-1234"
    (workspace / "profile" / "master_profile.yaml").write_text(yaml.safe_dump(bad))
    with pytest.raises(pl.ProfileError, match="forbidden PII"):
        pl.load_profile()


def test_nested_pii_rejected(workspace: Path):
    bad = _good_profile()
    bad["identity"]["address"] = {"street": "1 Main"}
    (workspace / "profile" / "master_profile.yaml").write_text(yaml.safe_dump(bad))
    with pytest.raises(pl.ProfileError, match="forbidden PII"):
        pl.load_profile()


def test_birthday_rejected(workspace: Path):
    bad = _good_profile()
    bad["identity"]["birthday"] = "1999-01-01"
    (workspace / "profile" / "master_profile.yaml").write_text(yaml.safe_dump(bad))
    with pytest.raises(pl.ProfileError, match="forbidden PII"):
        pl.load_profile()


def test_required_keys_enforced(workspace: Path):
    bad = {"identity": {"full_name": "X"}}  # no preferences
    (workspace / "profile" / "master_profile.yaml").write_text(yaml.safe_dump(bad))
    with pytest.raises(pl.ProfileError, match="missing required"):
        pl.load_profile()


def test_secrets_optional(workspace: Path):
    s = pl.load_secrets()
    assert s.data == {}


def test_secrets_placeholder_map(workspace: Path):
    p = workspace / "profile" / "secrets.yaml"
    p.write_text(yaml.safe_dump({
        "email": "u@example.com",
        "phone": "555-1234",
        "address": {"street": "1 Main", "city": "Tulsa", "state": "OK", "zip": "74000"},
        "linkedin_url": "https://linkedin.com/in/u",
    }))
    s = pl.load_secrets()
    m = s.placeholder_map()
    assert m["{{email}}"] == "u@example.com"
    assert m["{{phone}}"] == "555-1234"
    assert m["{{address_city}}"] == "Tulsa"
    assert "{{linkedin_url}}" in m
    # Empty values are dropped
    assert "{{github_url}}" not in m


def test_secrets_values_for_grep(workspace: Path):
    p = workspace / "profile" / "secrets.yaml"
    p.write_text(yaml.safe_dump({
        "email": "u@example.com",
        "phone": "555-1234",
        "address": {"street": "1 Main"},
    }))
    s = pl.load_secrets()
    vals = s.values_for_grep()
    assert "u@example.com" in vals
    assert "555-1234" in vals
    assert "1 Main" in vals
