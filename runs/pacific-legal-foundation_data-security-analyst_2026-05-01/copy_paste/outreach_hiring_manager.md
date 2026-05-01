**Subject:** Data Security Analyst at Pacific Legal Foundation - Graylog alerts

For the Data Security Analyst role, your posting calls for someone to 'Support monitoring for anomalies and policy violations', which maps to my Centralized Logging Lab deploying Graylog with rsyslog/NXLog and alerting on sudo/auth and Windows failed-logon events.

I sent Windows logs via NXLog in GELF format to keep fields like event_id, logon_type, and target_user intact, while Linux used Syslog for lower overhead. Early on, timestamp mismatches between hosts made sequences look out of order; setting everything to UTC in Graylog and the forwarders fixed correlation. I also filtered known-noisy services so alerts focused on repeated failed logons and sudo misuse, not background chatter.

I can share a one-page lab writeup with the docker-compose, inputs, and alert logic; is 20 minutes on Wednesday next week, 11:00 to 11:20 ET, workable?

Dillon Stinson
dds1244@utulsa.edu • 580-678-7939
