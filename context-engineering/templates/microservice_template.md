# Microservice Tool Template

## Basic Information

**Service Name**: [Descriptive name for the microservice]
**Component**: Manager Tools
**Purpose**: [Brief description of what this service provides]
**Port**: [Default port number, e.g., 8000]
**Category**: [Integration/Processing/Communication/etc.]

## Business Context

### Problem Statement
[Describe the problem this microservice solves]

### Integration Requirements
- **External Service**: [Name of external service being integrated]
- **Authentication**: [How authentication is handled]
- **Rate Limits**: [Any rate limiting considerations]
- **Dependencies**: [Other services or components this depends on]

### Success Criteria
- [ ] [Specific, measurable outcome 1]
- [ ] [Specific, measurable outcome 2]
- [ ] [Response time requirements]
- [ ] [Availability requirements]

## API Design

### Base Configuration
```python
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
import logging

app = FastAPI(
    title="[Service Name]",
    description="[Service description]",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

logger = logging.getLogger(__name__)
```

### Data Models
```python
class ServiceRequest(BaseModel):
    """Request model for primary service operation."""
    field1: str = Field(..., description="Description of field1")
    field2: Optional[int] = Field(None, description="Optional field2")
    
    class Config:
        schema_extra = {
            "example": {
                "field1": "example_value",
                "field2": 123
            }
        }

class ServiceResponse(BaseModel):
    """Response model for service operations."""
    success: bool = Field(..., description="Operation success status")
    data: Dict[str, Any] = Field(..., description="Response data")
    message: Optional[str] = Field(None, description="Status message")

class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: str = Field(..., description="Error type")
    detail: str = Field(..., description="Error details")
    code: int = Field(..., description="Error code")
```

## API Endpoints

### Health Check Endpoints
```python
@app.get("/health", response_model=Dict[str, str])
async def health_check():
    """Basic health check endpoint."""
    return {"status": "healthy", "service": "[service_name]"}

@app.get("/health/ready", response_model=Dict[str, Any])
async def readiness_check():
    """Readiness check with external service connectivity."""
    try:
        # Check external service connectivity
        await check_external_service()
        return {
            "status": "ready",
            "external_service": "connected",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=503, detail="Service not ready")
```

### Core API Endpoints
```python
@app.post("/[primary_operation]", response_model=ServiceResponse)
async def primary_operation(
    request: ServiceRequest,
    client: [ExternalClient] = Depends(get_client)
):
    """
    Primary service operation.
    
    Args:
        request: Service request data
        client: External service client
        
    Returns:
        ServiceResponse with operation results
        
    Raises:
        HTTPException: When operation fails
    """
    try:
        logger.info(f"Processing request: {request.field1}")
        
        # Validate request
        await validate_request(request)
        
        # Process with external service
        result = await client.process_operation(request)
        
        logger.info(f"Operation completed successfully")
        return ServiceResponse(
            success=True,
            data=result,
            message="Operation completed successfully"
        )
        
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    except ExternalServiceError as e:
        logger.error(f"External service error: {e}")
        raise HTTPException(status_code=503, detail="External service unavailable")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/[resource]/{resource_id}", response_model=ServiceResponse)
async def get_resource(
    resource_id: str,
    client: [ExternalClient] = Depends(get_client)
):
    """Get resource by ID."""
    try:
        resource = await client.get_resource(resource_id)
        if not resource:
            raise HTTPException(status_code=404, detail="Resource not found")
            
        return ServiceResponse(
            success=True,
            data=resource,
            message="Resource retrieved successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving resource: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
```

## External Service Integration

### Client Implementation
```python
import httpx
from typing import Optional, Dict, Any
import asyncio
from contextlib import asynccontextmanager

class [ExternalService]Client:
    """Client for [External Service] integration."""
    
    def __init__(
        self,
        base_url: str,
        username: str,
        api_token: str,
        timeout: int = 30
    ):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.api_token = api_token
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
    
    @asynccontextmanager
    async def _get_client(self):
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                auth=(self.username, self.api_token)
            )
        try:
            yield self._client
        finally:
            pass  # Keep client alive for reuse
    
    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def process_operation(self, request: ServiceRequest) -> Dict[str, Any]:
        """Process operation with external service."""
        async with self._get_client() as client:
            response = await client.post(
                f"{self.base_url}/api/operation",
                json=request.dict()
            )
            response.raise_for_status()
            return response.json()
    
    async def get_resource(self, resource_id: str) -> Optional[Dict[str, Any]]:
        """Get resource from external service."""
        async with self._get_client() as client:
            response = await client.get(
                f"{self.base_url}/api/resource/{resource_id}"
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
```

### Dependency Injection
```python
from src.config import get_config

def get_client() -> [ExternalService]Client:
    """Get external service client."""
    config = get_config()
    return [ExternalService]Client(
        base_url=config.[EXTERNAL_SERVICE]_URL,
        username=config.[EXTERNAL_SERVICE]_USERNAME,
        api_token=config.[EXTERNAL_SERVICE]_API_TOKEN,
        timeout=config.[EXTERNAL_SERVICE]_TIMEOUT
    )
```

## Configuration

### Environment Variables
```python
# Required environment variables
[EXTERNAL_SERVICE]_URL=https://external-service.com
[EXTERNAL_SERVICE]_USERNAME=service_username
[EXTERNAL_SERVICE]_API_TOKEN=service_api_token

# Optional environment variables
[EXTERNAL_SERVICE]_TIMEOUT=30  # Default timeout in seconds
```

### Configuration Class
```python
from pydantic import BaseSettings

class [Service]Config(BaseSettings):
    """Configuration for [Service] microservice."""
    
    # External service configuration
    [external_service]_url: str
    [external_service]_username: str
    [external_service]_api_token: str
    [external_service]_timeout: int = 30
    
    # Service configuration
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False
    
    class Config:
        env_file = ".env"
        case_sensitive = False

config = [Service]Config()
```

## Error Handling

### Custom Exceptions
```python
class [Service]Error(Exception):
    """Base exception for [Service] operations."""
    pass

class ExternalServiceError([Service]Error):
    """Exception for external service errors."""
    pass

class ValidationError([Service]Error):
    """Exception for validation errors."""
    pass
```

### Error Handler
```python
@app.exception_handler([Service]Error)
async def service_error_handler(request, exc):
    """Handle service-specific errors."""
    logger.error(f"Service error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "ServiceError",
            "detail": str(exc),
            "code": 500
        }
    )

@app.exception_handler(httpx.HTTPStatusError)
async def http_error_handler(request, exc):
    """Handle HTTP errors from external services."""
    logger.error(f"HTTP error: {exc}")
    return JSONResponse(
        status_code=503,
        content={
            "error": "ExternalServiceError",
            "detail": f"External service returned {exc.response.status_code}",
            "code": 503
        }
    )
```

## Testing Strategy

### Unit Tests
```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, Mock

@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)

@pytest.fixture
def mock_external_client():
    """Mock external client fixture."""
    client = Mock()
    client.process_operation = AsyncMock()
    client.get_resource = AsyncMock()
    return client

def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_primary_operation_success(client, mock_external_client):
    """Test successful primary operation."""
    # Mock dependencies
    app.dependency_overrides[get_client] = lambda: mock_external_client
    mock_external_client.process_operation.return_value = {"result": "success"}
    
    response = client.post(
        "/[primary_operation]",
        json={"field1": "test_value", "field2": 123}
    )
    
    assert response.status_code == 200
    assert response.json()["success"] is True
    
    # Clean up
    app.dependency_overrides.clear()

def test_validation_error(client, mock_external_client):
    """Test validation error handling."""
    app.dependency_overrides[get_client] = lambda: mock_external_client
    
    response = client.post(
        "/[primary_operation]",
        json={"invalid_field": "value"}
    )
    
    assert response.status_code == 422
    app.dependency_overrides.clear()
```

### Integration Tests
```python
import pytest
import asyncio
from httpx import AsyncClient

@pytest.mark.integration
async def test_integration_with_external_service():
    """Test integration with real external service."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            "/[primary_operation]",
            json={"field1": "integration_test", "field2": 456}
        )
        assert response.status_code == 200
```

## Deployment

### Dockerfile
```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Copy requirements
COPY pyproject.toml uv.lock ./

# Install uv and dependencies
RUN pip install uv && uv sync --frozen

# Copy application code
COPY app/ ./app/

# Expose port
EXPOSE 8000

# Run application
CMD ["uv", "run", "uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose
```yaml
version: '3.8'
services:
  [service_name]:
    build: .
    ports:
      - "8000:8000"
    environment:
      - [EXTERNAL_SERVICE]_URL=${[EXTERNAL_SERVICE]_URL}
      - [EXTERNAL_SERVICE]_USERNAME=${[EXTERNAL_SERVICE]_USERNAME}
      - [EXTERNAL_SERVICE]_API_TOKEN=${[EXTERNAL_SERVICE]_API_TOKEN}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Kubernetes Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: [service-name]
spec:
  replicas: 2
  selector:
    matchLabels:
      app: [service-name]
  template:
    metadata:
      labels:
        app: [service-name]
    spec:
      containers:
      - name: [service-name]
        image: [service-name]:latest
        ports:
        - containerPort: 8000
        env:
        - name: [EXTERNAL_SERVICE]_URL
          valueFrom:
            configMapKeyRef:
              name: [service-name]-config
              key: external-service-url
        - name: [EXTERNAL_SERVICE]_API_TOKEN
          valueFrom:
            secretKeyRef:
              name: [service-name]-secrets
              key: api-token
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
          initialDelaySeconds: 5
```

## Security Considerations

### Authentication & Authorization
- [ ] API token validation implemented
- [ ] Rate limiting configured
- [ ] Input sanitization in place
- [ ] No sensitive data in logs

### Network Security
- [ ] HTTPS only in production
- [ ] Firewall rules configured
- [ ] Service-to-service authentication

## Monitoring and Observability

### Logging Configuration
```python
import logging
from src.config import get_config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add correlation IDs for request tracking
@app.middleware("http")
async def logging_middleware(request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    with logger.contextualize(correlation_id=correlation_id):
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response
```

### Metrics Endpoints
```python
@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    # Implement Prometheus metrics collection
    pass
```

## Performance Considerations

### Response Time Targets
- Health checks: < 100ms
- Primary operations: < 2s
- Resource retrieval: < 500ms

### Scalability
- Stateless design for horizontal scaling
- Connection pooling for external services
- Async operations for I/O bound tasks

## Maintenance Checklist

### Pre-Deployment
- [ ] All tests passing
- [ ] Security review completed
- [ ] Performance benchmarks met
- [ ] Documentation updated
- [ ] Environment variables configured

### Post-Deployment
- [ ] Health checks responding
- [ ] Metrics being collected
- [ ] Logs being generated properly
- [ ] External service connectivity verified

## References

### Related Services
- [List related microservices for reference]

### Documentation
- Manager API Patterns: `context-engineering/examples/manager_api_patterns.py`
- Existing Tools: `src/tools/confluence/`, `src/tools/jira/`
- Configuration: `src/config.py`

### External APIs
- [Link to external service API documentation]