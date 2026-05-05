"""Ethical, low-effort OSINT contact research v1.

Given (company, role title, optional department, optional known email),
emit:

  outputs/<slug>/internal/contacts.json
  outputs/<slug>/internal/contacts.md

The .md is a human checklist with one-click search URLs (LinkedIn,
Google, GitHub) and -- when seeded with a known company email --
candidate email addresses for any name the user pastes in.

This module deliberately does NOT scrape LinkedIn (TOS), call paid
contact-data APIs (Hunter / Apollo), or parse public-data dumps. It
just makes the user's manual research one click per query."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable
from urllib.parse import quote_plus

from . import config


# --------- email-pattern detection / generation ---------

# Pattern keys are stable identifiers; values are the human description.
EMAIL_PATTERNS: dict[str, str] = {
    "first.last":    "{first}.{last}@{domain}",
    "firstlast":     "{first}{last}@{domain}",
    "first_last":    "{first}_{last}@{domain}",
    "first":         "{first}@{domain}",
    "last":          "{last}@{domain}",
    "flast":         "{f}{last}@{domain}",
    "f.last":        "{f}.{last}@{domain}",
    "firstl":        "{first}{l}@{domain}",
    "first.l":       "{first}.{l}@{domain}",
    "lastfirst":     "{last}{first}@{domain}",
    "last.first":    "{last}.{first}@{domain}",
    "lfirst":        "{l}{first}@{domain}",
}


def _split_name(full_name: str) -> tuple[str, str]:
    """Return (first, last). Strips middle names; lowercases."""
    parts = [p for p in re.split(r"\s+", (full_name or "").strip()) if p]
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0].lower(), ""
    return parts[0].lower(), parts[-1].lower()


def _domain_from_email(email: str) -> str:
    if not email or "@" not in email:
        return ""
    return email.rsplit("@", 1)[1].strip().lower()


def detect_pattern(known_email: str, known_full_name: str) -> str | None:
    """Given one (email, name) example from the company, return the matching
    pattern key, or None if nothing matches.

    Example: detect_pattern("alice.smith@asana.com", "Alice Smith")
             -> "first.last"
    """
    if not known_email or not known_full_name:
        return None
    local = known_email.split("@", 1)[0].lower().strip()
    domain = _domain_from_email(known_email)
    if not local or not domain:
        return None
    first, last = _split_name(known_full_name)
    if not first:
        return None
    f = first[:1]
    l = last[:1] if last else ""
    subs = {"first": first, "last": last, "f": f, "l": l, "domain": domain}
    for key, template in EMAIL_PATTERNS.items():
        try:
            if template.format(**subs).split("@", 1)[0] == local:
                return key
        except (KeyError, IndexError):
            continue
    return None


def candidate_emails(*, target_name: str, domain: str,
                      pattern: str | None = None) -> list[dict[str, str]]:
    """Generate candidate emails for `target_name` at `domain`.

    If `pattern` is provided, that one is listed first (highest confidence).
    Returns a deduped list of {"pattern": ..., "address": ...}, ordered by
    descending confidence.
    """
    first, last = _split_name(target_name)
    if not first or not domain:
        return []
    f = first[:1]
    l = last[:1] if last else ""
    subs = {"first": first, "last": last, "f": f, "l": l, "domain": domain}

    out: list[dict[str, str]] = []
    seen: set[str] = set()

    def _emit(pat: str) -> None:
        tmpl = EMAIL_PATTERNS.get(pat)
        if not tmpl:
            return
        try:
            addr = tmpl.format(**subs)
        except KeyError:
            return
        if "{" in addr or addr in seen:
            return
        seen.add(addr)
        out.append({"pattern": pat, "address": addr})

    # Pinned pattern first (highest confidence)
    if pattern:
        _emit(pattern)
    # Then walk the full pattern list in priority order
    priority = [
        "first.last", "flast", "first", "firstlast",
        "f.last", "firstl", "first.l", "first_last",
        "last.first", "lastfirst", "last", "lfirst",
    ]
    for p in priority:
        # If we don't have a last name, skip any pattern that needs one
        # (matches both "{last}" and "{l}").
        if not last and ("{last}" in EMAIL_PATTERNS[p] or "{l}" in EMAIL_PATTERNS[p]):
            continue
        _emit(p)
    return out


# --------- search URLs ---------

def search_urls(*, company: str, role_title: str = "",
                 department: str = "") -> dict[str, str]:
    """Return clickable LinkedIn / Google / GitHub URLs for manual scan.
    All values are URL-encoded so they paste cleanly."""
    company = (company or "").strip()
    role_title = (role_title or "").strip()
    department = (department or "").strip()
    cq = quote_plus(company)
    role_q = quote_plus(role_title)
    out: dict[str, str] = {}
    if company:
        out["linkedin_company_people"] = (
            f"https://www.linkedin.com/search/results/people/"
            f"?keywords={cq}&origin=GLOBAL_SEARCH_HEADER"
        )
        # Google-LinkedIn — finds profiles even without a LinkedIn login
        google_li_recruiter = quote_plus(
            f'site:linkedin.com/in "{company}" (recruiter OR "talent acquisition" OR "people operations")'
        )
        out["google_linkedin_recruiter"] = (
            f"https://www.google.com/search?q={google_li_recruiter}"
        )
        if role_title:
            google_li_hm = quote_plus(
                f'site:linkedin.com/in "{company}" ("hiring manager" OR "{role_title}" OR "engineering manager")'
            )
            out["google_linkedin_hiring_manager"] = (
                f"https://www.google.com/search?q={google_li_hm}"
            )
            google_li_team = quote_plus(
                f'site:linkedin.com/in "{company}" "{role_title}"'
            )
            out["google_linkedin_team_members"] = (
                f"https://www.google.com/search?q={google_li_team}"
            )
        if department:
            dept_q = quote_plus(f'site:linkedin.com/in "{company}" "{department}"')
            out["google_linkedin_department"] = (
                f"https://www.google.com/search?q={dept_q}"
            )
        out["google_company_recruiting"] = (
            f"https://www.google.com/search?q="
            + quote_plus(f'"{company}" (recruiter OR "talent acquisition") email')
        )
        out["github_org"] = f"https://github.com/{cq.replace('+', '-').lower()}"
    return out


# --------- artifact writers ---------

@dataclass
class ContactsArtifact:
    company: str = ""
    role_title: str = ""
    department: str = ""
    company_domain: str = ""
    detected_pattern: str | None = None
    seed_email: str = ""
    seed_name: str = ""
    target_names: list[str] = field(default_factory=list)
    search_links: dict[str, str] = field(default_factory=dict)
    candidate_emails_by_target: dict[str, list[dict[str, str]]] = field(default_factory=dict)


def build_artifact(*, company: str, role_title: str = "",
                    department: str = "", company_domain: str = "",
                    seed_email: str = "", seed_name: str = "",
                    target_names: Iterable[str] | None = None,
                    ) -> ContactsArtifact:
    """Pure-data assembly. No I/O."""
    target_names = list(target_names or [])
    domain = company_domain.strip().lower() or _domain_from_email(seed_email)
    detected = detect_pattern(seed_email, seed_name) if seed_email and seed_name else None

    by_target: dict[str, list[dict[str, str]]] = {}
    if domain:
        for tn in target_names:
            tn = tn.strip()
            if not tn:
                continue
            by_target[tn] = candidate_emails(
                target_name=tn, domain=domain, pattern=detected,
            )

    return ContactsArtifact(
        company=company, role_title=role_title, department=department,
        company_domain=domain, detected_pattern=detected,
        seed_email=seed_email, seed_name=seed_name,
        target_names=target_names,
        search_links=search_urls(company=company, role_title=role_title,
                                  department=department),
        candidate_emails_by_target=by_target,
    )


def render_md(art: ContactsArtifact) -> str:
    lines: list[str] = []
    lines.append(f"# Contact research: {art.company}, {art.role_title or '(any role)'}")
    lines.append("")
    lines.append("> Ethical OSINT scaffold. The tool does NOT scrape LinkedIn or")
    lines.append("> hit paid databases; it just makes your manual research one")
    lines.append("> click per query. Open the URLs, scan, paste names below, and")
    lines.append("> use `job-apply contacts <ident> --known-email ... --target-name ...`")
    lines.append("> to get email-pattern guesses for each name you find.")
    lines.append("")
    if art.department:
        lines.append(f"**Department:** {art.department}  ")
    if art.company_domain:
        lines.append(f"**Company domain:** `{art.company_domain}`  ")
    if art.detected_pattern:
        lines.append(f"**Detected email pattern:** `{art.detected_pattern}` "
                      f"(from seed `{art.seed_email}` -> `{art.seed_name}`)")
    lines.append("")

    lines.append("## Search URLs (open in browser)")
    lines.append("")
    if not art.search_links:
        lines.append("_(no search URLs -- pass --company)_")
    else:
        labels = {
            "linkedin_company_people":      "LinkedIn: search people at this company",
            "google_linkedin_recruiter":    "Google -> LinkedIn: recruiters at this company",
            "google_linkedin_hiring_manager": "Google -> LinkedIn: hiring managers / role keywords",
            "google_linkedin_team_members": "Google -> LinkedIn: team members in this role",
            "google_linkedin_department":   "Google -> LinkedIn: department members",
            "google_company_recruiting":    "Google: company recruiting / TA contact",
            "github_org":                   "GitHub: company org page (engineering signal)",
        }
        for key, url in art.search_links.items():
            lines.append(f"- **{labels.get(key, key)}**: <{url}>")
    lines.append("")

    lines.append("## Candidate emails")
    lines.append("")
    if not art.candidate_emails_by_target:
        lines.append("_(none yet -- re-run `job-apply contacts <ident>"
                      " --target-name \"Jane Doe\" --known-email seed@example.com`)_")
    else:
        for name, candidates in art.candidate_emails_by_target.items():
            lines.append(f"### {name}")
            if not candidates:
                lines.append("- _(no domain known -- pass --company-domain or --known-email)_")
                continue
            for c in candidates:
                lines.append(f"- `{c['address']}`  ({c['pattern']})")
            lines.append("")
    lines.append("")
    lines.append("## Notes / log")
    lines.append("")
    lines.append("- [ ] Recruiter contacted (name, channel, date)")
    lines.append("- [ ] Hiring manager contacted (name, channel, date)")
    lines.append("- [ ] Referral request sent (name, channel, date)")
    lines.append("- [ ] Outreach reply (date, sentiment)")
    return "\n".join(lines).rstrip() + "\n"


def write_artifact(*, slug: str, art: ContactsArtifact) -> tuple[Path, Path]:
    """Write contacts.json + contacts.md under outputs/<slug>/internal/.
    Returns (json_path, md_path)."""
    out_dir = config.OUTPUTS_DIR / slug / "internal"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "contacts.json"
    md_path = out_dir / "contacts.md"
    payload = {
        "company": art.company,
        "role_title": art.role_title,
        "department": art.department,
        "company_domain": art.company_domain,
        "detected_pattern": art.detected_pattern,
        "seed_email": art.seed_email,
        "seed_name": art.seed_name,
        "search_links": art.search_links,
        "target_names": art.target_names,
        "candidate_emails_by_target": art.candidate_emails_by_target,
    }
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    md_path.write_text(render_md(art), encoding="utf-8")
    return json_path, md_path
