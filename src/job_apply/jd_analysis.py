"""Stage 1 of the multi-pass pipeline: extract employer pain points + map to candidate evidence.

This pre-pass is shared across all downstream artifacts (resume bullets, cover
letter, application answers, three outreach variants). It surfaces pain points
in the JD's own language and honestly grades the candidate's evidence as
strong / adjacent / weak / missing — so downstream writing can lead with strong
matches and quietly skip pain points without supporting evidence.
"""
from __future__ import annotations

import json
from importlib.resources import files
from typing import Any

from .llm_client import LLMClient
from .profile_loader import Profile

PROMPT_VERSION = "extract_jd_analysis@v1"


def _prompt() -> str:
    return files("job_apply.prompts").joinpath("extract_jd_analysis.txt").read_text()


def analyze_jd(
    *,
    profile: Profile,
    analyzed: dict[str, Any],
    job_text: str,
    llm: LLMClient | None = None,
) -> dict[str, Any]:
    client = llm or LLMClient()
    user_prompt = (
        "PROFILE (the only source of evidence):\n"
        + json.dumps(profile.data, indent=2, default=str)
        + "\n\nJOB POSTING (extracted fields):\n"
        + json.dumps(
            {k: analyzed.get(k) for k in (
                "company", "title", "location", "remote_mode",
                "required_skills", "preferred_skills", "responsibilities",
                "required_certifications", "min_years_experience",
            )},
            indent=2,
        )
        + "\n\nFULL POSTING TEXT (use to extract verbatim jd_anchor strings):\n"
        + job_text
    )
    resp = client.complete(
        tier="extract",
        system=_prompt(),
        user=user_prompt,
        json_mode=True,
        temperature=0.1,
    )
    obj = resp.as_json()
    if not isinstance(obj, dict):
        raise RuntimeError(f"jd_analysis returned non-object: {type(obj).__name__}")
    out: dict[str, Any] = {
        "pain_points": list(obj.get("pain_points") or []),
        "evidence_map": list(obj.get("evidence_map") or []),
        "missing_evidence": list(obj.get("missing_evidence") or []),
        "prompt_version": PROMPT_VERSION,
        "model": resp.model,
    }
    return out


def render_for_prompt(jd: dict[str, Any]) -> str:
    """Compact text view of the JD analysis to embed in downstream user prompts."""
    if not jd or not jd.get("pain_points"):
        return ""
    lines: list[str] = ["JD_ANALYSIS:"]
    for i, pp in enumerate(jd.get("pain_points") or []):
        anchor = pp.get("jd_anchor") or ""
        lines.append(f"  [{i}] {pp.get('text', '')}")
        if anchor:
            lines.append(f"      jd_anchor: \"{anchor}\"")
        if pp.get("stakes"):
            lines.append(f"      stakes: {pp['stakes']}")
        # Evidence for this pain point
        evidence_for = next(
            (em for em in jd.get("evidence_map") or []
             if em.get("pain_point_index") == i),
            None,
        )
        if evidence_for and evidence_for.get("candidate_evidence"):
            for ev in evidence_for["candidate_evidence"]:
                lines.append(
                    f"      evidence ({ev.get('match_strength', '?')}): "
                    f"{ev.get('source_id', '?')} — {ev.get('summary', '')}"
                )
        else:
            lines.append("      evidence: (none mapped — DO NOT claim this pain point)")
    miss = jd.get("missing_evidence") or []
    if miss:
        lines.append("\n  Pain points to leave OUT (no supporting evidence):")
        for m in miss:
            idx = m.get("pain_point_index", "?")
            note = m.get("note", "")
            lines.append(f"    - pain_point[{idx}]: {note}")
    return "\n".join(lines)
