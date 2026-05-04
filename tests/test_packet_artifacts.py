from __future__ import annotations

from pathlib import Path

from job_apply import packet_artifacts


def _packet(**overrides) -> dict:
    base = {
        "job_id": "abc123def456",
        "slug": "acme_security-analyst",
        "validation": {"fabrication_blocks": [], "fabrication_warnings": [],
                       "schema_ok": True},
        "production_status": "portal_ready",
        "strategic_interest": "high",
        "fit_score": 78,
    }
    base.update(overrides)
    return base


def _analyzed(**overrides) -> dict:
    base = {
        "id": "abc123def456", "company": "Acme Corp", "title": "Security Analyst",
        "location": "Tulsa, OK", "remote_mode": "hybrid",
        "source_url": "https://acme.example.com/jobs/sa", "fit_score": 78,
    }
    base.update(overrides)
    return base


def test_write_apply_url_creates_file(workspace: Path):
    p = packet_artifacts.write_apply_url(
        "acme_security-analyst",
        apply_url="https://acme.example.com/jobs/sa")
    assert p.exists()
    assert p.read_text().strip() == "https://acme.example.com/jobs/sa"


def test_write_apply_url_handles_empty(workspace: Path):
    p = packet_artifacts.write_apply_url("acme_security-analyst", apply_url="")
    assert p.exists()
    assert p.read_text() == "\n"


def test_write_readme_apply_includes_company_and_url(workspace: Path):
    p = packet_artifacts.write_readme_apply(
        slug="acme_security-analyst",
        packet=_packet(),
        analyzed=_analyzed(),
        apply_url="https://acme.example.com/jobs/sa",
    )
    text = p.read_text()
    assert "Acme Corp" in text
    assert "Security Analyst" in text
    assert "Tulsa, OK" in text
    assert "https://acme.example.com/jobs/sa" in text
    assert "Apply checklist" in text
    assert "set-status" in text   # post-submit step
    # URL also written to apply_url.txt next to it
    pkt_dir = p.parent.parent
    assert (pkt_dir / "internal" / "README_APPLY.md").exists()


def test_write_readme_apply_surfaces_blocks_and_warnings(workspace: Path):
    pkt = _packet(validation={
        "fabrication_blocks": ["numeric '40%' not in source"],
        "fabrication_warnings": ["skill 'Splunk' is adjacent but not exact"],
        "schema_ok": True,
    })
    p = packet_artifacts.write_readme_apply(
        slug="acme_security-analyst",
        packet=pkt, analyzed=_analyzed(),
        apply_url="https://acme.example.com/jobs/sa",
    )
    text = p.read_text()
    assert "Hard blocks" in text
    assert "numeric '40%' not in source" in text
    assert "Soft warnings" in text
    assert "Splunk" in text


def test_write_readme_apply_lists_only_existing_files(workspace: Path):
    """If the employer dir is empty, the file checklist should reflect that
    rather than printing dead links."""
    p = packet_artifacts.write_readme_apply(
        slug="acme_security-analyst",
        packet=_packet(), analyzed=_analyzed(),
        apply_url="https://acme.example.com/jobs/sa",
    )
    text = p.read_text()
    assert "no files generated yet" in text


def test_write_readme_apply_includes_real_files_when_present(workspace: Path):
    pkt_root = packet_artifacts._packet_dir("acme_security-analyst")
    employer = pkt_root / "employer"
    internal = pkt_root / "internal"
    employer.mkdir(parents=True, exist_ok=True)
    internal.mkdir(parents=True, exist_ok=True)
    (employer / "tailored_resume.pdf").write_bytes(b"%PDF-fake")
    (employer / "cover_letter.pdf").write_bytes(b"%PDF-fake")
    (internal / "application_answers.md").write_text("# answers")
    p = packet_artifacts.write_readme_apply(
        slug="acme_security-analyst",
        packet=_packet(), analyzed=_analyzed(),
        apply_url="https://acme.example.com/jobs/sa",
    )
    text = p.read_text()
    assert "tailored_resume.pdf" in text
    assert "cover_letter.pdf" in text
    assert "application_answers.md" in text


def test_write_company_outreach_single_role(workspace: Path):
    p = packet_artifacts.write_company_outreach(
        company="Acme Corp", company_slug="acme",
        roles=[{"title": "Security Analyst", "apply_url": "https://acme/jobs/1",
                "location": "Tulsa, OK", "fit_score": 78}],
    )
    text = p.read_text()
    assert "Acme Corp" in text
    assert "Security Analyst" in text
    assert "1 role" in text
    assert "https://acme/jobs/1" in text
    # Single-role intro phrasing
    assert "a role posted" in text


def test_write_company_outreach_bundle(workspace: Path):
    p = packet_artifacts.write_company_outreach(
        company="Acme Corp", company_slug="acme",
        roles=[
            {"title": "Security Analyst", "apply_url": "https://acme/jobs/1",
             "location": "Tulsa, OK", "fit_score": 78},
            {"title": "SOC Analyst", "apply_url": "https://acme/jobs/2",
             "location": "Remote", "fit_score": 72},
        ],
    )
    text = p.read_text()
    assert "Acme Corp" in text
    assert "2 roles" in text
    assert "Security Analyst" in text
    assert "SOC Analyst" in text
    # Bundle intro phrasing
    assert "two roles posted" in text
    # Path lives under <slug>__bundle
    assert "acme__bundle" in str(p)


def test_write_company_outreach_uses_pii_placeholders(workspace: Path):
    """Outreach must use {{full_name}} / {{email}} / {{phone}} placeholders,
    never hardcode any candidate identity. PII substitution happens at send
    time, not at draft time."""
    p = packet_artifacts.write_company_outreach(
        company="Acme Corp", company_slug="acme",
        roles=[{"title": "Security Analyst", "apply_url": "https://x"}],
    )
    text = p.read_text()
    assert "{{full_name}}" in text
    assert "{{email}}" in text
    assert "{{phone}}" in text
    assert "{{linkedin_url}}" in text
    assert "{{first_name}}" in text


def test_write_company_outreach_empty_roles_raises(workspace: Path):
    import pytest
    with pytest.raises(ValueError):
        packet_artifacts.write_company_outreach(
            company="Acme", company_slug="acme", roles=[])
