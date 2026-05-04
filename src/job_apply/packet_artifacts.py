"""V1 usage-upgrade packet helpers: README_APPLY.md (a checklist for the
human submitting the application), apply_url.txt (one-line direct URL to
copy/paste into the browser), and company_outreach.md (single outreach
message that covers a bundle of roles at one company).

Each function takes the in-memory packet dict (already validated) and the
matching `analyzed` job dict, writes the artifact under
`outputs/<slug>/internal/` (or `outputs/<company-slug>__bundle/internal/`
for company bundles), and returns the path."""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from . import config
from .render import _scrub_source_ids, collect_known_ids


def _outputs_dir() -> Path:
    """Resolved per-call so test conftest's OUTPUTS_DIR monkeypatch sticks."""
    return config.OUTPUTS_DIR


def _packet_dir(slug: str) -> Path:
    return _outputs_dir() / slug


def _internal_dir(slug: str) -> Path:
    d = _packet_dir(slug) / "internal"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _employer_dir(slug: str) -> Path:
    d = _packet_dir(slug) / "employer"
    d.mkdir(parents=True, exist_ok=True)
    return d


# ---------- apply_url.txt ----------

def write_apply_url(slug: str, *, apply_url: str) -> Path:
    """One-line .txt with the URL the user should open to apply. Lives in
    the packet root (not internal/) so it's findable."""
    p = _packet_dir(slug) / "apply_url.txt"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text((apply_url or "") + "\n", encoding="utf-8")
    return p


# ---------- README_APPLY.md ----------

def _format_packet_files(slug: str) -> list[str]:
    """List the files an applicant should attach / open, in order. Only
    includes files that actually exist on disk."""
    employer = _employer_dir(slug)
    internal = _internal_dir(slug)
    candidates = [
        ("Resume (PDF, attach this)",          employer / "tailored_resume.pdf"),
        ("Cover letter (PDF, attach this)",    employer / "cover_letter.pdf"),
        ("Resume (DOCX, fallback if portal needs Word)", employer / "tailored_resume.docx"),
        ("Cover letter (DOCX, fallback)",      employer / "cover_letter.docx"),
        ("Application answers (paste into portal text fields)",
         internal / "application_answers.md"),
        ("Match report (your reference)",      internal / "match_report.md"),
        ("Candidate brief (your reference)",   internal / "candidate_brief.md"),
        ("QA report (issues to read first)",   internal / "qa_report.md"),
        ("Outreach message (recruiter, optional follow-up)",
         internal / "outreach_recruiter.md"),
        ("Outreach message (hiring manager, optional follow-up)",
         internal / "outreach_hiring_manager.md"),
        ("LinkedIn DM (optional)",             internal / "linkedin_dm.md"),
    ]
    return [f"- **{label}** -> `{p.relative_to(_packet_dir(slug))}`"
            for label, p in candidates if p.exists()]


def write_readme_apply(*, slug: str, packet: dict[str, Any],
                        analyzed: dict[str, Any],
                        apply_url: str = "") -> Path:
    """Per-role apply checklist: where to apply, what to attach, what to
    paste, what to verify before submitting. Markdown so the user can
    open it in any viewer."""
    company = analyzed.get("company") or "(unknown company)"
    title = analyzed.get("title") or "(unknown role)"
    location = analyzed.get("location") or ""
    remote_mode = analyzed.get("remote_mode") or ""
    fit_score = packet.get("fit_score") or analyzed.get("fit_score") or "?"
    production_status = packet.get("production_status") or "?"
    strategic_interest = packet.get("strategic_interest") or "?"

    validation = packet.get("validation") or {}
    fab_blocks = validation.get("fabrication_blocks") or []
    fab_warnings = validation.get("fabrication_warnings") or []

    # Build the file checklist
    file_lines = _format_packet_files(slug)

    block_lines = ""
    if fab_blocks:
        block_lines = "\n## Hard blocks (DO NOT SUBMIT until resolved)\n\n"
        for b in fab_blocks:
            block_lines += f"- {b}\n"

    warn_lines = ""
    if fab_warnings:
        warn_lines = "\n## Soft warnings (review before submitting)\n\n"
        for w in fab_warnings:
            warn_lines += f"- {w}\n"

    md = f"""# Apply checklist: {company}, {title}

| | |
|---|---|
| Company | {company} |
| Role | {title} |
| Location | {location} {('(' + remote_mode + ')') if remote_mode else ''} |
| Fit score | {fit_score} |
| Production status | {production_status} |
| Strategic interest | {strategic_interest} |
| Apply URL | {apply_url or '(none captured, see analyzed/)'} |

## Step 1, open the apply page

```
{apply_url or '(no apply_url captured)'}
```

The same URL is in `apply_url.txt` (next to this file) so you can
`open $(cat outputs/{slug}/apply_url.txt)` from a shell.

## Step 2, attach / paste files

{chr(10).join(file_lines) if file_lines else '(no files generated yet, run `job-apply tailor` first)'}

## Step 3, before clicking Submit

- [ ] Resume PDF opens cleanly and matches what you reviewed
- [ ] Cover letter PDF references this company by name (no template leftover)
- [ ] No fabrication blocks remain (see above)
- [ ] Soft warnings reviewed and accepted (see above)
- [ ] Authorized-to-work, sponsorship, and location answers match `application_answers.md`
- [ ] If the portal asks for LinkedIn / GitHub URLs, paste from `secrets.yaml`
{block_lines}{warn_lines}
## Step 4, after submitting

```
job-apply set-status --ident {slug} --status submitted
```

This stamps `submitted_date = today` in `applications.xlsx`. Add an
optional `--notes "..."` (e.g. "applied via Workday, gave US-citizen
yes, no sponsorship") so future-you remembers the context.

---
_Generated {date.today().isoformat()} by job-apply._
"""
    p = _internal_dir(slug) / "README_APPLY.md"
    p.write_text(md, encoding="utf-8")
    return p


# ---------- company_outreach.md ----------

def _bundle_dir(company_slug: str) -> Path:
    """A bundle dir lives under outputs/<company-slug>__bundle/.
    Convention: __bundle suffix so it can't collide with a per-role slug."""
    d = _outputs_dir() / f"{company_slug}__bundle" / "internal"
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_company_outreach(*, company: str, company_slug: str,
                            roles: list[dict[str, Any]],
                            profile_data: dict[str, Any] | None = None) -> Path:
    """Single outreach message covering 2+ roles at one company.

    `roles` is a list of dicts with keys: title, apply_url, location,
    fit_score (any subset is fine, missing = blank).

    Output is a markdown file the user can copy into LinkedIn / email /
    a referral channel. No LLM call -- this is a deterministic template
    so the user can keep editing it without re-running tokens. The
    LLM-generated outreach_recruiter.md / outreach_hiring_manager.md
    inside each per-role packet are still available for richer one-off
    messages."""
    if not roles:
        raise ValueError("write_company_outreach: roles must be non-empty")

    role_lines: list[str] = []
    for r in roles:
        title = r.get("title") or "(role)"
        loc = r.get("location") or ""
        url = r.get("apply_url") or r.get("url") or ""
        fit = r.get("fit_score")
        loc_part = f" ({loc})" if loc else ""
        fit_part = f", fit ~{fit}/100" if fit else ""
        url_part = f"\n  {url}" if url else ""
        role_lines.append(f"- **{title}**{loc_part}{fit_part}{url_part}")

    known_ids = collect_known_ids(profile_data or {})
    plural = len(roles) > 1
    intro = (
        f"Hi {{{{first_name}}}}, I'm interested in two roles posted on "
        f"{company}'s careers page right now and wanted to reach out before "
        f"applying cold."
        if plural else
        f"Hi {{{{first_name}}}}, I'm interested in a role posted on "
        f"{company}'s careers page right now and wanted to reach out before "
        f"applying cold."
    )

    md = f"""# Outreach: {company} ({len(roles)} role{'s' if plural else ''})

> One outreach message that covers all approved roles at {company}.
> Replace the `{{{{first_name}}}}` placeholder with the actual recipient
> when you send. Edit freely, this file is not regenerated unless you
> re-run `job-apply pack-company`.

## Subject lines (pick one)

- {company}, application for {roles[0].get('title') or 'open role'}{(' + ' + str(len(roles) - 1) + ' related role' + ('s' if len(roles) > 2 else '')) if plural else ''}
- Quick note before I apply, {company}{(' (' + str(len(roles)) + ' roles)') if plural else ''}

## Roles I'm applying to

{chr(10).join(role_lines)}

## Message

{intro}

I'm finishing my MS in Cybersecurity (BA Computer Information Systems
already), hold CompTIA Network+ and Security+, and have hands-on lab
experience with SIEM, log monitoring, phishing analysis, and
vulnerability management. The roles above all line up with that
background, so rather than send N separate notes I wanted to flag them
together in case any one of them is the better fit on your end.

I've attached a tailored resume and a short note on why each role
matches. Happy to send the full packet for any specific role you'd
like to dig into, or to point me to the right person on your team.

Thanks,
{{{{full_name}}}}
{{{{email}}}}  ,  {{{{phone}}}}
{{{{linkedin_url}}}}
"""
    md = _scrub_source_ids(md, known_ids=known_ids)
    p = _bundle_dir(company_slug) / "company_outreach.md"
    p.write_text(md, encoding="utf-8")
    return p
