"""Orchestrate the tailor flow: tailor resume → emails → validate → render → save packet."""
from __future__ import annotations

import uuid
from typing import Any

from . import (candidate_brief, email_writer, jd_analysis, mail_draft, qa_pass,
               render, render_docx, render_pdf, resume_tailor, state)
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
    mode: str = "production",   # "production" (with early-stop) | "benchmark" (full pipeline)
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

    # === Posting quality gate (always-on, both modes) ===
    # If the analyzer flagged ingest_failure, refuse to tailor. Write a
    # diagnostic file so the user sees WHY and what to retry.
    quality = analyzed.get("posting_quality") or {"status": "ok", "reasons": []}
    if quality.get("status") == "ingest_failure" and not force:
        slug = state.packet_slug(analyzed.get("company") or "company",
                                 analyzed.get("title") or "role")
        out_dir = state.packet_dir(slug)
        internal_dir = out_dir / "internal"
        internal_dir.mkdir(parents=True, exist_ok=True)
        retry_advice = (
            "## Retry options\n"
            "- Run with `--refresh` to re-fetch the URL.\n"
            "- Re-ingest after sourcing the JD elsewhere: `job-apply ingest path/to/jd.txt`\n"
            "- Find the company's direct careers page (Greenhouse / Lever / Ashby / Workday) "
            "and ingest that URL instead.\n"
            "- For JS-rendered pages, the Playwright fallback is already automatic; "
            "if it fails, the page may require login or be expired.\n"
            "- Pass `--force` to override and tailor anyway (NOT RECOMMENDED — produces "
            "hallucinated artifacts).\n"
        )
        ingest_md = (
            f"# Ingest failure — {analyzed.get('company') or '?'} "
            f"({analyzed.get('title') or '?'})\n\n"
            f"The posting failed the quality gate. Tailoring was NOT run; no LLM tokens "
            f"were spent on resume / cover letter / outreach generation.\n\n"
            f"## Reasons\n"
            + "\n".join(f"- {r}" for r in (quality.get("reasons") or []))
            + f"\n\n## Source\n- URL: {analyzed.get('source_url') or '(local)'}\n"
            + f"- Char count: {quality.get('char_count', '?')}\n"
            + f"- Responsibilities extracted: {quality.get('responsibilities_count', '?')}\n"
            + f"- Requirements extracted: {quality.get('requirements_count', '?')}\n"
            + f"- Shell-marker hits: {quality.get('shell_marker_hits', '?')}\n\n"
            + retry_advice
        )
        (internal_dir / "ingest_failure.md").write_text(ingest_md)
        packet = {
            "job_id": job_id, "slug": slug,
            "run_id": uuid.uuid4().hex[:8],
            "tailored": {},
            "rendered": {"internal": {"ingest_failure_md": "internal/ingest_failure.md"}},
            "validation": {"fabrication_blocks": [], "fabrication_warnings": [],
                           "schema_ok": True},
            "status": "ingest_failure",
            "posting_quality": quality,
            "production_status": "ingest_failure",
            "strategic_interest": "low",
            "approval_log": [{"ts": state.now_iso(), "action": "ingest_failure_short_circuit"}],
            "prompt_versions": {}, "model": "n/a",
            "blocked": True,
        }
        state.save_packet(slug, packet)
        return packet, slug

    client = llm or LLMClient()

    # === Production-mode early-stop ===
    # Skip the expensive employer-facing generation when fit is too low.
    # Always still produce the JD analysis, candidate brief, scorecard, and
    # skip_reason, so the user can see WHY we stopped and study any gaps.
    fit = int(analyzed.get("fit_score") or 0)
    sc = (analyzed.get("source_confidence") or "medium").lower()
    industry_filter = analyzed.get("industry_filter") or "ok"
    early_stop = False
    early_stop_reason = ""
    early_stop_mode = "full"   # "full" | "lightweight" | "skip"
    if mode == "production":
        if industry_filter == "avoid" and not force:
            early_stop = True
            early_stop_reason = (
                f"industry filter set to AVOID (tags: {analyzed.get('industry_tags')}). "
                f"Pass --force to override."
            )
            early_stop_mode = "skip"
        elif fit < 50:
            early_stop = True
            early_stop_reason = (
                f"fit score {fit} below production threshold of 50. "
                f"Top gaps: {analyzed.get('top_gaps') or []}. "
                f"Use --mode benchmark to generate the full packet anyway."
            )
            early_stop_mode = "skip"
        elif 50 <= fit < 65:
            # Lightweight: JD analysis + brief + scorecard, NO employer renders.
            early_stop = True
            early_stop_reason = (
                f"fit score {fit} in 50-64 'maybe' band. Generating lightweight "
                f"internal review packet only. Use --force to render employer "
                f"PDFs or --mode benchmark for the full pipeline."
            )
            early_stop_mode = "lightweight"

    # If we're in production-mode early-stop=skip, write a minimal record and exit.
    if early_stop and early_stop_mode == "skip" and not force:
        slug = state.packet_slug(analyzed.get("company") or "company",
                                 analyzed.get("title") or "role")
        out_dir = state.packet_dir(slug)
        internal_dir = out_dir / "internal"
        employer_dir = out_dir / "employer"
        internal_dir.mkdir(parents=True, exist_ok=True)
        # Clean stale employer artifacts from any prior benchmark / unblocked run,
        # so a current "skip" packet doesn't leave hallucinated PDFs lying around.
        if employer_dir.exists():
            for stale in employer_dir.glob("*"):
                if stale.is_file():
                    try:
                        stale.unlink()
                    except OSError:
                        pass
        skip_md = (
            f"# Skipped — {analyzed.get('company')} ({analyzed.get('title')})\n\n"
            f"**Production mode: skip.** {early_stop_reason}\n\n"
            f"## Fit breakdown\n"
            + "\n".join(f"- {k}: {v}" for k, v in (analyzed.get("fit_breakdown") or {}).items())
            + "\n\n## Reasoning trace\n"
            + "\n".join(f"- {r}" for r in (analyzed.get("apply_reasoning") or []))
            + "\n\n## To override and generate a full packet\n"
            + "- `job-apply tailor <job-id> --force --mode benchmark`\n"
        )
        (internal_dir / "skip_reason.md").write_text(skip_md)
        # Compute strategic_interest even for skipped roles — they may still be worth tracking.
        from . import bench as _bench
        target_roles = (profile.data.get("preferences") or {}).get("target_roles") or []
        skip_packet = {
            "job_id": job_id, "slug": slug,
            "run_id": uuid.uuid4().hex[:8],
            "tailored": {}, "rendered": {"internal": {"skip_reason_md": "internal/skip_reason.md"}},
            "validation": {"fabrication_blocks": [], "fabrication_warnings": [],
                           "schema_ok": True},
            "status": "skipped",
            "early_stop": True, "early_stop_reason": early_stop_reason,
            "early_stop_mode": "skip",
            "production_mode_decision": "skip",
            "approval_log": [{"ts": state.now_iso(), "action": "early_stop_skip"}],
            "prompt_versions": {}, "model": "n/a",
            "blocked": True,    # nothing to render
            "jd_analysis": {},  # not generated; let strategic_interest fall back to fit-only logic
        }
        skip_packet["production_status"] = _bench.derive_production_status(
            analyzed=analyzed, packet=skip_packet,
        )
        interest, reason_consider = _bench.derive_strategic_interest(
            analyzed=analyzed, packet=skip_packet, profile_target_roles=target_roles,
        )
        skip_packet["strategic_interest"] = interest
        if reason_consider:
            skip_packet["reason_to_still_consider"] = reason_consider
        state.save_packet(slug, skip_packet)
        return skip_packet, slug

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
    employer_dir = out_dir / "employer"
    internal_dir = out_dir / "internal"
    out_dir.mkdir(parents=True, exist_ok=True)
    employer_dir.mkdir(parents=True, exist_ok=True)
    internal_dir.mkdir(parents=True, exist_ok=True)

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
        "run_id": uuid.uuid4().hex[:8],
        "tailored": tailored,
        "rendered": {
            # Employer-facing artifacts (PDF + DOCX, polished, employer email attachments).
            "employer": {
                "tailored_resume_pdf": "employer/tailored_resume.pdf",
                "tailored_resume_docx": "employer/tailored_resume.docx",
                "cover_letter_pdf": "employer/cover_letter.pdf",
                "cover_letter_docx": "employer/cover_letter.docx",
            },
            # Internal review artifacts (markdown views + report). Never sent to employer.
            "internal": {
                "tailored_resume_md": "internal/tailored_resume.md",
                "cover_letter_md": "internal/cover_letter.md",
                "application_answers_md": "internal/application_answers.md",
                "outreach_recruiter_md": "internal/outreach_recruiter.md",
                "outreach_hiring_manager_md": "internal/outreach_hiring_manager.md",
                "linkedin_dm_md": "internal/linkedin_dm.md",
                "match_report_md": "internal/match_report.md",
            },
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

    # Write all the markdown views into internal/ (match_report deferred until
    # after the QA pass below so the QA section is included).
    (internal_dir / "tailored_resume.md").write_text(resume_md)
    (internal_dir / "cover_letter.md").write_text(cover_md)
    (internal_dir / "application_answers.md").write_text(answers_md)
    (internal_dir / "outreach_recruiter.md").write_text(rec_email_md)
    (internal_dir / "outreach_hiring_manager.md").write_text(hm_email_md)
    (internal_dir / "linkedin_dm.md").write_text(dm_md)

    # Defer the employer-facing render (PDF + DOCX) until AFTER the QA pass
    # so HIGH-severity issues can hard-block it. We need fabrication validator
    # blocks to also block here. Below: stage 3 QA → guard → render.
    company = analyzed.get("company") or "Hiring Team"
    today = state.now_iso()[:10]

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
        forbidden = (profile.data.get("writing_style") or {}).get("forbidden_phrases") or []
        qa = qa_pass.qa_check(
            rendered_views=rendered_views, jd_analysis=jd, llm=client,
            forbidden_phrases=forbidden,
        )
        packet["validation"]["qa"] = qa
        packet["jd_analysis"] = jd
        packet["prompt_versions"]["jd_analysis"] = jd.get("prompt_version", "")
        packet["prompt_versions"]["qa_check"] = qa.get("prompt_version", "")
    except Exception as e:
        packet["validation"]["qa_error"] = str(e)
        qa = {"issues": [], "overall_polish": "ready"}

    # === GUARD ===
    # Any HIGH-severity QA issue OR any fabrication block blocks the
    # employer-facing render and the Mail draft. Production lightweight mode
    # also blocks render until the user approves with --force. Internal
    # markdowns are still written for review.
    high_issues = [i for i in (qa.get("issues") or []) if i.get("severity") == "high"]
    fab_blocks = packet["validation"].get("fabrication_blocks") or []
    qa_blocked = bool(high_issues or fab_blocks)
    lightweight_blocked = (early_stop and early_stop_mode == "lightweight" and not force)
    is_blocked = qa_blocked or lightweight_blocked
    packet["blocked"] = is_blocked
    packet["block_reasons"] = {
        "high_qa_issues": [
            {"category": i.get("category"), "where": i.get("where"),
             "snippet": i.get("snippet"), "fix_suggestion": i.get("fix_suggestion")}
            for i in high_issues
        ],
        "fabrication_blocks": fab_blocks,
        "lightweight_mode_pending_approval": (
            early_stop_reason if lightweight_blocked else None
        ),
    }
    packet["early_stop"] = early_stop
    packet["early_stop_reason"] = early_stop_reason
    packet["early_stop_mode"] = early_stop_mode
    packet["production_mode_decision"] = (
        "skip" if (mode == "production" and fit < 50) else
        "lightweight" if (mode == "production" and fit < 65) else
        "full"
    )

    # Render employer PDF + DOCX ONLY if the packet is not blocked.
    render_errors: list[str] = []
    if not is_blocked:
        try:
            render_pdf.render_resume_pdf(
                profile=profile, tailored=tailored, secrets=secrets,
                out_path=employer_dir / "tailored_resume.pdf",
            )
            render_pdf.render_cover_letter_pdf(
                profile=profile, tailored=tailored, secrets=secrets,
                out_path=employer_dir / "cover_letter.pdf",
                company=company, date_iso=today,
            )
        except render_pdf.PDFRenderError as e:
            render_errors.append(f"pdf: {e}")
        try:
            render_docx.render_resume_docx(
                profile=profile, tailored=tailored, secrets=secrets,
                out_path=employer_dir / "tailored_resume.docx",
            )
            render_docx.render_cover_letter_docx(
                profile=profile, tailored=tailored, secrets=secrets,
                out_path=employer_dir / "cover_letter.docx",
                company=company, date_iso=today,
            )
        except Exception as e:
            render_errors.append(f"docx: {e}")
    else:
        # Clean any stale employer renders so a previous "ready" run doesn't
        # leave stale PDFs lying around when this run is blocked.
        for stale in employer_dir.glob("*"):
            if stale.is_file():
                stale.unlink()
    if render_errors:
        packet["validation"]["render_errors"] = render_errors

    # Persist a separate qa_report.md and evidence_map.json under internal/ for visibility.
    (internal_dir / "qa_report.md").write_text(render.render_qa_report(qa))
    if jd:
        import json as _json
        (internal_dir / "evidence_map.json").write_text(_json.dumps(jd, indent=2))

    # Generate the candidate-facing interview prep brief + claim stress test
    # (both internal only, never sent to an employer). Generated on every packet,
    # including blocked ones, so the user can study the role + their gaps + their
    # talking points + truth-check claims either way.
    try:
        brief = candidate_brief.generate_brief(
            profile=profile, analyzed=analyzed, tailored=tailored,
            jd_analysis=jd, qa=qa, llm=client,
        )
        try:
            stress = candidate_brief.generate_stress_test(
                profile=profile, analyzed=analyzed, tailored=tailored,
                rendered_views=rendered_views, jd_analysis=jd, llm=client,
            )
            brief["stress_test"] = stress
            packet["prompt_versions"]["claim_stress_test"] = stress.get("prompt_version", "")
        except Exception as e:
            packet["validation"]["stress_test_error"] = str(e)
        (internal_dir / "candidate_brief.md").write_text(
            candidate_brief.render_brief_md(brief)
        )
        packet["candidate_brief"] = brief
        packet["prompt_versions"]["candidate_brief"] = brief.get("prompt_version", "")
    except Exception as e:
        packet["validation"]["candidate_brief_error"] = str(e)

    # Now write match_report (after QA so it includes the QA section).
    (internal_dir / "match_report.md").write_text(render.render_match_report(analyzed, packet))

    # Derive production_status + strategic_interest (independent of apply_recommendation).
    from . import bench as _bench
    target_roles = (profile.data.get("preferences") or {}).get("target_roles") or []
    packet["production_status"] = _bench.derive_production_status(
        analyzed=analyzed, packet=packet,
    )
    interest, reason_consider = _bench.derive_strategic_interest(
        analyzed=analyzed, packet=packet, profile_target_roles=target_roles,
    )
    packet["strategic_interest"] = interest
    if reason_consider:
        packet["reason_to_still_consider"] = reason_consider

    state.save_packet(slug, packet)

    if open_mail:
        to_addr = secrets.data.get("email") if secrets.data else None
        if not to_addr:
            packet["validation"].setdefault("mail_draft_error",
                                             "no email in secrets.yaml; cannot open draft")
        elif is_blocked:
            # Hard-stop: do not open a Mail draft when employer renders are blocked.
            packet["validation"].setdefault(
                "mail_draft_error",
                f"BLOCKED: {len(high_issues)} high-severity QA issue(s) and "
                f"{len(fab_blocks)} fabrication block(s). No employer-facing "
                f"render produced; no Mail draft opened. Fix issues then re-tailor."
            )
        else:
            try:
                run_id = packet["run_id"]
                attachments = mail_draft.packet_attachments(
                    out_dir, mode="employer", include_docx=False,
                )
                if not attachments:
                    raise mail_draft.MailDraftError(
                        "no employer-facing PDF found; refusing to open empty draft"
                    )
                subject = mail_draft.stamp_subject(
                    f"{company} — {analyzed.get('title') or 'role'}", run_id,
                )
                body = (
                    f"Draft for {company} — {analyzed.get('title') or 'role'}. "
                    f"Fit {analyzed.get('fit_score')}/100, source confidence "
                    f"{analyzed.get('source_confidence', 'unknown')}, QA polish "
                    f"{(packet['validation'].get('qa') or {}).get('overall_polish', '?')}.\n\n"
                    f"Attachments: polished resume + cover letter PDF only.\n"
                    f"Source URL: {analyzed.get('source_url') or '(local file)'}\n\n"
                    f"Internal review files (markdown views, match_report, qa_report) live "
                    f"under outputs/{slug}/internal/ and were NOT attached.\n\n"
                    f"Run id: {run_id}"
                )
                mail_draft.open_draft(
                    to_addr=to_addr, subject=subject, body=body,
                    attachments=attachments,
                )
                packet["mail_draft"] = {
                    "opened": True, "run_id": run_id, "subject": subject,
                    "attachment_count": len(attachments),
                    "to": to_addr,
                }
            except mail_draft.MailDraftError as e:
                packet["validation"].setdefault("mail_draft_error", str(e))
        state.save_packet(slug, packet)

    return packet, slug
