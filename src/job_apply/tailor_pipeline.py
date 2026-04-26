"""Orchestrate the tailor flow: tailor resume → emails → validate → render → save packet."""
from __future__ import annotations

from typing import Any

from . import email_writer, render, resume_tailor, state
from .llm_client import LLMClient
from .profile_loader import Profile, Secrets, load_profile, load_secrets
from .validators import fabrication
from .validators.schema import validate_packet


class TailorError(RuntimeError):
    pass


def run_tailor(
    *,
    job_id: str,
    force: bool = False,
    deep: bool = False,
    llm: LLMClient | None = None,
) -> tuple[dict[str, Any], str]:
    """Generate a packet for one analyzed job.

    Returns (packet, slug). Raises TailorError on missing prerequisites.
    The packet is saved to disk; failures populate validation.fabrication_blocks
    and the packet is still saved as `status="draft"` so the user can inspect it.
    """
    profile = load_profile()
    secrets = load_secrets()  # may be empty; substitution still works (no-op)

    analyzed = state.load_analyzed(job_id)
    if not analyzed:
        raise TailorError(f"job {job_id} not analyzed yet — run `job-apply analyze` first.")
    if analyzed.get("industry_filter") == "avoid" and not force:
        raise TailorError(
            f"job {job_id} is FILTER:AVOID (industry={analyzed.get('industry_tags')}). "
            f"Re-run with --force to override."
        )

    rec = state.load_ingest(job_id)
    if rec is None:
        raise TailorError(f"raw posting for {job_id} not found.")
    job_text = rec.text

    client = llm or LLMClient()
    tailored, tailor_model = resume_tailor.tailor(
        profile=profile, analyzed=analyzed, job_text=job_text, llm=client, deep=deep,
    )
    emails = email_writer.write_all(profile=profile, analyzed=analyzed, llm=client)

    # Fabrication validation runs on UNSUBSTITUTED text (placeholders still as templates).
    segs = fabrication.extract_segments_from_packet({"tailored": tailored})
    # Email bodies and the LinkedIn DM also go through validation:
    for kind in ("recruiter", "hiring_manager"):
        e = emails.get(kind, {})
        for p in e.get("body_paragraphs") or []:
            if isinstance(p, dict) and isinstance(p.get("text"), str):
                segs.append(fabrication.CitedSegment(
                    source_id=p.get("source_id") or "general", text=p["text"]
                ))
    dm = emails.get("linkedin_dm", {})
    if isinstance(dm.get("text"), str):
        sid = (dm.get("cited_items") or ["general"])[0]
        segs.append(fabrication.CitedSegment(source_id=sid, text=dm["text"]))

    report = fabrication.validate_segments(segs, profile.data)

    slug = state.packet_slug(analyzed.get("company") or "company", analyzed.get("title") or "role")
    out_dir = state.packet_dir(slug)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Render markdown views (substitution happens here, locally only).
    resume_md = render.render_resume(profile=profile, tailored=tailored, secrets=secrets)
    cover_md = render.render_cover_letter(
        profile=profile, tailored=tailored, secrets=secrets,
        company=analyzed.get("company") or "your team",
    )
    answers_md = render.render_application_answers(tailored=tailored)
    rec_email_md = render.render_email(
        subject=emails["recruiter"].get("subject", ""),
        body_paragraphs=emails["recruiter"].get("body_paragraphs") or [],
        signature_name=profile.full_name,
        secrets=secrets,
    )
    hm_email_md = render.render_email(
        subject=emails["hiring_manager"].get("subject", ""),
        body_paragraphs=emails["hiring_manager"].get("body_paragraphs") or [],
        signature_name=profile.full_name,
        secrets=secrets,
    )
    dm_md = render.render_linkedin_dm(emails["linkedin_dm"].get("text") or "")

    packet: dict[str, Any] = {
        "job_id": job_id,
        "slug": slug,
        "tailored": tailored,
        "rendered": {
            "tailored_resume_md": "tailored_resume.md",
            "cover_letter_md": "cover_letter.md",
            "application_answers_md": "application_answers.md",
            "outreach_recruiter_md": "outreach_recruiter.md",
            "outreach_hiring_manager_md": "outreach_hiring_manager.md",
            "linkedin_dm_md": "linkedin_dm.md",
            "match_report_md": "match_report.md",
        },
        "emails": emails,
        "validation": {
            **report.to_dict(),
            "schema_ok": True,
        },
        "status": "draft",
        "approval_log": [{"ts": state.now_iso(), "action": "draft"}],
        "prompt_versions": {
            "tailor": resume_tailor.PROMPT_VERSION,
            **email_writer.PROMPT_VERSIONS,
        },
        "model": tailor_model,
    }
    schema_errs = validate_packet(packet)
    if schema_errs:
        packet["validation"]["schema_ok"] = False
        packet["validation"]["schema_errors"] = schema_errs

    # Write all the markdown views.
    (out_dir / "tailored_resume.md").write_text(resume_md)
    (out_dir / "cover_letter.md").write_text(cover_md)
    (out_dir / "application_answers.md").write_text(answers_md)
    (out_dir / "outreach_recruiter.md").write_text(rec_email_md)
    (out_dir / "outreach_hiring_manager.md").write_text(hm_email_md)
    (out_dir / "linkedin_dm.md").write_text(dm_md)
    (out_dir / "match_report.md").write_text(render.render_match_report(analyzed, packet))
    state.save_packet(slug, packet)
    return packet, slug
