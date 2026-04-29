"""Tests for the JD analysis pre-pass."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from job_apply import jd_analysis, llm_client, profile_loader


PROFILE = {
    "identity": {"full_name": "T", "citizenship": "US", "work_auth": "yes"},
    "education": [{"id": "x", "school": "X", "degree": "BA CIS", "status": "in_progress"}],
    "preferences": {"target_roles": ["Security Analyst"], "industries_avoid": []},
}

ANALYZED = {
    "company": "Acme", "title": "Security Analyst",
    "required_skills": ["Python"], "preferred_skills": [],
    "responsibilities": ["Monitor logs", "Respond to incidents"],
    "required_certifications": [], "min_years_experience": 0,
    "remote_mode": "hybrid", "location": "Tulsa, OK",
}

CANNED_ANALYSIS = {
    "pain_points": [
        {
            "text": "Translating raw security signals into actionable reports for stakeholders",
            "jd_anchor": "Monitor logs",
            "stakes": "Without it the team drowns in alerts and never prioritizes",
        },
        {
            "text": "Responding to security incidents under time pressure",
            "jd_anchor": "Respond to incidents",
            "stakes": "Slow response = bigger blast radius",
        },
    ],
    "evidence_map": [
        {"pain_point_index": 0, "candidate_evidence": [
            {"source_id": "experience.dillards_intern.b1",
             "summary": "Built SAST reporting", "match_strength": "strong"},
        ]},
        {"pain_point_index": 1, "candidate_evidence": [
            {"source_id": "projects.proj_ir_playbook",
             "summary": "IR playbook from BIA", "match_strength": "adjacent"},
        ]},
    ],
    "missing_evidence": [],
}


class FakeLLM:
    def __init__(self, payload: dict):
        self.payload = payload
        self.calls: list[dict] = []

    def complete(self, *, tier, system, user, json_mode=False, temperature=0.4):  # noqa: ARG002
        self.calls.append({"tier": tier, "system": system[:60], "user_len": len(user)})
        return llm_client.LLMResponse(text=json.dumps(self.payload), model="test-extract")


def test_analyze_jd_returns_normalized_dict(workspace: Path):
    (workspace / "profile" / "master_profile.yaml").write_text(yaml.safe_dump(PROFILE))
    profile = profile_loader.load_profile()
    fake = FakeLLM(CANNED_ANALYSIS)
    result = jd_analysis.analyze_jd(
        profile=profile, analyzed=ANALYZED, job_text="raw posting text", llm=fake,
    )
    assert len(result["pain_points"]) == 2
    assert len(result["evidence_map"]) == 2
    assert result["missing_evidence"] == []
    assert result["prompt_version"] == "extract_jd_analysis@v1"
    assert fake.calls[0]["tier"] == "extract"


def test_render_for_prompt_includes_pain_points_and_evidence():
    rendered = jd_analysis.render_for_prompt(CANNED_ANALYSIS)
    assert "Translating raw security signals" in rendered
    assert "Monitor logs" in rendered      # jd_anchor surfaced
    assert "experience.dillards_intern.b1" in rendered
    assert "(strong)" in rendered
    assert "(adjacent)" in rendered


def test_render_for_prompt_lists_missing_evidence():
    analysis = {**CANNED_ANALYSIS, "missing_evidence": [
        {"pain_point_index": 1, "note": "no incident response evidence"},
    ]}
    rendered = jd_analysis.render_for_prompt(analysis)
    assert "Pain points to leave OUT" in rendered
    assert "no incident response evidence" in rendered


def test_render_for_prompt_empty():
    assert jd_analysis.render_for_prompt({}) == ""
    assert jd_analysis.render_for_prompt({"pain_points": []}) == ""


def test_render_flags_missing_evidence_for_pain_point_with_no_map():
    """A pain point with no evidence_map entry should show '(none mapped — DO NOT claim)'."""
    analysis = {
        "pain_points": [{"text": "Phishing analysis", "jd_anchor": "phishing"}],
        "evidence_map": [],
        "missing_evidence": [],
    }
    rendered = jd_analysis.render_for_prompt(analysis)
    assert "(none mapped" in rendered
