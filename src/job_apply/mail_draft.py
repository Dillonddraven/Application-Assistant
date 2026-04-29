"""Open a Mail.app draft with packet attachments.

Uses the proven AppleScript pattern (`at end` for attachments) that survived
the earlier `at after the last paragraph` timeout bug. Driver-script handles
"Mail not running" / "AppleScript permission denied" cases gracefully.

Two attachment modes:
  - "review": all internal + employer files (sent to candidate's own email
              for self-review).
  - "employer": only employer/ files (PDF + DOCX resume + cover letter).
                Used for the actual outreach email to a recruiter / hiring manager.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Iterable


# RFC-5322-ish (good enough). We're guarding against typos, not crafting validators.
_EMAIL_RE = re.compile(
    r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$"
)

MAX_TOTAL_ATTACH_BYTES = 20 * 1024 * 1024   # 20 MB (Gmail allows 25; leave headroom)
MAX_ATTACHMENT_COUNT = 25
MAX_SUBJECT_CHARS = 200
MAX_BODY_CHARS = 50_000


class MailDraftError(RuntimeError):
    pass


def _validate_email_address(addr: str) -> None:
    if not addr or not addr.strip():
        raise MailDraftError("recipient email address is empty")
    if not _EMAIL_RE.match(addr.strip()):
        raise MailDraftError(f"recipient {addr!r} doesn't look like an email address")


def _validate_subject(subject: str) -> None:
    if not subject or not subject.strip():
        raise MailDraftError("subject is empty")
    if len(subject) > MAX_SUBJECT_CHARS:
        raise MailDraftError(f"subject exceeds {MAX_SUBJECT_CHARS} chars (got {len(subject)})")


def _validate_body(body: str) -> None:
    if not body or not body.strip():
        raise MailDraftError("body is empty")
    if len(body) > MAX_BODY_CHARS:
        raise MailDraftError(f"body exceeds {MAX_BODY_CHARS} chars (got {len(body)})")


def _validate_attachments(paths: list[Path]) -> None:
    if not paths:
        raise MailDraftError("no attachments provided")
    if len(paths) > MAX_ATTACHMENT_COUNT:
        raise MailDraftError(
            f"too many attachments ({len(paths)} > {MAX_ATTACHMENT_COUNT})"
        )
    missing = [p for p in paths if not p.exists()]
    if missing:
        raise MailDraftError(f"missing attachment(s): {missing}")
    total_bytes = sum(p.stat().st_size for p in paths)
    if total_bytes > MAX_TOTAL_ATTACH_BYTES:
        raise MailDraftError(
            f"total attachment size {total_bytes / 1_048_576:.1f} MB exceeds "
            f"{MAX_TOTAL_ATTACH_BYTES / 1_048_576:.0f} MB cap (Gmail allows 25 MB; we cap at 20)"
        )


def _osascript_path() -> str:
    p = shutil.which("osascript") or "/usr/bin/osascript"
    return p


def _build_script(*, to_addr: str, subject: str, body: str,
                  attachments: list[Path]) -> str:
    set_lines = []
    add_lines = []
    for i, p in enumerate(attachments, start=1):
        var = f"f{i}"
        set_lines.append(f'    set {var} to (POSIX file "{p}")')
        add_lines.append(f'        make new attachment with properties {{file name:{var}}} at end')
    set_block = "\n".join(set_lines)
    add_block = "\n".join(add_lines)
    body_escaped = body.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    subject_escaped = subject.replace("\\", "\\\\").replace('"', '\\"')
    to_escaped = to_addr.replace("\\", "\\\\").replace('"', '\\"')
    return f"""with timeout of 300 seconds
{set_block}

    tell application "Mail"
        activate
        set newMessage to make new outgoing message with properties {{visible:true, subject:"{subject_escaped}", content:"{body_escaped}"}}
        tell newMessage
            make new to recipient at end of to recipients with properties {{address:"{to_escaped}"}}
{add_block}
        end tell
    end tell
    return "ok"
end timeout
"""


def open_draft(*, to_addr: str, subject: str, body: str,
               attachments: Iterable[Path]) -> None:
    """Open a Mail.app draft. Raises MailDraftError on any preflight failure or
    AppleScript timeout / permission issue."""
    paths = [Path(p).resolve() for p in attachments]
    _validate_email_address(to_addr)
    _validate_subject(subject)
    _validate_body(body)
    _validate_attachments(paths)
    script = _build_script(to_addr=to_addr, subject=subject, body=body, attachments=paths)
    try:
        proc = subprocess.run(
            [_osascript_path()],
            input=script,
            text=True,
            capture_output=True,
            timeout=320,
        )
    except subprocess.TimeoutExpired as e:
        raise MailDraftError(f"osascript timed out after {e.timeout}s") from e
    except FileNotFoundError as e:
        raise MailDraftError(f"osascript not found: {e}") from e
    if proc.returncode != 0:
        msg = proc.stderr.strip() or proc.stdout.strip() or "unknown osascript failure"
        if "-1712" in msg:
            raise MailDraftError(
                "Mail.app AppleEvent timed out (-1712). Check System Settings → "
                "Privacy & Security → Automation and ensure your terminal can control Mail."
            )
        raise MailDraftError(f"osascript failed: {msg}")


def packet_attachments(out_dir: Path, *, mode: str = "employer",
                       include_docx: bool = False) -> list[Path]:
    """Files to attach for the given Mail-draft mode.

    Modes:
      - "employer" (default): ONLY the polished employer-facing resume + cover
                              letter as PDF. Internal files (markdown views,
                              packet.json, match_report, application_answers,
                              outreach drafts, qa_report) must NEVER appear in
                              an employer email. DOCX is optional and off by
                              default — set include_docx=True to attach DOCX
                              when the application specifically asks for it.
      - "review": everything we generated (employer + internal). For a
                  self-review email — never sent to an employer.
    """
    employer_dir = out_dir / "employer"
    internal_dir = out_dir / "internal"

    if mode == "employer":
        candidates: list[Path] = [
            employer_dir / "tailored_resume.pdf",
            employer_dir / "cover_letter.pdf",
        ]
        if include_docx:
            candidates += [
                employer_dir / "tailored_resume.docx",
                employer_dir / "cover_letter.docx",
            ]
        return [c for c in candidates if c.exists()]

    if mode != "review":
        raise ValueError(f"unknown mode: {mode!r}")

    out: list[Path] = []
    for p in (
        employer_dir / "tailored_resume.pdf",
        employer_dir / "cover_letter.pdf",
        employer_dir / "tailored_resume.docx",
        employer_dir / "cover_letter.docx",
        internal_dir / "outreach_recruiter.md",
        internal_dir / "outreach_hiring_manager.md",
        internal_dir / "linkedin_dm.md",
        internal_dir / "application_answers.md",
        internal_dir / "match_report.md",
        internal_dir / "qa_report.md",
    ):
        if p.exists():
            out.append(p)
    if not out:
        legacy = [
            "tailored_resume.pdf", "cover_letter.pdf",
            "tailored_resume.docx", "cover_letter.docx",
            "outreach_recruiter.md", "outreach_hiring_manager.md",
            "linkedin_dm.md", "application_answers.md", "match_report.md",
        ]
        out = [out_dir / c for c in legacy if (out_dir / c).exists()]
    return out


def stamp_subject(subject: str, run_id: str) -> str:
    """Append a [run: <run_id>] tag to the subject for traceability and cleanup."""
    if not run_id:
        return subject
    if f"[run: {run_id}]" in subject:
        return subject
    return f"{subject.rstrip()} [run: {run_id}]"


def close_drafts_with_run_id(run_id: str) -> int:
    """Close any open Mail compose windows whose subject contains the given run id.
    Returns the number of windows closed. Best-effort; does not raise on AppleScript
    failure (Mail might not be running, the user might have closed it manually, etc).
    """
    if not run_id:
        return 0
    # Match the marker we stamp into subjects.
    marker = f"[run: {run_id}]"
    script = f"""
tell application "Mail"
    set closedCount to 0
    try
        repeat with w in (every window whose name contains "{marker}")
            try
                close w saving no
                set closedCount to closedCount + 1
            end try
        end repeat
    end try
    return closedCount
end tell
"""
    try:
        proc = subprocess.run(
            [_osascript_path()],
            input=script, text=True, capture_output=True, timeout=30,
        )
        if proc.returncode == 0:
            try:
                return int((proc.stdout or "0").strip())
            except ValueError:
                return 0
    except Exception:
        pass
    return 0
