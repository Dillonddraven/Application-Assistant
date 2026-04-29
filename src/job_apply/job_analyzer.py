"""LLM-driven extraction + rule-based fit score for a single job posting.

Flow:
  1. Load profile.
  2. Send the analyzer prompt + posting text to the LLM (extract tier).
  3. Parse JSON.
  4. Compute industry_filter from LLM tags + keyword fallback.
  5. Compute fit_score via deterministic rules using the profile.
  6. Validate + persist analyzed/<id>.json.
"""
from __future__ import annotations

import re
from importlib.resources import files
from typing import Any

from . import state
from .llm_client import LLMClient
from .profile_loader import Profile, load_profile
from .validators.schema import validate_analyzed

PROMPT_VERSION = "analyze_job@v1"

_ANALYZE_PROMPT = files("job_apply.prompts").joinpath("analyze_job.txt").read_text()


def _profile_summary_for_llm(profile: Profile) -> str:
    """Produce a compact summary the analyzer can use to populate missing_quals."""
    p = profile.data
    bits: list[str] = []
    edu = p.get("education") or []
    if edu:
        bits.append("education: " + "; ".join(
            f"{e.get('degree')} ({e.get('status')})" for e in edu
        ))
    certs = p.get("certifications") or []
    if certs:
        bits.append("certs: " + ", ".join(c.get("name", "") for c in certs))
    exp = p.get("experience") or []
    if exp:
        bits.append("experience: " + "; ".join(
            f"{e.get('title')} at {e.get('company')} ({e.get('role_type','')})"
            for e in exp
        ))
    skills = p.get("skills") or {}
    flat: list[str] = []
    for v in skills.values():
        if isinstance(v, list):
            flat.extend(v)
    if flat:
        bits.append("skills: " + ", ".join(flat))
    prefs = p.get("preferences") or {}
    if prefs.get("target_roles"):
        bits.append("target_roles: " + ", ".join(prefs["target_roles"]))
    return "\n".join(bits)


def compute_industry_filter(
    *,
    industry_tags: list[str],
    company: str,
    title: str,
    text: str,
    industries_avoid: list[str],
) -> str:
    if not industries_avoid:
        return "ok"
    tags_lower = {t.lower() for t in industry_tags}
    avoid_lower = {a.lower() for a in industries_avoid}
    if tags_lower & avoid_lower:
        return "avoid"
    # Keyword fallback: only triggers if a tag-based decision wasn't made.
    haystack = f"{company} {title}".lower()
    for term in avoid_lower:
        if re.search(rf"\b{re.escape(term)}\b", haystack):
            return "review"  # softer — let the user confirm; tags are primary
    # Last-resort: scan posting text for the avoid term very near common signals
    text_lower = text.lower()
    for term in avoid_lower:
        if term in text_lower and any(
            s in text_lower for s in ("active duty", "veteran preferred", "dod ", "department of defense")
        ):
            return "review"
    return "ok"


def _flat_profile_skills(profile: Profile) -> set[str]:
    out: set[str] = set()
    for v in (profile.data.get("skills") or {}).values():
        if isinstance(v, list):
            out.update(s.lower() for s in v if isinstance(s, str))
    return out


def _profile_cert_names(profile: Profile) -> set[str]:
    return {
        c.get("name", "").lower()
        for c in profile.data.get("certifications") or []
        if c.get("name")
    }


def _has_any_internship_or_more(profile: Profile) -> bool:
    return bool(profile.data.get("experience"))


def compute_fit_score(*, llm_fields: dict[str, Any], profile: Profile) -> dict[str, Any]:
    """Deterministic component scores in [0,100] and a weighted total."""
    req_skills = [s.lower() for s in llm_fields.get("required_skills") or []]
    pref_skills = [s.lower() for s in llm_fields.get("preferred_skills") or []]
    profile_skills = _flat_profile_skills(profile)

    def overlap(needed: list[str]) -> int:
        if not needed:
            return 100
        hits = sum(1 for s in needed if any(s in ps or ps in s for ps in profile_skills))
        return int(round(100 * hits / len(needed)))

    skills_match = overlap(req_skills)
    pref_skills_match = overlap(pref_skills)

    needed_certs = [c.lower() for c in llm_fields.get("required_certifications") or []]
    profile_certs = _profile_cert_names(profile)
    if not needed_certs:
        cert_match = 100
    else:
        hits = sum(1 for c in needed_certs if any(pc in c or c in pc for pc in profile_certs))
        cert_match = int(round(100 * hits / len(needed_certs)))

    # Experience: penalize if min_years > 1 since profile has internship-level experience
    min_years = int(llm_fields.get("min_years_experience") or 0)
    if min_years <= 0:
        exp_match = 100
    elif min_years == 1:
        exp_match = 80 if _has_any_internship_or_more(profile) else 50
    elif min_years == 2:
        exp_match = 60 if _has_any_internship_or_more(profile) else 30
    else:
        exp_match = max(0, 40 - 10 * (min_years - 2))

    # Location. The candidate must actually be reachable for the role:
    # remote-ok job + remote_ok candidate, OR posting location intersects the
    # candidate's preferred locations, OR willing_to_relocate=True. Otherwise
    # the role is not realistically attainable and the score reflects that.
    prefs = profile.data.get("preferences") or {}
    remote_mode = (llm_fields.get("remote_mode") or "unknown").lower()
    posting_loc = (llm_fields.get("location") or "").lower()
    wanted_locs = [w.lower() for w in (prefs.get("locations") or [])]
    location_intersects = bool(wanted_locs and any(w in posting_loc for w in wanted_locs))
    relocation_ok = bool(prefs.get("willing_to_relocate"))

    if remote_mode == "remote":
        location_match = 100 if prefs.get("remote_ok", True) else 35
    elif remote_mode == "hybrid":
        if not prefs.get("hybrid_ok", True):
            location_match = 35
        elif location_intersects:
            location_match = 100
        elif relocation_ok:
            location_match = 65
        else:
            location_match = 30
    elif remote_mode == "onsite":
        if not prefs.get("onsite_ok", True):
            location_match = 25
        elif location_intersects:
            location_match = 100
        elif relocation_ok:
            location_match = 65
        else:
            location_match = 25
    else:
        # remote_mode == "unknown" — the posting didn't say. Be conservative:
        # treat as if onsite-required since that's the riskier failure mode.
        if location_intersects:
            location_match = 90
        elif relocation_ok:
            location_match = 60
        elif prefs.get("remote_ok", True):
            # If the user is open to remote, give partial credit even when unknown.
            location_match = 55
        else:
            location_match = 30

    industry_filter = llm_fields.get("industry_filter", "ok")
    industry_penalty = {"ok": 0, "review": 25, "avoid": 80}.get(industry_filter, 0)

    weighted = (
        0.40 * skills_match
        + 0.15 * pref_skills_match
        + 0.20 * cert_match
        + 0.15 * exp_match
        + 0.10 * location_match
    )
    total = max(0, int(round(weighted - industry_penalty)))

    return {
        "fit_score": total,
        "fit_breakdown": {
            "skills_match": skills_match,
            "preferred_skills_match": pref_skills_match,
            "cert_match": cert_match,
            "experience_match": exp_match,
            "location_match": location_match,
            "industry_filter": industry_filter,
        },
    }


def analyze_job(
    *,
    job_id: str,
    profile: Profile,
    text: str,
    source_url: str | None,
    fetched_at: str,
    raw_text_path: str,
    llm: LLMClient | None = None,
) -> dict[str, Any]:
    client = llm or LLMClient()
    user_prompt = (
        "CANDIDATE PROFILE SUMMARY (use only to populate `concerns` and `missing_quals`):\n"
        + _profile_summary_for_llm(profile)
        + "\n\n--- JOB POSTING ---\n"
        + text
    )
    resp = client.complete(
        tier="extract",
        system=_ANALYZE_PROMPT,
        user=user_prompt,
        json_mode=True,
        temperature=0.1,
    )
    fields = resp.as_json()
    if not isinstance(fields, dict):
        raise RuntimeError(f"analyzer LLM returned non-object: {type(fields).__name__}")

    industry_filter = compute_industry_filter(
        industry_tags=fields.get("industry_tags") or [],
        company=fields.get("company") or "",
        title=fields.get("title") or "",
        text=text,
        industries_avoid=profile.industries_avoid,
    )

    merged: dict[str, Any] = {
        "id": job_id,
        "source_url": source_url,
        "fetched_at": fetched_at,
        "raw_text_path": raw_text_path,
        "company": fields.get("company") or "",
        "title": fields.get("title") or "",
        "location": fields.get("location"),
        "remote_mode": fields.get("remote_mode") or "unknown",
        "required_skills": fields.get("required_skills") or [],
        "preferred_skills": fields.get("preferred_skills") or [],
        "min_years_experience": int(fields.get("min_years_experience") or 0),
        "required_certifications": fields.get("required_certifications") or [],
        "responsibilities": fields.get("responsibilities") or [],
        "keywords_extracted": fields.get("keywords_extracted") or [],
        "industry_tags": fields.get("industry_tags") or [],
        "industry_filter": industry_filter,
        "fit_rationale": fields.get("fit_rationale") or "",
        "concerns": fields.get("concerns") or [],
        "missing_quals": fields.get("missing_quals") or [],
        "prompt_version": PROMPT_VERSION,
        "model": resp.model,
    }
    score = compute_fit_score(llm_fields=merged, profile=profile)
    merged.update(score)

    errs = validate_analyzed(merged)
    if errs:
        raise RuntimeError("analyzer output failed schema validation:\n" + "\n".join(errs))
    return merged


def analyze_all(*, only_id: str | None = None, refresh: bool = False) -> list[dict[str, Any]]:
    """Analyze ingested-but-not-yet-analyzed jobs (or one specific id, or all with refresh)."""
    profile = load_profile()
    client = LLMClient()
    out: list[dict[str, Any]] = []
    for rec in state.list_ingests():
        if only_id and rec.job_id != only_id:
            continue
        if state.load_analyzed(rec.job_id) and not refresh:
            continue
        analyzed = analyze_job(
            job_id=rec.job_id,
            profile=profile,
            text=rec.text,
            source_url=rec.source_url,
            fetched_at=rec.fetched_at,
            raw_text_path=str(rec.raw_text_path),
            llm=client,
        )
        state.save_analyzed(rec.job_id, analyzed)
        out.append(analyzed)
    return out
