# QA report

**Overall polish: `needs_work`**

## MEDIUM (2)

### [evidence_gap] application_answers — "How many years of professional experience do you have?"
> Internship-level plus project-heavy. I am finishing a BS in Computer Information Systems and an MS in Cybersecurity at the University of Tulsa.

**Fix:** Give a clear, numeric summary of experience (e.g., "~1 year of internship experience + ongoing independent projects") and briefly separate internship vs. personal projects so reviewers can quickly assess level.

### [redundancy] tailored_resume, cover_letter, outreach_recruiter, linkedin_dm
> SAST reporting workflow described repeatedly across resume, cover letter, and multiple outreach messages (similar wording about converting GitLab findings into Excel summaries).

**Fix:** Keep one canonical, concise description in the resume and vary the phrasing in outreach/cover letter to highlight different outcomes or audience impact (e.g., one message emphasizes technical implementation, another the stakeholder impact).

## LOW (2)

### [generic_phrase] tailored_resume — Summary
> Brings Python-based reporting automation, monitoring guardrails, and clear communication for technical and non-technical audiences.

**Fix:** Replace the generic 'clear communication...' phrasing with a short concrete example or metric from your materials (e.g., 'produced stakeholder-ready SAST summaries that reduced triage time by X' or 'presented migration risks to leadership, influencing rollout decisions').

### [tone] outreach_recruiter and linkedin_dm
> I can share a one-page writeup... are you the right contact for this role, or could you point me to the right person? / Is your team still hiring for this?

**Fix:** Personalize these messages to the recipient or team (reference PurpleBox-specific work, a team name, or a recent announcement) and shorten the ask to a single clear call-to-action (e.g., 'Would you be open to a 15-min call?').
