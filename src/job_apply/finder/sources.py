"""Source adapters for the job_finder.

Each source returns a list of normalized `Posting` dicts:

    {
      "company": str,         # human-readable
      "title": str,           # role title
      "location": str,        # "City, ST" or "Remote" or ""
      "url": str,             # public job URL
      "ats": str,             # "greenhouse" / "lever" / etc.
      "ats_slug": str,        # company identifier on that ATS
      "department": str,      # optional, may be empty
      "raw_text": str,        # short JD body if the API returns it
      "discovered_at": str,   # ISO datetime
    }

Both Greenhouse and Lever expose public JSON job-board APIs. No auth needed,
no scraping — these are documented endpoints for the company's own jobs page.
"""
from __future__ import annotations

import datetime as _dt
from typing import Any

import httpx

USER_AGENT = (
    "Mozilla/5.0 (compatible; job-apply-finder/1.0; +https://github.com/your-repo)"
)


def _now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()


def fetch_greenhouse(slug: str, *, timeout: float = 20.0) -> list[dict[str, Any]]:
    """https://boards-api.greenhouse.io/v1/boards/<slug>/jobs?content=true
    Returns Greenhouse's per-company jobs JSON. Public, no auth."""
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
    with httpx.Client(timeout=timeout, headers={"User-Agent": USER_AGENT}) as c:
        r = c.get(url, params={"content": "true"})
        r.raise_for_status()
        data = r.json()
    out: list[dict[str, Any]] = []
    for j in data.get("jobs") or []:
        location = (j.get("location") or {}).get("name", "")
        # Greenhouse exposes a content field with HTML; we strip lightly.
        raw = (j.get("content") or "").strip()
        out.append({
            "company": data.get("name") or slug,
            "title": (j.get("title") or "").strip(),
            "location": location,
            "url": j.get("absolute_url") or "",
            "ats": "greenhouse",
            "ats_slug": slug,
            "department": ", ".join(
                d.get("name", "") for d in (j.get("departments") or [])
            ),
            "raw_text": raw[:8000],   # cap to keep queue rows small
            "external_id": str(j.get("id") or ""),
            "discovered_at": _now_iso(),
        })
    return out


def fetch_lever(slug: str, *, timeout: float = 20.0) -> list[dict[str, Any]]:
    """https://api.lever.co/v0/postings/<slug>?mode=json
    Public per-company postings API."""
    url = f"https://api.lever.co/v0/postings/{slug}"
    with httpx.Client(timeout=timeout, headers={"User-Agent": USER_AGENT}) as c:
        r = c.get(url, params={"mode": "json"})
        r.raise_for_status()
        data = r.json()
    out: list[dict[str, Any]] = []
    if not isinstance(data, list):
        return out
    for j in data:
        cats = j.get("categories") or {}
        out.append({
            "company": (j.get("hostedUrl") or "").split("/")[3] if j.get("hostedUrl") else slug,
            "title": (j.get("text") or "").strip(),
            "location": cats.get("location", ""),
            "url": j.get("hostedUrl") or "",
            "ats": "lever",
            "ats_slug": slug,
            "department": cats.get("department") or cats.get("team") or "",
            "raw_text": ((j.get("descriptionPlain") or "")[:8000]).strip(),
            "external_id": str(j.get("id") or ""),
            "discovered_at": _now_iso(),
        })
    return out


def fetch_for_company(*, ats: str, slug: str) -> list[dict[str, Any]]:
    """Dispatch based on the ATS. Currently supports greenhouse + lever; other
    ATSes will be added later (ashby, workable, smartrecruiters, workday)."""
    if ats == "greenhouse":
        return fetch_greenhouse(slug)
    if ats == "lever":
        return fetch_lever(slug)
    raise NotImplementedError(f"ATS source not yet implemented: {ats}")
