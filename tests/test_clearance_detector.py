"""Tests for the deterministic clearance / export-control auto-skip detector."""
from __future__ import annotations

from job_apply.job_analyzer import detect_clearance_requirement


def test_ts_sci_detected():
    text = "This role requires an active TS/SCI clearance and must be a US citizen."
    r = detect_clearance_requirement(text)
    assert r["required"] is True
    labels = [m["pattern"] for m in r["matches"]]
    assert any("TS/SCI" in l for l in labels)


def test_top_secret_clearance_detected():
    text = "Candidates must possess an active Top Secret clearance prior to start."
    r = detect_clearance_requirement(text)
    assert r["required"] is True


def test_secret_clearance_detected():
    text = (
        "We are looking for an analyst with an active Secret clearance "
        "to support our DoD client."
    )
    r = detect_clearance_requirement(text)
    assert r["required"] is True


def test_polygraph_detected():
    text = "Successful candidates will undergo a counterintelligence polygraph."
    r = detect_clearance_requirement(text)
    assert r["required"] is True
    assert any("polygraph" in m["pattern"].lower() for m in r["matches"])


def test_must_hold_clearance_detected():
    text = "The candidate must hold an active US government security clearance."
    r = detect_clearance_requirement(text)
    assert r["required"] is True


def test_clearance_eligible_detected():
    text = "Position is clearance-eligible. Citizenship verification required."
    r = detect_clearance_requirement(text)
    assert r["required"] is True


def test_itar_detected():
    text = "Per ITAR regulations, this role is open only to U.S. persons."
    r = detect_clearance_requirement(text)
    assert r["required"] is True
    assert any("ITAR" in m["pattern"] for m in r["matches"])


def test_export_controlled_detected():
    text = "This role involves export-controlled technology."
    r = detect_clearance_requirement(text)
    assert r["required"] is True


def test_civilian_role_not_flagged():
    text = (
        "We're a SaaS company hiring a SOC analyst. You'll triage Splunk alerts, "
        "investigate phishing reports, and write incident summaries. CompTIA "
        "Security+ preferred. Hybrid in Austin, TX."
    )
    r = detect_clearance_requirement(text)
    assert r["required"] is False
    assert r["matches"] == []


def test_field_aware_detection():
    """Clearance can also appear in extracted fields, not just raw text."""
    text = "Looking for a security analyst to join our team."
    fields = {
        "required_skills": ["Python", "Active Top Secret clearance", "Splunk"],
        "responsibilities": ["triage alerts"],
    }
    r = detect_clearance_requirement(text, fields)
    assert r["required"] is True


def test_dedupes_by_pattern():
    """Multiple sentences mentioning the same clearance only flag once per pattern."""
    text = (
        "Active TS/SCI required. Candidates must have an active TS/SCI to apply. "
        "We'll verify your TS/SCI during onboarding."
    )
    r = detect_clearance_requirement(text)
    pat_labels = [m["pattern"] for m in r["matches"]]
    # Only one TS/SCI label
    assert sum(1 for l in pat_labels if "TS/SCI" in l) == 1


def test_snippet_includes_context():
    text = (
        "We're a defense contractor. You will work on classified systems and "
        "must hold an active Secret clearance. Other tasks include reviewing logs."
    )
    r = detect_clearance_requirement(text)
    assert r["required"] is True
    snippet = r["matches"][0]["snippet"]
    assert "clearance" in snippet.lower()


def test_lowercase_clearance_detected():
    """Detection must be case-insensitive."""
    text = "must hold an active secret clearance"
    r = detect_clearance_requirement(text)
    assert r["required"] is True


def test_able_to_obtain_clearance_flagged():
    """'Able to obtain a clearance' is also a hard barrier for someone without one."""
    text = "Candidate must be able to obtain a Secret clearance after hire."
    r = detect_clearance_requirement(text)
    assert r["required"] is True
