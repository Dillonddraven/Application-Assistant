"""HTML/CSS → PDF rendering via Playwright headless Chromium.

Single-column, sans-serif, navy accent, ATS-aware (no two-column tricks, no
text-in-image gimmicks). Same data as the markdown views; PDF is for human eyes,
DOCX for ATS upload.
"""
from __future__ import annotations

import html
from importlib.resources import files
from pathlib import Path
from typing import Any

from .profile_loader import Profile, Secrets
from .render import _scrub_source_ids, collect_known_ids


class PDFRenderError(RuntimeError):
    pass


def _css(name: str) -> str:
    return files("job_apply.templates").joinpath(name).read_text()


def _h(s: str) -> str:
    return html.escape(s, quote=True)


def _fmt_period(start: str, end: str) -> str:
    end = end or "Present"
    return f"{start} – {end}" if start else end


def _contact_line(profile: Profile, secrets: Secrets) -> str:
    bits: list[str] = []
    pm = secrets.placeholder_map()
    for key in ("{{email}}", "{{phone}}", "{{linkedin_url}}", "{{github_url}}"):
        if pm.get(key):
            bits.append(_h(pm[key]))
    return " &nbsp;•&nbsp; ".join(bits)


def _resume_html(profile: Profile, tailored: dict[str, Any], secrets: Secrets) -> str:
    p = profile.data
    known = collect_known_ids(p)
    name = _h(p.get("identity", {}).get("full_name", ""))
    contact = _contact_line(profile, secrets)
    summary = _scrub_source_ids(tailored.get("summary") or "", known).strip()

    parts: list[str] = []
    parts.append(f'<div class="name">{name}</div>')
    if contact:
        parts.append(f'<div class="contact">{contact}</div>')

    if summary:
        parts.append("<h2>Summary</h2>")
        parts.append(f'<p class="summary">{_h(summary)}</p>')

    skills = tailored.get("skills_emphasis") or []
    if skills:
        parts.append("<h2>Skills</h2>")
        parts.append('<ul class="skills-list">')
        for s in skills:
            parts.append(f"<li>{_h(s)}</li>")
        parts.append("</ul>")

    exp_id_set = {e.get("id") for e in (p.get("experience") or []) if isinstance(e, dict)}
    cited_exp_ids: set[str] = set()
    bullets_by_exp: dict[str, list[str]] = {}
    for b in tailored.get("bullets") or []:
        sid = b.get("source_id", "")
        bits = sid.split(".")
        exp_id = None
        for candidate in bits[:2]:
            if candidate in exp_id_set:
                exp_id = candidate
                break
        if exp_id:
            cited_exp_ids.add(exp_id)
            bullets_by_exp.setdefault(exp_id, []).append(_scrub_source_ids(b.get("text", ""), known))

    if cited_exp_ids:
        parts.append("<h2>Experience</h2>")
        for exp in p.get("experience") or []:
            if exp.get("id") not in cited_exp_ids:
                continue
            company = _h(exp.get("company") or "")
            title = _h(exp.get("title") or "")
            location = _h(exp.get("location") or "")
            period = _h(_fmt_period(exp.get("start") or "", exp.get("end") or ""))
            right = " &nbsp;•&nbsp; ".join(b for b in [period, location] if b)
            parts.append(f"<h3>{company} <span style='font-weight:500;color:#5b6068'>— {title}</span></h3>")
            if right:
                parts.append(f'<div class="role-meta"><span class="right">{right}</span></div>')
            parts.append('<ul class="bullets">')
            for txt in bullets_by_exp.get(exp.get("id"), []):
                parts.append(f"<li>{_h(txt)}</li>")
            parts.append("</ul>")

    edu = p.get("education") or []
    if edu:
        parts.append("<h2>Education</h2>")
        for e in edu:
            degree = _h(e.get("degree") or "")
            school = _h(e.get("school") or "")
            status = e.get("status") or ""
            expected = e.get("expected_end") or ""
            right_bits: list[str] = []
            if status == "in_progress":
                right_bits.append("in progress")
                if expected:
                    right_bits.append(f"expected {_h(expected)}")
            elif e.get("end"):
                right_bits.append(_h(e.get("end")))
            right = ", ".join(right_bits)
            parts.append(
                '<div class="education-row">'
                f'<span class="left"><span class="degree">{degree}</span> '
                f'<span class="school">— {school}</span></span>'
                f'<span class="right">{right}</span>'
                "</div>"
            )

    certs = p.get("certifications") or []
    if certs:
        parts.append("<h2>Certifications</h2>")
        for c in certs:
            n = _h(c.get("name") or "")
            issued = c.get("issued") or ""
            right = _h(issued) if issued and not str(issued).startswith("<") else ""
            parts.append(
                '<div class="cert-row">'
                f'<span class="left">{n}</span>'
                f'<span class="right">{right}</span>'
                "</div>"
            )

    body = "\n".join(parts)
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        f"<title>{name} — Resume</title>"
        f"<style>{_css('resume.css')}</style>"
        f"</head><body>{body}</body></html>"
    )


def _cover_html(
    *, profile: Profile, tailored: dict[str, Any], secrets: Secrets,
    company: str, salutation: str = "Dear Hiring Team,", date_iso: str,
) -> str:
    known = collect_known_ids(profile.data)
    pm = secrets.placeholder_map()
    name = _h(profile.data.get("identity", {}).get("full_name", ""))

    addr_lines: list[str] = []
    city_state_zip = " ".join(
        b for b in [
            (pm.get("{{address_city}}") or "") + ("," if pm.get("{{address_city}}") else ""),
            pm.get("{{address_state}}") or "",
            pm.get("{{address_zip}}") or "",
        ] if b.strip()
    ).strip()
    if pm.get("{{address_street}}"):
        addr_lines.append(_h(pm["{{address_street}}"]))
    if city_state_zip:
        addr_lines.append(_h(city_state_zip))

    parts: list[str] = []
    if addr_lines:
        parts.append('<div class="return-address">')
        for line in addr_lines:
            parts.append(f"<div>{line}</div>")
        parts.append("</div>")

    parts.append(f'<div class="date">{_h(date_iso)}</div>')
    parts.append(f'<div class="salutation">{_h(salutation)}</div>')
    for para in tailored.get("cover_letter_paragraphs") or []:
        text = _scrub_source_ids(para.get("text", ""), known).strip()
        if text:
            parts.append(f'<p class="body">{_h(text)}</p>')

    parts.append('<div class="signoff">Sincerely,</div>')
    parts.append(f'<div class="signature-name">{name}</div>')
    sig_bits: list[str] = []
    if pm.get("{{email}}"):
        sig_bits.append(_h(pm["{{email}}"]))
    if pm.get("{{phone}}"):
        sig_bits.append(_h(pm["{{phone}}"]))
    if sig_bits:
        parts.append(
            f'<div class="signature-contact">{" &nbsp;•&nbsp; ".join(sig_bits)}</div>'
        )

    body = "\n".join(parts)
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        f"<title>{name} — Cover letter — {_h(company)}</title>"
        f"<style>{_css('cover_letter.css')}</style>"
        f"</head><body>{body}</body></html>"
    )


def _html_to_pdf(html_str: str, out_path: Path) -> None:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        raise PDFRenderError(
            f"playwright not available: {e}. Install with: pip install playwright"
        )
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                page = browser.new_page()
                page.set_content(html_str, wait_until="load")
                out_path.parent.mkdir(parents=True, exist_ok=True)
                page.pdf(path=str(out_path), format="Letter",
                         margin={"top": "0in", "bottom": "0in", "left": "0in", "right": "0in"},
                         print_background=True)
            finally:
                browser.close()
    except Exception as e:
        if "Executable doesn't exist" in str(e) or "missing" in str(e).lower():
            raise PDFRenderError(
                "Chromium not installed for Playwright. Run: "
                "playwright install chromium"
            ) from e
        raise


def render_resume_pdf(*, profile: Profile, tailored: dict[str, Any], secrets: Secrets,
                      out_path: Path) -> Path:
    html_str = _resume_html(profile, tailored, secrets)
    _html_to_pdf(html_str, out_path)
    return out_path


def render_cover_letter_pdf(*, profile: Profile, tailored: dict[str, Any], secrets: Secrets,
                            out_path: Path, company: str, date_iso: str,
                            salutation: str = "Dear Hiring Team,") -> Path:
    html_str = _cover_html(profile=profile, tailored=tailored, secrets=secrets,
                           company=company, salutation=salutation, date_iso=date_iso)
    _html_to_pdf(html_str, out_path)
    return out_path
