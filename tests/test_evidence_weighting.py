"""Tests for evidence-strength-weighted skill matching."""
from __future__ import annotations

from job_apply import profile_loader
from job_apply.job_analyzer import (
    build_skill_strength_index, evidence_weighted_match,
)


def _profile(data: dict) -> profile_loader.Profile:
    return profile_loader.Profile(data=data)


def test_internship_bullet_skill_is_full_strength():
    p = _profile({
        "experience": [{
            "id": "intern", "company": "Acme", "title": "Intern",
            "role_type": "internship",
            "bullets": [{
                "id": "intern.b1", "text": "...",
                "skills_demonstrated": ["Python", "SAST"],
            }],
        }],
        "skills": {},
    })
    weights = build_skill_strength_index(p)
    assert weights.get("python") == 1.00
    assert weights.get("sast") == 1.00


def test_certification_lab_strength_for_cert_name():
    p = _profile({
        "experience": [],
        "certifications": [{"id": "secplus", "name": "CompTIA Security+"}],
        "skills": {},
    })
    weights = build_skill_strength_index(p)
    assert weights.get("comptia security+") == 0.65


def test_project_with_evidence_strength_moderate():
    p = _profile({
        "experience": [],
        "projects": [{
            "id": "proj_x", "skills": ["Phishing analysis"],
            "evidence_strength": "moderate",
        }],
        "skills": {},
    })
    weights = build_skill_strength_index(p)
    assert weights.get("phishing analysis") == 0.70


def test_project_with_evidence_strength_strong():
    p = _profile({
        "experience": [],
        "projects": [{
            "id": "proj_x", "skills": ["GitLab SAST"],
            "evidence_strength": "strong",
        }],
        "skills": {},
    })
    weights = build_skill_strength_index(p)
    assert weights.get("gitlab sast") == 0.95


def test_flat_skill_only_lowest_weight():
    p = _profile({
        "experience": [],
        "skills": {"technical": ["Python", "Linux"]},
    })
    weights = build_skill_strength_index(p)
    assert weights.get("python") == 0.60
    assert weights.get("linux") == 0.60


def test_max_across_sources_wins():
    """A skill listed in both an internship bullet AND a flat block should use
    the internship strength (1.0), not the flat strength (0.6)."""
    p = _profile({
        "experience": [{
            "id": "intern", "role_type": "internship",
            "bullets": [{"id": "intern.b1", "skills_demonstrated": ["Python"]}],
        }],
        "skills": {"technical": ["Python"]},
    })
    weights = build_skill_strength_index(p)
    assert weights.get("python") == 1.00


def test_self_directed_project_with_artifact_bumped():
    """Project with artifacts should reach self-directed-project strength
    even if no explicit evidence_strength was set."""
    p = _profile({
        "experience": [],
        "projects": [{
            "id": "proj_x", "skills": ["Python"],
            "artifacts": ["~/repos/x"],
            # no evidence_strength — relies on artifacts bump
        }],
        "skills": {},
    })
    weights = build_skill_strength_index(p)
    assert weights.get("python") == 0.85


def test_evidence_weighted_match_uses_strength():
    p = _profile({
        "experience": [{
            "id": "intern", "role_type": "internship",
            "bullets": [{"id": "intern.b1", "skills_demonstrated": ["GitLab SAST"]}],
        }],
        "projects": [{
            "id": "proj_x", "skills": ["Phishing recognition (lab)"],
            "evidence_strength": "moderate",
        }],
        "skills": {},
    })
    weights = build_skill_strength_index(p)
    # Direct match against an internship-strength skill
    assert evidence_weighted_match("GitLab SAST", weights, []) == 1.00
    # Direct match against a moderate-strength project skill
    assert abs(evidence_weighted_match("phishing recognition", weights, []) - 0.70) < 1e-9
    # No match
    assert evidence_weighted_match("Kubernetes operator", weights, []) == 0.00


def test_synonym_path_inherits_strength():
    """Synonym match should pull through the supporting skill's weight."""
    p = _profile({
        "experience": [{
            "id": "intern", "role_type": "internship",
            "bullets": [{"id": "intern.b1", "skills_demonstrated": ["Graylog"]}],
        }],
        "skills": {},
    })
    weights = build_skill_strength_index(p)
    clusters = [["siem", "graylog", "splunk", "opensearch"]]
    # JD asks for SIEM; profile has Graylog with internship strength.
    score = evidence_weighted_match("SIEM", weights, clusters)
    assert score == 1.00


def test_certification_lab_role_type_weight():
    """role_type='certification_lab' on an experience entry uses the explicit weight."""
    p = _profile({
        "experience": [{
            "id": "secplus_lab", "role_type": "certification_lab",
            "bullets": [{"id": "secplus_lab.b1", "skills_demonstrated": ["CIA triad"]}],
        }],
        "skills": {},
    })
    weights = build_skill_strength_index(p)
    assert weights.get("cia triad") == 0.65


def test_empty_profile_returns_empty_index():
    p = _profile({"experience": [], "skills": {}})
    assert build_skill_strength_index(p) == {}


def test_unknown_role_type_gets_midtier_default():
    p = _profile({
        "experience": [{
            "id": "x", "role_type": "totally_made_up",
            "bullets": [{"id": "x.b1", "skills_demonstrated": ["Python"]}],
        }],
        "skills": {},
    })
    weights = build_skill_strength_index(p)
    # Unknown role_type falls back to 0.75 (mid-tier)
    assert weights.get("python") == 0.75
