from __future__ import annotations

import json
import argparse
from pathlib import Path

import pytest

from job_apply import cli, contact_research, state


# -------- email pattern detection --------

def test_detect_first_last():
    assert contact_research.detect_pattern(
        "alice.smith@asana.com", "Alice Smith") == "first.last"


def test_detect_flast():
    assert contact_research.detect_pattern(
        "asmith@example.com", "Alice Smith") == "flast"


def test_detect_first_only():
    assert contact_research.detect_pattern(
        "alice@example.com", "Alice Smith") == "first"


def test_detect_handles_middle_name():
    """Middle names are stripped before matching."""
    assert contact_research.detect_pattern(
        "alice.smith@example.com", "Alice Mae Smith") == "first.last"


def test_detect_returns_none_on_mismatch():
    assert contact_research.detect_pattern(
        "weirdname@example.com", "Alice Smith") is None


def test_detect_returns_none_on_empty():
    assert contact_research.detect_pattern("", "Alice Smith") is None
    assert contact_research.detect_pattern("a@b.com", "") is None


# -------- candidate emails --------

def test_candidate_emails_pinned_pattern_is_first():
    out = contact_research.candidate_emails(
        target_name="Bob Jones", domain="example.com", pattern="flast")
    assert out[0] == {"pattern": "flast", "address": "bjones@example.com"}


def test_candidate_emails_dedupes_when_pinned_already_in_priority():
    out = contact_research.candidate_emails(
        target_name="Bob Jones", domain="example.com", pattern="first.last")
    addrs = [c["address"] for c in out]
    assert addrs.count("bob.jones@example.com") == 1


def test_candidate_emails_skips_last_patterns_when_no_last_name():
    out = contact_research.candidate_emails(
        target_name="Cher", domain="example.com")
    addrs = {c["address"] for c in out}
    assert "cher@example.com" in addrs
    # No "first.last" pattern variants
    for a in addrs:
        assert "." not in a.split("@", 1)[0]


def test_candidate_emails_returns_empty_when_no_domain():
    assert contact_research.candidate_emails(
        target_name="Bob Jones", domain="") == []


# -------- search URLs --------

def test_search_urls_basic_company_only():
    urls = contact_research.search_urls(company="Asana")
    assert "linkedin_company_people" in urls
    assert "google_linkedin_recruiter" in urls
    assert "github_org" in urls
    assert "Asana" in urls["linkedin_company_people"]


def test_search_urls_with_role_adds_hiring_manager_search():
    urls = contact_research.search_urls(
        company="Asana", role_title="Security Risk and Compliance Analyst")
    assert "google_linkedin_hiring_manager" in urls
    assert "google_linkedin_team_members" in urls


def test_search_urls_with_department():
    urls = contact_research.search_urls(
        company="Acme", role_title="Analyst", department="Security")
    assert "google_linkedin_department" in urls


def test_search_urls_url_encodes_company_with_spaces():
    urls = contact_research.search_urls(company="Acme Corp")
    assert "Acme+Corp" in urls["linkedin_company_people"]
    # GitHub uses dashes/lowercase
    assert urls["github_org"] == "https://github.com/acme-corp"


def test_search_urls_empty_when_no_company():
    assert contact_research.search_urls(company="") == {}


# -------- artifact builder --------

def test_build_artifact_full_round_trip():
    art = contact_research.build_artifact(
        company="Asana", role_title="Security Analyst", department="Security",
        seed_email="alice.smith@asana.com", seed_name="Alice Smith",
        target_names=["Jane Doe", "John Roe"],
    )
    assert art.detected_pattern == "first.last"
    assert art.company_domain == "asana.com"
    assert "linkedin_company_people" in art.search_links
    # Both targets get candidate emails, with the detected pattern first
    assert art.candidate_emails_by_target["Jane Doe"][0] == {
        "pattern": "first.last", "address": "jane.doe@asana.com",
    }
    assert art.candidate_emails_by_target["John Roe"][0] == {
        "pattern": "first.last", "address": "john.roe@asana.com",
    }


def test_build_artifact_without_seed_skips_pattern_detection():
    art = contact_research.build_artifact(
        company="Asana", role_title="Security Analyst",
        company_domain="asana.com",
        target_names=["Jane Doe"],
    )
    assert art.detected_pattern is None
    # Without a detected pattern, all priority patterns are emitted
    cands = art.candidate_emails_by_target["Jane Doe"]
    assert len(cands) >= 6
    addrs = {c["address"] for c in cands}
    assert "jane.doe@asana.com" in addrs
    assert "jdoe@asana.com" in addrs


# -------- write_artifact --------

def test_write_artifact_creates_md_and_json(workspace: Path):
    art = contact_research.build_artifact(
        company="Asana", role_title="Security Analyst",
        seed_email="alice.smith@asana.com", seed_name="Alice Smith",
        target_names=["Jane Doe"],
    )
    json_path, md_path = contact_research.write_artifact(
        slug="asana_security-analyst", art=art)
    assert json_path.exists() and md_path.exists()
    md = md_path.read_text()
    assert "Asana" in md
    assert "Security Analyst" in md
    assert "first.last" in md
    assert "jane.doe@asana.com" in md
    payload = json.loads(json_path.read_text())
    assert payload["company"] == "Asana"
    assert payload["detected_pattern"] == "first.last"


# -------- CLI --------

def _seed_packet(workspace: Path, *, slug="asana_security-analyst",
                  job_id="abc123def456", company="Asana",
                  title="Security Analyst"):
    state.save_analyzed(job_id, {
        "id": job_id, "company": company, "title": title,
        "location": "Remote", "remote_mode": "remote",
        "source_url": "https://example.com/jobs/x", "fit_score": 70,
        "industry_filter": "ok",
    })
    state.save_packet(slug, {
        "job_id": job_id, "slug": slug, "fit_score": 70,
        "tailored": {"summary": "x", "skills_emphasis": [], "bullets": [],
                     "cover_letter_paragraphs": [], "application_answers": []},
        "rendered": {}, "validation": {"fabrication_blocks": [],
                                        "fabrication_warnings": [], "schema_ok": True},
        "status": "draft", "approval_log": [],
        "prompt_versions": {"tailor": "tailor_resume@v1"}, "model": "test",
    })


def test_cli_contacts_writes_artifacts(workspace: Path, capsys):
    _seed_packet(workspace)
    args = argparse.Namespace(
        ident="asana_security-analyst",
        company="", role="", department="", company_domain="",
        known_email="alice.smith@asana.com", known_name="Alice Smith",
        target_name=["Jane Doe"],
    )
    rc = cli._cmd_contacts(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "contacts.md" in out
    assert "first.last" in out
    pkt_dir = workspace / "outputs" / "asana_security-analyst" / "internal"
    assert (pkt_dir / "contacts.md").exists()
    assert (pkt_dir / "contacts.json").exists()


def test_cli_contacts_pulls_company_from_analyzed_when_not_overridden(workspace: Path, capsys):
    _seed_packet(workspace)
    args = argparse.Namespace(
        ident="asana_security-analyst",
        company="", role="", department="", company_domain="asana.com",
        known_email="", known_name="", target_name=[],
    )
    cli._cmd_contacts(args)
    pkt_dir = workspace / "outputs" / "asana_security-analyst" / "internal"
    payload = json.loads((pkt_dir / "contacts.json").read_text())
    assert payload["company"] == "Asana"
    assert payload["role_title"] == "Security Analyst"


def test_cli_contacts_warns_when_no_company(workspace: Path, capsys):
    """If we can't resolve a company anywhere, surface that to the user."""
    state.save_analyzed("xyzxyzxyzxyz", {
        "id": "xyzxyzxyzxyz", "company": "", "title": "Analyst",
        "location": "", "remote_mode": "", "source_url": "https://x/j",
        "fit_score": 50, "industry_filter": "ok",
    })
    state.save_packet("nameless_analyst", {
        "job_id": "xyzxyzxyzxyz", "slug": "nameless_analyst",
        "tailored": {}, "rendered": {},
        "validation": {"fabrication_blocks": [], "fabrication_warnings": [],
                        "schema_ok": True},
        "status": "draft", "approval_log": [],
        "prompt_versions": {}, "model": "test",
    })
    args = argparse.Namespace(
        ident="nameless_analyst",
        company="", role="", department="", company_domain="",
        known_email="", known_name="", target_name=[],
    )
    cli._cmd_contacts(args)
    out = capsys.readouterr().out
    assert "no company" in out.lower()
