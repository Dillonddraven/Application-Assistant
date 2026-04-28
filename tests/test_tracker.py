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
    row = tracker.upsert(packet=_packet(), analyzed=_analyzed(), status="waiting")
    assert row["status"] == "waiting"
    assert row["company"] == "Acme Corp"
    assert row["applied_date"] == date.today().isoformat()
    expected_followup = (date.today() + timedelta(days=7)).isoformat()
    assert row["next_followup_date"] == expected_followup
    # File written
    assert tracker.TRACKER_PATH.exists()


def test_upsert_idempotent(workspace: Path):
    tracker.upsert(packet=_packet(), analyzed=_analyzed(), status="waiting")
    tracker.upsert(packet=_packet(), analyzed=_analyzed(), status="waiting")
    rows = tracker.list_rows()
    assert len(rows) == 1


def test_set_status_flips_and_recomputes_followup(workspace: Path):
    tracker.upsert(packet=_packet(), analyzed=_analyzed(), status="waiting")
    row = tracker.set_status(ident="acme_security-analyst", new_status="interview_pending")
    assert row["status"] == "interview_pending"
    expected = (date.today() + timedelta(days=14)).isoformat()
    assert row["next_followup_date"] == expected


def test_set_status_terminal_clears_followup(workspace: Path):
    tracker.upsert(packet=_packet(), analyzed=_analyzed(), status="waiting")
    row = tracker.set_status(ident="acme_security-analyst", new_status="rejected")
    assert row["status"] == "rejected"
    assert row["next_followup_date"] == ""


def test_set_status_appends_notes(workspace: Path):
    tracker.upsert(packet=_packet(), analyzed=_analyzed(), status="waiting")
    row = tracker.set_status(
        ident="acme_security-analyst", new_status="interview_pending",
        notes="phone screen Tue 10am",
    )
    assert "phone screen Tue 10am" in row["notes"]


def test_set_status_unknown_raises(workspace: Path):
    tracker.upsert(packet=_packet(), analyzed=_analyzed(), status="waiting")
    with pytest.raises(tracker.TrackerError, match="unknown status"):
        tracker.set_status(ident="acme_security-analyst", new_status="ghosted")


def test_set_status_missing_raises(workspace: Path):
    tracker.upsert(packet=_packet(), analyzed=_analyzed(), status="waiting")
    with pytest.raises(tracker.TrackerError, match="no application"):
        tracker.set_status(ident="not-a-real-slug", new_status="rejected")


def test_list_rows_filter_by_status(workspace: Path):
    tracker.upsert(packet=_packet(slug="a_x"), analyzed=_analyzed(), status="waiting")
    tracker.upsert(packet=_packet(job_id="bbbbbbbbbbbb", slug="b_y"),
                   analyzed=_analyzed(company="Beta"), status="waiting")
    tracker.set_status(ident="b_y", new_status="rejected")
    waiting = tracker.list_rows(status="waiting")
    rejected = tracker.list_rows(status="rejected")
    assert {r["slug"] for r in waiting} == {"a_x"}
    assert {r["slug"] for r in rejected} == {"b_y"}


def test_due_followups_today(workspace: Path):
    tracker.upsert(packet=_packet(), analyzed=_analyzed(), status="waiting")
    rows = tracker.due_followups(by=date.today() + timedelta(days=8))
    assert len(rows) == 1
    rows_now = tracker.due_followups(by=date.today())
    assert rows_now == []


def test_due_followups_excludes_terminal(workspace: Path):
    tracker.upsert(packet=_packet(), analyzed=_analyzed(), status="waiting")
    tracker.set_status(ident="acme_security-analyst", new_status="rejected")
    rows = tracker.due_followups(by=date.today() + timedelta(days=99))
    assert rows == []


def test_status_cell_has_color_fill(workspace: Path):
    tracker.upsert(packet=_packet(), analyzed=_analyzed(), status="waiting")
    wb = openpyxl.load_workbook(str(tracker.TRACKER_PATH))
    ws = wb["applications"]
    # row 2 is the data row; "status" is column 11
    cell = ws.cell(row=2, column=tracker.COLUMNS.index("status") + 1)
    assert cell.fill.fgColor.value.upper().endswith("FFF7D6")  # waiting yellow


def test_render_table_shows_headers(workspace: Path):
    tracker.upsert(packet=_packet(), analyzed=_analyzed(), status="waiting")
    out = tracker.render_table(tracker.list_rows())
    assert "STATUS" in out and "FIT" in out and "Acme Corp" in out


def test_render_table_empty(workspace: Path):
    assert tracker.render_table([]) == "(no applications tracked yet)"


def test_approve_auto_logs_to_tracker(workspace: Path, tmp_path: Path):
    """approval_queue.approve should populate tracker automatically."""
    from job_apply import approval_queue
    # Set up an analyzed job + draft packet
    state.save_analyzed("abc123def456", _analyzed())
    state.save_packet("acme_security-analyst", _packet())
    pkt = approval_queue.approve("acme_security-analyst")
    assert pkt["status"] == "approved"
    rows = tracker.list_rows()
    assert len(rows) == 1
    assert rows[0]["status"] == "waiting"
    assert rows[0]["company"] == "Acme Corp"
