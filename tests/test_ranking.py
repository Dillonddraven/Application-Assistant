from __future__ import annotations

import pytest

from job_apply.finder import seniority, ranking


# -------- experience level --------

def test_detect_senior_from_title():
    sig = seniority.detect_experience_level(
        title="Senior Security Engineer", jd_text="")
    assert sig.level == "senior"


def test_detect_principal_from_title():
    assert seniority.detect_experience_level(
        title="Principal Threat Researcher", jd_text="").level == "senior"


def test_detect_mid_from_intermediate_title():
    assert seniority.detect_experience_level(
        title="Intermediate Vulnerability Researcher", jd_text="").level == "mid"


def test_detect_entry_from_body():
    sig = seniority.detect_experience_level(
        title="Security Analyst", jd_text="This is an entry-level role; new grads encouraged to apply.")
    assert sig.level == "entry"


def test_detect_target_from_2_3_years():
    sig = seniority.detect_experience_level(
        title="Cybersecurity Analyst", jd_text="2-3 years of experience required.")
    assert sig.level == "target"
    assert sig.years_min == 2


def test_detect_senior_from_5_years():
    sig = seniority.detect_experience_level(
        title="Cloud Security Analyst",
        jd_text="5+ years required in cloud security.")
    assert sig.level == "senior"
    assert sig.years_min == 5


def test_detect_unknown_when_no_signal():
    assert seniority.detect_experience_level(
        title="Cybersecurity Analyst", jd_text="").level == "unknown"


# -------- salary --------

def test_salary_target_band():
    s = seniority.detect_salary_range(
        "The base salary range for this role is $80,000 - $105,000.")
    assert s.bucket == "target"
    assert s.min_usd == 80_000 and s.max_usd == 105_000


def test_salary_reach_band():
    s = seniority.detect_salary_range("Salary range: $115,000 - $135,000")
    assert s.bucket == "reach"


def test_salary_mid_senior_band():
    s = seniority.detect_salary_range("Compensation: $145k - $175k")
    assert s.bucket == "mid_senior"
    assert s.min_usd == 145_000 and s.max_usd == 175_000


def test_salary_senior_band():
    s = seniority.detect_salary_range("Pay range $200,000 to $250,000")
    assert s.bucket == "senior"


def test_salary_unknown_when_no_match():
    assert seniority.detect_salary_range("compensation: competitive").bucket == "unknown"


# -------- blockers --------

def test_blocker_language_proficiency():
    body = "Required: professional fluency in Mandarin Chinese."
    bl = seniority.detect_blockers(title="Fraud Analyst", jd_text=body)
    assert any(b.kind == "language" for b in bl)


def test_blocker_aml_kyc_years():
    body = "Must have 3+ years of AML / KYC investigations experience."
    bl = seniority.detect_blockers(title="Compliance Analyst", jd_text=body)
    assert any(b.kind == "aml_kyc_years" for b in bl)


def test_blocker_law_enforcement():
    body = "Prior law enforcement background strongly preferred."
    bl = seniority.detect_blockers(title="Trust & Safety Investigator", jd_text=body)
    assert any(b.kind == "le_background" for b in bl)


def test_blocker_production_ownership():
    body = "You will own the production cloud security program at scale."
    bl = seniority.detect_blockers(title="Security Engineer", jd_text=body)
    assert any(b.kind == "production_ownership" for b in bl)


def test_no_blockers_for_clean_jd():
    body = "Looking for a curious cybersecurity analyst to support the team."
    bl = seniority.detect_blockers(title="Security Analyst", jd_text=body)
    assert bl == []


# -------- ranking.score_role --------

def _posting(**kw):
    base = {"title": "Cybersecurity Analyst", "company": "Acme Corp",
            "raw_text": "Entry-level cybersecurity analyst position.",
            "location": "Remote - USA"}
    base.update(kw)
    return base


def test_score_strong_target_entry_level():
    p = _posting(title="Cybersecurity Analyst",
                  raw_text="Entry-level role; 0-2 years acceptable. Python, security monitoring.")
    r = ranking.score_role(posting=p, profile_skills=["Python", "vulnerability management"],
                            certs_needed_match=True, target_roles=[])
    assert r.category in ("Strong Target", "Target")
    assert r.recommendation == "Apply"
    assert r.breakdown.experience_level in ("entry", "junior")


def test_score_too_senior():
    p = _posting(title="Senior Security Engineer",
                  raw_text="5+ years required in production cloud security.")
    r = ranking.score_role(posting=p, profile_skills=["Python"],
                            certs_needed_match=False, target_roles=[])
    assert r.category in ("Too Senior", "Reach", "Blocker")
    assert r.recommendation in ("Skip", "Maybe apply")


def test_score_blocker_language():
    p = _posting(title="Fraud Analyst",
                  raw_text="Professional fluency in Mandarin required. 1-2 years experience.")
    r = ranking.score_role(posting=p, profile_skills=["Python"],
                            certs_needed_match=False, target_roles=[])
    assert r.category == "Blocker"
    assert r.recommendation == "Skip"
    assert any("language" in b.kind for b in r.breakdown.blockers)


def test_score_blocker_production_ownership():
    p = _posting(title="Cloud Security Engineer",
                  raw_text="You will own the production cloud security program. $150,000 - $200,000.")
    r = ranking.score_role(posting=p, profile_skills=["Python"],
                            certs_needed_match=False, target_roles=[])
    assert r.category == "Blocker"


def test_in_person_role_doesnt_lose_to_remote_by_much():
    """Per Dillon's directive: location flexibility is a SMALL bonus, not
    dominant. An in-person role in a preferred metro should score within
    2 points of an identical remote role."""
    body = "Cybersecurity analyst, 1-2 years experience. Python, security monitoring."
    base_kwargs = dict(profile_skills=["Python", "security monitoring"],
                       certs_needed_match=True, target_roles=[],
                       preferred_metros=["Tulsa", "Dallas"])
    remote = ranking.score_role(
        posting=_posting(location="Remote - USA", raw_text=body), **base_kwargs)
    inperson = ranking.score_role(
        posting=_posting(location="Tulsa, OK", raw_text=body), **base_kwargs)
    delta = remote.score - inperson.score
    assert 0 <= delta <= 2, f"remote-vs-in-person delta too large: {delta}"


def test_role_family_target_match():
    p = _posting(title="GRC Analyst",
                  raw_text="Looking for a GRC analyst to support audits and control mapping.")
    r = ranking.score_role(posting=p, profile_skills=["compliance documentation"],
                            certs_needed_match=False, target_roles=[])
    assert r.breakdown.role_family_label == "target"
    assert "GRC" in r.resume_angle or "compliance" in r.resume_angle.lower() \
           or "audit" in r.resume_angle.lower()


# --- fraud / identity / trust & safety / risk family ---

def test_role_family_fraud_investigator_classified_as_fraud_risk():
    p = _posting(title="Fraud Investigator",
                  raw_text="Investigate suspicious account activity. Entry-level.")
    r = ranking.score_role(posting=p, profile_skills=["log monitoring"],
                            certs_needed_match=False, target_roles=[])
    assert r.breakdown.role_family_label == "fraud_risk"


def test_role_family_fraud_identity_specialist():
    p = _posting(title="Fraud & Identity Specialist (Contract)",
                  raw_text="Review identity-verification cases. 1-2 years.")
    r = ranking.score_role(posting=p, profile_skills=["log monitoring"],
                            certs_needed_match=False, target_roles=[])
    assert r.breakdown.role_family_label == "fraud_risk"


def test_role_family_trust_and_safety_analyst():
    p = _posting(title="Trust & Safety Analyst",
                  raw_text="Review user behavior, evidence collection, risk decisions.")
    r = ranking.score_role(posting=p, profile_skills=[],
                            certs_needed_match=False, target_roles=[])
    assert r.breakdown.role_family_label == "fraud_risk"


def test_role_family_account_security_analyst():
    p = _posting(title="Account Security Analyst",
                  raw_text="Review account takeover patterns. 1+ years.")
    r = ranking.score_role(posting=p, profile_skills=[],
                            certs_needed_match=False, target_roles=[])
    assert r.breakdown.role_family_label == "fraud_risk"


def test_fraud_risk_role_gets_transferable_experience_credit():
    """JD with no explicit experience signal: the fraud/risk family should
    treat Dillon's profile as junior-level (transferable from labs +
    internships) rather than 'unknown'."""
    p = _posting(title="Fraud Investigator", raw_text="Review fraud cases.")
    r = ranking.score_role(posting=p, profile_skills=["log monitoring"],
                            certs_needed_match=False, target_roles=[])
    # Without the boost, exp_score for level=unknown would be 60.
    # With the boost it lifts to >=80.
    assert r.breakdown.experience >= 80
    # And the category should clear into Target territory once paired
    # with a strong role-family signal.
    assert r.category in ("Target", "Strong Target")


def test_fraud_risk_resume_angle_is_investigation_focused():
    """The resume angle for fraud/risk roles should emphasize investigation
    workflows, log/event review, evidence collection -- NOT lead with PCI
    compliance and control mapping."""
    p = _posting(title="Fraud Investigator", raw_text="Investigate fraud.")
    r = ranking.score_role(posting=p, profile_skills=[],
                            certs_needed_match=False, target_roles=[])
    angle = r.resume_angle.lower()
    assert "investigation" in angle
    assert "evidence" in angle
    assert "transferable" in angle
    assert "1.5" in angle


def test_fraud_risk_outreach_angle_is_specific():
    """Fraud/risk outreach should NOT use the generic recruiter template."""
    p = _posting(title="Fraud Investigator", raw_text="Investigate fraud.")
    r = ranking.score_role(posting=p, profile_skills=[],
                            certs_needed_match=False, target_roles=[])
    angle = r.outreach_angle.lower()
    assert "fraud" in angle
    assert "transferable" in angle


def test_compliance_analyst_still_in_target_family_not_fraud_risk():
    """Make sure we didn't accidentally route GRC/compliance into the
    fraud_risk bucket. They should stay in 'target'."""
    p = _posting(title="Compliance Analyst",
                  raw_text="GRC role focused on audits.")
    r = ranking.score_role(posting=p, profile_skills=[],
                            certs_needed_match=False, target_roles=[])
    assert r.breakdown.role_family_label == "target"


def test_role_family_off_target():
    p = _posting(title="Marketing Coordinator", raw_text="Marketing role.")
    r = ranking.score_role(posting=p, profile_skills=["Python"],
                            certs_needed_match=False, target_roles=[])
    assert r.breakdown.role_family_label == "off-target"


def test_render_role_card_includes_user_format():
    """The rendered card should include all the fields the user requested."""
    p = _posting()
    r = ranking.score_role(posting=p, profile_skills=["Python"],
                            certs_needed_match=False, target_roles=[])
    card = ranking.render_role_card(r, p)
    for needed in ("Fit score", "Category", "Biggest reason",
                    "Biggest risk", "Tailor a resume", "Resume angle",
                    "Outreach angle", "Recommendation"):
        assert needed in card
