from __future__ import annotations

from job_apply.validators.schema import validate_analyzed, validate_packet


def _good_analyzed() -> dict:
    return {
        "id": "abc123def456",
        "source_url": None,
        "fetched_at": "2026-04-26T00:00:00+00:00",
        "raw_text_path": "x",
        "company": "Acme",
        "title": "Security Analyst",
        "location": "Tulsa, OK",
        "remote_mode": "hybrid",
        "required_skills": ["python"],
        "preferred_skills": [],
        "min_years_experience": 1,
        "required_certifications": [],
        "responsibilities": ["triage alerts"],
        "keywords_extracted": ["soc"],
        "industry_tags": ["cybersecurity"],
        "industry_filter": "ok",
        "fit_score": 72,
        "fit_breakdown": {},
        "fit_rationale": "good fit",
        "concerns": [],
        "missing_quals": [],
        "prompt_version": "analyze_job@v1",
        "model": "gpt-4.1-mini",
    }


def test_valid_analyzed_passes():
    assert validate_analyzed(_good_analyzed()) == []


def test_missing_fields_caught():
    bad = _good_analyzed()
    del bad["fit_score"]
    errs = validate_analyzed(bad)
    assert any("fit_score" in e for e in errs)


def test_remote_mode_enum():
    bad = _good_analyzed()
    bad["remote_mode"] = "anywhere"
    errs = validate_analyzed(bad)
    assert any("remote_mode" in e for e in errs)


def test_industry_filter_enum():
    bad = _good_analyzed()
    bad["industry_filter"] = "skip"
    errs = validate_analyzed(bad)
    assert any("industry_filter" in e for e in errs)


def test_fit_score_range():
    bad = _good_analyzed()
    bad["fit_score"] = 150
    errs = validate_analyzed(bad)
    assert any("fit_score" in e for e in errs)


def _good_packet() -> dict:
    return {
        "job_id": "abc",
        "slug": "acme_security-analyst",
        "tailored": {
            "summary": "x",
            "skills": ["python"],
            "bullets": [{"source_id": "experience.dillards.b1", "text": "did things"}],
        },
        "rendered": {},
        "validation": {"fabrication_blocks": [], "fabrication_warnings": [], "schema_ok": True},
        "status": "draft",
        "approval_log": [],
        "prompt_versions": {"tailor": "tailor_resume@v1"},
        "model": "gpt-5.2-mini",
    }


def test_valid_packet_passes():
    assert validate_packet(_good_packet()) == []


def test_packet_status_enum():
    bad = _good_packet()
    bad["status"] = "sent"
    errs = validate_packet(bad)
    assert any("status" in e for e in errs)


def test_packet_bullet_requires_source_id():
    bad = _good_packet()
    bad["tailored"]["bullets"][0].pop("source_id")
    errs = validate_packet(bad)
    assert any("source_id" in e for e in errs)
