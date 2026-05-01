**Subject:** Cybersecurity Analyst at PurpleBox - Graylog logging lab

Your Cybersecurity Analyst posting calls for someone to "Run daily processes and tools for managing cybersecurity", which maps directly to my Graylog + OpenSearch centralized logging lab with rsyslog and NXLog forwarding and auth-event alerts.

I segmented inputs by using GELF UDP for Windows via NXLog to preserve structured fields, and Syslog UDP for Linux via rsyslog, then routed streams and built pipeline rules to tag sudo and 4625 events. A failure I debugged was missing failed-logon alerts; the fix was switching NXLog to im_msvistalog with a Security channel QueryXML and normalizing timestamps to UTC in Graylog to avoid off-by-day filters. That change stabilized alerting and kept dashboards focused on real auth anomalies.

I can share a one-page lab writeup plus the docker-compose.yml and NXLog/rsyslog configs; worth 20 minutes next Wed 10:00-10:20 am CT to walk it end to end?

Dillon Stinson
dds1244@utulsa.edu • 580-678-7939
