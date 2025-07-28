"""
Tests for RunbookDiscoveryService

This module contains comprehensive tests for the Confluence Runbook Discovery
and ChromaDB Population System.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from usecases.db_runbook_finder.runbook_discovery_service import RunbookDiscoveryService
from tools.confluence.app.models import (
    RunbookContent, 
    RunbookMetadata, 
    PopulationResult
)


class TestRunbookDiscoveryService:
    """Test suite for RunbookDiscoveryService."""

    def setup_method(self):
        """Setup test fixtures."""
        self.service = RunbookDiscoveryService(collection_name="test-runbooks")
        
        # Mock dependencies
        self.mock_confluence = Mock()
        self.mock_vector_store = Mock()
        
        self.service.confluence_client = self.mock_confluence
        self.service.vector_store = self.mock_vector_store

    def test_init_default_collection(self):
        """Test service initialization with default collection name."""
        service = RunbookDiscoveryService()
        assert service.collection_name == "mcdb-runbooks"
        assert len(service.root_urls) == 2
        assert "Helvetia" in service.root_urls[0]
        assert "Neste" in service.root_urls[1]

    def test_init_custom_collection(self):
        """Test service initialization with custom collection name."""
        service = RunbookDiscoveryService(collection_name="custom-runbooks")
        assert service.collection_name == "custom-runbooks"

    def test_extract_page_id_from_url_valid(self):
        """Test page ID extraction from valid Confluence URLs."""
        test_cases = [
            ("https://nordcloud.atlassian.net/wiki/spaces/MCDBA/pages/4012343437/Helvetia+Runbooks", "4012343437"),
            ("https://company.atlassian.net/wiki/spaces/TEST/pages/123456/Test+Page", "123456"),
            ("https://example.com/wiki/spaces/SPACE/pages/999999999/Some+Title", "999999999")
        ]
        
        for url, expected_id in test_cases:
            result = self.service.extract_page_id_from_url(url)
            assert result == expected_id

    def test_extract_page_id_from_url_invalid(self):
        """Test page ID extraction from invalid URLs."""
        invalid_urls = [
            "",
            "   ",
            "https://example.com/invalid/url",
            "https://example.com/wiki/spaces/TEST/pages/invalid/Title",
            "not-a-url"
        ]
        
        for url in invalid_urls:
            with pytest.raises(ValueError):
                self.service.extract_page_id_from_url(url)

    def test_get_client_name_from_url(self):
        """Test client name extraction from URLs."""
        test_cases = [
            ("https://nordcloud.atlassian.net/wiki/spaces/MCDBA/pages/4012343437/Helvetia+Runbooks", "helvetia"),
            ("https://nordcloud.atlassian.net/wiki/spaces/MCDBA/pages/4322296000/Neste+Runbooks", "neste"),
            ("https://example.com/wiki/spaces/TEST/pages/123456/Random+Page", "unknown")
        ]
        
        for url, expected_client in test_cases:
            result = self.service.get_client_name_from_url(url)
            assert result == expected_client

    def test_is_likely_runbook_include_patterns(self):
        """Test runbook detection with include patterns."""
        include_test_pages = [
            {"title": "Database Runbook"},
            {"title": "Installation Instructions"},
            {"title": "Troubleshooting Procedure"},
            {"title": "User Access Guide"},
            {"title": "Health Check Checklist"},
            {"title": "Monitoring Setup"},
            {"title": "Backup Restore Process"},
            {"title": "Security Patching Guide"},
            {"title": "System Upgrade Instructions"},
            {"title": "User Onboarding Process"},
            {"title": "DB2 Hotel Configuration"}
        ]
        
        for page in include_test_pages:
            assert self.service.is_likely_runbook(page), f"Should include: {page['title']}"

    def test_is_likely_runbook_exclude_patterns(self):
        """Test runbook detection with exclude patterns."""
        exclude_test_pages = [
            {"title": "All Runbooks"},  # plural
            {"title": "Known Issues List"},
            {"title": "General Instructions Page"}
        ]
        
        for page in exclude_test_pages:
            assert not self.service.is_likely_runbook(page), f"Should exclude: {page['title']}"

    def test_is_likely_runbook_no_match(self):
        """Test runbook detection with pages that don't match any pattern."""
        no_match_pages = [
            {"title": "Random Page"},
            {"title": "Meeting Notes"},
            {"title": "Project Status"}
        ]
        
        for page in no_match_pages:
            assert not self.service.is_likely_runbook(page), f"Should not match: {page['title']}"

    def test_is_likely_runbook_invalid_input(self):
        """Test runbook detection with invalid input."""
        invalid_inputs = [None, {}, {"no_title": "value"}, "not_a_dict", []]
        
        for invalid_input in invalid_inputs:
            assert not self.service.is_likely_runbook(invalid_input)

    @patch('usecases.db_runbook_finder.runbook_discovery_service.logger')
    def test_discover_runbooks_from_root_success(self, mock_logger):
        """Test successful runbook discovery from root URL."""
        # Setup mocks
        root_url = "https://nordcloud.atlassian.net/wiki/spaces/MCDBA/pages/4012343437/Helvetia+Runbooks"
        
        # Mock root page
        root_page = {"id": "4012343437", "title": "Helvetia Runbooks"}
        self.mock_confluence.get_page_by_id.return_value = root_page
        
        # Mock child pages
        runbook_child = {"id": "123456", "title": "Oracle DB Runbook"}
        non_runbook_child = {"id": "789012", "title": "Random Page"}
        self.mock_confluence.get_page_children.return_value = [runbook_child, non_runbook_child]
        
        # Mock runbook content extraction
        mock_metadata = RunbookMetadata(
            title="Oracle DB Runbook",
            last_modified=datetime.utcnow(),
            space_key="MCDBA",
            page_id="123456",
            page_url="https://example.com/page/123456",
            tags=["database"]
        )
        mock_runbook = RunbookContent(
            metadata=mock_metadata,
            procedures=["Step 1", "Step 2"],
            troubleshooting_steps=["Check logs"],
            prerequisites=["Access required"],
            raw_content="Mock content"
        )
        self.mock_confluence.extract_runbook_content.return_value = mock_runbook
        
        # Execute
        result = self.service.discover_runbooks_from_root(root_url)
        
        # Verify
        assert len(result) == 1
        assert result[0].metadata.title == "Oracle DB Runbook"
        assert "helvetia" in result[0].metadata.tags
        assert "runbook" in result[0].metadata.tags
        
        # Verify API calls
        self.mock_confluence.get_page_by_id.assert_called()
        self.mock_confluence.get_page_children.assert_called_with("4012343437")
        self.mock_confluence.extract_runbook_content.assert_called_once()

    def test_discover_runbooks_from_root_invalid_url(self):
        """Test runbook discovery with invalid root URL."""
        invalid_url = "invalid-url"
        
        result = self.service.discover_runbooks_from_root(invalid_url)
        
        assert result == []

    def test_populate_chromadb_success(self):
        """Test successful ChromaDB population."""
        # Setup test runbooks
        metadata1 = RunbookMetadata(
            title="Test Runbook 1",
            last_modified=datetime.utcnow(),
            space_key="TEST",
            page_id="111",
            page_url="https://example.com/111"
        )
        runbook1 = RunbookContent(
            metadata=metadata1,
            raw_content="Content 1"
        )
        
        metadata2 = RunbookMetadata(
            title="Test Runbook 2", 
            last_modified=datetime.utcnow(),
            space_key="TEST",
            page_id="222",
            page_url="https://example.com/222"
        )
        runbook2 = RunbookContent(
            metadata=metadata2,
            raw_content="Content 2"
        )
        
        runbooks = [runbook1, runbook2]
        
        # Mock vector store responses
        self.mock_vector_store.add_runbook.side_effect = ["runbook_id_1", "runbook_id_2"]
        
        # Execute
        result = self.service.populate_chromadb(runbooks)
        
        # Verify
        assert result.total_runbooks == 2
        assert result.successful_populations == 2
        assert result.failed_populations == 0
        assert result.collection_name == "test-runbooks"
        assert len(result.populated_runbook_ids) == 2
        assert result.deduplication_stats["unique_runbooks"] == 2
        assert result.deduplication_stats["duplicates_found"] == 0

    def test_populate_chromadb_with_duplicates(self):
        """Test ChromaDB population with duplicate runbooks."""
        # Create runbooks with same page_id (duplicates)
        metadata = RunbookMetadata(
            title="Duplicate Runbook",
            last_modified=datetime.utcnow(),
            space_key="TEST", 
            page_id="same_id",
            page_url="https://example.com/same"
        )
        
        runbook1 = RunbookContent(metadata=metadata, raw_content="Content 1")
        runbook2 = RunbookContent(metadata=metadata, raw_content="Content 2")  # Same page_id
        
        runbooks = [runbook1, runbook2]
        
        # Mock vector store response
        self.mock_vector_store.add_runbook.return_value = "runbook_id_1"
        
        # Execute
        result = self.service.populate_chromadb(runbooks)
        
        # Verify deduplication
        assert result.total_runbooks == 2
        assert result.successful_populations == 1  # Only one unique processed
        assert result.deduplication_stats["duplicates_found"] == 1
        assert result.deduplication_stats["unique_runbooks"] == 1
        
        # Vector store should be called only once
        self.mock_vector_store.add_runbook.assert_called_once()

    def test_populate_chromadb_with_errors(self):
        """Test ChromaDB population with some failures."""
        # Setup test runbooks
        metadata1 = RunbookMetadata(
            title="Success Runbook",
            last_modified=datetime.utcnow(),
            space_key="TEST",
            page_id="success",
            page_url="https://example.com/success"
        )
        success_runbook = RunbookContent(metadata=metadata1, raw_content="Success content")
        
        metadata2 = RunbookMetadata(
            title="Failure Runbook",
            last_modified=datetime.utcnow(),
            space_key="TEST",
            page_id="failure",
            page_url="https://example.com/failure"
        )
        failure_runbook = RunbookContent(metadata=metadata2, raw_content="Failure content")
        
        runbooks = [success_runbook, failure_runbook]
        
        # Mock vector store responses - second call fails
        self.mock_vector_store.add_runbook.side_effect = ["success_id", Exception("Vector store error")]
        
        # Execute
        result = self.service.populate_chromadb(runbooks)
        
        # Verify
        assert result.total_runbooks == 2
        assert result.successful_populations == 1
        assert result.failed_populations == 1
        assert len(result.populated_runbook_ids) == 1
        assert len(result.errors) == 1
        assert "Vector store error" in result.errors[0]

    @patch('usecases.db_runbook_finder.runbook_discovery_service.logger')
    def test_discover_and_populate_dry_run(self, mock_logger):
        """Test discover_and_populate in dry run mode."""
        # Mock discovery method
        mock_runbooks = [Mock()]
        with patch.object(self.service, 'discover_runbooks_from_root', return_value=mock_runbooks):
            result = self.service.discover_and_populate(dry_run=True)
        
        # Verify dry run behavior
        assert result.total_discovered == 2  # 2 root URLs
        assert len(result.discovered_runbooks) == 2  # mock_runbooks for each URL
        
        # Vector store should not be called in dry run
        self.mock_vector_store.add_runbook.assert_not_called()

    @patch('usecases.db_runbook_finder.runbook_discovery_service.logger')
    def test_discover_and_populate_full_run(self, mock_logger):
        """Test discover_and_populate with actual population."""
        # Mock discovery method
        mock_runbooks = [Mock()]
        mock_population_result = PopulationResult(
            total_runbooks=2,
            successful_populations=2,
            failed_populations=0,
            processing_time=1.0,
            collection_name="test-runbooks",
            populated_runbook_ids=["id1", "id2"],
            errors=[],
            deduplication_stats={"duplicates_found": 0, "unique_runbooks": 2}
        )
        
        with patch.object(self.service, 'discover_runbooks_from_root', return_value=mock_runbooks):
            with patch.object(self.service, 'populate_chromadb', return_value=mock_population_result):
                result = self.service.discover_and_populate(dry_run=False)
        
        # Verify full run behavior
        assert result.total_discovered == 2  # 2 root URLs
        assert len(result.discovered_runbooks) == 2
        
        # Population should have been called
        self.service.populate_chromadb.assert_called_once()

    def test_discover_and_populate_discovery_error(self):
        """Test discover_and_populate with discovery errors."""
        # Mock discovery method to raise exception for first URL
        def mock_discovery_side_effect(url):
            if "Helvetia" in url:
                raise Exception("Discovery failed")
            return []
        
        with patch.object(self.service, 'discover_runbooks_from_root', side_effect=mock_discovery_side_effect):
            result = self.service.discover_and_populate(dry_run=True)
        
        # Verify error handling
        assert result.failed_discoveries == 1
        assert len(result.errors) >= 1
        assert any("Discovery failed" in error for error in result.errors)
        assert result.client_stats["helvetia"] == 0  # Failed discovery
        assert result.client_stats["neste"] == 0     # Empty result


class TestRunbookDiscoveryServiceIntegration:
    """Integration tests that require real components (if available)."""
    
    def test_service_initialization_with_real_components(self):
        """Test service can be initialized with real Confluence and VectorStore."""
        try:
            service = RunbookDiscoveryService()
            assert service.confluence_client is not None
            assert service.vector_store is not None
            assert service.collection_name == "mcdb-runbooks"
        except Exception as e:
            pytest.skip(f"Real components not available: {e}")

    def test_url_parsing_real_examples(self):
        """Test URL parsing with real Confluence URL examples."""
        service = RunbookDiscoveryService()
        
        real_urls = [
            "https://nordcloud.atlassian.net/wiki/spaces/MCDBA/pages/4012343437/Helvetia+Runbooks",
            "https://nordcloud.atlassian.net/wiki/spaces/MCDBA/pages/4322296000/Neste+Runbooks"
        ]
        
        expected_ids = ["4012343437", "4322296000"]
        
        for url, expected_id in zip(real_urls, expected_ids):
            page_id = service.extract_page_id_from_url(url)
            assert page_id == expected_id


# Additional test fixtures for complex scenarios
@pytest.fixture
def sample_runbook_content():
    """Fixture providing sample RunbookContent for testing."""
    metadata = RunbookMetadata(
        title="Sample Database Runbook",
        author="Test Author",
        last_modified=datetime.utcnow(),
        space_key="TEST",
        page_id="sample123",
        page_url="https://example.com/sample123",
        tags=["database", "runbook", "sample"]
    )
    
    return RunbookContent(
        metadata=metadata,
        procedures=["Connect to database", "Run health check", "Verify results"],
        troubleshooting_steps=["Check logs", "Restart service", "Contact admin"],
        prerequisites=["Database access", "VPN connection"],
        raw_content="This is a sample runbook for database operations...",
        structured_sections={
            "overview": "Database runbook overview",
            "steps": "Detailed procedural steps"
        }
    )


@pytest.fixture
def mock_confluence_api_responses():
    """Fixture providing mock Confluence API responses."""
    return {
        "root_page": {
            "id": "4012343437",
            "title": "Helvetia Runbooks",
            "space": {"key": "MCDBA"},
            "version": {"number": 1}
        },
        "child_pages": [
            {"id": "child1", "title": "Oracle DB Health Check Runbook"},
            {"id": "child2", "title": "SQL Server Access Guide"}, 
            {"id": "child3", "title": "General Information"}  # Should be excluded
        ]
    }