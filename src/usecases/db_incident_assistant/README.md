

# DB Incident Assistant

A tool for assisting with database incident management and troubleshooting.

## Overview

This service provides automated assistance for diagnosing and resolving database-related incidents. It offers a RESTful API for incident management and resolution workflows.

## Features

- Automated incident detection and classification
- Diagnostic workflows for common database issues
- Integration with credential stores (Azure Key Vault, AWS Secret Manager)
- Incident resolution recommendations
- Historical incident tracking and analysis

## Installation

### Requirements

- Python 3.12 or higher
- MongoDB for incident storage
- Access to credential stores (optional)

### Environment Variables

- `MONGODB_URI`: Connection string for MongoDB
- `SPN_PSWD`: Service Principal Password for Azure Key Vault (if used)


## Architecture

The DB Incident Assistant integrates with the DB Servers CMDB to retrieve database connection information and credentials. It uses these details to connect to problematic databases and perform diagnostics.

## Docker
docker build -t db_incident_assistant .

docker build --platform linux/amd64 -t db_incident_assistant .
docker tag db_incident_assistant containerregistryovoradev.azurecr.io/usecases/db_incident_assistant
docker push containerregistryovoradev.azurecr.io/usecases/db_incident_assistant


az login --identity
az acr login --name containerregistryovoradev

docker pull containerregistryovoradev.azurecr.io/usecases/db_incident_assistant

docker run -p 8000:8000 -d --name my-db-assistant containerregistryovoradev.azurecr.io/usecases/db_incident_assistant

1)Postgres High CPU incident:
curl -X POST http://20.117.121.86:8000/public/incidents \
  -H 'Content-Type: application/json' \
  -d '{
   "id":"8082436309665268856",
   "source":"datadog",
   "last_updated":"1746013550000",
   "event_type":"query_alert_monitor",
   "title":"[Triggered on {host:db-incident-demo}] Postgres is near the max CPU usage limit",
   "date":"1746013550000",
   "org":{
      "id":"1325540",
      "name":"IBM Ovora"
   },
   "body":"%%%\n## CPU usage reached a ceiling for postgres\nTriggered for:\n- Host: db-incident-demo\n- Value: 93.002 (Threshold: 90.0)\n\n@webhook-ovora-incident-assistant\n\n\n",
   "hostname":"db-incident-demo"
}'
2)Linux High CPU incident:
curl -X POST http://20.117.121.86:8000/public/incidents \
  -H 'Content-Type: application/json' \
  -d '{
   "id":"8082436309665268856",
   "source":"datadog",
   "last_updated":"1746013550000",
   "event_type":"query_alert_monitor",
   "title":"[Triggered on {host:db-incident-demo}] DB Host is near the max CPU usage limit",
   "date":"1746013550000",
   "org":{
      "id":"1325540",
      "name":"IBM Ovora"
   },
   "body":"%%%\n## CPU usage reached a ceiling\nTriggered for:\n- Host: db-incident-demo\n- Value: 93.002 (Threshold: 90.0)\n\n@webhook-ovora-incident-assistant\n\n\n",
   "hostname":"db-incident-demo"
}'
3) Lock Contention Critical incident:
curl -X POST http://20.117.121.86:8000/public/incidents \
  -H 'Content-Type: application/json' \
  -d '{
   "id":"8082436309665268856",
   "source":"datadog",
   "last_updated":"1746013550000",
   "event_type":"query_alert_monitor",
   "title":"[Triggered on {host:db-incident-demo}] PostgreSQL Lock Contention Critical",
   "date":"1746013550000",
   "org":{
      "id":"1325540",
      "name":"IBM Ovora"
   },
   "body":"%%%\n## Lock Contention Alert\nDetected 11.0 blocked transactions on PostgreSQL server.\n\nService Impact\n* Transaction queuing\n* Increased response times\n* Potential application timeouts\n\n@webhook-ovora-incident-assistant",
   "hostname":"db-incident-demo"
}'
4) Slow Query Detection incident:
curl -X POST http://20.117.121.86:8000/public/incidents \
  -H 'Content-Type: application/json' \
  -d '{
   "id":"8082436309665268856",
   "source":"datadog",
   "last_updated":"1746013550000",
   "event_type":"query_alert_monitor",
   "title":"[Triggered on {host:db-incident-demo}] PostgreSQL Slow Query Detection",
   "date":"1746013550000",
   "org":{
      "id":"1325540",
      "name":"IBM Ovora"
   },
   "body":"%%%\n## PostgreSQL Slow Query Alert\nThe average query time on has increased by 84551.093ms in the last 5 minutes.\n\nImpact\n * Increased application response times\n *Possible timeout errors\n * Database connection saturation\n\n@webhook-ovora-incident-assistant",
   "hostname":"db-incident-demo"
}'

5) Connection pool exhausted incident:
curl -X POST http://20.117.121.86:8000/public/incidents \
  -H 'Content-Type: application/json' \
  -d '{
   "id":"8082436309665268856",
   "source":"datadog",
   "last_updated":"1746013550000",
   "event_type":"query_alert_monitor",
   "title":"[Triggered on {host:db-incident-demo}] PostgreSQL Connection Pool Near Saturation",
   "date":"1746013550000",
   "org":{
      "id":"1325540",
      "name":"IBM Ovora"
   },
   "body":"%%%\n## PostgreSQL Connection Pool Alert\nConnection pool on db-incident-demo is at 0.924 capacity (threshold: 0.8).\n\nImpact\n* New connections will be rejected once the pool is exhausted, causing application errors.\n\n@webhook-ovora-incident-assistant",
   "hostname":"db-incident-demo"
}'
6) Unexpected Database shutdown incident:
curl -X POST http://20.117.121.86:8000/public/incidents \
  -H 'Content-Type: application/json' \
  -d '{
   "id":"8082436309665268856",
   "source":"datadog",
   "last_updated":"1746013550000",
   "event_type":"query_alert_monitor",
   "title":"[Triggered on {host:db-incident-demo}] Unexpected showdown PostgreSQL DB",
   "date":"1746013550000",
   "org":{
      "id":"1325540",
      "name":"IBM Ovora"
   },
   "body":"%%%\n## Detected unexpected shutdown of the PostgreSQL DB.\n\nMetric: postgresql.heartbeat\n\nTriggered for:\n\nHost: db-incident-demo\nValue: 0.0 (Threshold: 0.5)\nDB hostname: db-incident-demo\nPostgreSQL version: 14.17_ubuntu_14.17-0ubuntu0.22.04.1\n\n@webhook-ovora-incident-assistant",
   "hostname":"db-incident-demo"
}'


curl -X POST http://20.117.121.86:8002/questions/ \
  -H "Content-Type: application/json" \
-d '{"thread_id": "1747153436.310999", "question": "Is this issue critical?", "incident_id": "d13ad41d-21fc-44bc-9361-6b8ec4a30e17"}'
