"""Core Confluence API client."""

import re
from typing import Dict, List, Optional, Any
import requests
from requests.auth import HTTPBasicAuth
from requests.exceptions import RequestException, HTTPError, Timeout
from bs4 import BeautifulSoup
from .config import config
from .models import RunbookContent, RunbookMetadata
from .error_handler import (
    StructuredLogger,
    RetryConfig,
    with_retry,
    RateLimitError,
    ServiceUnavailableError
)

logger = StructuredLogger(__name__)


class ConfluenceAPIError(Exception):
    """Custom exception for Confluence API errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[Dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class ConfluenceClient:
    """Client for interacting with Confluence REST API."""
    
    def __init__(self):
        """Initialize Confluence client with environment-based authentication."""
        if not config.is_configured():
            raise ValueError("Confluence configuration is incomplete. Required: CONFLUENCE_URL, CONFLUENCE_USERNAME, CONFLUENCE_API_TOKEN")
        
        self.base_url = config.url.rstrip('/')
        self.auth = HTTPBasicAuth(config.username, config.api_token)
        self.timeout = config.timeout
        self.session = requests.Session()
        self.session.auth = self.auth
        self.session.headers.update({
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        
        # Retry configuration
        self.retry_config = RetryConfig(
            max_retries=3,
            base_delay=1.0,
            max_delay=60.0,
            exponential_base=2.0,
            jitter=True
        )
    
    @with_retry()
    def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None, 
                     data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make HTTP request to Confluence API with error handling and retries."""
        url = f"{self.base_url}/rest/api{endpoint}"
        
        try:
            logger.debug(
                f"Making {method} request to Confluence API",
                url=url,
                params=params is not None,
                data=data is not None
            )
            
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=data,
                timeout=self.timeout
            )
            
            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 60))
                logger.warning(
                    "Confluence API rate limit exceeded",
                    retry_after=retry_after,
                    url=url
                )
                raise RateLimitError(
                    "Confluence API rate limit exceeded",
                    retry_after=retry_after
                )
            
            # Handle authentication errors
            if response.status_code == 401:
                logger.error("Confluence authentication failed", url=url)
                raise ConfluenceAPIError(
                    "Authentication failed. Check your credentials.",
                    status_code=401
                )
            
            # Handle not found errors
            if response.status_code == 404:
                logger.warning("Confluence resource not found", url=url)
                raise ConfluenceAPIError(
                    "Resource not found.",
                    status_code=404
                )
            
            # Handle server errors that should be retried
            if response.status_code >= 500:
                logger.warning(
                    "Confluence server error, will retry",
                    status_code=response.status_code,
                    url=url
                )
                raise ServiceUnavailableError(
                    f"Confluence server error: {response.status_code}"
                )
            
            # Handle other HTTP errors
            response.raise_for_status()
            
            logger.debug(
                "Confluence API request successful",
                status_code=response.status_code,
                url=url
            )
            
            return response.json() if response.content else {}
            
        except Timeout as e:
            logger.error("Confluence API request timeout", url=url, timeout=self.timeout)
            raise ServiceUnavailableError(f"Request timeout: {str(e)}")
        except HTTPError as e:
            error_msg = f"HTTP error: {e.response.status_code}"
            try:
                error_data = e.response.json()
                if 'message' in error_data:
                    error_msg += f" - {error_data['message']}"
            except Exception:
                pass
            
            logger.error(
                "Confluence API HTTP error",
                status_code=e.response.status_code,
                url=url,
                error=error_msg
            )
            raise ConfluenceAPIError(error_msg, status_code=e.response.status_code)
        except RequestException as e:
            logger.error("Confluence API request failed", url=url, error=str(e))
            raise ServiceUnavailableError(f"Request failed: {str(e)}")
    
    def get_page_by_id(self, page_id: str) -> Dict[str, Any]:
        """
        Get a Confluence page by its ID.
        
        Args:
            page_id: The ID of the page to retrieve
            
        Returns:
            Dict containing page data including title, body, metadata
            
        Raises:
            ConfluenceAPIError: If page not found or API error occurs
        """
        if not page_id or not page_id.strip():
            raise ValueError("Page ID cannot be empty")
        
        endpoint = f"/content/{page_id}"
        params = {
            'expand': 'body.storage,version,space,ancestors'
        }
        
        try:
            return self._make_request('GET', endpoint, params=params)
        except ConfluenceAPIError as e:
            if e.status_code == 404:
                raise ConfluenceAPIError(f"Page with ID '{page_id}' not found", status_code=404)
            raise
    
    def get_page_by_title(self, space_key: str, title: str) -> Dict[str, Any]:
        """
        Get a Confluence page by its title within a specific space.
        
        Args:
            space_key: The key of the space containing the page
            title: The title of the page to retrieve
            
        Returns:
            Dict containing page data including title, body, metadata
            
        Raises:
            ConfluenceAPIError: If page not found or API error occurs
        """
        if not space_key or not space_key.strip():
            raise ValueError("Space key cannot be empty")
        if not title or not title.strip():
            raise ValueError("Page title cannot be empty")
        
        endpoint = "/content"
        params = {
            'spaceKey': space_key,
            'title': title,
            'expand': 'body.storage,version,space,ancestors'
        }
        
        try:
            response = self._make_request('GET', endpoint, params=params)
            results = response.get('results', [])
            
            if not results:
                raise ConfluenceAPIError(
                    f"Page with title '{title}' not found in space '{space_key}'",
                    status_code=404
                )
            
            return results[0]  # Return the first matching page
            
        except ConfluenceAPIError:
            raise
    
    def search_pages(self, query: str, space_key: Optional[str] = None, limit: int = 25) -> List[Dict[str, Any]]:
        """
        Search Confluence pages using text query.
        
        Args:
            query: Search query string
            space_key: Optional space key to limit search scope
            limit: Maximum number of results to return (default: 25)
            
        Returns:
            List of page dictionaries matching the search criteria
            
        Raises:
            ConfluenceAPIError: If search fails or API error occurs
        """
        if not query or not query.strip():
            raise ValueError("Search query cannot be empty")
        
        if limit <= 0 or limit > 100:
            raise ValueError("Limit must be between 1 and 100")
        
        # Build CQL query
        cql_parts = [f'text ~ "{query}"', 'type = page']
        
        if space_key:
            if not space_key.strip():
                raise ValueError("Space key cannot be empty when provided")
            cql_parts.append(f'space = "{space_key}"')
        
        cql = ' AND '.join(cql_parts)
        
        endpoint = "/content/search"
        params = {
            'cql': cql,
            'limit': limit,
            'expand': 'space,version'
        }
        
        try:
            response = self._make_request('GET', endpoint, params=params)
            return response.get('results', [])
            
        except ConfluenceAPIError:
            raise
    
    def _clean_html_content(self, html: str) -> str:
        """
        Clean and sanitize HTML content, extracting plain text.
        
        Args:
            html: Raw HTML content from Confluence
            
        Returns:
            Cleaned plain text content
        """
        if not html or not html.strip():
            return ""
        
        # Parse HTML with BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Remove navigation and metadata elements
        for nav in soup.find_all(['nav', 'header', 'footer']):
            nav.decompose()
        
        # Remove Confluence-specific elements that don't contain content
        for element in soup.find_all(attrs={'class': re.compile(r'confluence-metadata|page-metadata|breadcrumbs')}):
            element.decompose()
        
        # Convert common HTML elements to readable text
        # Replace headers with text and line breaks
        for header in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            header_text = header.get_text().strip()
            if header_text:
                header.replace_with(f"\n\n{header_text}\n")
        
        # Replace list items with bullet points
        for li in soup.find_all('li'):
            li_text = li.get_text().strip()
            if li_text:
                li.replace_with(f"\n• {li_text}")
        
        # Replace paragraphs with line breaks
        for p in soup.find_all('p'):
            p_text = p.get_text().strip()
            if p_text:
                p.replace_with(f"\n{p_text}\n")
        
        # Replace line breaks and divs
        for br in soup.find_all('br'):
            br.replace_with('\n')
        
        for div in soup.find_all('div'):
            div_text = div.get_text().strip()
            if div_text:
                div.replace_with(f"\n{div_text}\n")
        
        # Get the final text
        text = soup.get_text()
        
        # Clean up whitespace
        # Replace multiple newlines with double newlines
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        # Replace multiple spaces with single space
        text = re.sub(r' +', ' ', text)
        # Strip leading/trailing whitespace from each line
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)
        
        return text.strip()
    
    def _identify_runbook_sections(self, content: str) -> Dict[str, List[str]]:
        """
        Identify and extract runbook-specific sections from content.
        
        Args:
            content: Cleaned text content
            
        Returns:
            Dictionary with categorized sections (procedures, troubleshooting, prerequisites)
        """
        sections = {
            'procedures': [],
            'troubleshooting_steps': [],
            'prerequisites': [],
            'other_sections': []
        }
        
        if not content or not content.strip():
            return sections
        
        # Split content into lines for processing
        lines = content.split('\n')
        current_section = None
        current_content = []
        
        # Patterns to identify different section types
        procedure_patterns = [
            r'(?i)^(procedure|steps?|instructions?|how\s+to|process|workflow)',
            r'(?i)^(step\s+\d+|^\d+\.)',
            r'(?i)(implementation|execution|deployment)'
        ]
        
        troubleshooting_patterns = [
            r'(?i)^(troubleshoot|debug|problem|issue|error|fix|solution)',
            r'(?i)(common\s+issues?|known\s+problems?|error\s+handling)',
            r'(?i)(if.*then|when.*occurs|in\s+case\s+of)'
        ]
        
        prerequisite_patterns = [
            r'(?i)^(prerequisite|requirement|before|setup|preparation)',
            r'(?i)(you\s+need|must\s+have|ensure\s+that|make\s+sure)',
            r'(?i)(dependencies|requirements|assumptions)'
        ]
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if this line starts a new section
            section_identified = False
            
            # Check for procedure patterns
            for pattern in procedure_patterns:
                if re.search(pattern, line):
                    if current_section and current_content:
                        sections[current_section].append('\n'.join(current_content))
                    current_section = 'procedures'
                    current_content = [line]
                    section_identified = True
                    break
            
            if not section_identified:
                # Check for troubleshooting patterns
                for pattern in troubleshooting_patterns:
                    if re.search(pattern, line):
                        if current_section and current_content:
                            sections[current_section].append('\n'.join(current_content))
                        current_section = 'troubleshooting_steps'
                        current_content = [line]
                        section_identified = True
                        break
            
            if not section_identified:
                # Check for prerequisite patterns
                for pattern in prerequisite_patterns:
                    if re.search(pattern, line):
                        if current_section and current_content:
                            sections[current_section].append('\n'.join(current_content))
                        current_section = 'prerequisites'
                        current_content = [line]
                        section_identified = True
                        break
            
            if not section_identified:
                # If no specific section identified, add to current or other
                if current_section:
                    current_content.append(line)
                else:
                    # Start a new "other" section
                    if not current_section:
                        current_section = 'other_sections'
                        current_content = [line]
                    else:
                        current_content.append(line)
        
        # Add the last section
        if current_section and current_content:
            sections[current_section].append('\n'.join(current_content))
        
        # Clean up sections - remove empty ones and merge similar content
        for section_key in sections:
            sections[section_key] = [s.strip() for s in sections[section_key] if s.strip()]
        
        return sections
    
    def extract_runbook_content(self, page_content: Dict[str, Any]) -> RunbookContent:
        """
        Extract and structure runbook content from Confluence page data.
        
        Args:
            page_content: Raw page data from Confluence API
            
        Returns:
            RunbookContent model with structured data
            
        Raises:
            ValueError: If page content is invalid or missing required fields
        """
        if not page_content or not isinstance(page_content, dict):
            raise ValueError("Page content cannot be empty")
        
        # Extract basic metadata
        try:
            page_id = page_content.get('id', '')
            title = page_content.get('title', '')
            space_info = page_content.get('space', {})
            space_key = space_info.get('key', '')
            version_info = page_content.get('version', {})
            
            # Get author information
            author = None
            if 'by' in version_info:
                author = version_info['by'].get('displayName', '')
            
            # Get last modified date
            from datetime import datetime
            last_modified_str = version_info.get('when', '')
            if last_modified_str:
                # Parse ISO format datetime
                try:
                    last_modified = datetime.fromisoformat(last_modified_str.replace('Z', '+00:00'))
                except ValueError:
                    # Fallback to current time if parsing fails
                    last_modified = datetime.utcnow()
            else:
                last_modified = datetime.utcnow()
            
            # Construct page URL
            page_url = f"{self.base_url}/spaces/{space_key}/pages/{page_id}"
            
            # Extract HTML content
            body_content = page_content.get('body', {})
            storage_content = body_content.get('storage', {})
            html_content = storage_content.get('value', '')
            
            if not html_content:
                raise ValueError("Page has no content")
            
        except KeyError as e:
            raise ValueError(f"Missing required field in page content: {e}")
        
        # Clean HTML content
        cleaned_content = self._clean_html_content(html_content)
        
        if not cleaned_content:
            raise ValueError("Page content is empty after cleaning")
        
        # Identify runbook sections
        sections = self._identify_runbook_sections(cleaned_content)
        
        # Create metadata
        metadata = RunbookMetadata(
            title=title,
            author=author,
            last_modified=last_modified,
            space_key=space_key,
            page_id=page_id,
            page_url=page_url,
            tags=[]  # Tags could be extracted from labels if available
        )
        
        # Create structured sections dictionary
        structured_sections = {}
        for section_type, content_list in sections.items():
            if content_list:
                structured_sections[section_type] = '\n\n'.join(content_list)
        
        # Create and return RunbookContent
        return RunbookContent(
            metadata=metadata,
            procedures=sections.get('procedures', []),
            troubleshooting_steps=sections.get('troubleshooting_steps', []),
            prerequisites=sections.get('prerequisites', []),
            raw_content=cleaned_content,
            structured_sections=structured_sections
        )