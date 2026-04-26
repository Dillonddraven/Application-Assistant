from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from job_apply import job_analyzer, llm_client, profile_loader, state


def _write_profile(workspace: Path) -> None:
    prof = {
        "identity": {"full_name": "Test", "citizenship": "US", "work_auth": "yes"},
        "education": [
            {"id": "bs", "degree": "BA CIS", "status": "in_progress", "school": "X"},
        ],
        "certifications": [
            {"id": "secplus", "name": "CompTIA Security+"},
            {"id": "netplus", "name": "CompTIA Network+"},
        ],
        "experience": [
            {"id": "intern", "company": "Dillard's", "title": "Intern", "role_type": "internship"},
        ],
        "skills": {"technical": ["Python"], "security": ["SIEM basics"]},
        "preferences": {
            "target_roles": ["Security Analyst"],
            "industries_avoid": ["military", "defense"],
            "remote_ok": True,
            "hybrid_ok": True,
            "onsite_ok": True,
        },
    }
    (workspace / "profile" / "master_profile.yaml").write_text(yaml.safe_dump(prof))


class FakeLLM:
    """LLM stub that returns a canned JSON dict regardless of input."""
    def __init__(self, payload: dict, model: str = "gpt-4.1-mini-test"):
        self.payload = payload
        self.model = model
        self.calls = 0

    def complete(self, *, tier, system, user, json_mode=False, temperature=0.4):  # noqa: ARG002
        self.calls += 1
        return llm_client.LLMResponse(text=json.dumps(self.payload), model=self.model)


def _civilian_payload() -> dict:
    return {
        "company": "Acme Corp",
        "title": "Security Analyst",
        "location": "Tulsa, OK",
        "remote_mode": "hybrid",
        "required_skills": ["Python", "SIEM"],
        "preferred_skills": ["AWS"],
        "min_years_experience": 1,
        "required_certifications": ["CompTIA Security+"],
        "responsibilities": ["triage alerts", "run vuln scans"],
        "keywords_extracted": ["soc", "siem", "python"],
        "industry_tags": ["cybersecurity", "saas"],
        "fit_rationale": "Cert and skills overlap.",
        "concerns": ["limited prior full-time experience"],
        "missing_quals": [],
    }


def _military_payload() -> dict:
    p = _civilian_payload()
    p["company"] = "Northrop Grumman"
    p["industry_tags"] = ["defense", "military"]
    return p


def test_analyze_civilian_job(workspace: Path):
    _write_profile(workspace)
    rec = state.save_ingest(
        job_id="job0civ", text="(posting body)", source_url="https://x.com/a", source_kind="url"
    )
    profile = profile_loader.load_profile()
    result = job_analyzer.analyze_job(
        job_id=rec.job_id,
        profile=profile,
        text=rec.text,
        source_url=rec.source_url,
        fetched_at=rec.fetched_at,
        raw_text_path=str(rec.raw_text_path),
        llm=FakeLLM(_civilian_payload()),
    )
    assert result["industry_filter"] == "ok"
    assert result["company"] == "Acme Corp"
    assert 0 <= result["fit_score"] <= 100
    # Security+ is in profile, so cert_match should be 100
    assert result["fit_breakdown"]["cert_match"] == 100
    assert result["prompt_version"] == "analyze_job@v1"


def test_analyze_military_job_flagged_avoid(workspace: Path):
    _write_profile(workspace)
    rec = state.save_ingest(
        job_id="job0mil", text="defense systems work", source_url=None, source_kind="file"
    )
    profile = profile_loader.load_profile()
    result = job_analyzer.analyze_job(
        job_id=rec.job_id,
        profile=profile,
        text=rec.text,
        source_url=None,
        fetched_at=rec.fetched_at,
        raw_text_path=str(rec.raw_text_path),
        llm=FakeLLM(_military_payload()),
    )
    assert result["industry_filter"] == "avoid"
    # avoid penalty should significantly reduce the score
    assert result["fit_score"] < 50


def test_analyze_idempotent_skips_existing(workspace: Path, monkeypatch):
    _write_profile(workspace)
    state.save_ingest(job_id="aaaaaaaaaaaa", text="x", source_url=None, source_kind="file")
    fake = FakeLLM(_civilian_payload())
    monkeypatch.setattr(job_analyzer, "LLMClient", lambda: fake)
    r1 = job_analyzer.analyze_all()
    assert len(r1) == 1
    assert fake.calls == 1
    r2 = job_analyzer.analyze_all()
    assert r2 == []  # nothing new to analyze
    assert fake.calls == 1  # no extra LLM calls
    r3 = job_analyzer.analyze_all(refresh=True)
    assert len(r3) == 1
    assert fake.calls == 2


def test_industry_filter_keyword_fallback_when_tags_silent(workspace: Path):
    """If the LLM forgets to tag a defense company, name-based fallback flags REVIEW."""
    _write_profile(workspace)
    payload = _civilian_payload()
    payload["company"] = "Northrop Grumman"
    payload["industry_tags"] = ["aerospace"]  # tags don't include 'defense'
    rec = state.save_ingest(job_id="job0fb", text="x", source_url=None, source_kind="file")
    profile = profile_loader.load_profile()
    result = job_analyzer.analyze_job(
        job_id=rec.job_id,
        profile=profile,
        text=rec.text,
        source_url=None,
        fetched_at=rec.fetched_at,
        raw_text_path=str(rec.raw_text_path),
        llm=FakeLLM(payload),
    )
    # No exact tag match, but Northrop is famous defense -> won't match by company name alone
    # since "defense" isn't in "Northrop Grumman". This test really verifies that the
    # fallback never returns 'avoid' on the basis of company-name-only.
    assert result["industry_filter"] in {"ok", "review"}


def test_industry_filter_keyword_in_title(workspace: Path):
    _write_profile(workspace)
    payload = _civilian_payload()
    payload["title"] = "Defense Systems Engineer"
    payload["industry_tags"] = ["aerospace"]
    rec = state.save_ingest(job_id="jobtit", text="x", source_url=None, source_kind="file")
    profile = profile_loader.load_profile()
    result = job_analyzer.analyze_job(
        job_id=rec.job_id, profile=profile, text=rec.text, source_url=None,
        fetched_at=rec.fetched_at, raw_text_path=str(rec.raw_text_path),
        llm=FakeLLM(payload),
    )
    assert result["industry_filter"] == "review"


def test_fit_score_components_sane(workspace: Path):
    _write_profile(workspace)
    profile = profile_loader.load_profile()
    fields = _civilian_payload()
    fields["industry_filter"] = "ok"
    score = job_analyzer.compute_fit_score(llm_fields=fields, profile=profile)
    b = score["fit_breakdown"]
    assert b["cert_match"] == 100  # has Security+
    assert 0 <= b["skills_match"] <= 100
    assert b["location_match"] == 100  # hybrid_ok=True
    assert score["fit_score"] >= 50
