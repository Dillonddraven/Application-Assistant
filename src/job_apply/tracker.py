"""Application tracker — single XLSX, OpenPyXL, source of truth.

Schema:
    job_id | slug | company | title | location | remote_mode | source_url
    fit_score | industry_filter | applied_date | status | last_status_change
    next_followup_date | notes

Status values:
    waiting              — applied, awaiting first response
    interview_pending    — interview scheduled, not yet held
    interview_completed  — interview done, awaiting decision
    rejected             — no further action
    offer                — offer received, awaiting your decision
    accepted             — terminal state, accepted offer
    withdrawn            — you withdrew

Follow-up cadence:
    waiting              -> applied_date  + 7 days
    interview_pending    -> applied_date  + 14 days
    interview_completed  -> last_status_change + 7 days
    others               -> none
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet

from .config import ROOT

TRACKER_PATH = ROOT / "applications.xlsx"

COLUMNS: list[str] = [
    "job_id", "slug", "company", "title", "location", "remote_mode",
    "source_url", "fit_score", "industry_filter",
    "applied_date", "status", "last_status_change",
    "next_followup_date", "notes",
]

STATUSES: list[str] = [
    "waiting", "interview_pending", "interview_completed",
    "rejected", "offer", "accepted", "withdrawn",
]
TERMINAL_STATUSES: set[str] = {"rejected", "accepted", "withdrawn"}

# Cell fills per status. Pastel for in-progress, muted for terminal.
STATUS_FILLS: dict[str, PatternFill] = {
    "waiting":             PatternFill("solid", fgColor="FFF7D6"),
    "interview_pending":   PatternFill("solid", fgColor="DDE8F7"),
    "interview_completed": PatternFill("solid", fgColor="D6EAEA"),
    "offer":               PatternFill("solid", fgColor="DDF0D2"),
    "accepted":            PatternFill("solid", fgColor="9FCF85"),
    "rejected":            PatternFill("solid", fgColor="EAD6D6"),
    "withdrawn":           PatternFill("solid", fgColor="E5E5E5"),
}

HEADER_FILL = PatternFill("solid", fgColor="1A3A5C")
HEADER_FONT = Font(bold=True, color="FFFFFF")


class TrackerError(RuntimeError):
    pass


@dataclass
class Row:
    """One application row, dict-shaped."""
    data: dict[str, Any]

    def get(self, k: str, default: Any = None) -> Any:
        return self.data.get(k, default)

    @property
    def job_id(self) -> str:
        return str(self.data.get("job_id") or "")

    @property
    def slug(self) -> str:
        return str(self.data.get("slug") or "")

    @property
    def status(self) -> str:
        return str(self.data.get("status") or "waiting")


def today_iso() -> str:
    return date.today().isoformat()


def _parse_date(s: Any) -> date | None:
    if not s:
        return None
    if isinstance(s, date):
        return s
    try:
        return datetime.fromisoformat(str(s)).date()
    except ValueError:
        try:
            return datetime.strptime(str(s)[:10], "%Y-%m-%d").date()
        except ValueError:
            return None


def followup_for(*, status: str, applied_date: str, last_status_change: str) -> str | None:
    if status in TERMINAL_STATUSES:
        return None
    applied = _parse_date(applied_date)
    last = _parse_date(last_status_change) or applied
    if status == "waiting" and applied:
        return (applied + timedelta(days=7)).isoformat()
    if status == "interview_pending" and applied:
        return (applied + timedelta(days=14)).isoformat()
    if status == "interview_completed" and last:
        return (last + timedelta(days=7)).isoformat()
    return None


def _fresh_workbook() -> Workbook:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "applications"
    for i, col in enumerate(COLUMNS, start=1):
        cell = ws.cell(row=1, column=i, value=col)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="left", vertical="center")
    ws.freeze_panes = "A2"
    # Sensible column widths
    widths = {
        "job_id": 14, "slug": 38, "company": 22, "title": 30, "location": 18,
        "remote_mode": 10, "source_url": 50, "fit_score": 9,
        "industry_filter": 14, "applied_date": 12, "status": 20,
        "last_status_change": 14, "next_followup_date": 14, "notes": 40,
    }
    for i, col in enumerate(COLUMNS, start=1):
        ws.column_dimensions[get_column_letter(i)].width = widths.get(col, 14)
    return wb


def _load_workbook(path: Path) -> Workbook:
    if not path.exists():
        return _fresh_workbook()
    return openpyxl.load_workbook(str(path))


def _ws(wb: Workbook) -> Worksheet:
    if "applications" in wb.sheetnames:
        return wb["applications"]
    return wb.active


def _row_index_for(ws: Worksheet, *, job_id: str | None = None,
                   slug: str | None = None) -> int | None:
    """Return 1-based row index in the sheet, or None if not found."""
    for r in range(2, ws.max_row + 1):
        ji = ws.cell(row=r, column=1).value
        sl = ws.cell(row=r, column=2).value
        if job_id and ji == job_id:
            return r
        if slug and sl == slug:
            return r
    return None


def _write_row(ws: Worksheet, row_idx: int, row: dict[str, Any]) -> None:
    for col_idx, col in enumerate(COLUMNS, start=1):
        ws.cell(row=row_idx, column=col_idx, value=row.get(col, ""))
    # Status fill
    status = str(row.get("status") or "")
    fill = STATUS_FILLS.get(status)
    if fill:
        ws.cell(row=row_idx, column=COLUMNS.index("status") + 1).fill = fill


def _row_to_dict(ws: Worksheet, row_idx: int) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for col_idx, col in enumerate(COLUMNS, start=1):
        val = ws.cell(row=row_idx, column=col_idx).value
        if isinstance(val, datetime):
            val = val.date().isoformat()
        elif isinstance(val, date):
            val = val.isoformat()
        out[col] = val if val is not None else ""
    return out


def _save_atomic(wb: Workbook, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    wb.save(str(tmp))
    tmp.replace(path)


def upsert(*, packet: dict[str, Any], analyzed: dict[str, Any] | None,
           status: str = "waiting", notes: str = "",
           path: Path | None = None) -> dict[str, Any]:
    """Insert or update the row for a packet. Idempotent on (job_id, slug)."""
    if status not in STATUSES:
        raise TrackerError(f"unknown status {status!r} (valid: {STATUSES})")
    p = path or TRACKER_PATH
    wb = _load_workbook(p)
    ws = _ws(wb)
    job_id = packet.get("job_id") or ""
    slug = packet.get("slug") or ""
    existing_idx = _row_index_for(ws, job_id=job_id, slug=slug)
    today = today_iso()

    if existing_idx:
        existing = _row_to_dict(ws, existing_idx)
        applied_date = existing.get("applied_date") or today
        last_change = (today if status != existing.get("status") else
                       (existing.get("last_status_change") or today))
        notes_final = notes or existing.get("notes") or ""
    else:
        applied_date = today
        last_change = today
        notes_final = notes

    row = {
        "job_id": job_id,
        "slug": slug,
        "company": (analyzed or {}).get("company") or "",
        "title": (analyzed or {}).get("title") or "",
        "location": (analyzed or {}).get("location") or "",
        "remote_mode": (analyzed or {}).get("remote_mode") or "",
        "source_url": (analyzed or {}).get("source_url") or "",
        "fit_score": (analyzed or {}).get("fit_score") or "",
        "industry_filter": (analyzed or {}).get("industry_filter") or "",
        "applied_date": applied_date,
        "status": status,
        "last_status_change": last_change,
        "next_followup_date": followup_for(
            status=status, applied_date=applied_date, last_status_change=last_change,
        ) or "",
        "notes": notes_final,
    }

    target_row = existing_idx or (ws.max_row + 1)
    _write_row(ws, target_row, row)
    _save_atomic(wb, p)
    return row


def set_status(*, ident: str, new_status: str, notes: str = "",
               path: Path | None = None) -> dict[str, Any]:
    """Flip status by job_id or slug. Recomputes next_followup_date."""
    if new_status not in STATUSES:
        raise TrackerError(f"unknown status {new_status!r} (valid: {STATUSES})")
    p = path or TRACKER_PATH
    if not p.exists():
        raise TrackerError(f"no tracker file at {p}; nothing to update.")
    wb = _load_workbook(p)
    ws = _ws(wb)
    idx = _row_index_for(ws, job_id=ident, slug=ident)
    if idx is None:
        raise TrackerError(f"no application with job_id or slug {ident!r}")
    existing = _row_to_dict(ws, idx)
    today = today_iso()
    existing["status"] = new_status
    existing["last_status_change"] = today
    existing["next_followup_date"] = followup_for(
        status=new_status,
        applied_date=existing.get("applied_date") or today,
        last_status_change=today,
    ) or ""
    if notes:
        prefix = (existing.get("notes") or "").rstrip()
        existing["notes"] = (prefix + ("\n" if prefix else "") + f"[{today}] {notes}").strip()
    _write_row(ws, idx, existing)
    _save_atomic(wb, p)
    return existing


def list_rows(*, status: str | None = None, path: Path | None = None) -> list[dict[str, Any]]:
    p = path or TRACKER_PATH
    if not p.exists():
        return []
    wb = _load_workbook(p)
    ws = _ws(wb)
    out: list[dict[str, Any]] = []
    for r in range(2, ws.max_row + 1):
        d = _row_to_dict(ws, r)
        if not d.get("job_id") and not d.get("slug"):
            continue
        if status and d.get("status") != status:
            continue
        out.append(d)
    return out


def due_followups(*, by: date | None = None, path: Path | None = None) -> list[dict[str, Any]]:
    cutoff = by or date.today()
    out: list[dict[str, Any]] = []
    for row in list_rows(path=path):
        if row.get("status") in TERMINAL_STATUSES:
            continue
        d = _parse_date(row.get("next_followup_date"))
        if d and d <= cutoff:
            out.append(row)
    return sorted(out, key=lambda r: r.get("next_followup_date") or "")


def render_table(rows: Iterable[dict[str, Any]]) -> str:
    rows = list(rows)
    if not rows:
        return "(no applications tracked yet)"
    cols = ("STATUS", "FIT", "COMPANY", "TITLE", "APPLIED", "FOLLOWUP", "URL")
    lines: list[tuple[str, ...]] = [cols]
    for r in rows:
        lines.append((
            (r.get("status") or "")[:20],
            str(r.get("fit_score") or "")[:3],
            (r.get("company") or "")[:24],
            (r.get("title") or "")[:32],
            (r.get("applied_date") or "")[:10],
            (r.get("next_followup_date") or "")[:10],
            (r.get("source_url") or "")[:46],
        ))
    widths = [max(len(row[i]) for row in lines) for i in range(len(cols))]
    out: list[str] = []
    for i, row in enumerate(lines):
        out.append("  ".join(cell.ljust(widths[j]) for j, cell in enumerate(row)))
        if i == 0:
            out.append("-" * len(out[-1]))
    return "\n".join(out)
