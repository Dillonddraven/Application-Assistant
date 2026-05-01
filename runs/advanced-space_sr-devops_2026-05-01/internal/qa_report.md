# QA report

**Overall polish: `needs_work`**

## HIGH (1)

### [overclaiming] linkedin_dm; outreach_hiring_manager; tailored_resume Summary / cover_letter opening
> I know the spec is Sr. DevOps (8-12 yrs), but I bring practical security automation and monitoring you can plug in fast.

**Fix:** Don't frame yourself as a direct match to an 8–12 year Sr. role. State your actual level (internship + projects) and emphasize concrete, transferable skills and rapid learning. Example: 'Early-career DevOps candidate with hands-on Graylog and SAST automation experience, ready to contribute to logging and security automation efforts and scale under senior mentorship.'

## MEDIUM (3)

### [evidence_gap] cover_letter opening; tailored_resume Summary
> Deliver reliable, scalable, and secure DevOps infrastructure and automation... (implied match in letters) / centralized logging and alerting in lab environments

**Fix:** Clarify scope: explicitly state these were lab / intern / project implementations, not multi-year production operation of enterprise or ML-scale infrastructure. If you have any cloud, uptime, scaling, or team-production metrics, include them (hosts, event rate, retention, SLAs). Otherwise remove phrasing that implies large-scale production ownership.

### [internal_metadata] tailored_resume Experience
> R1649, Backend Development Intern

**Fix:** Replace 'R1649' with the actual company name or a meaningful placeholder (e.g., 'Stealth startup (backend intern)') — employers will be confused by an ID-like label and may suspect a scraping artifact.

### [tone] linkedin_dm; outreach_recruiter; cover_letter closing
> I know the spec is Sr. DevOps (8-12 yrs), but I bring practical security automation and monitoring you can plug in fast. / I can share a one-page lab summary; are you the right contact...?

**Fix:** Avoid pleading or overly sales-y phrasing. Be concise and confident: describe a measurable contribution or a concrete artifact you can share, then ask for the appropriate next step ('If this aligns, I can share a one-page lab summary and Docker Compose snippets; would you prefer a quick call or I email the summary?').

## LOW (1)

### [redundancy] tailored_resume Summary; cover_letter; application_answers
> Repeated mentions of 'GitLab SAST reporting', 'centralized logging and alerting', and 'approval-gated workflows' across resume, cover letter, and answers with little added detail.

**Fix:** Use each document to add unique value: resume = concise bullets/impact, cover letter = one short story showing impact, application answers = specific technical details or metrics. Avoid verbatim repeats; instead surface a metric or short example in one place.
