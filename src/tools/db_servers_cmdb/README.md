# DB Servers CMDB

A tool for managing database server configuration management database (CMDB).

## Overview

This service provides a centralized repository for storing and retrieving metadata about database servers. It offers a RESTful API for interacting with the CMDB.

## Features

- Store and retrieve metadata for database servers
- Query all available metadata
- Clear metadata when needed
- Simple REST API interface

## Installation

### Requirements

- Python 3.12 or higher
- MongoDB

## Environment Variables

The following environment variables are required for the service to function properly:

- `MONGODB_URI`: Connection string for MongoDB (e.g., "mongodb://username:password@hostname:port/database?ssl=true")
- `SPN_PSWD`: Service Principal Password for Azure authentication
- `SPN_TENANT_ID`: Azure Tenant ID for authentication
- `SPN_CLIENT_ID`: Azure Client ID for authentication


These variables must be set in the environment before starting the service.

### Building with docker 
docker build -t tool-db-servers-cmdb .
docker run -p 8001:8001 tool-db-servers-cmdb



docker build --platform linux/amd64 -t  containerregistryovoradev.azurecr.io/tools/db-servers-cmdb .
docker push containerregistryovoradev.azurecr.io/tools/db-servers-cmdb


az login --identity
az acr login --name containerregistryovoradev

docker pull containerregistryovoradev.azurecr.io/tools/db-servers-cmdb

docker run -p 8001:8001 --restart=always --env-file .env  -d --name db-servers-cmdb containerregistryovoradev.azurecr.io/tools/db-servers-cmdb

curl http://20.117.121.86:8001/metadata/db-incident-sandbox

