**Subject:** Information Security Analyst at Xpansiv - Graylog alerting lab

For the Information Security Analyst role, your posting calls for someone to "monitor, investigate, and respond to security alerts and incidents," which maps to my Centralized Logging Lab where I deployed Graylog with OpenSearch/MongoDB and built sudo/auth and Windows failed logon alerts using rsyslog and NXLog.

I chose GELF UDP for Windows so event fields stayed structured end to end, then normalized timestamps to UTC to avoid false correlations from Proxmox clock drift. To cut noise, I used Graylog event definitions to aggregate 5 failed logons per user in 3 minutes before firing, which reduced alert storms but still caught brute attempts.

I can share the Docker Compose file, NXLog and rsyslog configs, and the alert definition as a one-page lab writeup; worth 20 minutes Tuesday 10:30-10:50 am CT next week to walk through it?

Dillon Stinson
dds1244@utulsa.edu • 580-678-7939
