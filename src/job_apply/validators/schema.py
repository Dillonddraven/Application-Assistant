"""Lightweight schema validators for analyzed jobs and packets.

We avoid jsonschema as a dependency; the schemas are small enough that a
hand-rolled walker is clearer. Each validator returns a list of error
strings; empty list = OK.
"""
from __future__ import annotations

from typing import Any

ANALYZED_REQUIRED_FIELDS: dict[str, type | tuple[type, ...]] = {
    "id": str,
    "fetched_at": str,
    "company": str,
    "title": str,
    "remote_mode": str,
    "required_skills": list,
    "preferred_skills": list,
    "min_years_experience": int,
    "required_certifications": list,
    "responsibilities": list,
    "keywords_extracted": list,
    "industry_tags": list,
    "industry_filter": str,
    "fit_score": int,
    "fit_breakdown": dict,
    "fit_rationale": str,
    "concerns": list,
    "missing_quals": list,
    "prompt_version": str,
    "model": str,
}

ALLOWED_REMOTE_MODES = {"remote", "hybrid", "onsite", "unknown"}
ALLOWED_INDUSTRY_FILTER = {"ok", "avoid", "review"}


def validate_analyzed(data: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    for field, expected in ANALYZED_REQUIRED_FIELDS.items():
        if field not in data:
            errs.append(f"missing field: {field}")
            continue
        if not isinstance(data[field], expected):
            errs.append(f"{field}: expected {expected.__name__ if isinstance(expected, type) else expected}, got {type(data[field]).__name__}")
    if data.get("remote_mode") not in ALLOWED_REMOTE_MODES:
        errs.append(f"remote_mode must be one of {ALLOWED_REMOTE_MODES}, got {data.get('remote_mode')!r}")
    if data.get("industry_filter") not in ALLOWED_INDUSTRY_FILTER:
        errs.append(f"industry_filter must be one of {ALLOWED_INDUSTRY_FILTER}, got {data.get('industry_filter')!r}")
    score = data.get("fit_score")
    if isinstance(score, int) and not (0 <= score <= 100):
        errs.append(f"fit_score out of [0,100]: {score}")
    return errs


PACKET_REQUIRED_FIELDS = {
    "job_id": str,
    "slug": str,
    "tailored": dict,
    "rendered": dict,
    "validation": dict,
    "status": str,
    "approval_log": list,
    "prompt_versions": dict,
    "model": str,
}

ALLOWED_STATUS = {"draft", "approved", "skipped"}


def validate_packet(data: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    for field, expected in PACKET_REQUIRED_FIELDS.items():
        if field not in data:
            errs.append(f"missing field: {field}")
            continue
        if not isinstance(data[field], expected):
            errs.append(f"{field}: expected {expected.__name__}, got {type(data[field]).__name__}")
    if data.get("status") not in ALLOWED_STATUS:
        errs.append(f"status must be one of {ALLOWED_STATUS}, got {data.get('status')!r}")
    tailored = data.get("tailored", {})
    if isinstance(tailored, dict):
        bullets = tailored.get("bullets", [])
        if not isinstance(bullets, list):
            errs.append("tailored.bullets: expected list")
        else:
            for i, b in enumerate(bullets):
                if not isinstance(b, dict):
                    errs.append(f"tailored.bullets[{i}]: expected object")
                    continue
                if "source_id" not in b or not isinstance(b.get("source_id"), str):
                    errs.append(f"tailored.bullets[{i}]: missing string source_id")
                if "text" not in b or not isinstance(b.get("text"), str):
                    errs.append(f"tailored.bullets[{i}]: missing string text")
    return errs
