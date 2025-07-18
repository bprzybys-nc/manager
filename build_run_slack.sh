



docker build -f src/tools/communication/Dockerfile -t containerregistryovoradev.azurecr.io/tools/communication .


docker stop communication
docker rm communication

docker run --name communication  --env-file .env -d -p 8002:8002 containerregistryovoradev.azurecr.io/tools/communication


