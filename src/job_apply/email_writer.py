"""Generate three outreach email variants for one analyzed job."""
from __future__ import annotations

import json
from importlib.resources import files
from typing import Any

from .llm_client import LLMClient
from .profile_loader import Profile

PROMPT_VERSIONS = {
    "recruiter": "write_email_recruiter@v1",
    "hiring_manager": "write_email_hiring_manager@v1",
    "linkedin_dm": "write_linkedin_dm@v1",
}


def _prompt(name: str) -> str:
    return files("job_apply.prompts").joinpath(f"{name}.txt").read_text()


def _user_prompt(profile: Profile, analyzed: dict[str, Any]) -> str:
    return (
        "PROFILE (the only source of truth):\n"
        + json.dumps(profile.data, indent=2, default=str)
        + "\n\nJOB POSTING:\n"
        + json.dumps(
            {k: analyzed.get(k) for k in (
                "company", "title", "location", "remote_mode",
                "required_skills", "preferred_skills", "responsibilities",
            )},
            indent=2,
        )
    )


def _generate(name: str, profile: Profile, analyzed: dict[str, Any], llm: LLMClient) -> dict[str, Any]:
    resp = llm.complete(
        tier="tailor",
        system=_prompt(name),
        user=_user_prompt(profile, analyzed),
        json_mode=True,
        temperature=0.6,
    )
    obj = resp.as_json()
    if not isinstance(obj, dict):
        raise RuntimeError(f"email_writer ({name}) returned non-object: {type(obj).__name__}")
    obj.setdefault("_model", resp.model)
    return obj


def write_all(
    *, profile: Profile, analyzed: dict[str, Any], llm: LLMClient | None = None,
) -> dict[str, dict[str, Any]]:
    client = llm or LLMClient()
    return {
        "recruiter": _generate("write_email_recruiter", profile, analyzed, client),
        "hiring_manager": _generate("write_email_hiring_manager", profile, analyzed, client),
        "linkedin_dm": _generate("write_linkedin_dm", profile, analyzed, client),
    }
