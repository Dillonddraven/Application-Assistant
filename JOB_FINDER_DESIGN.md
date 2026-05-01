# `job_finder` — design doc (NOT YET IMPLEMENTED)

A future module for the `job-apply` pipeline that surfaces postings from authoritative sources, deduplicates, scores fit against Dillon's profile, and returns an approval-gated review queue. This document describes the design only. No code in this module ships yet — the team will sign off on the design first.

## Goal

Reduce manual URL hunting. The user should arrive at a short list of postings worth tailoring without scrolling LinkedIn or Indeed. The system never auto-submits; it produces candidates and a recommended action per posting (`run packet` / `skip` / `save for later`).

## Non-goals

- Mass auto-applying. Out of scope.
- Bypassing site Terms of Service. We use only public, authorized data: ATS-hosted job-board JSON APIs and a small allowlist of aggregators that publish via RSS / sitemap.
- Cracking JS-rendered pages with stealth automation. Stick to source-of-truth APIs where they exist.

## Architecture

```
job_finder/
├── sources/                # one module per data source
│   ├── greenhouse.py       # boards.greenhouse.io/<co>/embed/job_board?for=<co> JSON
│   ├── lever.py            # api.lever.co/v0/postings/<co>?mode=json
│   ├── ashby.py            # api.ashbyhq.com/posting-api/job-board/<co>
│   ├── workable.py         # apply.workable.com/api/v3/accounts/<co>/jobs
│   └── adzuna.py           # search API (free tier 1k calls/mo)
├── filters.py              # title-pattern matching, location, industry-avoid
├── dedupe.py               # canonical key = (company, title, location)
├── scorer.py               # quick fit estimate without full LLM tailor
├── queue.py                # review-queue persistence (XLSX, like tracker)
└── cli.py                  # `job-apply finder run`, `finder review`, etc.
```

## Data sources (priority order)

| Source | Why high-priority | Mechanism |
|---|---|---|
| **Greenhouse** | Direct ATS, hundreds of mid-size cyber companies | Per-company JSON board: `https://boards-api.greenhouse.io/v1/boards/<token>/jobs` |
| **Lever** | Same | `https://api.lever.co/v0/postings/<co>?mode=json` |
| **Ashby** | Same, growing | `https://api.ashbyhq.com/posting-api/job-board/<token>` |
| **Workable** | Mid-market | `https://apply.workable.com/api/v3/accounts/<token>/jobs` |
| **SmartRecruiters** | Public job board API | `https://api.smartrecruiters.com/v1/companies/<id>/postings` |
| **Adzuna** | Aggregator for **discovery** of new companies, then resolve to direct ATS where possible | REST search API |
| Skipped | LinkedIn jobs (no public API), Indeed (locked-down), generic aggregators | — |

The user maintains a curated company watchlist (`profile/companies.yaml`) of 30–80 cyber-relevant companies, with their ATS slug. Polling 50 boards once daily is ~100 API calls — well under any rate limit.

## Curated company watchlist (initial seed)

```yaml
# profile/companies.yaml — example
companies:
  - { name: "Datadog",         ats: "greenhouse", slug: "datadog" }
  - { name: "Cloudflare",      ats: "greenhouse", slug: "cloudflare" }
  - { name: "GitLab",          ats: "greenhouse", slug: "gitlab" }
  - { name: "1Password",       ats: "greenhouse", slug: "1password" }
  - { name: "Tines",           ats: "ashby",      slug: "tines" }
  - { name: "Snyk",             ats: "lever",      slug: "snyk" }
  - { name: "Dragos",           ats: "lever",      slug: "dragos" }
  - { name: "SailPoint",        ats: "workday",    slug: "sailpoint" }
  - { name: "CrowdStrike",      ats: "workday",    slug: "crowdstrike" }
  # ... ~50 more
```

## Title matching

Targets (configurable per-user, defaults derived from `profile.preferences.target_roles`):

```
SOC Analyst I / II
Cybersecurity Analyst
Information Security Analyst
Security Operations Analyst
Vulnerability Management Analyst
GRC Analyst
IT Security Analyst
IAM Analyst
Security Automation Analyst / Engineer
Technical Support Engineer (Security)
Cloud Security Analyst
```

Matching uses substring + a curated synonym map (e.g., "SecOps Analyst" → "Security Operations Analyst"). Future: add a small embedding similarity check for fuzzier matches.

## Filtering (downgrade or drop)

Reject:
- Title contains "Senior", "Staff", "Principal", "Lead", "Architect", "Director" (Dillon is early-career — these are stretch only with explicit `--include-stretch`)
- Description contains "Active TS/SCI clearance", "DOD Secret clearance", "polygraph"
- Tags include `military` or `defense` (per `preferences.industries_avoid`)
- Location is onsite-only AND not in `preferences.locations` AND `willing_to_relocate=False`
- Salary listed and < `preferences.salary_min`

Mark as "stretch" but don't drop:
- 3-5 years requested (Dillon has ~1)
- One missing cert that's "preferred not required"

## Deduplication

Canonical key: `(normalize(company), normalize(title), location_state)`. Postings cross-listed on multiple aggregators collapse to a single row. The Greenhouse/Lever/Ashby version is preferred over the aggregator version (higher source confidence).

## Quick fit-score (no LLM tailor needed)

Reuse `job_analyzer.compute_fit_score` deterministic logic on extracted JD fields. Skip the LLM extraction step — instead, use lightweight heuristics on the raw JD text:
- Required-skills overlap with `profile.skills.*` flat list
- Cert-name match
- Years-experience tolerance (≤2 = good)
- Location/remote-mode against preferences
- Industry tag against avoid list

This produces a "preliminary fit estimate" 0–100. The expensive full pipeline (LLM extraction + tailor + brief + stress test) only runs after the user approves a posting from the review queue.

## Review queue

`runs/_finder_queue.xlsx` (mirrors the existing `applications.xlsx` tracker style):

| company | title | location | source | source_confidence | est_fit | est_fit_reason | top_match | top_risk | recommended_action | review_status | discovered_date | url |
|---|---|---|---|---|---|---|---|---|---|---|---|---|

`recommended_action` ∈ `{run_packet, skip, save_for_later, stretch}`.

CLI:
```
job-apply finder run                       # poll all sources, dedupe, populate queue
job-apply finder review                    # interactive: each new row, choose action
job-apply finder approve <slug>            # promote to full pipeline
job-apply finder ignore <slug>             # mark as not interested
job-apply finder daily                     # cron-friendly: poll + email digest of new finds
```

## Long-term: portal-fill assistance (after job_finder hardens)

The user's stretch goal: once the packet is approved, optionally have the system *help* with the portal — attaching the resume/cover letter PDF and filling SAFE fields (name, email, phone, LinkedIn, education, certifications, city/state, work auth) using Playwright. The system **must stop before**:

- Salary, sponsorship, relocation, shift availability, start date, custom long answers, legal acknowledgements, demographic/disability/veteran questions, **and the final Submit button**.

Implementation sketch:
- New module `portal_fill.py`. Uses Playwright (already a dependency).
- Field-classification ruleset matches the standardized lists in `bench.py`:
  `SAFE_AUTOFILL`, `HUMAN_REVIEW_REQUIRED`, `NEVER_AUTO_ANSWER`.
- For each field on the page, classify via `name`/`id`/`label` text match.
- Fill SAFE fields. Highlight HUMAN_REVIEW fields and pause. Refuse NEVER_AUTO_ANSWER fields.
- Final submit always requires explicit human click. The system will **navigate up to the submit button and stop**.

This is a separate, opt-in feature after `job_finder` and the benchmark loop are stable. **No part of this gets built in the same commit as `job_finder` itself.**

## Approval surface

Every output remains approval-gated. The flow:

```
[finder run] → review queue (XLSX + CLI)
[user approves a row] → standard pipeline (ingest → analyze → tailor → QA → brief)
[packet ready] → user reviews artifacts (already-existing flow)
[user approves packet] → tracker logs application; portal_fill (when built) attaches files & pauses
[user manually submits] → status flips to "applied"
```

## What this does NOT do

- It does not crawl LinkedIn or Indeed. Their ToS makes scraping unsafe and unreliable.
- It does not auto-submit. Final submit always requires the user.
- It does not scrape stealthily. All API access is through documented public endpoints.
- It does not replace the candidate's review. The packet review (resume, cover letter, brief, QA) remains the authoritative gate.

## Implementation order (when this is approved)

1. `sources/greenhouse.py` + `sources/lever.py` (cover ~60% of relevant companies; pure JSON API; no scraping)
2. `dedupe.py`, `scorer.py`, `filters.py`
3. `queue.py` (XLSX persistence following the existing tracker pattern)
4. `cli.py` (`finder run`, `finder review`)
5. `sources/ashby.py`, `sources/workable.py`, `sources/smartrecruiters.py`
6. `sources/adzuna.py` (aggregator, only for discovering new ATS-hosted companies)
7. `daily` cron mode + Telegram or email digest
8. `portal_fill.py` (last; Playwright; safety-first)

## Open questions for review

- Should the curated company list live in `profile/companies.yaml` (per-candidate) or `~/.config/job-apply/companies.yaml` (per-user)? Probably per-candidate — different candidates target different companies.
- Adzuna API key handling: same `~/.openclaw/.env` pattern, or separate? Use the existing pattern.
- How much fit-score divergence between the cheap pre-screen and the full LLM analysis is acceptable before we re-tune the heuristics?
- Telegram digest vs Mail digest for `finder daily`? The current pipeline uses Mail.app drafts; Telegram exists in Hermes. Probably Telegram for digests, Mail for individual approved packets.
