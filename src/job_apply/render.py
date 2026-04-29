"""Render structured tailored data to markdown views.

PII placeholder substitution happens HERE, after fabrication validation, in a
local-only step. The markdown templates use `{{email}}`, `{{phone}}`, etc.;
prompts never reference these placeholders so the LLM can't talk about them.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Any

from .profile_loader import Profile, Secrets

# LLMs occasionally leak parenthetical source-id citations into prose
# ("...summaries (dillards_intern.b1)..."). Scrub them at render time so
# user-facing documents stay clean.
#
# Two-layer defense:
#   1. The dotted-id regex catches "experience.foo.b1" / "reusable_answers.x" etc.
#   2. When a `known_ids` set is passed, any parenthetical exactly matching a
#      known id (or a known id prefix) is also stripped. This catches single-
#      token project ids like "(proj_centralized_logging_lab)".
_SOURCE_ID_LEAK_RE = re.compile(r"\s*\(\s*[a-z][a-z0-9_]*(?:\.[a-z0-9_]+)+\s*\)")
_PARENTHETICAL = re.compile(r"\s*\(\s*([a-z][a-z0-9_]*)\s*\)")


def _scrub_source_ids(text: str, known_ids: set[str] | None = None) -> str:
    cleaned = _SOURCE_ID_LEAK_RE.sub("", text)
    if known_ids:
        def _strip_known(match: re.Match) -> str:
            ident = match.group(1)
            if ident in known_ids:
                return ""
            return match.group(0)
        cleaned = _PARENTHETICAL.sub(_strip_known, cleaned)
    # Collapse any double spaces left behind, and tidy " ." or " ," seams.
    cleaned = re.sub(r" {2,}", " ", cleaned)
    cleaned = re.sub(r"\s+([.,;:!?])", r"\1", cleaned)
    return cleaned


def collect_known_ids(profile_data: dict[str, Any]) -> set[str]:
    """Build the set of profile-derived ids that should be scrubbed if leaked."""
    out: set[str] = set()
    for section in ("experience", "education", "certifications", "projects"):
        for item in profile_data.get(section) or []:
            if isinstance(item, dict):
                ident = item.get("id")
                if isinstance(ident, str):
                    out.add(ident)
                for bullet in item.get("bullets") or []:
                    if isinstance(bullet, dict):
                        bid = bullet.get("id")
                        if isinstance(bid, str):
                            # bullet ids are typically dotted (already covered by
                            # the dotted regex) but we add the trailing token in
                            # case the LLM cites just the suffix.
                            out.add(bid)
                            tail = bid.rsplit(".", 1)[-1]
                            out.add(tail)
    ra = profile_data.get("reusable_answers")
    if isinstance(ra, dict):
        out.update(ra.keys())
    return out


def substitute_pii(text: str, secrets: Secrets) -> str:
    out = text
    for placeholder, value in secrets.placeholder_map().items():
        out = out.replace(placeholder, value)
    return out


def _contact_line(secrets: Secrets) -> str:
    bits = []
    pm = secrets.placeholder_map()
    for k in ("{{email}}", "{{phone}}", "{{linkedin_url}}", "{{github_url}}"):
        if pm.get(k):
            bits.append(pm[k])
    return " • ".join(bits)


def render_resume(*, profile: Profile, tailored: dict[str, Any], secrets: Secrets) -> str:
    p = profile.data
    known = collect_known_ids(p)
    name = p.get("identity", {}).get("full_name", "")
    contact = _contact_line(secrets)
    lines: list[str] = [f"# {name}"]
    if contact:
        lines.append(contact)
    lines.append("")

    summary = _scrub_source_ids(tailored.get("summary") or "", known)
    if summary:
        lines += ["## Summary", summary, ""]

    skills_emphasis = tailored.get("skills_emphasis") or []
    if skills_emphasis:
        lines += ["## Skills"]
        for s in skills_emphasis:
            lines.append(f"- {s}")
        lines.append("")

    # Experience: only experiences cited by tailored bullets get rendered, in profile order.
    cited_exp_ids: set[str] = set()
    bullets_by_exp: dict[str, list[str]] = {}
    for b in tailored.get("bullets") or []:
        sid = b.get("source_id", "")
        parts = sid.split(".")
        if len(parts) >= 2 and parts[0] == "experience":
            exp_id = parts[1]
            cited_exp_ids.add(exp_id)
            bullets_by_exp.setdefault(exp_id, []).append(b.get("text", ""))

    if cited_exp_ids:
        lines += ["## Experience"]
        for exp in p.get("experience") or []:
            if exp.get("id") not in cited_exp_ids:
                continue
            company = exp.get("company", "")
            title = exp.get("title", "")
            location = exp.get("location", "")
            start = exp.get("start", "")
            end = exp.get("end", "") or "Present"
            lines.append(f"### {company} — {title}")
            meta_bits = [f"{start} – {end}"]
            if location:
                meta_bits.append(location)
            lines.append(" • ".join(meta_bits))
            for txt in bullets_by_exp.get(exp.get("id"), []):
                lines.append(f"- {_scrub_source_ids(txt, known)}")
            lines.append("")

    edu = p.get("education") or []
    if edu:
        lines += ["## Education"]
        for e in edu:
            degree = e.get("degree", "")
            school = e.get("school", "")
            status = e.get("status", "")
            expected = e.get("expected_end", "")
            tail = " (in progress" + (f", expected {expected}" if expected else "") + ")" if status == "in_progress" else ""
            lines.append(f"- **{degree}** — {school}{tail}")
        lines.append("")

    certs = p.get("certifications") or []
    if certs:
        lines += ["## Certifications"]
        for c in certs:
            n = c.get("name", "")
            issued = c.get("issued") or ""
            tail = f" ({issued})" if issued and not issued.startswith("<") else ""
            lines.append(f"- {n}{tail}")
        lines.append("")

    return substitute_pii("\n".join(lines).rstrip() + "\n", secrets)


def render_cover_letter(
    *,
    profile: Profile,
    tailored: dict[str, Any],
    secrets: Secrets,
    company: str,
    salutation: str = "Dear Hiring Team,",
) -> str:
    known = collect_known_ids(profile.data)
    pm = secrets.placeholder_map()
    addr_lines = []
    if pm.get("{{address_street}}"):
        addr_lines.append(pm["{{address_street}}"])
    city_state_zip = " ".join(
        bit for bit in [
            (pm.get("{{address_city}}") or "") + ("," if pm.get("{{address_city}}") else ""),
            pm.get("{{address_state}}") or "",
            pm.get("{{address_zip}}") or "",
        ] if bit.strip()
    ).strip()
    if city_state_zip:
        addr_lines.append(city_state_zip)

    today = date.today().isoformat()
    lines: list[str] = []
    lines.extend(addr_lines)
    if addr_lines:
        lines.append("")
    lines.append(today)
    lines.append("")
    lines.append(salutation)
    lines.append("")
    for para in tailored.get("cover_letter_paragraphs") or []:
        lines.append(_scrub_source_ids(para.get("text", ""), known))
        lines.append("")
    name = profile.data.get("identity", {}).get("full_name", "")
    lines.append("Sincerely,")
    lines.append(name)
    sig_bits = [pm.get("{{email}}", ""), pm.get("{{phone}}", "")]
    sig = " • ".join(b for b in sig_bits if b)
    if sig:
        lines.append(sig)
    return "\n".join(lines).rstrip() + "\n"


def render_application_answers(*, tailored: dict[str, Any], profile: Profile | None = None) -> str:
    items = tailored.get("application_answers") or []
    if not items:
        return "_(no anticipated application answers generated)_\n"
    known = collect_known_ids(profile.data) if profile else None
    lines: list[str] = ["# Application Answers", ""]
    for a in items:
        q = a.get("question", "")
        ans = _scrub_source_ids(a.get("answer", ""), known)
        lines.append(f"### {q}")
        lines.append(ans)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_email(*, subject: str, body_paragraphs: list[dict[str, Any]], signature_name: str,
                 secrets: Secrets, known_ids: set[str] | None = None) -> str:
    pm = secrets.placeholder_map()
    lines = [f"**Subject:** {_scrub_source_ids(subject, known_ids)}", ""]
    for p in body_paragraphs:
        lines.append(_scrub_source_ids(p.get("text", ""), known_ids))
        lines.append("")
    lines.append(signature_name)
    sig_bits = [pm.get("{{email}}", ""), pm.get("{{phone}}", "")]
    sig = " • ".join(b for b in sig_bits if b)
    if sig:
        lines.append(sig)
    return "\n".join(lines).rstrip() + "\n"


def render_linkedin_dm(text: str, known_ids: set[str] | None = None) -> str:
    return _scrub_source_ids(text, known_ids).rstrip() + "\n"


def render_match_report(analyzed: dict[str, Any], packet: dict[str, Any]) -> str:
    lines = [f"# Match report: {analyzed.get('company')} — {analyzed.get('title')}", ""]
    lines.append(f"- Job ID: `{analyzed.get('id')}`")
    if analyzed.get("source_url"):
        lines.append(f"- Source: {analyzed['source_url']}")
    lines.append(f"- Location: {analyzed.get('location') or '—'}  ({analyzed.get('remote_mode')})")
    lines.append(f"- Industry filter: **{analyzed.get('industry_filter')}** (tags: {', '.join(analyzed.get('industry_tags') or []) or '—'})")
    lines.append(f"- **Fit score: {analyzed.get('fit_score')}**")
    fb = analyzed.get("fit_breakdown") or {}
    if fb:
        lines.append("- Breakdown:")
        for k, v in fb.items():
            lines.append(f"  - {k}: {v}")
    if analyzed.get("fit_rationale"):
        lines += ["", "## Rationale", analyzed["fit_rationale"]]
    if analyzed.get("concerns"):
        lines += ["", "## Concerns"]
        for c in analyzed["concerns"]:
            lines.append(f"- {c}")
    if analyzed.get("missing_quals"):
        lines += ["", "## Missing qualifications"]
        for c in analyzed["missing_quals"]:
            lines.append(f"- {c}")

    val = packet.get("validation", {})
    blocks = val.get("fabrication_blocks") or []
    warns = val.get("fabrication_warnings") or []
    lines += ["", "## Fabrication validator"]
    if not blocks and not warns:
        lines.append("- Clean: no blocks, no warnings.")
    if blocks:
        lines.append("- **BLOCKS:**")
        for b in blocks:
            lines.append(f"  - [{b.get('rule')}] {b.get('detail')}  (source: {b.get('source_id') or '—'})")
    if warns:
        lines.append("- Warnings:")
        for w in warns:
            lines.append(f"  - [{w.get('rule')}] {w.get('detail')}")
    return "\n".join(lines).rstrip() + "\n"
