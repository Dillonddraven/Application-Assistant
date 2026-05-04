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

    # Dedupe in two passes:
    # 1) URL dedupe across sources (same posting indexed twice).
    # 2) (company, normalized_title) collapse — same role posted to multiple
    #    locations. We keep the first one and stash the others' locations on it
    #    so the queue row reads "Remote / Toronto / Mexico City" instead of
    #    being three separate rows.
    url_dedup: dict[str, dict[str, Any]] = {}
    for p in raw_postings:
        url_key = p.get("url") or f"{p.get('company')}|{p.get('title')}"
        if url_key not in url_dedup:
            url_dedup[url_key] = p
    title_groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for p in url_dedup.values():
        company = (p.get("company") or "").strip().lower()
        title = (p.get("title") or "").strip().lower()
        title_groups.setdefault((company, title), []).append(p)
    after_dedupe: list[dict[str, Any]] = []
    for group in title_groups.values():
        # Keep the first posting; merge other postings' locations into it.
        primary = group[0]
        if len(group) > 1:
            extra_locs = sorted({(p.get("location") or "").strip()
                                  for p in group if (p.get("location") or "").strip()})
            primary = dict(primary)
            primary["location"] = " / ".join(extra_locs[:5])
            if len(extra_locs) > 5:
                primary["location"] += f" (+{len(extra_locs) - 5} more)"
            primary["__multi_location_count"] = len(group)
        after_dedupe.append(primary)

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

        category = _categorize_role(
            title=p.get("title") or "",
            jd_text=p.get("raw_text") or "",
            stretch_flags=fit["stretch_flags"],
            target_roles=target_roles,
        )
        production_status_estimate = _estimate_production_status(fit["score"])
        strategic_interest = _estimate_strategic_interest(fit["score"], category)

        # Two parallel recommendation columns:
        # - recommended_action: legacy, drives the badge color
        # - recommended_next_action: v1-usage; what the user should *do*
        if fit["stretch_flags"]:
            action = "stretch"
            next_action = "save_for_later"
        elif fit["score"] >= 65:
            action = "run_packet"
            next_action = "run_packet"
        elif fit["score"] >= 40:
            action = "save_for_later"
            next_action = "save_for_later"
        else:
            action = "skip"
            next_action = "skip"

        url = p.get("url") or ""
        row = queue.FinderQueueRow(
            company=p.get("company") or "",
            title=p.get("title") or "",
            location=p.get("location") or "",
            ats=p.get("ats") or "",
            url=url,
            quick_fit=fit["score"],
            stretch_flags="; ".join(fit["stretch_flags"]),
            role_category=category,
            recommended_action=action,
            recommended_next_action=next_action,
            production_status_estimate=production_status_estimate,
            strategic_interest=strategic_interest,
            why_matched=_format_why_matched(fit["reasons"]),
            why_risky="; ".join(fit["stretch_flags"]),
            company_group_id=p.get("ats_slug") or (p.get("company") or "").strip().lower(),
            apply_url=url,
            source_url=url,
            review_status="new",
            discovered_date=_dt.date.today().isoformat(),
            review_notes="",
            external_id=p.get("external_id") or "",
        )
        queue_rows.append(row)

    # Merge with any existing queue (preserve user-edited fields)
    existing = queue.load_queue()
    merged = list(existing)
    for new in queue_rows:
        merged = queue.upsert(merged, new)

    # Diversified ranking + grouping (mutates rows in-place, returns reordered)
    merged = queue.diversify(merged)
    # If the user has approved 2+ roles at a single company, mark the
    # outreach_group_id so company-bundle email mode picks them up together.
    _propagate_outreach_groups(merged)
    # Promote next_action to bundle_with_company when the company has multiple
    # high-fit roles (so the user sees one outreach instead of N)
    _promote_bundle_actions(merged)

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


# ---------- helpers used during row construction ----------

def _categorize_role(*, title: str, jd_text: str,
                      stretch_flags: list[str],
                      target_roles: list[str]) -> str:
    """core_security | security_adjacent | stretch | non_core."""
    if not title:
        return "non_core"
    title_lc = title.lower()
    direct_lists = (target_roles or []) + filters.DEFAULT_TITLE_TARGETS
    if any(t.lower() in title_lc for t in direct_lists):
        return "stretch" if stretch_flags else "core_security"
    if any(t in title_lc for t in filters.CONDITIONAL_TITLE_TARGETS):
        if jd_text and filters.SECURITY_KEYWORDS.search(jd_text):
            return "stretch" if stretch_flags else "security_adjacent"
    if stretch_flags:
        return "stretch"
    return "non_core"


def _estimate_production_status(score: int) -> str:
    if score >= 65:
        return "portal_ready"
    if score >= 50:
        return "maybe_review"
    return "skip"


def _estimate_strategic_interest(score: int, category: str) -> str:
    """High = clearly worth the user's energy. Medium = worth a glance.
    Low = fill-in-the-queue. Category modifies the score-only mapping
    (non_core never makes it above 'low')."""
    if category == "non_core":
        return "low"
    if score >= 75:
        return "high"
    if score >= 60:
        return "medium"
    return "low"


def _format_why_matched(reasons: list[str]) -> str:
    """Compact reason string for the queue. Skips the boring negative title
    line so the user only sees the positive signal."""
    keep = [r for r in reasons if not r.startswith("title does not match")]
    return "; ".join(keep[:4])


def _propagate_outreach_groups(rows: list[queue.FinderQueueRow]) -> None:
    """If a row already has an outreach_group_id (user-approved bundle), keep
    it. Otherwise default outreach_group_id == company_group_id when the
    company has 2+ matched rows."""
    by_group: dict[str, list[queue.FinderQueueRow]] = {}
    for r in rows:
        by_group.setdefault(r.company_group_id, []).append(r)
    for gid, group_rows in by_group.items():
        if len(group_rows) >= 2:
            for r in group_rows:
                if not r.outreach_group_id:
                    r.outreach_group_id = gid


def _promote_bundle_actions(rows: list[queue.FinderQueueRow]) -> None:
    """When a company has 2+ rows whose next_action is run_packet, switch
    them to `bundle_with_company` so the user can run one company-bundle
    pack instead of N individual packs."""
    by_group: dict[str, list[queue.FinderQueueRow]] = {}
    for r in rows:
        by_group.setdefault(r.company_group_id, []).append(r)
    for gid, group_rows in by_group.items():
        run_packet_rows = [r for r in group_rows
                            if r.recommended_next_action == "run_packet"]
        if len(run_packet_rows) >= 2:
            for r in run_packet_rows:
                r.recommended_next_action = "bundle_with_company"
