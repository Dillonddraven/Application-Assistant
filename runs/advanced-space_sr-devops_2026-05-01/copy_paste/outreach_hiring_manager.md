**Subject:** Sr. DevOps at Advanced Space - Graylog logging lab

For the Sr. DevOps role, your posting calls for someone to "Design and operate scalable logging, alerting, and incident response workflows to quickly detect and remediate system issues," which maps directly to my Graylog central logging lab with OpenSearch and MongoDB using rsyslog and NXLog to alert on Linux sudo and Windows failed logons.

I started with Syslog for Windows events but switched to GELF UDP to preserve structured fields and avoid brittle extractors. In Graylog I normalized usernames to lowercase and used a pipeline rule to discard repeat bursts from service accounts, which cut noise and stabilized threshold alerts. That choice made searches and dashboards reliable across hosts and reduced false pages.

I can share the Docker Compose file plus the rsyslog, NXLog, and Graylog pipeline snippets that drive the alerts; worth twenty minutes Thursday at two PM MT to walk through it?

Dillon Stinson
dds1244@utulsa.edu • 580-678-7939
