"""Generate an internal candidate-facing interview prep brief.

This is for the candidate (Dillon), not the employer. It includes role context,
top talking points, claims to be ready to explain, honest weak-spot answers,
30/60-second pitches, and questions for the recruiter/hiring manager.

Saved to `internal/candidate_brief.md` on every packet.
"""
from __future__ import annotations

import json
from importlib.resources import files
from typing import Any

from .llm_client import LLMClient
from .profile_loader import Profile

PROMPT_VERSION = "candidate_brief@v1"


def _prompt() -> str:
    return files("job_apply.prompts").joinpath("candidate_brief.txt").read_text()


def generate_brief(
    *,
    profile: Profile,
    analyzed: dict[str, Any],
    tailored: dict[str, Any],
    jd_analysis: dict[str, Any] | None = None,
    qa: dict[str, Any] | None = None,
    llm: LLMClient | None = None,
) -> dict[str, Any]:
    client = llm or LLMClient()
    parts = [
        "PROFILE:",
        json.dumps(profile.data, indent=2, default=str),
        "",
        "ANALYZED JOB:",
        json.dumps(
            {k: analyzed.get(k) for k in (
                "company", "title", "location", "remote_mode",
                "required_skills", "preferred_skills", "responsibilities",
                "required_certifications", "min_years_experience",
                "industry_tags", "fit_score", "fit_breakdown", "fit_rationale",
                "concerns", "missing_quals", "source_url", "source_confidence",
            )},
            indent=2,
        ),
        "",
        "TAILORED PACKET CONTENT (what's in the resume / cover letter / answers):",
        json.dumps({
            "summary": tailored.get("summary"),
            "skills_emphasis": tailored.get("skills_emphasis"),
            "bullets": tailored.get("bullets"),
            "cover_letter_paragraphs": tailored.get("cover_letter_paragraphs"),
            "application_answers": tailored.get("application_answers"),
        }, indent=2),
    ]
    if jd_analysis:
        from .jd_analysis import render_for_prompt
        rendered = render_for_prompt(jd_analysis)
        if rendered:
            parts += ["", rendered]
    if qa and qa.get("issues"):
        parts += [
            "",
            "QA RESULT (issues found by the QA pass):",
            json.dumps(qa, indent=2),
        ]
    user = "\n".join(parts)

    resp = client.complete(
        tier="deep",       # this is the artifact Dillon studies before interviews — quality matters
        system=_prompt(),
        user=user,
        json_mode=True,
        temperature=0.4,
    )
    obj = resp.as_json()
    if not isinstance(obj, dict):
        raise RuntimeError(f"candidate_brief returned non-object: {type(obj).__name__}")
    obj["prompt_version"] = PROMPT_VERSION
    obj["model"] = resp.model
    return obj


def render_brief_md(brief: dict[str, Any]) -> str:
    """Render the structured brief as a clean Markdown file for internal/candidate_brief.md."""
    lines: list[str] = ["# Candidate brief (internal, for you, not the employer)", ""]

    if brief.get("role_company_summary"):
        lines.append("## Role + company summary")
        lines.append("")
        lines.append(brief["role_company_summary"])
        lines.append("")

    if brief.get("why_this_role_fits"):
        lines.append("## Why this role fits")
        lines.append("")
        lines.append(brief["why_this_role_fits"])
        lines.append("")

    if brief.get("top_three_talking_points"):
        lines.append("## Top 3 talking points")
        lines.append("")
        for tp in brief["top_three_talking_points"]:
            lines.append(f"- {tp}")
        lines.append("")

    if brief.get("resume_emphasis"):
        lines.append("## What the resume is emphasizing")
        lines.append("")
        lines.append(brief["resume_emphasis"])
        lines.append("")

    if brief.get("cover_letter_emphasis"):
        lines.append("## What the cover letter is emphasizing")
        lines.append("")
        lines.append(brief["cover_letter_emphasis"])
        lines.append("")

    if brief.get("claims_to_be_ready_to_explain"):
        lines.append("## Claims to be ready to explain")
        lines.append("")
        for c in brief["claims_to_be_ready_to_explain"]:
            if isinstance(c, dict):
                lines.append(f"- **{c.get('claim', '')}** ({c.get('where', '')})")
                if c.get("supporting_detail"):
                    lines.append(f"  - {c['supporting_detail']}")
        lines.append("")

    if brief.get("weak_spots_or_gaps"):
        lines.append("## Weak spots / gaps + honest answers")
        lines.append("")
        for w in brief["weak_spots_or_gaps"]:
            if isinstance(w, dict):
                lines.append(f"- **{w.get('gap', '')}**")
                if w.get("honest_answer"):
                    lines.append(f"  - Honest answer: {w['honest_answer']}")
        lines.append("")

    if brief.get("thirty_second_interest_answer"):
        lines.append("## 30-second \"why are you interested\" answer")
        lines.append("")
        lines.append(brief["thirty_second_interest_answer"])
        lines.append("")

    if brief.get("sixty_second_background_walkthrough"):
        lines.append("## 60-second \"walk me through your background\" answer")
        lines.append("")
        lines.append(brief["sixty_second_background_walkthrough"])
        lines.append("")

    if brief.get("questions_to_ask"):
        lines.append("## Questions to ask the recruiter / hiring manager")
        lines.append("")
        for q in brief["questions_to_ask"]:
            lines.append(f"- {q}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
