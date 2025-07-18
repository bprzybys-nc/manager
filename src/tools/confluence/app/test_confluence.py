"""
Unit tests for ConfluenceClient.

This module contains comprehensive tests for the ConfluenceClient class
including authentication, API calls, error handling, and edge cases.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests
from requests.exceptions import HTTPError, Timeout, RequestException

from .confluence import ConfluenceClient, ConfluenceAPIError
from .config import ConfluenceConfig


class TestConfluenceClient:
    """Test cases for ConfluenceClient class."""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing."""
        with patch('app.confluence.config') as mock_config:
            mock_config.is_configured.return_value = True
            mock_config.url = "https://test.atlassian.net/wiki"
            mock_config.username = "test@example.com"
            mock_config.api_token = "test_token"
            mock_config.timeout = 30
            yield mock_config
    
    @pytest.fixture
    def client(self, mock_config):
        """Create ConfluenceClient instance for testing."""
        return ConfluenceClient()
    
    def test_client_initialization_success(self, mock_config):
        """Test successful client initialization."""
        client = ConfluenceClient()
        
        assert client.base_url == "https://test.atlassian.net/wiki"
        assert client.timeout == 30
        assert client.max_retries == 3
        assert client.retry_delay == 1.0
        assert client.session.auth.username == "test@example.com"
        assert client.session.auth.password == "test_token"
    
    def test_client_initialization_failure(self):
        """Test client initialization failure with incomplete config."""
        with patch('app.confluence.config') as mock_config:
            mock_config.is_configured.return_value = False
            
            with pytest.raises(ValueError) as exc_info:
                ConfluenceClient()
            
            assert "Confluence configuration is incomplete" in str(exc_info.value)
    
    def test_base_url_trailing_slash_removal(self, mock_config):
        """Test that trailing slash is removed from base URL."""
        mock_config.url = "https://test.atlassian.net/wiki/"
        client = ConfluenceClient()
        
        assert client.base_url == "https://test.atlassian.net/wiki"


class TestConfluenceClientMakeRequest:
    """Test cases for _make_request method."""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing."""
        with patch('app.confluence.config') as mock_config:
            mock_config.is_configured.return_value = True
            mock_config.url = "https://test.atlassian.net/wiki"
            mock_config.username = "test@example.com"
            mock_config.api_token = "test_token"
            mock_config.timeout = 30
            yield mock_config
    
    @pytest.fixture
    def client(self, mock_config):
        """Create ConfluenceClient instance for testing."""
        return ConfluenceClient()
    
    @patch('requests.Session.request')
    def test_make_request_success(self, mock_request, client):
        """Test successful API request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'{"result": "success"}'
        mock_response.json.return_value = {"result": "success"}
        mock_request.return_value = mock_response
        
        result = client._make_request('GET', '/test')
        
        assert result == {"result": "success"}
        mock_request.assert_called_once()
    
    @patch('requests.Session.request')
    def test_make_request_empty_response(self, mock_request, client):
        """Test API request with empty response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b''
        mock_request.return_value = mock_response
        
        result = client._make_request('GET', '/test')
        
        assert result == {}
    
    @patch('requests.Session.request')
    def test_make_request_401_error(self, mock_request, client):
        """Test authentication error handling."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_request.return_value = mock_response
        
        with pytest.raises(ConfluenceAPIError) as exc_info:
            client._make_request('GET', '/test')
        
        assert exc_info.value.status_code == 401
        assert "Authentication failed" in str(exc_info.value)
    
    @patch('requests.Session.request')
    def test_make_request_404_error(self, mock_request, client):
        """Test not found error handling."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_request.return_value = mock_response
        
        with pytest.raises(ConfluenceAPIError) as exc_info:
            client._make_request('GET', '/test')
        
        assert exc_info.value.status_code == 404
        assert "Resource not found" in str(exc_info.value)
    
    @patch('time.sleep')
    @patch('requests.Session.request')
    def test_make_request_rate_limiting_retry(self, mock_request, mock_sleep, client):
        """Test rate limiting with retry."""
        # First call returns 429, second call succeeds
        mock_response_429 = Mock()
        mock_response_429.status_code = 429
        mock_response_429.headers = {'Retry-After': '2'}
        
        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.content = b'{"result": "success"}'
        mock_response_200.json.return_value = {"result": "success"}
        
        mock_request.side_effect = [mock_response_429, mock_response_200]
        
        result = client._make_request('GET', '/test')
        
        assert result == {"result": "success"}
        assert mock_request.call_count == 2
        mock_sleep.assert_called_once_with(2)
    
    @patch('time.sleep')
    @patch('requests.Session.request')
    def test_make_request_rate_limiting_max_retries(self, mock_request, mock_sleep, client):
        """Test rate limiting exceeding max retries."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {'Retry-After': '1'}
        mock_response.raise_for_status.side_effect = HTTPError()
        mock_request.return_value = mock_response
        
        with pytest.raises(ConfluenceAPIError):
            client._make_request('GET', '/test')
        
        assert mock_request.call_count == 4  # Initial + 3 retries
    
    @patch('requests.Session.request')
    def test_make_request_timeout_error(self, mock_request, client):
        """Test timeout error handling."""
        mock_request.side_effect = Timeout("Request timeout")
        
        with pytest.raises(ConfluenceAPIError) as exc_info:
            client._make_request('GET', '/test')
        
        assert exc_info.value.status_code == 408
        assert "Request timeout" in str(exc_info.value)
    
    @patch('requests.Session.request')
    def test_make_request_http_error_with_json_response(self, mock_request, client):
        """Test HTTP error with JSON error response."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"message": "Bad request"}
        
        http_error = HTTPError()
        http_error.response = mock_response
        mock_request.side_effect = http_error
        
        with pytest.raises(ConfluenceAPIError) as exc_info:
            client._make_request('GET', '/test')
        
        assert exc_info.value.status_code == 400
        assert "Bad request" in str(exc_info.value)
    
    @patch('requests.Session.request')
    def test_make_request_http_error_without_json(self, mock_request, client):
        """Test HTTP error without JSON response."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.side_effect = ValueError("No JSON")
        
        http_error = HTTPError()
        http_error.response = mock_response
        mock_request.side_effect = http_error
        
        with pytest.raises(ConfluenceAPIError) as exc_info:
            client._make_request('GET', '/test')
        
        assert exc_info.value.status_code == 500
        assert "HTTP error: 500" in str(exc_info.value)
    
    @patch('requests.Session.request')
    def test_make_request_general_request_exception(self, mock_request, client):
        """Test general request exception handling."""
        mock_request.side_effect = RequestException("Connection error")
        
        with pytest.raises(ConfluenceAPIError) as exc_info:
            client._make_request('GET', '/test')
        
        assert "Request failed" in str(exc_info.value)
        assert "Connection error" in str(exc_info.value)


class TestConfluenceClientGetPageById:
    """Test cases for get_page_by_id method."""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing."""
        with patch('app.confluence.config') as mock_config:
            mock_config.is_configured.return_value = True
            mock_config.url = "https://test.atlassian.net/wiki"
            mock_config.username = "test@example.com"
            mock_config.api_token = "test_token"
            mock_config.timeout = 30
            yield mock_config
    
    @pytest.fixture
    def client(self, mock_config):
        """Create ConfluenceClient instance for testing."""
        return ConfluenceClient()
    
    def test_get_page_by_id_success(self, client):
        """Test successful page retrieval by ID."""
        expected_response = {
            "id": "12345",
            "title": "Test Page",
            "body": {"storage": {"value": "<p>Content</p>"}},
            "version": {"number": 1}
        }
        
        with patch.object(client, '_make_request', return_value=expected_response):
            result = client.get_page_by_id("12345")
            
            assert result == expected_response
            client._make_request.assert_called_once_with(
                'GET',
                '/content/12345',
                params={'expand': 'body.storage,version,space,ancestors'}
            )
    
    def test_get_page_by_id_empty_page_id(self, client):
        """Test get_page_by_id with empty page ID."""
        with pytest.raises(ValueError) as exc_info:
            client.get_page_by_id("")
        
        assert "Page ID cannot be empty" in str(exc_info.value)
        
        with pytest.raises(ValueError) as exc_info:
            client.get_page_by_id("   ")
        
        assert "Page ID cannot be empty" in str(exc_info.value)
    
    def test_get_page_by_id_not_found(self, client):
        """Test get_page_by_id with non-existent page."""
        with patch.object(client, '_make_request', side_effect=ConfluenceAPIError("Resource not found", status_code=404)):
            with pytest.raises(ConfluenceAPIError) as exc_info:
                client.get_page_by_id("nonexistent")
            
            assert exc_info.value.status_code == 404
            assert "Page with ID 'nonexistent' not found" in str(exc_info.value)
    
    def test_get_page_by_id_other_error(self, client):
        """Test get_page_by_id with other API error."""
        with patch.object(client, '_make_request', side_effect=ConfluenceAPIError("Server error", status_code=500)):
            with pytest.raises(ConfluenceAPIError) as exc_info:
                client.get_page_by_id("12345")
            
            assert exc_info.value.status_code == 500
            assert "Server error" in str(exc_info.value)


class TestConfluenceClientGetPageByTitle:
    """Test cases for get_page_by_title method."""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing."""
        with patch('app.confluence.config') as mock_config:
            mock_config.is_configured.return_value = True
            mock_config.url = "https://test.atlassian.net/wiki"
            mock_config.username = "test@example.com"
            mock_config.api_token = "test_token"
            mock_config.timeout = 30
            yield mock_config
    
    @pytest.fixture
    def client(self, mock_config):
        """Create ConfluenceClient instance for testing."""
        return ConfluenceClient()
    
    def test_get_page_by_title_success(self, client):
        """Test successful page retrieval by title."""
        expected_page = {
            "id": "12345",
            "title": "Test Page",
            "body": {"storage": {"value": "<p>Content</p>"}},
            "version": {"number": 1}
        }
        expected_response = {"results": [expected_page]}
        
        with patch.object(client, '_make_request', return_value=expected_response):
            result = client.get_page_by_title("TEST", "Test Page")
            
            assert result == expected_page
            client._make_request.assert_called_once_with(
                'GET',
                '/content',
                params={
                    'spaceKey': 'TEST',
                    'title': 'Test Page',
                    'expand': 'body.storage,version,space,ancestors'
                }
            )
    
    def test_get_page_by_title_empty_space_key(self, client):
        """Test get_page_by_title with empty space key."""
        with pytest.raises(ValueError) as exc_info:
            client.get_page_by_title("", "Test Page")
        
        assert "Space key cannot be empty" in str(exc_info.value)
        
        with pytest.raises(ValueError) as exc_info:
            client.get_page_by_title("   ", "Test Page")
        
        assert "Space key cannot be empty" in str(exc_info.value)
    
    def test_get_page_by_title_empty_title(self, client):
        """Test get_page_by_title with empty title."""
        with pytest.raises(ValueError) as exc_info:
            client.get_page_by_title("TEST", "")
        
        assert "Page title cannot be empty" in str(exc_info.value)
        
        with pytest.raises(ValueError) as exc_info:
            client.get_page_by_title("TEST", "   ")
        
        assert "Page title cannot be empty" in str(exc_info.value)
    
    def test_get_page_by_title_not_found(self, client):
        """Test get_page_by_title with non-existent page."""
        expected_response = {"results": []}
        
        with patch.object(client, '_make_request', return_value=expected_response):
            with pytest.raises(ConfluenceAPIError) as exc_info:
                client.get_page_by_title("TEST", "Nonexistent Page")
            
            assert exc_info.value.status_code == 404
            assert "Page with title 'Nonexistent Page' not found in space 'TEST'" in str(exc_info.value)
    
    def test_get_page_by_title_api_error(self, client):
        """Test get_page_by_title with API error."""
        with patch.object(client, '_make_request', side_effect=ConfluenceAPIError("Server error", status_code=500)):
            with pytest.raises(ConfluenceAPIError) as exc_info:
                client.get_page_by_title("TEST", "Test Page")
            
            assert exc_info.value.status_code == 500
            assert "Server error" in str(exc_info.value)


class TestConfluenceClientSearchPages:
    """Test cases for search_pages method."""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing."""
        with patch('app.confluence.config') as mock_config:
            mock_config.is_configured.return_value = True
            mock_config.url = "https://test.atlassian.net/wiki"
            mock_config.username = "test@example.com"
            mock_config.api_token = "test_token"
            mock_config.timeout = 30
            yield mock_config
    
    @pytest.fixture
    def client(self, mock_config):
        """Create ConfluenceClient instance for testing."""
        return ConfluenceClient()
    
    def test_search_pages_success_without_space(self, client):
        """Test successful page search without space filter."""
        expected_results = [
            {"id": "12345", "title": "Test Page 1"},
            {"id": "67890", "title": "Test Page 2"}
        ]
        expected_response = {"results": expected_results}
        
        with patch.object(client, '_make_request', return_value=expected_response):
            result = client.search_pages("test query")
            
            assert result == expected_results
            client._make_request.assert_called_once_with(
                'GET',
                '/content/search',
                params={
                    'cql': 'text ~ "test query" AND type = page',
                    'limit': 25,
                    'expand': 'space,version'
                }
            )
    
    def test_search_pages_success_with_space(self, client):
        """Test successful page search with space filter."""
        expected_results = [{"id": "12345", "title": "Test Page"}]
        expected_response = {"results": expected_results}
        
        with patch.object(client, '_make_request', return_value=expected_response):
            result = client.search_pages("test query", space_key="TEST", limit=10)
            
            assert result == expected_results
            client._make_request.assert_called_once_with(
                'GET',
                '/content/search',
                params={
                    'cql': 'text ~ "test query" AND type = page AND space = "TEST"',
                    'limit': 10,
                    'expand': 'space,version'
                }
            )
    
    def test_search_pages_empty_query(self, client):
        """Test search_pages with empty query."""
        with pytest.raises(ValueError) as exc_info:
            client.search_pages("")
        
        assert "Search query cannot be empty" in str(exc_info.value)
        
        with pytest.raises(ValueError) as exc_info:
            client.search_pages("   ")
        
        assert "Search query cannot be empty" in str(exc_info.value)
    
    def test_search_pages_invalid_limit(self, client):
        """Test search_pages with invalid limit values."""
        with pytest.raises(ValueError) as exc_info:
            client.search_pages("test", limit=0)
        
        assert "Limit must be between 1 and 100" in str(exc_info.value)
        
        with pytest.raises(ValueError) as exc_info:
            client.search_pages("test", limit=101)
        
        assert "Limit must be between 1 and 100" in str(exc_info.value)
    
    def test_search_pages_empty_space_key(self, client):
        """Test search_pages with empty space key."""
        with pytest.raises(ValueError) as exc_info:
            client.search_pages("test", space_key="")
        
        assert "Space key cannot be empty when provided" in str(exc_info.value)
        
        with pytest.raises(ValueError) as exc_info:
            client.search_pages("test", space_key="   ")
        
        assert "Space key cannot be empty when provided" in str(exc_info.value)
    
    def test_search_pages_api_error(self, client):
        """Test search_pages with API error."""
        with patch.object(client, '_make_request', side_effect=ConfluenceAPIError("Server error", status_code=500)):
            with pytest.raises(ConfluenceAPIError) as exc_info:
                client.search_pages("test query")
            
            assert exc_info.value.status_code == 500
            assert "Server error" in str(exc_info.value)
    
    def test_search_pages_empty_results(self, client):
        """Test search_pages with empty results."""
        expected_response = {"results": []}
        
        with patch.object(client, '_make_request', return_value=expected_response):
            result = client.search_pages("nonexistent query")
            
            assert result == []


class TestConfluenceAPIError:
    """Test cases for ConfluenceAPIError exception."""
    
    def test_confluence_api_error_basic(self):
        """Test basic ConfluenceAPIError creation."""
        error = ConfluenceAPIError("Test error")
        
        assert str(error) == "Test error"
        assert error.status_code is None
        assert error.response_data is None
    
    def test_confluence_api_error_with_status_code(self):
        """Test ConfluenceAPIError with status code."""
        error = ConfluenceAPIError("Test error", status_code=404)
        
        assert str(error) == "Test error"
        assert error.status_code == 404
        assert error.response_data is None
    
    def test_confluence_api_error_with_response_data(self):
        """Test ConfluenceAPIError with response data."""
        response_data = {"error": "Not found", "details": "Page does not exist"}
        error = ConfluenceAPIError("Test error", status_code=404, response_data=response_data)
        
        assert str(error) == "Test error"
        assert error.status_code == 404
        assert error.response_data == response_data


class TestConfluenceClientHTMLParsing:
    """Test cases for HTML content parsing and extraction methods."""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing."""
        with patch('app.confluence.config') as mock_config:
            mock_config.is_configured.return_value = True
            mock_config.url = "https://test.atlassian.net/wiki"
            mock_config.username = "test@example.com"
            mock_config.api_token = "test_token"
            mock_config.timeout = 30
            yield mock_config
    
    @pytest.fixture
    def client(self, mock_config):
        """Create ConfluenceClient instance for testing."""
        return ConfluenceClient()
    
    def test_clean_html_content_basic(self, client):
        """Test basic HTML cleaning functionality."""
        html = "<p>This is a test paragraph.</p><br><div>Another section</div>"
        result = client._clean_html_content(html)
        
        assert "This is a test paragraph." in result
        assert "Another section" in result
        assert "<p>" not in result
        assert "<div>" not in result
    
    def test_clean_html_content_empty_input(self, client):
        """Test HTML cleaning with empty input."""
        assert client._clean_html_content("") == ""
        assert client._clean_html_content("   ") == ""
        assert client._clean_html_content(None) == ""
    
    def test_clean_html_content_remove_scripts_and_styles(self, client):
        """Test removal of script and style elements."""
        html = """
        <html>
            <head>
                <style>body { color: red; }</style>
                <script>alert('test');</script>
            </head>
            <body>
                <p>Content to keep</p>
                <script>console.log('remove me');</script>
            </body>
        </html>
        """
        result = client._clean_html_content(html)
        
        assert "Content to keep" in result
        assert "alert('test')" not in result
        assert "console.log" not in result
        assert "color: red" not in result
    
    def test_clean_html_content_remove_navigation(self, client):
        """Test removal of navigation elements."""
        html = """
        <nav>Navigation menu</nav>
        <header>Page header</header>
        <footer>Page footer</footer>
        <p>Main content</p>
        """
        result = client._clean_html_content(html)
        
        assert "Main content" in result
        assert "Navigation menu" not in result
        assert "Page header" not in result
        assert "Page footer" not in result
    
    def test_clean_html_content_headers_conversion(self, client):
        """Test conversion of header elements."""
        html = """
        <h1>Main Title</h1>
        <h2>Subtitle</h2>
        <h3>Section Header</h3>
        <p>Regular paragraph</p>
        """
        result = client._clean_html_content(html)
        
        assert "Main Title" in result
        assert "Subtitle" in result
        assert "Section Header" in result
        assert "Regular paragraph" in result
        # Headers should have line breaks around them
        assert "\n\nMain Title\n" in result or "Main Title\n" in result
    
    def test_clean_html_content_list_conversion(self, client):
        """Test conversion of list elements."""
        html = """
        <ul>
            <li>First item</li>
            <li>Second item</li>
        </ul>
        <ol>
            <li>Numbered item</li>
        </ol>
        """
        result = client._clean_html_content(html)
        
        assert "• First item" in result
        assert "• Second item" in result
        assert "• Numbered item" in result
    
    def test_clean_html_content_confluence_metadata_removal(self, client):
        """Test removal of Confluence-specific metadata elements."""
        html = """
        <div class="confluence-metadata">Metadata content</div>
        <div class="page-metadata">Page info</div>
        <div class="breadcrumbs">Home > Page</div>
        <p>Actual content</p>
        """
        result = client._clean_html_content(html)
        
        assert "Actual content" in result
        assert "Metadata content" not in result
        assert "Page info" not in result
        assert "Home > Page" not in result
    
    def test_clean_html_content_whitespace_normalization(self, client):
        """Test whitespace normalization."""
        html = """
        <p>Line   with    multiple     spaces</p>
        
        
        
        <p>Another paragraph</p>
        """
        result = client._clean_html_content(html)
        
        # Multiple spaces should be reduced to single spaces
        assert "Line with multiple spaces" in result
        # Multiple newlines should be reduced to double newlines
        lines = result.split('\n')
        consecutive_empty = 0
        max_consecutive_empty = 0
        for line in lines:
            if line.strip() == '':
                consecutive_empty += 1
                max_consecutive_empty = max(max_consecutive_empty, consecutive_empty)
            else:
                consecutive_empty = 0
        assert max_consecutive_empty <= 2
    
    def test_identify_runbook_sections_empty_content(self, client):
        """Test section identification with empty content."""
        result = client._identify_runbook_sections("")
        
        expected_keys = ['procedures', 'troubleshooting_steps', 'prerequisites', 'other_sections']
        assert all(key in result for key in expected_keys)
        assert all(len(result[key]) == 0 for key in expected_keys)
    
    def test_identify_runbook_sections_procedures(self, client):
        """Test identification of procedure sections."""
        content = """
        Procedure for Database Backup
        
        Step 1: Connect to the database server
        Step 2: Run the backup command
        Step 3: Verify backup completion
        
        Implementation Notes:
        - Use secure connection
        - Monitor disk space
        """
        result = client._identify_runbook_sections(content)
        
        assert len(result['procedures']) > 0
        procedures_text = ' '.join(result['procedures'])
        assert "Procedure for Database Backup" in procedures_text
        assert "Step 1" in procedures_text
        assert "Implementation" in procedures_text
    
    def test_identify_runbook_sections_troubleshooting(self, client):
        """Test identification of troubleshooting sections."""
        content = """
        Troubleshooting Database Connection Issues
        
        Problem: Cannot connect to database
        Solution: Check network connectivity
        
        Common Issues:
        - Port blocked by firewall
        - Invalid credentials
        
        If connection fails, then restart the service
        """
        result = client._identify_runbook_sections(content)
        
        assert len(result['troubleshooting_steps']) > 0
        troubleshooting_text = ' '.join(result['troubleshooting_steps'])
        assert "Troubleshooting" in troubleshooting_text
        assert "Problem" in troubleshooting_text
        assert "Common Issues" in troubleshooting_text
        assert "If connection fails" in troubleshooting_text
    
    def test_identify_runbook_sections_prerequisites(self, client):
        """Test identification of prerequisite sections."""
        content = """
        Prerequisites for Installation
        
        You need the following:
        - Admin access to server
        - Database credentials
        
        Requirements:
        - Python 3.8 or higher
        - 4GB RAM minimum
        
        Before starting, ensure that all dependencies are installed
        """
        result = client._identify_runbook_sections(content)
        
        assert len(result['prerequisites']) > 0
        prerequisites_text = ' '.join(result['prerequisites'])
        assert "Prerequisites" in prerequisites_text
        assert "You need" in prerequisites_text
        assert "Requirements" in prerequisites_text
        assert "Before starting" in prerequisites_text
    
    def test_identify_runbook_sections_mixed_content(self, client):
        """Test identification of mixed section types."""
        content = """
        Database Maintenance Runbook
        
        Prerequisites:
        - Admin access required
        - Backup completed
        
        Procedure:
        1. Stop the database service
        2. Run maintenance scripts
        3. Restart the service
        
        Troubleshooting:
        If the service fails to start, check the logs
        Common error: Permission denied
        """
        result = client._identify_runbook_sections(content)
        
        assert len(result['prerequisites']) > 0
        assert len(result['procedures']) > 0
        assert len(result['troubleshooting_steps']) > 0
        
        # Check content distribution
        prereq_text = ' '.join(result['prerequisites'])
        proc_text = ' '.join(result['procedures'])
        trouble_text = ' '.join(result['troubleshooting_steps'])
        
        assert "Admin access required" in prereq_text
        assert "Stop the database service" in proc_text
        assert "service fails to start" in trouble_text
    
    def test_extract_runbook_content_success(self, client):
        """Test successful runbook content extraction."""
        page_content = {
            'id': '12345',
            'title': 'Database Backup Runbook',
            'space': {'key': 'IT'},
            'version': {
                'when': '2023-01-01T10:00:00.000Z',
                'by': {'displayName': 'John Doe'}
            },
            'body': {
                'storage': {
                    'value': '''
                    <h1>Database Backup Procedure</h1>
                    <h2>Prerequisites</h2>
                    <p>You need admin access to the database server</p>
                    <h2>Steps</h2>
                    <ol>
                        <li>Connect to database</li>
                        <li>Run backup command</li>
                        <li>Verify completion</li>
                    </ol>
                    <h2>Troubleshooting</h2>
                    <p>If backup fails, check disk space</p>
                    '''
                }
            }
        }
        
        result = client.extract_runbook_content(page_content)
        
        # Check metadata
        assert result.metadata.title == 'Database Backup Runbook'
        assert result.metadata.author == 'John Doe'
        assert result.metadata.space_key == 'IT'
        assert result.metadata.page_id == '12345'
        assert 'test.atlassian.net' in str(result.metadata.page_url)
        
        # Check content extraction
        assert result.raw_content
        assert "Database Backup Procedure" in result.raw_content
        assert "admin access" in result.raw_content
        
        # Check structured sections
        assert len(result.procedures) > 0 or len(result.troubleshooting_steps) > 0 or len(result.prerequisites) > 0
    
    def test_extract_runbook_content_empty_page_content(self, client):
        """Test runbook extraction with empty page content."""
        with pytest.raises(ValueError) as exc_info:
            client.extract_runbook_content(None)
        
        assert "Page content cannot be empty" in str(exc_info.value)
        
        with pytest.raises(ValueError) as exc_info:
            client.extract_runbook_content({})
        
        assert "Page content cannot be empty" in str(exc_info.value)
    
    def test_extract_runbook_content_missing_required_fields(self, client):
        """Test runbook extraction with missing required fields."""
        incomplete_content = {
            'id': '12345',
            # Missing title, space, version, body
        }
        
        with pytest.raises(ValueError) as exc_info:
            client.extract_runbook_content(incomplete_content)
        
        # The method will fail at HTML content validation since body is missing
        assert "Page has no content" in str(exc_info.value)
    
    def test_extract_runbook_content_no_html_content(self, client):
        """Test runbook extraction with no HTML content."""
        page_content = {
            'id': '12345',
            'title': 'Test Page',
            'space': {'key': 'TEST'},
            'version': {
                'when': '2023-01-01T10:00:00.000Z',
                'by': {'displayName': 'Test User'}
            },
            'body': {
                'storage': {
                    'value': ''  # Empty content
                }
            }
        }
        
        with pytest.raises(ValueError) as exc_info:
            client.extract_runbook_content(page_content)
        
        assert "Page has no content" in str(exc_info.value)
    
    def test_extract_runbook_content_empty_after_cleaning(self, client):
        """Test runbook extraction with content that becomes empty after cleaning."""
        page_content = {
            'id': '12345',
            'title': 'Test Page',
            'space': {'key': 'TEST'},
            'version': {
                'when': '2023-01-01T10:00:00.000Z',
                'by': {'displayName': 'Test User'}
            },
            'body': {
                'storage': {
                    'value': '<script>alert("test");</script><style>body{}</style>'  # Only removable content
                }
            }
        }
        
        with pytest.raises(ValueError) as exc_info:
            client.extract_runbook_content(page_content)
        
        assert "Page content is empty after cleaning" in str(exc_info.value)
    
    def test_extract_runbook_content_datetime_parsing(self, client):
        """Test runbook extraction with various datetime formats."""
        page_content = {
            'id': '12345',
            'title': 'Test Page',
            'space': {'key': 'TEST'},
            'version': {
                'when': '2023-01-01T10:00:00Z',  # Different format
                'by': {'displayName': 'Test User'}
            },
            'body': {
                'storage': {
                    'value': '<p>Test content</p>'
                }
            }
        }
        
        result = client.extract_runbook_content(page_content)
        
        # Should not raise an error and should have a valid datetime
        assert result.metadata.last_modified is not None
        assert result.metadata.last_modified.year == 2023
    
    def test_extract_runbook_content_invalid_datetime(self, client):
        """Test runbook extraction with invalid datetime format."""
        page_content = {
            'id': '12345',
            'title': 'Test Page',
            'space': {'key': 'TEST'},
            'version': {
                'when': 'invalid-date-format',
                'by': {'displayName': 'Test User'}
            },
            'body': {
                'storage': {
                    'value': '<p>Test content</p>'
                }
            }
        }
        
        result = client.extract_runbook_content(page_content)
        
        # Should fallback to current time without raising an error
        assert result.metadata.last_modified is not None
    
    def test_extract_runbook_content_missing_author(self, client):
        """Test runbook extraction with missing author information."""
        page_content = {
            'id': '12345',
            'title': 'Test Page',
            'space': {'key': 'TEST'},
            'version': {
                'when': '2023-01-01T10:00:00.000Z'
                # Missing 'by' field
            },
            'body': {
                'storage': {
                    'value': '<p>Test content</p>'
                }
            }
        }
        
        result = client.extract_runbook_content(page_content)
        
        # Should handle missing author gracefully
        assert result.metadata.author is None
        assert result.metadata.title == 'Test Page'


if __name__ == "__main__":
    pytest.main([__file__])