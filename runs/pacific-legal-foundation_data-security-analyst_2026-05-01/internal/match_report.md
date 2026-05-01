# Match report: Pacific Legal Foundation — Data Security Analyst

- Job ID: `e96ec639e44d`
- Source: https://job-boards.greenhouse.io/pacificlegalfoundation/jobs/4183667009
- Source confidence: **high** — direct ATS board (greenhouse.io)
- Location: Arlington, Virginia  (hybrid)
- Industry filter: **ok** (tags: legal, nonprofit, cybersecurity, it support)
- **Fit score: 35**
- Breakdown:
  - skills_match: 0
  - preferred_skills_match: 0
  - cert_match: 100
  - experience_match: 80
  - location_match: 30
  - industry_filter: ok

## Rationale
The candidate has relevant experience in security automation, IT support, and vulnerability management, along with strong scripting and technical skills. Their background in security fundamentals and customer-facing roles aligns with the hybrid IT support and entry-level security operations focus of the role. The candidate's interest in cybersecurity and technical problem-solving matches the job's learning and development opportunities.

## Concerns
- Candidate's current certifications do not include Security+ or other security certifications explicitly required or preferred by the role.
- Candidate's experience is more focused on security automation and vulnerability management rather than direct help desk or IT support roles.
- The role requires onsite presence in Arlington, VA, which may be a concern depending on candidate's location and availability.

## Missing qualifications
- 1-3 years of direct help desk or IT support experience with ticketing systems
- Experience with Freshdesk, Zendesk, ServiceNow or similar ticketing systems
- Security certifications such as Security+ or Okta (willingness to earn is noted but not yet obtained)
- Experience with Microsoft 365, Salesforce, Okta, Azure AD/Entra, or Intune

## Fabrication validator
- Warnings:
  - [strong_adjective] strong-claim phrase 'lead' detected — verify it matches profile reality

## QA pass
- Overall polish: **needs_work**
- HIGH (3):
  - [evidence_gap] outreach_recruiter / linkedin_dm
      "Serve as primary IT support for DC office staff maps to my onsite troubleshooting work."
      fix: Don't imply you can be the 'primary' onsite IT contact without showing sustained helpdesk ownership. Either remove the 'primary' framing or add concrete evidence (ticketing system used, typical ticket volume, examples of onboarding/offboarding tasks you handled, asset tagging/checkout lists you maintained, or that you staffed an office helpdesk shift).
  - [evidence_gap] tailored_resume (Experience & Skills)
      "No mention of hardware inventory, device lifecycle, asset tagging, MDM, or managing peripherals in Experience or Skills."
      fix: The JD asks explicitly for hardware inventory/device lifecycle work. If you have any experience (even limited) — add a bullet: e.g., 'Maintained asset inventory (XX devices) using [tool/Excel sheet], prepared devices for new hires, handled returns/wiping and redeployment.' If you don't, remove or avoid claiming hardware-related responsibilities in outreach/cover materials and state willingness to learn or train on asset management systems.
  - [evidence_gap] cover_letter / tailored_resume
      "Coordinating onboarding logistics including parking passes, metro cards, and physical security access (key fobs) — no supporting examples in materials."
      fix: Don't suggest you handle logistical onboarding items unless you can cite specific examples. Either add a short example (e.g., 'Coordinated issuing of keycards and temporary access for X new hires') or rephrase to focus on technical provisioning experience you do have (MFA, account provisioning workflows) and state you can coordinate with facilities/security on physical access.
- MEDIUM (1):
  - [overclaiming] cover_letter / application_answers
      ""I built a centralized logging lab that produced practical alerting on authentication activity..." (presented as production-ready capability)"
      fix: Clarify scope: if this was a personal lab, label it as a lab/project (e.g., 'personal Graylog/OpenSearch lab') and note its scale and purpose. Employers care whether tooling was run in production, supported real users, or was a proof-of-concept. State limits (number of hosts, simulated vs real traffic) or tie it to a measurable outcome.
- LOW (2):
  - [redundancy] cover_letter / outreach_hiring_manager / application_answers
      "Multiple near-identical descriptions of the 'centralized logging lab' and Graylog alerting appear across documents."
      fix: Consolidate: keep one concise, consistent phrasing of the Graylog/centralized logging project in the resume, and in other documents reference it briefly with an offer to share the one-page lab writeup. This reduces repetition and lets each document highlight a different strength.
  - [tone] cover_letter
      ""I am available this week on Wednesday or Thursday between 1 and 4 pm ET to discuss how this experience would support PLF's DC office.""
      fix: Avoid overly prescriptive availability in an initial cover letter. Offer general availability windows or say 'I'd welcome a conversation — I'm flexible and can accommodate your schedule' or ask them to suggest times.

## JD analysis (used for tailoring)
- **Provide primary IT support for DC office staff including troubleshooting and resolving general technical issues**
  - anchor: "Serve as primary IT support for DC office staff"
  - evidence (adjacent): nonprofit_health_consultant.b2 — Presented migration risks and security considerations to technical and non-technical stakeholders, demonstrating communication and support skills.
  - evidence (strong): accurate_interpretations_intern.b1 — Built and maintained secure computer networks onsite while troubleshooting performance and connectivity issues.
  - evidence (adjacent): accurate_interpretations_intern.b2 — Performed network traffic analysis to support troubleshooting and strengthen secure operations.
- **Manage IT hardware inventory and device lifecycle to ensure availability and prevent waste**
  - anchor: "Manage IT hardware inventory: monitors, keyboards & mice, cables, and other peripherals"
  - evidence (adjacent): nonprofit_health_consultant.b3 — Designed secure access workflows including tokenized links and database-backed forms, showing experience managing secure systems and related resources.
- **Assist with onboarding and separation workflows including provisioning and deprovisioning system access and coordinating physical security access**
  - anchor: "Coordinate onboarding logistics including parking passes, metro cards, and physical security access (key fobs)"
  - evidence (adjacent): nonprofit_health_consultant.b1 — Mapped workflows and tech environment to security and implementation risks during a planned migration, indicating understanding of onboarding and access control risks.
  - evidence (strong): nonprofit_health_consultant.b3 — Designed SMS MFA workflow to strengthen access control, showing practical experience with access provisioning.
- **Support monitoring activities to identify anomalies, inappropriate data access, or potential policy violations**
  - anchor: "Supporting monitoring activities to identify anomalies, inappropriate data access, or potential policy violations"
  - evidence (strong): security_automation_projects.b1 — Designed security automation workflows for vulnerability discovery and remediation tracking with alerting and approval gates.
  - evidence (strong): security_automation_projects.b2 — Built monitoring and approval-gate workflows to detect automation failures and flag risky actions.
  - evidence (strong): proj_centralized_logging_lab — Deployed centralized logging with alert conditions for authentication and failed logon events.
- **Help maintain security documentation and incident response materials to support security operations**
  - anchor: "Helping maintain PLF’s access control program by assisting with least-privilege reviews, entitlement checks, and regular access audits"
  - evidence (strong): dillards_intern.b1 — Helped build SAST reporting workflow converting raw scanner output into clean reports with severity breakdowns and stakeholder views.
  - evidence (strong): dillards_intern.b4 — Translated technical vulnerability findings into actionable reporting for decision-makers.
  - evidence (adjacent): nonprofit_health_consultant.b2 — Presented migration risks and rollout recommendations to stakeholders, supporting documentation and communication.
- **Communicate effectively with non-technical staff to explain technical concepts and support security awareness and compliance activities**
  - anchor: "Excellent communication skills and professional fluency in English (written and verbal) to effectively handle documentation, incident response, and explain technical concepts to non-technical staff"
  - evidence (strong): dillards_intern.b4 — Translated technical vulnerability findings into actionable reporting for decision-makers, demonstrating communication skills.
  - evidence (strong): nonprofit_health_consultant.b2 — Presented technical and non-technical stakeholders with security considerations, showing ability to explain technical concepts clearly.
- **Pain points without evidence:**
  - [1] No direct evidence of managing IT hardware inventory and device lifecycle; closest is secure access workflow design but not hardware inventory.
