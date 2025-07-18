


docker build -f src/tools/db_servers_cmdb/Dockerfile --platform linux/amd64 -t containerregistryovoradev.azurecr.io/tools/db_servers_cmdb .
docker push containerregistryovoradev.azurecr.io/tools/db_servers_cmdb
