"""Single owner of on-disk lifecycle.

Job lifecycle:
  ingested  -> jobs/raw_posts/<id>.txt + .meta.json exist
  analyzed  -> jobs/analyzed/<id>.json exists
  drafted   -> outputs/<slug>/packet.json status == "draft"
  approved  -> packet.json status == "approved"
  skipped   -> packet.json status == "skipped"

Job id = sha1(url-or-canonical-text)[:12]. Stable; idempotent.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from .config import ANALYZED_DIR, OUTPUTS_DIR, RAW_POSTS_DIR, ensure_dirs

Status = Literal["draft", "approved", "skipped"]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def job_id_for(source: str, *, is_url: bool) -> str:
    """sha1[:12] of URL (lowercased) or canonical text."""
    if is_url:
        canonical = source.strip().lower()
    else:
        canonical = re.sub(r"\s+", " ", source).strip()
    return hashlib.sha1(canonical.encode("utf-8")).hexdigest()[:12]


def slugify(s: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").lower()
    return s or "untitled"


def packet_slug(company: str, title: str) -> str:
    return f"{slugify(company)}_{slugify(title)}"[:80]


@dataclass
class IngestRecord:
    job_id: str
    raw_text_path: Path
    meta_path: Path
    source_url: str | None
    source_kind: Literal["url", "file", "stdin"]
    fetched_at: str

    @property
    def text(self) -> str:
        return self.raw_text_path.read_text()


def write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content)
    tmp.replace(path)


def write_json_atomic(path: Path, obj: Any) -> None:
    write_atomic(path, json.dumps(obj, indent=2, sort_keys=False))


def save_ingest(
    *,
    job_id: str,
    text: str,
    source_url: str | None,
    source_kind: Literal["url", "file", "stdin"],
) -> IngestRecord:
    ensure_dirs()
    raw_path = RAW_POSTS_DIR / f"{job_id}.txt"
    meta_path = RAW_POSTS_DIR / f"{job_id}.meta.json"
    fetched_at = now_iso()
    write_atomic(raw_path, text)
    write_json_atomic(
        meta_path,
        {
            "job_id": job_id,
            "source_url": source_url,
            "source_kind": source_kind,
            "fetched_at": fetched_at,
            "char_count": len(text),
        },
    )
    return IngestRecord(
        job_id=job_id,
        raw_text_path=raw_path,
        meta_path=meta_path,
        source_url=source_url,
        source_kind=source_kind,
        fetched_at=fetched_at,
    )


def load_ingest(job_id: str) -> IngestRecord | None:
    raw_path = RAW_POSTS_DIR / f"{job_id}.txt"
    meta_path = RAW_POSTS_DIR / f"{job_id}.meta.json"
    if not raw_path.exists() or not meta_path.exists():
        return None
    meta = json.loads(meta_path.read_text())
    return IngestRecord(
        job_id=job_id,
        raw_text_path=raw_path,
        meta_path=meta_path,
        source_url=meta.get("source_url"),
        source_kind=meta.get("source_kind", "url"),
        fetched_at=meta.get("fetched_at", ""),
    )


def list_ingests() -> list[IngestRecord]:
    out: list[IngestRecord] = []
    if not RAW_POSTS_DIR.exists():
        return out
    for meta in sorted(RAW_POSTS_DIR.glob("*.meta.json")):
        rec = load_ingest(meta.stem.replace(".meta", ""))
        if rec:
            out.append(rec)
    return out


def analyzed_path(job_id: str) -> Path:
    return ANALYZED_DIR / f"{job_id}.json"


def load_analyzed(job_id: str) -> dict[str, Any] | None:
    p = analyzed_path(job_id)
    if not p.exists():
        return None
    return json.loads(p.read_text())


def save_analyzed(job_id: str, data: dict[str, Any]) -> Path:
    ensure_dirs()
    p = analyzed_path(job_id)
    write_json_atomic(p, data)
    return p


def list_analyzed() -> list[dict[str, Any]]:
    if not ANALYZED_DIR.exists():
        return []
    return [json.loads(p.read_text()) for p in sorted(ANALYZED_DIR.glob("*.json"))]


def packet_dir(slug: str) -> Path:
    return OUTPUTS_DIR / slug


def packet_path(slug: str) -> Path:
    return packet_dir(slug) / "packet.json"


def load_packet(slug: str) -> dict[str, Any] | None:
    p = packet_path(slug)
    if not p.exists():
        return None
    return json.loads(p.read_text())


def save_packet(slug: str, packet: dict[str, Any]) -> Path:
    p = packet_path(slug)
    write_json_atomic(p, packet)
    return p


def list_packets() -> list[dict[str, Any]]:
    if not OUTPUTS_DIR.exists():
        return []
    out: list[dict[str, Any]] = []
    for d in sorted(OUTPUTS_DIR.iterdir()):
        if not d.is_dir():
            continue
        pkt = load_packet(d.name)
        if pkt:
            out.append(pkt)
    return out


def find_slug_by_job_id(job_id: str) -> str | None:
    for pkt in list_packets():
        if pkt.get("job_id") == job_id:
            return pkt.get("slug")
    return None
