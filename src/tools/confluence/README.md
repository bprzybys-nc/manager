# Confluence Integration Tool

A comprehensive FastAPI-based tool for interacting with Confluence pages and spaces, featuring intelligent content search, vector-based similarity matching, and robust error handling.

## Features

### Core Functionality
- **Page Management**: Create, read, update, and delete Confluence pages
- **Content Search**: Search pages by title, content, or space with advanced filtering
- **Vector Search**: Semantic search using ChromaDB and sentence transformers
- **Attachment Handling**: Upload, download, and manage page attachments
- **Bulk Operations**: Process multiple pages efficiently with job management
- **Health Monitoring**: Comprehensive health checks and system status endpoints

### Advanced Features
- **Intelligent Content Processing**: Extract and process page content with BeautifulSoup
- **Error Recovery**: Robust error handling with retry mechanisms
- **Performance Optimization**: Async operations and efficient data processing
- **Runbook Management**: Specialized handling for operational documentation
- **Integration Testing**: Comprehensive test suite with real Confluence integration

## Architecture

The tool is built with a modular architecture:

```
app/
├── api.py              # FastAPI application and route definitions
├── confluence.py       # Core Confluence API client
├── vector_store.py     # ChromaDB integration for semantic search
├── models.py           # Pydantic data models
├── error_handler.py    # Centralized error handling
├── job_manager.py      # Background job processing
└── config.py           # Configuration management
```

## Configuration

### Environment Variables

Create a `.env` file with the following variables:

```bash
# Confluence Configuration
CONFLUENCE_URL=https://your-domain.atlassian.net
CONFLUENCE_USERNAME=your-email@domain.com
CONFLUENCE_API_TOKEN=your-api-token

# Vector Store Configuration (Optional)
CHROMA_PERSIST_DIRECTORY=./chroma
EMBEDDING_MODEL=all-MiniLM-L6-v2

# API Configuration (Optional)
API_HOST=0.0.0.0
API_PORT=8005
LOG_LEVEL=INFO
```

### Confluence API Token Setup

1. Go to [Atlassian Account Settings](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Click "Create API token"
3. Give it a descriptive label
4. Copy the generated token to your `.env` file

## Installation

### Using UV (Recommended)

```bash
# Install dependencies
uv sync

# Run the application
uv run uvicorn app.api:app --port 8005 --host 0.0.0.0
```

### Using Docker

```bash
# Build the image
docker build -t confluence-tool .

# Run the container
docker run -p 8005:8005 --env-file .env confluence-tool
```

### Using Docker Compose

```bash
# Start the service
docker-compose up -d
```

## API Documentation

### Core Endpoints

#### Pages
- `POST /pages` - Create a new page
- `GET /pages/{page_id}` - Get page by ID
- `PUT /pages/{page_id}` - Update page content
- `DELETE /pages/{page_id}` - Delete page
- `GET /pages/{page_id}/content` - Get page content with metadata

#### Search
- `GET /search` - Search pages with filters
- `POST /search/vector` - Semantic vector search
- `GET /search/spaces/{space_key}` - Search within specific space

#### Attachments
- `POST /pages/{page_id}/attachments` - Upload attachment
- `GET /pages/{page_id}/attachments` - List page attachments
- `GET /attachments/{attachment_id}` - Download attachment

#### Bulk Operations
- `POST /bulk/process` - Start bulk processing job
- `GET /jobs/{job_id}` - Get job status
- `POST /bulk/index` - Index pages for vector search

#### Health & Monitoring
- `GET /health` - Basic health check
- `GET /health/detailed` - Detailed system status
- `GET /health/confluence` - Confluence connectivity check

### Request/Response Examples

#### Create Page
```bash
curl -X POST "http://localhost:8005/pages" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "My New Page",
    "content": "<p>Page content here</p>",
    "space_key": "MYSPACE",
    "parent_id": "123456"
  }'
```

#### Search Pages
```bash
curl "http://localhost:8005/search?query=troubleshooting&space=DOCS&limit=10"
```

#### Vector Search
```bash
curl -X POST "http://localhost:8005/search/vector" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "database connection issues",
    "limit": 5,
    "space_key": "RUNBOOKS"
  }'
```

## Testing

### Unit Tests
```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=app

# Run specific test file
uv run pytest app/test_api.py -v
```

### Integration Tests
```bash
# Run integration tests (requires Confluence access)
python run_integration_tests.py
```

### Test Configuration
Create a `.env.test` file for test-specific configuration:
```bash
CONFLUENCE_URL=https://test-instance.atlassian.net
CONFLUENCE_USERNAME=test@example.com
CONFLUENCE_API_TOKEN=test-token
```

## Deployment

### Production Deployment

#### Docker Compose (Recommended)
```yaml
version: '3.8'
services:
  confluence-tool:
    build: .
    ports:
      - "8005:8005"
    environment:
      - CONFLUENCE_URL=${CONFLUENCE_URL}
      - CONFLUENCE_USERNAME=${CONFLUENCE_USERNAME}
      - CONFLUENCE_API_TOKEN=${CONFLUENCE_API_TOKEN}
    volumes:
      - ./chroma:/app/chroma
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8005/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

#### Kubernetes
See `k8s/` directory for Kubernetes manifests.

### Environment-Specific Configuration

#### Development
```bash
export LOG_LEVEL=DEBUG
export API_HOST=127.0.0.1
```

#### Production
```bash
export LOG_LEVEL=INFO
export API_HOST=0.0.0.0
# Add monitoring and security configurations
```

## Monitoring

### Health Checks
The service provides multiple health check endpoints:
- `/health` - Basic liveness check
- `/health/detailed` - Comprehensive system status
- `/health/confluence` - Confluence API connectivity

### Logging
Structured logging is available at multiple levels:
- `DEBUG` - Detailed operation logs
- `INFO` - General operation information
- `WARNING` - Non-critical issues
- `ERROR` - Error conditions

### Metrics
Key metrics to monitor:
- Request latency
- Error rates
- Confluence API response times
- Vector search performance
- Job processing status

## Troubleshooting

### Common Issues

#### Authentication Errors
- Verify API token is valid and not expired
- Check username format (usually email address)
- Ensure proper permissions in Confluence

#### Connection Issues
- Verify Confluence URL is accessible
- Check network connectivity
- Validate SSL certificates

#### Performance Issues
- Monitor vector store size and performance
- Check available memory for embeddings
- Review bulk operation batch sizes

### Debug Mode
Enable debug logging:
```bash
export LOG_LEVEL=DEBUG
uv run uvicorn app.api:app --port 8005 --host 0.0.0.0 --log-level debug
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

### Development Setup
```bash
# Install development dependencies
uv sync --group dev

# Install pre-commit hooks
pre-commit install

# Run linting
uv run ruff check app/
uv run black app/
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review existing GitHub issues
3. Create a new issue with detailed information