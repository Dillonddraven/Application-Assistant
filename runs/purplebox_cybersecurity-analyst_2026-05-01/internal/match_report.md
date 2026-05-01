# Match report: PurpleBox — Cybersecurity Analyst

- Job ID: `4e801786ae6c`
- Source: https://jobs.smartrecruiters.com/PurpleBoxInc/743999936212683-cybersecurity-analyst
- Source confidence: **high** — direct ATS board (smartrecruiters.com)
- Location: —  (unknown)
- Industry filter: **ok** (tags: technology consulting, cybersecurity, cloud computing, devops)
- **Fit score: 47**
- Breakdown:
  - skills_match: 14
  - preferred_skills_match: 8
  - cert_match: 100
  - experience_match: 100
  - location_match: 55
  - industry_filter: ok

## Rationale
The candidate has experience and skills in vulnerability management, scripting, security monitoring, and technical risk analysis, which align with the job responsibilities. Their background in security automation and incident response fundamentals supports the role's requirements. The candidate's willingness to learn and diverse technical skills fit the company's emphasis on learning and teamwork.

## Concerns
- Candidate's degrees are in progress, not completed
- No direct mention of experience with specific tools like Qualys, Tenable, Rapid7, Kali, Metasploit
- No listed certifications such as OSCP, OSCE, CEH, or AWS Security Specialty
- Unclear level of experience with penetration testing and ethical hacking

## Missing qualifications
- Completed degree in Computer Science, Computer Engineering, IT Management or similar
- Experience with Qualys, Tenable, Rapid7 vulnerability management tools
- Experience with penetration testing tools such as Kali, Metasploit
- Certifications like OSCP, OSCE, CEH, AWS Security Specialty

## Fabrication validator
- Warnings:
  - [strong_adjective] strong-claim phrase 'lead' detected — verify it matches profile reality

## QA pass
- Overall polish: **needs_work**
- MEDIUM (2):
  - [evidence_gap] application_answers — "How many years of professional experience do you have?"
      "Internship-level plus project-heavy. I am finishing a BS in Computer Information Systems and an MS in Cybersecurity at the University of Tulsa."
      fix: Give a clear, numeric summary of experience (e.g., "~1 year of internship experience + ongoing independent projects") and briefly separate internship vs. personal projects so reviewers can quickly assess level.
  - [redundancy] tailored_resume, cover_letter, outreach_recruiter, linkedin_dm
      "SAST reporting workflow described repeatedly across resume, cover letter, and multiple outreach messages (similar wording about converting GitLab findings into Excel summaries)."
      fix: Keep one canonical, concise description in the resume and vary the phrasing in outreach/cover letter to highlight different outcomes or audience impact (e.g., one message emphasizes technical implementation, another the stakeholder impact).
- LOW (2):
  - [generic_phrase] tailored_resume — Summary
      "Brings Python-based reporting automation, monitoring guardrails, and clear communication for technical and non-technical audiences."
      fix: Replace the generic 'clear communication...' phrasing with a short concrete example or metric from your materials (e.g., 'produced stakeholder-ready SAST summaries that reduced triage time by X' or 'presented migration risks to leadership, influencing rollout decisions').
  - [tone] outreach_recruiter and linkedin_dm
      "I can share a one-page writeup... are you the right contact for this role, or could you point me to the right person? / Is your team still hiring for this?"
      fix: Personalize these messages to the recipient or team (reference PurpleBox-specific work, a team name, or a recent announcement) and shorten the ask to a single clear call-to-action (e.g., 'Would you be open to a 15-min call?').

## JD analysis (used for tailoring)
- **Provide engineering, architecture design, assessment, and technical support for projects**
  - anchor: "provide engineering, architecture design, assessment, and technical support"
  - evidence (strong): nonprofit_health_consultant.b1 — Mapped workflows and tech environment to security risks during migration, demonstrating assessment and design skills.
  - evidence (adjacent): r1649_intern.b2 — Supported software security operations by identifying risks and helping protect proprietary APIs and internal tools.
- **Run daily processes and tools for managing cybersecurity including Vulnerability Management, Security Logging, Monitoring, and Incident Response**
  - anchor: "run daily processes and tools for managing cybersecurity"
  - evidence (strong): dillards_intern.b1 — Built a SAST reporting workflow ingesting findings and converting raw scanner output into clean reports for vulnerability management.
  - evidence (strong): security_automation_projects.b1 — Designed security automation workflows for vulnerability discovery and remediation tracking with alerting and approval gates.
  - evidence (strong): security_automation_projects.b2 — Built monitoring and approval-gate workflows to detect automation failures and route remediation through human review.
  - evidence (strong): proj_centralized_logging_lab — Deployed centralized logging with alert conditions for Linux and Windows authentication events.
- **Perform penetration testing, ethical hacking, and security assessments against Networks, Web Applications, API, Mobile Applications, IoT Devices, and Public Cloud Infrastructure**
  - anchor: "perform penetration testing, ethical hacking, and security assessments"
  - evidence (strong): dillards_intern.b1 — Helped build SAST reporting workflow converting raw scanner output into actionable reports, supporting vulnerability assessment.
  - evidence (adjacent): r1649_intern.b2 — Supported software security operations including risk identification and API protection, adjacent to penetration testing.
- **Collaborate in creation of technical collateral and provide training in your area of expertise**
  - anchor: "collaborate in the creation of technical collateral and provide training"
  - evidence (strong): nonprofit_health_consultant.b2 — Presented migration risks and security considerations to technical and non-technical stakeholders, demonstrating communication and training support.
  - evidence (strong): dillards_intern.b3 — Supported secure code training efforts to help developers meet PCI compliance expectations.
- **Write, review, and edit reports, use cases, and system documentation**
  - anchor: "write, review, and edit reports and system documentation"
  - evidence (strong): dillards_intern.b4 — Translated technical vulnerability findings into actionable reporting for decision-makers.
  - evidence (strong): nonprofit_health_consultant.b2 — Presented findings and recommendations to leadership, improving understanding of security risks.
- **Pain points without evidence:**
  - [2] No direct evidence of performing penetration testing or ethical hacking; candidate has adjacent experience in risk identification and software security operations.
