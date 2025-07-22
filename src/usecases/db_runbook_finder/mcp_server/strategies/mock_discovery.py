"""
Mock Runbook Discovery Strategy Implementation.

This module provides a mock implementation of RunbookDiscoveryStrategy using
existing test data for development and testing purposes.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import random
from pathlib import Path

from .protocols import RunbookDiscoveryStrategy
from ..exceptions import MCPRunbookError, RunbookNotFoundError

logger = logging.getLogger(__name__)


class MockDiscoveryStrategy:
    """
    Mock runbook discovery strategy implementation.
    
    Uses existing test data from tests/data/ directory to simulate runbook
    discovery operations. Implements RunbookDiscoveryStrategy protocol
    through structural subtyping.
    """
    
    def __init__(self):
        """Initialize mock strategy with test data."""
        self._mock_runbooks: List[Dict[str, Any]] = []
        self._load_test_data()
        
        logger.info(f"MockDiscoveryStrategy initialized with {len(self._mock_runbooks)} test runbooks")
    
    def _load_test_data(self) -> None:
        """Load test runbook data from JSON files."""
        try:
            # Import the test data loader
            import sys
            import os
            sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "tests", "data"))
            
            from test_data_loader import load_test_runbooks
            
            self._mock_runbooks = load_test_runbooks()
            
            # Ensure each runbook has required fields
            for runbook in self._mock_runbooks:
                metadata = runbook.get("metadata", {})
                if "page_id" not in metadata:
                    metadata["page_id"] = f"mock_{hash(metadata.get('title', 'unknown'))}"
                if "space_key" not in metadata:
                    metadata["space_key"] = "MOCK_RUNBOOKS"
                if "url" not in metadata:
                    metadata["url"] = f"https://mock-confluence.example.com/pages/{metadata['page_id']}"
                
                runbook["metadata"] = metadata
                
        except Exception as e:
            logger.warning(f"Could not load test data, using minimal mock data: {e}")
            
            # Fallback minimal mock data
            self._mock_runbooks = [
                {
                    "metadata": {
                        "title": "Mock Database Connection Runbook",
                        "space_key": "MOCK_RUNBOOKS",
                        "page_id": "mock_db_001",
                        "url": "https://mock-confluence.example.com/pages/mock_db_001",
                        "tags": ["database", "connection", "troubleshooting"],
                        "created_at": "2024-01-01T10:00:00Z",
                        "updated_at": "2024-01-02T10:00:00Z"
                    },
                    "procedures": [
                        {
                            "step": 1,
                            "description": "Check database status",
                            "command": "systemctl status database",
                            "expected_result": "Service active"
                        }
                    ],
                    "troubleshooting_steps": [
                        {
                            "symptom": "Connection timeout",
                            "possible_causes": ["Network issues"],
                            "resolution": "Check network connectivity"
                        }
                    ],
                    "prerequisites": ["Database access"],
                    "raw_content": "# Mock Database Connection Runbook\nTest runbook for development"
                },
                {
                    "metadata": {
                        "title": "Mock Performance Optimization Runbook",
                        "space_key": "MOCK_RUNBOOKS", 
                        "page_id": "mock_perf_001",
                        "url": "https://mock-confluence.example.com/pages/mock_perf_001",
                        "tags": ["performance", "optimization", "database"],
                        "created_at": "2024-01-01T11:00:00Z",
                        "updated_at": "2024-01-02T11:00:00Z"
                    },
                    "procedures": [
                        {
                            "step": 1,
                            "description": "Monitor query performance",
                            "command": "SHOW PROCESSLIST",
                            "expected_result": "Identify slow queries"
                        }
                    ],
                    "troubleshooting_steps": [
                        {
                            "symptom": "Slow queries",
                            "possible_causes": ["Missing indexes"],
                            "resolution": "Add appropriate indexes"
                        }
                    ],
                    "prerequisites": ["Performance monitoring access"],
                    "raw_content": "# Mock Performance Optimization Runbook\nTest runbook for performance tuning"
                }
            ]
    
    async def health_check(self) -> bool:
        """
        Mock health check - always returns True.
        
        Returns:
            True (mock implementation is always healthy)
        """
        return True
    
    # RunbookDiscoveryStrategy Protocol Implementation
    async def discover_runbooks(self, spaces: List[str]) -> List[Dict[str, Any]]:
        """
        Discover mock runbooks in specified spaces.
        
        Args:
            spaces: List of space keys to search
            
        Returns:
            List of mock runbook metadata dictionaries
        """
        try:
            # Simulate some processing time (reduced to meet performance requirements)
            await asyncio.sleep(0.01)
            
            discovered_runbooks = []
            
            for runbook in self._mock_runbooks:
                metadata = runbook.get("metadata", {})
                space_key = metadata.get("space_key", "")
                
                # Filter by spaces if specified
                if not spaces or space_key in spaces or "MOCK_RUNBOOKS" in spaces:
                    discovered_metadata = self._extract_runbook_metadata_from_full(runbook)
                    discovered_runbooks.append(discovered_metadata)
            
            # Add some randomness to simulate real discovery variability
            if len(discovered_runbooks) > 1:
                random.shuffle(discovered_runbooks)
            
            logger.info(f"Mock discovered {len(discovered_runbooks)} runbooks in spaces: {spaces}")
            return discovered_runbooks
            
        except Exception as e:
            raise MCPRunbookError(f"Mock runbook discovery failed: {e}")
    
    async def get_runbook_content(self, runbook_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve specific mock runbook content.
        
        Args:
            runbook_id: Mock runbook identifier
            
        Returns:
            Mock runbook content dictionary or None if not found
        """
        try:
            # Simulate some processing time (reduced for performance)
            await asyncio.sleep(0.005)
            
            for runbook in self._mock_runbooks:
                metadata = runbook.get("metadata", {})
                if metadata.get("page_id") == runbook_id:
                    # Return full runbook content
                    content = runbook.copy()
                    content["retrieved_at"] = datetime.utcnow().isoformat()
                    content["source"] = "mock"
                    
                    logger.info(f"Mock retrieved runbook content for ID: {runbook_id}")
                    return content
            
            logger.warning(f"Mock runbook not found: {runbook_id}")
            return None
            
        except Exception as e:
            raise MCPRunbookError(f"Mock failed to get runbook content: {e}")
    
    async def validate_runbook_content(self, page: Dict[str, Any]) -> bool:
        """
        Validate mock runbook content structure.
        
        Args:
            page: Page content dictionary to validate
            
        Returns:
            True if content appears to be a valid runbook (mock validation)
        """
        try:
            # Mock validation - check for basic runbook structure
            title = page.get("title", page.get("metadata", {}).get("title", "")).lower()
            content = page.get("content", page.get("raw_content", "")).lower()
            
            # Mock runbook indicators
            runbook_indicators = [
                "runbook", "procedure", "troubleshooting", "guide", 
                "steps", "instructions", "process", "workflow"
            ]
            
            # Check for indicators in title or content
            has_indicators = any(indicator in title or indicator in content 
                               for indicator in runbook_indicators)
            
            # Mock structural validation
            has_procedures = bool(page.get("procedures"))
            has_troubleshooting = bool(page.get("troubleshooting_steps"))
            has_content = len(content) > 50
            
            is_valid = has_indicators or has_procedures or has_troubleshooting or has_content
            
            logger.debug(f"Mock validation result: {is_valid} for page with title: {title}")
            return is_valid
            
        except Exception as e:
            logger.error(f"Mock validation error: {e}")
            return False
    
    async def extract_runbook_metadata(self, page: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract metadata from mock runbook page.
        
        Args:
            page: Page content dictionary
            
        Returns:
            Mock metadata dictionary with standardized fields
        """
        try:
            # Extract metadata from page structure
            if "metadata" in page:
                base_metadata = page["metadata"].copy()
            else:
                base_metadata = {}
            
            # Standard metadata extraction
            extracted_metadata = {
                "title": page.get("title", base_metadata.get("title", "Unknown Runbook")),
                "page_id": base_metadata.get("page_id", f"mock_{hash(str(page))}"),
                "space_key": base_metadata.get("space_key", "MOCK_RUNBOOKS"),
                "space_name": base_metadata.get("space_name", "Mock Runbooks Space"),
                "url": base_metadata.get("url", "https://mock-confluence.example.com/pages/unknown"),
                "last_modified": base_metadata.get("updated_at", datetime.utcnow().isoformat()),
                "author": base_metadata.get("author", "Mock Author"),
                "tags": base_metadata.get("tags", []),
                "extracted_at": datetime.utcnow().isoformat(),
                "source": "mock"
            }
            
            # Extract content-based metadata if available
            if "raw_content" in page:
                content_metadata = self._extract_mock_content_metadata(page["raw_content"])
                extracted_metadata.update(content_metadata)
            
            return extracted_metadata
            
        except Exception as e:
            logger.error(f"Mock metadata extraction error: {e}")
            return {
                "error": str(e), 
                "extracted_at": datetime.utcnow().isoformat(),
                "source": "mock"
            }
    
    async def search_runbooks_by_query(self, query: str, spaces: Optional[List[str]] = None, 
                                     limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search mock runbooks by text query.
        
        Args:
            query: Search query string
            spaces: Optional list of spaces to search (searches all if None)
            limit: Maximum results to return
            
        Returns:
            List of matching mock runbook dictionaries
        """
        try:
            # Simulate some processing time (reduced to meet <50ms performance requirement)
            await asyncio.sleep(0.01)
            
            query_lower = query.lower()
            matching_runbooks = []
            
            for runbook in self._mock_runbooks:
                metadata = runbook.get("metadata", {})
                
                # Filter by spaces if specified
                if spaces and metadata.get("space_key") not in spaces:
                    continue
                
                # Check for query matches in various fields
                matches_title = query_lower in metadata.get("title", "").lower()
                matches_tags = any(query_lower in tag.lower() for tag in metadata.get("tags", []))
                matches_content = query_lower in runbook.get("raw_content", "").lower()
                
                # Calculate relevance score (mock scoring)
                relevance_score = 0.0
                if matches_title:
                    relevance_score += 0.8
                if matches_tags:
                    relevance_score += 0.6
                if matches_content:
                    relevance_score += 0.4
                
                if relevance_score > 0:
                    result = self._extract_runbook_metadata_from_full(runbook)
                    result["search_relevance"] = relevance_score
                    result["search_query"] = query
                    result["matched_fields"] = []
                    
                    if matches_title:
                        result["matched_fields"].append("title")
                    if matches_tags:
                        result["matched_fields"].append("tags")
                    if matches_content:
                        result["matched_fields"].append("content")
                    
                    matching_runbooks.append(result)
            
            # Sort by relevance score (descending)
            matching_runbooks.sort(key=lambda x: x.get("search_relevance", 0), reverse=True)
            
            # Apply limit
            matching_runbooks = matching_runbooks[:limit]
            
            logger.info(f"Mock search for '{query}' found {len(matching_runbooks)} results")
            return matching_runbooks
            
        except Exception as e:
            raise MCPRunbookError(f"Mock runbook search failed: {e}")
    
    # Helper Methods
    def _extract_runbook_metadata_from_full(self, runbook: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract standardized metadata from full runbook data.
        
        Args:
            runbook: Full runbook dictionary
            
        Returns:
            Standardized metadata dictionary
        """
        metadata = runbook.get("metadata", {})
        
        return {
            "runbook_id": metadata.get("page_id", f"mock_{hash(str(runbook))}"),
            "title": metadata.get("title", "Unknown Mock Runbook"),
            "space_key": metadata.get("space_key", "MOCK_RUNBOOKS"),
            "space_name": metadata.get("space_name", "Mock Runbooks Space"),
            "url": metadata.get("url", "https://mock-confluence.example.com/pages/unknown"),
            "last_modified": metadata.get("updated_at", datetime.utcnow().isoformat()),
            "author": metadata.get("author", "Mock Author"),
            "summary": runbook.get("structured_sections", {}).get("overview", "Mock runbook for development and testing"),
            "tags": metadata.get("tags", []),
            "source": "mock",
            "discovery_timestamp": datetime.utcnow().isoformat(),
            "estimated_steps": len(runbook.get("procedures", [])),
            "complexity": self._estimate_mock_complexity(runbook),
            "categories": self._extract_mock_categories(runbook)
        }
    
    def _extract_mock_content_metadata(self, content: str) -> Dict[str, Any]:
        """
        Extract additional metadata from mock content.
        
        Args:
            content: Runbook text content
            
        Returns:
            Additional metadata dictionary
        """
        content_lower = content.lower()
        
        # Estimate steps/procedures
        step_count = max(
            content.count("step "),
            content.count("1."),
            content.count("2."),
            len([line for line in content.split('\n') if line.strip().startswith(('1.', '2.', '3.'))])
        )
        
        # Estimate complexity
        complexity = "high" if len(content) > 2000 else "medium" if len(content) > 500 else "low"
        
        # Identify categories
        categories = []
        category_indicators = {
            "database": ["database", "db", "sql", "mysql", "postgresql", "mongodb"],
            "infrastructure": ["server", "network", "infrastructure", "deployment"],
            "security": ["security", "authentication", "authorization", "ssl", "certificate"],
            "monitoring": ["monitoring", "alert", "metric", "log", "performance"],
            "troubleshooting": ["troubleshoot", "debug", "error", "issue", "problem"]
        }
        
        for category, indicators in category_indicators.items():
            if any(indicator in content_lower for indicator in indicators):
                categories.append(category)
        
        return {
            "estimated_steps": step_count,
            "content_length": len(content),
            "complexity": complexity,
            "categories": categories
        }
    
    def _estimate_mock_complexity(self, runbook: Dict[str, Any]) -> str:
        """
        Estimate runbook complexity for mock data.
        
        Args:
            runbook: Full runbook dictionary
            
        Returns:
            Complexity string (low, medium, high)
        """
        procedure_count = len(runbook.get("procedures", []))
        troubleshooting_count = len(runbook.get("troubleshooting_steps", []))
        prerequisite_count = len(runbook.get("prerequisites", []))
        content_length = len(runbook.get("raw_content", ""))
        
        complexity_score = procedure_count + troubleshooting_count + prerequisite_count + (content_length // 500)
        
        if complexity_score > 10:
            return "high"
        elif complexity_score > 5:
            return "medium"
        else:
            return "low"
    
    def _extract_mock_categories(self, runbook: Dict[str, Any]) -> List[str]:
        """
        Extract categories from mock runbook data.
        
        Args:
            runbook: Full runbook dictionary
            
        Returns:
            List of category strings
        """
        categories = set()
        
        # Extract from tags
        tags = runbook.get("metadata", {}).get("tags", [])
        for tag in tags:
            tag_lower = tag.lower()
            if tag_lower in ["database", "db", "performance", "security", "monitoring", "troubleshooting", "infrastructure"]:
                categories.add(tag_lower)
        
        # Extract from content if available
        content = runbook.get("raw_content", "").lower()
        if "database" in content or "db" in content:
            categories.add("database")
        if "performance" in content or "optimization" in content:
            categories.add("performance")
        if "security" in content or "authentication" in content:
            categories.add("security")
        if "monitor" in content or "alert" in content:
            categories.add("monitoring")
        if "troubleshoot" in content or "debug" in content:
            categories.add("troubleshooting")
        
        return list(categories)
    
    def get_all_mock_runbooks(self) -> List[Dict[str, Any]]:
        """Get all mock runbook data for testing and debugging."""
        return self._mock_runbooks.copy()
    
    def add_mock_runbook(self, runbook: Dict[str, Any]) -> None:
        """Add a new mock runbook for testing purposes."""
        # Ensure proper metadata structure
        if "metadata" not in runbook:
            runbook["metadata"] = {}
        
        metadata = runbook["metadata"]
        if "page_id" not in metadata:
            metadata["page_id"] = f"mock_custom_{len(self._mock_runbooks)}"
        if "space_key" not in metadata:
            metadata["space_key"] = "MOCK_RUNBOOKS"
        if "created_at" not in metadata:
            metadata["created_at"] = datetime.utcnow().isoformat()
        if "updated_at" not in metadata:
            metadata["updated_at"] = datetime.utcnow().isoformat()
        
        self._mock_runbooks.append(runbook)
        logger.info(f"Added mock runbook: {metadata.get('title', 'Unknown')}")
    
    def clear_mock_data(self) -> None:
        """Clear all mock data and reload from files."""
        self._mock_runbooks.clear()
        self._load_test_data()
        logger.info("Mock runbook data cleared and reloaded")