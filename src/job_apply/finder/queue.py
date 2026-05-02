"""Persistence for the finder review queue. Mirrors the tracker XLSX style
so the user can open it in Excel/Numbers and act on it."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from ..config import ROOT

QUEUE_PATH = ROOT / "runs" / "_finder_queue.xlsx"

COLUMNS = [
    "company", "title", "location", "ats", "url",
    "quick_fit", "stretch_flags",
    "recommended_action",   # run_packet | save_for_later | skip | stretch
    "review_status",        # new | reviewed | approved | ignored
    "discovered_date", "review_notes", "external_id",
]

ACTION_COLORS = {
    "run_packet":     PatternFill("solid", fgColor="DDF0D2"),
    "save_for_later": PatternFill("solid", fgColor="FFF7D6"),
    "stretch":        PatternFill("solid", fgColor="DDE8F7"),
    "skip":           PatternFill("solid", fgColor="EAD6D6"),
}
HEADER_FILL = PatternFill("solid", fgColor="1A3A5C")
HEADER_FONT = Font(bold=True, color="FFFFFF")


@dataclass
class FinderQueueRow:
    company: str = ""
    title: str = ""
    location: str = ""
    ats: str = ""
    url: str = ""
    quick_fit: int = 0
    stretch_flags: str = ""
    recommended_action: str = "save_for_later"
    review_status: str = "new"
    discovered_date: str = ""
    review_notes: str = ""
    external_id: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "company": self.company, "title": self.title, "location": self.location,
            "ats": self.ats, "url": self.url, "quick_fit": self.quick_fit,
            "stretch_flags": self.stretch_flags,
            "recommended_action": self.recommended_action,
            "review_status": self.review_status,
            "discovered_date": self.discovered_date,
            "review_notes": self.review_notes,
            "external_id": self.external_id,
        }


def _fresh_workbook():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "finder_queue"
    for i, col in enumerate(COLUMNS, start=1):
        cell = ws.cell(row=1, column=i, value=col)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="left", vertical="center")
    ws.freeze_panes = "A2"
    widths = {
        "company": 22, "title": 36, "location": 18, "ats": 10,
        "url": 50, "quick_fit": 10, "stretch_flags": 28,
        "recommended_action": 16, "review_status": 14,
        "discovered_date": 12, "review_notes": 30, "external_id": 16,
    }
    for i, col in enumerate(COLUMNS, start=1):
        ws.column_dimensions[get_column_letter(i)].width = widths.get(col, 14)
    return wb


def load_queue(path: Path | None = None) -> list[FinderQueueRow]:
    p = path or QUEUE_PATH
    if not p.exists():
        return []
    wb = openpyxl.load_workbook(str(p))
    ws = wb["finder_queue"] if "finder_queue" in wb.sheetnames else wb.active
    out: list[FinderQueueRow] = []
    for r in range(2, ws.max_row + 1):
        vals: dict[str, Any] = {}
        for col_idx, col in enumerate(COLUMNS, start=1):
            v = ws.cell(row=r, column=col_idx).value
            if isinstance(v, datetime):
                v = v.date().isoformat()
            elif isinstance(v, date):
                v = v.isoformat()
            vals[col] = v if v is not None else ""
        if not vals.get("url") and not vals.get("company"):
            continue
        out.append(FinderQueueRow(
            company=str(vals.get("company") or ""),
            title=str(vals.get("title") or ""),
            location=str(vals.get("location") or ""),
            ats=str(vals.get("ats") or ""),
            url=str(vals.get("url") or ""),
            quick_fit=int(vals.get("quick_fit") or 0),
            stretch_flags=str(vals.get("stretch_flags") or ""),
            recommended_action=str(vals.get("recommended_action") or "save_for_later"),
            review_status=str(vals.get("review_status") or "new"),
            discovered_date=str(vals.get("discovered_date") or ""),
            review_notes=str(vals.get("review_notes") or ""),
            external_id=str(vals.get("external_id") or ""),
        ))
    return out


def save_queue(rows: list[FinderQueueRow], path: Path | None = None) -> Path:
    p = path or QUEUE_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    wb = _fresh_workbook()
    ws = wb["finder_queue"]
    for i, row in enumerate(rows, start=2):
        d = row.as_dict()
        for col_idx, col in enumerate(COLUMNS, start=1):
            ws.cell(row=i, column=col_idx, value=d.get(col, ""))
        # Color the recommended_action cell
        action = d.get("recommended_action", "")
        fill = ACTION_COLORS.get(action)
        if fill:
            ws.cell(row=i, column=COLUMNS.index("recommended_action") + 1).fill = fill
    tmp = p.with_suffix(p.suffix + ".tmp")
    wb.save(str(tmp))
    tmp.replace(p)
    return p


def upsert(rows: list[FinderQueueRow], new_row: FinderQueueRow) -> list[FinderQueueRow]:
    """Idempotent upsert by URL. Preserves user-edited review_status / review_notes."""
    by_url = {r.url: r for r in rows}
    existing = by_url.get(new_row.url)
    if existing:
        # Keep user-edited fields; refresh discovery + recommendation.
        new_row.review_status = existing.review_status or new_row.review_status
        new_row.review_notes = existing.review_notes or ""
        by_url[new_row.url] = new_row
    else:
        by_url[new_row.url] = new_row
    return list(by_url.values())
