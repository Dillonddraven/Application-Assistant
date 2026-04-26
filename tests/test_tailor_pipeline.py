"""End-to-end pipeline test with stubbed LLM. Verifies:
  - tailor pipeline writes packet.json + 7 markdown files
  - clean tailored output produces validation.fabrication_blocks == []
  - fabricated output (e.g. CISSP) populates blocks
  - PII placeholders in templates are substituted from secrets at render time
  - PII values DO NOT appear in packet.json (which carries unsubstituted text)
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from job_apply import llm_client, profile_loader, state, tailor_pipeline


PROFILE_DICT = {
    "identity": {"full_name": "Test User", "citizenship": "US", "work_auth": "yes"},
    "education": [
        {"id": "bs_cis", "school": "X", "degree": "BA Computer Information Systems",
         "status": "in_progress"},
    ],
    "certifications": [
        {"id": "secplus", "name": "CompTIA Security+"},
        {"id": "netplus", "name": "CompTIA Network+"},
    ],
    "experience": [
        {
            "id": "dillards_intern",
            "company": "Dillard's",
            "title": "IT / Information Security Intern",
            "role_type": "internship",
            "summary": "Worked on the IT/Infosec team at Dillard's.",
            "bullets": [
                {"id": "dillards_intern.b1",
                 "text": "Reviewed access requests across the corporate identity system.",
                 "metrics_present": []},
                {"id": "dillards_intern.b2",
                 "text": "Documented incident-response runbooks for the SOC team.",
                 "metrics_present": []},
            ],
        }
    ],
    "skills": {"technical": ["Python", "Linux"], "security": ["SIEM basics"]},
    "preferences": {
        "target_roles": ["Security Analyst"],
        "industries_avoid": ["military"],
    },
    "metrics_allowed": [],
}

ANALYZED = {
    "id": "abc123def456",
    "source_url": "https://acme.example.com/jobs/sa",
    "fetched_at": "2026-04-26T00:00:00+00:00",
    "raw_text_path": "x",
    "company": "Acme Corp",
    "title": "Security Analyst",
    "location": "Tulsa, OK",
    "remote_mode": "hybrid",
    "required_skills": ["Python", "SIEM"],
    "preferred_skills": ["AWS"],
    "min_years_experience": 1,
    "required_certifications": ["CompTIA Security+"],
    "responsibilities": ["triage alerts"],
    "keywords_extracted": ["soc"],
    "industry_tags": ["cybersecurity"],
    "industry_filter": "ok",
    "fit_score": 75,
    "fit_breakdown": {},
    "fit_rationale": "good match",
    "concerns": [],
    "missing_quals": [],
    "prompt_version": "analyze_job@v1",
    "model": "gpt-4.1-mini-test",
}

CLEAN_TAILORED = {
    "summary": "Finishing a BA in CIS and a MS in Cybersecurity, with an internship at Dillard's.",
    "skills_emphasis": ["Python", "Linux", "SIEM basics"],
    "bullets": [
        {"source_id": "experience.dillards_intern.b1",
         "text": "Reviewed access requests across the corporate identity system."},
        {"source_id": "experience.dillards_intern.b2",
         "text": "Documented incident-response runbooks for the SOC team."},
    ],
    "cover_letter_paragraphs": [
        {"source_id": "general",
         "text": "I am writing about the Security Analyst opening at Acme Corp."},
        {"source_id": "experience.dillards_intern",
         "text": "During my internship at Dillard's I worked on access reviews and runbook documentation."},
        {"source_id": "general",
         "text": "I would welcome the chance to discuss the role."},
    ],
    "application_answers": [],
}

DIRTY_TAILORED = {
    "summary": "Senior security engineer with 5 years of full-time experience at Dillard's.",
    "skills_emphasis": ["Python"],
    "bullets": [
        {"source_id": "experience.dillards_intern.b1",
         "text": "Reduced alert volume by 40% during my CISSP-led tenure at Dillard's."},
    ],
    "cover_letter_paragraphs": [
        {"source_id": "general",
         "text": "I hold a BA Computer Information Systems and an AWS Certified Security Specialty."},
    ],
    "application_answers": [],
}

CLEAN_EMAILS = {
    "recruiter": {
        "subject": "Security Analyst — quick note",
        "body_paragraphs": [
            {"source_id": "general",
             "text": "I am applying for the Security Analyst role at Acme Corp."},
            {"source_id": "experience.dillards_intern.b1",
             "text": "I reviewed access requests during my internship at Dillard's."},
        ],
        "cited_items": ["experience.dillards_intern.b1"],
    },
    "hiring_manager": {
        "subject": "Security Analyst at Acme Corp",
        "body_paragraphs": [
            {"source_id": "general",
             "text": "I would like to be considered for the Security Analyst role."},
        ],
        "cited_items": [],
    },
    "linkedin_dm": {
        "text": "Hi — I am interested in the Security Analyst role and have CompTIA Security+. Are you the right person to talk to about this role?",
        "cited_items": ["general"],
    },
}


class FakeLLM:
    def __init__(self, tailored_payload: dict, emails_payload: dict):
        self._tailored = tailored_payload
        self._emails = emails_payload
        self._call_log: list[str] = []

    def complete(self, *, tier, system, user, json_mode=False, temperature=0.4):  # noqa: ARG002
        # Route based on system prompt content
        if "tailoring a candidate" in system:
            payload = self._tailored
            self._call_log.append("tailor")
        elif "recruiter or talent" in system:
            payload = self._emails["recruiter"]
            self._call_log.append("recruiter")
        elif "hiring manager" in system:
            payload = self._emails["hiring_manager"]
            self._call_log.append("hiring_manager")
        elif "LinkedIn DM" in system:
            payload = self._emails["linkedin_dm"]
            self._call_log.append("linkedin_dm")
        else:
            raise AssertionError(f"unexpected system prompt: {system[:80]!r}")
        return llm_client.LLMResponse(text=json.dumps(payload), model=f"test-{tier}")


@pytest.fixture
def populated(workspace: Path) -> Path:
    (workspace / "profile" / "master_profile.yaml").write_text(yaml.safe_dump(PROFILE_DICT))
    (workspace / "profile" / "secrets.yaml").write_text(yaml.safe_dump({
        "email": "test@example.com",
        "phone": "+1-555-555-1234",
        "address": {"street": "1 Main St", "city": "Tulsa", "state": "OK", "zip": "74000"},
        "linkedin_url": "https://linkedin.com/in/test",
    }))
    state.save_ingest(
        job_id="abc123def456",
        text="Acme Corp is hiring a Security Analyst...",
        source_url="https://acme.example.com/jobs/sa",
        source_kind="url",
    )
    state.save_analyzed("abc123def456", ANALYZED)
    return workspace


def test_clean_tailor_writes_packet_and_files(populated: Path):
    fake = FakeLLM(CLEAN_TAILORED, CLEAN_EMAILS)
    packet, slug = tailor_pipeline.run_tailor(job_id="abc123def456", llm=fake)
    out = populated / "outputs" / slug
    assert (out / "packet.json").exists()
    for fname in (
        "tailored_resume.md", "cover_letter.md", "application_answers.md",
        "outreach_recruiter.md", "outreach_hiring_manager.md",
        "linkedin_dm.md", "match_report.md",
    ):
        assert (out / fname).exists(), f"missing render: {fname}"
    assert packet["validation"]["fabrication_blocks"] == [], packet["validation"]
    assert packet["status"] == "draft"
    assert packet["job_id"] == "abc123def456"


def test_dirty_tailor_populates_blocks(populated: Path):
    fake = FakeLLM(DIRTY_TAILORED, CLEAN_EMAILS)
    packet, _ = tailor_pipeline.run_tailor(job_id="abc123def456", llm=fake)
    blocks = packet["validation"]["fabrication_blocks"]
    rules = {b["rule"] for b in blocks}
    assert "numeric_whitelist" in rules
    assert "internship_inflation" in rules
    assert "in_progress_degree_inflation" in rules
    assert "unknown_credential" in rules


def test_pii_substituted_into_resume_only_at_render(populated: Path):
    fake = FakeLLM(CLEAN_TAILORED, CLEAN_EMAILS)
    packet, slug = tailor_pipeline.run_tailor(job_id="abc123def456", llm=fake)
    out = populated / "outputs" / slug
    resume = (out / "tailored_resume.md").read_text()
    cover = (out / "cover_letter.md").read_text()
    assert "test@example.com" in resume
    assert "+1-555-555-1234" in resume
    assert "1 Main St" in cover
    # Crucially, the unsubstituted packet.json must NOT carry secrets.
    packet_text = (out / "packet.json").read_text()
    assert "test@example.com" not in packet_text
    assert "+1-555-555-1234" not in packet_text
    assert "1 Main St" not in packet_text


def test_avoid_filter_refuses_without_force(populated: Path):
    avoid = {**ANALYZED, "industry_filter": "avoid", "industry_tags": ["military"]}
    state.save_analyzed("abc123def456", avoid)
    fake = FakeLLM(CLEAN_TAILORED, CLEAN_EMAILS)
    with pytest.raises(tailor_pipeline.TailorError, match="FILTER:AVOID"):
        tailor_pipeline.run_tailor(job_id="abc123def456", llm=fake)
    # Force overrides
    packet, _ = tailor_pipeline.run_tailor(job_id="abc123def456", force=True, llm=fake)
    assert packet["status"] == "draft"


def test_missing_analyzed_raises(populated: Path):
    fake = FakeLLM(CLEAN_TAILORED, CLEAN_EMAILS)
    with pytest.raises(tailor_pipeline.TailorError, match="not analyzed"):
        tailor_pipeline.run_tailor(job_id="zzzzzzzzzzzz", llm=fake)
