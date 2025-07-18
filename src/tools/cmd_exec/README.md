


uv run uvicorn api:app --port 9123


curl -X POST http://20.117.121.86:8003/executions \
  -H "Content-Type: application/json" \
  -d '{
    "incident_id": "27e36587-84ad-4bdd-a84b-91f76919aff8",
    "instance_id": "66f7c2d7-536e-439f-9f9c-394357c91248",
    "commands": [
      {
        "command": "top -b|head -n 10"
      }
    ],
    "response_endpoint":"test"
  }'
