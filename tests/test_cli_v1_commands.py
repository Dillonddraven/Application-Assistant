"""Integration tests for the V1 usage-upgrade CLI commands: set-status, pack,
pack-company, finder-approve, email. We exercise the handlers directly (not
via subprocess) so the workspace fixture's monkeypatched paths apply."""
from __future__ import annotations

import argparse
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from job_apply import cli, state, tracker
from job_apply.finder import queue as fq


# --------- helpers ---------

def _packet(**overrides) -> dict:
    base = {
        "job_id": "abc123def456",
        "slug": "acme_security-analyst",
        "tailored": {"summary": "x", "skills_emphasis": [], "bullets": [],
                     "cover_letter_paragraphs": [], "application_answers": []},
        "rendered": {},
        "validation": {"fabrication_blocks": [], "fabrication_warnings": [],
                       "schema_ok": True},
        "status": "draft",
        "approval_log": [],
        "prompt_versions": {"tailor": "tailor_resume@v1"},
        "model": "test",
        "production_status": "portal_ready",
        "strategic_interest": "high",
        "fit_score": 78,
        "run_id": "r-test-01",
    }
    base.update(overrides)
    return base


def _analyzed(**overrides) -> dict:
    base = {
        "id": "abc123def456", "company": "Acme Corp",
        "title": "Security Analyst",
        "location": "Tulsa, OK", "remote_mode": "hybrid",
        "source_url": "https://acme.example.com/jobs/sa", "fit_score": 78,
        "industry_filter": "ok",
    }
    base.update(overrides)
    return base


def _seed_packet_with_files(workspace: Path, *, slug="acme_security-analyst",
                              job_id="abc123def456", company="Acme Corp",
                              title="Security Analyst", url="https://acme/jobs/sa"):
    state.save_analyzed(job_id, _analyzed(id=job_id, company=company,
                                            title=title, source_url=url))
    state.save_packet(slug, _packet(slug=slug, job_id=job_id))
    pkt_dir = workspace / "outputs" / slug / "employer"
    pkt_dir.mkdir(parents=True, exist_ok=True)
    (pkt_dir / "tailored_resume.pdf").write_bytes(b"%PDF-r")
    (pkt_dir / "cover_letter.pdf").write_bytes(b"%PDF-c")


def _seed_secrets(workspace: Path, email: str = "dillon@example.com"):
    (workspace / "profile" / "secrets.yaml").write_text(
        yaml.safe_dump({"email": email})
    )


def _seed_minimal_profile(workspace: Path):
    (workspace / "profile" / "master_profile.yaml").write_text(yaml.safe_dump({
        "identity": {"full_name": "T", "citizenship": "US", "work_auth": "yes"},
        "education": [{"id": "x", "school": "X", "degree": "BA CIS",
                       "status": "in_progress"}],
        "skills": {"technical": ["Python"]},
        "preferences": {"target_roles": ["Security Analyst"], "industries_avoid": []},
    }))


# --------- set-status ---------

def test_set_status_flips_submitted_status(workspace: Path, capsys):
    """First need a tracker row -> insert via tracker.upsert."""
    tracker.upsert(packet=_packet(), analyzed=_analyzed())
    args = argparse.Namespace(ident="acme_security-analyst",
                              status="submitted", notes="applied via Workday")
    rc = cli._cmd_set_status(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "submitted" in out
    rows = tracker.list_rows()
    assert rows[0]["submitted_status"] == "submitted"
    assert "applied via Workday" in rows[0]["notes"]


def test_set_status_unknown_returns_1(workspace: Path, capsys):
    tracker.upsert(packet=_packet(), analyzed=_analyzed())
    args = argparse.Namespace(ident="acme_security-analyst",
                              status="ghosted", notes="")
    # argparse choices guards real CLI invocation; bypassed here so we check
    # the function-level error path
    with pytest.raises(SystemExit) if False else _noop():
        rc = cli._cmd_set_status(args)
        assert rc == 1


class _noop:
    def __enter__(self): return self
    def __exit__(self, *a): return False


# --------- pack ---------

def test_pack_writes_readme_apply_url_and_email_md(workspace: Path, capsys):
    _seed_packet_with_files(workspace)
    _seed_minimal_profile(workspace)
    _seed_secrets(workspace)
    args = argparse.Namespace(
        ident="acme_security-analyst", apply_url="https://acme/jobs/sa",
        to="", mail=False, update_tracker=False,
    )
    rc = cli._cmd_pack(args)
    assert rc == 0
    pkt_dir = workspace / "outputs" / "acme_security-analyst"
    assert (pkt_dir / "apply_url.txt").read_text().strip() == "https://acme/jobs/sa"
    assert (pkt_dir / "internal" / "README_APPLY.md").exists()
    assert (pkt_dir / "internal" / "email_to_dillon.md").exists()
    out = capsys.readouterr().out
    assert "README_APPLY.md" in out
    assert "email_to_dillon.md" in out


def test_pack_updates_tracker_when_flag_set(workspace: Path, capsys):
    _seed_packet_with_files(workspace)
    _seed_minimal_profile(workspace)
    _seed_secrets(workspace)
    args = argparse.Namespace(
        ident="acme_security-analyst", apply_url="https://acme/jobs/sa",
        to="", mail=False, update_tracker=True,
    )
    rc = cli._cmd_pack(args)
    assert rc == 0
    rows = tracker.list_rows()
    assert len(rows) == 1
    assert rows[0]["submitted_status"] == "emailed_to_dillon"
    assert rows[0]["next_action"] == "submit_portal"


def test_pack_missing_packet_raises_systemexit(workspace: Path):
    args = argparse.Namespace(
        ident="not-a-slug", apply_url="", to="", mail=False, update_tracker=False,
    )
    with pytest.raises(SystemExit, match="no packet found"):
        cli._cmd_pack(args)


def test_pack_uses_analyzed_source_url_as_default(workspace: Path):
    _seed_packet_with_files(workspace)
    _seed_minimal_profile(workspace)
    _seed_secrets(workspace)
    args = argparse.Namespace(
        ident="acme_security-analyst", apply_url="",
        to="", mail=False, update_tracker=False,
    )
    cli._cmd_pack(args)
    pkt_dir = workspace / "outputs" / "acme_security-analyst"
    assert (pkt_dir / "apply_url.txt").read_text().strip() == "https://acme/jobs/sa"


# --------- pack-company ---------

def test_pack_company_bundles_approved_rows(workspace: Path, tmp_path: Path,
                                              monkeypatch: pytest.MonkeyPatch,
                                              capsys):
    # Two roles at Acme, one at Beta; only Acme rows get approved
    _seed_packet_with_files(workspace, slug="acme_sa", job_id="aaaaaaaaaaaa",
                             url="https://acme/jobs/sa", title="Security Analyst")
    _seed_packet_with_files(workspace, slug="acme_soc", job_id="bbbbbbbbbbbb",
                             url="https://acme/jobs/soc", title="SOC Analyst")
    _seed_packet_with_files(workspace, slug="beta_sa", job_id="cccccccccccc",
                             company="Beta Inc", url="https://beta/jobs/sa",
                             title="Security Analyst")
    _seed_minimal_profile(workspace)
    _seed_secrets(workspace)

    queue_path = workspace / "runs" / "_finder_queue.xlsx"
    monkeypatch.setattr(fq, "QUEUE_PATH", queue_path)
    rows = [
        fq.FinderQueueRow(company="Acme Corp", title="Security Analyst",
                           url="https://acme/jobs/sa", ats="greenhouse",
                           company_group_id="acme",
                           approved_for_packet="y"),
        fq.FinderQueueRow(company="Acme Corp", title="SOC Analyst",
                           url="https://acme/jobs/soc", ats="greenhouse",
                           company_group_id="acme",
                           approved_for_packet="y"),
        fq.FinderQueueRow(company="Beta Inc", title="Security Analyst",
                           url="https://beta/jobs/sa", ats="greenhouse",
                           company_group_id="beta",
                           approved_for_packet=""),
    ]
    fq.save_queue(rows, queue_path)

    args = argparse.Namespace(company="acme", include_unapproved=False,
                              to="", mail=False)
    rc = cli._cmd_pack_company(args)
    assert rc == 0
    bundle_dir = workspace / "outputs" / "acme__bundle" / "internal"
    assert (bundle_dir / "company_outreach.md").exists()
    assert (bundle_dir / "email_to_dillon.md").exists()
    out = capsys.readouterr().out
    assert "2 role(s)" in out
    # Beta should not appear since not approved
    bundle_text = (bundle_dir / "email_to_dillon.md").read_text()
    assert "Beta Inc" not in bundle_text


def test_pack_company_no_approved_rows_returns_1(workspace: Path,
                                                    monkeypatch: pytest.MonkeyPatch,
                                                    capsys):
    queue_path = workspace / "runs" / "_finder_queue.xlsx"
    monkeypatch.setattr(fq, "QUEUE_PATH", queue_path)
    rows = [
        fq.FinderQueueRow(company="Acme Corp", title="Security Analyst",
                           url="https://acme/jobs/sa", ats="greenhouse",
                           company_group_id="acme", approved_for_packet=""),
    ]
    fq.save_queue(rows, queue_path)
    _seed_minimal_profile(workspace)
    _seed_secrets(workspace)
    args = argparse.Namespace(company="acme", include_unapproved=False,
                              to="", mail=False)
    rc = cli._cmd_pack_company(args)
    assert rc == 1
    err = capsys.readouterr().err
    assert "no approved_for_packet=y" in err


def test_pack_company_no_matches_returns_1(workspace: Path,
                                              monkeypatch: pytest.MonkeyPatch,
                                              capsys):
    queue_path = workspace / "runs" / "_finder_queue.xlsx"
    monkeypatch.setattr(fq, "QUEUE_PATH", queue_path)
    fq.save_queue([], queue_path)
    args = argparse.Namespace(company="nonexistent", include_unapproved=False,
                              to="", mail=False)
    rc = cli._cmd_pack_company(args)
    assert rc == 1


# --------- finder-approve ---------

def test_finder_approve_marks_row(workspace: Path,
                                    monkeypatch: pytest.MonkeyPatch,
                                    capsys):
    queue_path = workspace / "runs" / "_finder_queue.xlsx"
    monkeypatch.setattr(fq, "QUEUE_PATH", queue_path)
    rows = [
        fq.FinderQueueRow(company="Acme Corp", title="Security Analyst",
                           url="https://acme/jobs/sa", ats="greenhouse",
                           company_group_id="acme", review_status="new"),
    ]
    fq.save_queue(rows, queue_path)
    args = argparse.Namespace(ident="acme/jobs/sa", notes="apply tomorrow")
    rc = cli._cmd_finder_approve(args)
    assert rc == 0
    rows2 = fq.load_queue(queue_path)
    assert rows2[0].approved_for_packet == "y"
    assert rows2[0].review_status == "approved"
    assert "apply tomorrow" in rows2[0].user_notes


def test_finder_approve_matches_company_title_substring(workspace: Path,
                                                            monkeypatch: pytest.MonkeyPatch):
    queue_path = workspace / "runs" / "_finder_queue.xlsx"
    monkeypatch.setattr(fq, "QUEUE_PATH", queue_path)
    rows = [
        fq.FinderQueueRow(company="Acme Corp", title="Security Analyst",
                           url="https://x/1", ats="greenhouse"),
    ]
    fq.save_queue(rows, queue_path)
    args = argparse.Namespace(ident="security analyst", notes="")
    rc = cli._cmd_finder_approve(args)
    assert rc == 0


def test_finder_approve_no_match_returns_1(workspace: Path,
                                              monkeypatch: pytest.MonkeyPatch,
                                              capsys):
    queue_path = workspace / "runs" / "_finder_queue.xlsx"
    monkeypatch.setattr(fq, "QUEUE_PATH", queue_path)
    fq.save_queue([], queue_path)
    args = argparse.Namespace(ident="nothing-here", notes="")
    rc = cli._cmd_finder_approve(args)
    assert rc == 1


# --------- email ---------

def test_email_md_only_writes_md_and_skips_mail(workspace: Path, capsys):
    _seed_packet_with_files(workspace)
    _seed_minimal_profile(workspace)
    _seed_secrets(workspace)
    args = argparse.Namespace(
        ident="acme_security-analyst", apply_url="", to="", md_only=True,
    )
    with patch("job_apply.mail_draft.open_draft") as mock_open:
        rc = cli._cmd_email(args)
        assert rc == 0
        mock_open.assert_not_called()
    md = workspace / "outputs" / "acme_security-analyst" / "internal" / "email_to_dillon.md"
    assert md.exists()


def test_email_opens_mail_draft_when_not_md_only(workspace: Path, capsys):
    _seed_packet_with_files(workspace)
    _seed_minimal_profile(workspace)
    _seed_secrets(workspace)
    args = argparse.Namespace(
        ident="acme_security-analyst", apply_url="", to="dillon@x.com", md_only=False,
    )
    with patch("job_apply.mail_draft.open_draft") as mock_open:
        rc = cli._cmd_email(args)
        assert rc == 0
        mock_open.assert_called_once()
        kwargs = mock_open.call_args.kwargs
        assert kwargs["to_addr"] == "dillon@x.com"
