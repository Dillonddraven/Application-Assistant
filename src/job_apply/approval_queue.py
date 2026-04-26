"""Approval workflow: list / review / approve / skip.

`approve` refuses to flip status if the packet has any
validation.fabrication_blocks. The user must edit the markdown / re-tailor first.
"""
from __future__ import annotations

from typing import Any

from . import state


class ApprovalError(RuntimeError):
    pass


def _resolve(slug_or_id: str) -> tuple[str, dict[str, Any]]:
    """Accept either a packet slug or a job id; return (slug, packet)."""
    pkt = state.load_packet(slug_or_id)
    if pkt:
        return slug_or_id, pkt
    found_slug = state.find_slug_by_job_id(slug_or_id)
    if found_slug:
        pkt = state.load_packet(found_slug)
        if pkt:
            return found_slug, pkt
    raise ApprovalError(
        f"no packet found for {slug_or_id!r} (try slug like `acme-corp_security-analyst` "
        f"or the 12-char job id from `rank`)."
    )


def review(slug_or_id: str) -> str:
    """Render a terminal-friendly review of a packet."""
    slug, pkt = _resolve(slug_or_id)
    out_dir = state.packet_dir(slug)
    lines: list[str] = []
    lines.append(f"=== {slug} ===")
    lines.append(f"job_id: {pkt.get('job_id')}")
    lines.append(f"status: {pkt.get('status')}")
    lines.append(f"model:  {pkt.get('model')}")

    val = pkt.get("validation", {})
    blocks = val.get("fabrication_blocks") or []
    warns = val.get("fabrication_warnings") or []
    if blocks:
        lines.append("")
        lines.append(f"⚠ {len(blocks)} fabrication BLOCKS — must fix before approving:")
        for b in blocks:
            lines.append(f"  - [{b.get('rule')}] {b.get('detail')}  (source: {b.get('source_id') or '—'})")
    if warns:
        lines.append("")
        lines.append(f"ℹ {len(warns)} warnings:")
        for w in warns:
            lines.append(f"  - [{w.get('rule')}] {w.get('detail')}")

    rendered = pkt.get("rendered", {})
    if rendered:
        lines.append("")
        lines.append("Generated files (review these manually before approving):")
        for k, fname in rendered.items():
            p = out_dir / fname
            mark = "✓" if p.exists() else "✗"
            lines.append(f"  {mark} {p}")

    lines.append("")
    lines.append("Tailored summary:")
    lines.append(f"  {(pkt.get('tailored') or {}).get('summary', '') or '(empty)'}")

    lines.append("")
    lines.append("Approval log:")
    for entry in pkt.get("approval_log") or []:
        lines.append(f"  - {entry.get('ts')}  {entry.get('action')}")

    if blocks:
        lines.append("")
        lines.append("To approve, fix the blocks (edit the markdown or re-run `job-apply tailor`).")
    else:
        lines.append("")
        lines.append("To approve: `job-apply approve <slug-or-id>`")
        lines.append("To skip:    `job-apply skip <slug-or-id>`")

    return "\n".join(lines)


def approve(slug_or_id: str) -> dict[str, Any]:
    slug, pkt = _resolve(slug_or_id)
    blocks = (pkt.get("validation") or {}).get("fabrication_blocks") or []
    if blocks:
        raise ApprovalError(
            f"{slug}: {len(blocks)} fabrication block(s) present — refusing to approve. "
            f"Run `job-apply review {slug}` for details."
        )
    pkt["status"] = "approved"
    pkt.setdefault("approval_log", []).append({"ts": state.now_iso(), "action": "approve"})
    state.save_packet(slug, pkt)
    return pkt


def skip(slug_or_id: str) -> dict[str, Any]:
    slug, pkt = _resolve(slug_or_id)
    pkt["status"] = "skipped"
    pkt.setdefault("approval_log", []).append({"ts": state.now_iso(), "action": "skip"})
    state.save_packet(slug, pkt)
    return pkt


def queue(status: str = "all") -> list[dict[str, Any]]:
    rows = state.list_packets()
    if status != "all":
        rows = [p for p in rows if p.get("status") == status]
    return rows


def render_queue_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "(no packets yet — run `job-apply tailor <job-id>`)"
    lines: list[tuple[str, ...]] = [("STATUS", "BLOCKS", "JOB_ID", "SLUG")]
    for p in rows:
        b = len((p.get("validation") or {}).get("fabrication_blocks") or [])
        lines.append((
            p.get("status", ""),
            f"{b:2d}" if b else "  ",
            p.get("job_id", "")[:12],
            p.get("slug", ""),
        ))
    widths = [max(len(row[i]) for row in lines) for i in range(len(lines[0]))]
    out: list[str] = []
    for i, row in enumerate(lines):
        out.append("  ".join(cell.ljust(widths[j]) for j, cell in enumerate(row)))
        if i == 0:
            out.append("-" * len(out[-1]))
    return "\n".join(out)
