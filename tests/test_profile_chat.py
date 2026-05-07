"""Tests for the chat-driven profile-update layer.

We don't call the LLM here -- propose_patch() is exercised via mocked
LLMClient. The bulk of the tests cover validate_patch() (the truth-safe
gatekeeper) and apply_patch() (deterministic merge logic)."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from job_apply.profile_chat import (
    ProfilePatch, apply_patch, propose_patch, validate_patch,
)


def _profile_with_dillards():
    return {
        "experience": [
            {"id": "dillards_intern", "company": "Dillard's",
             "title": "InfoSec Intern", "bullets": []},
        ],
        "projects": [],
        "certifications": [],
        "skills": {"technical": ["Python"], "security": []},
        "preferences": {
            "target_roles": ["SOC Analyst"],
            "locations": ["Tulsa, OK"],
            "industries_avoid": [],
        },
    }


# -------- validation: hard rules --------

def test_rejects_unknown_action():
    p = ProfilePatch(action="add_password", data={}, verbatim_quote="x")
    errs = validate_patch(p, "x", _profile_with_dillards())
    assert any("unknown action" in e for e in errs)


def test_no_change_skips_quote_check():
    p = ProfilePatch(action="no_change")
    errs = validate_patch(p, "hello", _profile_with_dillards())
    assert errs == []


def test_rejects_missing_verbatim_quote():
    p = ProfilePatch(action="add_project",
                      data={"name": "X", "description": "y"},
                      verbatim_quote="")
    errs = validate_patch(p, "I built X", _profile_with_dillards())
    assert any("verbatim_quote is required" in e for e in errs)


def test_rejects_quote_not_in_message():
    p = ProfilePatch(action="add_project",
                      data={"name": "X", "description": "y"},
                      verbatim_quote="something the user did NOT say")
    errs = validate_patch(p, "I built X", _profile_with_dillards())
    assert any("not a substring" in e for e in errs)


def test_quote_match_is_case_insensitive_and_whitespace_normalized():
    p = ProfilePatch(
        action="add_project",
        data={"name": "X", "description": "y"},
        verbatim_quote="MALWARE\n  analysis  lab",
    )
    errs = validate_patch(p, "I did a malware analysis lab in CYBR 4123",
                           _profile_with_dillards())
    # Should NOT complain about the quote
    quote_errs = [e for e in errs if "substring" in e]
    assert quote_errs == []


# -------- truth-safe: numeric / specific claims must come from user --------

def test_rejects_invented_percentage():
    p = ProfilePatch(
        action="add_project",
        data={"name": "Phishing lab",
               "description": "Reduced false positives by 40%"},
        verbatim_quote="phishing lab",
    )
    errs = validate_patch(p, "I did a phishing lab in CYBR 4123",
                           _profile_with_dillards())
    assert any("40%" in e and "refusing" in e for e in errs)


def test_rejects_invented_duration():
    p = ProfilePatch(
        action="add_experience",
        data={"company": "Acme", "title": "Intern",
               "role_type": "internship",
               "summary": "Worked there for 2 years on detection."},
        verbatim_quote="acme",
    )
    errs = validate_patch(p, "I worked at Acme one summer",
                           _profile_with_dillards())
    assert any("2 years" in e for e in errs)


def test_accepts_numeric_when_user_did_state_it():
    p = ProfilePatch(
        action="add_experience",
        data={"company": "Acme", "title": "Intern",
               "role_type": "internship",
               "summary": "Three months on detection."},
        verbatim_quote="three months",
    )
    errs = validate_patch(
        p, "I interned at Acme for 3 months on detection. Three months total.",
        _profile_with_dillards())
    assert all("refusing" not in e for e in errs), errs


# -------- action-specific rules --------

def test_add_bullet_requires_existing_experience_id():
    p = ProfilePatch(
        action="add_bullet", target_id="nonexistent",
        data={"target_experience_id": "nonexistent", "text": "I did a thing"},
        verbatim_quote="I did a thing",
    )
    errs = validate_patch(p, "I did a thing at Dillard's",
                           _profile_with_dillards())
    assert any("not found in profile" in e for e in errs)


def test_add_bullet_with_existing_experience_id_validates():
    p = ProfilePatch(
        action="add_bullet", target_id="dillards_intern",
        data={"target_experience_id": "dillards_intern",
               "text": "Reviewed audit evidence with the team."},
        verbatim_quote="reviewed audit evidence",
    )
    errs = validate_patch(p, "I also reviewed audit evidence with the team",
                           _profile_with_dillards())
    assert errs == []


def test_add_skill_requires_known_category():
    p = ProfilePatch(
        action="add_skill",
        data={"category": "magic", "value": "telepathy"},
        verbatim_quote="telepathy",
    )
    errs = validate_patch(p, "telepathy", _profile_with_dillards())
    assert any("category" in e for e in errs)


def test_edit_field_requires_whitelisted_path():
    p = ProfilePatch(
        action="edit_field",
        data={"path": "identity.full_name", "value": "Imposter"},
        verbatim_quote="i am imposter",
    )
    errs = validate_patch(p, "i am imposter", _profile_with_dillards())
    assert any("editable whitelist" in e for e in errs)


def test_edit_field_target_roles_passes():
    p = ProfilePatch(
        action="edit_field",
        data={"path": "preferences.target_roles",
               "op": "append",
               "value": ["Threat Hunter"]},
        verbatim_quote="threat hunter",
    )
    errs = validate_patch(p, "Add Threat Hunter to my target roles",
                           _profile_with_dillards())
    assert errs == []


# -------- apply_patch: deterministic merge --------

def test_apply_add_project():
    profile = _profile_with_dillards()
    p = ProfilePatch(action="add_project",
                      data={"name": "Phishing lab",
                            "description": "Coursework lab covering analysis."},
                      verbatim_quote="phishing lab")
    out = apply_patch(profile, p)
    assert out["projects"][0]["name"] == "Phishing lab"
    assert out["projects"][0]["id"].startswith("proj_chat_")
    # original profile NOT mutated
    assert profile["projects"] == []


def test_apply_add_experience_assigns_id_and_empty_bullets():
    profile = _profile_with_dillards()
    p = ProfilePatch(
        action="add_experience",
        data={"company": "Acme", "title": "Intern",
               "role_type": "internship", "summary": "Three months."},
        verbatim_quote="three months",
    )
    out = apply_patch(profile, p)
    new = out["experience"][1]
    assert new["company"] == "Acme"
    assert new["id"].startswith("exp_chat_")
    assert new["bullets"] == []


def test_apply_add_bullet_to_existing_experience():
    profile = _profile_with_dillards()
    p = ProfilePatch(
        action="add_bullet", target_id="dillards_intern",
        data={"target_experience_id": "dillards_intern",
               "text": "Reviewed audit evidence."},
        verbatim_quote="reviewed audit evidence",
    )
    out = apply_patch(profile, p)
    bullets = out["experience"][0]["bullets"]
    assert len(bullets) == 1
    assert bullets[0]["text"] == "Reviewed audit evidence."
    assert bullets[0]["id"] == "dillards_intern.b1"


def test_apply_add_skill_dedupes():
    profile = _profile_with_dillards()
    p = ProfilePatch(
        action="add_skill",
        data={"category": "technical", "value": "Python"},
        verbatim_quote="python",
    )
    out = apply_patch(profile, p)
    assert out["skills"]["technical"] == ["Python"]   # not duplicated


def test_apply_edit_field_append():
    profile = _profile_with_dillards()
    p = ProfilePatch(
        action="edit_field",
        data={"path": "preferences.target_roles",
               "op": "append", "value": ["Threat Hunter"]},
        verbatim_quote="threat hunter",
    )
    out = apply_patch(profile, p)
    assert "Threat Hunter" in out["preferences"]["target_roles"]
    assert "SOC Analyst" in out["preferences"]["target_roles"]


def test_apply_edit_field_remove():
    profile = _profile_with_dillards()
    p = ProfilePatch(
        action="edit_field",
        data={"path": "preferences.target_roles",
               "op": "remove", "value": "SOC Analyst"},
        verbatim_quote="soc analyst",
    )
    out = apply_patch(profile, p)
    assert "SOC Analyst" not in out["preferences"]["target_roles"]


def test_apply_no_change_returns_unchanged_copy():
    profile = _profile_with_dillards()
    p = ProfilePatch(action="no_change")
    out = apply_patch(profile, p)
    assert out == profile
    assert out is not profile


# -------- propose_patch: LLM is mocked --------

def test_propose_patch_round_trip(monkeypatch):
    fake_resp = MagicMock()
    fake_resp.as_json.return_value = {
        "action": "add_project",
        "data": {"name": "Phishing lab",
                  "description": "Coursework lab covering analysis."},
        "verbatim_quote": "phishing lab",
        "reasoning": "User mentioned a new project.",
        "target_id": None,
    }
    fake_client = MagicMock()
    fake_client.complete.return_value = fake_resp
    patch = propose_patch(
        user_message="I forgot a phishing lab from CYBR 4123",
        profile_yaml="experience: []",
        client=fake_client,
    )
    assert patch.action == "add_project"
    assert patch.verbatim_quote == "phishing lab"
    fake_client.complete.assert_called_once()
    kwargs = fake_client.complete.call_args.kwargs
    assert kwargs["json_mode"] is True
    assert kwargs["tier"] == "extract"
