from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from job_apply import email_to_self, packet_artifacts, profile_loader


def _packet(**overrides) -> dict:
    base = {
        "job_id": "abc123def456",
        "slug": "acme_security-analyst",
        "validation": {"fabrication_blocks": [], "fabrication_warnings": [],
                       "schema_ok": True},
        "production_status": "portal_ready",
        "strategic_interest": "high",
        "fit_score": 78,
        "run_id": "r-2026-04-26-01",
    }
    base.update(overrides)
    return base


def _analyzed(**overrides) -> dict:
    base = {
        "id": "abc123def456", "company": "Acme Corp", "title": "Security Analyst",
        "location": "Tulsa, OK", "remote_mode": "hybrid",
        "source_url": "https://acme/jobs/sa", "fit_score": 78,
    }
    base.update(overrides)
    return base


def _setup_packet_files(workspace: Path, slug: str = "acme_security-analyst"):
    """Create minimal packet output dir with PDFs."""
    pkt_dir = packet_artifacts._packet_dir(slug)
    employer = pkt_dir / "employer"
    employer.mkdir(parents=True, exist_ok=True)
    (employer / "tailored_resume.pdf").write_bytes(b"%PDF-resume")
    (employer / "cover_letter.pdf").write_bytes(b"%PDF-cover")
    return pkt_dir


def _secrets() -> profile_loader.Secrets:
    return profile_loader.Secrets(data={"email": "dillon@example.com"})


# ---------- _resolve_to_addr ----------

def test_resolve_to_addr_uses_override():
    addr = email_to_self._resolve_to_addr(_secrets(), "override@x.com")
    assert addr == "override@x.com"


def test_resolve_to_addr_falls_back_to_secrets():
    addr = email_to_self._resolve_to_addr(_secrets(), None)
    assert addr == "dillon@example.com"


def test_resolve_to_addr_raises_if_neither():
    with pytest.raises(ValueError, match="no recipient email"):
        email_to_self._resolve_to_addr(profile_loader.Secrets(data={}), None)


# ---------- single-role email ----------

def test_prepare_single_role_email_writes_md_and_assembles_draft(workspace: Path):
    _setup_packet_files(workspace)
    draft = email_to_self.prepare_single_role_email(
        slug="acme_security-analyst", packet=_packet(),
        analyzed=_analyzed(), apply_url="https://acme/jobs/sa",
        secrets=_secrets(),
    )
    assert draft.to_addr == "dillon@example.com"
    assert "Acme Corp" in draft.subject
    assert "Security Analyst" in draft.subject
    # Run id stamped
    assert "[run: r-2026-04-26-01]" in draft.subject
    # PDFs attached
    names = [p.name for p in draft.attachments]
    assert "tailored_resume.pdf" in names
    assert "cover_letter.pdf" in names
    assert draft.md_path.exists()
    md = draft.md_path.read_text()
    assert "Acme Corp" in md
    assert "Security Analyst" in md
    assert "https://acme/jobs/sa" in md
    assert "set-status" in md


def test_prepare_single_role_email_includes_apply_url_attachment(workspace: Path):
    _setup_packet_files(workspace)
    packet_artifacts.write_apply_url(
        "acme_security-analyst", apply_url="https://acme/jobs/sa")
    draft = email_to_self.prepare_single_role_email(
        slug="acme_security-analyst", packet=_packet(),
        analyzed=_analyzed(), apply_url="https://acme/jobs/sa",
        secrets=_secrets(),
    )
    names = [p.name for p in draft.attachments]
    assert "apply_url.txt" in names


def test_prepare_single_role_email_surfaces_blocks(workspace: Path):
    _setup_packet_files(workspace)
    pkt = _packet(validation={
        "fabrication_blocks": ["numeric '40%' not in source"],
        "fabrication_warnings": [],
        "schema_ok": True,
    })
    draft = email_to_self.prepare_single_role_email(
        slug="acme_security-analyst", packet=pkt,
        analyzed=_analyzed(), apply_url="", secrets=_secrets(),
    )
    assert "HARD BLOCKS" in draft.body
    md = draft.md_path.read_text()
    assert "Hard blocks" in md
    assert "numeric '40%' not in source" in md


def test_prepare_single_role_email_handles_no_packet_files(workspace: Path):
    """If tailor hasn't run, the email should still draft with zero attachments."""
    draft = email_to_self.prepare_single_role_email(
        slug="acme_security-analyst", packet=_packet(),
        analyzed=_analyzed(), apply_url="https://x", secrets=_secrets(),
    )
    assert draft.attachments == []
    assert draft.md_path.exists()


# ---------- company-bundle email ----------

def test_prepare_company_bundle_email_2_roles(workspace: Path):
    _setup_packet_files(workspace, slug="acme_security-analyst")
    _setup_packet_files(workspace, slug="acme_soc-analyst")
    draft = email_to_self.prepare_company_bundle_email(
        company="Acme Corp", company_slug="acme",
        role_packets=[_packet(slug="acme_security-analyst"),
                      _packet(slug="acme_soc-analyst", run_id="r2")],
        role_analyzed={
            "acme_security-analyst": _analyzed(),
            "acme_soc-analyst": _analyzed(title="SOC Analyst",
                                            source_url="https://acme/jobs/soc"),
        },
        role_slugs=["acme_security-analyst", "acme_soc-analyst"],
        role_apply_urls={"acme_security-analyst": "https://acme/jobs/sa",
                          "acme_soc-analyst": "https://acme/jobs/soc"},
        secrets=_secrets(),
    )
    assert draft.mode == "company-bundle"
    assert "2 roles" in draft.subject
    assert "Acme Corp" in draft.subject
    # Each role's PDFs in attachments
    names = [p.name for p in draft.attachments]
    assert names.count("tailored_resume.pdf") == 2
    assert names.count("cover_letter.pdf") == 2
    md = draft.md_path.read_text()
    assert "Security Analyst" in md
    assert "SOC Analyst" in md
    assert "https://acme/jobs/sa" in md
    assert "https://acme/jobs/soc" in md
    # Bundle md lives under outputs/<slug>__bundle/internal/
    assert "acme__bundle" in str(draft.md_path)


def test_prepare_company_bundle_email_includes_outreach_when_present(workspace: Path):
    _setup_packet_files(workspace, slug="acme_security-analyst")
    _setup_packet_files(workspace, slug="acme_soc-analyst")
    packet_artifacts.write_company_outreach(
        company="Acme Corp", company_slug="acme",
        roles=[{"title": "Security Analyst", "apply_url": "https://x"},
                {"title": "SOC Analyst", "apply_url": "https://y"}],
    )
    draft = email_to_self.prepare_company_bundle_email(
        company="Acme Corp", company_slug="acme",
        role_packets=[_packet(slug="acme_security-analyst"),
                      _packet(slug="acme_soc-analyst")],
        role_analyzed={
            "acme_security-analyst": _analyzed(),
            "acme_soc-analyst": _analyzed(title="SOC Analyst"),
        },
        role_slugs=["acme_security-analyst", "acme_soc-analyst"],
        secrets=_secrets(),
    )
    names = [p.name for p in draft.attachments]
    assert "company_outreach.md" in names


def test_prepare_company_bundle_email_empty_raises(workspace: Path):
    with pytest.raises(ValueError):
        email_to_self.prepare_company_bundle_email(
            company="Acme", company_slug="acme",
            role_packets=[], role_analyzed={}, role_slugs=[],
        )


def test_prepare_company_bundle_email_misaligned_args_raises(workspace: Path):
    with pytest.raises(ValueError, match="same length"):
        email_to_self.prepare_company_bundle_email(
            company="Acme", company_slug="acme",
            role_packets=[_packet()],
            role_analyzed={},
            role_slugs=["a", "b"],
        )


# ---------- driver ----------

def test_open_in_mail_calls_mail_draft_with_assembled_draft(workspace: Path):
    _setup_packet_files(workspace)
    draft = email_to_self.prepare_single_role_email(
        slug="acme_security-analyst", packet=_packet(),
        analyzed=_analyzed(), apply_url="https://x", secrets=_secrets(),
    )
    with patch("job_apply.mail_draft.open_draft") as mock_open:
        email_to_self.open_in_mail(draft)
        mock_open.assert_called_once()
        kwargs = mock_open.call_args.kwargs
        assert kwargs["to_addr"] == "dillon@example.com"
        assert "Acme Corp" in kwargs["subject"]
        assert kwargs["attachments"] == draft.attachments


def test_open_in_mail_raises_when_no_attachments(workspace: Path):
    """Defensive: refuse to open a draft with zero attachments."""
    from job_apply import mail_draft
    draft = email_to_self.prepare_single_role_email(
        slug="acme_security-analyst", packet=_packet(),
        analyzed=_analyzed(), apply_url="", secrets=_secrets(),
    )
    assert draft.attachments == []
    with pytest.raises(mail_draft.MailDraftError, match="no attachments"):
        email_to_self.open_in_mail(draft)
