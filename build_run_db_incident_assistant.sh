



docker build -f src/usecases/db_incident_assistant/Dockerfile -t containerregistryovoradev.azurecr.io/usecases/db_incident_assistant .

docker stop my-db-assistant
docker rm my-db-assistant

docker run  --name my-db-assistant  --env-file .env -d -p 8000:8000 containerregistryovoradev.azurecr.io/usecases/db_incident_assistant



