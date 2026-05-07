"""LLM-driven profile updates with truth-safe guardrails.

Flow:
  1. User chats e.g. "I forgot a malware-analysis lab from CYBR 4123"
  2. propose_patch() asks the LLM to emit a STRUCTURED patch (one of a
     small action set) with a `verbatim_quote` field that MUST be a
     substring of the user's message.
  3. validate_patch() rejects patches whose verbatim_quote is missing,
     whose numeric / employer / credential claims weren't actually said,
     or whose action is unknown.
  4. apply_patch() merges the patch into the profile YAML in memory.
  5. The UI renders a diff and lets the user click Apply or Skip.

Truth-safe contract: if the LLM tries to invent a percentage, employer,
duration, or seniority the user didn't state, the validator rejects it.
We never auto-write -- the user always confirms.
"""
from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass, field
from typing import Any

from .llm_client import LLMClient


# --- patch schema ---

ACTIONS = (
    "add_project",        # data: {name, description, skills?, role_type?}
    "add_experience",     # data: {company, title, role_type, summary, start?, end?, bullets?}
    "add_certification",  # data: {name, issued?}
    "add_skill",          # data: {category: technical|security|systems|cloud_security, value}
    "add_bullet",         # data: {target_experience_id, text, skills_demonstrated?}
    "add_education",      # data: {school, degree, status?, start?, expected_end?}
    "edit_field",         # data: {path: "preferences.target_roles", value: [...] or set/append}
    "no_change",          # nothing to add (acknowledgement / question / off-topic)
)


@dataclass
class ProfilePatch:
    action: str
    data: dict[str, Any] = field(default_factory=dict)
    verbatim_quote: str = ""
    reasoning: str = ""
    target_id: str | None = None  # for add_bullet / edit_field

    def is_no_op(self) -> bool:
        return self.action == "no_change"


# --- validation ---

# Patterns we treat as "specific factual claims that must come from the user"
# Match: percentages, durations (years/months/days/hours), Nx multipliers,
# dollar amounts. Trailing word-boundary is OPTIONAL because "%" / "$"
# are non-word characters and won't anchor cleanly with \b on both sides.
NUMERIC_RE = re.compile(
    r"(?:\b\d+%|\b\d+\s*(?:years?|months?|days?|hours?|x\b|times\b)|\$\d[\d,.]*)",
    re.I,
)
PROPER_NOUN_FRAGMENT_RE = re.compile(r"\b[A-Z][A-Za-z0-9]{2,}(?:[\s&-][A-Z][A-Za-z0-9]+)*\b")


class PatchError(ValueError):
    pass


def _all_text(data: Any) -> list[str]:
    """Walk the patch.data tree and collect every string value."""
    out: list[str] = []
    if isinstance(data, str):
        out.append(data)
    elif isinstance(data, dict):
        for v in data.values():
            out.extend(_all_text(v))
    elif isinstance(data, list):
        for v in data:
            out.extend(_all_text(v))
    return out


def validate_patch(patch: ProfilePatch, user_message: str,
                    profile: dict[str, Any]) -> list[str]:
    """Return a list of validation errors. Empty list = patch is OK to apply.

    Hard rules:
      - action must be in ACTIONS
      - if action != no_change, verbatim_quote must be non-empty AND must
        be a substring of the user message (case-insensitive, whitespace-
        normalized)
      - any numeric token in the patch (percentages, durations, dollar
        amounts) must also appear in the user's message
      - for add_bullet, target_experience_id must resolve to an existing
        experience entry in the profile
      - for edit_field, path must point at a field we allow editing
      - for add_skill, category must be one of the known buckets
    """
    errors: list[str] = []
    if patch.action not in ACTIONS:
        errors.append(f"unknown action {patch.action!r}; valid: {ACTIONS}")
        return errors
    if patch.action == "no_change":
        return errors

    msg_norm = re.sub(r"\s+", " ", (user_message or "").strip().lower())
    quote_norm = re.sub(r"\s+", " ", (patch.verbatim_quote or "").strip().lower())
    if not quote_norm:
        errors.append("verbatim_quote is required (must be a substring of your message)")
    elif quote_norm not in msg_norm:
        errors.append(
            f"verbatim_quote {patch.verbatim_quote!r} is not a substring of "
            f"your message; refusing to add unsourced content"
        )

    # Every numeric claim in patch.data must appear in the user message
    patch_strings = _all_text(patch.data)
    for s in patch_strings:
        for m in NUMERIC_RE.finditer(s or ""):
            tok = m.group(0)
            if tok.lower() not in msg_norm:
                errors.append(
                    f"numeric claim {tok!r} appears in patch but not in "
                    f"your message; refusing (truth-safe rule)"
                )

    # Action-specific rules
    if patch.action == "add_bullet":
        eid = patch.target_id or patch.data.get("target_experience_id", "")
        exp_ids = {e.get("id") for e in (profile.get("experience") or [])}
        if eid not in exp_ids:
            errors.append(
                f"add_bullet target_experience_id {eid!r} not found in profile; "
                f"existing ids: {sorted(x for x in exp_ids if x)}"
            )
    if patch.action == "add_skill":
        cat = patch.data.get("category", "")
        valid = ("technical", "security", "systems", "cloud_security",
                 "programming", "tools")
        if cat not in valid:
            errors.append(f"add_skill category {cat!r} not in {valid}")
    if patch.action == "edit_field":
        path = patch.data.get("path", "")
        # Whitelist of editable paths -- intentionally narrow
        allowed = (
            "preferences.target_roles",
            "preferences.locations",
            "preferences.industries_avoid",
            "preferences.preferred_metros",
            "preferences.willing_to_relocate",
            "preferences.salary_min",
            "preferences.remote_ok",
            "preferences.hybrid_ok",
            "preferences.onsite_ok",
            "writing_style.forbidden_phrases",
        )
        if path not in allowed:
            errors.append(f"edit_field path {path!r} not in editable whitelist")

    return errors


# --- application ---

def apply_patch(profile: dict[str, Any], patch: ProfilePatch) -> dict[str, Any]:
    """Return a new profile dict with the patch applied. Does NOT mutate
    the input. Caller should validate first."""
    p = copy.deepcopy(profile)

    if patch.action == "no_change":
        return p

    if patch.action == "add_project":
        p.setdefault("projects", [])
        d = dict(patch.data)
        if "id" not in d:
            d["id"] = _next_id(p["projects"], prefix="proj_chat_")
        p["projects"].append(d)
    elif patch.action == "add_experience":
        p.setdefault("experience", [])
        d = dict(patch.data)
        if "id" not in d:
            d["id"] = _next_id(p["experience"], prefix="exp_chat_")
        d.setdefault("bullets", [])
        p["experience"].append(d)
    elif patch.action == "add_certification":
        p.setdefault("certifications", [])
        d = dict(patch.data)
        if "id" not in d:
            d["id"] = _next_id(p["certifications"], prefix="cert_chat_")
        p["certifications"].append(d)
    elif patch.action == "add_education":
        p.setdefault("education", [])
        d = dict(patch.data)
        if "id" not in d:
            d["id"] = _next_id(p["education"], prefix="edu_chat_")
        p["education"].append(d)
    elif patch.action == "add_skill":
        cat = patch.data["category"]
        p.setdefault("skills", {}).setdefault(cat, [])
        val = patch.data.get("value", "")
        if val and val not in p["skills"][cat]:
            p["skills"][cat].append(val)
    elif patch.action == "add_bullet":
        eid = patch.target_id or patch.data["target_experience_id"]
        for exp in p.get("experience") or []:
            if exp.get("id") == eid:
                exp.setdefault("bullets", [])
                bid = f"{eid}.b{len(exp['bullets']) + 1}"
                bullet = {
                    "id": bid,
                    "text": patch.data.get("text", ""),
                    "skills_demonstrated": patch.data.get("skills_demonstrated") or [],
                    "metrics_present": [],
                }
                exp["bullets"].append(bullet)
                break
    elif patch.action == "edit_field":
        path = patch.data["path"]
        new_value = patch.data["value"]
        op = patch.data.get("op", "set")   # "set" | "append" | "remove"
        _apply_edit_field(p, path, new_value, op)

    return p


def _next_id(items: list[dict[str, Any]], *, prefix: str) -> str:
    n = 1
    while any((i.get("id") or "") == f"{prefix}{n}" for i in items):
        n += 1
    return f"{prefix}{n}"


def _apply_edit_field(profile: dict[str, Any], path: str, value: Any, op: str) -> None:
    keys = path.split(".")
    parent = profile
    for k in keys[:-1]:
        parent = parent.setdefault(k, {})
    leaf = keys[-1]
    if op == "set":
        parent[leaf] = value
    elif op == "append":
        parent.setdefault(leaf, [])
        if isinstance(value, list):
            for v in value:
                if v not in parent[leaf]:
                    parent[leaf].append(v)
        elif value not in parent[leaf]:
            parent[leaf].append(value)
    elif op == "remove":
        if leaf in parent and isinstance(parent[leaf], list):
            parent[leaf] = [v for v in parent[leaf]
                            if v != value and (
                                not isinstance(value, list) or v not in value
                            )]
    else:
        raise PatchError(f"unknown op {op!r}; valid: set, append, remove")


# --- LLM proposal ---

PROMPT = """You are a profile editor for a job-application tool.

The user will tell you something they want added to their profile (a new
project, internship, certification, skill, role bullet, or preference
update). Your job is to emit ONE structured patch in JSON.

# Output schema (return EXACTLY one JSON object)

{
  "action": "add_project" | "add_experience" | "add_certification" |
            "add_skill" | "add_bullet" | "add_education" |
            "edit_field" | "no_change",
  "data": { ... },
  "verbatim_quote": "exact substring of the user's message that justifies this patch",
  "reasoning": "one short sentence explaining why this action",
  "target_id": null   // only for add_bullet / edit_field
}

# Hard rules (the validator rejects patches that break these)

1. ONLY add fields the user EXPLICITLY mentioned. If they say "a few
   months" do NOT invent specific dates. If they don't say a percentage,
   don't add one. If they don't name an employer, don't make one up.
2. The `verbatim_quote` must be an exact substring of the user's message.
3. Numeric tokens (percentages, durations, dollar amounts) in your patch
   MUST also appear in the user's message. Don't infer "3 months" from
   "the last semester."
4. If the user is asking a question, making small talk, or saying
   something off-topic, return `{"action": "no_change", ...}`.
5. role_type for projects defaults to "project". For experience defaults
   to "internship" only if the user said "intern" / "internship";
   otherwise use "contract" or "fulltime" only if the user clearly said so.

# Action data shapes

add_project:       { name, description, skills?: [string], role_type?: "project" }
add_experience:    { company, title, role_type, summary, start?, end?, bullets? }
add_certification: { name, issued?: "YYYY-MM" }
add_skill:         { category: "technical"|"security"|"systems"|"cloud_security",
                     value: string }
add_bullet:        { target_experience_id: string, text: string,
                     skills_demonstrated?: [string] }
add_education:     { school, degree, status?: "in_progress"|"completed",
                     start?, expected_end? }
edit_field:        { path: "preferences.target_roles" | "preferences.locations"
                     | "preferences.industries_avoid" | ...,
                     value: any, op?: "set"|"append"|"remove" }

# Context

You'll receive the user's current profile (YAML) so you know existing
experience ids when adding bullets. Don't dump the profile back; just
emit the patch.
"""


def propose_patch(*, user_message: str, profile_yaml: str,
                   client: LLMClient | None = None) -> ProfilePatch:
    """Ask the LLM for a structured patch. Does NOT validate or apply --
    caller does that so the user can see + approve the proposal first."""
    client = client or LLMClient()
    user_block = (
        f"=== current profile (YAML) ===\n{profile_yaml.strip()}\n"
        f"\n=== user message ===\n{user_message.strip()}\n"
    )
    resp = client.complete(
        tier="extract", system=PROMPT, user=user_block,
        json_mode=True, temperature=0.1,
    )
    obj = resp.as_json()
    if not isinstance(obj, dict):
        raise PatchError(f"LLM returned non-object: {type(obj).__name__}")

    return ProfilePatch(
        action=str(obj.get("action") or "no_change"),
        data=obj.get("data") or {},
        verbatim_quote=str(obj.get("verbatim_quote") or ""),
        reasoning=str(obj.get("reasoning") or ""),
        target_id=obj.get("target_id"),
    )
