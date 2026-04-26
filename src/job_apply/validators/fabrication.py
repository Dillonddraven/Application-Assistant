"""No-fabrication validator.

Three layers of hard-block checks:

1. **Numeric whitelist.** Any number-bearing token (X%, X years, $X, Xx) in
   generated text must appear verbatim in the cited source's text/metrics or
   in the profile-level `metrics_allowed`.
2. **Tenure / credential lexicon.** If a cited experience is `role_type:
   internship`, the output cannot describe it as "X years at <company>",
   "full-time at <company>", or "senior <title> at <company>". If a cited
   education has `status: in_progress`, the output cannot say "graduated",
   "holds a degree in", "completed BS/MS in", or similar.
3. **Unknown credential.** Cert-like tokens (CompTIA X+, AWS Certified ...,
   CISSP, OSCP, etc.) appearing in output must match a cert name in the
   profile.

Soft warnings (non-blocking) are returned alongside blocks.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

NUMERIC_PATTERNS = [
    re.compile(r"\b\d+(?:\.\d+)?\s*%"),                      # 30%, 12.5 %
    re.compile(r"\b\d+(?:\.\d+)?\s*(?:years?|yrs?)\b", re.I),
    re.compile(r"\b\d+(?:\.\d+)?\s*(?:months?|mos?)\b", re.I),
    re.compile(r"\$\s?\d+(?:\.\d+)?\s?[KMBkmb]?\b"),
    re.compile(r"\b\d+(?:\.\d+)?\s?[xX]\b"),                  # 3x, 5x
]

# Known cert family patterns. We use these to detect cert-like tokens in output;
# any token not present in the profile's certs is a block.
CERT_PATTERNS = [
    re.compile(r"\bCompTIA\s+\w+\+", re.I),
    re.compile(r"\b(?:AWS|Amazon)\s+Certified[\w \-]*?(?=[.,;\n]|$)", re.I),
    re.compile(r"\bAzure\s+(?:Administrator|Architect|Developer|Security[\w \-]*?|Fundamentals)\b", re.I),
    re.compile(r"\b(?:Google\s+Cloud|GCP)\s+(?:Certified|Professional)[\w \-]*?(?=[.,;\n]|$)", re.I),
    re.compile(r"\bCISSP\b"),
    re.compile(r"\bCISM\b"),
    re.compile(r"\bCISA\b"),
    re.compile(r"\bCCSP\b"),
    re.compile(r"\bCEH\b"),
    re.compile(r"\bOSCP\b"),
    re.compile(r"\bOSCE\b"),
    re.compile(r"\bGCIH\b"),
    re.compile(r"\bGCIA\b"),
    re.compile(r"\bGIAC\s+\w+", re.I),
    re.compile(r"\bCCNA\b"),
    re.compile(r"\bCCNP\b"),
    re.compile(r"\bPMP\b"),
]

# Strong adjectives that warrant a soft warning when applied to in-progress areas.
STRONG_ADJ = {"expert", "senior", "lead", "principal", "10+ years", "veteran"}


@dataclass
class Block:
    rule: str
    detail: str
    source_id: str | None = None


@dataclass
class FabricationReport:
    blocks: list[Block] = field(default_factory=list)
    warnings: list[Block] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.blocks

    def to_dict(self) -> dict[str, list[dict[str, str | None]]]:
        return {
            "fabrication_blocks": [
                {"rule": b.rule, "detail": b.detail, "source_id": b.source_id}
                for b in self.blocks
            ],
            "fabrication_warnings": [
                {"rule": b.rule, "detail": b.detail, "source_id": b.source_id}
                for b in self.warnings
            ],
        }


def extract_numeric_tokens(text: str) -> list[str]:
    out: list[str] = []
    for r in NUMERIC_PATTERNS:
        for m in r.finditer(text):
            tok = re.sub(r"\s+", " ", m.group(0).strip())
            if tok and tok not in out:
                out.append(tok)
    return out


def _normalize(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower().strip())


def _resolve_source(source_id: str, profile: dict[str, Any]) -> dict[str, Any] | None:
    """Resolve dotted ids like 'experience.dillards_intern.b1' to the profile node.

    Returns the deepest matched node (bullet, experience, education, etc.) or
    None if it can't be resolved. 'skills', 'general', and unknown ids return
    None — those are treated as "no per-source numeric whitelist; fall back to
    metrics_allowed only".
    """
    if not source_id or source_id in {"skills", "general"}:
        return None
    parts = source_id.split(".")
    if len(parts) < 2:
        return None
    section = parts[0]
    section_id = parts[1]
    sub = parts[2] if len(parts) >= 3 else None

    items = profile.get(section)
    if not isinstance(items, list):
        # Handle "reusable_answers.<key>"
        if section == "reusable_answers":
            ra = profile.get("reusable_answers") or {}
            if isinstance(ra, dict) and section_id in ra:
                return {"text": ra[section_id]}
        return None

    parent = next((it for it in items if isinstance(it, dict) and it.get("id") == section_id), None)
    if parent is None:
        return None
    if sub is None:
        return parent
    bullets = parent.get("bullets") or []
    return next((b for b in bullets if isinstance(b, dict) and b.get("id") == source_id), None)


def _allowed_numerics_for(source_id: str, profile: dict[str, Any]) -> list[str]:
    """Numeric tokens permitted for output cited to this source_id."""
    allowed: list[str] = []
    metrics_allowed = profile.get("metrics_allowed") or []
    if isinstance(metrics_allowed, list):
        allowed.extend(_normalize(x) for x in metrics_allowed if isinstance(x, str))
    node = _resolve_source(source_id, profile)
    if isinstance(node, dict):
        # Numbers in the bullet/experience text itself
        text = node.get("text") or node.get("summary") or ""
        if isinstance(text, str):
            allowed.extend(_normalize(t) for t in extract_numeric_tokens(text))
        mp = node.get("metrics_present") or []
        if isinstance(mp, list):
            allowed.extend(_normalize(x) for x in mp if isinstance(x, str))
        # When source is an experience (no bullet sub), also allow each bullet's metrics
        for b in (node.get("bullets") or []):
            if isinstance(b, dict):
                text2 = b.get("text") or ""
                if isinstance(text2, str):
                    allowed.extend(_normalize(t) for t in extract_numeric_tokens(text2))
                for x in (b.get("metrics_present") or []):
                    if isinstance(x, str):
                        allowed.append(_normalize(x))
    return list(dict.fromkeys(allowed))  # dedupe, preserve order


def _profile_employer_names(profile: dict[str, Any]) -> list[str]:
    return [
        e.get("company") for e in (profile.get("experience") or [])
        if isinstance(e, dict) and isinstance(e.get("company"), str)
    ]


def _internship_companies(profile: dict[str, Any]) -> list[str]:
    return [
        e.get("company") for e in (profile.get("experience") or [])
        if isinstance(e, dict) and e.get("role_type") == "internship"
        and isinstance(e.get("company"), str)
    ]


def _in_progress_degrees(profile: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for e in (profile.get("education") or []):
        if isinstance(e, dict) and e.get("status") == "in_progress":
            d = e.get("degree")
            if isinstance(d, str):
                out.append(d)
    return out


def _profile_cert_names(profile: dict[str, Any]) -> list[str]:
    return [
        c.get("name") for c in (profile.get("certifications") or [])
        if isinstance(c, dict) and isinstance(c.get("name"), str)
    ]


def _check_numeric(
    *,
    source_id: str,
    text: str,
    profile: dict[str, Any],
) -> list[Block]:
    blocks: list[Block] = []
    out_nums = extract_numeric_tokens(text)
    if not out_nums:
        return blocks
    allowed = _allowed_numerics_for(source_id, profile)
    for tok in out_nums:
        norm = _normalize(tok)
        # Tolerate punctuation/whitespace variants
        if norm not in allowed and not any(norm == a or norm in a or a in norm for a in allowed):
            blocks.append(Block(
                rule="numeric_whitelist",
                detail=f"unsourced number {tok!r} in output cited to {source_id}",
                source_id=source_id,
            ))
    return blocks


def _check_internship_inflation(text: str, profile: dict[str, Any]) -> list[Block]:
    blocks: list[Block] = []
    for company in _internship_companies(profile):
        c = re.escape(company)
        patterns = [
            rf"\b\d+(?:\.\d+)?\s*(?:years?|yrs?)\b[^.\n]{{0,60}}\bat\s+{c}\b",
            rf"\bat\s+{c}\b[^.\n]{{0,60}}\b\d+(?:\.\d+)?\s*(?:years?|yrs?)\b",
            rf"\bfull[- ]time\b[^.\n]{{0,40}}\b{c}\b",
            rf"\b{c}\b[^.\n]{{0,40}}\bfull[- ]time\b",
            rf"\bsenior\b[^.\n]{{0,12}}\bat\s+{c}\b",
            rf"\b(?:engineer|analyst|administrator)\s+(?:II|III|IV)\b[^.\n]{{0,30}}\b{c}\b",
        ]
        for p in patterns:
            for m in re.finditer(p, text, re.I):
                blocks.append(Block(
                    rule="internship_inflation",
                    detail=f"phrase suggests non-internship tenure: {m.group(0)!r}",
                ))
    return blocks


def _check_in_progress_degree(text: str, profile: dict[str, Any]) -> list[Block]:
    blocks: list[Block] = []
    degrees = _in_progress_degrees(profile)
    if not degrees:
        return blocks
    # Per-degree phrases
    for d in degrees:
        d_re = re.escape(d)
        # also a softer match on degree level (BS, MS, etc.) extracted from the degree string
        level_match = re.search(r"\b(BA|BS|MA|MS|PhD)\b", d, re.I)
        level = level_match.group(0) if level_match else None
        patterns = [
            rf"\bgraduated\b[^.\n]{{0,40}}\b{d_re}\b",
            rf"\bholds?\s+(?:a|an|the)?\s*{d_re}\b",
            rf"\bcompleted\s+(?:a|an|my|the)?\s*{d_re}\b",
            rf"\b{d_re}\s+graduate\b",
            rf"\bearned\s+(?:a|an|my|the)?\s*{d_re}\b",
        ]
        if level:
            l = re.escape(level)
            patterns.extend([
                rf"\bgraduated\s+with\s+(?:a|an|my)?\s*{l}\b",
                rf"\bholds?\s+(?:a|an)?\s*{l}\b",
                rf"\bcompleted\s+(?:a|an|my)?\s*{l}\b",
                rf"\bearned\s+(?:a|an|my)?\s*{l}\b",
            ])
        for p in patterns:
            for m in re.finditer(p, text, re.I):
                blocks.append(Block(
                    rule="in_progress_degree_inflation",
                    detail=f"phrase suggests degree completed: {m.group(0)!r}",
                ))
    return blocks


def _check_unknown_certs(text: str, profile: dict[str, Any]) -> list[Block]:
    blocks: list[Block] = []
    profile_certs = [_normalize(n) for n in _profile_cert_names(profile)]
    for r in CERT_PATTERNS:
        for m in r.finditer(text):
            tok = m.group(0).strip()
            tok_norm = _normalize(tok)
            if any(tok_norm in pc or pc in tok_norm for pc in profile_certs):
                continue
            blocks.append(Block(
                rule="unknown_credential",
                detail=f"credential not in profile: {tok!r}",
            ))
    # Dedupe by detail
    seen: set[str] = set()
    out: list[Block] = []
    for b in blocks:
        if b.detail in seen:
            continue
        seen.add(b.detail)
        out.append(b)
    return out


def _check_strong_adjectives(text: str, profile: dict[str, Any]) -> list[Block]:
    warnings: list[Block] = []
    text_lower = text.lower()
    for adj in STRONG_ADJ:
        if adj in text_lower:
            warnings.append(Block(
                rule="strong_adjective",
                detail=f"strong-claim phrase {adj!r} detected — verify it matches profile reality",
            ))
    return warnings


@dataclass
class CitedSegment:
    source_id: str
    text: str


def validate_segments(
    segments: list[CitedSegment],
    profile: dict[str, Any],
) -> FabricationReport:
    """Run all fabrication checks across a list of (source_id, text) segments.

    Numeric checks are per-segment (each segment is judged against its source).
    Lexicon checks (internship/in-progress/cert) run on the full concatenation,
    since these violations don't depend on which source claims them.
    """
    report = FabricationReport()
    full_text = "\n\n".join(s.text for s in segments)

    for seg in segments:
        report.blocks.extend(_check_numeric(
            source_id=seg.source_id, text=seg.text, profile=profile
        ))

    report.blocks.extend(_check_internship_inflation(full_text, profile))
    report.blocks.extend(_check_in_progress_degree(full_text, profile))
    report.blocks.extend(_check_unknown_certs(full_text, profile))
    report.warnings.extend(_check_strong_adjectives(full_text, profile))
    return report


def extract_segments_from_packet(packet: dict[str, Any]) -> list[CitedSegment]:
    """Pull every cited (source_id, text) pair out of a packet's `tailored` block."""
    out: list[CitedSegment] = []
    tailored = packet.get("tailored", {})
    summary = tailored.get("summary")
    if isinstance(summary, str) and summary.strip():
        out.append(CitedSegment(source_id="general", text=summary))
    for b in tailored.get("bullets") or []:
        if isinstance(b, dict) and isinstance(b.get("text"), str):
            out.append(CitedSegment(source_id=b.get("source_id") or "general", text=b["text"]))
    for p in tailored.get("cover_letter_paragraphs") or []:
        if isinstance(p, dict) and isinstance(p.get("text"), str):
            out.append(CitedSegment(source_id=p.get("source_id") or "general", text=p["text"]))
    for a in tailored.get("application_answers") or []:
        if isinstance(a, dict) and isinstance(a.get("answer"), str):
            out.append(CitedSegment(source_id=a.get("source_id") or "general", text=a["answer"]))
    return out
