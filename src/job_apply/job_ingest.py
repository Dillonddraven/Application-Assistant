"""Ingest a job posting from a URL or local file.

Idempotent: re-running with the same URL/file is a no-op unless --refresh.
URL fetch uses httpx; main-text extraction uses trafilatura. For local files
we read the bytes and treat them as already-clean text.

We do NOT touch the LLM here — analyzer.py owns all LLM work.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from . import state

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


class IngestError(RuntimeError):
    pass


@dataclass
class IngestResult:
    record: state.IngestRecord
    cached: bool


def _looks_like_url(s: str) -> bool:
    s = s.strip().lower()
    return s.startswith("http://") or s.startswith("https://")


def _fetch_url(url: str, timeout: float = 30.0) -> str:
    import httpx  # local import keeps import-time cheap and tests can stub
    with httpx.Client(
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
        timeout=timeout,
    ) as client:
        r = client.get(url)
        r.raise_for_status()
        return r.text


def _extract_main_text(html_or_text: str, *, url: str | None = None) -> str:
    import trafilatura  # local import
    extracted = trafilatura.extract(
        html_or_text,
        include_comments=False,
        include_tables=False,
        favor_recall=True,
        url=url,
    )
    if extracted and extracted.strip():
        return extracted.strip()
    # Fall back to the input if it's already plaintext (no HTML tags detected).
    if "<" not in html_or_text or "</" not in html_or_text:
        return html_or_text.strip()
    raise IngestError("trafilatura could not extract main text from the page.")


def ingest(source: str, *, refresh: bool = False) -> IngestResult:
    """Ingest from a URL, a file path, or '-' for stdin.

    Stdin input is treated as already-clean text; URL/file goes through
    HTML extraction.
    """
    if source == "-":
        text = sys.stdin.read()
        if not text.strip():
            raise IngestError("stdin was empty.")
        text = text.strip()
        job_id = state.job_id_for(text, is_url=False)
        existing = state.load_ingest(job_id)
        if existing and not refresh:
            return IngestResult(record=existing, cached=True)
        rec = state.save_ingest(job_id=job_id, text=text, source_url=None, source_kind="stdin")
        return IngestResult(record=rec, cached=False)

    if _looks_like_url(source):
        url = source
        job_id = state.job_id_for(url, is_url=True)
        existing = state.load_ingest(job_id)
        if existing and not refresh:
            return IngestResult(record=existing, cached=True)
        html = _fetch_url(url)
        text = _extract_main_text(html, url=url)
        rec = state.save_ingest(job_id=job_id, text=text, source_url=url, source_kind="url")
        return IngestResult(record=rec, cached=False)

    # Local file
    p = Path(source).expanduser()
    if not p.exists():
        raise IngestError(f"no such file or URL: {source}")
    raw = p.read_text()
    if "<" in raw and "</" in raw and not p.suffix.lower() in (".txt", ".md"):
        text = _extract_main_text(raw)
    else:
        text = raw.strip()
    if not text:
        raise IngestError(f"{p}: empty after extraction.")
    # Hash on canonical text for files (so reformatting whitespace doesn't churn ids).
    job_id = state.job_id_for(text, is_url=False)
    existing = state.load_ingest(job_id)
    if existing and not refresh:
        return IngestResult(record=existing, cached=True)
    rec = state.save_ingest(
        job_id=job_id, text=text, source_url=None, source_kind="file"
    )
    return IngestResult(record=rec, cached=False)
