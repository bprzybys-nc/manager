



docker build -f src/tools/cmd_exec/Dockerfile -t containerregistryovoradev.azurecr.io/tools/cmd_exec .


docker stop cmd_exec
docker rm cmd_exec

docker run --name cmd_exec  --env-file .env -d -p 8003:8003 containerregistryovoradev.azurecr.io/tools/cmd_exec


