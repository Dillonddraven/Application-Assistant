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

# Job board / ATS confidence: where the URL came from is a reasonable proxy
# for how reliable the listing is. Direct ATS boards (Greenhouse, Lever, etc.)
# tend to be authoritative employer postings. LinkedIn / Indeed are mid-tier
# (real but mediated). Aggregators that re-syndicate (OptNation, Glassdoor)
# are low-confidence — apply directly via the company's careers page if you can.
_SOURCE_CONFIDENCE_HIGH = [
    "greenhouse.io", "boards.greenhouse.io",
    "lever.co", "jobs.lever.co",
    "ashbyhq.com", "jobs.ashbyhq.com",
    "workable.com", "apply.workable.com",
    "myworkdayjobs.com", "myworkday.com",
    "smartrecruiters.com",
    "icims.com",
    "successfactors.com",
    "bamboohr.com",
    "personio.com",
    "rippling.com/jobs",
    "jobvite.com",
]

_SOURCE_CONFIDENCE_MEDIUM = [
    "linkedin.com/jobs",
    "indeed.com",
    "monster.com",
    "dice.com",
    "builtin.com",
    "stackoverflow.com/jobs",
    "weworkremotely.com",
]

_SOURCE_CONFIDENCE_LOW = [
    "optnation.com",
    "glassdoor.com",
    "ziprecruiter.com",
    "wellfound.com",
    "angel.co",
    "simplyhired.com",
    "talent.com",
    "joblist.com",
    "neuvoo.com",
    "utm_campaign=google_jobs_apply",
    "google_jobs_apply",
]


def score_source_confidence(url: str | None) -> tuple[str, str]:
    """Return (confidence, reason). Confidence is 'high' | 'medium' | 'low'."""
    if not url:
        return "medium", "no source URL (pasted text or local file)"
    u = url.lower()
    for pattern in _SOURCE_CONFIDENCE_HIGH:
        if pattern in u:
            return "high", f"direct ATS board ({pattern})"
    for pattern in _SOURCE_CONFIDENCE_LOW:
        if pattern in u:
            return "low", f"aggregator / re-syndicator ({pattern}); apply via the company's direct careers page if possible"
    for pattern in _SOURCE_CONFIDENCE_MEDIUM:
        if pattern in u:
            return "medium", f"job-board listing ({pattern})"
    return "medium", "unrecognized source — treat cautiously"


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
    """Deterministic component scores in [0,100] and a weighted total.

    Returns the score plus an `apply_reasoning` list of human-readable strings
    explaining why each component scored what it did. The reasoning is used by
    `bench.build_scorecard` and the production-mode early-stop logic.
    """
    reasoning: list[str] = []

    req_skills = [s.lower() for s in llm_fields.get("required_skills") or []]
    pref_skills = [s.lower() for s in llm_fields.get("preferred_skills") or []]
    profile_skills = _flat_profile_skills(profile)

    def overlap(needed: list[str]) -> tuple[int, int, int]:
        if not needed:
            return 100, 0, 0
        hits = sum(1 for s in needed if any(s in ps or ps in s for ps in profile_skills))
        return int(round(100 * hits / len(needed))), hits, len(needed)

    skills_match, skill_hits, skill_total = overlap(req_skills)
    pref_skills_match, _, _ = overlap(pref_skills)
    if req_skills:
        reasoning.append(f"required-skill overlap: {skill_hits}/{skill_total} = {skills_match}")

    needed_certs = [c.lower() for c in llm_fields.get("required_certifications") or []]
    profile_certs = _profile_cert_names(profile)
    if not needed_certs:
        cert_match = 100
    else:
        hits = sum(1 for c in needed_certs if any(pc in c or c in pc for pc in profile_certs))
        cert_match = int(round(100 * hits / len(needed_certs)))
        reasoning.append(f"cert match: {hits}/{len(needed_certs)} = {cert_match}")

    # Experience-level scoring (revised May 2026):
    # 0-3 years required + has internships/projects -> high (still a fit)
    # 4 years -> medium penalty
    # 5+ years OR senior/lead/principal -> heavy penalty
    title_lc = (llm_fields.get("title") or "").lower()
    senior_signal = any(t in title_lc for t in (
        "senior", "staff", "principal", "lead", "manager", "architect"
    ))
    min_years = int(llm_fields.get("min_years_experience") or 0)
    has_intern = _has_any_internship_or_more(profile)

    if senior_signal:
        exp_match = 15
        reasoning.append(f"senior/lead/principal/staff title detected -> heavy penalty (exp_match=15)")
    elif min_years <= 2:
        exp_match = 100 if has_intern else 70
        reasoning.append(f"≤2 years required + internships present -> exp_match={exp_match}")
    elif min_years == 3:
        exp_match = 75 if has_intern else 50
        reasoning.append(f"3 years required (within stretch range for early-career) -> exp_match={exp_match}")
    elif min_years == 4:
        exp_match = 55 if has_intern else 30
        reasoning.append(f"4 years required -> stretch; exp_match={exp_match}")
    else:
        exp_match = max(0, 30 - 5 * (min_years - 5))
        reasoning.append(f"5+ years required -> heavy penalty; exp_match={exp_match}")

    # Location scoring (revised May 2026): the candidate is now flexible across
    # developed metros. Don't over-penalize unfamiliar cities. Hard-block only
    # on clearance/visa/citizenship/relocation-impossible cases (handled in
    # apply_recommendation, not here).
    prefs = profile.data.get("preferences") or {}
    remote_mode = (llm_fields.get("remote_mode") or "unknown").lower()
    posting_loc = (llm_fields.get("location") or "").lower()
    wanted_locs = [w.lower() for w in (prefs.get("locations") or [])]
    preferred_metros = [m.lower() for m in (prefs.get("preferred_metros") or [])]
    location_intersects = bool(wanted_locs and any(w in posting_loc for w in wanted_locs))
    metro_match = bool(preferred_metros and any(m in posting_loc for m in preferred_metros))
    relocation_ok = bool(prefs.get("willing_to_relocate"))

    location_confidence = "neutral"
    if remote_mode == "remote":
        if prefs.get("remote_ok", True):
            location_match = 100
            location_confidence = "strong"
            reasoning.append("remote role + remote_ok=true -> location_match=100")
        else:
            location_match = 35
            location_confidence = "negative"
            reasoning.append("remote role but candidate doesn't accept remote -> 35")
    elif remote_mode == "hybrid":
        if not prefs.get("hybrid_ok", True):
            location_match = 35
            location_confidence = "negative"
            reasoning.append("hybrid role but candidate doesn't accept hybrid -> 35")
        elif location_intersects or metro_match:
            location_match = 100
            location_confidence = "strong"
            reasoning.append(f"hybrid role in preferred metro -> 100 ({posting_loc})")
        elif relocation_ok:
            location_match = 80
            location_confidence = "neutral"
            reasoning.append("hybrid role + willing_to_relocate -> 80 (worth considering)")
        else:
            location_match = 45
            location_confidence = "negative"
            reasoning.append("hybrid role outside preferred metros + no relocation -> 45")
    elif remote_mode == "onsite":
        if not prefs.get("onsite_ok", True):
            location_match = 25
            location_confidence = "negative"
            reasoning.append("onsite role but candidate doesn't accept onsite -> 25")
        elif location_intersects or metro_match:
            location_match = 100
            location_confidence = "strong"
            reasoning.append(f"onsite role in preferred metro -> 100 ({posting_loc})")
        elif relocation_ok:
            location_match = 75
            location_confidence = "neutral"
            reasoning.append("onsite + willing_to_relocate -> 75 (relocation worth it for fit)")
        else:
            location_match = 30
            location_confidence = "negative"
            reasoning.append("onsite outside preferred metros + no relocation -> 30")
    else:
        # remote_mode unknown
        if location_intersects or metro_match:
            location_match = 90
            location_confidence = "strong"
            reasoning.append(f"unknown remote_mode but location is preferred metro -> 90")
        elif relocation_ok or prefs.get("remote_ok", True):
            location_match = 70
            location_confidence = "neutral"
            reasoning.append("unknown remote_mode but candidate is flexible -> 70")
        else:
            location_match = 40
            location_confidence = "negative"
            reasoning.append("unknown remote_mode + candidate not flexible -> 40")

    industry_filter = llm_fields.get("industry_filter", "ok")
    industry_penalty = {"ok": 0, "review": 25, "avoid": 80}.get(industry_filter, 0)
    if industry_penalty:
        reasoning.append(f"industry filter = {industry_filter} -> -{industry_penalty}")

    weighted = (
        0.40 * skills_match
        + 0.15 * pref_skills_match
        + 0.20 * cert_match
        + 0.15 * exp_match
        + 0.10 * location_match
    )
    total = max(0, int(round(weighted - industry_penalty)))
    reasoning.append(
        f"weighted total = 0.40*skills({skills_match}) + 0.15*pref({pref_skills_match}) + "
        f"0.20*cert({cert_match}) + 0.15*exp({exp_match}) + 0.10*loc({location_match}) "
        f"- industry({industry_penalty}) = {total}"
    )

    # Top reasons for / against
    component_scores = {
        "required-skills overlap": skills_match,
        "preferred-skills overlap": pref_skills_match,
        "cert match": cert_match,
        "experience-level": exp_match,
        "location": location_match,
    }
    sorted_components = sorted(component_scores.items(), key=lambda x: -x[1])
    top_reasons_for = [f"{name}: {score}" for name, score in sorted_components[:3]
                       if score >= 60]
    top_gaps = [f"{name}: {score}" for name, score in sorted_components[::-1][:3]
                if score < 60]

    return {
        "fit_score": total,
        "fit_breakdown": {
            "skills_match": skills_match,
            "preferred_skills_match": pref_skills_match,
            "cert_match": cert_match,
            "experience_match": exp_match,
            "location_match": location_match,
            "location_confidence": location_confidence,
            "industry_filter": industry_filter,
        },
        "apply_reasoning": reasoning,
        "top_reasons_for": top_reasons_for,
        "top_gaps": top_gaps,
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

    source_confidence, source_confidence_reason = score_source_confidence(source_url)

    merged: dict[str, Any] = {
        "id": job_id,
        "source_url": source_url,
        "source_confidence": source_confidence,
        "source_confidence_reason": source_confidence_reason,
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
