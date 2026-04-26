"""The safety net. These tests must catch the failure modes the plan agent
flagged: numeric drift, internship inflation, in-progress degree inflation,
unknown credential invention.
"""
from __future__ import annotations

import pytest

from job_apply.validators import fabrication as fab


PROFILE = {
    "identity": {"full_name": "Test User"},
    "education": [
        {"id": "bs_cis", "school": "X", "degree": "BA Computer Information Systems",
         "status": "in_progress"},
        {"id": "ms_cyber", "school": "Y", "degree": "MS Cybersecurity",
         "status": "in_progress"},
    ],
    "certifications": [
        {"id": "secplus", "name": "CompTIA Security+"},
        {"id": "netplus", "name": "CompTIA Network+"},
    ],
    "experience": [
        {
            "id": "dillards_intern",
            "company": "Dillard's",
            "title": "IT / Information Security Intern",
            "role_type": "internship",
            "summary": "Worked on the IT/Infosec team at Dillard's.",
            "bullets": [
                {"id": "dillards_intern.b1",
                 "text": "Reviewed access requests across the corporate identity system.",
                 "metrics_present": []},
                {"id": "dillards_intern.b2",
                 "text": "Documented incident-response runbooks for the SOC team.",
                 "metrics_present": ["3 runbooks"]},
            ],
        }
    ],
    "skills": {"technical": ["Python", "Linux"], "security": ["SIEM basics"]},
    "metrics_allowed": [],
}


def _seg(source_id: str, text: str) -> fab.CitedSegment:
    return fab.CitedSegment(source_id=source_id, text=text)


# --------- numeric whitelist ----------

def test_numeric_unsourced_percentage_blocks():
    segs = [_seg("experience.dillards_intern.b1",
                 "Reviewed access requests, reducing incident response time by 30%.")]
    rep = fab.validate_segments(segs, PROFILE)
    assert not rep.ok
    assert any(b.rule == "numeric_whitelist" for b in rep.blocks)


def test_numeric_in_metrics_present_passes():
    segs = [_seg("experience.dillards_intern.b2",
                 "Documented 3 runbooks for the SOC team.")]
    rep = fab.validate_segments(segs, PROFILE)
    assert rep.ok, [b.detail for b in rep.blocks]


def test_numeric_in_metrics_allowed_passes():
    profile = {**PROFILE, "metrics_allowed": ["50+ alerts"]}
    segs = [_seg("experience.dillards_intern.b1",
                 "Triaged 50+ alerts during my internship at Dillard's.")]
    # NOTE: still has internship-inflation risk if phrased as years; this phrasing is fine
    rep = fab.validate_segments(segs, profile)
    assert all(b.rule != "numeric_whitelist" for b in rep.blocks)


def test_numeric_dollars_unsourced_blocks():
    segs = [_seg("experience.dillards_intern.b1",
                 "Saved the company $50K in licensing.")]
    rep = fab.validate_segments(segs, PROFILE)
    assert any(b.rule == "numeric_whitelist" for b in rep.blocks)


def test_numeric_years_unsourced_blocks():
    segs = [_seg("experience.dillards_intern.b1",
                 "Brought 2 years of incident-response experience.")]
    rep = fab.validate_segments(segs, PROFILE)
    assert any(b.rule == "numeric_whitelist" for b in rep.blocks)


# --------- internship inflation ----------

def test_internship_to_full_time_blocks():
    segs = [_seg("experience.dillards_intern.b1",
                 "Worked full-time at Dillard's on the security team.")]
    rep = fab.validate_segments(segs, PROFILE)
    assert any(b.rule == "internship_inflation" for b in rep.blocks)


def test_internship_to_years_at_blocks():
    segs = [_seg("experience.dillards_intern.b1",
                 "Spent 2 years at Dillard's hardening the network.")]
    rep = fab.validate_segments(segs, PROFILE)
    assert any(b.rule == "internship_inflation" for b in rep.blocks)


def test_internship_senior_title_blocks():
    segs = [_seg("experience.dillards_intern.b1",
                 "Acted as senior analyst at Dillard's.")]
    rep = fab.validate_segments(segs, PROFILE)
    assert any(b.rule == "internship_inflation" for b in rep.blocks)


def test_internship_phrasing_OK_when_honest():
    segs = [_seg("experience.dillards_intern.b1",
                 "During my internship at Dillard's, I reviewed access requests.")]
    rep = fab.validate_segments(segs, PROFILE)
    assert rep.ok, [b.detail for b in rep.blocks]


# --------- in-progress degree inflation ----------

def test_graduated_in_progress_blocks():
    segs = [_seg("general", "I graduated with a BA Computer Information Systems.")]
    rep = fab.validate_segments(segs, PROFILE)
    assert any(b.rule == "in_progress_degree_inflation" for b in rep.blocks)


def test_holds_degree_in_progress_blocks():
    segs = [_seg("general", "I hold a MS Cybersecurity from State University.")]
    rep = fab.validate_segments(segs, PROFILE)
    assert any(b.rule == "in_progress_degree_inflation" for b in rep.blocks)


def test_completed_in_progress_blocks():
    segs = [_seg("general", "I completed my BA Computer Information Systems last year.")]
    rep = fab.validate_segments(segs, PROFILE)
    assert any(b.rule == "in_progress_degree_inflation" for b in rep.blocks)


def test_in_progress_phrasing_OK():
    segs = [_seg("general", "I am finishing a BA Computer Information Systems and a MS Cybersecurity.")]
    rep = fab.validate_segments(segs, PROFILE)
    assert rep.ok, [b.detail for b in rep.blocks]


def test_holds_BS_softer_form_blocks():
    segs = [_seg("general", "I hold a BS in Information Systems.")]
    profile = {
        **PROFILE,
        "education": [
            {"id": "bs", "school": "X", "degree": "BS Information Systems", "status": "in_progress"}
        ],
    }
    rep = fab.validate_segments(segs, profile)
    assert any(b.rule == "in_progress_degree_inflation" for b in rep.blocks)


# --------- unknown credential ----------

def test_invented_cissp_blocks():
    segs = [_seg("general", "I hold my CISSP and Security+.")]
    rep = fab.validate_segments(segs, PROFILE)
    assert any(b.rule == "unknown_credential" for b in rep.blocks)


def test_invented_aws_cert_blocks():
    segs = [_seg("general", "Pursuing AWS Certified Security Specialty.")]
    rep = fab.validate_segments(segs, PROFILE)
    assert any(b.rule == "unknown_credential" for b in rep.blocks)


def test_real_certs_pass():
    segs = [_seg("general", "Earned CompTIA Security+ and CompTIA Network+ during school.")]
    rep = fab.validate_segments(segs, PROFILE)
    # 'Earned' is fine here since the certs are real (no in-progress status on certs).
    cert_blocks = [b for b in rep.blocks if b.rule == "unknown_credential"]
    assert cert_blocks == []


# --------- soft warnings ----------

def test_strong_adjective_warns_not_blocks():
    segs = [_seg("general", "Senior security professional with deep expertise.")]
    rep = fab.validate_segments(segs, PROFILE)
    # 'senior' would be in STRONG_ADJ -> warning
    rules = {w.rule for w in rep.warnings}
    assert "strong_adjective" in rules


# --------- multi-violation summary ----------

def test_multiple_violations_all_caught():
    segs = [_seg("experience.dillards_intern.b1",
                 "Spent 3 years at Dillard's as a senior analyst with my CISSP, "
                 "reducing alert volume by 40%.")]
    rep = fab.validate_segments(segs, PROFILE)
    rules = {b.rule for b in rep.blocks}
    assert "numeric_whitelist" in rules
    assert "internship_inflation" in rules
    assert "unknown_credential" in rules


# --------- helper: extract_segments_from_packet ----------

def test_extract_segments_pulls_from_all_blocks():
    packet = {"tailored": {
        "summary": "Summary text.",
        "bullets": [{"source_id": "experience.dillards_intern.b1", "text": "Bullet text."}],
        "cover_letter_paragraphs": [{"source_id": "general", "text": "Cover paragraph."}],
        "application_answers": [{"question": "Q?", "source_id": "reusable_answers.x", "answer": "A."}],
    }}
    segs = fab.extract_segments_from_packet(packet)
    sids = [s.source_id for s in segs]
    assert sids.count("general") >= 1  # summary + cover paragraph
    assert "experience.dillards_intern.b1" in sids
    assert "reusable_answers.x" in sids
