# Candidate brief (internal, for you, not the employer)

## Role + company summary

Information Security Analyst (GRC) focused on SOC 2 operations and audit readiness. The team likely coordinates control owners, performs control testing and evidence collection, maintains policies and the risk register, and runs recurring user access reviews. LVT appears to be a technology and SaaS-oriented company; specifics of their product are not stated in the JD. Remote setup and exact team size are not clear from the posting.

## Why this role fits

Your strongest evidence lines up with the audit readiness mechanics: collecting technical evidence, normalizing it, and presenting it clearly to stakeholders. At Dillard's you turned raw SAST findings into decision-ready Excel reports with severity and ownership views, which mirrors evidence collection and control verification. In your nonprofit capstone, you mapped workflows to risks and presented recommendations, which is adjacent to risk register entries and policy-process clarity. Security+ plus your compliance coursework show fundamentals that transfer to SOC 2. You can honestly position yourself as eager to formalize these adjacent skills into SOC 2 control testing and documentation.

## Top 3 talking points

- At Dillard's I built a Python and OpenPyXL workflow that ingested GitLab SAST reports and produced management-ready Excel summaries with severity and team or repo views.
- For a nonprofit healthcare client I designed a low-cost SMS MFA workflow with Twilio Verify and tokenized links and mapped migration risks that I presented to leadership.
- I stood up a Graylog stack with OpenSearch and MongoDB and configured rsyslog and NXLog forwarding with alert conditions for Linux sudo or auth and Windows failed-logon activity.

## What the resume is emphasizing

The resume leads with evidence collection and reporting that map to GRC control testing: SAST-to-Excel pipelines, risk mapping during a migration, and clear stakeholder communication. It highlights Security+ and Network+ to show baseline knowledge, and it grounds policy or compliance mentions in concrete tasks you actually performed. PCI is phrased as support to avoid overclaiming, and SOC 2 is kept as a target area rather than a past deliverable.

## What the cover letter is emphasizing

The cover letter argues you can drive audit readiness by collecting and organizing technical evidence, verifying control behavior at a practical level, and presenting outcomes clearly to control owners and auditors. It connects your SAST reporting and risk mapping to SOC 2 tasks without claiming prior SOC 2 ownership. It offers a redacted sample or mockup of your reporting format to demonstrate how you handle evidence and traceability.

## Claims to be ready to explain

- **Built a GitLab SAST-to-Excel reporting workflow with severity breakdowns and team or repository views** (Resume and Dillard's internship bullet; Project: SAST Vulnerability Reporting + Excel Automation)
  - Python and OpenPyXL, normalized severities, combined outputs from GitLab SAST plus Invicti and ACS where available, grouped by team via mapping data, produced a summary tab and visuals; be ready to describe input format, fields retained, how you handled duplicates, and how stakeholders used the report.
- **Mapped workflows and tech to security and privacy risks during a migration and presented recommendations** (Nonprofit Healthcare capstone bullets)
  - Risk identification across data touchpoints, exposure during rollout phases, and mitigation sequencing; be ready to walk through an example risk, likelihood or impact thinking, and what artifacts you produced for leadership.
- **Designed a low-cost SMS MFA workflow using Twilio Verify and tokenized links** (Nonprofit Healthcare capstone bullet and related project)
  - High-level flow, token TTL and storage, link scoping, handling retries, basic logs for auditability, and why SMS was chosen given constraints; clarify it was HIPAA-aligned design, not a HIPAA audit.
- **Supported PCI compliance via secure code training efforts for developers** (Dillard's internship bullet)
  - Scope was enablement and training support, not owning PCI program or audits; examples include sharing secure coding materials, clarifying scanner findings against PCI expectations, and reinforcing remediation priorities.
- **Centralized logging lab with Graylog, OpenSearch, and MongoDB and alerting for key auth events** (Projects: Centralized Logging Lab)
  - Docker Compose deployment, rsyslog and NXLog configuration, Syslog and GELF inputs, alert rules for sudo or auth and failed-logon attempts; explain how you validated ingestion and tuned noise.
- **Security+ and Network+ certifications** (Certifications section)
  - Security+ issued 2025-12 and Network+ 2024-08; be ready to cite domains most relevant to SOC 2 control testing like risk management basics, access control concepts, and incident response fundamentals.

## Weak spots / gaps + honest answers

- **No direct SOC 2 audit participation or internal audit ownership**
  - Honest answer: I have not directly run SOC 2 activities yet. My adjacent experience is organizing technical evidence and presenting it cleanly for decision-makers. I am ready to formalize that into SOC 2 by following your control catalog, learning your testing procedures, and using your templates to make evidence collection repeatable and audit-ready.
- **No hands-on GRC platform use like Drata, Vanta, or ZenGRC**
  - Honest answer: I have not used those tools in production. I have built structured evidence pipelines in Python and Excel and I understand control-object to evidence mapping. Give me access to your platform and a control or two, and I will ramp quickly using vendor docs and internal playbooks.
- **No explicit experience running quarterly user access reviews**
  - Honest answer: I have not executed formal UAR cycles. I understand the objective and mechanics and can walk through how I would request and validate entitlements from systems like Okta or AD, sample for SoD concerns, and document approvals. I am ready to learn your cadence and evidence standards.
- **Limited evidence of maintaining a live risk register over time**
  - Honest answer: I have done risk identification and documentation in projects, but not ongoing register maintenance. I am comfortable with common fields like likelihood, impact, owner, treatment, and due dates and can keep it current with input from control owners and audit findings.

## 30-second "why are you interested" answer

I like the part of security where you turn messy technical signals into clean, auditable answers. At Dillard's I built reporting that let leaders prioritize fixes without digging through scanner output, and in my nonprofit capstone I mapped migration risks and got everyone on the same page. This role is the formal version of that work for SOC 2. I want to support control owners, collect solid evidence, and keep the risk picture accurate so audits run smoothly and customers can trust the results.

## 60-second "walk me through your background" answer

I am finishing a BS in CIS with a cybersecurity minor and an MS in Cybersecurity at the University of Tulsa. I hold Security+ and Network+. My internships and projects aimed at the day to day GRC and audit readiness work. At Dillard's I built a Python and OpenPyXL pipeline that turned GitLab SAST output into clear reports with severity and ownership views and I supported secure code training tied to PCI expectations. Earlier I did network ops work with Wireshark and firewall or switch configurations. I also ran a Graylog lab with OpenSearch and MongoDB, forwarding logs from Linux and Windows and alerting on key auth activity. In my nonprofit capstone I mapped migration risks and designed an SMS MFA workflow with Twilio Verify and tokenized links, then presented recommendations to leadership. I want to bring that evidence collection, control thinking, and clear communication to LVT and grow into SOC 2 control testing and documentation.

## Questions to ask the recruiter / hiring manager

- What is the current state of your SOC 2 program and where is the biggest bottleneck right now: control testing, evidence collection, or coordinating control owners?
- Which GRC platform or tools are you using for control management, evidence storage, and risk registers, and how mature are your workflows there?
- For the next audit cycle, which specific controls do you expect this role to own or co-own for testing and evidence collection?
- How do you run quarterly user access reviews today and which systems are in scope first?
- What does success look like in the first 90 days for this role and how will it be measured?
- What policy areas are due for refresh or creation this quarter and what is the review or approval process?
- How do you track and triage audit findings or risk register items to closure and who needs to be kept in the loop?
- Are there opportunities to use automation for evidence collection or report generation and where would you want me to start experimenting?

## Claim Stress Test: Likely Interview Questions

For each major claim in the resume, cover letter, outreach messages, and application answers, this section gives likely interview follow-ups, what a strong answer should cover, a confidence rating, and a recommendation. Use it as a truth-check before sending.

### Turns scanner output into decision-ready reports for leadership

- **Where:** tailored_resume — Summary, line 1
- **Confidence:** high
- **Recommendation:** keep
- **Likely follow-up questions:**
    - Which scanners and sources did you convert and how did you obtain the raw data?
    - What fields did you standardize and how did you handle inconsistent severities across tools?
    - What did the final Excel report include (tabs, pivots, visualizations)?
    - How often did you produce these reports and who consumed them?
    - How did you avoid duplicate or stale findings across scans?
- **A strong answer should include:**
    - GitLab SAST JSON or artifact ingestion via API or pipeline export
    - Severity normalization approach and preserving original labels for traceability
    - Excel/OpenPyXL structure: summary tab, repo/team pivots, charts
    - Deduplication strategy across runs using stable identifiers (e.g., file path, rule ID, fingerprint)
    - Stakeholder workflow for review and prioritization

### Maps operational risk during system changes and migrations

- **Where:** tailored_resume — Summary; Experience: Nonprofit Healthcare, bullet 1
- **Confidence:** high
- **Recommendation:** keep
- **Likely follow-up questions:**
    - How did you document current-state workflows and data flows?
    - What concrete risks did you identify and how did you prioritize them?
    - How did you tie risks to controls or mitigation steps?
    - What artifacts did you deliver (risk register, diagrams, RACI, rollout plan)?
- **A strong answer should include:**
    - Workflow/data flow mapping with where sensitive data is handled
    - Risk identification across security, privacy, and implementation
    - Prioritization criteria (impact/likelihood) and proposed mitigations
    - Deliverables that leadership used to sequence rollout safely

### Brings hands-on evidence collection aligned to GRC operations

- **Where:** tailored_resume — Summary, line 2
- **Confidence:** medium
- **Recommendation:** study_before_sending
- **Likely follow-up questions:**
    - What specific control evidence have you collected and for which frameworks?
    - How did you validate authenticity and completeness of evidence?
    - What tools or ticketing systems did you use to track evidence and reviews?
    - How did you handle sampling or period coverage requirements?
- **A strong answer should include:**
    - Examples from SAST reporting as structured evidence artifacts
    - Process for traceability (source, timestamp, owner) and versioning
    - General SOC 2 evidence types and coverage concepts (point-in-time vs period)
    - Workflow with stakeholders for evidence requests and follow-ups

### Designed low-cost SMS MFA workflow using Twilio Verify and tokenized links

- **Where:** tailored_resume — Experience: Nonprofit Healthcare, bullet 3
- **Confidence:** high
- **Recommendation:** keep
- **Likely follow-up questions:**
    - Why SMS and Twilio Verify vs app-based or TOTP MFA for your use case?
    - How does the verification flow work end-to-end and what gets stored?
    - How did you prevent replay of tokenized links and enforce TTL?
    - What HIPAA-aligned considerations did you build in (minimum necessary, audit)?
- **A strong answer should include:**
    - Justification of SMS tradeoffs and cost constraints
    - Twilio Verify start/check flow and data minimization in DB
    - Token TTL, one-time use, rate limiting, and audit logging
    - Separation of PHI from authentication data and role-based access

### Helped build GitLab SAST-to-Excel reporting with severity, team and repo views, visuals

- **Where:** tailored_resume — Experience: Dillard’s, bullet 1
- **Confidence:** high
- **Recommendation:** keep
- **Likely follow-up questions:**
    - How did you pull SAST results (API endpoints or artifacts)?
    - How did you map repos to teams for grouping?
    - What visualizations or pivots proved most useful to stakeholders?
    - How did you handle scanner rule changes across versions?
- **A strong answer should include:**
    - Data fetch method and input schema understanding
    - Team-repo mapping source (lookup file or naming convention)
    - Concrete report structure and visuals used in briefings
    - Handling rule changes and maintaining comparability across runs

### Correlated severity and logging dates to sharpen remediation priorities

- **Where:** tailored_resume — Experience: Dillard’s, bullet 2
- **Confidence:** high
- **Recommendation:** keep
- **Likely follow-up questions:**
    - Which dates did you correlate (created, updated, first_seen) and why?
    - How did you distinguish reopened issues from net-new?
    - How was this surfaced in the report for prioritization?
- **A strong answer should include:**
    - Definition of the date fields available and chosen
    - Logic for reopened vs net-new and aging buckets
    - Report views that highlighted recency and aging to guide action

### Translated technical vulnerability details into actionable summaries for decision-makers

- **Where:** tailored_resume — Experience: Dillard’s, bullet 3
- **Confidence:** high
- **Recommendation:** keep
- **Likely follow-up questions:**
    - What did an actionable summary look like and who was the audience?
    - How did you balance technical depth with clarity?
    - What decisions did these summaries enable?
- **A strong answer should include:**
    - Example summary structure with risk, owner, and next steps
    - Level-of-detail tailoring for exec vs engineering audiences
    - Concrete decisions informed (prioritization, sprint planning)

### Can support SOC 2 audit with evidence collection and control verification

- **Where:** cover_letter — paragraph 1; outreach_recruiter
- **Confidence:** medium
- **Recommendation:** study_before_sending
- **Likely follow-up questions:**
    - Which SOC 2 trust services criteria and control areas are you most familiar with?
    - How would you structure an evidence request to a control owner?
    - Describe your approach to testing design vs operating effectiveness.
- **A strong answer should include:**
    - Familiarity with common SOC 2 control families (access, change, vulnerability mgmt)
    - Clear evidence request templates and follow-up cadence
    - High-level methodology for walkthroughs, sampling, and testing OE

### SAST reporting gave teams a single view of severity and ownership that sped triage

- **Where:** cover_letter — paragraph 2
- **Confidence:** medium
- **Recommendation:** soften
- **Likely follow-up questions:**
    - How did you measure that triage sped up?
    - What changed in the remediation process after your reports?
    - Who owned remediation and how was ownership assigned in the report?
- **A strong answer should include:**
    - Anecdotal or qualitative before/after examples even if not quantified
    - Description of ownership mapping and how teams used it
    - Specific meeting cadence or workflow that became more efficient

### Migration risk mapping clarified sensitive data touchpoints and sequencing to manage exposure

- **Where:** cover_letter — paragraph 3
- **Confidence:** high
- **Recommendation:** keep
- **Likely follow-up questions:**
    - What specific data touchpoints were most sensitive and why?
    - What sequencing decisions did leadership make based on your mapping?
    - What safeguards did you recommend during rollout?
- **A strong answer should include:**
    - Concrete examples of PHI touchpoints and associated risks
    - How sequencing reduced exposure windows or blast radius
    - Safeguards like MFA gating, least privilege, and audit logging

### Can share a sanitized SAST report sample and SMS MFA workflow outline

- **Where:** cover_letter — closing paragraph
- **Confidence:** medium
- **Recommendation:** study_before_sending
- **Likely follow-up questions:**
    - Can you walk us through the sample now and explain each section?
    - How did you sanitize the report while preserving usefulness?
    - Can you diagram the MFA flow and token lifecycle?
- **A strong answer should include:**
    - Prepared redacted or mock sample with clear sections and notes
    - Sanitization approach that removes identifiers but retains structure
    - Diagram or step-by-step MFA flow with security controls

### Built an IR playbook from BIA and documented control mappings; prepared to document control effectiveness

- **Where:** application_answers — Q1
- **Confidence:** medium
- **Recommendation:** soften
- **Likely follow-up questions:**
    - What did your BIA identify as critical and how did that drive IR steps?
    - Which controls did you map and to what framework?
    - How would you evidence control effectiveness versus just existence?
- **A strong answer should include:**
    - IR playbook structure tied to critical business functions
    - NIST 800-171/CMMC mapping scope and artifacts produced
    - Approach to testing and evidencing OE (tickets, logs, samples)

### Experience with control testing and evidence collection via SAST reporting workflow

- **Where:** application_answers — Q2
- **Confidence:** high
- **Recommendation:** keep
- **Likely follow-up questions:**
    - How does SAST reporting relate to SOC 2 control testing?
    - What would you change to adapt your process for audit evidence?
    - How did you ensure repeatability and integrity of the output?
- **A strong answer should include:**
    - Mapping SAST outputs to vulnerability mgmt control objectives
    - Adjustments for audit trails, timestamps, and approvals
    - Repeatable script-driven process and versioned outputs

### Policy/risk work and stakeholder communication during nonprofit migration

- **Where:** application_answers — Q3
- **Confidence:** high
- **Recommendation:** keep
- **Likely follow-up questions:**
    - What policies or standards did your recommendations reference?
    - How did you present to mixed technical and non-technical groups?
    - What escalations or decision gates did you propose?
- **A strong answer should include:**
    - Reference to HIPAA-aligned safeguards and internal policy implications
    - Communication artifacts tailored by audience
    - Clear escalation paths and decision checkpoints

### Holds CompTIA Security+

- **Where:** application_answers — Do you hold CompTIA Security+?
- **Confidence:** high
- **Recommendation:** keep
- **Likely follow-up questions:**
    - When did you earn it and what areas did you find most challenging?
    - How have you applied Security+ concepts in projects or internships?
- **A strong answer should include:**
    - Issue date (2025-12) and brief study highlights
    - Concrete application examples (access control, risk management)

### Built the pipeline that turned GitLab output into structured evidence for control owners

- **Where:** outreach_hiring_manager — paragraph 1
- **Confidence:** medium
- **Recommendation:** soften
- **Likely follow-up questions:**
    - What parts did you personally implement versus the team?
    - How was this evidence consumed by control owners specifically?
    - What made it suitable as auditable evidence?
- **A strong answer should include:**
    - Your specific contributions vs team’s contributions
    - Clarify stakeholders (security leads, engineering managers) and use cases
    - Traceability and reproducibility features qualifying it as evidence

### Normalized severities while preserving original scanner labels for traceability

- **Where:** outreach_hiring_manager — paragraph 2, sentence 1
- **Confidence:** medium
- **Recommendation:** study_before_sending
- **Likely follow-up questions:**
    - What normalization scheme did you use and why?
    - Where did you store the original labels and how did reviewers see them?
    - How did you handle tools with non-standard severities?
- **A strong answer should include:**
    - Description of mapping table and chosen canonical scale
    - UI/report design showing both normalized and original labels
    - Handling edge cases and unknown mappings

### Keyed findings by repo, path, and rule to avoid double counting; separated reopened vs net-new; reduced churn

- **Where:** outreach_hiring_manager — paragraph 2, sentences 2-3
- **Confidence:** low
- **Recommendation:** soften
- **Likely follow-up questions:**
    - Exactly which fields formed the deduplication key and why?
    - How did you detect reopened vs net-new in practice?
    - What evidence do you have that churn was reduced?
- **A strong answer should include:**
    - Clear dedup logic with rationale and limitations
    - Method for reopened detection based on timestamps or fingerprints
    - Anecdotal before/after or process change explanation

### I can execute control testing and I built a GitLab SAST reporting workflow

- **Where:** linkedin_dm — entire message
- **Confidence:** medium
- **Recommendation:** soften
- **Likely follow-up questions:**
    - What control tests have you personally executed end-to-end?
    - What did you own in the SAST reporting workflow build?
    - How would you adapt your experience to quarterly access reviews?
- **A strong answer should include:**
    - Examples of test steps you would execute even if coursework-based
    - Clarify that you helped build the SAST workflow and your contributions
    - A general approach for access reviews even if you have not done them

### HIPAA-aligned security considerations

- **Where:** tailored_resume — Skills section
- **Confidence:** medium
- **Recommendation:** study_before_sending
- **Likely follow-up questions:**
    - Which HIPAA Security Rule safeguards did your design address?
    - How did you limit exposure to PHI in your workflow?
    - Did you consider BAAs and vendor responsibilities (e.g., with Twilio)?
- **A strong answer should include:**
    - Administrative, physical, and technical safeguards you touched
    - Data minimization, access control, audit logging in the design
    - Awareness of BAAs and vendor risk considerations

### PCI compliance support

- **Where:** tailored_resume — Skills section
- **Confidence:** medium
- **Recommendation:** study_before_sending
- **Likely follow-up questions:**
    - Which PCI DSS requirements were relevant to your support work?
    - What did your secure code training support include?
    - How was completion or effectiveness tracked?
- **A strong answer should include:**
    - High-level PCI DSS secure coding requirements relevance
    - Your role supporting training logistics/content alignment
    - How outcomes were tracked (attendance, assessments, follow-ups)

## Claims to Remove or Soften Before Sending

### SAST reporting sped triage and made remediation conversations more direct

- **Where:** cover_letter — paragraph 2
- **Why:** Impact is asserted without measurable evidence in the profile.
- **Suggested action:** Soften to: "provided a centralized view of severity and ownership that streamlined triage discussions."

### Prepared to document control effectiveness

- **Where:** application_answers — Q1
- **Why:** Implies formal control testing experience that is not directly evidenced.
- **Suggested action:** Soften to: "prepared to collect evidence and support documentation of control implementation and effectiveness indicators."

### Built the pipeline that turned GitLab output into structured evidence for control owners

- **Where:** outreach_hiring_manager — paragraph 1
- **Why:** Overstates ownership and targets 'control owners' specifically, which is not established.
- **Suggested action:** Soften to: "helped build a pipeline that organized GitLab output into structured evidence for stakeholders."

### Keyed findings by repo, path, and rule to avoid double counting; separated reopened vs net-new; reduced churn

- **Where:** outreach_hiring_manager — paragraph 2
- **Why:** Introduces specific implementation details and impact not supported explicitly in the profile.
- **Suggested action:** Soften to: "reduced duplicate counting across runs using stable identifiers where available and surfaced recency to focus discussions."

### I built a GitLab SAST reporting workflow

- **Where:** linkedin_dm — sentence 2
- **Why:** Conflicts with "helped build" phrasing supported by experience.
- **Suggested action:** Soften to: "I helped build a GitLab SAST reporting workflow."
