"""Per-role ranking: combines title-fit, experience-fit, blockers, and
salary signal into a single fit score (0-100) with categorical recommendation
(Strong Target / Target / Reach / Too Senior / Blocker).

Scoring weights (per Dillon's directive 2026-05-05):
  experience_fit      35%
  role_family_fit     25%
  skills_match        20%
  location_flex       10%   (remote/hybrid is a SMALL bonus, not a tiebreaker)
  interest            10%
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from . import filters
from .seniority import (
    Blocker, ExperienceSignal, SalarySignal,
    detect_experience_level, detect_salary_range, detect_blockers,
)

# Target role families -- lowercased substrings checked against the title.
# These are the FIRST-CLASS targets; matches earn full role_family_fit.
TARGET_FAMILIES = [
    "cybersecurity analyst", "security analyst", "soc analyst",
    "vulnerability management analyst", "vulnerability analyst",
    "grc analyst", "security compliance analyst", "compliance analyst",
    "risk and compliance analyst",
    "it security analyst",
    "cloud security analyst", "cloud security associate",
    "threat intelligence analyst",
    "security operations analyst", "secops analyst",
    "application security analyst", "appsec analyst",
    "information security analyst", "infosec analyst",
]

# Fraud / identity / trust & safety / risk family -- distinct from generic
# "security_other" because Dillon's transferable experience (cybersecurity
# labs, internship investigations, SAST reporting / evidence review,
# centralized logging, PCI audit) maps DIRECTLY to these roles' core work
# (event review, suspicious-activity pattern recognition, evidence
# collection, risk-based decisioning). Per Dillon's 2026-05-05 directive.
FRAUD_RISK_FAMILIES = [
    "fraud investigator", "fraud analyst", "fraud risk analyst",
    "fraud & identity", "fraud and identity", "fraud specialist",
    "trust & safety analyst", "trust and safety analyst",
    "trust & safety operations", "trust and safety operations",
    "trust & safety associate", "trust and safety associate",
    "identity verification analyst", "identity analyst",
    "account security analyst", "account security specialist",
    "account takeover", "abuse analyst",
    "risk analyst",          # standalone "Risk Analyst" -- not "compliance analyst"
    "risk operations analyst", "risk operations associate",
    "platform risk", "payments risk", "credit risk analyst",
    "kyc analyst", "aml analyst",
    "investigations analyst",
]

# Adjacent families -- earn partial credit when paired with security-domain
# language in the JD body.
ADJACENT_FAMILIES = [
    "security engineer", "security engineer i",
    "associate security engineer", "junior security engineer",
    "security operations engineer",
    "data security analyst", "iam analyst",
    "privacy analyst", "audit analyst",
]


@dataclass
class FitBreakdown:
    experience: float          # 0-100
    role_family: float         # 0-100
    skills: float              # 0-100
    location: float            # 0-100
    interest: float            # 0-100
    blockers: list[Blocker] = field(default_factory=list)
    experience_level: str = "unknown"
    salary_bucket: str = "unknown"
    role_family_label: str = "off-target"   # "target" | "fraud_risk" | "adjacent" | "security_other" | "off-target"


@dataclass
class RankResult:
    score: int                       # weighted 0-100
    category: str                    # Strong Target / Target / Reach / Too Senior / Blocker
    biggest_reason: str
    biggest_risk: str
    tailor_resume: bool
    resume_angle: str
    outreach_angle: str
    recommendation: str               # Apply / Maybe apply / Skip
    breakdown: FitBreakdown


# --- experience scoring ---

def _experience_score(sig: ExperienceSignal) -> float:
    """Returns 0-100; higher = better fit for an early-career candidate.

    entry-level / new-grad / 0 yrs    -> 100
    junior / associate / 1-2 yrs      -> 90
    target / 2-3 yrs                  -> 70 (Dillon's edge of viability)
    mid / intermediate / 3-5 yrs      -> 35
    senior / 5+ yrs                   -> 5  (almost zero, but not -1: a senior
                                            JD with a junior-friendly note can
                                            still score >0)
    unknown                           -> 60 (no signal, treat as plausibly OK)
    """
    return {
        "entry": 100.0,
        "junior": 90.0,
        "target": 70.0,
        "mid": 35.0,
        "senior": 5.0,
        "unknown": 60.0,
    }.get(sig.level, 60.0)


# --- role-family scoring ---

def _role_family_score(*, title: str, jd_text: str,
                        target_families: list[str] | None = None,
                        ) -> tuple[float, str]:
    """Returns (score 0-100, label)."""
    title_lc = (title or "").lower()
    if not title_lc:
        return 0.0, "off-target"

    # Fraud / identity / trust & safety / risk family is checked FIRST so
    # specific titles like "Account Security Analyst" don't accidentally
    # match the broader "security analyst" target family. Dillon's
    # transferable cyber + internship + lab experience maps directly to
    # these roles' investigation / event-review / risk-decisioning core
    # work, so we score them as 'target'-tier (95) rather than dumping
    # them into generic security_other.
    for fam in FRAUD_RISK_FAMILIES:
        if fam in title_lc:
            return 95.0, "fraud_risk"

    # First-class targets: Cybersecurity Analyst, GRC Analyst, etc.
    for fam in (target_families or TARGET_FAMILIES):
        if fam in title_lc:
            return 100.0, "target"

    # Adjacent families (security_engineer etc.) only if JD body mentions security
    has_sec_signal = bool(jd_text and filters.SECURITY_KEYWORDS.search(jd_text))
    for fam in ADJACENT_FAMILIES:
        if fam in title_lc:
            return (60.0 if has_sec_signal else 40.0), "adjacent"

    # Generic "security X" or "compliance X" or "risk X" titles
    if any(w in title_lc for w in ("security", "compliance", "risk", "audit",
                                    "fraud", "trust", "safety")):
        return 30.0, "security_other"
    return 0.0, "off-target"


# --- location scoring ---

REMOTE_RE = re.compile(r"\b(remote|distributed|fully remote|work from anywhere)\b", re.I)
HYBRID_RE = re.compile(r"\bhybrid\b", re.I)


def _location_score(*, location: str,
                     preferred_metros: list[str] | None = None,
                     remote_ok: bool = True,
                     hybrid_ok: bool = True,
                     onsite_ok: bool = True,
                     ) -> float:
    """Per Dillon's 2026-05-05 directive: remote/hybrid is a SMALL bonus, not
    dominant. In-person in a preferred metro is treated as fully acceptable
    (90); fully remote is 100; hybrid is 95.

    The 10-point cap on this dimension at the weighted level keeps the spread
    between in-person and remote tight (<=1 point in the final score)."""
    loc = (location or "").strip().lower()
    if not loc:
        return 70.0   # unknown
    if REMOTE_RE.search(loc):
        return 100.0
    if HYBRID_RE.search(loc):
        return 95.0
    # In-person: accept if any preferred metro matches or onsite_ok
    metros = [m.lower() for m in (preferred_metros or [])]
    if any(m in loc or loc in m for m in metros):
        return 95.0
    # In-person elsewhere: 75 if onsite_ok, 35 otherwise
    return 75.0 if onsite_ok else 35.0


# --- top-level scorer ---

def score_role(*, posting: dict[str, Any], profile_skills: list[str],
                certs_needed_match: bool, target_roles: list[str],
                preferred_metros: list[str] | None = None,
                profile_target_families: list[str] | None = None,
                allowed_locations: list[str] | None = None,
                ) -> RankResult:
    title = posting.get("title") or ""
    body = posting.get("raw_text") or ""
    location = posting.get("location") or ""

    # Experience
    exp = detect_experience_level(title=title, jd_text=body)
    exp_score = _experience_score(exp)

    # Role family
    role_score, role_label = _role_family_score(
        title=title, jd_text=body,
        target_families=profile_target_families,
    )

    # Transferable-experience boost for fraud/identity/trust/risk roles.
    # Dillon has ~1.5 yrs of transferable fraud/identity/account-security/
    # investigation-relevant experience across academic cyber labs, the
    # Dillard's IT/InfoSec internship (PCI audit evidence + SAST reporting),
    # an RJ internship, and applied security projects (centralized logging,
    # phishing labs, evidence review). For these roles we treat his profile
    # as roughly junior-level rather than entry/unknown -- the JDs care
    # about transferable investigation/analysis ability, not formal
    # fraud-job tenure.
    if role_label == "fraud_risk":
        # Lift unknown/entry to junior-equivalent (90); leave higher signals alone.
        if exp.level in ("unknown", "entry"):
            exp_score = max(exp_score, 80.0)
        elif exp.level == "junior":
            exp_score = max(exp_score, 90.0)

    # Skills (reuse the existing quick_fit synonym matcher)
    fit = filters.quick_fit(
        posting=posting, profile_skills=profile_skills,
        certs_needed_match=certs_needed_match, target_roles=target_roles,
    )
    skills_score = float(fit.get("score") or 0)

    # Location
    loc_score = _location_score(
        location=location, preferred_metros=preferred_metros,
    )

    # Interest -- v1 baseline 60 with bumps for likely high-interest signals
    interest = 60.0
    if any(t in title.lower() for t in ("compliance", "audit", "risk", "grc")):
        interest = 80.0  # close to Dillon's lab/coursework strengths
    if "intern" in title.lower():
        interest = 50.0  # not an intern anymore; deprioritize new-grad internships

    # Blockers
    blockers = detect_blockers(
        title=title, jd_text=body, location=location,
        allowed_locations=allowed_locations,
    )
    salary = detect_salary_range(body)

    # Weighted score (35/25/20/10/10)
    weighted = (
        exp_score * 0.35 +
        role_score * 0.25 +
        skills_score * 0.20 +
        loc_score * 0.10 +
        interest * 0.10
    )

    # Adjust for salary signal: high bands get a soft penalty
    if salary.bucket == "mid_senior":
        weighted = max(0.0, weighted - 5.0)
    elif salary.bucket == "senior":
        weighted = max(0.0, weighted - 12.0)

    # Hard blockers cap the score
    has_hard = any(b.severity == "hard" for b in blockers)
    if has_hard:
        category = "Blocker"
        recommendation = "Skip"
    elif exp.level == "senior" or weighted < 35:
        category = "Too Senior" if exp.level == "senior" else "Reach"
        recommendation = "Skip" if weighted < 30 else "Maybe apply"
    elif weighted >= 75 and exp_score >= 70:
        category = "Strong Target"
        recommendation = "Apply"
    elif weighted >= 60 and exp_score >= 60:
        category = "Target"
        recommendation = "Apply"
    elif weighted >= 45:
        category = "Reach"
        recommendation = "Maybe apply"
    else:
        category = "Reach"
        recommendation = "Skip"

    breakdown = FitBreakdown(
        experience=exp_score, role_family=role_score, skills=skills_score,
        location=loc_score, interest=interest, blockers=blockers,
        experience_level=exp.level, salary_bucket=salary.bucket,
        role_family_label=role_label,
    )

    # Reason / risk strings -- short and actionable
    biggest_reason = _format_biggest_reason(role_label, exp.level, role_score, exp_score)
    biggest_risk = _format_biggest_risk(blockers, exp.level, salary.bucket, role_label)
    tailor = (category in ("Strong Target", "Target")) or (
        category == "Reach" and exp_score >= 60
    )
    resume_angle = _resume_angle(role_label, title)
    outreach_angle = _outreach_angle(role_label)

    return RankResult(
        score=int(round(weighted)), category=category,
        biggest_reason=biggest_reason, biggest_risk=biggest_risk,
        tailor_resume=tailor, resume_angle=resume_angle,
        outreach_angle=outreach_angle, recommendation=recommendation,
        breakdown=breakdown,
    )


def _format_biggest_reason(role_label: str, level: str,
                            role_score: float, exp_score: float) -> str:
    if role_label == "target" and level in ("entry", "junior", "target"):
        return f"On-target role family + experience level matches ({level})."
    if role_label == "target":
        return "On-target role family; check seniority of responsibilities."
    if role_label == "adjacent" and exp_score >= 70:
        return "Adjacent role family with security signal in JD; experience level fits."
    if role_label == "security_other":
        return "Security-domain title; review JD for analyst-level scope."
    if level in ("entry", "junior"):
        return f"Experience level fits ({level}); off-target role family."
    return "Mixed signal; read the JD before deciding."


def _format_biggest_risk(blockers: list[Blocker], level: str,
                          salary_bucket: str, role_label: str) -> str:
    if blockers:
        b = blockers[0]
        return f"BLOCKER ({b.kind}): {b.detail}"
    if level == "senior":
        return "Title or JD signals 5+ years / senior responsibilities."
    if level == "mid":
        return "Mid-level signal in title or 3-5 yrs in JD."
    if salary_bucket in ("mid_senior", "senior"):
        return f"Salary band ({salary_bucket}) suggests seniority above target."
    if role_label == "off-target":
        return "Title doesn't match target role families."
    return "No major risk surfaced; still review JD before applying."


def _resume_angle(role_label: str, title: str) -> str:
    title_lc = (title or "").lower()
    # Fraud / identity / trust & safety / risk roles get a dedicated angle:
    # frame the cyber + internship + lab work as transferable investigation /
    # event-review / evidence-collection / risk-decisioning experience,
    # NOT compliance-heavy.
    if role_label == "fraud_risk":
        return (
            "Lead with investigation workflows + event/log review + evidence "
            "collection + risk-based decision-making. Pull from SAST reporting "
            "(suspicious-finding triage), centralized logging lab (auth / "
            "access event review in Graylog/OpenSearch), Dillard's PCI audit "
            "evidence support, academic phishing-analysis labs (suspicious-"
            "activity pattern recognition), and the nonprofit healthcare risk-"
            "mapping engagement. Frame as ~1.5 yrs transferable fraud / "
            "identity / account-security / investigation experience across "
            "labs, internships, and applied security projects -- NOT formal "
            "fraud-specialist tenure. Mention compliance / control mapping as "
            "secondary, not primary."
        )
    if "compliance" in title_lc or "grc" in title_lc or "audit" in title_lc:
        return ("Lead with PCI audit evidence support + ISO 27001 / NIST 800-53 "
                "coursework + control mapping. Subtle FedRAMP ConMon lab line.")
    if "soc" in title_lc or "security operations" in title_lc or "incident" in title_lc:
        return ("Lead with SAST reporting workflow + centralized logging lab "
                "(Graylog/OpenSearch) + log monitoring + IR fundamentals.")
    if "vulnerability" in title_lc:
        return ("Lead with SAST workflow + severity normalization + Wireshark/Nmap "
                "vulnerability scanning lab + remediation tracking.")
    if "cloud" in title_lc:
        return ("Lead with security-control awareness + lab-based system hardening "
                "+ NIST cybersecurity coursework. Note: limited production cloud.")
    if role_label == "target":
        return "Use the broad-cyber resume; emphasize internship + GRC coursework."
    return "Use the broad-cyber resume; tailor lightly to the JD's top skills."


def _outreach_angle(role_label: str) -> str:
    if role_label == "fraud_risk":
        return (
            "Use the fraud/identity/trust/risk outreach variant. Frame "
            "yourself as targeting fraud, identity, trust & safety, risk, "
            "and account-security roles where your cybersecurity background, "
            "internship, and investigation-style project work transfer well. "
            "Cite ~1.5 yrs transferable from labs + internships + applied "
            "security projects (Dillard's PCI audit evidence + SAST "
            "reporting + centralized logging lab + phishing analysis labs)."
        )
    if role_label == "target":
        return ("Lead with internship + GRC coursework; ask for 15-min intro. "
                "Mention specific role family (analyst / GRC / etc.).")
    if role_label == "adjacent":
        return ("Be honest about adjacency. Lead with closest match (Dillard's "
                "internship or labs); ask whether the team has a junior path.")
    return ("General-recruiter template; mention you're targeting cyber / GRC / "
            "sec-ops and ask if the team has roles where this fits.")


def render_role_card(rank: RankResult, posting: dict[str, Any]) -> str:
    """Single-role markdown card with the user-requested output format."""
    title = posting.get("title") or "(role)"
    company = posting.get("company") or "(company)"
    location = posting.get("location") or "(unknown)"
    url = posting.get("url") or ""
    bd = rank.breakdown
    lines = [
        f"### {company} | {title}",
        "",
        f"- **Location:** {location}",
        f"- **Apply:** <{url}>",
        f"- **Fit score:** {rank.score} / 100",
        f"- **Category:** {rank.category}",
        f"- **Biggest reason to apply:** {rank.biggest_reason}",
        f"- **Biggest risk / blocker:** {rank.biggest_risk}",
        f"- **Tailor a resume?** {'Yes' if rank.tailor_resume else 'No'}",
        f"- **Resume angle:** {rank.resume_angle}",
        f"- **Outreach angle:** {rank.outreach_angle}",
        f"- **Recommendation:** {rank.recommendation}",
        f"- **Breakdown:** experience={int(bd.experience)} role={int(bd.role_family)} "
        f"skills={int(bd.skills)} location={int(bd.location)} interest={int(bd.interest)} "
        f"| level={bd.experience_level} salary={bd.salary_bucket} fam={bd.role_family_label}",
    ]
    if bd.blockers:
        lines.append(f"- **Blockers ({len(bd.blockers)}):**")
        for b in bd.blockers:
            lines.append(f"  - [{b.severity}] {b.kind}: {b.detail}")
    return "\n".join(lines)
