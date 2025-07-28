# DB Runbook Finder Workflow - Context Engineering Specification

## FEATURE:
**AI-Powered Database Runbook Discovery and Semantic Search Workflow**

Implement a comprehensive workflow that leverages ChromaDB vector database and Confluence integration to provide intelligent database runbook discovery, semantic search capabilities, and automated runbook extraction for the SysAIdmin platform.

### Core Capabilities:
- **Semantic Search**: RAG-based runbook discovery using ChromaDB vector embeddings
- **Confluence Integration**: Automated runbook extraction from Confluence pages  
- **Vector Database Management**: Persistent storage and indexing of runbook content
- **Bulk Operations**: Parallel processing of multiple runbook extractions
- **Job Management**: Asynchronous task tracking with comprehensive status monitoring
- **Health Monitoring**: Multi-layer system health checks and metrics collection

### Technical Components:
- **GraphMCP Framework**: Utilizes the shared workflow orchestration framework
- **ChromaDB Vector Store**: Semantic similarity search with sentence-transformers
- **Confluence API Client**: Full CRUD operations for page management
- **FastAPI Service**: RESTful API endpoints for all runbook operations
- **Job Management System**: Background task processing with Redis/Celery integration
- **Comprehensive Testing**: Mock data, integration tests, and performance validation

## EXAMPLES:
### Test Data Structure (`tests/data/`):
- **Mock Runbook Dataset**: 5 comprehensive database runbooks covering:
  - Database Connection Troubleshooting (`database_connection_runbook.json`)
  - Performance Monitoring & Optimization (`performance_monitoring_runbook.json`) 
  - Backup & Recovery Procedures (`backup_recovery_runbook.json`)
  - Security Hardening & Access Control (`security_hardening_runbook.json`)
  - Database Migration & Schema Changes (`migration_runbook.json`)

### Test Data Loader (`test_data_loader.py`):
- **MockRunbookDataLoader**: Comprehensive test data management
- **Semantic Search Queries**: Predefined test queries with expected results
- **Error Test Cases**: Validation scenarios for comprehensive error handling
- **Performance Test Data**: Load testing and timing validation scenarios

### Endpoint Test Coverage (`test_comprehensive_chromadb_endpoints.py`):
- **Health Endpoints**: `/health`, `/health/ready`, `/health/live`, `/metrics`
- **Runbook Management**: `/runbooks`, `/runbooks/{id}`, `/pages/extract`
- **Search Operations**: `/search/runbooks`, `/search/confluence`
- **Bulk Operations**: `/pages/bulk-extract`, `/jobs/{id}`, `/jobs/statistics`
- **Error Handling**: Comprehensive validation and error response testing
- **Performance Testing**: Response time validation and load testing

## DOCUMENTATION:
### Primary References:
- **GraphMCP Framework**: `/manager/src/frameworks/graphmcp/` - Shared workflow orchestration
- **ChromaDB Documentation**: Vector database operations and semantic search
- **Confluence API**: REST API integration for page management
- **FastAPI Documentation**: API endpoint design and validation patterns
- **Sentence Transformers**: Text embedding models for semantic search

### Configuration Files:
- **Manager pyproject.toml**: All dependencies (chromadb>=0.4.0, sentence-transformers>=2.2.0, atlassian-python-api>=3.41.0)
- **Environment Variables**: CONFLUENCE_URL, CONFLUENCE_USERNAME, CONFLUENCE_API_TOKEN
- **MCP Server Config**: GitHub, Slack, Repomix, and Filesystem integrations

### Integration Points:
- **Existing Confluence Tool**: `/manager/src/tools/confluence/` - API client and vector store
- **Jira Integration**: `/manager/src/tools/jira/` - Ticket management workflow integration  
- **Database Client**: MongoDB integration for persistent storage
- **Slack Notifications**: Workflow completion and error reporting

## OTHER CONSIDERATIONS:
### Critical Implementation Requirements:

1. **Single Python Environment Rule**: 
   - ALL code MUST use `/Users/bprzybysz/nc-src/ovora/manager/.venv/bin/python`
   - NO separate virtual environments for tools or components
   - ALL dependencies managed through manager's main pyproject.toml

2. **GraphMCP Framework Integration**:
   - Use existing workflow patterns from `/manager/src/frameworks/graphmcp/`
   - Implement multi-client orchestration pattern (GitHub, Slack, Repomix)
   - Follow fluent workflow builder pattern with `step_auto()` preference
   - Implement graceful degradation with caching for offline capability

3. **ChromaDB Vector Store Architecture**:
   - Database files at `/manager/src/tools/confluence/app/chroma/chroma.sqlite3`
   - Collection initialization and embedding management
   - Semantic similarity search with configurable thresholds
   - Batch processing for large runbook datasets

4. **Error Handling and Resilience**:
   - Comprehensive error responses with structured logging
   - Graceful degradation when Confluence is unavailable
   - Vector database fallback mechanisms
   - Job failure recovery and retry logic

5. **Performance Requirements**:
   - Search response time < 2 seconds for semantic queries
   - Bulk extraction jobs handle 50+ pages concurrently
   - Vector database queries support 10+ concurrent users
   - Memory-efficient embedding generation and storage

6. **Testing Strategy**:
   - Mock data enables offline development and CI/CD
   - Comprehensive endpoint coverage (health, CRUD, search, bulk ops)
   - Performance validation with timing assertions
   - Error handling validation for all failure scenarios

7. **Security Considerations**:
   - API token masking in logs and error messages
   - Input validation for all search queries and parameters
   - Rate limiting for API endpoints
   - Secure vector database access patterns

8. **Monitoring and Observability**:
   - Structured logging with correlation IDs
   - Prometheus metrics for operational monitoring
   - Health check endpoints for Kubernetes integration
   - Job statistics and performance metrics

### Common AI Assistant Gotchas:
- **Don't create separate tool environments**: Use manager's single .venv
- **Don't skip comprehensive testing**: All endpoints need full test coverage
- **Don't ignore ChromaDB initialization**: Collections must be properly set up
- **Don't forget error handling**: Every endpoint needs validation and error responses
- **Don't overlook performance**: Semantic search must be optimized for production use
- **Don't miss integration patterns**: Follow existing GraphMCP framework conventions
- **Don't create unnecessary files**: Extend existing tools rather than creating new ones