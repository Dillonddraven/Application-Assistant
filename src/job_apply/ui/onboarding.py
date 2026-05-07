"""Guided profile-builder. Asks a non-technical user a small set of
questions and writes a complete master_profile.yaml + secrets.yaml
(both truth-safe, both gitignored) into the user's data dir."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class OnboardingAnswers:
    # Identity
    full_name: str = ""
    citizenship: str = "US Citizen"
    work_auth: str = "Authorized to work in the US, no sponsorship required"
    pronouns: str = ""
    # Contact (PII -- goes in secrets.yaml)
    email: str = ""
    phone: str = ""
    address_city: str = ""
    address_state: str = ""
    linkedin_url: str = ""
    github_url: str = ""
    # Education
    schools: list[dict[str, Any]] = field(default_factory=list)
    # Certifications
    certifications: list[dict[str, str]] = field(default_factory=list)
    # Experience (free-form for v0; user can refine via the Setup tab)
    most_recent_role_company: str = ""
    most_recent_role_title: str = ""
    most_recent_role_summary: str = ""
    most_recent_role_start: str = ""
    most_recent_role_end: str = ""
    most_recent_role_type: str = "internship"   # internship|fulltime|contract|project
    # Skills
    technical_skills: list[str] = field(default_factory=list)
    security_skills: list[str] = field(default_factory=list)
    # Preferences
    target_roles: list[str] = field(default_factory=list)
    workplace_modes: list[str] = field(default_factory=lambda: ["remote", "hybrid"])
    locations: list[str] = field(default_factory=list)
    willing_to_relocate: bool = True
    industries_avoid: list[str] = field(default_factory=list)
    salary_min: int | None = None


# --- field options surfaced in the UI ---

DEFAULT_TARGET_ROLES = [
    "Cybersecurity Analyst",
    "Security Analyst",
    "SOC Analyst",
    "GRC Analyst",
    "Compliance Analyst",
    "Risk Analyst",
    "Vulnerability Management Analyst",
    "IT Security Analyst",
    "Cloud Security Analyst",
    "Threat Intelligence Analyst",
    "Trust & Safety Analyst",
    "Fraud Investigator",
    "Fraud & Identity Specialist",
    "Identity Verification Analyst",
    "Application Security Analyst",
    "Security Operations Analyst",
    "IT Support / Help Desk",
    "Junior Software Engineer",
    "Backend Engineer (junior)",
    "Data Analyst",
    "Business Analyst",
    "Project Coordinator",
]

DEFAULT_TECHNICAL_SKILLS = [
    "Python", "JavaScript", "Java", "C++", "Go", "Bash", "SQL",
    "PowerShell", "PHP", "Ruby", "TypeScript",
    "Linux administration", "Windows Server", "macOS",
    "Docker", "Kubernetes", "AWS", "Azure", "GCP",
    "Git", "GitLab", "GitHub", "Jenkins",
    "REST APIs", "JSON", "YAML",
]

DEFAULT_SECURITY_SKILLS = [
    "Vulnerability management", "SAST", "DAST", "Security monitoring",
    "Incident response fundamentals", "Phishing analysis (lab)",
    "Log analysis", "SIEM concepts", "Wireshark", "Nmap",
    "PCI compliance support", "ISO 27001 concepts", "NIST cybersecurity concepts",
    "NIST SP 800-53", "NIST SP 800-171 / CMMC",
    "Risk assessment", "Compliance documentation",
    "Identity & access management",
    "Investigation workflows (transferable)",
    "Evidence review for risk decisions (transferable)",
]

DEFAULT_INDUSTRIES_AVOID = ["military", "defense", "weapons"]


def to_profile_yaml(a: OnboardingAnswers) -> str:
    """Return the master_profile.yaml content for the answers. Truth-safe:
    every entry traces to user-supplied input."""
    education = [
        {
            "id": s.get("id") or f"edu_{i+1}",
            "school": s.get("school", ""),
            "degree": s.get("degree", ""),
            "status": s.get("status", "in_progress"),
            "start": s.get("start", ""),
            "expected_end": s.get("expected_end", ""),
            "gpa": None,
            "honors": [],
        }
        for i, s in enumerate(a.schools)
    ]
    certs = [
        {
            "id": c.get("id") or f"cert_{i+1}",
            "name": c.get("name", ""),
            "issued": c.get("issued") or None,
            "expires": None,
            "credential_id": None,
        }
        for i, c in enumerate(a.certifications)
    ]
    experience = []
    if a.most_recent_role_company and a.most_recent_role_title:
        experience.append({
            "id": "primary_role",
            "company": a.most_recent_role_company,
            "title": a.most_recent_role_title,
            "role_type": a.most_recent_role_type or "internship",
            "location": "",
            "start": a.most_recent_role_start or "",
            "end": a.most_recent_role_end or "",
            "summary": a.most_recent_role_summary or "",
            "bullets": [],
        })

    profile_data = {
        "identity": {
            "full_name": a.full_name,
            "pronouns": a.pronouns or None,
            "citizenship": a.citizenship,
            "work_auth": a.work_auth,
        },
        "education": education,
        "certifications": certs,
        "experience": experience,
        "projects": [],
        "skills": {
            "technical": a.technical_skills,
            "security": a.security_skills,
            "systems": [],
            "cloud_security": [],
        },
        "preferences": {
            "target_roles": a.target_roles,
            "locations": a.locations,
            "remote_ok": "remote" in a.workplace_modes,
            "hybrid_ok": "hybrid" in a.workplace_modes,
            "onsite_ok": "in-person" in a.workplace_modes,
            "willing_to_relocate": a.willing_to_relocate,
            "preferred_metros": a.locations,
            "industries_avoid": a.industries_avoid,
            "visa_sponsorship_needed": False,
            "salary_min": a.salary_min,
        },
        "reusable_answers": {
            "authorized_to_work": a.work_auth,
            "willing_to_relocate": (
                f"Open to relocation for the right role; based in "
                f"{a.address_city or '(your city)'}, {a.address_state or '(state)'}."
                if a.willing_to_relocate else
                "Prefer roles in or remote-friendly to my current city."
            ),
            "years_of_experience": (
                f"Internship-level + project-heavy. Most recent role: "
                f"{a.most_recent_role_title} at {a.most_recent_role_company}."
                if a.most_recent_role_title else
                "Internship-level + project-heavy."
            ),
            "why_this_company": "",
            "why_security": "",
        },
        "writing_style": {
            "tone": "natural, sharp, professional; concrete and hands-on; not corporate, not robotic, not exaggerated, not spammy",
            "forbidden_phrases": [
                "passionate", "synergy", "rockstar", "ninja",
                "proven track record", "results-driven", "go-getter",
                "thought leader", "move the needle", "circle back",
            ],
            "must_avoid_overclaim": [
                "Senior security engineer experience",
                "Full-time multi-year SOC analyst experience",
                "Production enterprise ownership beyond what's listed",
            ],
            "safe_phrasing_for_adjacent_skills": [
                "Hands-on exposure to...", "Built lab environments involving...",
                "Supported workflows related to...", "Coursework and project experience with...",
                "Familiar with...",
            ],
        },
        "metrics_allowed": [],
        "needs_confirmation": [],
    }
    return yaml.dump(profile_data, sort_keys=False, default_flow_style=False)


def to_secrets_yaml(a: OnboardingAnswers) -> str:
    """secrets.yaml content. NEVER sent to LLM."""
    secrets_data = {
        "email": a.email,
        "phone": a.phone,
        "address_city": a.address_city,
        "address_state": a.address_state,
        "linkedin_url": a.linkedin_url,
        "github_url": a.github_url,
    }
    # Drop empty values for cleanliness
    secrets_data = {k: v for k, v in secrets_data.items() if v}
    return yaml.dump(secrets_data, sort_keys=False, default_flow_style=False)


def write_profile(user_dir: Path, a: OnboardingAnswers) -> tuple[Path, Path]:
    profile_dir = user_dir / "profile"
    profile_dir.mkdir(parents=True, exist_ok=True)
    pp = profile_dir / "master_profile.yaml"
    sp = profile_dir / "secrets.yaml"
    pp.write_text(to_profile_yaml(a), encoding="utf-8")
    sp.write_text(to_secrets_yaml(a), encoding="utf-8")
    return pp, sp
