

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
docker build -t communication .

docker build --platform linux/amd64 -t communication .
docker tag communication containerregistryovoradev.azurecr.io/tool/communication
docker push containerregistryovoradev.azurecr.io/tool/communication

docker build -t communication .


az login --identity
az acr login --name containerregistryovoradev

docker pull containerregistryovoradev.azurecr.io/tool/communication

docker run -p 8002:8002 -d --name communication containerregistryovoradev.azurecr.io/tool/communication




    # Send a new message:
    curl -X POST http://20.117.121.86:8002/messages/ \
      -H "Content-Type: application/json" \
      -d '{"message": "```my test 2 "}'

    curl -X POST http://20.117.121.86:8002/messages/ \
      -H "Content-Type: application/json" \
      -d '{"message": "*Test message*"}'
    
    # Reply to an existing thread:
    curl -X POST http://20.117.121.86:8002/messages/ \
      -H "Content-Type: application/json" \
      -d '{"thread_id": "1746386597.490769", "message": "Reply to thread"}'

     # Reply to an existing thread:
    curl -X POST http://localhost:8002/questions/ \
      -H "Content-Type: application/json" \
      -d '{"thread_id": "1746386597.490769", "message": "Reply to thread","question":"Does it work?","question_id":"28374"}'


Slack formatting:
bold: *your text*
italics: _your text_
code: `your text`
code block: ```your text


 curl -X POST http://20.117.121.86:8002/questions/ \
   -H "Content-Type: application/json" \
   -d '{
     "incident_id": "d13ad41d-21fc-44bc-9361-6b8ec4a30e17",
     "instance_id": "2c1f79d2-c1e5-4ff8-b438-b2f5311c5e4f",
     "command": "ls -la",
     "command_type": "shell",
     "thread_id": "1747153436.310999",
     "question": "Do you want to execute this command?"
 }'