from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import openpyxl
import pytest

from job_apply import tracker, state


def _packet(*, job_id: str = "abc123def456", slug: str = "acme_security-analyst") -> dict:
    return {
        "job_id": job_id, "slug": slug,
        "tailored": {"summary": "x", "skills_emphasis": [], "bullets": [],
                     "cover_letter_paragraphs": [], "application_answers": []},
        "rendered": {}, "validation": {"fabrication_blocks": [], "fabrication_warnings": [],
                                       "schema_ok": True},
        "status": "draft", "approval_log": [], "prompt_versions": {"tailor": "tailor_resume@v1"},
        "model": "test",
    }


def _analyzed(**overrides) -> dict:
    base = {
        "id": "abc123def456", "company": "Acme Corp", "title": "Security Analyst",
        "location": "Tulsa, OK", "remote_mode": "hybrid",
        "source_url": "https://acme.example.com/jobs/sa", "fit_score": 75,
        "industry_filter": "ok",
    }
    base.update(overrides)
    return base


def test_upsert_creates_xlsx_and_row(workspace: Path):
    """Default upsert (no status arg) lands in 'packet_ready' state."""
    row = tracker.upsert(packet=_packet(), analyzed=_analyzed())
    assert row["submitted_status"] == "packet_ready"
    assert row["company"] == "Acme Corp"
    assert row["applied_date"] == date.today().isoformat()
    assert row["application_id"].startswith("a-")
    assert tracker.TRACKER_PATH.exists()


def test_upsert_legacy_status_translates_to_submitted(workspace: Path):
    """Legacy status='waiting' translates to submitted_status='submitted'."""
    row = tracker.upsert(packet=_packet(), analyzed=_analyzed(), status="waiting")
    assert row["submitted_status"] == "submitted"


def test_upsert_idempotent(workspace: Path):
    tracker.upsert(packet=_packet(), analyzed=_analyzed())
    tracker.upsert(packet=_packet(), analyzed=_analyzed())
    rows = tracker.list_rows()
    assert len(rows) == 1


def test_upsert_preserves_user_edits_on_reupsert(workspace: Path):
    tracker.upsert(packet=_packet(), analyzed=_analyzed())
    tracker.set_status(
        ident="acme_security-analyst", new_status="interview",
        notes="phone screen Wed",
    )
    # Re-running upsert (e.g., re-tailor) shouldn't downgrade the manual interview state
    row = tracker.upsert(packet=_packet(), analyzed=_analyzed())
    assert row["submitted_status"] == "interview"
    assert "phone screen Wed" in row["notes"]


def test_set_status_flips_submitted_status(workspace: Path):
    tracker.upsert(packet=_packet(), analyzed=_analyzed())
    row = tracker.set_status(
        ident="acme_security-analyst", new_status="submitted",
    )
    assert row["submitted_status"] == "submitted"
    assert row["submitted_date"] == date.today().isoformat()


def test_set_status_terminal_clears_followup(workspace: Path):
    tracker.upsert(packet=_packet(), analyzed=_analyzed())
    row = tracker.set_status(ident="acme_security-analyst", new_status="rejected")
    assert row["submitted_status"] == "rejected"
    assert row["next_followup_date"] == ""
    assert row["next_action"] == "skip"


def test_set_status_appends_notes(workspace: Path):
    tracker.upsert(packet=_packet(), analyzed=_analyzed())
    row = tracker.set_status(
        ident="acme_security-analyst", new_status="interview",
        notes="phone screen Tue 10am",
    )
    assert "phone screen Tue 10am" in row["notes"]


def test_set_status_unknown_raises(workspace: Path):
    tracker.upsert(packet=_packet(), analyzed=_analyzed())
    with pytest.raises(tracker.TrackerError, match="unknown status"):
        tracker.set_status(ident="acme_security-analyst", new_status="ghosted")


def test_set_status_missing_raises(workspace: Path):
    tracker.upsert(packet=_packet(), analyzed=_analyzed())
    with pytest.raises(tracker.TrackerError, match="no application"):
        tracker.set_status(ident="not-a-real-slug", new_status="rejected")


def test_set_status_accepts_application_id(workspace: Path):
    """set_status should also work when given the short application_id."""
    row = tracker.upsert(packet=_packet(), analyzed=_analyzed())
    aid = row["application_id"]
    updated = tracker.set_status(ident=aid, new_status="submitted")
    assert updated["submitted_status"] == "submitted"


def test_list_rows_filter_by_submitted_status(workspace: Path):
    tracker.upsert(packet=_packet(slug="a_x"), analyzed=_analyzed())
    tracker.upsert(packet=_packet(job_id="bbbbbbbbbbbb", slug="b_y"),
                   analyzed=_analyzed(company="Beta"))
    tracker.set_status(ident="b_y", new_status="rejected")
    packet_ready = tracker.list_rows(status="packet_ready")
    rejected = tracker.list_rows(status="rejected")
    assert {r["slug"] for r in packet_ready} == {"a_x"}
    assert {r["slug"] for r in rejected} == {"b_y"}


def test_due_followups_excludes_terminal(workspace: Path):
    tracker.upsert(packet=_packet(), analyzed=_analyzed())
    tracker.set_status(ident="acme_security-analyst", new_status="rejected")
    rows = tracker.due_followups(by=date.today() + timedelta(days=99))
    assert rows == []


def test_status_cell_has_color_fill(workspace: Path):
    tracker.upsert(packet=_packet(), analyzed=_analyzed())
    wb = openpyxl.load_workbook(str(tracker.TRACKER_PATH))
    ws = wb["applications"]
    cell = ws.cell(row=2, column=tracker.COLUMNS.index("submitted_status") + 1)
    # packet_ready blue
    assert cell.fill.fgColor.value.upper().endswith("DDE8F7")


def test_render_table_shows_new_columns(workspace: Path):
    tracker.upsert(packet=_packet(), analyzed=_analyzed())
    out = tracker.render_table(tracker.list_rows())
    assert "STATUS" in out and "NEXT" in out and "Acme Corp" in out


def test_render_table_empty(workspace: Path):
    assert tracker.render_table([]) == "(no applications tracked yet)"


def test_approve_auto_logs_to_tracker(workspace: Path):
    """approval_queue.approve should populate tracker with the new schema."""
    from job_apply import approval_queue
    state.save_analyzed("abc123def456", _analyzed())
    state.save_packet("acme_security-analyst", _packet())
    pkt = approval_queue.approve("acme_security-analyst")
    assert pkt["status"] == "approved"
    rows = tracker.list_rows()
    assert len(rows) == 1
    # The legacy 'waiting' status from approve flows through translate -> 'submitted'
    assert rows[0]["submitted_status"] == "submitted"
    assert rows[0]["company"] == "Acme Corp"
    assert rows[0]["application_id"].startswith("a-")


def test_mark_email_created_advances_state(workspace: Path):
    tracker.upsert(packet=_packet(), analyzed=_analyzed())
    row = tracker.mark_email_created("acme_security-analyst", mode="single")
    assert row is not None
    assert row["submitted_status"] == "emailed_to_dillon"
    assert "single" in row["email_created"]
    assert row["next_action"] == "submit_portal"


def test_mark_email_created_does_not_downgrade(workspace: Path):
    """If the user already marked it 'submitted', email_created shouldn't reset that."""
    tracker.upsert(packet=_packet(), analyzed=_analyzed())
    tracker.set_status(ident="acme_security-analyst", new_status="submitted")
    row = tracker.mark_email_created("acme_security-analyst", mode="company-bundle")
    assert row["submitted_status"] == "submitted"   # not downgraded
    assert "company-bundle" in row["email_created"]
