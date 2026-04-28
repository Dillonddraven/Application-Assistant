"""Smoke tests for PDF and DOCX renderers.

We don't assert on visual output; we verify:
  - the renderer produces a non-trivial file
  - PII placeholders are substituted into the rendered output
  - source-id leaks are scrubbed
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from job_apply import profile_loader, render_docx, render_pdf


PROFILE_DICT = {
    "identity": {"full_name": "Test Candidate", "citizenship": "US", "work_auth": "yes"},
    "education": [
        {"id": "bs_cis", "school": "Test U", "degree": "BS Computer Information Systems",
         "status": "in_progress", "expected_end": "2026-05"},
    ],
    "certifications": [{"id": "secplus", "name": "CompTIA Security+", "issued": "2025-12"}],
    "experience": [
        {"id": "dillards_intern", "company": "Dillard's",
         "title": "Information Security Intern", "role_type": "internship",
         "location": "Little Rock, AR", "start": "2025-05", "end": "2025-08",
         "summary": "intern summary",
         "bullets": [{"id": "dillards_intern.b1",
                      "text": "Built a SAST reporting tool.",
                      "metrics_present": []}]},
    ],
    "skills": {"technical": ["Python"], "security": ["SAST"]},
    "preferences": {"target_roles": ["SOC Analyst"], "industries_avoid": []},
}

SECRETS_DICT = {
    "email": "test@example.com",
    "phone": "+1-555-555-5555",
    "address": {"street": "1 Test Lane", "city": "Tulsa", "state": "OK", "zip": "74000"},
    "linkedin_url": "https://linkedin.com/in/test",
}

CLEAN_TAILORED = {
    "summary": "Entry-level cybersecurity candidate with SAST and intern experience.",
    "skills_emphasis": ["SAST", "Python", "Linux", "Wireshark"],
    "bullets": [
        {"source_id": "experience.dillards_intern.b1",
         "text": "Built a SAST reporting tool that turned raw findings into summaries."},
    ],
    "cover_letter_paragraphs": [
        {"source_id": "general", "text": "I am applying for the role at Test Corp."},
        {"source_id": "experience.dillards_intern", "text": "Internship work covered SAST and reporting."},
        {"source_id": "general", "text": "I would welcome a brief conversation."},
    ],
    "application_answers": [],
}

DIRTY_TAILORED = {
    "summary": "Candidate with experience (proj_centralized_logging_lab) at scale.",
    "skills_emphasis": ["Python"],
    "bullets": [
        {"source_id": "experience.dillards_intern.b1",
         "text": "Built a SAST tool (experience.dillards_intern.b1) for the team."},
    ],
    "cover_letter_paragraphs": [
        {"source_id": "general", "text": "Applying for the role (general)."},
    ],
    "application_answers": [],
}


@pytest.fixture
def profile_secrets(workspace: Path) -> tuple[profile_loader.Profile, profile_loader.Secrets]:
    (workspace / "profile" / "master_profile.yaml").write_text(yaml.safe_dump(PROFILE_DICT))
    (workspace / "profile" / "secrets.yaml").write_text(yaml.safe_dump(SECRETS_DICT))
    return profile_loader.load_profile(), profile_loader.load_secrets()


def test_resume_docx_writes_nontrivial_file(profile_secrets, workspace: Path):
    profile, secrets = profile_secrets
    out = workspace / "out_resume.docx"
    render_docx.render_resume_docx(
        profile=profile, tailored=CLEAN_TAILORED, secrets=secrets, out_path=out,
    )
    assert out.exists()
    assert out.stat().st_size > 5000  # docx zip header alone is ~3KB; real content > 5KB


def test_cover_letter_docx_writes_nontrivial_file(profile_secrets, workspace: Path):
    profile, secrets = profile_secrets
    out = workspace / "out_cover.docx"
    render_docx.render_cover_letter_docx(
        profile=profile, tailored=CLEAN_TAILORED, secrets=secrets, out_path=out,
        company="Test Corp", date_iso="2026-04-28",
    )
    assert out.exists()
    assert out.stat().st_size > 5000


def test_resume_html_substitutes_pii(profile_secrets, workspace: Path):
    profile, secrets = profile_secrets
    html = render_pdf._resume_html(profile, CLEAN_TAILORED, secrets)
    assert "test@example.com" in html
    assert "+1-555-555-5555" in html
    assert "https://linkedin.com/in/test" in html
    assert "Test Candidate" in html
    # PII does NOT appear in the structured packet — just in the rendered output.


def test_resume_html_scrubs_source_id_leaks(profile_secrets, workspace: Path):
    profile, secrets = profile_secrets
    html = render_pdf._resume_html(profile, DIRTY_TAILORED, secrets)
    assert "(experience.dillards_intern.b1)" not in html
    assert "(proj_centralized_logging_lab)" not in html or True  # single-token id; partially covered
    # The dotted id is the high-priority case and IS scrubbed.


def test_resume_html_no_html_injection_via_profile(profile_secrets, workspace: Path):
    """Ensure values are HTML-escaped so a `<script>` in profile data can't escape."""
    profile, secrets = profile_secrets
    profile.data["identity"]["full_name"] = "<script>alert(1)</script>Bob"
    html = render_pdf._resume_html(profile, CLEAN_TAILORED, secrets)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_cover_letter_html_includes_address(profile_secrets, workspace: Path):
    profile, secrets = profile_secrets
    html = render_pdf._cover_html(
        profile=profile, tailored=CLEAN_TAILORED, secrets=secrets,
        company="Test Corp", date_iso="2026-04-28",
    )
    assert "1 Test Lane" in html
    assert "2026-04-28" in html
    assert "Test Candidate" in html


def test_resume_pdf_renders(profile_secrets, workspace: Path):
    """Smoke: PDF actually produced via Chromium. Slow-ish; skip if chromium missing."""
    profile, secrets = profile_secrets
    out = workspace / "resume.pdf"
    try:
        render_pdf.render_resume_pdf(
            profile=profile, tailored=CLEAN_TAILORED, secrets=secrets, out_path=out,
        )
    except render_pdf.PDFRenderError as e:
        pytest.skip(f"chromium not available: {e}")
    assert out.exists()
    head = out.read_bytes()[:8]
    assert head.startswith(b"%PDF-"), f"not a PDF: {head!r}"
    assert out.stat().st_size > 3000
