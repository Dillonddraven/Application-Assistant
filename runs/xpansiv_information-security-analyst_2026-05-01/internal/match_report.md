# Match report: Xpansiv — Information Security Analyst

- Job ID: `bfad0445f7c8`
- Source: https://jobs.lever.co/Xpansiv%20/6652760b-5fda-44dc-a3e6-2d853886bdf8
- Source confidence: **high** — direct ATS board (lever.co)
- Location: Remote U.S.  (remote)
- Industry filter: **ok** (tags: energy, environmental commodities, fintech, saas)
- **Fit score: 46**
- Breakdown:
  - skills_match: 20
  - preferred_skills_match: 25
  - cert_match: 100
  - experience_match: 30
  - location_match: 100
  - industry_filter: ok

## Rationale
The candidate has foundational skills in cybersecurity, vulnerability management, incident response, and scripting, aligning with many of the job's technical requirements. Their experience with security automation and risk analysis supports the responsibilities of monitoring and improving security posture. However, the candidate is still completing their degrees and has less than the required 3 years of hands-on cybersecurity experience.

## Concerns
- Currently in-progress Bachelor and Master degrees, not completed
- Less than 3 years of hands-on cybersecurity experience
- No direct experience stated with cloud platforms AWS, Azure, or GCP
- No explicit experience with SIEM platforms or common EDR tools
- No direct experience with compliance audits such as SOC 2 or ISO 27001
- Certifications held (CompTIA Security+, Network+) are relevant but not among preferred advanced certs like CySA+ or CEH

## Missing qualifications
- 3–5 years of hands-on cybersecurity or IT risk experience
- Bachelor’s degree in Information Security, Computer Science, or related field (completed)
- Experience with SIEM platforms
- Experience with common EDR platforms
- Experience with cloud security on AWS, Azure, or GCP
- Familiarity with compliance audits (SOC 2, ISO 27001)
- Preferred certifications such as CySA+ or CEH

## Fabrication validator
- Clean: no blocks, no warnings.

## QA pass
- Overall polish: **needs_work**
- HIGH (1):
  - [internal_metadata] Top of packet
      "JD_ANALYSIS:
  [0] Monitor, investigate, and respond to security alerts and incidents across systems, networks, and cloud environments
  ...
  Pain points to leave OUT (no supporting evidence):
    - pain_point[2]: No direct evidence of implementing secure configurations, code reviews, or cloud security best practices in collaboration with IT, DevOps, and engineering teams.
    - pain_point[3]: No direct evidence of conducting access reviews or supporting formal audit and compliance efforts beyond coursework and presentations."
      fix: Remove the JD_ANALYSIS block and any internal notes before sending. Only include candidate-facing materials (resume, cover letter, answers). Keep internal mapping in a separate file not shared with employers.
- MEDIUM (3):
  - [internal_metadata] Section separators throughout packet
      "=== tailored_resume ===
=== cover_letter ===
=== application_answers ===
=== outreach_recruiter ===
=== outreach_hiring_manager ===
=== linkedin_dm ==="
      fix: Delete internal section markers from the files/emails you send. Present each document (resume, cover letter, messages) as clean, standalone content without developer/authoring scaffolding.
  - [overclaiming] tailored_resume — Summary
      "Security analyst focused on monitoring and vulnerability reporting, with hands-on SAST-to-report workflows, centralized logging and alerting, and SMS MFA design for stronger access control."
      fix: Soften the title to reflect experience level (e.g., 'Aspiring/Entry-level security analyst' or 'Early-career security professional'). Briefly indicate internships and projects that back up the skills to avoid implying longer professional tenure.
  - [evidence_gap] application_answers — 'How has your education and project work prepared you for this role?' and overall materials
      "Combined with my Dillard's internship work on SAST ingestion and vulnerability reporting, my Graylog and OpenSearch centralized logging lab with rsyslog and NXLog forwarding and alerts, Wireshark-based traffic analysis ..., and CMMC v2 and NIST SP 800-171 documentation work, I am ready to monitor events, triage findings, and escalate when needed."
      fix: The JD asks for collaboration with IT/DevOps and support for audits/access reviews. You don't have direct, documented experience running formal access reviews or partnering on secure configuration/code review programs. Reframe as: emphasize stakeholder communication and coursework, call out any instances you worked with repo owners / admins (if true), or explicitly state you're experienced in monitoring and reporting and eager to apply those skills to cross-team secure-configuration and audit tasks.
- LOW (1):
  - [tone] linkedin_dm
      "Information Security Analyst fit to Perform regular vulnerability assessments, patch verification, and risk remediation tracking. At Dillard's I built a GitLab SAST reporting workflow that turned scanner output into management-ready summaries. Is your team still hiring for this?"
      fix: The DM reads like pasted JD text and is slightly awkward. Make it shorter and more conversational (one line about fit + one question). Personalize the opener (name/company) and avoid title-case JD fragments.

## JD analysis (used for tailoring)
- **Monitor, investigate, and respond to security alerts and incidents across systems, networks, and cloud environments**
  - anchor: "Monitor, investigate, and respond to security alerts and incidents"
  - evidence (strong): experience.security_automation_projects.b1 — Designed security-focused automation workflows for vulnerability discovery and remediation tracking, using structured logs, alerting, and approval gates to improve visibility across automated systems.
  - evidence (strong): experience.security_automation_projects.b2 — Built security monitoring and approval-gate workflows to detect automation failures, flag risky actions, and route remediation steps through human review.
  - evidence (adjacent): experience.accurate_interpretations_intern.b2 — Performed onsite network traffic analysis with Wireshark to identify anomalies, support troubleshooting, and strengthen secure network operations.
  - evidence (strong): projects.proj_centralized_logging_lab — Deployed Graylog stack with alert conditions for Linux sudo/auth activity and Windows failed-logon attempts, demonstrating monitoring and alerting capabilities.
- **Perform regular vulnerability assessments, patch verification, and risk remediation tracking**
  - anchor: "Perform regular vulnerability assessments, patch verification, and risk remediation tracking"
  - evidence (strong): experience.dillards_intern.b1 — Helped build a SAST reporting workflow that ingested findings from GitLab repositories and converted raw scanner output into clean Excel reports with severity breakdowns and team views.
  - evidence (strong): experience.dillards_intern.b2 — Correlated vulnerability details such as severity and logging dates to improve visibility into remediation priorities.
  - evidence (strong): projects.proj_sast_xlsx — Developed Python tooling to normalize severity, color-code findings, and build management-ready reports combining multiple vulnerability scanners.
- **Collaborate with IT, DevOps, and engineering teams to implement secure configurations, code reviews, and cloud security best practices**
  - anchor: "Collaborate with IT, DevOps, and engineering teams on security"
  - evidence (adjacent): experience.r1649_intern.b2 — Supported software security operations by identifying potential risks and helping protect proprietary APIs and internal tools.
  - evidence (adjacent): experience.nonprofit_health_consultant.b1 — Mapped workflows and tech environment to security, privacy, and implementation risks during a planned migration, indicating collaboration with technical teams.
  - evidence (adjacent): experience.nonprofit_health_consultant.b2 — Presented migration risks and security considerations to technical and non-technical stakeholders, supporting cross-team communication.
- **Support audit and compliance efforts including conducting access reviews and contributing to risk assessments and control testing**
  - anchor: "Conduct periodic access reviews and support audit and compliance efforts"
  - evidence (adjacent): projects.proj_cmmc_nist_docs — Coursework comparing CMMC v2 and NIST SP 800-171 controls, analyzing self-assessment implications, and writing assessment-objective explanations for monitoring controls and CUI handling.
  - evidence (adjacent): experience.nonprofit_health_consultant.b2 — Presented security risks and rollout recommendations to leadership, helping them understand vulnerabilities and escalation paths, relevant to compliance communication.
- **Stay current on emerging threats, vulnerabilities, and regulatory requirements impacting the business**
  - anchor: "Stay current on emerging threats, vulnerabilities, and regulatory requirements"
  - evidence (strong): reusable_answers.security_logs_experience — Configured log forwarding and alerting in a centralized logging environment, gaining hands-on experience with event ingestion, classification, and investigation.
  - evidence (adjacent): projects.proj_cmmc_nist_docs — Studied security frameworks and regulatory requirements, supporting knowledge of compliance and emerging standards.
  - evidence (adjacent): experience.dillards_intern.b4 — Translated technical vulnerability findings into actionable reporting for decision-makers, demonstrating awareness of evolving threats and communication.
- **Manage endpoint security tools and identity/access management systems**
  - anchor: "Manage endpoint security tools and identity/access management"
  - evidence (strong): experience.nonprofit_health_consultant.b3 — Designed a low-cost SMS MFA workflow using Twilio Verify and tokenized links to strengthen access control, demonstrating experience with identity and access management.
  - evidence (adjacent): experience.r1649_intern.b2 — Supported software security operations including protecting proprietary APIs and internal tools, relevant to endpoint and access security.
- **Pain points without evidence:**
  - [2] No direct evidence of implementing secure configurations, code reviews, or cloud security best practices in collaboration with IT, DevOps, and engineering teams.
  - [3] No direct evidence of conducting access reviews or supporting formal audit and compliance efforts beyond coursework and presentations.
