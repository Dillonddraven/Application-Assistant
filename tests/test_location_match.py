"""Targeted tests for the location_match scoring fix."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from job_apply import job_analyzer, profile_loader


def _profile(*, locations: list[str] = None,
             remote_ok: bool = True, hybrid_ok: bool = True, onsite_ok: bool = True,
             willing_to_relocate: bool = False) -> profile_loader.Profile:
    data = {
        "identity": {"full_name": "T", "citizenship": "US", "work_auth": "yes"},
        "education": [{"id": "x", "school": "X", "degree": "BA CIS",
                       "status": "in_progress"}],
        "preferences": {
            "target_roles": ["Security Analyst"],
            "industries_avoid": [],
            "locations": locations if locations is not None else ["Tulsa, OK"],
            "remote_ok": remote_ok,
            "hybrid_ok": hybrid_ok,
            "onsite_ok": onsite_ok,
            "willing_to_relocate": willing_to_relocate,
        },
    }
    return profile_loader.Profile(data=data)


def _llm(remote_mode: str, location: str = "") -> dict:
    return {
        "required_skills": [], "preferred_skills": [],
        "required_certifications": [], "min_years_experience": 0,
        "remote_mode": remote_mode, "location": location,
        "industry_filter": "ok",
    }


def test_remote_job_remote_ok_gets_100():
    p = _profile(remote_ok=True)
    s = job_analyzer.compute_fit_score(llm_fields=_llm("remote"), profile=p)
    assert s["fit_breakdown"]["location_match"] == 100


def test_remote_job_remote_not_ok_gets_low():
    p = _profile(remote_ok=False)
    s = job_analyzer.compute_fit_score(llm_fields=_llm("remote"), profile=p)
    assert s["fit_breakdown"]["location_match"] == 35


def test_onsite_job_in_my_city_gets_100():
    p = _profile(locations=["Tulsa, OK"])
    s = job_analyzer.compute_fit_score(
        llm_fields=_llm("onsite", "Tulsa, OK"), profile=p,
    )
    assert s["fit_breakdown"]["location_match"] == 100


def test_onsite_job_not_in_my_city_no_relocation_gets_low():
    """The Soro bug: onsite San Diego, candidate in Tulsa, not relocating -> NOT 100."""
    p = _profile(locations=["Tulsa, OK"], willing_to_relocate=False)
    s = job_analyzer.compute_fit_score(
        llm_fields=_llm("onsite", "San Diego, CA"), profile=p,
    )
    assert s["fit_breakdown"]["location_match"] == 25


def test_onsite_job_not_in_my_city_with_relocation_gets_partial():
    p = _profile(locations=["Tulsa, OK"], willing_to_relocate=True)
    s = job_analyzer.compute_fit_score(
        llm_fields=_llm("onsite", "San Diego, CA"), profile=p,
    )
    assert s["fit_breakdown"]["location_match"] == 65


def test_hybrid_job_in_my_city_gets_100():
    p = _profile(locations=["Tulsa, OK"])
    s = job_analyzer.compute_fit_score(
        llm_fields=_llm("hybrid", "Tulsa, OK"), profile=p,
    )
    assert s["fit_breakdown"]["location_match"] == 100


def test_hybrid_job_not_in_my_city_no_relocation_gets_low():
    p = _profile(locations=["Tulsa, OK"], willing_to_relocate=False)
    s = job_analyzer.compute_fit_score(
        llm_fields=_llm("hybrid", "Boston, MA"), profile=p,
    )
    assert s["fit_breakdown"]["location_match"] == 30


def test_unknown_remote_mode_with_intersect_gets_partial():
    """When the posting doesn't say, treat conservatively but credit if location matches."""
    p = _profile(locations=["Tulsa, OK"])
    s = job_analyzer.compute_fit_score(
        llm_fields=_llm("unknown", "Tulsa, OK"), profile=p,
    )
    assert s["fit_breakdown"]["location_match"] == 90


def test_unknown_remote_mode_no_intersect_no_relocate_low():
    """Soro analyzed as 'unknown' remote_mode -> previously got 100, now should be < 70."""
    p = _profile(locations=["Tulsa, OK"], willing_to_relocate=False, remote_ok=True)
    s = job_analyzer.compute_fit_score(
        llm_fields=_llm("unknown", "San Diego, CA"), profile=p,
    )
    assert s["fit_breakdown"]["location_match"] < 70
