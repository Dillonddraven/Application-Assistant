"""Stage 3 of the multi-pass pipeline: LLM-driven QA pass on a generated packet.

Returns a structured list of issues (category, severity, where, snippet,
fix_suggestion) plus an overall polish grade. The pass runs ON the rendered
text views (resume, cover letter, application answers, three outreach
variants), with the JD_ANALYSIS as context so the LLM can flag evidence_gap
violations.
"""
from __future__ import annotations

import json
from importlib.resources import files
from typing import Any

from .llm_client import LLMClient

PROMPT_VERSION = "qa_check@v1"


def _prompt() -> str:
    return files("job_apply.prompts").joinpath("qa_check.txt").read_text()


def qa_check(
    *,
    rendered_views: dict[str, str],
    jd_analysis: dict[str, Any] | None,
    llm: LLMClient | None = None,
) -> dict[str, Any]:
    """Run a QA pass on the rendered packet views.

    `rendered_views` is a dict mapping a label (e.g. "tailored_resume",
    "cover_letter", "application_answers", "outreach_recruiter",
    "outreach_hiring_manager", "linkedin_dm") to the text the user will
    actually read or send.
    """
    client = llm or LLMClient()

    user_lines: list[str] = []
    if jd_analysis:
        from .jd_analysis import render_for_prompt
        rendered_jd = render_for_prompt(jd_analysis)
        if rendered_jd:
            user_lines.append(rendered_jd)
            user_lines.append("")
    for label, text in rendered_views.items():
        user_lines.append(f"=== {label} ===")
        user_lines.append(text.strip() if isinstance(text, str) else "")
        user_lines.append("")

    user_prompt = "\n".join(user_lines)

    resp = client.complete(
        tier="tailor",
        system=_prompt(),
        user=user_prompt,
        json_mode=True,
        temperature=0.2,
    )
    obj = resp.as_json()
    if not isinstance(obj, dict):
        raise RuntimeError(f"qa_check returned non-object: {type(obj).__name__}")
    return {
        "issues": [i for i in (obj.get("issues") or []) if isinstance(i, dict)],
        "overall_polish": str(obj.get("overall_polish") or "ready"),
        "prompt_version": PROMPT_VERSION,
        "model": resp.model,
    }


def render_qa_summary(qa: dict[str, Any]) -> str:
    if not qa or not qa.get("issues"):
        polish = qa.get("overall_polish", "ready") if qa else "ready"
        return f"QA: {polish} — no issues flagged."
    lines: list[str] = [f"QA polish: **{qa.get('overall_polish')}**"]
    by_sev = {"high": [], "medium": [], "low": []}
    for issue in qa.get("issues", []):
        sev = issue.get("severity", "low")
        if sev in by_sev:
            by_sev[sev].append(issue)
    for sev in ("high", "medium", "low"):
        items = by_sev.get(sev) or []
        if not items:
            continue
        lines.append(f"\n{sev.upper()} ({len(items)}):")
        for issue in items:
            lines.append(f"  - [{issue.get('category')}] {issue.get('where', '')}")
            snippet = (issue.get("snippet") or "").strip()
            if snippet:
                lines.append(f"      \"{snippet}\"")
            fix = issue.get("fix_suggestion") or ""
            if fix:
                lines.append(f"      fix: {fix}")
    return "\n".join(lines)
