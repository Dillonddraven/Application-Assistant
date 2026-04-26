"""Tailor a resume + cover-letter content for one analyzed job."""
from __future__ import annotations

import json
from importlib.resources import files
from typing import Any

from . import state
from .llm_client import LLMClient
from .profile_loader import Profile

PROMPT_VERSION = "tailor_resume@v1"


def _prompt() -> str:
    return files("job_apply.prompts").joinpath("tailor_resume.txt").read_text()


def tailor(
    *,
    profile: Profile,
    analyzed: dict[str, Any],
    job_text: str,
    llm: LLMClient | None = None,
    deep: bool = False,
) -> tuple[dict[str, Any], str]:
    """Returns (tailored_dict, model_used)."""
    client = llm or LLMClient()
    user = (
        "PROFILE (the only source of truth — do not introduce facts beyond this):\n"
        + json.dumps(profile.data, indent=2, default=str)
        + "\n\nJOB POSTING (target):\n"
        + json.dumps(
            {k: analyzed.get(k) for k in (
                "company", "title", "location", "remote_mode",
                "required_skills", "preferred_skills", "responsibilities",
                "required_certifications", "min_years_experience",
            )},
            indent=2,
        )
        + "\n\nFULL POSTING TEXT (for context only):\n"
        + job_text
    )
    resp = client.complete(
        tier="deep" if deep else "tailor",
        system=_prompt(),
        user=user,
        json_mode=True,
        temperature=0.5,
    )
    obj = resp.as_json()
    if not isinstance(obj, dict):
        raise RuntimeError(f"tailor LLM returned non-object: {type(obj).__name__}")

    # Normalize shape: ensure required keys exist with correct list/dict types.
    tailored: dict[str, Any] = {
        "summary": str(obj.get("summary") or ""),
        "skills_emphasis": list(obj.get("skills_emphasis") or []),
        "bullets": [b for b in (obj.get("bullets") or []) if isinstance(b, dict)],
        "cover_letter_paragraphs": [p for p in (obj.get("cover_letter_paragraphs") or []) if isinstance(p, dict)],
        "application_answers": [a for a in (obj.get("application_answers") or []) if isinstance(a, dict)],
    }
    return tailored, resp.model
