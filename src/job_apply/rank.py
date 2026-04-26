"""Rank analyzed jobs and pretty-print a table."""
from __future__ import annotations

from typing import Any

from . import state


def ranked() -> list[dict[str, Any]]:
    rows = state.list_analyzed()
    return sorted(rows, key=lambda r: r.get("fit_score", 0), reverse=True)


def render_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "(no analyzed jobs yet — run `job-apply ingest` then `job-apply analyze`)"
    header = ("ID", "FIT", "FILTER", "COMPANY", "TITLE", "LOC", "REMOTE")
    lines: list[tuple[str, ...]] = [header]
    for r in rows:
        flag = ""
        if r.get("industry_filter") == "avoid":
            flag = "AVOID"
        elif r.get("industry_filter") == "review":
            flag = "REVIEW"
        lines.append((
            r.get("id", "")[:12],
            f"{r.get('fit_score', 0):3d}",
            flag,
            (r.get("company") or "")[:24],
            (r.get("title") or "")[:36],
            (r.get("location") or "")[:18],
            (r.get("remote_mode") or "")[:7],
        ))
    widths = [max(len(row[i]) for row in lines) for i in range(len(header))]
    out_lines: list[str] = []
    for i, row in enumerate(lines):
        s = "  ".join(cell.ljust(widths[j]) for j, cell in enumerate(row))
        out_lines.append(s)
        if i == 0:
            out_lines.append("-" * len(s))
    return "\n".join(out_lines)
