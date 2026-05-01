**Subject:** Information Security Analyst (GRC) at LVT - control testing + evidence

Your posting calls for someone to "Execute control testing and evidence collection," which maps to my Dillard's SAST reporting work building the pipeline that turned GitLab output into structured evidence for control owners.

A key decision was to normalize severities to a consistent scale while preserving the original scanner label, so each row stayed traceable to source during review. I also keyed findings by repo, path, and rule to avoid double counting across runs, then correlated logging dates to separate reopened issues from net-new. That made status changes auditable and reduced churn in remediation discussions.

I can share a redacted severity-mapping sheet and sample evidence layout; is Wed 2:00-2:20 pm CT next week open to walk through it?

Dillon Stinson

Dillon Stinson
dds1244@utulsa.edu • 580-678-7939
