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
