#docker build -f src/usecases/db_incident_assistant/Dockerfile -t containerregistryovoradev.azurecr.io/usecases/db_incident_assistant .




docker build -f src/usecases/db_incident_assistant/Dockerfile --platform linux/amd64 -t containerregistryovoradev.azurecr.io/usecases/db_incident_assistant .
docker push containerregistryovoradev.azurecr.io/usecases/db_incident_assistant