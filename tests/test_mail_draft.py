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


def test_packet_attachments_lists_existing_files(tmp_path: Path):
    out = tmp_path / "out"
    out.mkdir()
    (out / "tailored_resume.pdf").write_bytes(b"x")
    (out / "linkedin_dm.md").write_text("x")
    # Don't create cover_letter.pdf etc.
    paths = mail_draft.packet_attachments(out)
    names = [p.name for p in paths]
    assert "tailored_resume.pdf" in names
    assert "linkedin_dm.md" in names
    assert "cover_letter.pdf" not in names
