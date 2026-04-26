# job-apply-assistant

Local-first job application assistant. Maintain a structured profile of your real
experience, ingest job postings, get a fit-scored ranking, generate honestly
tailored application packets (resume + cover letter + 3 outreach email variants),
and approve everything before anything is sent or submitted.

**Hard rules baked in:**
- No fabrication: every tailored claim must trace to a profile entry, and a
  fabrication validator hard-blocks invented numbers, tenure inflation
  ("internship" → "experience"), in-progress degree inflation, and unknown
  employer/cert names.
- PII (phone, address, DOB, personal email) lives in `profile/secrets.yaml`,
  is gitignored, and is never sent to the LLM. Outputs use placeholders that
  are substituted locally at export time.
- No auto-submit, no auto-send. `approve` only flips a status flag.
- Industry-avoid filter (e.g. military/defense) flags jobs and refuses to
  generate a packet without `--force`.

## Setup

```bash
cd ~/job-apply-assistant
python3.13 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]

cp profile/samples/master_profile.example.yaml profile/master_profile.yaml
cp profile/samples/secrets.example.yaml profile/secrets.yaml
$EDITOR profile/master_profile.yaml profile/secrets.yaml
# (or:  python scripts/init_profile.py)
```

`OPENAI_API_KEY` is read from `~/.openclaw/.env` automatically; a project-local
`.env` overrides it if present.

## Thin-slice workflow

```bash
job-apply ingest https://jobs.example.com/security-analyst
job-apply ingest path/to/local-job-posting.txt
job-apply analyze
job-apply rank
job-apply tailor <job-id>
job-apply review <job-id>
job-apply approve <job-id>     # status flip; no send
```

## Layout

```
profile/   master_profile.yaml + secrets.yaml (both gitignored)
jobs/      raw_posts/  analyzed/  input_urls.txt
outputs/   <company>_<role>/  packet.json + 7 markdown views
src/       job_apply/  (cli.py + modules + prompts/)
tests/     fixtures/   test_*.py
```

## Status

Thin slice (M0–M4) complete; 78 tests passing.

- M0 — repo + sample profile + CLI skeleton
- M1 — profile loader, ingest, state, LLM client
- M2 — analyzer + fit scoring + industry filter + rank
- M3 — tailor pipeline + 3 email variants + fabrication validator + render
- M4 — review/approve/skip/queue + PII leak guard

Deferred to M5+ (post-MVP): contact research helpers, composite `run`, DOCX/PDF
rendering, cautious Playwright form-fill, optional Streamlit UI. See plan in
`~/.claude/plans/steady-whistling-pascal.md`.
