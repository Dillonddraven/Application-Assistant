"""Open a Mail.app draft with packet attachments.

Uses the proven AppleScript pattern (`at end` for attachments) that survived
the earlier `at after the last paragraph` timeout bug. Driver-script handles
"Mail not running" / "AppleScript permission denied" cases gracefully.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Iterable


class MailDraftError(RuntimeError):
    pass


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
    """Open a Mail.app draft. Raises MailDraftError on failure (timeout, permission, etc)."""
    paths = [Path(p).resolve() for p in attachments]
    missing = [p for p in paths if not p.exists()]
    if missing:
        raise MailDraftError(f"missing attachment(s): {missing}")
    if not paths:
        raise MailDraftError("no attachments provided")
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


def packet_attachments(out_dir: Path) -> list[Path]:
    """The complete set of files we want in the review email."""
    candidates = [
        "tailored_resume.pdf",
        "cover_letter.pdf",
        "tailored_resume.docx",
        "cover_letter.docx",
        "outreach_recruiter.md",
        "outreach_hiring_manager.md",
        "linkedin_dm.md",
        "application_answers.md",
        "match_report.md",
    ]
    return [out_dir / c for c in candidates if (out_dir / c).exists()]
