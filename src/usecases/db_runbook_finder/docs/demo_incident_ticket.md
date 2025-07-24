# Demo Incident Ticket for DB Runbook Finder

## Ticket Details

**Project:** AGENT  
**Issue Type:** Incident  
**Priority:** High  
**Summary:** DB2 Hotel PMMASTER database connection failures after OS patching  

## Description

**Impact:** Critical production database PMMASTER on DB2 Hotel environment is experiencing connection failures following recent OS patching activities.

**Symptoms:**
- Applications unable to connect to PMMASTER database
- DB2 service appears to be running but connections are timing out
- HADR replication status showing issues between primary and standby nodes
- Database activation commands failing with port binding errors

**Environment Details:**
- **Client:** Helvetia  
- **System:** DB2 Hotel (Production)
- **Database:** PMMASTER
- **Servers Affected:** 
  - Primary: aw-sdb2001p
  - Standby: aw-sdb2002p
- **Port:** 55014

**Error Messages Observed:**
```
SQL30081N  A communication error has been detected. Communication protocol being used: "TCP/IP".
Communication API being used: "SOCKETS". Location where the error was detected: "".
Communication function detecting the error: "selectForConnectTimeout".
Protocol specific error code(s): "", "", "0". SQLSTATE=08001
```

**Timeline:**
- **14:30** - OS patching completed on both DB2 Hotel servers
- **14:45** - First connection failure reports from applications
- **15:00** - Database team notified
- **15:15** - Investigation started, HADR issues identified

**Troubleshooting Attempted:**
- Verified DB2 service status: `db2pd -alldbp` (service running)
- Checked network connectivity between nodes
- Attempted database activation: `db2 activate db PMMASTER` (failed)
- Verified port availability: `netstat -an | grep :55014` (port appears bound but not responding)

**Business Impact:**
- Production applications down for Helvetia Hotel management system
- Booking system unavailable
- Customer-facing services impacted
- Estimated revenue impact: €50,000/hour

**Expected Resolution:**
Need to restore database connectivity and ensure HADR synchronization is working properly. Likely requires following DB2 Hotel OS patching recovery procedures.

---

## Technical Context for Demo

**Why this incident is perfect for the demo:**

1. **Matches Existing Runbooks:** Will match strongly with:
   - "DB2 Hotel - OS patching (DBA activities)" (30 chunks, highest relevance expected)
   - "Pacemaker commands not working (DB2 Hotel)" (troubleshooting commands)
   - "Helvetia - DB2 Restore DB from the same environment" (HADR procedures)

2. **Realistic Scenario:** Based on actual DB2 Hotel architecture and common post-patching issues

3. **Rich Context:** Contains specific:
   - Database names (PMMASTER)
   - Server names (aw-sdb2001p, aw-sdb2002p)  
   - Port numbers (55014)
   - Error codes (SQL30081N)
   - DB2 commands mentioned in runbooks

4. **High Priority:** Justifies immediate runbook search and Slack notification

5. **Client Context:** Helvetia client matches the runbook tags for proper client identification

## Expected Demo Flow

1. **Input:** `AGENT-123` (or similar ticket ID)
2. **Fetch Incident:** Retrieves this incident data
3. **Search Runbooks:** Should find DB2 Hotel OS patching runbook with high relevance
4. **Jira Update:** Adds runbook recommendations to ticket
5. **Slack Notification:** Sends notification to #mc-dba-jira-notifications with results

## Jira Ticket Fields

```json
{
  "project": {"key": "AGENT"},
  "summary": "DB2 Hotel PMMASTER database connection failures after OS patching",
  "description": "[Full description from above]",
  "issuetype": {"name": "Incident"},
  "priority": {"name": "High"},
  "labels": ["database", "db2", "helvetia", "production", "hotel", "patching"],
  "assignee": {"name": "dba-team"}
}
```