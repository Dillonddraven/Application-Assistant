"""Mail draft tests — mock subprocess.run so we don't actually open Mail."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from job_apply import mail_draft


def _make_files(tmp: Path, names: list[str]) -> list[Path]:
    out = []
    for n in names:
        p = tmp / n
        p.write_text("x")
        out.append(p)
    return out


def test_open_draft_invokes_osascript(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    files = _make_files(tmp_path, ["a.pdf", "b.docx", "c.md"])
    captured: dict = {}

    def fake_run(cmd, input=None, text=None, capture_output=None, timeout=None):  # noqa
        captured["cmd"] = cmd
        captured["input"] = input
        return subprocess.CompletedProcess(cmd, 0, stdout="ok\n", stderr="")

    monkeypatch.setattr(mail_draft.subprocess, "run", fake_run)
    mail_draft.open_draft(
        to_addr="me@example.com", subject="Subj", body="Hello\nworld",
        attachments=files,
    )
    assert "/osascript" in captured["cmd"][0] or captured["cmd"][0].endswith("osascript")
    script = captured["input"]
    assert 'address:"me@example.com"' in script
    assert 'subject:"Subj"' in script
    # All three files referenced
    for f in files:
        assert str(f.resolve()) in script
    # `at end` pattern (avoids the -1712 timeout bug)
    assert "at end" in script


def test_missing_attachment_raises(tmp_path: Path):
    with pytest.raises(mail_draft.MailDraftError, match="missing attachment"):
        mail_draft.open_draft(
            to_addr="x@y.com", subject="s", body="b",
            attachments=[tmp_path / "nope.pdf"],
        )


def test_no_attachments_raises():
    with pytest.raises(mail_draft.MailDraftError, match="no attachments"):
        mail_draft.open_draft(to_addr="x@y.com", subject="s", body="b", attachments=[])


def test_osascript_failure_surfaces(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    files = _make_files(tmp_path, ["a.pdf"])

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess([], 1, stdout="", stderr="execution error: (-1712)")

    monkeypatch.setattr(mail_draft.subprocess, "run", fake_run)
    with pytest.raises(mail_draft.MailDraftError, match="-1712"):
        mail_draft.open_draft(
            to_addr="x@y.com", subject="s", body="b", attachments=files,
        )


def test_quotes_and_newlines_escaped(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    files = _make_files(tmp_path, ["a.pdf"])
    captured = {}

    def fake_run(cmd, input=None, **kwargs):
        captured["input"] = input
        return subprocess.CompletedProcess(cmd, 0, "ok", "")

    monkeypatch.setattr(mail_draft.subprocess, "run", fake_run)
    mail_draft.open_draft(
        to_addr="me@example.com",
        subject='With "quotes" — and dash',
        body='Line 1\nLine "2"',
        attachments=files,
    )
    s = captured["input"]
    # Quotes escaped
    assert 'With \\"quotes\\"' in s
    # Newlines escaped (so AppleScript stays one line)
    assert "Line 1\\nLine" in s


def test_packet_attachments_legacy_layout_still_works(tmp_path: Path):
    """Pre-split packets had everything at the top of out_dir — keep working."""
    out = tmp_path / "out"
    out.mkdir()
    (out / "tailored_resume.pdf").write_bytes(b"x")
    (out / "linkedin_dm.md").write_text("x")
    paths = mail_draft.packet_attachments(out)
    names = [p.name for p in paths]
    assert "tailored_resume.pdf" in names
    assert "linkedin_dm.md" in names
    assert "cover_letter.pdf" not in names


def test_packet_attachments_employer_mode_only_includes_pdf_docx(tmp_path: Path):
    out = tmp_path / "out"
    (out / "employer").mkdir(parents=True)
    (out / "internal").mkdir(parents=True)
    (out / "employer" / "tailored_resume.pdf").write_bytes(b"x")
    (out / "employer" / "tailored_resume.docx").write_bytes(b"x")
    (out / "employer" / "cover_letter.pdf").write_bytes(b"x")
    (out / "employer" / "cover_letter.docx").write_bytes(b"x")
    (out / "internal" / "outreach_recruiter.md").write_text("x")
    (out / "internal" / "linkedin_dm.md").write_text("x")
    (out / "internal" / "match_report.md").write_text("x")

    employer_paths = mail_draft.packet_attachments(out, mode="employer")
    employer_names = [p.name for p in employer_paths]
    # Only PDF + DOCX; no markdown leaks
    assert sorted(employer_names) == sorted([
        "tailored_resume.pdf", "tailored_resume.docx",
        "cover_letter.pdf", "cover_letter.docx",
    ])
    assert not any(n.endswith(".md") for n in employer_names)
    assert not any("match_report" in n for n in employer_names)
    assert not any("packet.json" in n for n in employer_names)


def test_packet_attachments_review_mode_includes_internal(tmp_path: Path):
    out = tmp_path / "out"
    (out / "employer").mkdir(parents=True)
    (out / "internal").mkdir(parents=True)
    (out / "employer" / "tailored_resume.pdf").write_bytes(b"x")
    (out / "internal" / "match_report.md").write_text("x")
    review_paths = mail_draft.packet_attachments(out, mode="review")
    names = [p.name for p in review_paths]
    assert "tailored_resume.pdf" in names
    assert "match_report.md" in names


def test_packet_attachments_unknown_mode_raises(tmp_path: Path):
    with pytest.raises(ValueError, match="unknown mode"):
        mail_draft.packet_attachments(tmp_path, mode="weird")


def test_open_draft_invalid_email_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    files = _make_files(tmp_path, ["a.pdf"])
    with pytest.raises(mail_draft.MailDraftError, match="doesn't look like an email"):
        mail_draft.open_draft(
            to_addr="not-an-email", subject="Subj", body="Body",
            attachments=files,
        )


def test_open_draft_empty_subject_raises(tmp_path: Path):
    files = _make_files(tmp_path, ["a.pdf"])
    with pytest.raises(mail_draft.MailDraftError, match="subject is empty"):
        mail_draft.open_draft(
            to_addr="me@example.com", subject="  ", body="Body",
            attachments=files,
        )


def test_open_draft_empty_body_raises(tmp_path: Path):
    files = _make_files(tmp_path, ["a.pdf"])
    with pytest.raises(mail_draft.MailDraftError, match="body is empty"):
        mail_draft.open_draft(
            to_addr="me@example.com", subject="Subj", body="  ",
            attachments=files,
        )


def test_open_draft_total_attachment_size_cap(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    big = tmp_path / "huge.bin"
    big.write_bytes(b"\0" * (21 * 1024 * 1024))  # 21 MB > 20 MB cap
    with pytest.raises(mail_draft.MailDraftError, match="exceeds.*MB cap"):
        mail_draft.open_draft(
            to_addr="me@example.com", subject="Subj", body="Body",
            attachments=[big],
        )


def test_open_draft_too_many_attachments(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    files = _make_files(tmp_path, [f"f{i}.txt" for i in range(30)])
    with pytest.raises(mail_draft.MailDraftError, match="too many attachments"):
        mail_draft.open_draft(
            to_addr="me@example.com", subject="Subj", body="Body",
            attachments=files,
        )
