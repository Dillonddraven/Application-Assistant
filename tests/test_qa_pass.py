"""Tests for the QA post-pass module."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from job_apply import llm_client, qa_pass


CANNED_QA_CLEAN = {"issues": [], "overall_polish": "ready"}

CANNED_QA_WITH_ISSUES = {
    "issues": [
        {
            "category": "generic_phrase", "severity": "medium",
            "where": "tailored_resume — Skills",
            "snippet": "Stakeholder communication",
            "fix_suggestion": "Replace with a concrete example.",
        },
        {
            "category": "overclaiming", "severity": "high",
            "where": "cover_letter — paragraph 2",
            "snippet": "I have years of experience in SAST",
            "fix_suggestion": "Reframe as internship-level.",
        },
    ],
    "overall_polish": "needs_work",
}


class FakeQALLM:
    def __init__(self, payload: dict):
        self.payload = payload
        self.last_user: str = ""
        self.tier_used: str = ""

    def complete(self, *, tier, system, user, json_mode=False, temperature=0.4):  # noqa: ARG002
        self.last_user = user
        self.tier_used = tier
        return llm_client.LLMResponse(text=json.dumps(self.payload), model="test-qa")


def test_qa_check_clean_returns_ready():
    fake = FakeQALLM(CANNED_QA_CLEAN)
    rendered = {"tailored_resume": "...", "cover_letter": "..."}
    result = qa_pass.qa_check(rendered_views=rendered, jd_analysis=None, llm=fake)
    assert result["overall_polish"] == "ready"
    assert result["issues"] == []
    assert result["prompt_version"] == "qa_check@v1"


def test_qa_check_with_issues_normalizes():
    fake = FakeQALLM(CANNED_QA_WITH_ISSUES)
    rendered = {"tailored_resume": "...", "cover_letter": "..."}
    result = qa_pass.qa_check(rendered_views=rendered, jd_analysis=None, llm=fake)
    assert result["overall_polish"] == "needs_work"
    assert len(result["issues"]) == 2
    assert result["issues"][0]["category"] == "generic_phrase"


def test_qa_check_uses_tailor_tier_for_quality():
    """The QA pass uses gpt-5-mini (tailor tier) for stronger detection than gpt-4.1-mini."""
    fake = FakeQALLM(CANNED_QA_CLEAN)
    qa_pass.qa_check(rendered_views={"x": "y"}, jd_analysis=None, llm=fake)
    assert fake.tier_used == "tailor"


def test_qa_check_includes_jd_analysis_in_prompt():
    fake = FakeQALLM(CANNED_QA_CLEAN)
    jd = {
        "pain_points": [{"text": "Monitor noisy alerts", "jd_anchor": "monitor"}],
        "evidence_map": [], "missing_evidence": [],
    }
    qa_pass.qa_check(rendered_views={"resume": "."}, jd_analysis=jd, llm=fake)
    assert "Monitor noisy alerts" in fake.last_user
    assert "JD_ANALYSIS:" in fake.last_user


def test_qa_check_includes_all_views_in_prompt():
    fake = FakeQALLM(CANNED_QA_CLEAN)
    rendered = {
        "tailored_resume": "RESUME CONTENT",
        "cover_letter": "COVER CONTENT",
        "outreach_recruiter": "RECRUITER CONTENT",
    }
    qa_pass.qa_check(rendered_views=rendered, jd_analysis=None, llm=fake)
    for label, content in rendered.items():
        assert label in fake.last_user
        assert content in fake.last_user


def test_render_qa_summary_clean():
    out = qa_pass.render_qa_summary(CANNED_QA_CLEAN)
    assert "ready" in out


def test_render_qa_summary_grouped_by_severity():
    out = qa_pass.render_qa_summary(CANNED_QA_WITH_ISSUES)
    assert "HIGH (1)" in out
    assert "MEDIUM (1)" in out
    assert "needs_work" in out
    assert "Reframe as internship-level" in out


def test_forbidden_phrase_scan_deterministic():
    fake = FakeQALLM(CANNED_QA_CLEAN)
    rendered = {
        "tailored_resume": "Results-driven analyst with passion for security.",
        "cover_letter": "I want to be a rockstar engineer.",
        "linkedin_dm": "Quick note about the role.",
    }
    forbidden = ["passion", "rockstar", "results-driven"]
    result = qa_pass.qa_check(
        rendered_views=rendered, jd_analysis=None, llm=fake,
        forbidden_phrases=forbidden,
    )
    # Three phrases each appear once -> 3 deterministic high-severity issues
    cats = [(i["category"], i["severity"], i["snippet"]) for i in result["issues"]]
    high_issues = [c for c in cats if c[1] == "high"]
    assert len(high_issues) == 3
    # Polish should downgrade from "ready" to "needs_work" because of high hits
    assert result["overall_polish"] == "needs_work"


def test_forbidden_phrase_scan_case_insensitive():
    fake = FakeQALLM(CANNED_QA_CLEAN)
    rendered = {"resume": "I am Passionate about security."}
    result = qa_pass.qa_check(
        rendered_views=rendered, jd_analysis=None, llm=fake,
        forbidden_phrases=["passionate"],
    )
    high_issues = [i for i in result["issues"] if i["severity"] == "high"]
    assert len(high_issues) == 1


def test_forbidden_phrase_scan_word_boundary():
    """'pass' should NOT match 'passionate' — word boundaries are real."""
    fake = FakeQALLM(CANNED_QA_CLEAN)
    rendered = {"resume": "I am passionate about security."}
    result = qa_pass.qa_check(
        rendered_views=rendered, jd_analysis=None, llm=fake,
        forbidden_phrases=["pass"],
    )
    deterministic_high = [i for i in result["issues"]
                          if i["severity"] == "high" and i["snippet"] == "pass"]
    assert deterministic_high == []


def test_forbidden_phrase_scan_skips_when_no_list():
    fake = FakeQALLM(CANNED_QA_CLEAN)
    rendered = {"resume": "Results-driven rockstar with synergy."}
    result = qa_pass.qa_check(
        rendered_views=rendered, jd_analysis=None, llm=fake,
    )
    # No forbidden_phrases passed; no deterministic adds.
    assert result["overall_polish"] == "ready"
