"""Unit tests for the posting_quality_gate that catches thin-content
hallucinations before tailoring."""
from __future__ import annotations

from job_apply.job_analyzer import posting_quality_gate

LONG_TEXT = "x" * 3000
SHORT_TEXT = "x" * 400  # below 1500 hard floor

GOOD_FIELDS = {
    "title": "Cybersecurity Analyst",
    "company": "Acme Corp",
    "responsibilities": ["a", "b", "c", "d"],
    "required_skills": ["Python", "SIEM", "Linux"],
    "required_certifications": [],
}


def test_healthy_posting_is_ok():
    result = posting_quality_gate(text=LONG_TEXT, fields=GOOD_FIELDS)
    assert result["status"] == "ok"
    assert result["reasons"] == []


def test_bloomreach_style_empty_title_fails():
    """Bloomreach: 581 chars, populated company, empty title — hallucination."""
    fields = {**GOOD_FIELDS, "title": ""}
    text = "x" * 581
    result = posting_quality_gate(text=text, fields=fields)
    assert result["status"] == "ingest_failure"
    assert any("title is empty" in r for r in result["reasons"])
    # Below 1500 hard floor also fires
    assert any("hard floor" in r for r in result["reasons"])


def test_advanced_space_style_short_text_fails():
    """Advanced Space: 434 chars, populated title — but content too thin to trust."""
    result = posting_quality_gate(text=SHORT_TEXT, fields=GOOD_FIELDS)
    assert result["status"] == "ingest_failure"
    assert any("hard floor" in r for r in result["reasons"])


def test_empty_company_fails():
    fields = {**GOOD_FIELDS, "company": ""}
    result = posting_quality_gate(text=LONG_TEXT, fields=fields)
    assert result["status"] == "ingest_failure"


def test_low_responsibilities_low_requirements_review():
    """2 responsibilities + 2 requirements + medium-length text -> source_needs_review."""
    fields = {
        **GOOD_FIELDS,
        "responsibilities": ["a", "b"],
        "required_skills": ["Python"],
        "required_certifications": [],
    }
    result = posting_quality_gate(text="x" * 1800, fields=fields)
    assert result["status"] == "source_needs_review"


def test_shell_marker_hits_count_as_failure():
    """An ATS shell page (404 + cookies markers + thin content) is ingest_failure."""
    text = (
        "Page not found. Please accept cookies to continue. "
        "We couldn't find the job you're looking for."
    ) * 5
    result = posting_quality_gate(text=text, fields=GOOD_FIELDS)
    assert result["status"] == "ingest_failure"
    assert any("shell" in r for r in result["reasons"])


def test_expected_title_mismatch_adds_review_signal():
    """If a URL slug expects 'Information Security' but extraction is 'Sr. DevOps',
    flag for review (combined with thin content gives ingest_failure)."""
    fields = {**GOOD_FIELDS, "title": "Sr. DevOps Engineer"}
    text = "x" * 1700  # below 2000 soft floor
    result = posting_quality_gate(
        text=text, fields=fields,
        expected_title_hint="Information Security Analyst",
    )
    # text<2000 + title mismatch = 2 soft fails → source_needs_review
    assert result["status"] == "source_needs_review"
    assert any("doesn't share a word" in r for r in result["reasons"])


def test_expected_title_match_no_extra_signal():
    """If extraction title overlaps with expected, no soft signal added."""
    fields = {**GOOD_FIELDS, "title": "Cybersecurity Analyst"}
    result = posting_quality_gate(
        text=LONG_TEXT, fields=fields,
        expected_title_hint="Cybersecurity Analyst",
    )
    assert result["status"] == "ok"


def test_status_field_always_present():
    """Even on a fully ok posting, status and reasons keys must always be present."""
    result = posting_quality_gate(text=LONG_TEXT, fields=GOOD_FIELDS)
    assert "status" in result
    assert "reasons" in result
    assert "char_count" in result
    assert result["char_count"] == len(LONG_TEXT)
