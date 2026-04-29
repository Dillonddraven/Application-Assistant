"""Tests for job source confidence scoring."""
from __future__ import annotations

import pytest

from job_apply.job_analyzer import score_source_confidence


@pytest.mark.parametrize("url,expected", [
    ("https://boards.greenhouse.io/acme/jobs/12345", "high"),
    ("https://jobs.lever.co/acme/abc-def", "high"),
    ("https://jobs.ashbyhq.com/acme/xxx", "high"),
    ("https://acme.myworkdayjobs.com/Careers/job/Senior-X", "high"),
    ("https://apply.workable.com/acme/j/abc", "high"),
    ("https://careers.smartrecruiters.com/Acme/job-1", "high"),
])
def test_high_confidence_ats_boards(url, expected):
    sc, reason = score_source_confidence(url)
    assert sc == expected
    assert "ATS" in reason


@pytest.mark.parametrize("url,expected", [
    ("https://www.linkedin.com/jobs/view/1234567890", "medium"),
    ("https://www.indeed.com/viewjob?jk=abc", "medium"),
    ("https://www.dice.com/jobs/detail/abc", "medium"),
])
def test_medium_confidence_job_boards(url, expected):
    sc, _ = score_source_confidence(url)
    assert sc == expected


@pytest.mark.parametrize("url", [
    "https://www.optnation.com/junior-cybersecurity-analyst-job-in-san-diego-ca-view-jobid-38755",
    "https://www.glassdoor.com/job-listing/abc",
    "https://www.ziprecruiter.com/jobs/abc",
    "https://www.example.com/jobs?utm_campaign=google_jobs_apply",
])
def test_low_confidence_aggregators(url):
    sc, reason = score_source_confidence(url)
    assert sc == "low"
    assert "aggregator" in reason or "re-syndicator" in reason


def test_no_url_returns_medium():
    sc, reason = score_source_confidence(None)
    assert sc == "medium"
    assert "no source URL" in reason


def test_unknown_url_returns_medium():
    sc, reason = score_source_confidence("https://random-company-careers.com/jobs/123")
    assert sc == "medium"
    assert "unrecognized" in reason


def test_optnation_url_with_query_params():
    """The Soro URL we ingested earlier — ensure detection works through query params."""
    url = (
        "https://www.optnation.com/junior-cybersecurity-analyst-job-in-san-diego-ca"
        "-view-jobid-38755?utm_campaign=google_jobs_apply&utm_source=google_jobs_apply"
        "&utm_medium=organic"
    )
    sc, _ = score_source_confidence(url)
    assert sc == "low"  # both optnation.com AND google_jobs_apply markers present
