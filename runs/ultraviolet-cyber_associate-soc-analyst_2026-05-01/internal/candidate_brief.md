# Candidate brief (internal, for you, not the employer)

## Role + company summary

Associate SOC Analyst at UltraViolet Cyber is an entry-level, remote role on a 24x7 security operations team. You would monitor logs and network traffic, triage and escalate incidents, support vulnerability scanning, and write clear incident reports. The posting does not list their exact SIEM or tool stack, but expects Windows/Linux knowledge, strong communication, and shift coverage.

## Why this role fits

Your Graylog lab gives you practical experience forwarding logs from Linux and Windows and alerting on authentication activity, which maps directly to the monitoring and triage asks. The Dillard's internship is solid evidence that you can turn scanner output into clear remediation guidance, which supports their vulnerability scan and reporting needs. Your Wireshark work shows you can analyze traffic to spot anomalies. The nonprofit capstone proves you can brief different stakeholders clearly. Security+ plus Python automation are aligned with their preferred skills and will help you ramp quickly on their SIEM and ticketing tools.

## Top 3 talking points

- Built a centralized logging lab with Graylog, rsyslog, and NXLog that alerted on Linux sudo/auth events and Windows failed logons, giving me end-to-end exposure to event generation, forwarding, alerting, and basic triage.
- At Dillard's I helped build a GitLab SAST to Excel reporting pipeline in Python (OpenPyXL) with severity normalization and team/repo mapping, so engineering leaders saw clear priorities instead of raw scanner output.
- For a nonprofit healthcare client I implemented secure access patterns with Twilio Verify SMS MFA and tokenized links in a WordPress/PHP plugin, then presented risk and rollout recommendations to technical and non-technical leaders.

## What the resume is emphasizing

The resume leads with monitoring and analysis you can speak to confidently: Graylog lab alerts, Wireshark traffic analysis, and the Dillard's SAST reporting workflow. It shows you can investigate signals, turn them into action-ready summaries, and communicate clearly across Linux and Windows environments.

## What the cover letter is emphasizing

The cover letter argues fit for real-time monitoring and crisp escalation, grounding it with one concrete alerting example from the Graylog lab and one concrete reporting example from Dillard's. It also highlights stakeholder communication from the nonprofit project to show you can brief customers and seniors clearly.

## Claims to be ready to explain

- **Configured Graylog with rsyslog and NXLog to alert on Linux sudo/auth and Windows failed-logon events** (Resume summary, projects.proj_centralized_logging_lab, cover letter)
  - Be explicit that this was a lab on Proxmox VMs. Outline inputs you configured, the high-level alert condition logic, and how you validated alerts. If asked about other SIEMs, translate your approach to Splunk or Sentinel concepts.
- **Built Python OpenPyXL reporting to convert GitLab SAST (plus Invicti and ACS) into management-ready Excel** (Dillard's internship bullets and project 'SAST Vulnerability Reporting + Excel Automation')
  - Walk through the data flow, fields you normalized (severity, repo, team), example workbook tabs, and how stakeholders used it. Do not claim reductions or coverage improvements without numbers.
- **Presented migration risks and access control recommendations to leadership** (Nonprofit healthcare capstone bullets and project)
  - Describe the specific decision you influenced (choosing SMS MFA with tokenized links), the risk tradeoffs you framed, and any HIPAA-aligned considerations. Avoid quoting costs unless you can back exact figures.
- **Performed onsite network traffic analysis with Wireshark to identify anomalies** (Accurate Interpretations internship bullet)
  - Be ready to describe your workflow: capture or read pcaps, use of filters, identifying authentication or connectivity issues, and how findings informed troubleshooting. Keep examples generic if details are confidential.
- **Python script to classify log entries into clearer categories** (Application answer on security logs)
  - Explain at a high level how you parsed logs, what categories you produced, and how that improved visibility. Clarify if this was for a lab environment, and avoid overclaiming scale.
- **Incident response playbook starting from a business impact analysis and tiered cloud backup schedule** (Projects 'Incident Response Playbook + Tiered Cloud Backup Schedule' and application answer)
  - Summarize how BIA informed restoration sequencing, how you balanced RTO with storage cost, and what an initial incident report would include at Tier 1.
- **Ansible configuration automation** (Project 'Ansible Configuration Automation (needs confirmation)')
  - Only speak to this if you have confirmed scope. If asked, say the exact playbook focus is being finalized and you will share specifics when ready.

## Weak spots / gaps + honest answers

- **No production SIEM experience or named platforms like Splunk, Sentinel, or QRadar**
  - Honest answer: My SIEM experience is a lab deployment with Graylog where I set up forwarding and alerts and practiced triage. The concepts translate cleanly, and I am comfortable learning your platform quickly with runbooks and shadowing.
- **No explicit 24x7 SOC or rotating shift experience**
  - Honest answer: I have not worked rotating shifts yet. I understand SOC coverage requirements and I am open to nights and weekends. I plan my schedule around shifts and handoffs, and I will lean on checklists and runbooks to stay consistent across time blocks.
- **No named ticketing or case management system experience (ServiceNow, Jira, etc.)**
  - Honest answer: I have used issue trackers in school and internships but not enterprise case tools. I can learn your ticketing workflows quickly and I already write concise, action-focused updates and link evidence for clean handoffs.
- **Still completing an MS while starting work**
  - Honest answer: I am finishing my BS now and completing the MS on an accelerated schedule. I can take evening or online classes and keep work hours aligned to shift needs. If helpful, I can share a class schedule to show it will not conflict.
- **Limited PowerShell experience**
  - Honest answer: My scripting focus has been Python. I am comfortable picking up PowerShell for common triage and collection tasks and can ramp with your scripts and examples.

## 30-second "why are you interested" answer

I want this Associate SOC Analyst role because it combines what I have been building toward: real-time monitoring, clear triage, and practical reporting. In my Graylog lab I set up alerts on authentication activity and practiced turning signals into escalations. At Dillard's I took scanner output and made it actionable for teams. I enjoy the mix of investigation and communication, and I am ready to learn your SIEM and ticketing stack and contribute on shift right away.

## 60-second "walk me through your background" answer

I am finishing a BS in Computer Information Systems with a cybersecurity minor and an MS in Cybersecurity at the University of Tulsa, and I hold CompTIA Network+ and Security+. In my Dillard's information security internship I helped build a GitLab SAST to Excel reporting pipeline in Python that gave leaders severity and ownership views they could act on. Before that, I was onsite doing network operations and Wireshark analysis to support secure network troubleshooting. On the project side, I built a centralized logging lab with Graylog, rsyslog, and NXLog to alert on Linux sudo/auth and Windows failed logon activity, and I created a small Python script to classify log entries for easier review. I also designed an incident response playbook that starts from a business impact analysis and a tiered cloud backup schedule. I am applying here because I want to do this work full time on a real SOC team, learn your SIEM and ticketing workflows, and be dependable on shift.

## Questions to ask the recruiter / hiring manager

- Which SIEM and EDR tools does the team use today, and what does a typical Tier 1 queue look like during a busy shift?
- How are shifts structured for the 24x7 coverage, and what is the expected rotation for nights, weekends, and holidays?
- What runbooks or playbooks are in place for the most common alerts, and where do you want an associate to apply judgment versus escalate?
- What ticketing or case management system do you use, and what does a high quality incident ticket look like in your environment?
- How do you measure success for Associate SOC Analysts in the first 90 days, and what metrics matter most day to day?
- What is the process for tuning noisy detections and contributing back to detection content as an associate?
- How much direct customer communication does Tier 1 handle, and what types of updates or reports are expected from analysts?
- What training or shadowing plan do new analysts follow to ramp on your tooling and procedures?

## Claim Stress Test: Likely Interview Questions

For each major claim in the resume, cover letter, outreach messages, and application answers, this section gives likely interview follow-ups, what a strong answer should cover, a confidence rating, and a recommendation. Use it as a truth-check before sending.

### Built a Graylog lab with rsyslog/NXLog and alerts for Linux sudo/auth and Windows failed logons.

- **Where:** resume summary; cover letter para 2; application answers (education prep and logs/SIEM); outreach_recruiter; linkedin_dm
- **Confidence:** high
- **Recommendation:** keep
- **Likely follow-up questions:**
    - How did you configure rsyslog on Linux and NXLog on Windows to forward to Graylog? Which inputs and ports did you use?
    - What exact alert conditions did you set for Linux sudo/auth and Windows failed logon events?
    - How did you validate end-to-end that the events were generated, forwarded, indexed, and alerted?
    - What steps did you take to reduce noise and false positives from these alerts?
    - Did you use pipelines or extractors in Graylog to normalize fields? If so, how?
- **A strong answer should include:**
    - Docker Compose stack for Graylog with Syslog UDP and GELF UDP inputs; rsyslog imjournal or imuxsock and NXLog outputs to GELF
    - Linux auth.log/sudo logs pattern and Windows Security log failed-logon criteria with clear thresholds
    - Test generation (failed password attempts, sudo misuse), confirmation in Graylog search and triggered notifications
    - Basic filtering/whitelisting strategy to cut service-account or lab-noise without losing signal
    - Reference to Proxmox VMs used as sources and any field normalization performed

### Chose NXLog GELF UDP over Syslog UDP to preserve structured fields; filtered by LogonType and whitelisted service accounts.

- **Where:** outreach_hiring_manager email body
- **Confidence:** medium
- **Recommendation:** study_before_sending
- **Likely follow-up questions:**
    - Show a snippet of your NXLog config and the Graylog input settings you used for GELF.
    - Which structured fields did GELF preserve for you and how did you use them in stream rules?
    - Which Windows LogonType values did you filter on and why?
    - How did you implement service-account whitelisting without masking real attacks?
    - What evidence did you collect that this change reduced false positives while keeping true positives?
- **A strong answer should include:**
    - NXLog Output GELF configuration and Graylog GELF UDP input; brief comparison to Syslog’s key-value loss
    - Examples of preserved fields (e.g., event_id, IpAddress, SubjectUserName) and how they powered filters/streams
    - LogonType rationale (interactive vs network vs remote interactive) and which types were excluded from alerting
    - Service-account handling via explicit lists or patterns and safeguards to avoid gaps
    - Before/after noise levels or qualitative results from tuning

### Performed onsite network traffic analysis with Wireshark to identify anomalies and support troubleshooting.

- **Where:** resume Accurate Interpretations bullet; resume summary; application answers (education prep)
- **Confidence:** high
- **Recommendation:** keep
- **Likely follow-up questions:**
    - Describe a concrete anomaly you found and how you verified the root cause with Wireshark.
    - Which display filters and views do you rely on for quick triage?
    - What TCP or DNS behaviors indicate a networking issue versus an application issue?
    - How did you handle and store packet captures securely on customer networks?
- **A strong answer should include:**
    - Specific issue (e.g., ARP broadcast storm, DNS timeouts, TCP retransmissions) and evidence from packet timelines
    - Key filters like tcp.analysis.flags, arp.duplicate-address-detected, dns and ssl/tls handshakes
    - Distinguishing latency/packet loss (SACK, retransmissions) from server-side resets or MTU problems
    - Secure handling: minimal capture scope, redaction/sanitization, controlled storage, and cleanup

### Helped build a GitLab SAST reporting workflow with Excel outputs, severity breakdowns, and team/repo views.

- **Where:** resume Dillard’s bullets; application answers (vuln assessment)
- **Confidence:** high
- **Recommendation:** keep
- **Likely follow-up questions:**
    - How did you ingest GitLab SAST results (API vs pipeline artifacts) and what format did you parse?
    - What was your deduplication logic across repeated findings and multiple runs?
    - How did you map repositories to teams and handle edge cases or missing ownership?
    - What Excel automation did you implement (tabs, charts, conditional formatting) and how was it distributed?
- **A strong answer should include:**
    - Parsing GitLab SAST JSON (API or artifacts), field extraction for severity/rule/file path
    - Dedup keys (e.g., rule id + file path + fingerprint) and status tracking across runs
    - Repo-to-team mapping via a maintained CSV or lookup table and exception handling
    - OpenPyXL for summary tabs, conditional formatting/color scales, pivot-like summaries; delivery cadence to stakeholders

### Correlated severity and logging dates to improve visibility into remediation priorities.

- **Where:** resume Dillard’s bullet 2
- **Confidence:** high
- **Recommendation:** keep
- **Likely follow-up questions:**
    - What did you mean by logging dates and how were they different from detection or first-seen dates?
    - How did you calculate age and prioritize items that were both old and severe?
    - How did you visualize or present this correlation to stakeholders?
- **A strong answer should include:**
    - Clear definition of timestamps used (e.g., first_seen, last_seen, reported_at) and source fields
    - Age buckets by severity and SLA-aligned prioritization rules
    - Report elements showing cross-tabs or charts highlighting old high-severity items

### Translated technical vulnerability findings into actionable reporting for decision-makers.

- **Where:** resume Dillard’s bullet 4; resume summary; application answers (vuln assessment)
- **Confidence:** high
- **Recommendation:** keep
- **Likely follow-up questions:**
    - Provide an example of how your report changed a team’s remediation plan.
    - How did you handle false positives or low-confidence findings in your summaries?
    - What fields or visuals did decision-makers find most helpful?
- **A strong answer should include:**
    - Concrete before/after example with clarified ownership and due dates
    - Approach to flagging likely false positives and providing guidance to validate or suppress
    - Top visuals (severity by team, age by severity) and short narrative takeaways

### Designed security-focused automation workflows with structured logs, alerting, and approval gates.

- **Where:** resume Self-directed / Independent bullets
- **Confidence:** high
- **Recommendation:** keep
- **Likely follow-up questions:**
    - What specific automated tasks did you monitor and what failure signals did you detect?
    - How did you implement human-in-the-loop approvals and audit trails?
    - What criteria classified an action as risky and how was it blocked or queued?
    - What language/stack and data formats did you use?
- **A strong answer should include:**
    - Examples of automation failures caught and signals (exit codes, timeouts, invariant checks)
    - Approval queue mechanism, auditable logs (JSONL), and reviewer sign-off details
    - Risk criteria (write/delete in sensitive paths, external calls with side effects) with allowlists
    - Python-based implementation tied to Mission Control/Command Broker concepts

### Presented migration risks and rollout recommendations to technical and non-technical stakeholders.

- **Where:** resume Nonprofit Healthcare bullet; cover letter para 4
- **Confidence:** high
- **Recommendation:** keep
- **Likely follow-up questions:**
    - What were the top three risks you highlighted and how did you communicate their impact?
    - How did your recommendations influence rollout sequencing or access patterns?
    - How did you address HIPAA-aligned considerations in your guidance?
- **A strong answer should include:**
    - Specific risks tied to migration (access control gaps, data exposure, change management) with plain-language impact
    - Resulting decisions (e.g., phased rollout, safer access pattern) and rationale
    - HIPAA-aligned design considerations that informed recommendations

### Can share a sanitized mockup of the vulnerability report and a brief walkthrough of my alert-triage checklist.

- **Where:** cover letter final paragraph
- **Confidence:** medium
- **Recommendation:** soften
- **Likely follow-up questions:**
    - What are the sections and fields in your triage checklist and why are they ordered that way?
    - Show how you move from an initial alert to a decision to close, escalate, or continue investigating.
    - How do you document exceptions and tune follow-up detection to reduce recurrence?
- **A strong answer should include:**
    - A concise, stepwise triage flow (validate time source, deduplicate, user/context check, correlate, decision and documentation)
    - Example alert walked through with evidence gathered and escalation criteria
    - Notes on tuning and adding context fields to reduce future noise

### Python-driven reporting and Excel/XLSX automation for security data.

- **Where:** resume summary; skills; Dillard’s bullets
- **Confidence:** high
- **Recommendation:** keep
- **Likely follow-up questions:**
    - Why OpenPyXL (or chosen library) and how did you handle performance on larger workbooks?
    - How did you implement severity-based color coding and summary tabs?
    - What error handling and validation did you build into the pipeline?
- **A strong answer should include:**
    - Library choice tradeoffs; techniques like write-only mode, styles reuse, memory control
    - Clear mapping from severity to styles and automated summary creation
    - Validation steps, schema checks, and graceful handling for missing fields

### Linux administration and Windows Server troubleshooting fundamentals.

- **Where:** resume summary; skills
- **Confidence:** high
- **Recommendation:** keep
- **Likely follow-up questions:**
    - Which logs and commands do you check first for Linux auth or service issues?
    - How do you troubleshoot Windows service failures and where do you find relevant events?
    - Describe a time you traced an authentication problem across OS and logs.
- **A strong answer should include:**
    - Linux basics (journalctl, /var/log/auth.log, systemctl) and SSH/sudo traces
    - Windows Event Viewer Security/System logs and linkage to NXLog forwarding
    - A brief cross-OS example tying events to a resolved issue

### Holds CompTIA Network+ and Security+ certifications.

- **Where:** resume certifications
- **Confidence:** high
- **Recommendation:** keep
- **Likely follow-up questions:**
    - When did you earn each and which domains do you apply most in your work?
    - How has Security+ influenced your approach to incident response or access control?
    - Where have you applied Network+ knowledge during Wireshark analysis?
- **A strong answer should include:**
    - Issue dates with emphasis on applied domains (networks, access control, IR basics)
    - Concrete examples linking Security+ concepts to lab and internship tasks
    - Wireshark use cases anchored in TCP/IP fundamentals

### CMMC v2 / NIST SP 800-171 documentation and control mapping coursework.

- **Where:** application answers (education prep)
- **Confidence:** high
- **Recommendation:** keep
- **Likely follow-up questions:**
    - Give an example of mapping a CMMC v2 practice to a specific NIST 800-171 requirement.
    - How would you explain CUI handling and logging controls to a small business?
    - What changed materially from CMMC v1 to v2 at a high level?
- **A strong answer should include:**
    - A concrete control mapping example with assessment objectives
    - Plain-language explanation of CUI handling and monitoring expectations
    - High-level differences (streamlining levels, self-assessment implications)

### Built a Python script to classify log entries into clearer categories to support investigation.

- **Where:** application answers (logs/SIEM)
- **Confidence:** medium
- **Recommendation:** study_before_sending
- **Likely follow-up questions:**
    - What sources and formats did you parse and how did you categorize events?
    - How did you evaluate the accuracy of your classification and reduce mislabels?
    - Show a small example of input and the resulting labeled output.
- **A strong answer should include:**
    - Parsing JSON logs and mapping to a taxonomy (auth_success, auth_failure, sudo, process start, etc.)
    - Regex/field-based rules with a test set and basic precision checks
    - CLI or script outline demonstrating before/after classification

### Used Graylog with OpenSearch and MongoDB backends via Docker Compose.

- **Where:** outreach_hiring_manager email; application answers (education prep)
- **Confidence:** medium
- **Recommendation:** study_before_sending
- **Likely follow-up questions:**
    - What did your docker-compose.yml look like for Graylog, OpenSearch, and MongoDB?
    - How did you handle index rotation and data retention in OpenSearch?
    - What resource and health checks did you configure for the stack?
- **A strong answer should include:**
    - Overview of services, volumes, and network in docker-compose with discovery.type=single-node for OpenSearch
    - Basic Graylog index set rotation and retention settings appropriate for a lab
    - Notes on memory/CPU limits and simple health checks or readiness probes

### Can monitor and analyze logs, network traffic, and alerts in real time across a variety of security technologies.

- **Where:** linkedin_dm body
- **Confidence:** medium
- **Recommendation:** soften
- **Likely follow-up questions:**
    - Beyond Graylog and Wireshark, which other security technologies have you monitored in real time?
    - Describe your real-time triage flow and how you decide to escalate.
    - What ticketing or case systems have you used to track incidents?
- **A strong answer should include:**
    - Scope-setting that this is lab-scale for Graylog and Wireshark with fundamentals applicable to other SIEMs
    - A crisp real-time triage flow leading to clear escalation criteria
    - Honest note on tooling exposure for ticketing and readiness to adopt team tools

## Claims to Remove or Soften Before Sending

### Chose NXLog GELF UDP; filtered by LogonType and whitelisted service accounts to cut noise.

- **Where:** outreach_hiring_manager email body
- **Why:** Includes specific field-level tuning details not explicitly documented in the profile and likely to prompt technical probing.
- **Suggested action:** Keep the claim but study NXLog config, GELF vs Syslog tradeoffs, Windows LogonType values, and be ready with examples.

### Can share a brief walkthrough of the alert-triage checklist I used.

- **Where:** cover letter final paragraph
- **Why:** A formal checklist is not shown elsewhere; interviewer may ask to see it or walk through steps in detail.
- **Suggested action:** Soften to 'walk through how I triaged alerts in my lab' or prepare a one-page checklist before sending.

### Built a Python script to classify log entries into clearer categories.

- **Where:** application answers (logs/SIEM)
- **Why:** Not listed as a standalone project; specifics on taxonomy, parsing, and accuracy may be tested.
- **Suggested action:** Move to interview study: prepare a short example, taxonomy, and code snippet to discuss if asked.

### Used Graylog with OpenSearch and MongoDB backends via Docker Compose.

- **Where:** outreach_hiring_manager email; application answers (education prep)
- **Why:** You may be asked for compose details, index rotation, and retention settings; these are easy to stumble on if not fresh.
- **Suggested action:** Study before sending: refresh docker-compose config, index sets, and retention basics.

### Monitor and analyze logs, network traffic, and alerts in real time across a variety of technologies.

- **Where:** linkedin_dm body
- **Why:** Reads broader than the evidence (lab-centric experience with Graylog and Wireshark).
- **Suggested action:** Soften to 'Built and used a Graylog lab for real-time alerting and used Wireshark for network analysis; ready to apply those fundamentals to your stack.'
