"""Multi-user Streamlit web UI.

Flow:
  1. /                -- if not logged in, show login + signup forms
  2. (signup)         -- creates account, drops user into onboarding wizard
  3. /onboarding      -- guided form -> writes user's profile + secrets
  4. /                -- main app (Setup / Add job / Run pipeline / Queue / Artifacts)

Per-user data lives at <users_root>/<username>/. The CLI commands honor
JOB_APPLY_ROOT, so the same `job-apply tailor` etc. transparently writes
into the logged-in user's dir.

DeepSeek is the default LLM provider; users plug in their own API key
or the host operator can set DEEPSEEK_API_KEY at the server level.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import streamlit as st
import yaml

from job_apply.ui import auth, onboarding


REPO_ROOT = Path(__file__).resolve().parents[3]


# --- per-session helpers ---

def _logged_in_user() -> str | None:
    return st.session_state.get("username")


def _user_root() -> Path:
    return auth.user_dir(_logged_in_user() or "_invalid")


_LLM_SECRET_VARS = (
    "OPENAI_API_KEY", "DEEPSEEK_API_KEY", "ANTHROPIC_API_KEY", "LLM_API_KEY",
    "LLM_BASE_URL", "LLM_PROVIDER",
    "JOB_APPLY_MODEL_EXTRACT", "JOB_APPLY_MODEL_TAILOR", "JOB_APPLY_MODEL_DEEP",
)


def _user_env() -> dict[str, str]:
    """Env vars to pass to subprocess so the CLI scopes to this user's dir.

    Security: we explicitly STRIP any LLM-provider env vars from the
    host's shell so one user can't accidentally rack up cost on the host
    operator's API key. The user's per-account .env is the only source
    of LLM credentials for that session, UNLESS the host opts into
    sharing via JOB_APPLY_SHARED_LLM=true (e.g. for friends-and-family
    where the host pays the bill).
    """
    env = os.environ.copy()
    if env.get("JOB_APPLY_SHARED_LLM", "").lower() not in ("1", "true", "yes"):
        for k in _LLM_SECRET_VARS:
            env.pop(k, None)
    env["JOB_APPLY_ROOT"] = str(_user_root())
    user_env_file = _user_root() / ".env"
    if user_env_file.exists():
        for line in user_env_file.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if not s or s.startswith("#") or "=" not in s:
                continue
            k, _, v = s.partition("=")
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def _run_cli(args: list[str], timeout: int = 900) -> tuple[int, str]:
    cmd = ["job-apply"] + args
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
            cwd=str(REPO_ROOT), env=_user_env(),
        )
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except subprocess.TimeoutExpired:
        return -1, f"timed out after {timeout}s"
    except FileNotFoundError:
        return -2, "`job-apply` not found. Install with `pip install -e .`."


# --- auth screens ---

def _login_screen() -> None:
    st.title("job-apply-assistant")
    st.caption(
        "Local-first, fabrication-paranoid job-application pipeline. "
        "Your data stays under your account on this server. No auto-submit."
    )
    tab_login, tab_signup = st.tabs(["Log in", "Sign up"])

    with tab_login:
        with st.form("login_form"):
            username = st.text_input("Username", key="li_user")
            password = st.text_input("Password", type="password", key="li_pw")
            submitted = st.form_submit_button("Log in", type="primary")
        if submitted:
            try:
                user = auth.login(username, password)
            except ValueError as e:
                st.error(str(e))
            else:
                st.session_state["username"] = user.username
                st.session_state["session_token"] = auth.issue_session_token()
                st.rerun()

    with tab_signup:
        st.caption(
            "Pick a username (3-31 chars, lowercase letters / digits / "
            "`_-`) and a password (8+ chars). Both are stored locally on "
            "this server and never shared."
        )
        with st.form("signup_form"):
            username = st.text_input("Username", key="su_user")
            password = st.text_input(
                "Password", type="password",
                help="Minimum 8 characters.", key="su_pw")
            password2 = st.text_input(
                "Confirm password", type="password", key="su_pw2")
            submitted = st.form_submit_button("Create account",
                                                type="primary")
        if submitted:
            if password != password2:
                st.error("Passwords don't match.")
            else:
                try:
                    user = auth.signup(username, password)
                except ValueError as e:
                    st.error(str(e))
                else:
                    st.session_state["username"] = user.username
                    st.session_state["session_token"] = auth.issue_session_token()
                    st.success("Account created -- let's build your profile.")
                    st.rerun()


# --- onboarding wizard ---

def _onboarding_screen() -> None:
    user = _logged_in_user()
    st.title(f"Welcome, {user}")
    st.caption(
        "We'll ask a few questions to build your profile. None of your "
        "PII (phone, address) is sent to the LLM. You can edit any of "
        "this later from the Setup tab."
    )
    st.progress(0.0, text="Step 1 of 5")

    if "ob_answers" not in st.session_state:
        st.session_state["ob_answers"] = onboarding.OnboardingAnswers()
    a: onboarding.OnboardingAnswers = st.session_state["ob_answers"]

    step = st.session_state.get("ob_step", 1)
    st.progress(step / 5, text=f"Step {step} of 5")

    if step == 1:
        st.subheader("Who are you?")
        a.full_name = st.text_input("Full name", value=a.full_name)
        cols = st.columns(2)
        a.citizenship = cols[0].text_input("Citizenship / work-auth status",
                                            value=a.citizenship)
        a.pronouns = cols[1].text_input("Pronouns (optional)",
                                          value=a.pronouns)
        a.work_auth = st.text_input(
            "Work authorization", value=a.work_auth,
            help="What you'd say on an application: e.g. 'Authorized to work in the US, no sponsorship required.'")

        st.subheader("Contact info (PII -- never sent to LLM)")
        cols = st.columns(2)
        a.email = cols[0].text_input("Email", value=a.email)
        a.phone = cols[1].text_input("Phone", value=a.phone)
        cols = st.columns(2)
        a.address_city = cols[0].text_input("City", value=a.address_city)
        a.address_state = cols[1].text_input("State / region",
                                              value=a.address_state)
        a.linkedin_url = st.text_input("LinkedIn URL (optional)",
                                        value=a.linkedin_url)
        a.github_url = st.text_input("GitHub URL (optional)",
                                      value=a.github_url)

        if st.button("Next: Education", type="primary"):
            if not a.full_name.strip() or not a.email.strip():
                st.error("Full name and email are required.")
            else:
                st.session_state["ob_step"] = 2
                st.rerun()

    elif step == 2:
        st.subheader("Education")
        st.caption("Add each degree (in progress or completed). At least one required.")
        n_schools = st.number_input(
            "How many schools / degrees to add?",
            min_value=1, max_value=5, value=max(1, len(a.schools) or 1))
        a.schools = a.schools or []
        new_schools = []
        for i in range(int(n_schools)):
            with st.container(border=True):
                cols = st.columns([2, 2])
                school = cols[0].text_input(
                    f"School {i+1}",
                    value=(a.schools[i].get("school") if i < len(a.schools) else ""),
                    key=f"sch_school_{i}")
                degree = cols[1].text_input(
                    f"Degree {i+1}",
                    value=(a.schools[i].get("degree") if i < len(a.schools) else ""),
                    key=f"sch_deg_{i}",
                    help="e.g. 'BS, Computer Information Systems'")
                cols = st.columns([1, 1, 1])
                status = cols[0].selectbox(
                    "Status",
                    ["in_progress", "completed"],
                    index=(0 if i >= len(a.schools)
                           else (0 if a.schools[i].get("status") == "in_progress" else 1)),
                    key=f"sch_status_{i}")
                start = cols[1].text_input(
                    "Start (YYYY-MM)",
                    value=(a.schools[i].get("start") if i < len(a.schools) else ""),
                    key=f"sch_start_{i}", placeholder="2022-08")
                end_label = "Expected end (YYYY-MM)" if status == "in_progress" else "End (YYYY-MM)"
                end_key = "expected_end" if status == "in_progress" else "end"
                end_val = cols[2].text_input(
                    end_label,
                    value=(a.schools[i].get(end_key) if i < len(a.schools) else ""),
                    key=f"sch_end_{i}", placeholder="2026-05")
                new_schools.append({
                    "id": f"edu_{i+1}",
                    "school": school, "degree": degree,
                    "status": status, "start": start,
                    "expected_end" if status == "in_progress" else "end": end_val,
                })
        a.schools = new_schools

        st.subheader("Certifications")
        n_certs = st.number_input(
            "How many certs to add?", min_value=0, max_value=10,
            value=len(a.certifications))
        new_certs = []
        for i in range(int(n_certs)):
            cols = st.columns([3, 1])
            name = cols[0].text_input(
                f"Cert {i+1} name",
                value=(a.certifications[i].get("name") if i < len(a.certifications) else ""),
                key=f"cert_name_{i}",
                placeholder="e.g. CompTIA Security+")
            issued = cols[1].text_input(
                "Issued (YYYY-MM)",
                value=(a.certifications[i].get("issued") if i < len(a.certifications) else ""),
                key=f"cert_iss_{i}")
            new_certs.append({"id": f"cert_{i+1}", "name": name, "issued": issued})
        a.certifications = new_certs

        cols = st.columns(2)
        if cols[0].button("Back"):
            st.session_state["ob_step"] = 1
            st.rerun()
        if cols[1].button("Next: Experience", type="primary"):
            st.session_state["ob_step"] = 3
            st.rerun()

    elif step == 3:
        st.subheader("Most recent role")
        st.caption(
            "v0 captures one role to seed the profile. You can add more "
            "later from the Setup tab. Leave blank if you have no work "
            "or internship experience yet -- projects + coursework will "
            "carry the resume."
        )
        cols = st.columns(2)
        a.most_recent_role_company = cols[0].text_input(
            "Company / org", value=a.most_recent_role_company)
        a.most_recent_role_title = cols[1].text_input(
            "Title", value=a.most_recent_role_title,
            placeholder="e.g. Information Security Intern")
        cols = st.columns(3)
        a.most_recent_role_type = cols[0].selectbox(
            "Type",
            ["internship", "fulltime", "contract", "project"],
            index=["internship", "fulltime", "contract", "project"].index(
                a.most_recent_role_type or "internship"))
        a.most_recent_role_start = cols[1].text_input(
            "Start (YYYY-MM)",
            value=a.most_recent_role_start, placeholder="2025-05")
        a.most_recent_role_end = cols[2].text_input(
            "End (YYYY-MM or 'Present')",
            value=a.most_recent_role_end, placeholder="2025-08")
        a.most_recent_role_summary = st.text_area(
            "1-2 sentence summary of the role", height=100,
            value=a.most_recent_role_summary,
            placeholder="e.g. Information Security internship: vulnerability "
                        "reporting, SAST workflows, secure code training "
                        "support, and translating raw scanner data into "
                        "stakeholder-ready summaries.")

        cols = st.columns(2)
        if cols[0].button("Back"):
            st.session_state["ob_step"] = 2
            st.rerun()
        if cols[1].button("Next: Skills", type="primary"):
            st.session_state["ob_step"] = 4
            st.rerun()

    elif step == 4:
        st.subheader("Skills")
        a.technical_skills = st.multiselect(
            "Technical / programming skills",
            options=onboarding.DEFAULT_TECHNICAL_SKILLS + a.technical_skills,
            default=a.technical_skills,
            help="Pick what applies. You can add custom entries by typing.",
            accept_new_options=True)
        a.security_skills = st.multiselect(
            "Cybersecurity-related skills",
            options=onboarding.DEFAULT_SECURITY_SKILLS + a.security_skills,
            default=a.security_skills,
            accept_new_options=True)

        cols = st.columns(2)
        if cols[0].button("Back"):
            st.session_state["ob_step"] = 3
            st.rerun()
        if cols[1].button("Next: Preferences", type="primary"):
            st.session_state["ob_step"] = 5
            st.rerun()

    elif step == 5:
        st.subheader("What roles are you targeting?")
        a.target_roles = st.multiselect(
            "Pick all that apply",
            options=onboarding.DEFAULT_TARGET_ROLES + a.target_roles,
            default=a.target_roles or onboarding.DEFAULT_TARGET_ROLES[:5],
            accept_new_options=True)
        a.workplace_modes = st.multiselect(
            "Workplace mode",
            options=["remote", "hybrid", "in-person"],
            default=a.workplace_modes,
            help="Pick all that work. The ranker treats remote/hybrid as a small bonus, not a deciding factor.")
        a.locations = st.multiselect(
            "Cities / metros open to (or where you live)",
            options=a.locations + ["Tulsa, OK", "Dallas, TX", "Oklahoma City, OK",
                                    "Austin, TX", "Denver, CO", "New York, NY",
                                    "San Francisco, CA", "Seattle, WA", "Chicago, IL"],
            default=a.locations, accept_new_options=True)
        a.willing_to_relocate = st.checkbox(
            "Willing to relocate for the right role",
            value=a.willing_to_relocate)
        a.industries_avoid = st.multiselect(
            "Industries to AVOID (jobs in these will be auto-flagged)",
            options=onboarding.DEFAULT_INDUSTRIES_AVOID,
            default=a.industries_avoid)
        a.salary_min = st.number_input(
            "Minimum target salary (USD, optional)",
            min_value=0, max_value=500_000,
            value=a.salary_min or 0, step=5_000) or None

        cols = st.columns(2)
        if cols[0].button("Back"):
            st.session_state["ob_step"] = 4
            st.rerun()
        if cols[1].button("Save profile and start", type="primary"):
            if not a.target_roles:
                st.error("Pick at least one target role.")
            else:
                pp, sp = onboarding.write_profile(_user_root(), a)
                st.success(f"Profile saved at {pp.relative_to(_user_root())}")
                # Drop the wizard state
                st.session_state.pop("ob_step", None)
                st.session_state.pop("ob_answers", None)
                st.rerun()


# --- main app tabs (post-onboarding) ---

def _setup_tab() -> None:
    st.subheader("Profile + LLM provider")
    user = _logged_in_user()
    st.caption(f"Editing data for `{user}` at `{_user_root()}`.")

    user_env = _user_root() / ".env"

    with st.expander("LLM provider (.env)"):
        st.caption(
            "DeepSeek is the cheapest mainstream provider and is the default. "
            "If the host has set a server-wide key (DEEPSEEK_API_KEY in the "
            "container env) you can leave the field blank and it'll be used. "
            "Otherwise paste your own key."
        )
        provider = st.selectbox(
            "LLM_PROVIDER",
            ["deepseek", "openai", "anthropic", "openai-compat"],
            index=["deepseek", "openai", "anthropic", "openai-compat"].index(
                _detect_provider(_read_text(user_env))))
        keyvar = {
            "deepseek": "DEEPSEEK_API_KEY",
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "openai-compat": "LLM_API_KEY",
        }[provider]
        api_key = st.text_input(
            keyvar, type="password",
            value=_extract_var(_read_text(user_env), keyvar))
        base_url = ""
        if provider == "openai-compat":
            base_url = st.text_input(
                "LLM_BASE_URL",
                value=_extract_var(_read_text(user_env), "LLM_BASE_URL"))
        if st.button("Save .env", type="primary"):
            lines = [f"LLM_PROVIDER={provider}"]
            if api_key:
                lines.append(f"{keyvar}={api_key}")
            if base_url:
                lines.append(f"LLM_BASE_URL={base_url}")
            user_env.parent.mkdir(parents=True, exist_ok=True)
            user_env.write_text("\n".join(lines) + "\n", encoding="utf-8")
            st.success("Saved.")

    profile_path = _user_root() / "profile" / "master_profile.yaml"
    secrets_path = _user_root() / "profile" / "secrets.yaml"
    with st.expander("Profile (career history -- LLM-bound)"):
        text = st.text_area("master_profile.yaml",
                             value=_read_text(profile_path), height=400)
        if st.button("Save profile"):
            try:
                yaml.safe_load(text)
                profile_path.write_text(text, encoding="utf-8")
                st.success("Saved.")
            except yaml.YAMLError as e:
                st.error(f"YAML error: {e}")
    with st.expander("Secrets (PII -- NEVER sent to LLM)"):
        text = st.text_area("secrets.yaml",
                             value=_read_text(secrets_path), height=200)
        if st.button("Save secrets"):
            try:
                yaml.safe_load(text)
                secrets_path.write_text(text, encoding="utf-8")
                st.success("Saved.")
            except yaml.YAMLError as e:
                st.error(f"YAML error: {e}")


def _add_job_tab() -> None:
    st.subheader("Add a job posting")
    url = st.text_input("Job URL")
    if st.button("Ingest", type="primary", disabled=not url):
        with st.spinner(f"fetching {url}..."):
            rc, out = _run_cli(["ingest", url], timeout=120)
        st.code(out)


def _pipeline_tab() -> None:
    st.subheader("Run pipeline")
    # Lazy import so changes to JOB_APPLY_ROOT take effect
    from job_apply import state as _state, config as _cfg
    _cfg.ROOT = _user_root()
    _cfg.ANALYZED_DIR = _user_root() / "jobs" / "analyzed"
    _cfg.OUTPUTS_DIR = _user_root() / "outputs"
    analyzed = _state.list_analyzed() if _cfg.ANALYZED_DIR.exists() else []
    if not analyzed:
        st.info("No analyzed jobs yet. Use the 'Add a job' tab.")
        return
    options = sorted(analyzed, key=lambda a: -(a.get("fit_score") or 0))
    label_map = {f"{a.get('company','?')} -- {a.get('title','?')} (fit {a.get('fit_score',0)})": a
                 for a in options}
    pick = st.selectbox("pick a role", list(label_map.keys()))
    ana = label_map[pick]
    jid = ana.get("id", "")
    cols = st.columns(3)
    if cols[0].button("Analyze", type="primary"):
        with st.spinner("analyzing..."):
            rc, out = _run_cli(["analyze", "--id", jid], timeout=120)
        st.code(out[-2000:])
    if cols[1].button("Tailor (LLM, ~5-7 min)"):
        with st.status("tailoring...", expanded=True):
            rc, out = _run_cli(["tailor", jid], timeout=900)
            st.code(out[-3000:])
    if cols[2].button("Pack + email"):
        # Find slug from packets list
        for p in _state.list_packets():
            if p.get("job_id") == jid:
                slug = p.get("slug", "")
                rc1, out1 = _run_cli(["pack", slug, "--apply-url",
                                       ana.get("source_url", "")])
                st.code(out1)
                break
        else:
            st.error("No packet -- run Tailor first.")


def _artifacts_tab() -> None:
    st.subheader("Download artifacts")
    out_dir = _user_root() / "outputs"
    if not out_dir.exists():
        st.info("No packets yet.")
        return
    slugs = sorted(d.name for d in out_dir.iterdir() if d.is_dir())
    if not slugs:
        st.info("No packets yet.")
        return
    slug = st.selectbox("pick a packet", slugs)
    employer = out_dir / slug / "employer"
    internal = out_dir / slug / "internal"
    cols = st.columns(2)
    cols[0].markdown("**Employer files**")
    for f in ("tailored_resume.pdf", "cover_letter.pdf",
              "tailored_resume.docx", "cover_letter.docx"):
        p = employer / f
        if p.exists():
            cols[0].download_button(
                f, data=p.read_bytes(), file_name=f, key=f"emp_{slug}_{f}")
    cols[1].markdown("**Internal review files**")
    for f in ("README_APPLY.md", "qa_report.md", "match_report.md",
              "candidate_brief.md", "application_answers.md",
              "outreach_recruiter.md", "outreach_hiring_manager.md",
              "linkedin_dm.md", "contacts.md"):
        p = internal / f
        if p.exists():
            cols[1].download_button(
                f, data=p.read_bytes(), file_name=f, key=f"int_{slug}_{f}")


# --- helpers ---

def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _detect_provider(env_text: str) -> str:
    for line in env_text.splitlines():
        s = line.strip()
        if s.startswith("LLM_PROVIDER=") and not s.startswith("#"):
            return s.partition("=")[2].strip().strip('"').strip("'")
    return "deepseek"


def _extract_var(env_text: str, name: str) -> str:
    for line in env_text.splitlines():
        s = line.strip()
        if s.startswith(f"{name}=") and not s.startswith("#"):
            return s.partition("=")[2].strip().strip('"').strip("'")
    return ""


# --- entry ---

def main() -> None:
    st.set_page_config(page_title="job-apply-assistant", layout="wide")
    user = _logged_in_user()

    if not user:
        _login_screen()
        return

    if not auth.has_profile(user):
        _onboarding_screen()
        return

    # Sidebar with logout + identity
    with st.sidebar:
        st.markdown(f"**Logged in as:** `{user}`")
        st.caption(f"Data dir: `users/{user}/`")
        if st.button("Log out"):
            for k in ("username", "session_token", "ob_step", "ob_answers"):
                st.session_state.pop(k, None)
            st.rerun()
        st.divider()
        st.caption(
            "DeepSeek is the cheapest mainstream LLM. Set your key under "
            "Setup -> LLM provider, or ask the host operator to set "
            "DEEPSEEK_API_KEY at the server level."
        )

    st.title("job-apply-assistant")
    tabs = st.tabs(["Setup", "Add a job", "Run pipeline", "Download artifacts"])
    with tabs[0]:
        _setup_tab()
    with tabs[1]:
        _add_job_tab()
    with tabs[2]:
        _pipeline_tab()
    with tabs[3]:
        _artifacts_tab()


if __name__ == "__main__":
    main()
