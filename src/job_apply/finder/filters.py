"""Filtering + lightweight scoring for the job_finder review queue.

These run BEFORE the expensive per-role pipeline (ingest+analyze+tailor).
The goal is to drop obviously-irrelevant rows fast, surface stretch roles
flagged as such, and produce a quick fit estimate so the user can review the
queue without burning LLM tokens.
"""
from __future__ import annotations

import re
from typing import Any

from ..job_analyzer import detect_clearance_requirement
from ..synonyms import matches_with_synonyms

# Title-pattern markers that indicate strong relevance to Dillon's targets
# (extended via profile.preferences.target_roles for per-user customization).
DEFAULT_TITLE_TARGETS = [
    "soc analyst", "security analyst", "cybersecurity analyst",
    "information security analyst", "infosec analyst",
    "vulnerability management", "vulnerability analyst",
    "grc analyst", "compliance analyst",
    "iam analyst", "identity analyst",
    "security operations analyst", "secops analyst",
    "security automation",
    "cloud security analyst",
    "it security analyst",
    "security engineer i", "associate security engineer", "junior security engineer",
    "associate soc",
    "data security analyst",
    "security assurance analyst", "security risk analyst",
    "threat detection",
]

# Titles that match ONLY when the JD body also contains a security keyword.
# Prevents generic "Technical Support Engineer" or "Software Engineer" matches
# from dominating the queue.
CONDITIONAL_TITLE_TARGETS = [
    "technical support engineer", "support engineer",
    "software engineer",
]
SECURITY_KEYWORDS = re.compile(
    r"\b(security|cybersecurity|soc|incident response|vulnerability|"
    r"siem|siem ?platform|threat|appsec|infosec|compliance|iam|"
    r"penetration test|phishing|forensic|malware|risk assessment)\b", re.I)

SENIOR_TITLE_MARKERS = [
    "senior", "staff", "principal", "lead", "manager", "director",
    "head of", "vp ", "architect",
]

STRETCH_YEARS_RE = re.compile(r"\b(\d+)\+?\s*(?:to\s*\d+\s*)?years?\b", re.I)


def title_matches_targets(title: str, targets: list[str] | None = None,
                          jd_text: str = "") -> bool:
    """Direct match against strict targets, OR conditional match (broad title +
    security keyword in JD body)."""
    if not title:
        return False
    title_lc = title.lower()
    candidates = (targets or []) + DEFAULT_TITLE_TARGETS
    if any(t.lower() in title_lc for t in candidates):
        return True
    if any(t in title_lc for t in CONDITIONAL_TITLE_TARGETS):
        return bool(jd_text and SECURITY_KEYWORDS.search(jd_text))
    return False


def is_senior_title(title: str) -> bool:
    title_lc = (title or "").lower()
    return any(m in title_lc for m in SENIOR_TITLE_MARKERS)


def required_years_from_text(text: str) -> int | None:
    """Best-effort years-required extraction from JD text. Returns the SMALLEST
    integer match, since postings usually phrase ranges as '3-5 years' or
    '2+ years'. Used to flag 5+ stretches."""
    if not text:
        return None
    matches = [int(m) for m in STRETCH_YEARS_RE.findall(text)]
    return min(matches) if matches else None


def quick_fit(*, posting: dict[str, Any], profile_skills: list[str],
              certs_needed_match: bool, target_roles: list[str]) -> dict[str, Any]:
    """Cheap fit estimate without LLM. Returns
    {"score": 0..100, "reasons": [...], "stretch_flags": [...]}.

    Components:
      - title alignment with target roles (40 pts)
      - synonym-aware skill overlap on raw_text snippet (40 pts)
      - cert match (20 pts)
      - stretch-year penalty (-30 if 5+ years detected)
      - senior-title penalty (-40 if title contains senior/lead/etc.)
    """
    title = posting.get("title", "")
    text = posting.get("raw_text") or ""
    reasons: list[str] = []
    stretch_flags: list[str] = []

    title_pts = 40 if title_matches_targets(title, target_roles, jd_text=text) else 10
    if title_pts == 40:
        reasons.append(f"title matches target list: {title!r}")
    else:
        reasons.append(f"title does not match target list: {title!r}")

    # Crude tokenization of JD text for skill matching
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9+./_-]{2,}", text.lower())
    sample = list(set(tokens))
    hits = sum(
        1 for s in sample if matches_with_synonyms(s, profile_skills)
    )
    skill_pts = min(40, int(40 * hits / max(40, 1)))   # heuristic cap
    if hits:
        reasons.append(f"~{hits} skill-overlap tokens via synonym matcher")

    cert_pts = 20 if certs_needed_match else 0
    if cert_pts:
        reasons.append("cert match")

    score = title_pts + skill_pts + cert_pts

    # Stretch detection emits FLAGS only — does NOT subtract from the score.
    # `should_drop` uses flags to decide whether to surface or drop the row,
    # honoring the user's `--allow-stretch` preference. Scoring this separately
    # keeps the score interpretable (a stretch role with strong skill overlap
    # still shows a high fit and just gets the stretch label).
    if is_senior_title(title):
        stretch_flags.append("title contains senior/lead/staff/principal")
    yrs = required_years_from_text(text)
    if yrs and yrs >= 5:
        stretch_flags.append(f"{yrs}+ years required")

    score = max(0, min(100, score))
    return {"score": score, "reasons": reasons, "stretch_flags": stretch_flags}


def should_drop(posting: dict[str, Any], *, fit: dict[str, Any],
                allow_stretch: bool = False) -> tuple[bool, str]:
    """Hard drop rules: clearance, industries_avoid, etc."""
    text = posting.get("raw_text") or ""
    fields = {
        "responsibilities": [], "required_skills": [],
        "preferred_skills": [], "keywords_extracted": [],
    }
    cr = detect_clearance_requirement(text, fields)
    if cr.get("required"):
        labels = [m.get("pattern", "?") for m in (cr.get("matches") or [])]
        return True, f"clearance/export-control: {labels[0]}"

    if not allow_stretch and fit.get("stretch_flags"):
        # Senior + non-junior signals → drop unless user opts in
        return True, "; ".join(fit["stretch_flags"])

    if fit.get("score", 0) < 25:
        return True, f"quick fit score too low ({fit.get('score')})"

    return False, ""
