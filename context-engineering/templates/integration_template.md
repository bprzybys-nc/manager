# External Service Integration Template

## Basic Information

**Integration Name**: [Name of the external service integration]
**External Service**: [Name of external service - Slack, GitHub, Jira, etc.]
**Component**: Manager/Tools
**Integration Type**: [API/Webhook/Event-driven/Database/File-based]
**Authentication Method**: [OAuth/API Key/Basic Auth/JWT/etc.]

## Business Context

### Problem Statement
[Describe why this integration is needed and what problem it solves]

### Business Requirements
- **Primary Use Case**: [Main business use case]
- **Secondary Use Cases**: [Additional use cases]
- **Business Value**: [Expected business impact]
- **Success Metrics**: [How success will be measured]

### Integration Requirements
- **Data Flow Direction**: [Inbound/Outbound/Bidirectional]
- **Real-time vs Batch**: [Processing requirements]
- **Data Volume**: [Expected data volume and frequency]
- **Reliability Requirements**: [Uptime, error tolerance]

## External Service Analysis

### Service Overview
**Service Name**: [External service name]
**Documentation**: [Link to official API documentation]
**API Version**: [Which API version to use]
**Rate Limits**: [API rate limits and quotas]
**SLA/Uptime**: [Service level agreements]

### Authentication & Authorization
```json
{
  "auth_type": "[OAuth2/API Key/Basic Auth]",
  "credentials_required": [
    "API_TOKEN",
    "CLIENT_ID",
    "CLIENT_SECRET"
  ],
  "scopes_needed": [
    "read:data",
    "write:data"
  ],
  "token_refresh": "automatic/manual"
}
```

### API Endpoints Analysis
| Endpoint | Method | Purpose | Rate Limit | Auth Required |
|----------|---------|---------|------------|---------------|
| `/api/resource` | GET | List resources | 100/hour | Yes |
| `/api/resource/{id}` | GET | Get resource | 1000/hour | Yes |
| `/api/resource` | POST | Create resource | 50/hour | Yes |
| `/api/resource/{id}` | PUT | Update resource | 50/hour | Yes |
| `/api/resource/{id}` | DELETE | Delete resource | 25/hour | Yes |

### Data Models
```python
# External service data models
@dataclass
class ExternalResource:
    """Model representing external service resource."""
    id: str
    name: str
    status: str
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any]
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'ExternalResource':
        """Create instance from API response."""
        return cls(
            id=data['id'],
            name=data['name'],
            status=data['status'],
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at']),
            metadata=data.get('metadata', {})
        )
    
    def to_api_request(self) -> Dict[str, Any]:
        """Convert to API request format."""
        return {
            'name': self.name,
            'status': self.status,
            'metadata': self.metadata
        }
```

## Integration Architecture

### Component Design
```
┌─────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│   Manager API   │───▶│  Integration     │───▶│  External        │
│                 │    │  Client          │    │  Service API     │
│  - Receives     │    │                  │    │                  │
│    requests     │◀───│  - Auth handling │◀───│  - Rate limiting │
│  - Validates    │    │  - Request/      │    │  - Data          │
│    input        │    │    Response      │    │    validation    │
│  - Returns      │    │    mapping       │    │  - Error         │
│    results      │    │  - Error         │    │    responses     │
└─────────────────┘    │    handling      │    └──────────────────┘
                       │  - Caching       │
                       └──────────────────┘
```

### Data Flow
1. **Inbound Data Flow** (External Service → Manager)
   - External service sends data via webhook/polling
   - Integration client receives and validates data
   - Data transformed to Manager format
   - Data stored in Manager database
   - Notifications sent if required

2. **Outbound Data Flow** (Manager → External Service)
   - Manager API receives request
   - Data validated and transformed
   - Integration client sends to external service
   - Response processed and returned
   - Audit logs created

### Error Handling Strategy
```python
class IntegrationError(Exception):
    """Base exception for integration errors."""
    pass

class AuthenticationError(IntegrationError):
    """Authentication with external service failed."""
    pass

class RateLimitError(IntegrationError):
    """Rate limit exceeded."""
    def __init__(self, reset_time: Optional[datetime] = None):
        self.reset_time = reset_time
        super().__init__("Rate limit exceeded")

class ServiceUnavailableError(IntegrationError):
    """External service is unavailable."""
    pass

class DataValidationError(IntegrationError):
    """Data validation failed."""
    pass
```

## Implementation

### Integration Client
```python
import httpx
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import backoff

class [ExternalService]Integration:
    """Integration client for [External Service]."""
    
    def __init__(
        self,
        base_url: str,
        api_token: str,
        timeout: int = 30,
        max_retries: int = 3
    ):
        self.base_url = base_url.rstrip('/')
        self.api_token = api_token
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: Optional[httpx.AsyncClient] = None
        self._rate_limit_reset: Optional[datetime] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            timeout=self.timeout,
            headers={
                'Authorization': f'Bearer {self.api_token}',
                'Content-Type': 'application/json',
                'User-Agent': 'Ovora-Manager/1.0'
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
    
    @backoff.on_exception(
        backoff.expo,
        (httpx.RequestError, httpx.TimeoutException),
        max_tries=3
    )
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> httpx.Response:
        """Make HTTP request with retry logic."""
        # Check rate limiting
        if self._rate_limit_reset and datetime.utcnow() < self._rate_limit_reset:
            wait_time = (self._rate_limit_reset - datetime.utcnow()).total_seconds()
            await asyncio.sleep(wait_time)
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        response = await self._client.request(method, url, **kwargs)
        
        # Handle rate limiting
        if response.status_code == 429:
            reset_time = response.headers.get('X-RateLimit-Reset')
            if reset_time:
                self._rate_limit_reset = datetime.fromtimestamp(int(reset_time))
            raise RateLimitError(self._rate_limit_reset)
        
        # Handle authentication errors
        if response.status_code == 401:
            raise AuthenticationError("Invalid or expired credentials")
        
        # Handle service unavailable
        if response.status_code >= 500:
            raise ServiceUnavailableError(f"Service returned {response.status_code}")
        
        response.raise_for_status()
        return response
    
    async def get_resource(self, resource_id: str) -> Optional[ExternalResource]:
        """Get resource by ID."""
        try:
            response = await self._make_request('GET', f'/api/resource/{resource_id}')
            data = response.json()
            return ExternalResource.from_api_response(data)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise
    
    async def list_resources(
        self,
        limit: int = 100,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ExternalResource]:
        """List resources with pagination."""
        params = {
            'limit': limit,
            'offset': offset,
            **(filters or {})
        }
        
        response = await self._make_request('GET', '/api/resource', params=params)
        data = response.json()
        
        return [
            ExternalResource.from_api_response(item)
            for item in data.get('items', [])
        ]
    
    async def create_resource(self, resource: ExternalResource) -> ExternalResource:
        """Create new resource."""
        response = await self._make_request(
            'POST',
            '/api/resource',
            json=resource.to_api_request()
        )
        data = response.json()
        return ExternalResource.from_api_response(data)
    
    async def update_resource(
        self,
        resource_id: str,
        updates: Dict[str, Any]
    ) -> ExternalResource:
        """Update existing resource."""
        response = await self._make_request(
            'PUT',
            f'/api/resource/{resource_id}',
            json=updates
        )
        data = response.json()
        return ExternalResource.from_api_response(data)
    
    async def delete_resource(self, resource_id: str) -> bool:
        """Delete resource."""
        try:
            await self._make_request('DELETE', f'/api/resource/{resource_id}')
            return True
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return False
            raise
```

### Manager API Integration
```python
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from typing import List, Optional

router = APIRouter(prefix="/integration/[service]", tags=["[service]"])

def get_integration_client() -> [ExternalService]Integration:
    """Get integration client."""
    config = get_config()
    return [ExternalService]Integration(
        base_url=config.[EXTERNAL_SERVICE]_URL,
        api_token=config.[EXTERNAL_SERVICE]_API_TOKEN
    )

@router.get("/resources/{resource_id}")
async def get_resource(
    resource_id: str,
    client: [ExternalService]Integration = Depends(get_integration_client)
):
    """Get resource from external service."""
    try:
        async with client:
            resource = await client.get_resource(resource_id)
            if not resource:
                raise HTTPException(status_code=404, detail="Resource not found")
            return resource
    except AuthenticationError:
        raise HTTPException(status_code=401, detail="Authentication failed")
    except ServiceUnavailableError:
        raise HTTPException(status_code=503, detail="External service unavailable")
    except Exception as e:
        logger.error(f"Error retrieving resource: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/resources")
async def create_resource(
    resource_data: Dict[str, Any],
    background_tasks: BackgroundTasks,
    client: [ExternalService]Integration = Depends(get_integration_client)
):
    """Create resource in external service."""
    try:
        # Validate input data
        resource = ExternalResource(**resource_data)
        
        async with client:
            created_resource = await client.create_resource(resource)
            
        # Schedule background tasks
        background_tasks.add_task(sync_to_database, created_resource)
        background_tasks.add_task(send_notifications, created_resource)
        
        return created_resource
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating resource: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
```

## Webhook Integration (if applicable)

### Webhook Receiver
```python
@router.post("/webhook")
async def webhook_handler(
    request: Request,
    background_tasks: BackgroundTasks,
    signature: str = Header(None, alias="X-[Service]-Signature")
):
    """Handle webhooks from external service."""
    try:
        # Verify webhook signature
        body = await request.body()
        if not verify_webhook_signature(body, signature):
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Parse webhook payload
        payload = await request.json()
        webhook_type = payload.get('type')
        
        # Process webhook based on type
        if webhook_type == 'resource.created':
            background_tasks.add_task(handle_resource_created, payload['data'])
        elif webhook_type == 'resource.updated':
            background_tasks.add_task(handle_resource_updated, payload['data'])
        elif webhook_type == 'resource.deleted':
            background_tasks.add_task(handle_resource_deleted, payload['data'])
        else:
            logger.warning(f"Unknown webhook type: {webhook_type}")
        
        return {"status": "received"}
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")

def verify_webhook_signature(body: bytes, signature: str) -> bool:
    """Verify webhook signature."""
    import hmac
    import hashlib
    
    secret = get_config().WEBHOOK_SECRET
    expected = hmac.new(
        secret.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(f"sha256={expected}", signature)
```

## Caching Strategy

### Response Caching
```python
import redis.asyncio as redis
from typing import Optional
import json
from datetime import timedelta

class IntegrationCache:
    """Cache for integration responses."""
    
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)
    
    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached data."""
        data = await self.redis.get(f"integration:[service]:{key}")
        return json.loads(data) if data else None
    
    async def set(
        self,
        key: str,
        data: Dict[str, Any],
        ttl: timedelta = timedelta(minutes=15)
    ):
        """Set cached data."""
        await self.redis.setex(
            f"integration:[service]:{key}",
            int(ttl.total_seconds()),
            json.dumps(data, default=str)
        )
    
    async def delete(self, key: str):
        """Delete cached data."""
        await self.redis.delete(f"integration:[service]:{key}")
```

## Testing Strategy

### Unit Tests
```python
import pytest
from unittest.mock import AsyncMock, Mock, patch
import httpx

@pytest.fixture
def mock_client():
    """Mock HTTP client."""
    client = Mock()
    client.request = AsyncMock()
    return client

@pytest.fixture
def integration_client(mock_client):
    """Integration client with mocked HTTP client."""
    client = [ExternalService]Integration(
        base_url="https://api.example.com",
        api_token="test_token"
    )
    client._client = mock_client
    return client

@pytest.mark.asyncio
async def test_get_resource_success(integration_client, mock_client):
    """Test successful resource retrieval."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'id': '123',
        'name': 'Test Resource',
        'status': 'active',
        'created_at': '2023-01-01T00:00:00Z',
        'updated_at': '2023-01-01T00:00:00Z'
    }
    mock_client.request.return_value = mock_response
    
    resource = await integration_client.get_resource('123')
    
    assert resource is not None
    assert resource.id == '123'
    assert resource.name == 'Test Resource'

@pytest.mark.asyncio
async def test_rate_limiting(integration_client, mock_client):
    """Test rate limiting handling."""
    mock_response = Mock()
    mock_response.status_code = 429
    mock_response.headers = {'X-RateLimit-Reset': str(int(time.time() + 60))}
    mock_client.request.return_value = mock_response
    
    with pytest.raises(RateLimitError):
        await integration_client.get_resource('123')
```

### Integration Tests
```python
@pytest.mark.integration
async def test_real_api_integration():
    """Test with real external API (requires test credentials)."""
    client = [ExternalService]Integration(
        base_url=os.getenv('TEST_API_URL'),
        api_token=os.getenv('TEST_API_TOKEN')
    )
    
    async with client:
        resources = await client.list_resources(limit=1)
        assert isinstance(resources, list)
```

## Configuration

### Environment Variables
```bash
# External service configuration
[EXTERNAL_SERVICE]_URL=https://api.external-service.com
[EXTERNAL_SERVICE]_API_TOKEN=your_api_token_here
[EXTERNAL_SERVICE]_TIMEOUT=30

# Webhook configuration (if applicable)
WEBHOOK_SECRET=your_webhook_secret
WEBHOOK_URL=https://your-domain.com/api/integration/[service]/webhook

# Cache configuration
REDIS_URL=redis://localhost:6379/0

# Rate limiting configuration
RATE_LIMIT_PER_HOUR=1000
RATE_LIMIT_BURST=50
```

### Configuration Validation
```python
from pydantic import BaseSettings, validator

class IntegrationConfig(BaseSettings):
    """Configuration for external service integration."""
    
    [external_service]_url: str
    [external_service]_api_token: str
    [external_service]_timeout: int = 30
    webhook_secret: Optional[str] = None
    redis_url: str = "redis://localhost:6379/0"
    
    @validator('[external_service]_url')
    def validate_url(cls, v):
        """Validate URL format."""
        if not v.startswith(('http://', 'https://')):
            raise ValueError('URL must start with http:// or https://')
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False
```

## Monitoring and Observability

### Metrics Collection
```python
from prometheus_client import Counter, Histogram, Gauge

# Metrics
integration_requests_total = Counter(
    'integration_requests_total',
    'Total integration requests',
    ['service', 'endpoint', 'status']
)

integration_request_duration = Histogram(
    'integration_request_duration_seconds',
    'Integration request duration',
    ['service', 'endpoint']
)

integration_rate_limit_remaining = Gauge(
    'integration_rate_limit_remaining',
    'Remaining rate limit',
    ['service']
)

# Usage in client
async def _make_request(self, method: str, endpoint: str, **kwargs):
    """Make request with metrics collection."""
    start_time = time.time()
    
    try:
        response = await self._client.request(method, url, **kwargs)
        
        # Record metrics
        integration_requests_total.labels(
            service='[service]',
            endpoint=endpoint,
            status=response.status_code
        ).inc()
        
        # Record rate limit info
        remaining = response.headers.get('X-RateLimit-Remaining')
        if remaining:
            integration_rate_limit_remaining.labels(service='[service]').set(int(remaining))
        
        return response
    finally:
        duration = time.time() - start_time
        integration_request_duration.labels(
            service='[service]',
            endpoint=endpoint
        ).observe(duration)
```

### Health Checks
```python
@router.get("/health")
async def integration_health():
    """Check integration health."""
    client = get_integration_client()
    
    try:
        async with client:
            # Try a simple API call
            await client._make_request('GET', '/health')
        
        return {
            "status": "healthy",
            "service": "[external_service]",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Integration unhealthy: {str(e)}"
        )
```

## Security Considerations

### Authentication Security
- [ ] API tokens stored securely (environment variables/secrets manager)
- [ ] Token rotation strategy implemented
- [ ] Webhook signature verification enabled
- [ ] Rate limiting configured

### Data Security
- [ ] Sensitive data encrypted at rest and in transit
- [ ] Data retention policies implemented
- [ ] Audit logging enabled
- [ ] Input validation and sanitization

### Network Security
- [ ] HTTPS only communication
- [ ] IP allowlisting configured (if supported)
- [ ] VPN/private network access (if required)

## Performance Optimization

### Response Time Targets
- API calls: < 2 seconds
- Webhook processing: < 500ms
- Background sync: < 30 seconds

### Optimization Strategies
- Connection pooling and keep-alive
- Response caching with appropriate TTL
- Asynchronous processing for non-critical operations
- Batch operations where supported

## Deployment Checklist

### Pre-Deployment
- [ ] Integration tests passing
- [ ] Rate limiting tested
- [ ] Error handling validated
- [ ] Security review completed
- [ ] Documentation updated

### Post-Deployment
- [ ] Health checks responding
- [ ] Metrics being collected
- [ ] Webhooks receiving data (if applicable)
- [ ] Error rates within acceptable limits

## Troubleshooting Guide

### Common Issues
| Issue | Symptoms | Solutions |
|-------|----------|-----------|
| Authentication failures | 401 errors | Check token validity, rotation needed |
| Rate limiting | 429 errors | Implement backoff, check limits |
| Service unavailable | 5xx errors | Check service status, implement fallbacks |
| Webhook failures | Missing data | Check signature, endpoint accessibility |

### Debug Commands
```bash
# Check integration health
curl -X GET "http://localhost:9123/api/integration/[service]/health"

# Test webhook endpoint
curl -X POST "http://localhost:9123/api/integration/[service]/webhook" \
  -H "Content-Type: application/json" \
  -H "X-[Service]-Signature: test" \
  -d '{"type": "test", "data": {}}'
```

## References

### Documentation
- External Service API: [Link to official documentation]
- Manager API Patterns: `context-engineering/examples/manager_api_patterns.py`
- Configuration Management: `src/config.py`

### Related Integrations
- [List other similar integrations for reference]

### Support Resources
- External Service Support: [Support contact information]
- Internal Documentation: [Internal documentation links]