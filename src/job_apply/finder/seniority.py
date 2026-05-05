"""Seniority + salary + blocker detectors used by the new ranking module.

These run on JD raw_text + title and produce structured signals that the
ranking layer combines into a single fit score with category."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


# --- experience level ---

ENTRY_HINT = re.compile(
    r"\b(entry[\s-]?level|early[\s-]?career|new\s+grad(?:uate)?|"
    r"recent\s+graduate|rotational\s+program|"
    r"no\s+experience\s+required|new\s+college\s+grad)\b", re.I)

# Look for an explicit "X years" requirement; pick the SMALLEST mentioned
# (postings typically phrase ranges as "3-5 years" / "2+ years").
YEARS_RE = re.compile(r"\b(\d+)\+?\s*(?:to|–|-)?\s*\d*\s*years?\b", re.I)

# Title-level senior markers (already in filters.py but duplicated for clarity)
SENIOR_MARKERS = re.compile(
    r"\b(senior|sr\.?|staff|principal|lead|architect|"
    r"director|head of|vp|chief)\b", re.I)
MID_MARKERS = re.compile(
    r"\b(intermediate|mid|mid-level|l3|level\s*3|engineer\s*ii)\b", re.I)


@dataclass
class ExperienceSignal:
    level: str           # "entry" | "junior" | "target" | "mid" | "senior" | "unknown"
    years_min: int | None
    years_max: int | None
    matched_markers: list[str]


def detect_experience_level(*, title: str, jd_text: str) -> ExperienceSignal:
    """Combine title-level markers + JD body to estimate seniority.

    Returns one of:
      entry   = entry-level / new-grad / 0 yrs
      junior  = associate / 1-2 yrs / "junior" in title
      target  = 2-3 yrs (Dillon's sweet spot)
      mid     = 3-5 yrs OR "intermediate" / "mid" / "engineer II" markers
      senior  = 5+ yrs OR senior/staff/principal/lead/architect/manager+
      unknown = nothing detected
    """
    title = title or ""
    body = jd_text or ""
    matched: list[str] = []

    # Strong senior signal from title — short-circuit
    if SENIOR_MARKERS.search(title):
        matched.append(f"title-senior:{SENIOR_MARKERS.search(title).group(0)}")
        return ExperienceSignal(level="senior", years_min=None, years_max=None,
                                 matched_markers=matched)

    # Mid markers in title
    title_mid = MID_MARKERS.search(title)
    if title_mid:
        matched.append(f"title-mid:{title_mid.group(0)}")

    # Years from body
    years_hits = [int(m) for m in YEARS_RE.findall(body)]
    years_min = min(years_hits) if years_hits else None
    years_max = max(years_hits) if years_hits else None

    # Entry hints (new-grad, internship, junior in body)
    entry_hits = [m.group(0) for m in ENTRY_HINT.finditer(body)]
    if entry_hits:
        matched.extend(f"body-entry:{h.strip()[:30]}" for h in entry_hits[:2])

    # Decide level
    level = "unknown"
    if years_min is not None:
        if years_min >= 5:
            level = "senior"
        elif years_min >= 3:
            level = "mid"
        elif years_min >= 2:
            level = "target"
        elif years_min >= 1:
            level = "junior"
        else:
            level = "entry"
    if entry_hits and level in ("unknown", "junior", "target"):
        level = "entry" if level == "unknown" else "junior"
    if title_mid and level not in ("senior",):
        level = "mid"

    return ExperienceSignal(level=level, years_min=years_min,
                             years_max=years_max, matched_markers=matched)


# --- salary range ---

# Common patterns: "$100,000 - $130,000", "$100k - $130k", "$100K—$130K"
SALARY_RE = re.compile(
    r"\$\s*([\d]{2,3})(?:[,_]?(\d{3}))?\s*(k|,000)?\s*[-–—to]+\s*"
    r"\$\s*([\d]{2,3})(?:[,_]?(\d{3}))?\s*(k|,000)?",
    re.I)


@dataclass
class SalarySignal:
    min_usd: int | None
    max_usd: int | None
    bucket: str   # "target" | "reach" | "mid_senior" | "senior" | "below_target" | "unknown"


def _parse_amount(num: str, suffix_k: bool) -> int:
    n = int(num)
    if suffix_k or n < 1000:
        n = n * 1000
    return n


def detect_salary_range(jd_text: str) -> SalarySignal:
    if not jd_text:
        return SalarySignal(None, None, "unknown")
    m = SALARY_RE.search(jd_text)
    if not m:
        return SalarySignal(None, None, "unknown")
    lo = _parse_amount(m.group(1) + (m.group(2) or ""), bool(m.group(3)))
    hi = _parse_amount(m.group(4) + (m.group(5) or ""), bool(m.group(6)))
    if lo > hi:
        lo, hi = hi, lo
    midpoint = (lo + hi) // 2
    if midpoint < 60_000:
        bucket = "below_target"
    elif midpoint <= 110_000:
        bucket = "target"
    elif midpoint <= 140_000:
        bucket = "reach"
    elif midpoint <= 180_000:
        bucket = "mid_senior"
    else:
        bucket = "senior"
    return SalarySignal(min_usd=lo, max_usd=hi, bucket=bucket)


# --- blockers ---

# Languages other than English — flag if "fluent / professional / native"
# alongside a non-English language name.
NON_ENGLISH_LANGS = (
    "spanish", "portuguese", "mandarin", "chinese", "cantonese", "japanese",
    "korean", "german", "french", "italian", "dutch", "russian", "polish",
    "ukrainian", "turkish", "arabic", "hebrew", "hindi", "vietnamese", "thai",
    "indonesian", "malay", "tagalog", "swedish", "norwegian", "danish",
    "finnish", "czech", "slovak", "romanian", "bulgarian",
)
LANG_PROFICIENCY_RE = re.compile(
    r"\b(fluent|fluency|professional|business|native|"
    r"professional working proficiency)\b\s+(?:in\s+)?\W*("
    + "|".join(NON_ENGLISH_LANGS) + r")\b",
    re.I)
LANG_REQUIRED_RE = re.compile(
    r"\b(?:required|requirement|must have|must speak|need)\b[^.]*\b("
    + "|".join(NON_ENGLISH_LANGS) + r")\b", re.I)

# AML / KYC / fraud-investigations as a years-of-experience requirement
AML_KYC_RE = re.compile(
    r"\b(\d+\+?\s*years?\s+(?:of\s+)?(?:aml|kyc|"
    r"fraud\s+investigations?|sanctions|"
    r"transaction\s+monitoring))\b", re.I)

# Production cloud / security ownership (mature program ownership)
PROD_OWNERSHIP_RE = re.compile(
    r"\b(?:own(?:ed|ing|ership)?|architect(?:ed|ing)?|"
    r"led|lead(?:ing)?|drove|drive)\s+(?:the\s+)?(?:enterprise|"
    r"production|company-wide|organization-wide|global)\s+"
    r"(?:\w+\s+){0,3}"
    r"(?:program|practice|engineering|architecture|"
    r"strategy|roadmap)\b",
    re.I)

# Law-enforcement background
LE_BACKGROUND_RE = re.compile(
    r"\b(law enforcement background|prior law enforcement|"
    r"former\s+(?:law enforcement|police|fbi|cia|nsa)|"
    r"sworn\s+(?:officer|peace\s+officer))\b", re.I)

# Trust & Safety policy ownership (years-of)
TS_POLICY_RE = re.compile(
    r"\b(\d+\+?\s*years?\s+(?:of\s+)?(?:trust\s*(?:&|and)\s*safety|"
    r"content\s+policy|community\s+policy)\s+(?:policy|program)\s+"
    r"(?:ownership|leadership|management))\b", re.I)


@dataclass
class Blocker:
    kind: str       # "language" | "clearance" | "le_background" | ...
    detail: str     # short human description
    severity: str   # "hard" | "soft"


def detect_blockers(*, title: str, jd_text: str, location: str = "",
                     allowed_locations: list[str] | None = None,
                     ) -> list[Blocker]:
    """Detect hard blockers in a JD. Clearance detection lives in
    job_analyzer.detect_clearance_requirement; we re-import only when
    explicitly asked, since the runner already drops clearance roles."""
    blockers: list[Blocker] = []
    body = jd_text or ""

    # Language proficiency (non-English required)
    for m in LANG_PROFICIENCY_RE.finditer(body):
        lang = m.group(2).lower()
        blockers.append(Blocker(
            kind="language",
            detail=f"Required {m.group(1)} {lang} proficiency",
            severity="hard",
        ))
        break  # one is enough; don't spam
    if not any(b.kind == "language" for b in blockers):
        for m in LANG_REQUIRED_RE.finditer(body):
            lang = m.group(1).lower()
            blockers.append(Blocker(
                kind="language",
                detail=f"Required {lang} proficiency",
                severity="hard",
            ))
            break

    # AML / KYC years
    m = AML_KYC_RE.search(body)
    if m:
        blockers.append(Blocker(
            kind="aml_kyc_years",
            detail=f"Requires {m.group(1).strip()}",
            severity="hard",
        ))

    # Production / mature program ownership
    if PROD_OWNERSHIP_RE.search(body):
        blockers.append(Blocker(
            kind="production_ownership",
            detail="Requires production / enterprise program ownership",
            severity="hard",
        ))

    # Law-enforcement background
    if LE_BACKGROUND_RE.search(body):
        blockers.append(Blocker(
            kind="le_background",
            detail="Requires prior law-enforcement background",
            severity="hard",
        ))

    # Trust & Safety policy ownership years
    m = TS_POLICY_RE.search(body)
    if m:
        blockers.append(Blocker(
            kind="ts_policy_years",
            detail=f"Requires {m.group(1).strip()}",
            severity="hard",
        ))

    # Location: outside the allowed_locations set
    if location and allowed_locations:
        loc_lc = location.lower()
        loc_ok = any(a.lower() in loc_lc or loc_lc in a.lower()
                     for a in allowed_locations)
        # Soft blocker: still surface, but not hard-reject (user can relocate)
        if not loc_ok and not any(
            kw in loc_lc for kw in ("remote", "hybrid", "distributed")
        ):
            blockers.append(Blocker(
                kind="location",
                detail=f"Location {location!r} outside preferred metros",
                severity="soft",
            ))

    return blockers
