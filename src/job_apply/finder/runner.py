"""Top-level finder orchestration: load companies.yaml, poll each ATS, dedupe,
score, build the review queue."""
from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from ..config import PROFILE_DIR
from ..profile_loader import Profile
from . import filters, queue, sources

COMPANIES_PATH = PROFILE_DIR / "companies.yaml"


@dataclass
class FinderRunResult:
    queue_rows: list[queue.FinderQueueRow]
    polled_companies: int
    total_postings_seen: int
    after_dedupe: int
    after_filters: int
    dropped_clearance: int
    dropped_stretch: int
    dropped_low_fit: int
    errors: list[dict[str, Any]]


def load_companies(path: Path | None = None) -> list[dict[str, Any]]:
    p = path or COMPANIES_PATH
    if not p.exists():
        return []
    raw = yaml.safe_load(p.read_text()) or {}
    return list(raw.get("companies") or [])


def _profile_skill_list(profile: Profile) -> list[str]:
    out: list[str] = []
    for v in (profile.data.get("skills") or {}).values():
        if isinstance(v, list):
            out.extend(s for s in v if isinstance(s, str))
    return out


def _profile_certs(profile: Profile) -> list[str]:
    return [c.get("name", "") for c in profile.data.get("certifications") or []
            if isinstance(c, dict)]


def _certs_match(posting: dict[str, Any], profile_certs: list[str]) -> bool:
    """Crude: does the JD text mention Network+ / Security+ / etc.?"""
    text = (posting.get("raw_text") or "").lower()
    for cn in profile_certs:
        if not cn:
            continue
        # "CompTIA Security+" — check both the abbreviation and 'Security+'
        if cn.lower() in text:
            return True
        # Allow 'Sec+' / 'Net+' shorthand
        short = cn.replace("CompTIA ", "").lower()
        if short and short in text:
            return True
    return False


def run_finder(
    *,
    profile: Profile,
    allow_stretch: bool = False,
    companies_path: Path | None = None,
) -> FinderRunResult:
    """Poll all configured sources, dedupe, score, persist queue. Returns
    the summary + queue rows.

    `allow_stretch=True` keeps senior/lead postings in the queue tagged as
    `stretch` (rather than dropping them). Default is False (drop them)."""
    companies = load_companies(companies_path)
    profile_skills = _profile_skill_list(profile)
    profile_certs = _profile_certs(profile)
    target_roles = (profile.data.get("preferences") or {}).get("target_roles") or []
    industries_avoid = [
        s.lower() for s in
        (profile.data.get("preferences") or {}).get("industries_avoid") or []
    ]

    polled = 0
    seen = 0
    errors: list[dict[str, Any]] = []
    raw_postings: list[dict[str, Any]] = []

    for c in companies:
        ats = c.get("ats")
        slug = c.get("slug")
        if not ats or not slug:
            continue
        try:
            postings = sources.fetch_for_company(ats=ats, slug=slug)
            polled += 1
            seen += len(postings)
            raw_postings.extend(postings)
        except NotImplementedError as e:
            errors.append({"company": c.get("name"), "error": str(e), "fatal": False})
        except Exception as e:
            errors.append({"company": c.get("name"), "error": str(e), "fatal": True})

    # Dedupe by URL (Greenhouse + Lever each give canonical URLs)
    dedup: dict[str, dict[str, Any]] = {}
    for p in raw_postings:
        key = p.get("url") or f"{p.get('company')}|{p.get('title')}"
        if key not in dedup:
            dedup[key] = p
    after_dedupe = list(dedup.values())

    # Filter + score
    queue_rows: list[queue.FinderQueueRow] = []
    dropped_clearance = 0
    dropped_stretch = 0
    dropped_low_fit = 0

    for p in after_dedupe:
        # Industry-avoid keyword filter on title + raw text
        haystack = f"{p.get('title') or ''} {p.get('company') or ''}".lower()
        if any(av in haystack for av in industries_avoid):
            continue

        certs_match = _certs_match(p, profile_certs)
        fit = filters.quick_fit(
            posting=p, profile_skills=profile_skills,
            certs_needed_match=certs_match, target_roles=target_roles,
        )
        drop, drop_reason = filters.should_drop(
            p, fit=fit, allow_stretch=allow_stretch,
        )
        if drop:
            if "clearance" in drop_reason.lower():
                dropped_clearance += 1
            elif "senior" in drop_reason.lower() or "year" in drop_reason.lower():
                dropped_stretch += 1
            else:
                dropped_low_fit += 1
            continue

        # Determine recommendation tier for the queue
        if fit["stretch_flags"]:
            action = "stretch"
        elif fit["score"] >= 65:
            action = "run_packet"
        elif fit["score"] >= 40:
            action = "save_for_later"
        else:
            action = "skip"

        row = queue.FinderQueueRow(
            company=p.get("company") or "",
            title=p.get("title") or "",
            location=p.get("location") or "",
            ats=p.get("ats") or "",
            url=p.get("url") or "",
            quick_fit=fit["score"],
            stretch_flags="; ".join(fit["stretch_flags"]),
            recommended_action=action,
            review_status="new",
            discovered_date=_dt.date.today().isoformat(),
            review_notes="",
            external_id=p.get("external_id") or "",
        )
        queue_rows.append(row)

    # Merge with any existing queue (preserve user-edited review_status/notes)
    existing = queue.load_queue()
    merged = list(existing)
    for new in queue_rows:
        merged = queue.upsert(merged, new)
    queue.save_queue(merged)

    return FinderRunResult(
        queue_rows=merged,
        polled_companies=polled,
        total_postings_seen=seen,
        after_dedupe=len(after_dedupe),
        after_filters=len(queue_rows),
        dropped_clearance=dropped_clearance,
        dropped_stretch=dropped_stretch,
        dropped_low_fit=dropped_low_fit,
        errors=errors,
    )
