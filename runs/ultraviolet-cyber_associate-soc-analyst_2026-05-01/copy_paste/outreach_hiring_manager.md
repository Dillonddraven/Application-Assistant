**Subject:** Associate SOC Analyst at UltraViolet Cyber - Graylog logging lab

Your posting calls for someone to "monitor and analyze security logs and network traffic"; that maps directly to my Centralized Logging Lab using Graylog, OpenSearch, and MongoDB with rsyslog/NXLog forwarding and alerts on Linux sudo/auth and Windows failed-logon events.

One choice that mattered was sending Windows events via NXLog in GELF UDP, not Syslog UDP, so Graylog kept structured fields like event_id and IpAddress for precise stream rules. Early on, Windows failed-logon alerts were noisy, so I filtered by LogonType and whitelisted known service accounts, which cut false positives while keeping real brute attempts visible.

I can share a one-page lab writeup with the Graylog input configs and alert conditions; worth 20 minutes next Wed 10:00 to 10:20 CT to walk through it?

Dillon Stinson
dds1244@utulsa.edu • 580-678-7939
