



docker build -f src/tools/db_servers_cmdb/Dockerfile -t containerregistryovoradev.azurecr.io/tools/db_servers_cmdb_macos .


docker stop db_servers_cmdb
docker rm db_servers_cmdb

docker run  --name db_servers_cmdb  --env-file .env -d -p 8001:8001 containerregistryovoradev.azurecr.io/tools/db_servers_cmdb_macos


