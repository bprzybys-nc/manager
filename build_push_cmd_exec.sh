


docker build -f src/tools/cmd_exec/Dockerfile --platform linux/amd64 -t containerregistryovoradev.azurecr.io/tools/cmd_exec .
docker push containerregistryovoradev.azurecr.io/tools/cmd_exec
