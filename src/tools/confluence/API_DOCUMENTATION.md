# Confluence Integration Tool - API Documentation

## Overview

The Confluence Integration Tool provides a comprehensive REST API for interacting with Confluence pages, spaces, and attachments. This document provides detailed information about all available endpoints, request/response formats, and usage examples.

## Base URL

```
http://localhost:8005
```

## Authentication

The API uses Confluence API tokens for authentication. Configure your credentials using environment variables:

- `CONFLUENCE_URL`: Your Confluence instance URL
- `CONFLUENCE_USERNAME`: Your Confluence username (email)
- `CONFLUENCE_API_TOKEN`: Your Confluence API token

## Content Types

All endpoints accept and return JSON unless otherwise specified.

```
Content-Type: application/json
```

## Error Handling

The API returns standard HTTP status codes and structured error responses:

```json
{
  "error": "Error description",
  "details": "Additional error details",
  "status_code": 400
}
```

## Endpoints

### Health Check Endpoints

#### GET /health
Basic health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

#### GET /health/detailed
Detailed system status including dependencies.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "components": {
    "confluence": "healthy",
    "vector_store": "healthy",
    "database": "healthy"
  },
  "version": "0.1.0"
}
```

#### GET /health/confluence
Check Confluence API connectivity.

**Response:**
```json
{
  "status": "healthy",
  "confluence_url": "https://your-domain.atlassian.net",
  "response_time_ms": 150
}
```

### Page Management

#### POST /pages
Create a new Confluence page.

**Request Body:**
```json
{
  "title": "Page Title",
  "content": "<p>Page content in HTML format</p>",
  "space_key": "SPACE",
  "parent_id": "123456"
}
```

**Response:**
```json
{
  "id": "789012",
  "title": "Page Title",
  "space_key": "SPACE",
  "url": "https://your-domain.atlassian.net/wiki/spaces/SPACE/pages/789012",
  "created_at": "2024-01-15T10:30:00Z"
}
```

#### GET /pages/{page_id}
Retrieve a page by ID.

**Parameters:**
- `page_id` (path): The Confluence page ID

**Response:**
```json
{
  "id": "789012",
  "title": "Page Title",
  "content": "<p>Page content</p>",
  "space_key": "SPACE",
  "version": 1,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

#### PUT /pages/{page_id}
Update an existing page.

**Parameters:**
- `page_id` (path): The Confluence page ID

**Request Body:**
```json
{
  "title": "Updated Title",
  "content": "<p>Updated content</p>",
  "version": 2
}
```

**Response:**
```json
{
  "id": "789012",
  "title": "Updated Title",
  "version": 2,
  "updated_at": "2024-01-15T11:00:00Z"
}
```

#### DELETE /pages/{page_id}
Delete a page.

**Parameters:**
- `page_id` (path): The Confluence page ID

**Response:**
```json
{
  "message": "Page deleted successfully",
  "page_id": "789012"
}
```

#### GET /pages/{page_id}/content
Get page content with metadata.

**Parameters:**
- `page_id` (path): The Confluence page ID

**Response:**
```json
{
  "id": "789012",
  "title": "Page Title",
  "content": {
    "html": "<p>Page content</p>",
    "text": "Page content",
    "word_count": 2
  },
  "metadata": {
    "space_key": "SPACE",
    "version": 1,
    "labels": ["tag1", "tag2"],
    "restrictions": []
  }
}
```

### Search Endpoints

#### GET /search
Search pages with various filters.

**Query Parameters:**
- `query` (required): Search query string
- `space` (optional): Space key to limit search
- `type` (optional): Content type (page, blogpost)
- `limit` (optional): Maximum results (default: 25)
- `start` (optional): Starting index for pagination (default: 0)

**Example:**
```
GET /search?query=troubleshooting&space=DOCS&limit=10
```

**Response:**
```json
{
  "results": [
    {
      "id": "123456",
      "title": "Troubleshooting Guide",
      "space_key": "DOCS",
      "excerpt": "This guide covers common troubleshooting steps...",
      "url": "https://your-domain.atlassian.net/wiki/spaces/DOCS/pages/123456"
    }
  ],
  "total": 1,
  "start": 0,
  "limit": 10
}
```

#### POST /search/vector
Perform semantic vector search.

**Request Body:**
```json
{
  "query": "database connection issues",
  "limit": 5,
  "space_key": "RUNBOOKS",
  "threshold": 0.7
}
```

**Response:**
```json
{
  "results": [
    {
      "id": "456789",
      "title": "Database Connection Troubleshooting",
      "content_snippet": "When experiencing database connection issues...",
      "similarity_score": 0.85,
      "space_key": "RUNBOOKS"
    }
  ],
  "query": "database connection issues",
  "total": 1
}
```

#### GET /search/spaces/{space_key}
Search within a specific space.

**Parameters:**
- `space_key` (path): The space key to search within

**Query Parameters:**
- `query` (required): Search query string
- `limit` (optional): Maximum results (default: 25)

**Response:**
```json
{
  "results": [
    {
      "id": "789012",
      "title": "Space-specific Page",
      "excerpt": "Content excerpt...",
      "url": "https://your-domain.atlassian.net/wiki/spaces/SPACE/pages/789012"
    }
  ],
  "space_key": "SPACE",
  "total": 1
}
```

### Attachment Management

#### POST /pages/{page_id}/attachments
Upload an attachment to a page.

**Parameters:**
- `page_id` (path): The Confluence page ID

**Request:**
- Content-Type: `multipart/form-data`
- Form field: `file` (the file to upload)

**Response:**
```json
{
  "id": "att123456",
  "title": "document.pdf",
  "media_type": "application/pdf",
  "file_size": 1024000,
  "download_url": "/attachments/att123456"
}
```

#### GET /pages/{page_id}/attachments
List all attachments for a page.

**Parameters:**
- `page_id` (path): The Confluence page ID

**Response:**
```json
{
  "attachments": [
    {
      "id": "att123456",
      "title": "document.pdf",
      "media_type": "application/pdf",
      "file_size": 1024000,
      "created_at": "2024-01-15T10:30:00Z"
    }
  ],
  "total": 1
}
```

#### GET /attachments/{attachment_id}
Download an attachment.

**Parameters:**
- `attachment_id` (path): The attachment ID

**Response:**
- Binary file content with appropriate Content-Type header

### Bulk Operations

#### POST /bulk/process
Start a bulk processing job.

**Request Body:**
```json
{
  "operation": "index_pages",
  "space_keys": ["DOCS", "RUNBOOKS"],
  "filters": {
    "updated_since": "2024-01-01T00:00:00Z"
  }
}
```

**Response:**
```json
{
  "job_id": "job_123456",
  "status": "started",
  "operation": "index_pages",
  "created_at": "2024-01-15T10:30:00Z"
}
```

#### GET /jobs/{job_id}
Get job status and results.

**Parameters:**
- `job_id` (path): The job ID

**Response:**
```json
{
  "job_id": "job_123456",
  "status": "completed",
  "operation": "index_pages",
  "progress": {
    "total": 100,
    "completed": 100,
    "failed": 0
  },
  "results": {
    "pages_processed": 100,
    "pages_indexed": 98,
    "errors": []
  },
  "created_at": "2024-01-15T10:30:00Z",
  "completed_at": "2024-01-15T10:35:00Z"
}
```

#### POST /bulk/index
Index pages for vector search.

**Request Body:**
```json
{
  "space_keys": ["DOCS"],
  "page_ids": ["123456", "789012"],
  "force_reindex": false
}
```

**Response:**
```json
{
  "job_id": "job_789012",
  "status": "started",
  "pages_to_index": 2
}
```

## Error Codes

| Status Code | Description |
|-------------|-------------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request - Invalid input |
| 401 | Unauthorized - Invalid credentials |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource doesn't exist |
| 409 | Conflict - Resource already exists |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Internal Server Error |
| 502 | Bad Gateway - Confluence API error |
| 503 | Service Unavailable |

## Rate Limiting

The API implements rate limiting to prevent abuse:
- 100 requests per minute per IP address
- 1000 requests per hour per API token

Rate limit headers are included in responses:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1642248600
```

## Pagination

Search endpoints support pagination using `start` and `limit` parameters:

```
GET /search?query=test&start=25&limit=25
```

Response includes pagination metadata:
```json
{
  "results": [...],
  "total": 150,
  "start": 25,
  "limit": 25,
  "has_more": true
}
```

## Examples

### Complete Page Creation Workflow

1. **Create a page:**
```bash
curl -X POST "http://localhost:8005/pages" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "API Documentation",
    "content": "<h1>Welcome</h1><p>This is our API documentation.</p>",
    "space_key": "DOCS"
  }'
```

2. **Upload an attachment:**
```bash
curl -X POST "http://localhost:8005/pages/123456/attachments" \
  -F "file=@api-spec.pdf"
```

3. **Search for the page:**
```bash
curl "http://localhost:8005/search?query=API+Documentation&space=DOCS"
```

### Vector Search Example

```bash
curl -X POST "http://localhost:8005/search/vector" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How to troubleshoot database connectivity issues",
    "limit": 3,
    "space_key": "RUNBOOKS"
  }'
```

### Bulk Indexing Example

```bash
curl -X POST "http://localhost:8005/bulk/index" \
  -H "Content-Type: application/json" \
  -d '{
    "space_keys": ["DOCS", "RUNBOOKS"],
    "force_reindex": true
  }'
```

## SDK and Client Libraries

### Python Client Example

```python
import requests

class ConfluenceToolClient:
    def __init__(self, base_url="http://localhost:8005"):
        self.base_url = base_url
    
    def create_page(self, title, content, space_key, parent_id=None):
        data = {
            "title": title,
            "content": content,
            "space_key": space_key
        }
        if parent_id:
            data["parent_id"] = parent_id
        
        response = requests.post(f"{self.base_url}/pages", json=data)
        return response.json()
    
    def search_pages(self, query, space=None, limit=25):
        params = {"query": query, "limit": limit}
        if space:
            params["space"] = space
        
        response = requests.get(f"{self.base_url}/search", params=params)
        return response.json()

# Usage
client = ConfluenceToolClient()
page = client.create_page("Test Page", "<p>Content</p>", "DOCS")
results = client.search_pages("test", space="DOCS")
```

### JavaScript Client Example

```javascript
class ConfluenceToolClient {
    constructor(baseUrl = 'http://localhost:8005') {
        this.baseUrl = baseUrl;
    }
    
    async createPage(title, content, spaceKey, parentId = null) {
        const data = { title, content, space_key: spaceKey };
        if (parentId) data.parent_id = parentId;
        
        const response = await fetch(`${this.baseUrl}/pages`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        return response.json();
    }
    
    async searchPages(query, space = null, limit = 25) {
        const params = new URLSearchParams({ query, limit });
        if (space) params.append('space', space);
        
        const response = await fetch(`${this.baseUrl}/search?${params}`);
        return response.json();
    }
}

// Usage
const client = new ConfluenceToolClient();
const page = await client.createPage('Test Page', '<p>Content</p>', 'DOCS');
const results = await client.searchPages('test', 'DOCS');
```

## OpenAPI Specification

The complete OpenAPI 3.0 specification is available at:
```
GET /openapi.json
```

You can also view the interactive documentation at:
```
GET /docs
```