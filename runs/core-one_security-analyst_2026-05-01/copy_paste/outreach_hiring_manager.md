**Subject:** Security Analyst at Core One - SAST reporting + risk triage

For the Security Analyst role, your posting calls for someone to "Perform risk assessments, control assessments, and gap analyses," which maps to my Dillard's internship work building a GitLab SAST-to-Excel reporting pipeline with severity normalization and team mapping.

A key choice was to normalize GitLab severities to our internal scale and dedupe repeats before any rollups. I generated a stable fingerprint from rule_id, file path, and line, which stopped the same issue from inflating counts across pipelines, then used Python and OpenPyXL to produce per-team tabs plus a portfolio view stakeholders could act on.

I can share a one-page summary of the normalization decisions and a redacted Excel layout; worth 20 minutes Tue 10:00-10:20am CT next week?

Dillon Stinson

Dillon Stinson
dds1244@utulsa.edu • 580-678-7939
