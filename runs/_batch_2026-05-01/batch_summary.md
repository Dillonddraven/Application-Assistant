# Benchmark batch summary — 2026-05-01

Run on **10** cybersecurity postings. Mode: benchmark (full pipeline regardless of fit, to stress-test).

## Headline numbers

- **Completed runs**: 10 / 10
- **Failed early** (ingest/analyze/tailor exception): 0
- **Final status**: 1 portal_ready · 8 needs_patch · 1 skip
- **Apply recommendation**: 1 apply · 3 maybe · 6 skip
- **Fabrication blocks across batch**: 1
- **HIGH-severity QA issues**: 7
- **Unsupported claims (would-remove)**: 6
- **Softened/study-only claims**: 50
- **Total wall time**: 90.2 min (avg **9.0 min/role**)

## Distributions

**Source confidence:** high=10

**Location confidence (revised model):** ?=10

**Role categories:** GRC / Compliance=5, Vulnerability Management=2, SOC Analyst=1, Other=1, Stretch=1

**Portal complexity:** low=8, high=1, medium=1

## Production-mode efficiency (would-have-been)

The benchmark intentionally generated full packets for every role to stress-test the pipeline. In production mode, the new early-stop rules (fit<50 → skip; 50-64 → lightweight; ≥65 → full) would have:

- **Skipped early**: 7 role(s) — saved ~$5.25 and ~56 min wall time
- **Lightweight (no PDF/DOCX render)**: 1 role(s) — saved ~$0.50
- **Full pipeline**: 2 role(s)
- **Total estimated savings**: ~$5.75 per identical batch in production mode

**Roles that ran full pipeline in benchmark but would have early-stopped in production** (8):
  - Pacific Legal Foundation — Data Security Analyst (fit 35, would have been **skip**)
  - UltraViolet Cyber — Associate SOC Analyst (fit 52, would have been **lightweight**)
  - LVT — Information Security Analyst (GRC) (fit 38, would have been **skip**)
  - Xpansiv — Information Security Analyst (fit 46, would have been **skip**)
  - Machinify — Security Engineer – Threat & Vulnerability Management (fit 38, would have been **skip**)
  - Core One — Security Analyst (fit 0, would have been **skip**)
  - SailPoint — Vulnerability Management Analyst (fit 39, would have been **skip**)
  - PurpleBox — Cybersecurity Analyst (fit 47, would have been **skip**)

## Ranked by fit score

- **Bloomreach — ** (`apply`, fit 96, src high, Other) — 7.0 min
- **Advanced Space — Sr. DevOps** (`skip`, fit 80, src high, Stretch) — 7.3 min
- **UltraViolet Cyber — Associate SOC Analyst** (`maybe`, fit 52, src high, SOC Analyst) — 9.9 min
- **PurpleBox — Cybersecurity Analyst** (`maybe`, fit 47, src high, Vulnerability Management) — 6.8 min
- **Xpansiv — Information Security Analyst** (`skip`, fit 46, src high, GRC / Compliance) — 11.2 min
- **SailPoint — Vulnerability Management Analyst** (`skip`, fit 39, src high, GRC / Compliance) — 10.0 min
- **LVT — Information Security Analyst (GRC)** (`skip`, fit 38, src high, GRC / Compliance) — 9.8 min
- **Machinify — Security Engineer – Threat & Vulnerability Management** (`maybe`, fit 38, src high, Vulnerability Management) — 10.2 min
- **Pacific Legal Foundation — Data Security Analyst** (`skip`, fit 35, src high, GRC / Compliance) — 8.6 min
- **Core One — Security Analyst** (`skip`, fit 0, src high, GRC / Compliance) — 9.4 min

## ✅ Worth applying (apply)

- **Bloomreach — ** (`apply`, fit 96, src high, Other)
  - reason: fit 96, source high, no major blockers

## 🤔 Maybe but patchable

- **UltraViolet Cyber — Associate SOC Analyst** (`maybe`, fit 52, src high, SOC Analyst)
  - reason: fit score 52; meaningful gaps
- **Machinify — Security Engineer – Threat & Vulnerability Management** (`maybe`, fit 38, src high, Vulnerability Management)
  - reason: fit score 38; meaningful gaps
- **PurpleBox — Cybersecurity Analyst** (`maybe`, fit 47, src high, Vulnerability Management)
  - reason: fit score 47; meaningful gaps

## ⛔ True skips

- **Pacific Legal Foundation — Data Security Analyst** (`skip`, fit 35, src high, GRC / Compliance)
  - reason: blocked: 3 HIGH QA, 0 fabrication block(s)
- **LVT — Information Security Analyst (GRC)** (`skip`, fit 38, src high, GRC / Compliance)
  - reason: blocked: 1 HIGH QA, 0 fabrication block(s)
- **Xpansiv — Information Security Analyst** (`skip`, fit 46, src high, GRC / Compliance)
  - reason: blocked: 1 HIGH QA, 0 fabrication block(s)
- **Core One — Security Analyst** (`skip`, fit 0, src high, GRC / Compliance)
  - reason: industry filter set to AVOID (military/defense)
- **SailPoint — Vulnerability Management Analyst** (`skip`, fit 39, src high, GRC / Compliance)
  - reason: blocked: 1 HIGH QA, 0 fabrication block(s)
- **Advanced Space — Sr. DevOps** (`skip`, fit 80, src high, Stretch)
  - reason: blocked: 1 HIGH QA, 1 fabrication block(s)

## Best 3 roles for Dillon

### Bloomreach — 

- Fit: **96** · Source: **high** · Category: Other
- Recommendation: **apply** (fit 96, source high, no major blockers)
- Top match reasons:
  - Translating raw vulnerability scanner output into actionable, clear reports for stakeholders to prioritize remediation e
  - Designing and implementing security automation workflows that improve visibility, monitoring, and human-in-the-loop appr
  - Communicating technical security risks and recommendations effectively to both technical and non-technical stakeholders 
- Source URL: https://job-boards.greenhouse.io/bloomreach/jobs/4902749

### UltraViolet Cyber — Associate SOC Analyst

- Fit: **52** · Source: **high** · Category: SOC Analyst
- Recommendation: **maybe** (fit score 52; meaningful gaps)
- Top match reasons:
  - Monitor and analyze log data, network traffic, and/or alerts generated by a variety of security technologies in real-tim
  - Respond, triage, and escalate security incidents using a SIEM platform following documented procedures.
  - Support the execution of vulnerability scans and assist in analyzing results for remediation recommendations.
- Source URL: https://jobs.lever.co/uvcyber/fd6bd8a9-4b79-4793-bd1d-db080bed7e5b

### PurpleBox — Cybersecurity Analyst

- Fit: **47** · Source: **high** · Category: Vulnerability Management
- Recommendation: **maybe** (fit score 47; meaningful gaps)
- Top match reasons:
  - Provide engineering, architecture design, assessment, and technical support for projects
  - Run daily processes and tools for managing cybersecurity including Vulnerability Management, Security Logging, Monitorin
  - Perform penetration testing, ethical hacking, and security assessments against Networks, Web Applications, API, Mobile A
- Top gaps:
  - No direct evidence of performing penetration testing or ethical hacking; candidate has adjacent experience in risk ident
- Source URL: https://jobs.smartrecruiters.com/PurpleBoxInc/743999936212683-cybersecurity-analyst

## Common failure modes / pipeline weaknesses

- **Thin-content hallucination**: at least one posting (likely Bloomreach) returned <600 chars from the source but the analyzer produced a high fit with empty title fields. The current `MIN_EXTRACTED_CHARS=500` threshold is too low — recommend raising to ~2000 OR adding a post-analyze sanity check (empty title + fit>80 = treat as ingest_failure).
- **1 fabrication blocks** across batch — investigate which prompt/profile combinations triggered them.
- **7 HIGH QA issues** firing across the batch — these blocked employer renders correctly. Confirms the QA gate works.
- **Workday JS-rendered fallback** worked for SailPoint via the Playwright rescue. Confirms ATS coverage is now broad enough.
- **All 4 fabrication validators** held: 0 numeric drift, 0 internship inflation, 0 in-progress-degree inflation, 0 unknown credentials across 10 roles.

## Where the pipeline overclaims

- **6 claims** flagged for removal across the batch.
- Most common pattern: small lab-script claims ('built a Python helper', 'configured rsyslog/NXLog') that the LLM extends into stronger framings.

## Where the pipeline gets too generic

- Repeated 'hands-on' descriptor in resume summaries (LOW QA flag fires often).
- Cross-document repetition of the Graylog lab description (resume + cover + outreach + DM) — MEDIUM QA flag.
- 'Stakeholder communication' as a skill bullet without a concrete example.

## Where Dillon needs stronger evidence (recurring missing_evidence)

- **Phishing-email triage and indicator extraction** — appears in many SOC postings; profile has zero direct evidence. Highest-frequency missing item.
- **Penetration testing** — listed as required in 4-5 of these JDs; profile only shows basic/lab exposure. Adjacent at best.
- **Live forensic casework** vs the playbook/lab work currently in profile.
- **Active security clearance** — would have unlocked Core One; explicit auto-skip already in place via industries_avoid + clearance keyword.
- **Production SIEM operations** — Splunk / Sentinel / Elastic — adds discrete value. Even one lab project would move several `maybe` roles toward `apply`.
- **SOC 2 / ISO 27001 / control-testing artifacts** — matters for GRC roles (LVT). CMMC/NIST coursework alone is not enough.

## Fit-score model assessment (post-batch)

- **Avg fit across batch**: 47.1
- **Distribution**: <50: 7 · 50-64: 1 · ≥65: 2

**Verdict: TOO HARSH.** More than half of the batch landed below 50, but most of these are real, applicable cybersecurity-analyst roles Dillon could reasonably interview for. The current weights (40% required-skills overlap, 20% cert, 15% experience, 15% pref-skills, 10% location) over-penalize candidates with fewer broad-buzzword skills.

**Recommended changes:**
- Lower the required-skills weight from 0.40 to 0.30; raise cert weight from 0.20 to 0.25 (Dillon's two CompTIA certs are real, ATS-readable signals).
- Add an explicit `evidence_alignment` component (0.15 weight) that scores based on `jd_analysis.evidence_map` strong/adjacent matches. This rewards having actually-built artifacts, not just keyword overlap.
- For required-skill matching, use synonym mapping: e.g. 'SIEM' should match 'Graylog'/'OpenSearch'; 'log monitoring' should match 'rsyslog/NXLog'; 'vulnerability reporting' should match 'SAST + Excel reporting'.
- Cap industry_filter penalty at 50 (vs 80) for `avoid` — makes the score more interpretable; the explicit auto-skip rule handles the actual blocking.

## Proposed production-mode thresholds (recalibrated for this batch)

Current thresholds: skip<50, lightweight 50-64, full ≥65.

Given the avg-fit distribution observed, consider:
- **skip threshold: <40** (was <50) — only auto-skip clearly out-of-band roles
- **lightweight band: 40-59** (was 50-64) — still inspect with cheap analyses
- **full pipeline: ≥60** (was ≥65) — moderate-fit roles get full effort

## Recommended hardening before scaling

1. **Raise `MIN_EXTRACTED_CHARS` to 2000** in `bench.robust_ingest` — Bloomreach (581 chars) hallucinated a fit=96 with empty title.
2. **Add post-analyze sanity check**: if title is empty or fit>80 with zero evidence_map matches, treat as ingest_failure.
3. **Phishing-analysis lab as profile project** — single highest-frequency missing_evidence across the 10 roles. One lab packet would unblock 4-5 roles.
4. **Production SIEM exposure** — Splunk / Sentinel — moves multiple `maybe` roles toward `apply`.
5. **Federal/clearance auto-skip filter** — add deterministic check for TS/SCI/Secret/polygraph keywords; force `skip` regardless of fit.
6. **Cross-document deduplication checker** — detect when the Graylog lab description is repeated verbatim across resume/cover/outreach (currently flagged as MEDIUM redundancy in QA, but could be auto-fixed at render time).
7. **Synonym-aware required-skill matcher** — current literal substring match misses 'SIEM' = 'Graylog/OpenSearch', 'log monitoring' = 'rsyslog/NXLog forwarding'.
8. **Explicit `apply_reasoning` in scorecards** — already wired into the new fit-score model; surface in match_report.md and the brief.

## Per-run details

Each run lives at `runs/<slug>_2026-05-01/`. Open the corresponding `internal/candidate_brief.md` for talking points, claim stress test, and claims-to-soften specific to that role. Open `internal/match_report.md` for JD analysis and fit breakdown.
