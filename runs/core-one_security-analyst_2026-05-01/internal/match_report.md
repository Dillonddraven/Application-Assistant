# Match report: Core One — Security Analyst

- Job ID: `57e00f977783`
- Source: https://job-boards.greenhouse.io/coreone/jobs/8483213002
- Source confidence: **high** — direct ATS board (greenhouse.io)
- Location: —  (unknown)
- Industry filter: **avoid** (tags: defense, military, cybersecurity, government)
- **Fit score: 0**
- Breakdown:
  - skills_match: 13
  - preferred_skills_match: 0
  - cert_match: 50
  - experience_match: 30
  - location_match: 55
  - industry_filter: avoid

## Rationale
The candidate has foundational cybersecurity skills and certifications such as CompTIA Security+ and Security+ baseline knowledge. They have experience with vulnerability management, security monitoring, and compliance-related tasks, which align with some responsibilities of the role. However, the job requires active TS/SCI clearance and extensive federal or IC cybersecurity experience, which the candidate does not have.

## Concerns
- No active TS/SCI clearance with Polygraph
- Lacks 3-5 years of cybersecurity experience in federal or Intelligence Community environments
- No CISM, CISA, CAP, or CCSP certifications
- No direct experience with FedRAMP authorization processes or NIST RMF lifecycle management
- No experience with RSA Archer, ServiceNow GRC, or Azure Sentinel
- No demonstrated experience in classified or high-security environments

## Missing qualifications
- Active TS/SCI clearance with Polygraph
- CISM or CISA or Certified Authorization Professional (CAP) or CCSP certification
- 3+ years experience in federal or Intelligence Community cybersecurity environments
- Experience with FedRAMP Moderate/High and IC ATO authorization processes
- Experience with RSA Archer and ServiceNow GRC tools
- Experience with Azure Sentinel or equivalent SIEM tools

## Fabrication validator
- Warnings:
  - [strong_adjective] strong-claim phrase 'lead' detected — verify it matches profile reality

## QA pass
- Overall polish: **needs_work**
- MEDIUM (2):
  - [evidence_gap] tailored_resume: Skills; cover_letter (nonprofit healthcare paragraph)
      ""Security documentation" (Skills) / "I supported leadership with a clear picture of rollout risks and escalation paths..." (cover letter)"
      fix: Don't list "Security documentation" as a blanket skill without clarifying scope. Replace with specific, supported artifacts (e.g., "risk briefings and assessment-objective write-ups for migration planning") or say "familiar with drafting compliance-aligned documentation (presentations, assessment objectives) — no formal SSP/SAR/POA&M experience yet" and offer redacted examples.
  - [overclaiming] outreach_hiring_manager (email body); tailored_resume: Dillard's internship
      ""...which maps to my Dillard's internship work building a GitLab SAST-to-Excel reporting pipeline..." (outreach_hiring_manager)"
      fix: Avoid implying that building SAST reporting equates to performing formal control assessments or RMF/FedRAMP gap analyses. Rephrase to emphasize the true value: e.g., "improved vulnerability triage and prioritization that supports risk assessments" and offer to discuss how that feeds into formal control/gap work.
- LOW (2):
  - [redundancy] cover_letter; tailored_resume (Dillard's entry); outreach_hiring_manager
      "Multiple near-identical descriptions of SAST work: "turned raw code-scanner output into reports..." / "helped turn raw code-scanner output into reports..." / similar phrasing in outreach email"
      fix: Consolidate and vary examples across documents. Use one concise, strong bullet in the resume and reference a different angle (impact, metrics, or a takeaway) in the cover letter and outreach messages to avoid repetition.
  - [filler] application_answers (How many years of professional experience do you have?)
      ""Internship-level plus project-heavy.""
      fix: Give a clearer, recruiter-friendly answer (e.g., "~1 year of internship experience plus multiple independent/academic projects"), or quantify internship months to remove ambiguity.

## JD analysis (used for tailoring)
- **Lead and support FedRAMP Moderate/High and IC ATO authorization processes**
  - anchor: "Lead and support FedRAMP Moderate/High and IC ATO authorization processes"
  - evidence (adjacent): proj_cmmc_nist_docs — Coursework comparing CMMC v1/v2 levels and mapping controls to NIST SP 800-171, demonstrating understanding of compliance frameworks and control mapping.
  - evidence (adjacent): nonprofit_health_consultant.b1 — Mapped workflows and tech environment to security and implementation risks during a planned migration, showing risk assessment and compliance awareness.
- **Develop, review, and maintain security documentation including System Security Plans (SSP), Security Assessment Reports (SAR), and Plan of Action & Milestones (POA&M)**
  - anchor: "Develop, review, and maintain security documentation: System Security Plans (SSP), Security Assessment Reports (SAR), Plan of Action & Milestones (POA&M)"
  - evidence (adjacent): nonprofit_health_consultant.b2 — Presented migration risks and security considerations to stakeholders, indicating experience with security documentation and communication.
  - evidence (adjacent): proj_cmmc_nist_docs — Wrote assessment-objective explanations for monitoring controls and CUI handling, showing documentation skills aligned with compliance requirements.
- **Perform risk assessments, control assessments, and gap analyses to ensure compliance with NIST SP 800-53 / 800-37 RMF and FedRAMP baselines**
  - anchor: "Perform risk assessments, control assessments, and gap analyses"
  - evidence (strong): nonprofit_health_consultant.b1 — Performed risk assessment by mapping workflows and tech environment to security and privacy risks during migration planning.
  - evidence (strong): dillards_intern.b1 — Built SAST reporting workflow that normalized severity and correlated vulnerability details to improve remediation prioritization.
  - evidence (strong): dillards_intern.b2 — Correlated vulnerability details to improve visibility into remediation priorities, supporting risk assessment and management.
- **Execute continuous monitoring strategies and reporting, including tracking and managing POA&M remediation activities**
  - anchor: "Execute continuous monitoring strategies and reporting"
  - evidence (strong): security_automation_projects.b1 — Designed security automation workflows for vulnerability discovery and remediation tracking with alerting and approval gates.
  - evidence (strong): security_automation_projects.b2 — Built monitoring and approval-gate workflows to detect automation failures and route remediation through human review.
- **Support incident response and forensic analysis to investigate and mitigate security events**
  - anchor: "Support incident response and forensic analysis"
  - evidence (adjacent): proj_ir_playbook_cloud_backup — Designed incident response playbook with business impact analysis and recovery prioritization, demonstrating incident response fundamentals.
  - evidence (adjacent): accurate_interpretations_intern.b2 — Performed network traffic analysis with Wireshark to identify anomalies and support troubleshooting, relevant to forensic analysis.
- **Utilize security tools such as Splunk, Sentinel, RSA Archer, and ServiceNow for monitoring, compliance, and reporting**
  - anchor: "Utilize security tools for monitoring and compliance: Splunk, Sentinel, Vulnerability management tools, RSA Archer, ServiceNow"
  - evidence (adjacent): proj_centralized_logging_lab — Deployed Graylog stack with log forwarding and alert conditions for Linux and Windows events, showing experience with security monitoring tools.
  - evidence (adjacent): dillards_intern.b1 — Built SAST reporting workflow using Python and Excel automation to produce stakeholder-ready vulnerability reports.
- **Pain points without evidence:**
  - [0] No direct experience leading FedRAMP or IC ATO authorization processes; only adjacent coursework and risk assessment exposure.
  - [1] No direct experience developing or maintaining formal SSP, SAR, or POA&M documentation; evidence limited to related presentations and coursework.
  - [4] No direct incident response or forensic analysis in production environments; experience limited to coursework and network traffic analysis.
  - [5] No direct experience with Splunk, Sentinel, RSA Archer, or ServiceNow; experience limited to Graylog and Python-based reporting tools.
