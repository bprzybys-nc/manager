# Integration Testing Guide

This guide provides comprehensive instructions for running integration tests against the Confluence Integration Tool.

## Overview

Integration tests verify that the tool correctly interacts with a real Confluence instance. These tests cover:

- Authentication and connectivity
- Page CRUD operations
- Search functionality
- Attachment management
- Vector search capabilities
- Error handling scenarios

## Prerequisites

### Confluence Instance Access

You need access to a Confluence instance with:
- API token authentication enabled
- Permissions to create, read, update, and delete pages
- At least one space for testing
- Ability to upload attachments

### Test Environment Setup

1. **Create a test space** in your Confluence instance (e.g., "TESTSPACE")
2. **Generate an API token** for your test user
3. **Configure test environment variables**

## Configuration

### Environment Variables

Create a `.env.test` file in the project root:

```bash
# Test Confluence Configuration
CONFLUENCE_URL=https://your-test-domain.atlassian.net
CONFLUENCE_USERNAME=test-user@domain.com
CONFLUENCE_API_TOKEN=your-test-api-token

# Test Space Configuration
TEST_SPACE_KEY=TESTSPACE
TEST_PARENT_PAGE_ID=123456

# Vector Store Test Configuration
TEST_CHROMA_PERSIST_DIRECTORY=./test_chroma
TEST_EMBEDDING_MODEL=all-MiniLM-L6-v2

# API Test Configuration
TEST_API_HOST=127.0.0.1
TEST_API_PORT=8006
TEST_LOG_LEVEL=DEBUG
```

### Test Data Setup

The integration tests will create and clean up test data automatically, but you may want to prepare:

1. **Test pages** with known content for search testing
2. **Test attachments** (small PDF, image files)
3. **Test space** with appropriate permissions

## Running Integration Tests

### Quick Start

```bash
# Install test dependencies
uv sync --group test

# Run all integration tests
python run_integration_tests.py

# Run with verbose output
python run_integration_tests.py --verbose

# Run specific test categories
python run_integration_tests.py --category pages
python run_integration_tests.py --category search
python run_integration_tests.py --category attachments
```

### Individual Test Execution

```bash
# Run specific test files
uv run pytest app/test_integration.py -v

# Run with coverage
uv run pytest app/test_integration.py --cov=app --cov-report=html

# Run with detailed output
uv run pytest app/test_integration.py -v -s --tb=long
```

### Continuous Integration

For CI/CD pipelines, use the automated test runner:

```bash
# CI-friendly test execution
python run_integration_tests.py --ci --junit-xml=test-results.xml
```

## Test Categories

### 1. Authentication Tests

**Purpose:** Verify API token authentication and permissions

**Tests:**
- Valid credentials authentication
- Invalid credentials handling
- Permission verification
- Token expiration handling

**Example:**
```python
def test_authentication_valid_credentials():
    """Test successful authentication with valid credentials"""
    client = ConfluenceClient()
    assert client.test_connection() == True

def test_authentication_invalid_token():
    """Test authentication failure with invalid token"""
    client = ConfluenceClient(api_token="invalid-token")
    with pytest.raises(AuthenticationError):
        client.test_connection()
```

### 2. Page Management Tests

**Purpose:** Test CRUD operations on Confluence pages

**Tests:**
- Create page with various content types
- Read page content and metadata
- Update page content and properties
- Delete page and verify removal
- Handle page conflicts and versioning

**Example:**
```python
def test_create_page_success():
    """Test successful page creation"""
    page_data = {
        "title": "Integration Test Page",
        "content": "<p>Test content</p>",
        "space_key": TEST_SPACE_KEY
    }
    
    response = requests.post(f"{API_BASE_URL}/pages", json=page_data)
    assert response.status_code == 201
    
    page = response.json()
    assert page["title"] == page_data["title"]
    assert page["space_key"] == page_data["space_key"]
    
    # Cleanup
    cleanup_page(page["id"])
```

### 3. Search Tests

**Purpose:** Verify search functionality across different scenarios

**Tests:**
- Text search with various queries
- Space-specific search
- Content type filtering
- Pagination handling
- Search result accuracy

**Example:**
```python
def test_search_by_title():
    """Test searching pages by title"""
    # Create test page
    test_page = create_test_page("Unique Search Title")
    
    # Search for the page
    response = requests.get(f"{API_BASE_URL}/search", 
                          params={"query": "Unique Search Title"})
    
    assert response.status_code == 200
    results = response.json()
    assert results["total"] >= 1
    
    # Verify our page is in results
    page_ids = [page["id"] for page in results["results"]]
    assert test_page["id"] in page_ids
    
    # Cleanup
    cleanup_page(test_page["id"])
```

### 4. Vector Search Tests

**Purpose:** Test semantic search capabilities

**Tests:**
- Vector embedding generation
- Similarity search accuracy
- Index management
- Performance benchmarks

**Example:**
```python
def test_vector_search_similarity():
    """Test vector search finds semantically similar content"""
    # Create pages with related content
    page1 = create_test_page("Database Issues", 
                           "<p>Connection timeout errors</p>")
    page2 = create_test_page("Network Problems", 
                           "<p>Database connectivity failures</p>")
    
    # Index the pages
    requests.post(f"{API_BASE_URL}/bulk/index", 
                 json={"page_ids": [page1["id"], page2["id"]]})
    
    # Wait for indexing
    time.sleep(5)
    
    # Search for similar content
    search_data = {
        "query": "database connection problems",
        "limit": 5
    }
    
    response = requests.post(f"{API_BASE_URL}/search/vector", 
                           json=search_data)
    
    assert response.status_code == 200
    results = response.json()
    
    # Both pages should be found with good similarity scores
    assert len(results["results"]) >= 2
    for result in results["results"]:
        assert result["similarity_score"] > 0.5
    
    # Cleanup
    cleanup_page(page1["id"])
    cleanup_page(page2["id"])
```

### 5. Attachment Tests

**Purpose:** Test file upload and download functionality

**Tests:**
- Upload various file types
- Download attachments
- File size limits
- Metadata handling

**Example:**
```python
def test_upload_attachment():
    """Test file upload to a page"""
    # Create test page
    test_page = create_test_page("Attachment Test Page")
    
    # Create test file
    test_file_content = b"Test file content for integration testing"
    test_file = io.BytesIO(test_file_content)
    
    # Upload attachment
    files = {"file": ("test.txt", test_file, "text/plain")}
    response = requests.post(
        f"{API_BASE_URL}/pages/{test_page['id']}/attachments",
        files=files
    )
    
    assert response.status_code == 201
    attachment = response.json()
    assert attachment["title"] == "test.txt"
    assert attachment["media_type"] == "text/plain"
    
    # Verify attachment can be downloaded
    download_response = requests.get(
        f"{API_BASE_URL}/attachments/{attachment['id']}"
    )
    assert download_response.status_code == 200
    assert download_response.content == test_file_content
    
    # Cleanup
    cleanup_page(test_page["id"])
```

### 6. Error Handling Tests

**Purpose:** Verify proper error handling and recovery

**Tests:**
- Network connectivity issues
- API rate limiting
- Invalid input handling
- Confluence API errors

**Example:**
```python
def test_handle_page_not_found():
    """Test handling of non-existent page requests"""
    response = requests.get(f"{API_BASE_URL}/pages/999999999")
    
    assert response.status_code == 404
    error = response.json()
    assert "error" in error
    assert "not found" in error["error"].lower()

def test_handle_invalid_space():
    """Test handling of invalid space key"""
    page_data = {
        "title": "Test Page",
        "content": "<p>Content</p>",
        "space_key": "INVALIDSPACE"
    }
    
    response = requests.post(f"{API_BASE_URL}/pages", json=page_data)
    assert response.status_code == 400
    
    error = response.json()
    assert "error" in error
```

## Performance Tests

### Load Testing

Test the API under various load conditions:

```python
def test_concurrent_page_creation():
    """Test creating multiple pages concurrently"""
    import concurrent.futures
    
    def create_page(index):
        page_data = {
            "title": f"Load Test Page {index}",
            "content": f"<p>Content for page {index}</p>",
            "space_key": TEST_SPACE_KEY
        }
        response = requests.post(f"{API_BASE_URL}/pages", json=page_data)
        return response.status_code == 201
    
    # Create 10 pages concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(create_page, i) for i in range(10)]
        results = [future.result() for future in futures]
    
    # All pages should be created successfully
    assert all(results)
```

### Memory Usage Tests

Monitor memory usage during bulk operations:

```python
def test_bulk_indexing_memory_usage():
    """Test memory usage during bulk indexing"""
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss
    
    # Index a large number of pages
    page_ids = [create_test_page(f"Bulk Test {i}")["id"] 
                for i in range(100)]
    
    requests.post(f"{API_BASE_URL}/bulk/index", 
                 json={"page_ids": page_ids})
    
    # Wait for indexing to complete
    time.sleep(30)
    
    final_memory = process.memory_info().rss
    memory_increase = final_memory - initial_memory
    
    # Memory increase should be reasonable (less than 500MB)
    assert memory_increase < 500 * 1024 * 1024
    
    # Cleanup
    for page_id in page_ids:
        cleanup_page(page_id)
```

## Test Utilities

### Helper Functions

```python
def create_test_page(title, content="<p>Test content</p>"):
    """Create a test page and return its data"""
    page_data = {
        "title": title,
        "content": content,
        "space_key": TEST_SPACE_KEY
    }
    
    response = requests.post(f"{API_BASE_URL}/pages", json=page_data)
    assert response.status_code == 201
    return response.json()

def cleanup_page(page_id):
    """Delete a test page"""
    response = requests.delete(f"{API_BASE_URL}/pages/{page_id}")
    # Don't assert here as cleanup should be forgiving

def wait_for_job_completion(job_id, timeout=60):
    """Wait for a background job to complete"""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        response = requests.get(f"{API_BASE_URL}/jobs/{job_id}")
        if response.status_code == 200:
            job = response.json()
            if job["status"] in ["completed", "failed"]:
                return job
        
        time.sleep(2)
    
    raise TimeoutError(f"Job {job_id} did not complete within {timeout} seconds")
```

### Test Data Management

```python
class TestDataManager:
    """Manage test data lifecycle"""
    
    def __init__(self):
        self.created_pages = []
        self.created_attachments = []
    
    def create_page(self, title, content="<p>Test content</p>"):
        """Create and track a test page"""
        page = create_test_page(title, content)
        self.created_pages.append(page["id"])
        return page
    
    def cleanup_all(self):
        """Clean up all created test data"""
        for page_id in self.created_pages:
            cleanup_page(page_id)
        
        self.created_pages.clear()
        self.created_attachments.clear()

# Usage in tests
@pytest.fixture
def test_data():
    manager = TestDataManager()
    yield manager
    manager.cleanup_all()
```

## Troubleshooting

### Common Issues

1. **Authentication Failures**
   - Verify API token is valid and not expired
   - Check username format (should be email)
   - Ensure proper permissions in test space

2. **Test Environment Issues**
   - Verify Confluence instance is accessible
   - Check network connectivity
   - Validate SSL certificates

3. **Test Data Conflicts**
   - Ensure test space is clean before running tests
   - Use unique titles for test pages
   - Implement proper cleanup procedures

4. **Performance Issues**
   - Monitor Confluence API rate limits
   - Adjust test timing and concurrency
   - Check available memory for vector operations

### Debug Mode

Enable debug logging for detailed test output:

```bash
export TEST_LOG_LEVEL=DEBUG
python run_integration_tests.py --verbose
```

### Test Isolation

Ensure tests don't interfere with each other:

```python
@pytest.fixture(autouse=True)
def isolate_tests():
    """Ensure test isolation"""
    # Setup
    cleanup_test_space()
    
    yield
    
    # Teardown
    cleanup_test_space()
```

## Continuous Integration

### GitHub Actions Example

```yaml
name: Integration Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  integration-tests:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.12'
    
    - name: Install uv
      run: pip install uv
    
    - name: Install dependencies
      run: uv sync --group test
    
    - name: Run integration tests
      env:
        CONFLUENCE_URL: ${{ secrets.TEST_CONFLUENCE_URL }}
        CONFLUENCE_USERNAME: ${{ secrets.TEST_CONFLUENCE_USERNAME }}
        CONFLUENCE_API_TOKEN: ${{ secrets.TEST_CONFLUENCE_API_TOKEN }}
        TEST_SPACE_KEY: ${{ secrets.TEST_SPACE_KEY }}
      run: python run_integration_tests.py --ci --junit-xml=test-results.xml
    
    - name: Upload test results
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: test-results
        path: test-results.xml
```

## Reporting

### Test Reports

Generate comprehensive test reports:

```bash
# HTML coverage report
uv run pytest app/test_integration.py --cov=app --cov-report=html

# JUnit XML for CI
python run_integration_tests.py --junit-xml=integration-test-results.xml

# Performance report
python run_integration_tests.py --performance-report=performance.json
```

### Metrics Collection

Track key metrics during integration testing:

- API response times
- Success/failure rates
- Memory usage patterns
- Confluence API call counts
- Vector search accuracy scores

These metrics help identify performance regressions and optimize the tool's behavior.