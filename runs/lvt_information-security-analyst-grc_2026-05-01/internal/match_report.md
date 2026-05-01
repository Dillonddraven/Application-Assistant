# Match report: LVT — Information Security Analyst (GRC)

- Job ID: `ddc7ca3800a0`
- Source: https://job-boards.greenhouse.io/liveviewtechnologiesinc/jobs/5192885008
- Source confidence: **high** — direct ATS board (greenhouse.io)
- Location: —  (unknown)
- Industry filter: **ok** (tags: security, technology, saas)
- **Fit score: 38**
- Breakdown:
  - skills_match: 0
  - preferred_skills_match: 0
  - cert_match: 100
  - experience_match: 80
  - location_match: 55
  - industry_filter: ok

## Rationale
The candidate has relevant experience in information security and GRC-related tasks, including vulnerability management and security documentation. They possess certifications like CompTIA Security+ and have skills in automation and technical communication, which align with the role's requirements. Their background in security risk analysis and compliance support is relevant to the responsibilities of this position.

## Concerns
- Candidate is currently completing degrees and may lack full formal education required.
- No direct stated experience with SOC 2 audits or formal GRC platforms like Drata or Vanta.
- Limited explicit experience with control testing and evidence collection for audits.
- No mention of direct experience with internal audits or risk register maintenance.

## Missing qualifications
- 1-3 years of direct Information Security, GRC, or IT Audit experience
- Experience with SOC 2 audit processes
- Experience with GRC platforms (e.g., Drata, Vanta, ZenGRC)
- Relevant professional certifications such as CISA, CC, or CRISC

## Fabrication validator
- Warnings:
  - [strong_adjective] strong-claim phrase 'lead' detected — verify it matches profile reality

## QA pass
- Overall polish: **needs_work**
- HIGH (1):
  - [evidence_gap] cover_letter (opening paragraph); outreach_recruiter subject line; outreach_hiring_manager opening lines
      "Support LVT’s annual SOC 2 audit"
      fix: Don't present direct SOC 2 audit facilitation as a core deliverable unless you have explicit audit participation experience. Rephrase to emphasize directly supported activities you do have evidence for (e.g., 'support audit readiness by collecting and organizing technical evidence, translating findings for control owners, and preparing audit-facing reports') and call out specific artifacts you can share that map to audit needs.
- MEDIUM (2):
  - [overclaiming] tailored_resume — Skills section
      "PCI compliance support"
      fix: Remove or qualify this skill unless you can cite an explicit PCI-related project or outcome. If you have only general compliance exposure, replace with 'familiarity with compliance frameworks (HIPAA, SOC 2 concepts)' or add a brief bullet under experience showing where PCI work occurred.
  - [redundancy] multiple files: tailored_resume (Dillard's bullet), cover_letter paragraph, application_answers, outreach messages
      "built a GitLab SAST-to-Excel reporting workflow that transformed raw findings into organized reports / turned scanner output into clear Excel reports"
      fix: Consolidate and vary the emphasis across documents: use the resume to state the accomplishment and impact (metrics/outcomes), the cover letter to link that impact to the role's audit/control-testing needs, and outreach messages to request a specific next step (share a redacted sample). Avoid repeating the same wording verbatim.
- LOW (1):
  - [redundancy] outreach_hiring_manager (signature block) and outreach_recruiter (signature block)
      "Dillon Stinson

Dillon Stinson"
      fix: Remove duplicate name lines in signatures so each outreach message has a single, clean sign-off.

## JD analysis (used for tailoring)
- **Support LVT’s annual SOC 2 audit, including facilitating communication with control owners and resolving audit concerns**
  - anchor: "Support LVT’s annual SOC 2 audit"
  - evidence (adjacent): experience.dillards_intern.b1 — Helped build a SAST reporting workflow converting raw scanner output into clean reports for stakeholders, improving vulnerability visibility and prioritization.
  - evidence (adjacent): experience.dillards_intern.b4 — Translated technical vulnerability findings into actionable reporting for decision-makers, supporting communication between technical and non-technical stakeholders.
  - evidence (adjacent): experience.nonprofit_health_consultant.b2 — Presented migration risks and security considerations to technical and non-technical stakeholders, helping leadership understand vulnerabilities and escalation paths.
- **Execute control testing and evidence collection to verify security controls are effective**
  - anchor: "Execute control testing, including evidence collection and documentation"
  - evidence (strong): experience.dillards_intern.b1 — Built a SAST reporting workflow that ingested findings from GitLab and converted raw scanner output into clean Excel reports with severity breakdowns and team views.
  - evidence (strong): experience.dillards_intern.b2 — Correlated vulnerability details such as severity and logging dates to improve visibility into remediation priorities.
- **Develop and maintain security policies aligned with organizational standards**
  - anchor: "Develop LVT’s security policies, submitting them for approval, and ensuring alignment with organizational standards"
  - evidence (adjacent): experience.nonprofit_health_consultant.b1 — Mapped workflows and tech environment to security, privacy, and implementation risks during a migration, demonstrating understanding of security policy implications.
  - evidence (adjacent): experience.nonprofit_health_consultant.b2 — Presented security considerations and rollout recommendations to stakeholders, supporting policy and process communication.
- **Maintain and update the risk register to track identified risks and mitigation status**
  - anchor: "Maintain and update the risk register"
  - evidence (adjacent): experience.nonprofit_health_consultant.b1 — Mapped existing workflows and technology environment to potential security, privacy, and implementation risks, indicating risk identification and documentation skills.
- **Execute quarterly user access reviews to ensure appropriate access controls**
  - anchor: "Execute quarterly user access reviews"
- **Communicate effectively with stakeholders including customers and auditors to support GRC processes**
  - anchor: "Facilitate effective communication and coordination with internal SOC 2 control owners"
  - evidence (strong): experience.nonprofit_health_consultant.b2 — Presented migration risks and security considerations to technical and non-technical stakeholders, demonstrating effective communication skills.
  - evidence (strong): experience.dillards_intern.b4 — Translated technical vulnerability findings into actionable reporting for decision-makers, supporting clear communication with stakeholders.
- **Pain points without evidence:**
  - [4] No evidence found of executing quarterly user access reviews or similar access control review processes.
