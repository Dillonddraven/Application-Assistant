from __future__ import annotations

from pathlib import Path

import pytest

from job_apply import job_ingest


SAMPLE_HTML = """
<html><head><title>Acme - Security Analyst</title></head>
<body>
<header><nav>Home About Jobs</nav></header>
<main>
  <h1>Security Analyst</h1>
  <p>Acme Corp is hiring a Security Analyst to join our SOC team.
     You will triage alerts, run vulnerability scans, and maintain documentation.</p>
  <h2>Requirements</h2>
  <ul>
    <li>CompTIA Security+ or equivalent</li>
    <li>Familiarity with SIEM tools</li>
    <li>0-2 years experience</li>
  </ul>
</main>
<footer>(c) Acme</footer>
</body></html>
"""


def test_ingest_local_html_file_extracts_main_text(workspace: Path):
    p = workspace / "posting.html"
    p.write_text(SAMPLE_HTML)
    result = job_ingest.ingest(str(p))
    assert not result.cached
    text = result.record.text
    assert "Security Analyst" in text
    assert "SOC team" in text
    # Trafilatura should drop boilerplate nav/footer
    assert "Home About Jobs" not in text


def test_ingest_local_text_file_passthrough(workspace: Path):
    p = workspace / "posting.txt"
    p.write_text("Plain Text Posting\n\nWe need a SOC analyst.\n")
    result = job_ingest.ingest(str(p))
    assert "SOC analyst" in result.record.text


def test_ingest_idempotent_for_text_files(workspace: Path):
    p = workspace / "posting.txt"
    p.write_text("Plain Text Posting\n\nWe need a SOC analyst.\n")
    r1 = job_ingest.ingest(str(p))
    r2 = job_ingest.ingest(str(p))
    assert r1.record.job_id == r2.record.job_id
    assert r2.cached is True


def test_ingest_idempotent_for_url(workspace: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(job_ingest, "_fetch_url", lambda url, timeout=30.0: SAMPLE_HTML)
    r1 = job_ingest.ingest("https://acme.example.com/jobs/security-analyst")
    r2 = job_ingest.ingest("https://acme.example.com/jobs/security-analyst")
    assert r1.record.job_id == r2.record.job_id
    assert r2.cached is True
    assert r1.record.source_url == "https://acme.example.com/jobs/security-analyst"


def test_ingest_url_canonicalization_dedupes(workspace: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(job_ingest, "_fetch_url", lambda url, timeout=30.0: SAMPLE_HTML)
    r1 = job_ingest.ingest("https://acme.example.com/jobs/x")
    r2 = job_ingest.ingest("HTTPS://ACME.EXAMPLE.COM/jobs/x")
    assert r1.record.job_id == r2.record.job_id


def test_ingest_missing_file_raises(workspace: Path):
    with pytest.raises(job_ingest.IngestError, match="no such file"):
        job_ingest.ingest("/no/such/path.txt")


def test_refresh_re_saves(workspace: Path, monkeypatch: pytest.MonkeyPatch):
    p = workspace / "posting.txt"
    p.write_text("first body")
    r1 = job_ingest.ingest(str(p))
    p.write_text("first body")  # text identical -> same hash
    r2 = job_ingest.ingest(str(p), refresh=True)
    assert r1.record.job_id == r2.record.job_id
    assert r2.cached is False  # refresh forced re-save
