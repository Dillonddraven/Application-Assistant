from __future__ import annotations

from pathlib import Path

import pytest

from job_apply import approval_queue, state


def _packet(*, slug: str = "acme_security-analyst", status: str = "draft", blocks: int = 0) -> dict:
    return {
        "job_id": "abc123def456",
        "slug": slug,
        "tailored": {"summary": "summary", "skills_emphasis": [], "bullets": [],
                     "cover_letter_paragraphs": [], "application_answers": []},
        "rendered": {"tailored_resume_md": "tailored_resume.md"},
        "validation": {
            "fabrication_blocks": [{"rule": "x", "detail": "boom", "source_id": None}] * blocks,
            "fabrication_warnings": [],
            "schema_ok": True,
        },
        "status": status,
        "approval_log": [{"ts": "2026-04-26T00:00:00+00:00", "action": "draft"}],
        "prompt_versions": {"tailor": "tailor_resume@v1"},
        "model": "test",
    }


def test_resolve_by_slug(workspace: Path):
    state.save_packet("acme_security-analyst", _packet())
    slug, pkt = approval_queue._resolve("acme_security-analyst")
    assert slug == "acme_security-analyst"
    assert pkt["job_id"] == "abc123def456"


def test_resolve_by_job_id(workspace: Path):
    state.save_packet("acme_security-analyst", _packet())
    slug, _ = approval_queue._resolve("abc123def456")
    assert slug == "acme_security-analyst"


def test_resolve_unknown_raises(workspace: Path):
    with pytest.raises(approval_queue.ApprovalError, match="no packet"):
        approval_queue._resolve("nope")


def test_approve_clean_flips_status(workspace: Path):
    state.save_packet("acme_security-analyst", _packet())
    pkt = approval_queue.approve("acme_security-analyst")
    assert pkt["status"] == "approved"
    assert any(e["action"] == "approve" for e in pkt["approval_log"])
    # persisted
    again = state.load_packet("acme_security-analyst")
    assert again and again["status"] == "approved"


def test_approve_with_blocks_refused(workspace: Path):
    state.save_packet("acme_security-analyst", _packet(blocks=2))
    with pytest.raises(approval_queue.ApprovalError, match="fabrication block"):
        approval_queue.approve("acme_security-analyst")
    pkt = state.load_packet("acme_security-analyst")
    # status unchanged
    assert pkt and pkt["status"] == "draft"


def test_skip_flips_status(workspace: Path):
    state.save_packet("acme_security-analyst", _packet())
    pkt = approval_queue.skip("acme_security-analyst")
    assert pkt["status"] == "skipped"


def test_skip_works_even_with_blocks(workspace: Path):
    state.save_packet("acme_security-analyst", _packet(blocks=3))
    pkt = approval_queue.skip("acme_security-analyst")
    assert pkt["status"] == "skipped"


def test_queue_filters_by_status(workspace: Path):
    state.save_packet("a_x", _packet(slug="a_x", status="draft"))
    state.save_packet("b_y", _packet(slug="b_y", status="approved"))
    state.save_packet("c_z", _packet(slug="c_z", status="skipped"))
    assert {p["slug"] for p in approval_queue.queue("draft")} == {"a_x"}
    assert {p["slug"] for p in approval_queue.queue("approved")} == {"b_y"}
    assert {p["slug"] for p in approval_queue.queue("all")} == {"a_x", "b_y", "c_z"}


def test_review_renders_blocks(workspace: Path):
    state.save_packet("acme_security-analyst", _packet(blocks=1))
    out = approval_queue.review("acme_security-analyst")
    assert "fabrication BLOCKS" in out
    assert "must fix" in out


def test_review_clean_shows_approve_hint(workspace: Path):
    state.save_packet("acme_security-analyst", _packet())
    out = approval_queue.review("acme_security-analyst")
    assert "approve" in out.lower()
