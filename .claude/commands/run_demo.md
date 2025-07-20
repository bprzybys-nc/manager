# Run Manager Demo

Execute a comprehensive demonstration of manager component capabilities, including GraphMCP framework workflows and tool integrations.

## Demo Preparation

1. **Infrastructure Setup**
   ```bash
   cd manager
   # Start required services
   docker-compose up -d
   
   # Verify services are running
   docker-compose ps
   ```

2. **Environment Verification**
   ```bash
   cd manager
   # Install dependencies
   uv sync
   
   # Check environment variables
   python -c "from src.config import config; print('Environment OK')"
   ```

## Demo Scenarios

### 1. API Service Demo
```bash
cd manager
# Start API service
uv run uvicorn main:app --port 9123 --reload &

# Test health endpoint
curl http://localhost:9123/health

# Test basic API functionality
curl http://localhost:9123/api/v1/incidents
```

### 2. GraphMCP Framework Demo
```bash
cd manager/src/frameworks/graphmcp
# Setup GraphMCP environment
make setup

# Run demo workflow
make demo

# Show workflow capabilities
python -c "
from workflows.builder import WorkflowBuilder
print('GraphMCP Framework Ready')
"
```

### 3. Tool Services Demo
```bash
# Confluence Tool Demo (if configured)
cd manager/src/tools/confluence
uv sync
uv run uvicorn app.api:app --port 8000 &
curl http://localhost:8000/health/detailed

# Jira Tool Demo (if configured)
cd manager/src/tools/jira
uv sync
uv run uvicorn app.api:app --port 8001 &
curl http://localhost:8001/health
```

### 4. AI Integration Demo
```bash
cd manager
# Test AI components (if API keys configured)
python -c "
from src.llm.llm import get_llm_client
try:
    client = get_llm_client()
    print('AI Integration Ready')
except Exception as e:
    print(f'AI Integration: {e}')
"
```

### 5. Task Processing Demo
```bash
cd manager
# Start Celery worker
uv run celery -A worker_main worker --loglevel=info &

# Start Celery beat scheduler
uv run celery -A worker_main beat --loglevel=info &

# Check task queue status
uv run celery -A worker_main inspect active
```

### 6. Database Operations Demo
```bash
cd manager
# Test database connectivity
python -c "
from src.database.client import DatabaseClient
with DatabaseClient() as db:
    result = db.db.list_collection_names()
    print(f'Database collections: {result}')
"
```

### 7. Slack Integration Demo (if configured)
```bash
cd manager
# Start Slack worker
python slack_main.py &

# Test Slack connectivity (if tokens configured)
python -c "
try:
    from src.integrations.hil.slack.slack import SlackClient
    print('Slack Integration Ready')
except Exception as e:
    print(f'Slack Integration: {e}')
"
```

## Interactive Demo

### Test Incident Processing
```bash
cd manager
# Create test incident
curl -X POST http://localhost:9123/api/v1/incidents \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Demo Incident",
    "description": "Testing incident processing",
    "severity": "medium"
  }'

# List incidents
curl http://localhost:9123/api/v1/incidents
```

### Test GraphMCP Workflow
```bash
cd manager/src/frameworks/graphmcp
# Run pattern discovery demo
python -c "
from concrete.pattern_discovery import PatternDiscoveryWorkflow
workflow = PatternDiscoveryWorkflow('demo_config.json')
print('Pattern Discovery Workflow Ready')
"
```

## Performance Demo

### Load Testing
```bash
cd manager
# Simple load test
for i in {1..10}; do
  curl -s http://localhost:9123/health &
done
wait
echo "Load test completed"
```

### Memory Usage
```bash
cd manager
# Check memory usage
python -c "
import psutil
import os
process = psutil.Process(os.getpid())
print(f'Memory usage: {process.memory_info().rss / 1024 / 1024:.2f} MB')
"
```

## Demo Validation

### Service Health Checks
```bash
# Check all service endpoints
echo "API Service:"
curl -f http://localhost:9123/health && echo " ✓" || echo " ✗"

echo "Confluence Tool:"
curl -f http://localhost:8000/health && echo " ✓" || echo " ✗"

echo "Jira Tool:"
curl -f http://localhost:8001/health && echo " ✓" || echo " ✗"
```

### Component Integration
```bash
cd manager
# Test component integration
python -c "
from src.api import app
from src.database.client import DatabaseClient
from src.llm.llm import get_llm_client
print('✓ Manager components integrated')
"
```

## Demo Cleanup

```bash
# Stop background processes
pkill -f uvicorn
pkill -f celery
pkill -f python

# Stop infrastructure
cd manager
docker-compose down
```

## Demo Report

After running the demo, provide:
- ✅ Services successfully started
- ✅ API endpoints responding
- ✅ Database connectivity verified
- ✅ GraphMCP framework operational
- ✅ Tool services running
- ✅ Integration tests passed

## Troubleshooting

### Common Issues
1. **Port conflicts**: Check if ports 9123, 8000, 8001 are available
2. **Database connection**: Verify MongoDB is running
3. **Redis connection**: Verify Redis is running for Celery
4. **Environment variables**: Check all required variables are set

### Debug Commands
```bash
# Check running processes
ps aux | grep -E "(uvicorn|celery|python)"

# Check port usage
netstat -tlnp | grep -E "(9123|8000|8001)"

# Check logs
docker-compose logs -f
```

The demo showcases the full capabilities of the manager component within the Ovora ecosystem.