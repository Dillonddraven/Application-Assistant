# QA report

**Overall polish: `needs_work`**

## MEDIUM (3)

### [redundancy] tailored_resume Summary / Experience, cover_letter, outreach_recruiter, outreach_hiring_manager, linkedin_dm
> alerts on Linux sudo/auth and Windows failed logons

**Fix:** Reduce verbatim repetition across documents. Keep one short, clear example in the resume (e.g., in Experience) and in the cover letter highlight a different measurable outcome (e.g., reduced false positives by X% or how the alerting changed triage). For outreach messages keep a single-line summary and point to the one-page lab writeup rather than reproducing the same sentence.

### [overclaiming] linkedin_dm
> Built a Graylog stack with rsyslog and NXLog forwarding and alerting for Linux sudo/auth and Windows failed logons.

**Fix:** Clarify that this was a self-directed / lab deployment (if applicable) and state scale/constraints (e.g., 'lab deployment processing ~X events/hour' or 'proof-of-concept lab'). Employers can assume production experience if unspecified; be explicit about environment and scope.

### [evidence_gap] tailored_resume Education
> Bachelor of Science in Computer Information Systems, The University of Tulsa (in progress, expected 2026-05)
Master of Science in Cybersecurity, The University of Tulsa (in progress, expected 2026-12)

**Fix:** The two degree end-dates are close and may raise questions about program structure. Add a clarifying note (e.g., 'combined BS/MS accelerated program' or 'enrolling in an accelerated graduate program; MS begins after BS completion') so a reviewer understands the timeline.

## LOW (1)

### [generic_phrase] cover_letter / tailored_resume Summary and Application Answers
> hands-on log and traffic analysis

**Fix:** Replace generic 'hands-on' phrasing with a concrete descriptor or metric (e.g., 'configured Graylog alerts for sudo/auth and reduced alert noise by X%' or 'analyzed pcap captures using Wireshark to identify suspicious lateral movement patterns'). Concrete details are stronger than generic adjectives.
