"""Single-page Streamlit UI wrapping the job-apply CLI.

Designed so a non-technical user can: edit their profile, pick an LLM
provider, paste a job URL, run the full pipeline, and download the
generated resume / cover letter / message templates -- all from a browser.

Run locally:
    streamlit run src/job_apply/ui/streamlit_app.py

Deployment (any of):
  - Streamlit Community Cloud (free, hooks to a public GitHub repo)
  - Fly.io / Render / Railway (uses the Dockerfile in repo root)
  - Docker locally: docker build -t job-apply-ui . && docker run -p 8501:8501 -v $PWD:/app job-apply-ui
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import streamlit as st
import yaml

from job_apply import config as cfg
from job_apply import profile_loader, state, tracker

ROOT = Path(__file__).resolve().parents[3]
PROFILE_PATH = ROOT / "profile" / "master_profile.yaml"
SECRETS_PATH = ROOT / "profile" / "secrets.yaml"
COMPANIES_PATH = ROOT / "profile" / "companies.yaml"
ENV_PATH = ROOT / ".env"

QUEUE_PATH = ROOT / "runs" / "_finder_queue.xlsx"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _run_cli(args: list[str], timeout: int = 900) -> tuple[int, str]:
    """Run `job-apply <args>` and return (returncode, combined stdout+stderr)."""
    cmd = ["job-apply"] + args
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, cwd=str(ROOT),
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode, out
    except subprocess.TimeoutExpired:
        return -1, f"timed out after {timeout}s"
    except FileNotFoundError:
        return -2, "`job-apply` console script not found. Run `pip install -e .` first."


def _setup_tab() -> None:
    st.subheader("1. Profile + secrets + LLM provider")

    st.markdown(
        "Three files drive the system. They are gitignored, so your real "
        "data never leaves this machine."
    )

    cols = st.columns(3)
    cols[0].metric("Profile", "set" if PROFILE_PATH.exists() else "missing")
    cols[1].metric("Secrets", "set" if SECRETS_PATH.exists() else "missing")
    cols[2].metric(".env (LLM)", "set" if ENV_PATH.exists() else "missing")

    if not PROFILE_PATH.exists():
        if st.button("Create profile from sample", key="init_profile"):
            sample = ROOT / "profile" / "samples" / "master_profile.example.yaml"
            if sample.exists():
                _write_text(PROFILE_PATH, sample.read_text(encoding="utf-8"))
                st.success("Created. Edit below.")
                st.rerun()
    if not SECRETS_PATH.exists():
        if st.button("Create secrets from sample", key="init_secrets"):
            sample = ROOT / "profile" / "samples" / "secrets.example.yaml"
            if sample.exists():
                _write_text(SECRETS_PATH, sample.read_text(encoding="utf-8"))
                st.success("Created. Edit below.")
                st.rerun()
    if not ENV_PATH.exists():
        if st.button("Create .env from sample", key="init_env"):
            sample = ROOT / ".env.example"
            if sample.exists():
                _write_text(ENV_PATH, sample.read_text(encoding="utf-8"))
                st.success("Created. Edit below.")
                st.rerun()

    with st.expander("LLM provider (.env)", expanded=not ENV_PATH.exists()):
        st.markdown(
            "Pick one provider. Only fill in the API key for that provider."
        )
        provider = st.selectbox(
            "LLM_PROVIDER",
            ["openai", "deepseek", "anthropic", "openai-compat"],
            index=["openai", "deepseek", "anthropic", "openai-compat"].index(
                _detect_provider(_read_text(ENV_PATH))
            ),
        )
        api_key = st.text_input(
            f"{_key_var_for(provider)}",
            value=_extract_var(_read_text(ENV_PATH), _key_var_for(provider)),
            type="password",
            help="Your API key. Stored only in your local .env -- never sent over the network except to the LLM provider you chose.",
        )
        base_url = ""
        if provider == "openai-compat":
            base_url = st.text_input(
                "LLM_BASE_URL",
                value=_extract_var(_read_text(ENV_PATH), "LLM_BASE_URL"),
                placeholder="http://localhost:11434/v1",
            )
        if st.button("Save .env", type="primary"):
            lines = [
                f"LLM_PROVIDER={provider}",
                f"{_key_var_for(provider)}={api_key}",
            ]
            if base_url:
                lines.append(f"LLM_BASE_URL={base_url}")
            _write_text(ENV_PATH, "\n".join(lines) + "\n")
            st.success(".env saved.")

    with st.expander("Profile (career history, sent to LLM)",
                      expanded=PROFILE_PATH.exists()):
        st.caption(
            "PII rule: do NOT put phone, address, DOB, or personal email "
            "here. Those go in secrets.yaml."
        )
        text = st.text_area(
            "master_profile.yaml",
            value=_read_text(PROFILE_PATH),
            height=400,
            key="profile_yaml",
        )
        if st.button("Save profile"):
            try:
                yaml.safe_load(text)   # syntax check
                _write_text(PROFILE_PATH, text)
                st.success("Profile saved.")
            except yaml.YAMLError as e:
                st.error(f"YAML syntax error: {e}")

    with st.expander("Secrets (PII, NEVER sent to LLM)"):
        st.caption(
            "These values fill `{{email}}` / `{{phone}}` placeholders at "
            "render time only. Never sent to the LLM."
        )
        text = st.text_area(
            "secrets.yaml",
            value=_read_text(SECRETS_PATH),
            height=200,
            key="secrets_yaml",
        )
        if st.button("Save secrets"):
            try:
                yaml.safe_load(text)
                _write_text(SECRETS_PATH, text)
                st.success("Secrets saved.")
            except yaml.YAMLError as e:
                st.error(f"YAML syntax error: {e}")


def _add_job_tab() -> None:
    st.subheader("2. Add a job posting")
    url = st.text_input("Job URL", placeholder="https://example.com/jobs/123")
    cols = st.columns([1, 3])
    if cols[0].button("Ingest", type="primary", disabled=not url):
        with st.spinner(f"fetching {url}..."):
            rc, out = _run_cli(["ingest", url], timeout=120)
        if rc == 0:
            st.success("Ingested.")
            st.code(out)
        else:
            st.error(f"ingest failed (rc={rc})")
            st.code(out)
    cols[1].caption(
        "Or paste the JD text into a local file and run `job-apply ingest "
        "path/to/file.txt` from a terminal."
    )

    st.divider()
    st.subheader("Or pull from your watchlist (finder-run)")
    st.caption(
        "Polls every company in `profile/companies.yaml` for fresh openings. "
        "Takes ~30-60 seconds depending on how many companies you have."
    )
    if st.button("Run finder-run"):
        with st.spinner("polling ATS boards..."):
            rc, out = _run_cli(["finder-run"], timeout=300)
        st.code(out[-2000:] if len(out) > 2000 else out)


def _pipeline_tab() -> None:
    st.subheader("3. Run the pipeline")
    st.caption(
        "For each ingested job, run analyze -> tailor -> pack. Tailor is "
        "the expensive step (LLM call, ~5-7 minutes per role). The pack "
        "step writes a final apply checklist + email draft."
    )

    analyzed = state.list_analyzed()
    if not analyzed:
        st.info("Nothing analyzed yet. Use the 'Add a job' tab first.")
        return

    options = [(f"{a.get('company','?')} -- {a.get('title','?')} (fit {a.get('fit_score',0)})", a)
               for a in analyzed]
    options.sort(key=lambda x: -(x[1].get("fit_score") or 0))

    label, ana = options[
        st.selectbox("pick a role",
                      options=range(len(options)),
                      format_func=lambda i: options[i][0])
    ]
    jid = ana.get("id", "")
    st.write(f"**Job ID:** `{jid}`")
    st.write(f"**Apply URL:** {ana.get('source_url','(none)')}")

    cols = st.columns(3)
    if cols[0].button("Tailor (LLM)", type="primary"):
        with st.status("running tailor (this takes ~5-7 min)...", expanded=True) as s:
            rc, out = _run_cli(["tailor", jid], timeout=900)
            st.code(out[-3000:])
            s.update(state="complete" if rc == 0 else "error")
    if cols[1].button("Pack (write README + email)"):
        # Resolve slug from analyzed -> packet
        for p in state.list_packets():
            if p.get("job_id") == jid:
                slug = p.get("slug", "")
                rc, out = _run_cli(["pack", slug, "--apply-url", ana.get("source_url", "")])
                st.code(out)
                break
        else:
            st.error("No packet yet. Run Tailor first.")
    if cols[2].button("Email me a draft"):
        for p in state.list_packets():
            if p.get("job_id") == jid:
                rc, out = _run_cli(["email", p.get("slug", "")])
                st.code(out)
                break


def _queue_tab() -> None:
    st.subheader("4. Ranked queue")
    if not QUEUE_PATH.exists():
        st.info("No queue yet. Run finder-run on the 'Add a job' tab first.")
        return
    try:
        from job_apply.finder import queue as fq
        rows = fq.load_queue()
    except Exception as e:
        st.error(f"couldn't read queue: {e}")
        return

    cats = sorted({r.ranking_category for r in rows if r.ranking_category})
    cat = st.selectbox("filter by category", ["all"] + cats)

    filtered = [r for r in rows if cat == "all" or r.ranking_category == cat]
    filtered.sort(key=lambda r: -r.ranking_score)

    st.caption(f"{len(filtered)} roles")
    for r in filtered[:50]:
        with st.expander(
            f"{r.ranking_score} | {r.ranking_category} | {r.company} -- {r.title}"
        ):
            st.write(f"**Location:** {r.location}")
            st.write(f"**Apply URL:** {r.url}")
            st.write(f"**Recommendation:** {r.final_recommendation}")
            st.write(f"**Why apply:** {r.biggest_reason}")
            st.write(f"**Why risky:** {r.biggest_risk}")
            st.write(f"**Resume angle:** {r.resume_angle}")
            st.write(f"**Outreach angle:** {r.outreach_angle}")
            if r.blockers_summary:
                st.warning(f"Blockers: {r.blockers_summary}")


def _artifacts_tab() -> None:
    st.subheader("5. Download artifacts")
    packets = state.list_packets()
    if not packets:
        st.info("No packets generated yet.")
        return

    options = [(f"{p.get('slug','?')}", p) for p in packets]
    label, pkt = options[
        st.selectbox("pick a packet", options=range(len(options)),
                      format_func=lambda i: options[i][0])
    ]
    slug = pkt.get("slug", "")
    pkt_dir = ROOT / "outputs" / slug
    employer = pkt_dir / "employer"
    internal = pkt_dir / "internal"

    cols = st.columns(2)
    cols[0].markdown("**Employer files (PDF/DOCX -- attach to apply portal)**")
    for f in ("tailored_resume.pdf", "cover_letter.pdf",
              "tailored_resume.docx", "cover_letter.docx"):
        p = employer / f
        if p.exists():
            cols[0].download_button(
                f, data=p.read_bytes(), file_name=f,
                mime="application/octet-stream", key=f"emp_{slug}_{f}",
            )
    cols[1].markdown("**Internal review files (markdown)**")
    for f in ("README_APPLY.md", "qa_report.md", "match_report.md",
              "candidate_brief.md", "application_answers.md",
              "outreach_recruiter.md", "outreach_hiring_manager.md",
              "linkedin_dm.md", "contacts.md", "email_to_dillon.md"):
        p = internal / f
        if p.exists():
            cols[1].download_button(
                f, data=p.read_bytes(), file_name=f,
                mime="text/markdown", key=f"int_{slug}_{f}",
            )


# --- helpers ---

def _detect_provider(env_text: str) -> str:
    for line in env_text.splitlines():
        s = line.strip()
        if s.startswith("LLM_PROVIDER=") and not s.startswith("#"):
            return s.partition("=")[2].strip().strip('"').strip("'")
    return "openai"


def _extract_var(env_text: str, name: str) -> str:
    for line in env_text.splitlines():
        s = line.strip()
        if s.startswith(f"{name}=") and not s.startswith("#"):
            return s.partition("=")[2].strip().strip('"').strip("'")
    return ""


def _key_var_for(provider: str) -> str:
    return {
        "openai": "OPENAI_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "openai-compat": "LLM_API_KEY",
    }.get(provider, "OPENAI_API_KEY")


# --- main ---

def main() -> None:
    st.set_page_config(
        page_title="job-apply-assistant",
        page_icon="(:",
        layout="wide",
    )
    st.title("job-apply-assistant")
    st.caption(
        "Local-first, fabrication-paranoid job-application pipeline. "
        "All data stays on this machine. No auto-submit."
    )

    tabs = st.tabs(["Setup", "Add a job", "Run pipeline",
                     "Ranked queue", "Download artifacts"])
    with tabs[0]:
        _setup_tab()
    with tabs[1]:
        _add_job_tab()
    with tabs[2]:
        _pipeline_tab()
    with tabs[3]:
        _queue_tab()
    with tabs[4]:
        _artifacts_tab()


if __name__ == "__main__":
    main()
