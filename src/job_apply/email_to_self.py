"""V1 usage-upgrade email layer: single-role and company-bundle emails to
the user themself (Dillon) for human review before submitting.

Two modes:
  - "single": one role -> one email with that role's apply checklist +
              PDF resume + cover letter + apply_url + match_report.
  - "company-bundle": all approved roles at one company -> one email
              with each role's PDFs and the company outreach message.

Default behavior is **draft only**: write a markdown file representing the
email under outputs/<slug>/internal/email_to_dillon.md (or the bundle's
internal/) AND optionally open a Mail.app draft. No auto-send. The user
reviews in Mail (or just opens the .md) and clicks Send themselves.

The user's recipient address comes from secrets.yaml -> email. Subject lines
include a [run: <run_id>] tag for traceability when paired with
mail_draft.close_drafts_with_run_id."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from . import config, mail_draft, profile_loader, state
from . import packet_artifacts


@dataclass
class EmailDraft:
    """In-memory representation of an email-to-dillon draft. Caller decides
    whether to open it in Mail.app or just dump the .md."""
    to_addr: str
    subject: str
    body: str
    attachments: list[Path]
    md_path: Path                 # where the markdown view was/will be written
    mode: str                     # "single" | "company-bundle"
    slug: str                     # per-role slug, OR <company>__bundle for bundle
    run_id: str                   # from packet, or "" for bundles


def _outputs_dir() -> Path:
    return config.OUTPUTS_DIR


def _resolve_to_addr(secrets: profile_loader.Secrets | None,
                      override: str | None = None) -> str:
    """Recipient = override > secrets.yaml.email. Raises if neither set."""
    if override and override.strip():
        return override.strip()
    if secrets and secrets.data:
        addr = secrets.data.get("email") or ""
        if addr:
            return addr
    raise ValueError(
        "no recipient email address. Pass to_addr=... or set `email:` in "
        "profile/secrets.yaml."
    )


# ---------- single-role email ----------

def prepare_single_role_email(*, slug: str, packet: dict[str, Any],
                                analyzed: dict[str, Any],
                                apply_url: str = "",
                                to_addr: str = "",
                                secrets: profile_loader.Secrets | None = None,
                                ) -> EmailDraft:
    """Compose a per-role email-to-dillon draft. Writes
    outputs/<slug>/internal/email_to_dillon.md and returns the assembled
    EmailDraft."""
    company = analyzed.get("company") or "(unknown company)"
    title = analyzed.get("title") or "(unknown role)"
    fit = packet.get("fit_score") or analyzed.get("fit_score") or "?"
    production_status = packet.get("production_status") or "?"
    strategic_interest = packet.get("strategic_interest") or "?"
    run_id = packet.get("run_id") or ""

    out_dir = _outputs_dir() / slug
    employer = out_dir / "employer"

    attachments: list[Path] = []
    for fname in ("tailored_resume.pdf", "cover_letter.pdf"):
        f = employer / fname
        if f.exists():
            attachments.append(f)
    # Apply_url.txt is helpful as an attachment too
    apply_url_file = out_dir / "apply_url.txt"
    if apply_url_file.exists():
        attachments.append(apply_url_file)

    validation = packet.get("validation") or {}
    fab_blocks = validation.get("fabrication_blocks") or []
    fab_warnings = validation.get("fabrication_warnings") or []

    blocks_md = ""
    if fab_blocks:
        blocks_md = "\n\n## ⚠ Hard blocks (resolve before submitting)\n\n"
        blocks_md += "\n".join(f"- {b}" for b in fab_blocks)
    warnings_md = ""
    if fab_warnings:
        warnings_md = "\n\n## Soft warnings (review)\n\n"
        warnings_md += "\n".join(f"- {w}" for w in fab_warnings)

    subject = f"Application packet ready: {company}, {title}"
    body = (
        f"Apply checklist for {company}, {title}.\n\n"
        f"Apply URL: {apply_url or '(none captured)'}\n"
        f"Fit score: {fit}\n"
        f"Production status: {production_status}\n"
        f"Strategic interest: {strategic_interest}\n\n"
        f"Attached: tailored resume PDF, cover letter PDF, apply_url.txt.\n\n"
        f"After submitting, run:\n"
        f"  job-apply set-status --ident {slug} --status submitted\n\n"
        f"To attach DOCX too, re-run with --include-docx.\n"
    )
    if fab_blocks:
        body += (
            f"\n⚠ HARD BLOCKS: {len(fab_blocks)} issue(s). DO NOT SUBMIT until "
            f"resolved (see README_APPLY.md).\n"
        )

    md_view = f"""# Email draft: {company}, {title}

> Mode: single-role | Run: {run_id or '(no run_id)'}
> Drafted at: {datetime.now().isoformat(timespec='seconds')}

**To:** {to_addr or '(see secrets.yaml)'}
**Subject:** {subject}

---

{body}{blocks_md}{warnings_md}

## Attachments

{chr(10).join(f'- `{a}`' for a in attachments) if attachments else '(none — packet not built)'}
"""
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "internal").mkdir(parents=True, exist_ok=True)
    md_path = out_dir / "internal" / "email_to_dillon.md"
    md_path.write_text(md_view, encoding="utf-8")

    resolved_to = _resolve_to_addr(secrets, to_addr)
    return EmailDraft(
        to_addr=resolved_to,
        subject=mail_draft.stamp_subject(subject, run_id) if run_id else subject,
        body=body,
        attachments=attachments,
        md_path=md_path,
        mode="single",
        slug=slug,
        run_id=run_id,
    )


# ---------- company-bundle email ----------

def prepare_company_bundle_email(*, company: str, company_slug: str,
                                    role_packets: list[dict[str, Any]],
                                    role_analyzed: dict[str, dict[str, Any]],
                                    role_slugs: list[str],
                                    role_apply_urls: dict[str, str] | None = None,
                                    to_addr: str = "",
                                    secrets: profile_loader.Secrets | None = None,
                                    ) -> EmailDraft:
    """Bundle email: 2+ roles at one company in a single draft.

    `role_packets`, `role_analyzed`, `role_slugs` must align by index.
    `role_apply_urls` maps slug -> URL (may be empty)."""
    if not role_packets:
        raise ValueError("prepare_company_bundle_email: role_packets is empty")
    if len(role_packets) != len(role_slugs):
        raise ValueError("role_packets and role_slugs must have same length")

    role_apply_urls = role_apply_urls or {}
    role_lines: list[str] = []
    attachments: list[Path] = []
    seen_paths: set[Path] = set()

    for i, slug in enumerate(role_slugs):
        pkt = role_packets[i]
        ana = role_analyzed.get(slug) or {}
        title = ana.get("title") or "(role)"
        loc = ana.get("location") or ""
        fit = pkt.get("fit_score") or ana.get("fit_score") or "?"
        url = role_apply_urls.get(slug) or ana.get("source_url") or ""
        loc_part = f" ({loc})" if loc else ""
        role_lines.append(
            f"- **{title}**{loc_part}, fit {fit}/100\n"
            f"  Apply: {url or '(no URL captured)'}\n"
            f"  Packet: outputs/{slug}/"
        )
        # Each role's PDFs
        emp = _outputs_dir() / slug / "employer"
        for fname in ("tailored_resume.pdf", "cover_letter.pdf"):
            f = emp / fname
            if f.exists() and f not in seen_paths:
                attachments.append(f)
                seen_paths.add(f)

    # Bundle outreach message (if it exists)
    bundle_dir = _outputs_dir() / f"{company_slug}__bundle" / "internal"
    outreach = bundle_dir / "company_outreach.md"
    if outreach.exists() and outreach not in seen_paths:
        attachments.append(outreach)
        seen_paths.add(outreach)

    plural = len(role_slugs) > 1
    subject = (
        f"Application bundle ready: {company} ({len(role_slugs)} roles)"
        if plural else
        f"Application packet ready: {company}, {role_analyzed.get(role_slugs[0], {}).get('title') or 'role'}"
    )
    body = (
        f"{len(role_slugs)} role{'s' if plural else ''} ready at {company}.\n\n"
        + "\n".join(role_lines)
        + "\n\n"
        + "Attached: tailored resume + cover letter PDF for each role"
        + (", plus the company-outreach message." if outreach.exists() else ".")
        + "\n\n"
        + "After submitting each, run:\n"
        + "\n".join(
            f"  job-apply set-status --ident {s} --status submitted"
            for s in role_slugs
        )
        + "\n"
    )

    md_view = f"""# Email draft: {company} bundle

> Mode: company-bundle | Roles: {len(role_slugs)}
> Drafted at: {datetime.now().isoformat(timespec='seconds')}

**To:** {to_addr or '(see secrets.yaml)'}
**Subject:** {subject}

---

{body}

## Attachments

{chr(10).join(f'- `{a}`' for a in attachments) if attachments else '(none)'}
"""
    bundle_dir.mkdir(parents=True, exist_ok=True)
    md_path = bundle_dir / "email_to_dillon.md"
    md_path.write_text(md_view, encoding="utf-8")

    resolved_to = _resolve_to_addr(secrets, to_addr)
    return EmailDraft(
        to_addr=resolved_to,
        subject=subject,
        body=body,
        attachments=attachments,
        md_path=md_path,
        mode="company-bundle",
        slug=f"{company_slug}__bundle",
        run_id="",
    )


# ---------- driver ----------

def open_in_mail(draft: EmailDraft) -> None:
    """Open the prepared draft in Mail.app. Raises MailDraftError on failure
    (caller catches and falls back to md-only). No auto-send."""
    if not draft.attachments:
        raise mail_draft.MailDraftError(
            f"no attachments to send for {draft.slug} -- run `job-apply tailor` first."
        )
    mail_draft.open_draft(
        to_addr=draft.to_addr,
        subject=draft.subject,
        body=draft.body,
        attachments=draft.attachments,
    )
