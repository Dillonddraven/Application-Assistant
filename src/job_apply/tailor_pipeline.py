"""Orchestrate the tailor flow: tailor resume → emails → validate → render → save packet."""
from __future__ import annotations

from typing import Any

from . import (email_writer, jd_analysis, mail_draft, qa_pass, render,
               render_docx, render_pdf, resume_tailor, state)
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
    open_mail: bool = False,
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

    # Stage 1: extract JD pain points + map to candidate evidence (cheap pre-pass).
    try:
        jd = jd_analysis.analyze_jd(
            profile=profile, analyzed=analyzed, job_text=job_text, llm=client,
        )
    except Exception as e:
        # If the analysis fails, downstream still works in fallback mode (no JD context).
        jd = {"pain_points": [], "evidence_map": [], "missing_evidence": [],
              "error": str(e), "prompt_version": "extract_jd_analysis@v1", "model": ""}

    # Stage 2: generation passes (resume + cover + answers in one tailor call;
    # three outreach variants in separate calls). All on the deep tier.
    tailored, tailor_model = resume_tailor.tailor(
        profile=profile, analyzed=analyzed, job_text=job_text, llm=client, deep=deep,
        jd_analysis=jd,
    )
    emails = email_writer.write_all(
        profile=profile, analyzed=analyzed, llm=client, jd_analysis=jd,
    )

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
    known_ids = render.collect_known_ids(profile.data)
    resume_md = render.render_resume(profile=profile, tailored=tailored, secrets=secrets)
    cover_md = render.render_cover_letter(
        profile=profile, tailored=tailored, secrets=secrets,
        company=analyzed.get("company") or "your team",
    )
    answers_md = render.render_application_answers(tailored=tailored, profile=profile)
    rec_email_md = render.render_email(
        subject=emails["recruiter"].get("subject", ""),
        body_paragraphs=emails["recruiter"].get("body_paragraphs") or [],
        signature_name=profile.full_name,
        secrets=secrets,
        known_ids=known_ids,
    )
    hm_email_md = render.render_email(
        subject=emails["hiring_manager"].get("subject", ""),
        body_paragraphs=emails["hiring_manager"].get("body_paragraphs") or [],
        signature_name=profile.full_name,
        secrets=secrets,
        known_ids=known_ids,
    )
    dm_md = render.render_linkedin_dm(emails["linkedin_dm"].get("text") or "", known_ids)

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
            "tailored_resume_pdf": "tailored_resume.pdf",
            "cover_letter_pdf": "cover_letter.pdf",
            "tailored_resume_docx": "tailored_resume.docx",
            "cover_letter_docx": "cover_letter.docx",
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

    # Write all the markdown views (match_report deferred until after QA so
    # the QA section is included).
    (out_dir / "tailored_resume.md").write_text(resume_md)
    (out_dir / "cover_letter.md").write_text(cover_md)
    (out_dir / "application_answers.md").write_text(answers_md)
    (out_dir / "outreach_recruiter.md").write_text(rec_email_md)
    (out_dir / "outreach_hiring_manager.md").write_text(hm_email_md)
    (out_dir / "linkedin_dm.md").write_text(dm_md)

    # PDF + DOCX renders. PDF is best-effort (Chromium may be missing); we log
    # the failure into validation but never block the rest of the packet.
    company = analyzed.get("company") or "Hiring Team"
    today = state.now_iso()[:10]
    render_errors: list[str] = []
    try:
        render_pdf.render_resume_pdf(
            profile=profile, tailored=tailored, secrets=secrets,
            out_path=out_dir / "tailored_resume.pdf",
        )
        render_pdf.render_cover_letter_pdf(
            profile=profile, tailored=tailored, secrets=secrets,
            out_path=out_dir / "cover_letter.pdf",
            company=company, date_iso=today,
        )
    except render_pdf.PDFRenderError as e:
        render_errors.append(f"pdf: {e}")
    try:
        render_docx.render_resume_docx(
            profile=profile, tailored=tailored, secrets=secrets,
            out_path=out_dir / "tailored_resume.docx",
        )
        render_docx.render_cover_letter_docx(
            profile=profile, tailored=tailored, secrets=secrets,
            out_path=out_dir / "cover_letter.docx",
            company=company, date_iso=today,
        )
    except Exception as e:  # docx is pure-python; failures are unexpected
        render_errors.append(f"docx: {e}")
    if render_errors:
        packet["validation"]["render_errors"] = render_errors

    # Stage 3: LLM-driven QA pass on the rendered views.
    try:
        rendered_views = {
            "tailored_resume": resume_md,
            "cover_letter": cover_md,
            "application_answers": answers_md,
            "outreach_recruiter": rec_email_md,
            "outreach_hiring_manager": hm_email_md,
            "linkedin_dm": dm_md,
        }
        qa = qa_pass.qa_check(
            rendered_views=rendered_views, jd_analysis=jd, llm=client,
        )
        packet["validation"]["qa"] = qa
        packet["jd_analysis"] = jd
        packet["prompt_versions"]["jd_analysis"] = jd.get("prompt_version", "")
        packet["prompt_versions"]["qa_check"] = qa.get("prompt_version", "")
    except Exception as e:
        packet["validation"]["qa_error"] = str(e)

    # Now write match_report (after QA so it includes the QA section).
    (out_dir / "match_report.md").write_text(render.render_match_report(analyzed, packet))

    state.save_packet(slug, packet)

    if open_mail:
        to_addr = secrets.data.get("email") if secrets.data else None
        if to_addr and not (packet["validation"].get("fabrication_blocks") or []):
            try:
                mail_draft.open_draft(
                    to_addr=to_addr,
                    subject=f"{company} — {analyzed.get('title') or 'role'} application packet",
                    body=(
                        f"Application packet for {company} — {analyzed.get('title') or 'role'} "
                        f"(fit score {analyzed.get('fit_score')}/100, "
                        f"industry filter: {analyzed.get('industry_filter')}).\n\n"
                        f"Files attached. Fabrication validator: 0 blocks. "
                        f"Nothing has been sent — review and send when ready.\n\n"
                        f"Source URL: {analyzed.get('source_url') or '(local file)'}"
                    ),
                    attachments=mail_draft.packet_attachments(out_dir),
                )
            except mail_draft.MailDraftError as e:
                packet["validation"].setdefault("mail_draft_error", str(e))
                state.save_packet(slug, packet)

    return packet, slug
