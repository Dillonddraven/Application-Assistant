"""Benchmark harness: run the pipeline against a list of postings, produce
per-role packets in `runs/<slug>_<date>/`, scorecards, and a batch summary.

This is a separate output path from `outputs/<slug>/` so benchmark runs don't
collide with regular tailor runs and so each benchmark gets a dated folder.
"""
from __future__ import annotations

import json
import re
import shutil
import traceback
from dataclasses import dataclass, field, asdict
from datetime import date
from pathlib import Path
from typing import Any

from . import (candidate_brief, email_writer, jd_analysis, job_analyzer,
               job_ingest, mail_draft, qa_pass, render, render_docx,
               render_pdf, resume_tailor, state)
from .config import ROOT
from .llm_client import LLMClient
from .profile_loader import load_profile, load_secrets

RUNS_DIR = ROOT / "runs"


# Workday / SmartRecruiters / SailPoint pages are JS-rendered. httpx/trafilatura
# returns near-empty shells. Fall back to Playwright headless Chromium when the
# extracted text is too short.
JS_FALLBACK_DOMAINS = ("myworkdayjobs.com", "workday.com")
MIN_EXTRACTED_CHARS = 500


def _slugify(s: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").lower()
    return s or "untitled"


def _playwright_fetch(url: str, *, timeout_ms: int = 25000) -> str:
    """Fallback fetch via headless Chromium for JS-rendered pages."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=timeout_ms)
            # Wait a bit longer for SPA mounts.
            page.wait_for_timeout(2000)
            return page.content()
        finally:
            browser.close()


def robust_ingest(url: str, *, refresh: bool = True) -> tuple[str | None, str | None]:
    """Try the standard ingest; if extraction is too thin, fall back to Playwright.
    Returns (job_id, error_message). Either is None on success/failure."""
    try:
        result = job_ingest.ingest(url, refresh=refresh)
        text = result.record.text
        if len(text) < MIN_EXTRACTED_CHARS or any(d in url for d in JS_FALLBACK_DOMAINS):
            try:
                html = _playwright_fetch(url)
                from job_apply.job_ingest import _extract_main_text
                better = _extract_main_text(html, url=url)
                if len(better) > len(text) + 100:
                    job_id = state.job_id_for(url, is_url=True)
                    state.save_ingest(
                        job_id=job_id, text=better, source_url=url, source_kind="url",
                    )
                    return job_id, None
            except Exception:
                pass
        return result.record.job_id, None
    except Exception as e:
        # Try Playwright fallback as a last-ditch effort
        try:
            html = _playwright_fetch(url)
            from job_apply.job_ingest import _extract_main_text
            text = _extract_main_text(html, url=url)
            if len(text) >= MIN_EXTRACTED_CHARS:
                job_id = state.job_id_for(url, is_url=True)
                state.save_ingest(
                    job_id=job_id, text=text, source_url=url, source_kind="url",
                )
                return job_id, None
        except Exception:
            pass
        return None, str(e)


# Role-category rules: (category_name, [skill/keyword markers])
ROLE_CATEGORY_RULES: list[tuple[str, list[str]]] = [
    ("GRC / Compliance", ["soc 2", "iso 27001", "policy", "risk register",
                          "control testing", "evidence collection", "fedramp",
                          "nist 800", "cmmc", "audit"]),
    ("Vulnerability Management", ["vulnerability management", "vulnerability assessment",
                                  "remediation tracking", "patch management",
                                  "vuln lifecycle"]),
    ("SOC Analyst", ["soc analyst", "siem", "security operations center",
                     "alert triage", "tier 1", "tier 2", "incident response"]),
    ("IT Security Hybrid", ["onboarding", "offboarding", "access review",
                            "endpoint", "workstation", "helpdesk"]),
    ("Security Automation", ["soar", "playbook automation", "automation engineer",
                             "detection engineer"]),
    ("Cloud Security", ["aws security", "azure security", "gcp security",
                        "cloud security", "kubernetes security"]),
    ("IAM Analyst", ["iam", "identity and access", "okta", "sailpoint", "active directory"]),
    ("Stretch", ["senior", "5+ years", "lead", "principal", "architect"]),
]


def classify_role_category(analyzed: dict[str, Any]) -> str:
    haystack = " ".join([
        (analyzed.get("title") or "").lower(),
        " ".join((analyzed.get("required_skills") or [])).lower(),
        " ".join((analyzed.get("preferred_skills") or [])).lower(),
        " ".join((analyzed.get("responsibilities") or [])).lower(),
        " ".join((analyzed.get("keywords_extracted") or [])).lower(),
    ])
    for category, markers in ROLE_CATEGORY_RULES:
        if any(m in haystack for m in markers):
            return category
    title = (analyzed.get("title") or "").lower()
    if "analyst" in title and "security" in title:
        return "Cybersecurity Analyst (general)"
    return "Other"


def derive_apply_recommendation(*, analyzed: dict[str, Any], packet: dict[str, Any],
                                qa: dict[str, Any]) -> tuple[str, str]:
    fit = int(analyzed.get("fit_score") or 0)
    source = (analyzed.get("source_confidence") or "medium").lower()
    industry_filter = analyzed.get("industry_filter") or "ok"
    blocked = bool(packet.get("blocked"))
    high_qa = sum(1 for i in (qa.get("issues") or []) if i.get("severity") == "high")
    fab = len(packet.get("validation", {}).get("fabrication_blocks") or [])
    missing = len((packet.get("jd_analysis") or {}).get("missing_evidence") or [])
    pen_test_required = any(
        "penetration" in (s or "").lower()
        for s in (analyzed.get("required_skills") or [])
    )
    clearance = "clearance" in (
        " ".join(analyzed.get("required_skills") or []) + " " +
        " ".join(analyzed.get("responsibilities") or [])
    ).lower()

    # Hard skip conditions
    if blocked or high_qa or fab:
        return "skip", f"blocked: {high_qa} HIGH QA, {fab} fabrication block(s)"
    if industry_filter == "avoid":
        return "skip", "industry filter set to AVOID (military/defense)"
    if clearance:
        return "skip", "active security clearance required (Dillon does not have one)"
    if fit < 35:
        return "skip", f"fit score {fit} too low; gaps too significant"

    # Maybe band: real fit but some friction
    if fit < 55:
        return "maybe", f"fit score {fit}; meaningful gaps"
    if missing >= 3:
        return "maybe", f"{missing} pain points without supporting evidence"
    if source == "low":
        return "maybe", f"fit {fit} but source confidence LOW (aggregator); apply via direct careers page"
    if pen_test_required:
        return "maybe", "JD lists pen testing; adjacent skills only — be honest in interview"

    return "apply", f"fit {fit}, source {source}, no major blockers"


# Standardized portal-readiness lists
SAFE_AUTOFILL = [
    "name", "email", "phone", "linkedin", "github", "portfolio",
    "resume_upload", "cover_letter_upload",
    "education", "certifications", "city", "state", "work_authorization",
]
HUMAN_REVIEW_REQUIRED = [
    "desired_salary", "sponsorship_visa", "relocation", "shift_availability",
    "start_date", "custom_long_answers", "legal_acknowledgements",
    "demographic_or_disability_or_veteran", "final_submit",
]
NEVER_AUTO_ANSWER = [
    "demographic_identity", "disability_status", "veteran_status",
    "criminal_background", "legal_attestation",
]


def estimate_review_time_minutes(*, packet: dict[str, Any], qa: dict[str, Any],
                                 portal_complexity: str) -> int:
    base = 10
    issues = qa.get("issues") or []
    base += 2 * sum(1 for i in issues if i.get("severity") == "medium")
    base += 1 * sum(1 for i in issues if i.get("severity") == "low")
    base += {"low": 0, "medium": 5, "high": 15}.get(portal_complexity, 5)
    soften = len(((packet.get("candidate_brief") or {}).get("stress_test") or {})
                 .get("claims_to_soften_or_remove") or [])
    base += soften * 1
    return base


PORTAL_COMPLEXITY_BY_ATS = {
    "myworkdayjobs": "high",
    "workday": "high",
    "icims": "high",
    "greenhouse": "low",
    "lever": "low",
    "ashby": "low",
    "smartrecruiters": "medium",
    "workable": "low",
}


def classify_portal_complexity(url: str | None) -> str:
    if not url:
        return "medium"
    u = url.lower()
    for marker, level in PORTAL_COMPLEXITY_BY_ATS.items():
        if marker in u:
            return level
    return "medium"


def pdf_page_count(pdf_path: Path) -> int:
    try:
        data = pdf_path.read_bytes()
        return len(re.findall(rb"/Type\s*/Page[^s]", data))
    except Exception:
        return 0


def build_scorecard(*, slug: str, run_dir: Path, analyzed: dict[str, Any],
                    packet: dict[str, Any]) -> dict[str, Any]:
    qa = (packet.get("validation") or {}).get("qa") or {}
    brief = packet.get("candidate_brief") or {}
    stress = (brief.get("stress_test") or {})
    soften_list = stress.get("claims_to_soften_or_remove") or []
    unsupported = [s for s in soften_list
                   if "remove" in (s.get("suggested_action") or "").lower()]
    softened = [s for s in soften_list
                if any(k in (s.get("suggested_action") or "").lower()
                       for k in ("soften", "study", "move to interview"))]

    apply_rec, reason = derive_apply_recommendation(
        analyzed=analyzed, packet=packet, qa=qa,
    )

    role_cat = classify_role_category(analyzed)
    portal_complexity = classify_portal_complexity(analyzed.get("source_url"))

    resume_pdf = run_dir / "employer_packet" / "tailored_resume.pdf"
    pages = pdf_page_count(resume_pdf) if resume_pdf.exists() else 0
    ats_safe = "ok" if pages == 1 else ("multi_page" if pages > 1 else "missing")

    polish = qa.get("overall_polish") or "unknown"
    cover_letter_quality = {
        "ready": "good", "needs_work": "fair", "weak": "weak",
    }.get(polish, "unknown")

    high_recs = sum(1 for t in (stress.get("stress_tests") or [])
                    if t.get("recommendation") in ("soften", "remove",
                                                   "study_before_sending"))
    outreach_risk = ("low" if high_recs <= 1
                     else "medium" if high_recs <= 4
                     else "high")

    final_status: str
    if packet.get("blocked"):
        final_status = "needs_patch"
    elif apply_rec == "skip":
        final_status = "skip"
    elif apply_rec == "maybe":
        final_status = "needs_patch"
    else:
        final_status = "portal_ready"

    pain_points = (packet.get("jd_analysis") or {}).get("pain_points") or []
    missing_ev = (packet.get("jd_analysis") or {}).get("missing_evidence") or []
    top_match_reasons = []
    for em in (packet.get("jd_analysis") or {}).get("evidence_map") or []:
        ev = em.get("candidate_evidence") or []
        strong = [e for e in ev if e.get("match_strength") == "strong"]
        if strong:
            idx = em.get("pain_point_index", 0)
            if idx < len(pain_points):
                top_match_reasons.append(pain_points[idx].get("text", "")[:120])
    top_gaps = [m.get("note", "")[:120] for m in missing_ev[:5]]

    return {
        "company": analyzed.get("company") or "",
        "role_title": analyzed.get("title") or "",
        "source_url": analyzed.get("source_url") or "",
        "source_confidence": analyzed.get("source_confidence") or "medium",
        "source_confidence_reason": analyzed.get("source_confidence_reason") or "",
        "role_category": role_cat,
        "fit_score": analyzed.get("fit_score") or 0,
        "fit_breakdown": analyzed.get("fit_breakdown") or {},
        "industry_filter": analyzed.get("industry_filter") or "ok",
        "apply_recommendation": apply_rec,
        "apply_reason": reason,
        "top_match_reasons": top_match_reasons[:4],
        "top_gaps": top_gaps,
        "unsupported_claims_count": len(unsupported),
        "softened_claims_count": len(softened),
        "fabrication_blocks_count": len(
            (packet.get("validation") or {}).get("fabrication_blocks") or []
        ),
        "qa_high_count": sum(1 for i in (qa.get("issues") or [])
                             if i.get("severity") == "high"),
        "qa_medium_count": sum(1 for i in (qa.get("issues") or [])
                               if i.get("severity") == "medium"),
        "qa_low_count": sum(1 for i in (qa.get("issues") or [])
                            if i.get("severity") == "low"),
        "resume_page_count": pages,
        "ats_safety_status": ats_safe,
        "cover_letter_quality": cover_letter_quality,
        "qa_polish": polish,
        "outreach_risk": outreach_risk,
        "portal_complexity": portal_complexity,
        "manual_review_required_fields": HUMAN_REVIEW_REQUIRED,
        "never_auto_answer_fields": NEVER_AUTO_ANSWER,
        "estimated_user_review_time_minutes": estimate_review_time_minutes(
            packet=packet, qa=qa, portal_complexity=portal_complexity,
        ),
        "final_status": final_status,
        "run_id": packet.get("run_id"),
        "slug": slug,
    }


def export_run_layout(slug: str, run_date: str) -> Path:
    """Copy the existing outputs/<slug>/ packet into runs/<slug>_<date>/ with
    employer_packet/, copy_paste/, internal/ split."""
    src_employer = state.OUTPUTS_DIR / slug / "employer"
    src_internal = state.OUTPUTS_DIR / slug / "internal"
    src_packet_json = state.OUTPUTS_DIR / slug / "packet.json"

    dest = RUNS_DIR / f"{slug}_{run_date}"
    employer = dest / "employer_packet"
    copy_paste = dest / "copy_paste"
    internal = dest / "internal"
    for d in (employer, copy_paste, internal):
        d.mkdir(parents=True, exist_ok=True)

    # employer_packet: just the polished PDFs/DOCXs
    for fname in ("tailored_resume.pdf", "cover_letter.pdf",
                  "tailored_resume.docx", "cover_letter.docx"):
        src = src_employer / fname
        if src.exists():
            shutil.copy2(src, employer / fname)

    # copy_paste: markdown bodies for portal Q/A and outreach
    for fname in ("application_answers.md", "outreach_recruiter.md",
                  "outreach_hiring_manager.md", "linkedin_dm.md"):
        src = src_internal / fname
        if src.exists():
            shutil.copy2(src, copy_paste / fname)

    # internal-only files for review (NOT for employer)
    for fname in ("candidate_brief.md", "match_report.md", "qa_report.md",
                  "evidence_map.json"):
        src = src_internal / fname
        if src.exists():
            shutil.copy2(src, internal / fname)
    if src_packet_json.exists():
        shutil.copy2(src_packet_json, internal / "packet.json")

    return dest


def write_job_posting_snapshot(*, run_dir: Path, analyzed: dict[str, Any],
                               raw_text: str) -> None:
    """Write a snapshot of the JD that was used to tailor (so we have a record
    even if the source URL changes or 404s later)."""
    md = run_dir / "internal" / "job_posting_snapshot.md"
    lines = [
        f"# {analyzed.get('company') or '?'} — {analyzed.get('title') or '?'}",
        "",
        f"- Source URL: {analyzed.get('source_url') or '(local)'}",
        f"- Source confidence: {analyzed.get('source_confidence') or '?'}",
        f"- Fetched: {analyzed.get('fetched_at') or '?'}",
        f"- Job id: {analyzed.get('id') or '?'}",
        f"- Industry tags: {', '.join(analyzed.get('industry_tags') or [])}",
        "",
        "## Required skills",
        *[f"- {s}" for s in (analyzed.get("required_skills") or [])],
        "",
        "## Preferred skills",
        *[f"- {s}" for s in (analyzed.get("preferred_skills") or [])],
        "",
        "## Responsibilities",
        *[f"- {s}" for s in (analyzed.get("responsibilities") or [])],
        "",
        "## Raw posting text (snapshot)",
        "",
        "```",
        raw_text.strip(),
        "```",
    ]
    md.write_text("\n".join(lines))
