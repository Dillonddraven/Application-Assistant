"""PII boundary guard.

After running a tailor pipeline, every value from secrets.yaml must be absent
from:
  - jobs/raw_posts/*
  - jobs/analyzed/*
  - outputs/<slug>/packet.json   (the structured packet — pre-substitution)

It IS allowed (and expected) to appear in the locally-rendered .md files
inside outputs/<slug>/, since those are the user's exported documents.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from job_apply import llm_client, profile_loader, state, tailor_pipeline
from job_apply import config as cfg


PROFILE_DICT = {
    "identity": {"full_name": "Test User", "citizenship": "US", "work_auth": "yes"},
    "education": [
        {"id": "bs_cis", "school": "X", "degree": "BA Computer Information Systems",
         "status": "in_progress"},
    ],
    "certifications": [{"id": "secplus", "name": "CompTIA Security+"}],
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
            ],
        }
    ],
    "skills": {"technical": ["Python"], "security": []},
    "preferences": {"target_roles": ["Security Analyst"], "industries_avoid": []},
    "metrics_allowed": [],
}

SECRETS_DICT = {
    "email": "leak-canary-email@example.test",
    "phone": "+1-555-867-5309",
    "address": {
        "street": "742 Evergreen Terrace",
        "city": "Tulsa",
        "state": "OK",
        "zip": "74137",
    },
    "linkedin_url": "https://linkedin.com/in/leak-canary",
    "github_url": "https://github.com/leak-canary",
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
    "required_skills": ["Python"],
    "preferred_skills": [],
    "min_years_experience": 0,
    "required_certifications": [],
    "responsibilities": [],
    "keywords_extracted": [],
    "industry_tags": ["cybersecurity"],
    "industry_filter": "ok",
    "fit_score": 80,
    "fit_breakdown": {},
    "fit_rationale": "fit",
    "concerns": [],
    "missing_quals": [],
    "prompt_version": "analyze_job@v1",
    "model": "test",
}

CLEAN_TAILORED = {
    "summary": "Finishing a BA in CIS with internship experience at Dillard's.",
    "skills_emphasis": ["Python"],
    "bullets": [
        {"source_id": "experience.dillards_intern.b1",
         "text": "Reviewed access requests across the corporate identity system."}
    ],
    "cover_letter_paragraphs": [
        {"source_id": "general", "text": "I am applying for the Security Analyst role at Acme Corp."},
        {"source_id": "experience.dillards_intern",
         "text": "During my internship at Dillard's I supported the security team."},
        {"source_id": "general", "text": "Happy to discuss further."},
    ],
    "application_answers": [],
}

CLEAN_EMAILS = {
    "recruiter": {
        "subject": "Security Analyst — quick note",
        "body_paragraphs": [
            {"source_id": "general", "text": "Note about the Security Analyst role at Acme Corp."}
        ],
        "cited_items": [],
    },
    "hiring_manager": {
        "subject": "Security Analyst at Acme Corp",
        "body_paragraphs": [
            {"source_id": "general", "text": "I'd like to be considered for the Security Analyst role."}
        ],
        "cited_items": [],
    },
    "linkedin_dm": {
        "text": "Quick note about the Security Analyst role.",
        "cited_items": ["general"],
    },
}


class FakeLLM:
    def complete(self, *, tier, system, user, json_mode=False, temperature=0.4):  # noqa: ARG002
        if "tailoring a candidate" in system:
            payload = CLEAN_TAILORED
        elif "recruiter or talent" in system:
            payload = CLEAN_EMAILS["recruiter"]
        elif "hiring manager" in system:
            payload = CLEAN_EMAILS["hiring_manager"]
        elif "LinkedIn DM" in system:
            payload = CLEAN_EMAILS["linkedin_dm"]
        else:
            raise AssertionError("unexpected prompt")
        return llm_client.LLMResponse(text=json.dumps(payload), model=f"test-{tier}")


@pytest.fixture
def populated(workspace: Path) -> Path:
    (workspace / "profile" / "master_profile.yaml").write_text(yaml.safe_dump(PROFILE_DICT))
    (workspace / "profile" / "secrets.yaml").write_text(yaml.safe_dump(SECRETS_DICT))
    state.save_ingest(
        job_id="abc123def456",
        text="Acme Corp is hiring a Security Analyst...",
        source_url="https://acme.example.com/jobs/sa",
        source_kind="url",
    )
    state.save_analyzed("abc123def456", ANALYZED)
    return workspace


def _grep_dir_for_secrets(directory: Path, secrets: list[str]) -> list[tuple[Path, str]]:
    """Return list of (file, secret) hits across all files under directory."""
    hits: list[tuple[Path, str]] = []
    if not directory.exists():
        return hits
    for f in directory.rglob("*"):
        if not f.is_file():
            continue
        try:
            content = f.read_text(errors="ignore")
        except Exception:
            continue
        for s in secrets:
            if s and s in content:
                hits.append((f, s))
    return hits


# City / state / zip can legitimately appear in job postings (they describe
# the role's location). The truly sensitive PII is email, phone, street, and
# the unique URLs. We grep against high-entropy values only.
HIGH_ENTROPY_PII = [
    "leak-canary-email@example.test",
    "+1-555-867-5309",
    "742 Evergreen Terrace",
    "https://linkedin.com/in/leak-canary",
    "https://github.com/leak-canary",
]


def test_secrets_never_leak_to_raw_posts_or_analyzed(populated: Path):
    tailor_pipeline.run_tailor(job_id="abc123def456", llm=FakeLLM())
    raw_hits = _grep_dir_for_secrets(cfg.RAW_POSTS_DIR, HIGH_ENTROPY_PII)
    assert raw_hits == [], f"PII leaked into raw_posts/: {raw_hits}"
    analyzed_hits = _grep_dir_for_secrets(cfg.ANALYZED_DIR, HIGH_ENTROPY_PII)
    assert analyzed_hits == [], f"PII leaked into analyzed/: {analyzed_hits}"


def test_secrets_never_in_packet_json(populated: Path):
    _, slug = tailor_pipeline.run_tailor(job_id="abc123def456", llm=FakeLLM())
    packet_path = cfg.OUTPUTS_DIR / slug / "packet.json"
    text = packet_path.read_text()
    leaked = [s for s in HIGH_ENTROPY_PII if s in text]
    assert leaked == [], f"PII leaked into packet.json: {leaked}"


def test_canary_values_actually_loaded(populated: Path):
    """Sanity check: the test's canary values are actually present in secrets.yaml."""
    secrets = profile_loader.load_secrets().values_for_grep()
    for canary in HIGH_ENTROPY_PII:
        assert canary in secrets, f"canary {canary!r} missing from loaded secrets"


def test_secrets_DO_appear_in_rendered_md(populated: Path):
    """Sanity: the local .md files DO contain the secrets after substitution.
    (If they don't, we're not actually substituting and the user's resume is
    missing contact info.)"""
    _, slug = tailor_pipeline.run_tailor(job_id="abc123def456", llm=FakeLLM())
    resume = (cfg.OUTPUTS_DIR / slug / "internal" / "tailored_resume.md").read_text()
    assert "leak-canary-email@example.test" in resume
    assert "+1-555-867-5309" in resume
    cover = (cfg.OUTPUTS_DIR / slug / "internal" / "cover_letter.md").read_text()
    assert "742 Evergreen Terrace" in cover
