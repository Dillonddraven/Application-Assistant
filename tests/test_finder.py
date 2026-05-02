"""Tests for the job_finder module — sources (mocked HTTP), filters, queue,
and the orchestrator. No live network calls."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from job_apply.finder import filters, queue, runner, sources
from job_apply.finder.queue import FinderQueueRow
from job_apply import profile_loader


# -------------------- filters --------------------

def test_title_matches_targets_default_list():
    assert filters.title_matches_targets("SOC Analyst I")
    assert filters.title_matches_targets("Cybersecurity Analyst")
    assert filters.title_matches_targets("GRC Analyst, Senior") is True   # 'grc analyst' substring
    assert filters.title_matches_targets("Software Engineer") is False


def test_is_senior_title():
    assert filters.is_senior_title("Senior Security Engineer")
    assert filters.is_senior_title("Staff SOC Analyst")
    assert filters.is_senior_title("Principal Architect")
    assert not filters.is_senior_title("SOC Analyst I")


def test_required_years_extraction():
    assert filters.required_years_from_text("3+ years of experience required") == 3
    assert filters.required_years_from_text("5 to 7 years") == 5
    assert filters.required_years_from_text("entry-level role") is None


def test_quick_fit_target_match_no_stretch():
    posting = {
        "title": "Cybersecurity Analyst",
        "raw_text": "Required: Python, Splunk, log monitoring, incident response.",
    }
    fit = filters.quick_fit(
        posting=posting,
        profile_skills=["Python", "Graylog logging lab", "Linux"],
        certs_needed_match=True,
        target_roles=["Cybersecurity Analyst"],
    )
    assert fit["score"] >= 60
    assert fit["stretch_flags"] == []


def test_quick_fit_senior_title_stretch_flag():
    posting = {
        "title": "Senior SOC Analyst",
        "raw_text": "5+ years of SIEM experience required.",
    }
    fit = filters.quick_fit(
        posting=posting, profile_skills=["Python", "Graylog"],
        certs_needed_match=False, target_roles=[],
    )
    assert "senior" in " ".join(fit["stretch_flags"]).lower()
    assert any("years required" in f for f in fit["stretch_flags"])


def test_should_drop_clearance():
    posting = {"title": "Cybersecurity Analyst",
               "raw_text": "Active Top Secret clearance required."}
    fit = {"score": 80, "reasons": [], "stretch_flags": []}
    drop, reason = filters.should_drop(posting, fit=fit, allow_stretch=False)
    assert drop is True
    assert "clearance" in reason.lower()


def test_should_drop_low_fit():
    posting = {"title": "Sales Engineer", "raw_text": "Sell our product."}
    fit = {"score": 10, "reasons": [], "stretch_flags": []}
    drop, _ = filters.should_drop(posting, fit=fit, allow_stretch=False)
    assert drop is True


def test_should_drop_stretch_unless_allowed():
    """A stretch role with enough fit-score signal: dropped strict, kept loose."""
    posting = {
        "title": "Senior Security Engineer",
        "raw_text": (
            "5+ years of SIEM experience required. The role involves Python "
            "log automation, Splunk, vulnerability management, incident response, "
            "Linux administration, Wireshark traffic analysis, GitLab SAST."
        ),
    }
    fit = filters.quick_fit(
        posting=posting,
        profile_skills=["Python", "Splunk", "Linux", "Wireshark", "GitLab SAST"],
        certs_needed_match=True, target_roles=[],
    )
    drop_strict, reason_strict = filters.should_drop(posting, fit=fit, allow_stretch=False)
    drop_loose, _ = filters.should_drop(posting, fit=fit, allow_stretch=True)
    assert drop_strict is True
    assert "senior" in reason_strict.lower() or "year" in reason_strict.lower()
    # With allow_stretch=True, the stretch flags should no longer cause a drop
    assert drop_loose is False


# -------------------- sources (mocked) --------------------

class _FakeResp:
    def __init__(self, payload):
        self._payload = payload
        self.status_code = 200
    def raise_for_status(self): pass
    def json(self): return self._payload


class _FakeClient:
    def __init__(self, payload):
        self._payload = payload
    def __enter__(self): return self
    def __exit__(self, *a): pass
    def get(self, url, params=None):
        return _FakeResp(self._payload)


def test_fetch_greenhouse_normalizes(monkeypatch):
    payload = {
        "name": "Datadog",
        "jobs": [{
            "id": 12345,
            "title": " Senior Detection Engineer ",
            "absolute_url": "https://boards.greenhouse.io/datadog/jobs/12345",
            "location": {"name": "New York, NY"},
            "departments": [{"name": "Security"}],
            "content": "<p>Help us build detection content...</p>",
        }],
    }
    monkeypatch.setattr(sources.httpx, "Client",
                         lambda *a, **kw: _FakeClient(payload))
    out = sources.fetch_greenhouse("datadog")
    assert len(out) == 1
    p = out[0]
    assert p["company"] == "Datadog"
    assert p["title"] == "Senior Detection Engineer"
    assert p["location"] == "New York, NY"
    assert p["url"].endswith("/12345")
    assert p["ats"] == "greenhouse"
    assert p["external_id"] == "12345"


def test_fetch_lever_normalizes(monkeypatch):
    payload = [{
        "id": "abc-123",
        "text": "SOC Analyst",
        "hostedUrl": "https://jobs.lever.co/snyk/abc-123",
        "categories": {"location": "Remote", "department": "Security"},
        "descriptionPlain": "Triage alerts...",
    }]
    monkeypatch.setattr(sources.httpx, "Client",
                         lambda *a, **kw: _FakeClient(payload))
    out = sources.fetch_lever("snyk")
    assert len(out) == 1
    p = out[0]
    assert p["title"] == "SOC Analyst"
    assert p["location"] == "Remote"
    assert p["ats"] == "lever"


def test_fetch_for_company_dispatches():
    with pytest.raises(NotImplementedError):
        sources.fetch_for_company(ats="workday", slug="x")


# -------------------- queue --------------------

def test_queue_save_and_load_roundtrip(tmp_path: Path):
    rows = [
        FinderQueueRow(
            company="Datadog", title="SOC Analyst", location="Remote",
            ats="greenhouse", url="https://x.com/1",
            quick_fit=72, recommended_action="run_packet",
            review_status="new", discovered_date="2026-05-01",
            external_id="1",
        ),
    ]
    qpath = tmp_path / "q.xlsx"
    queue.save_queue(rows, qpath)
    assert qpath.exists()
    loaded = queue.load_queue(qpath)
    assert len(loaded) == 1
    assert loaded[0].company == "Datadog"
    assert loaded[0].quick_fit == 72


def test_queue_upsert_preserves_user_review_status(tmp_path: Path):
    """If the user marked a row 'reviewed', a re-run shouldn't reset it."""
    existing = FinderQueueRow(
        company="A", title="T", url="https://x/1", ats="greenhouse",
        quick_fit=60, recommended_action="run_packet",
        review_status="reviewed", review_notes="looks good",
        discovered_date="2026-05-01",
    )
    fresh = FinderQueueRow(
        company="A", title="T", url="https://x/1", ats="greenhouse",
        quick_fit=70, recommended_action="run_packet",
        review_status="new", review_notes="",
        discovered_date="2026-05-02",
    )
    rows = queue.upsert([existing], fresh)
    assert len(rows) == 1
    # User edits preserved, fit refreshed
    assert rows[0].review_status == "reviewed"
    assert rows[0].review_notes == "looks good"
    assert rows[0].quick_fit == 70


# -------------------- runner (orchestration with mocked sources) --------------------

def test_runner_polls_filters_and_persists(tmp_path: Path,
                                            monkeypatch: pytest.MonkeyPatch,
                                            workspace: Path):
    # Profile setup
    (workspace / "profile" / "master_profile.yaml").write_text(yaml.safe_dump({
        "identity": {"full_name": "Test", "citizenship": "US", "work_auth": "yes"},
        "education": [{"id": "x", "school": "X", "degree": "BA CIS",
                       "status": "in_progress"}],
        "certifications": [{"id": "secplus", "name": "CompTIA Security+"}],
        "skills": {"technical": ["Python"], "security": ["Graylog logging lab"]},
        "preferences": {
            "target_roles": ["SOC Analyst", "Cybersecurity Analyst"],
            "industries_avoid": ["military", "defense"],
            "remote_ok": True, "hybrid_ok": True, "onsite_ok": True,
            "willing_to_relocate": True,
        },
    }))
    # Companies file
    companies_path = workspace / "profile" / "companies.yaml"
    companies_path.write_text(yaml.safe_dump({
        "companies": [
            {"name": "Datadog", "ats": "greenhouse", "slug": "datadog"},
            {"name": "Snyk",    "ats": "lever",      "slug": "snyk"},
            {"name": "DefenseCo","ats": "greenhouse","slug": "defenseco"},  # filtered by industries_avoid
        ],
    }))
    # Mock the fetchers
    def fake_dispatch(*, ats, slug):
        if slug == "datadog":
            return [{
                "company": "Datadog", "title": "SOC Analyst",
                "location": "Remote",
                "url": "https://boards.greenhouse.io/datadog/jobs/1",
                "ats": "greenhouse", "ats_slug": "datadog",
                "department": "Security",
                "raw_text": "Required: Python, Graylog, monitor logs. CompTIA Security+ a plus.",
                "external_id": "1", "discovered_at": "now",
            }]
        if slug == "snyk":
            return [
                {
                    "company": "Snyk", "title": "Cybersecurity Analyst",
                    "location": "London, UK",
                    "url": "https://jobs.lever.co/snyk/2",
                    "ats": "lever", "ats_slug": "snyk",
                    "department": "Security",
                    "raw_text": "Active Top Secret clearance required.",
                    "external_id": "2", "discovered_at": "now",
                },
                {
                    "company": "Snyk", "title": "Senior Detection Engineer",
                    "location": "Remote",
                    "url": "https://jobs.lever.co/snyk/3",
                    "ats": "lever", "ats_slug": "snyk",
                    "department": "Security",
                    "raw_text": "5+ years required.",
                    "external_id": "3", "discovered_at": "now",
                },
            ]
        if slug == "defenseco":
            return [{
                "company": "DefenseCo", "title": "Cybersecurity Analyst",
                "location": "Tulsa, OK",
                "url": "https://boards.greenhouse.io/defenseco/jobs/4",
                "ats": "greenhouse", "ats_slug": "defenseco",
                "department": "", "raw_text": "Civilian role.",
                "external_id": "4", "discovered_at": "now",
            }]
        return []

    monkeypatch.setattr(runner.sources, "fetch_for_company", fake_dispatch)
    # Redirect queue path into tmp
    monkeypatch.setattr(runner.queue, "QUEUE_PATH", tmp_path / "q.xlsx")

    profile = profile_loader.load_profile()
    result = runner.run_finder(profile=profile, allow_stretch=False,
                                companies_path=companies_path)

    titles = [r.title for r in result.queue_rows]
    # Datadog SOC Analyst kept; Snyk Top Secret dropped (clearance);
    # Snyk Senior Detection Engineer dropped (stretch);
    # DefenseCo Cybersecurity Analyst dropped (industry-avoid via 'defense' substring in company)
    assert "SOC Analyst" in titles
    assert "Senior Detection Engineer" not in titles  # stretch dropped
    # Top Secret is dropped — should not appear
    snyk_top_secret = [r for r in result.queue_rows if r.url.endswith("/2")]
    assert snyk_top_secret == []
    assert result.dropped_clearance >= 1
    assert result.dropped_stretch >= 1


def test_runner_allow_stretch_keeps_senior(tmp_path: Path,
                                             monkeypatch: pytest.MonkeyPatch,
                                             workspace: Path):
    (workspace / "profile" / "master_profile.yaml").write_text(yaml.safe_dump({
        "identity": {"full_name": "T", "citizenship": "US", "work_auth": "yes"},
        "education": [{"id": "x", "school": "X", "degree": "BA CIS",
                       "status": "in_progress"}],
        "skills": {"technical": ["Python"]},
        "preferences": {"target_roles": ["Cybersecurity Analyst"],
                        "industries_avoid": []},
    }))
    companies_path = workspace / "profile" / "companies.yaml"
    companies_path.write_text(yaml.safe_dump({
        "companies": [{"name": "X", "ats": "greenhouse", "slug": "x"}],
    }))

    def fake_dispatch(*, ats, slug):
        return [{
            "company": "X", "title": "Senior Cybersecurity Analyst",
            "location": "Remote",
            "url": "https://x.com/1",
            "ats": "greenhouse", "ats_slug": "x", "department": "",
            "raw_text": (
                "5+ years required. Python automation, Linux administration, "
                "Wireshark analysis, GitLab SAST reporting, vulnerability "
                "management, log monitoring with Graylog/Splunk."
            ),
            "external_id": "1", "discovered_at": "now",
        }]

    monkeypatch.setattr(runner.sources, "fetch_for_company", fake_dispatch)
    monkeypatch.setattr(runner.queue, "QUEUE_PATH", tmp_path / "q.xlsx")

    profile = profile_loader.load_profile()
    result = runner.run_finder(profile=profile, allow_stretch=True,
                                companies_path=companies_path)
    titles = [r.title for r in result.queue_rows]
    # With allow_stretch=True, the Senior posting is kept tagged as 'stretch'
    assert any("Senior" in t for t in titles)
    stretch_rows = [r for r in result.queue_rows if r.recommended_action == "stretch"]
    assert len(stretch_rows) >= 1
