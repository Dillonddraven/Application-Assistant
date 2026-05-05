# job-apply-assistant

Local-first job application assistant. Maintain a structured profile of your
real experience, ingest job postings, get a fit-scored ranking, generate
**honestly tailored** application packets (resume + cover letter + 3 outreach
email variants), and approve everything before anything is sent or submitted.

**Hard rules baked into the pipeline:**

- **No fabrication.** Every tailored claim must trace to a profile entry. A
  fabrication validator hard-blocks invented numbers, tenure inflation (e.g.
  "internship" rendered as "experience"), in-progress degree inflation, and
  unknown employer / cert / title names.
- **PII boundary.** Phone, address, DOB, and personal email live in
  `profile/secrets.yaml`, are gitignored, and are **never sent to the LLM**.
  Outputs use `{{email}}` / `{{phone}}` placeholders that are substituted
  locally at export time.
- **No auto-submit, no auto-send.** `pack` and `email` only open a Mail.app
  draft (or write a markdown view); you click Send manually.
- **Industry-avoid filter.** Roles that match `preferences.industries_avoid`
  in your profile (e.g. `[military, defense]`) are flagged and refuse to
  generate a packet without `--force`.
- **Hard blockers.** Roles requiring non-English language proficiency, active
  clearance, prior law enforcement, AML/KYC years, or production-program
  ownership are detected and surfaced before you waste tokens tailoring them.

## What you get

```
profile/
  master_profile.yaml      ← career history, sent to LLM (gitignored)
  secrets.yaml             ← phone/address/email, NEVER sent to LLM (gitignored)
  companies.yaml           ← curated company watchlist for finder-run
jobs/
  raw_posts/               ← cached fetched JD text (gitignored)
  analyzed/                ← LLM-extracted structured fields per posting
outputs/
  <slug>/
    employer/              ← polished resume.pdf + cover.pdf (what you submit)
    internal/              ← markdown views, qa_report.md, contacts.md, README_APPLY.md
    packet.json            ← structured tailored data + run metadata
applications.xlsx          ← your apply history with state machine
runs/_finder_queue.xlsx    ← review queue from finder-run
```

## Setup

```bash
git clone https://github.com/<your-fork>/job-apply-assistant.git
cd job-apply-assistant

python3.13 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
playwright install chromium    # for PDF rendering and JS-rendered ATS fallback

cp profile/samples/master_profile.example.yaml profile/master_profile.yaml
cp profile/samples/secrets.example.yaml          profile/secrets.yaml
cp profile/samples/companies.example.yaml        profile/companies.yaml
cp profile/samples/skill_synonyms.example.yaml   profile/skill_synonyms.yaml
cp .env.example .env

$EDITOR profile/master_profile.yaml profile/secrets.yaml profile/companies.yaml .env
```

The `profile/*.yaml` files are gitignored — your real career data and PII
**never enter the public repo**, even if you push your fork. The `samples/`
directory contains template files that ARE tracked and serve as your
starting point.

## Choose an LLM provider

Edit `.env` to pick one. Defaults assume OpenAI; the tool also supports
DeepSeek, Anthropic, and any OpenAI-compatible endpoint (Ollama, LM Studio,
vLLM, Together, etc.):

```bash
# OpenAI (default)
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...

# DeepSeek (V3 / V4)
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-...
# Optional explicit model picks (defaults are deepseek-chat / -reasoner):
# JOB_APPLY_MODEL_TAILOR=deepseek-chat
# JOB_APPLY_MODEL_DEEP=deepseek-reasoner

# Anthropic
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Local Ollama / vLLM / LM Studio (any OpenAI-compatible endpoint)
LLM_PROVIDER=openai-compat
LLM_BASE_URL=http://localhost:11434/v1
LLM_API_KEY=ollama
JOB_APPLY_MODEL_EXTRACT=qwen2.5:7b
JOB_APPLY_MODEL_TAILOR=qwen2.5:14b
JOB_APPLY_MODEL_DEEP=qwen2.5:32b
```

Per-tier overrides (`JOB_APPLY_MODEL_EXTRACT` / `_TAILOR` / `_DEEP`) work for
every provider.

## Thin-slice workflow (apply to one role)

```bash
# 1. Ingest a single posting (URL or local .txt/.md)
job-apply ingest https://example.com/jobs/security-analyst

# 2. Extract structured fields + fit score
job-apply analyze

# 3. See your queue
job-apply rank

# 4. Generate the application packet (tailored resume + cover letter + 3 outreach variants)
job-apply tailor <job-id>

# 5. Review what was generated
job-apply review <job-id>
job-apply pack <slug>           # writes README_APPLY.md + apply_url.txt + email_to_dillon.md

# 6. Send yourself a draft to review in Mail.app (macOS)
job-apply email <slug>

# 7. After applying, log it
job-apply set-status --ident <slug> --status submitted
```

## Bulk workflow (find + apply across many companies)

```bash
# 1. Poll all companies in profile/companies.yaml (Greenhouse + Lever public APIs)
job-apply finder-run

# 2. Open runs/_finder_queue.xlsx in Excel/Numbers and review the rankings.
#    Each row is scored 0-100 with category (Strong Target / Target / Reach /
#    Too Senior / Blocker), recommendation, resume angle, outreach angle.
#    Mark approved_for_packet=y on rows you want to apply to.

# 3. Approve via CLI instead of XLSX (alternative)
job-apply finder-approve "https://example.com/jobs/123"

# 4. For each approved row: ingest -> analyze -> tailor -> pack
#    (See the Thin-slice workflow above)

# 5. If a company has 2+ approved roles, bundle them into one outreach packet
job-apply pack-company acme
```

## Contact research (ethical OSINT, no scraping)

```bash
# Generate clickable LinkedIn / Google search URLs for recruiters + hiring managers
job-apply contacts <slug> --department "Security" --company-domain example.com

# After you find one real email at the company, seed it to detect the pattern
job-apply contacts <slug> \
  --known-email "alice.smith@example.com" \
  --known-name "Alice Smith" \
  --target-name "Jane Doe" \
  --target-name "John Roe"
```

The tool produces `outputs/<slug>/internal/contacts.md` with one-click
search URLs and candidate-email guesses based on the detected pattern.
**No LinkedIn scraping, no paid contact-data APIs.** It just makes manual
research one click per query.

## Ranking model

Each role in `runs/_finder_queue.xlsx` is scored on five dimensions:

| Dimension | Weight | What it measures |
|---|---|---|
| Experience fit | 35% | Title + JD body for `entry / junior / target / mid / senior` signals (years required, "new grad" hints, senior markers like staff/principal/lead) |
| Role-family fit | 25% | Title against your target list (Cybersecurity Analyst, GRC Analyst, SOC Analyst, etc.) |
| Skills / project match | 20% | Synonym-aware matcher between profile skills and JD tokens |
| Location flexibility | 10% | Remote / hybrid / in-person; preferred metros from your profile |
| Company / interest | 10% | Light heuristic (compliance / GRC titles get a bump) |

Salary range is detected from JD body and used as a soft seniority warning
($60–110k = target band, $180k+ = generally deprioritize).

Hard blockers cap the score and force category=`Blocker`:

- Required non-English language proficiency
- Active security clearance (TS/SCI, polygraph, etc.)
- Prior law enforcement background
- N+ years of AML/KYC/fraud-investigation experience
- Production / enterprise program ownership ("owned the production cloud
  security program")

## Configuration files

| File | What it does | Tracked? |
|---|---|---|
| `profile/master_profile.yaml` | Your career facts: education, certs, experience, projects, skills, target_roles, preferred_metros, industries_avoid | **No** (gitignored) |
| `profile/secrets.yaml` | Phone, address, personal email, LinkedIn / GitHub URLs | **No** (gitignored) |
| `profile/companies.yaml` | Greenhouse / Lever slugs to poll on `finder-run` | **No** (gitignored) |
| `profile/skill_synonyms.yaml` | User-editable skill clusters (SIEM ↔ Splunk ↔ Graylog ↔ ...) | **No** (gitignored) |
| `.env` | LLM provider config | **No** (gitignored) |
| `profile/samples/*.example.yaml` | Templates for the four files above | **Yes** |

Copy a sample → fill it in → it's automatically gitignored from then on.

## Development

```bash
pip install -e .[dev]
pytest                 # full suite
pytest tests/test_tracker.py -v
```

The pipeline is **fabrication-paranoid by design** — many tests assert that
specific overclaims are caught. Don't relax those without thinking carefully.

## Files NOT to commit even if you fork

The `.gitignore` covers them, but to be explicit:

- `profile/master_profile.yaml`, `profile/secrets.yaml`, `profile/companies.yaml`, `profile/skill_synonyms.yaml`
- `jobs/raw_posts/`, `jobs/analyzed/`, `outputs/`
- `applications.xlsx`, `MORNING_REVIEW.md`, `RANKED_TODAY.md`
- `runs/` (one-off driver scripts often contain real URLs / data)
- `.env`

## License

MIT — see [LICENSE](LICENSE).

## Origin

Built by Dillon Stinson (CIS / MS Cybersecurity, University of Tulsa) with
heavy assistance from Claude Code (Anthropic). The truth-safe constraints,
QA pass, and PII boundary were the most important parts to design carefully —
the system refuses to ship overstated material, even when it costs you a
packet.
