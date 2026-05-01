#!/usr/bin/env python3
"""Benchmark orchestration. Runs the full pipeline against the 10 test roles,
exports each into runs/<slug>_<date>/, generates per-role scorecards, and
writes batch_summary.md at the end. Designed to keep going on individual
failures (URL down, JS-rendered, etc.) so the batch yields a useful summary."""
from __future__ import annotations

import json
import sys
import time
import traceback
from datetime import date
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from job_apply import (bench, candidate_brief, jd_analysis, job_analyzer,
                       qa_pass, render, render_docx, render_pdf, resume_tailor,
                       email_writer, state)
from job_apply.config import OUTPUTS_DIR, ROOT
from job_apply.llm_client import LLMClient
from job_apply.profile_loader import load_profile, load_secrets

ROLES = [
    {"id": 1, "company": "Pacific Legal Foundation", "role": "Data Security Analyst",
     "url": "https://job-boards.greenhouse.io/pacificlegalfoundation/jobs/4183667009",
     "purpose": "IT/security hybrid"},
    {"id": 2, "company": "UltraViolet Cyber", "role": "Associate SOC Analyst",
     "url": "https://jobs.lever.co/uvcyber/fd6bd8a9-4b79-4793-bd1d-db080bed7e5b",
     "purpose": "SOC analyst"},
    {"id": 3, "company": "LVT", "role": "Information Security Analyst, GRC",
     "url": "https://job-boards.greenhouse.io/liveviewtechnologiesinc/jobs/5192885008",
     "purpose": "GRC"},
    {"id": 4, "company": "Xpansiv", "role": "Information Security Analyst",
     "url": "https://jobs.lever.co/Xpansiv%20/6652760b-5fda-44dc-a3e6-2d853886bdf8",
     "purpose": "stretch InfoSec"},
    {"id": 5, "company": "Machinify",
     "role": "Security Engineer, Threat & Vulnerability Management",
     "url": "https://job-boards.greenhouse.io/machinifyinc/jobs/4231303009",
     "purpose": "stretch/reject test"},
    {"id": 6, "company": "Core One", "role": "Security Analyst",
     "url": "https://job-boards.greenhouse.io/coreone/jobs/8483213002",
     "purpose": "federal/RMF/GRC stretch"},
    {"id": 7, "company": "SailPoint", "role": "Vulnerability Management Analyst",
     "url": "https://sailpoint.wd1.myworkdayjobs.com/en-US/SailPoint/job/Vulnerability-Management-Analyst_R013230",
     "purpose": "vulnerability management"},
    {"id": 8, "company": "PurpleBox", "role": "Cybersecurity Analyst",
     "url": "https://jobs.smartrecruiters.com/PurpleBoxInc/743999936212683-cybersecurity-analyst",
     "purpose": "broad cybersec analyst"},
    {"id": 9, "company": "Bloomreach", "role": "Security Analyst",
     "url": "https://job-boards.greenhouse.io/bloomreach/jobs/4902749",
     "purpose": "general security analyst"},
    {"id": 10, "company": "Advanced Space", "role": "Information Security Analyst",
     "url": "https://job-boards.greenhouse.io/advancedspace/jobs/4194400009",
     "purpose": "technical stretch"},
]


def log(msg: str) -> None:
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def run_one(role: dict, profile, secrets, client: LLMClient,
            run_date: str) -> dict:
    """Returns scorecard dict (or a failure stub)."""
    role_id = role["id"]
    label = f"#{role_id} {role['company']} — {role['role']}"
    log(f"=== START {label} ===")
    log(f"  url: {role['url']}")

    # --- Stage 1: ingest ---
    job_id, err = bench.robust_ingest(role["url"], refresh=True)
    if not job_id:
        log(f"  INGEST FAILED: {err}")
        return {
            "id": role_id,
            "company": role["company"],
            "role_title": role["role"],
            "source_url": role["url"],
            "final_status": "skip",
            "apply_recommendation": "skip",
            "apply_reason": f"ingest failed: {err[:200] if err else 'unknown'}",
            "fit_score": 0,
            "source_confidence": "unknown",
            "_error": err,
        }
    rec = state.load_ingest(job_id)
    log(f"  ingest ok: {len(rec.text)} chars")

    # --- Stage 2: analyze ---
    try:
        analyzed = job_analyzer.analyze_job(
            job_id=job_id, profile=profile, text=rec.text,
            source_url=rec.source_url, fetched_at=rec.fetched_at,
            raw_text_path=str(rec.raw_text_path), llm=client,
        )
        state.save_analyzed(job_id, analyzed)
        log(f"  analyze ok: {analyzed.get('company')} — "
            f"{analyzed.get('title')} | fit={analyzed.get('fit_score')} "
            f"src_conf={analyzed.get('source_confidence')} "
            f"industry={analyzed.get('industry_filter')}")
    except Exception as e:
        log(f"  ANALYZE FAILED: {e}")
        return {
            "id": role_id,
            "company": role["company"],
            "role_title": role["role"],
            "source_url": role["url"],
            "final_status": "skip",
            "apply_recommendation": "skip",
            "apply_reason": f"analyze failed: {str(e)[:200]}",
            "fit_score": 0,
            "_error": str(e),
        }

    # --- Stage 3: tailor (full pipeline including JD analysis, QA, brief, stress test) ---
    try:
        from job_apply import tailor_pipeline
        # Force industry override flag for benchmark — we want to see what the
        # pipeline produces even on flagged jobs (will surface in scorecard).
        force = (analyzed.get("industry_filter") == "avoid")
        packet, slug = tailor_pipeline.run_tailor(
            job_id=job_id, force=force, llm=client, open_mail=False,
        )
        log(f"  tailor ok: slug={slug} blocked={packet.get('blocked')} "
            f"qa_polish={(packet.get('validation') or {}).get('qa', {}).get('overall_polish')}")
    except Exception as e:
        log(f"  TAILOR FAILED: {e}")
        traceback.print_exc()
        return {
            "id": role_id,
            "company": role["company"],
            "role_title": role["role"],
            "source_url": role["url"],
            "final_status": "skip",
            "apply_recommendation": "skip",
            "apply_reason": f"tailor failed: {str(e)[:200]}",
            "fit_score": analyzed.get("fit_score", 0),
            "source_confidence": analyzed.get("source_confidence", "unknown"),
            "_error": str(e),
        }

    # --- Stage 4: export to runs/<slug>_<date>/ ---
    run_dir = bench.export_run_layout(slug, run_date)
    bench.write_job_posting_snapshot(
        run_dir=run_dir, analyzed=analyzed, raw_text=rec.text,
    )

    # --- Stage 5: scorecard ---
    scorecard = bench.build_scorecard(
        slug=slug, run_dir=run_dir, analyzed=analyzed, packet=packet,
    )
    scorecard["id"] = role_id
    (run_dir / "internal" / "pipeline_scorecard.json").write_text(
        json.dumps(scorecard, indent=2)
    )
    log(f"  scorecard: status={scorecard['final_status']} "
        f"rec={scorecard['apply_recommendation']} "
        f"reason={scorecard['apply_reason']}")
    log(f"=== END {label} ===\n")
    return scorecard


def main() -> int:
    profile = load_profile()
    secrets = load_secrets()
    client = LLMClient()
    run_date = date.today().isoformat()
    log(f"benchmark start, run_date={run_date}, roles={len(ROLES)}")

    scorecards: list[dict] = []
    for role in ROLES:
        try:
            sc = run_one(role, profile, secrets, client, run_date)
        except Exception as e:
            log(f"FATAL on role #{role['id']}: {e}")
            traceback.print_exc()
            sc = {
                "id": role["id"], "company": role["company"],
                "role_title": role["role"], "source_url": role["url"],
                "final_status": "skip", "apply_recommendation": "skip",
                "apply_reason": f"unexpected error: {str(e)[:200]}",
                "_error": str(e),
            }
        scorecards.append(sc)

    # Persist the aggregated scorecards
    summary_dir = bench.RUNS_DIR / f"_batch_{run_date}"
    summary_dir.mkdir(parents=True, exist_ok=True)
    (summary_dir / "scorecards.json").write_text(
        json.dumps(scorecards, indent=2)
    )
    log(f"all 10 scorecards written: {summary_dir / 'scorecards.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
