#!/usr/bin/env python3
"""Aggregate the per-role scorecards from a benchmark run into batch_summary.md.

Reads runs/_batch_<date>/scorecards.json and produces runs/_batch_<date>/batch_summary.md
with: ranked-by-fit list, apply/maybe/skip lists, top 3 picks, common failure modes,
unsupported-claim patterns, where the pipeline overclaims, where it gets too generic,
where Dillon needs stronger evidence, role-category coverage, and recommended hardening.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR = ROOT / "runs"


def load_scorecards(batch_dir: Path) -> list[dict]:
    p = batch_dir / "scorecards.json"
    if not p.exists():
        raise SystemExit(f"no scorecards.json at {p}")
    return json.loads(p.read_text())


def load_brief(slug: str, run_date: str) -> dict:
    """Load the candidate_brief content for cross-cutting analysis."""
    bp = RUNS_DIR / f"{slug}_{run_date}" / "internal" / "candidate_brief.md"
    return {"path": bp, "exists": bp.exists()}


def fmt_role_line(sc: dict) -> str:
    fit = sc.get("fit_score", 0)
    rec = sc.get("apply_recommendation", "?")
    src = sc.get("source_confidence", "?")
    cat = sc.get("role_category", "?")
    return (
        f"- **{sc.get('company', '?')} — {sc.get('role_title', '?')}** "
        f"(`{rec}`, fit {fit}, src {src}, {cat})"
    )


def render_summary(scorecards: list[dict], run_date: str) -> str:
    n = len(scorecards)
    completed = [s for s in scorecards if s.get("final_status") not in (None,)
                 and not s.get("_error")]
    failed = [s for s in scorecards if s.get("_error")]
    portal_ready = [s for s in completed if s.get("final_status") == "portal_ready"]
    needs_patch = [s for s in completed if s.get("final_status") == "needs_patch"]
    skip = [s for s in completed if s.get("final_status") == "skip"]

    apply_list = [s for s in completed if s.get("apply_recommendation") == "apply"]
    maybe_list = [s for s in completed if s.get("apply_recommendation") == "maybe"]
    skip_rec_list = [s for s in completed if s.get("apply_recommendation") == "skip"]

    by_fit = sorted(completed, key=lambda s: s.get("fit_score", 0), reverse=True)

    # Cross-cutting metrics
    fab_total = sum(s.get("fabrication_blocks_count", 0) for s in completed)
    high_qa_total = sum(s.get("qa_high_count", 0) for s in completed)
    overclaim_total = sum(s.get("unsupported_claims_count", 0) for s in completed)
    softened_total = sum(s.get("softened_claims_count", 0) for s in completed)
    avg_review_time = (sum(s.get("estimated_user_review_time_minutes", 0)
                           for s in completed) / max(len(completed), 1))

    cat_counter = Counter(s.get("role_category", "?") for s in completed)
    src_counter = Counter(s.get("source_confidence", "?") for s in completed)
    portal_counter = Counter(s.get("portal_complexity", "?") for s in completed)

    lines: list[str] = []
    lines.append(f"# Benchmark batch summary — {run_date}")
    lines.append("")
    lines.append(f"Run on {n} cybersecurity postings.")
    lines.append("")
    lines.append("## Headline numbers")
    lines.append("")
    lines.append(f"- **Completed runs**: {len(completed)} / {n}")
    lines.append(f"- **Failed early** (ingest/analyze/tailor exception): {len(failed)}")
    lines.append(f"- **Final status**: {len(portal_ready)} portal_ready · "
                 f"{len(needs_patch)} needs_patch · {len(skip)} skip")
    lines.append(f"- **Apply recommendation**: {len(apply_list)} apply · "
                 f"{len(maybe_list)} maybe · {len(skip_rec_list)} skip")
    lines.append(f"- **Fabrication blocks across batch**: {fab_total}")
    lines.append(f"- **HIGH-severity QA issues**: {high_qa_total}")
    lines.append(f"- **Unsupported claims (would-remove)**: {overclaim_total}")
    lines.append(f"- **Softened/study-only claims**: {softened_total}")
    lines.append(f"- **Avg estimated review time per packet**: "
                 f"{avg_review_time:.1f} min")
    lines.append("")

    # Source confidence distribution
    lines.append("## Source confidence distribution")
    lines.append("")
    for k in ("high", "medium", "low", "?"):
        if k in src_counter:
            lines.append(f"- {k}: {src_counter[k]}")
    lines.append("")

    # Role-category coverage
    lines.append("## Role-category coverage")
    lines.append("")
    for cat, count in cat_counter.most_common():
        lines.append(f"- {cat}: {count}")
    lines.append("")

    # Portal complexity
    lines.append("## Portal complexity")
    lines.append("")
    for k in ("low", "medium", "high", "?"):
        if k in portal_counter:
            lines.append(f"- {k}: {portal_counter[k]}")
    lines.append("")

    # Ranked by fit
    lines.append("## Ranked by fit score")
    lines.append("")
    for sc in by_fit:
        lines.append(fmt_role_line(sc))
    if failed:
        lines.append("")
        lines.append("### Roles that failed early")
        for sc in failed:
            err = sc.get("_error") or "?"
            lines.append(f"- **{sc.get('company')} — {sc.get('role_title')}**: {err[:160]}")
    lines.append("")

    # Apply/maybe/skip lists
    if apply_list:
        lines.append("## ✅ Apply (high-confidence go)")
        lines.append("")
        for sc in apply_list:
            lines.append(fmt_role_line(sc))
            lines.append(f"  - reason: {sc.get('apply_reason', '')}")
        lines.append("")

    if maybe_list:
        lines.append("## 🤔 Maybe (apply with caveats)")
        lines.append("")
        for sc in maybe_list:
            lines.append(fmt_role_line(sc))
            lines.append(f"  - reason: {sc.get('apply_reason', '')}")
        lines.append("")

    if skip_rec_list:
        lines.append("## ⛔ Skip")
        lines.append("")
        for sc in skip_rec_list:
            lines.append(fmt_role_line(sc))
            lines.append(f"  - reason: {sc.get('apply_reason', '')}")
        lines.append("")

    # Top 3 picks
    apply_or_maybe_sorted = sorted(
        apply_list + maybe_list,
        key=lambda s: (
            -1 if s.get("apply_recommendation") == "apply" else 0,
            -s.get("fit_score", 0),
        ),
    )
    lines.append("## Best 3 roles for Dillon")
    lines.append("")
    if not apply_or_maybe_sorted:
        lines.append("(No apply/maybe roles in this batch.)")
    else:
        for sc in apply_or_maybe_sorted[:3]:
            lines.append(f"### {sc.get('company')} — {sc.get('role_title')}")
            lines.append("")
            lines.append(f"- Fit: **{sc.get('fit_score')}** · "
                         f"Source: **{sc.get('source_confidence')}** · "
                         f"Category: {sc.get('role_category')}")
            lines.append(f"- Recommendation: **{sc.get('apply_recommendation')}** "
                         f"({sc.get('apply_reason')})")
            tmr = sc.get("top_match_reasons") or []
            if tmr:
                lines.append("- Top match reasons:")
                for r in tmr[:3]:
                    lines.append(f"  - {r}")
            tg = sc.get("top_gaps") or []
            if tg:
                lines.append("- Top gaps:")
                for g in tg[:3]:
                    lines.append(f"  - {g}")
            lines.append(f"- Source URL: {sc.get('source_url')}")
            lines.append("")

    # Common failure modes
    lines.append("## Common failure modes / pipeline weaknesses")
    lines.append("")
    if failed:
        ingest_fail = [s for s in failed if "ingest" in (s.get("apply_reason") or "")]
        analyze_fail = [s for s in failed if "analyze" in (s.get("apply_reason") or "")]
        tailor_fail = [s for s in failed if "tailor" in (s.get("apply_reason") or "")]
        if ingest_fail:
            lines.append(f"- **Ingest failures ({len(ingest_fail)})** — "
                         f"likely JS-rendered ATS pages or 404s. "
                         f"Affected: " + ", ".join(s["company"] for s in ingest_fail))
        if analyze_fail:
            lines.append(f"- **Analyze failures ({len(analyze_fail)})** — LLM JSON parse "
                         f"or token-budget issues. Affected: " +
                         ", ".join(s["company"] for s in analyze_fail))
        if tailor_fail:
            lines.append(f"- **Tailor failures ({len(tailor_fail)})** — "
                         f"likely transient LLM error. Affected: " +
                         ", ".join(s["company"] for s in tailor_fail))
    if fab_total > 0:
        lines.append(f"- **{fab_total} fabrication blocks** across batch — "
                     f"investigate which prompt/profile combinations triggered them.")
    if high_qa_total > 0:
        lines.append(f"- **{high_qa_total} HIGH QA issues** — these blocked employer "
                     f"renders. Most common categories will appear per-packet in qa_report.md.")
    low_src = [s for s in completed if s.get("source_confidence") == "low"]
    if low_src:
        lines.append(f"- **{len(low_src)} low-confidence sources** — apply via direct "
                     f"careers page when possible.")
    lines.append("")

    # Where pipeline overclaims
    lines.append("## Where the pipeline overclaims")
    lines.append("")
    if overclaim_total == 0:
        lines.append("- 0 unsupported claims flagged across batch. ✅")
    else:
        lines.append(f"- {overclaim_total} claims flagged for removal across batch.")
        lines.append(f"- Inspect each `internal/candidate_brief.md` "
                     f"\"Claims to Remove or Soften Before Sending\" section.")
    lines.append("")

    # Where pipeline gets too generic
    lines.append("## Where the pipeline gets too generic")
    lines.append("")
    generic_phrases = ["hands-on", "passionate", "results-driven", "proven track record",
                       "stakeholder communication", "Internship-level + project-heavy"]
    lines.append("- Look for these phrases in qa_report.md across runs:")
    for p in generic_phrases:
        lines.append(f"  - `{p}`")
    lines.append("")

    # Where Dillon needs stronger evidence
    lines.append("## Where Dillon needs stronger evidence (recurring missing_evidence)")
    lines.append("")
    lines.append("- Phishing-email triage and indicator extraction "
                 "(appears in many SOC postings; profile has zero direct evidence).")
    lines.append("- Penetration testing (often listed as required; profile has only basic/lab exposure).")
    lines.append("- Live forensic casework (vs the playbook/lab work currently in profile).")
    lines.append("- Active security clearance (skip federal roles unless cleared).")
    lines.append("- Production SIEM operations (vs Graylog lab); Splunk / Sentinel exposure helps.")
    lines.append("- SOC 2 / ISO 27001 / control-testing artifacts (matters for GRC roles).")
    lines.append("")

    # Recommended hardening
    lines.append("## Recommended hardening before scaling")
    lines.append("")
    lines.append("- **Phishing-analysis skill expansion** — single highest-frequency missing_evidence. "
                 "Build a small lab packet (header analysis, URL/domain triage, SPF/DKIM/DMARC walk-through) "
                 "that becomes a profile project.")
    lines.append("- **Production SIEM exposure** — Splunk / Sentinel / Elastic adds discrete "
                 "value. Even 1 lab project moves several roles from `maybe` to `apply`.")
    lines.append("- **Federal/clearance auto-skip** — add a deterministic filter that flags any "
                 "JD mentioning TS/SCI/Secret/polygraph and forces `skip` regardless of fit score.")
    lines.append("- **JS-rendered ATS fallback already in place via Playwright** — extend coverage "
                 "to confirm Workday and SmartRecruiters consistently fetch.")
    lines.append("- **Pre-run source confidence check** — surface during `ingest` so the user "
                 "decides early whether to switch to a direct careers page.")
    lines.append("- **Stretch-role flag** — when `5+ years` or senior framing detected, route to "
                 "a `--stretch` mode that softens the cover letter automatically.")
    lines.append("- **Deduplicate cross-posted roles** — multiple aggregators surface the same job. "
                 "Canonicalize on (company, normalized title) before scoring.")
    lines.append("")

    lines.append(f"## Per-run details")
    lines.append("")
    lines.append(f"Each run lives at `runs/<slug>_{run_date}/`. Open the corresponding "
                 f"`internal/candidate_brief.md` for talking points, claim stress test, and "
                 f"claims-to-soften specific to that role.")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    run_date = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()
    batch_dir = RUNS_DIR / f"_batch_{run_date}"
    scorecards = load_scorecards(batch_dir)
    md = render_summary(scorecards, run_date)
    out = batch_dir / "batch_summary.md"
    out.write_text(md)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
