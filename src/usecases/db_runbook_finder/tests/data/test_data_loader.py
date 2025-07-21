#!/usr/bin/env python3
"""
Test data loader for ChromaDB runbook testing.
Provides utilities to load mock runbook data for comprehensive endpoint testing.
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional


class MockRunbookDataLoader:
    """Loads and manages mock runbook data for testing."""
    
    def __init__(self, data_dir: Optional[Path] = None):
        """Initialize the data loader.
        
        Args:
            data_dir: Directory containing mock runbook JSON files.
                     Defaults to the same directory as this file.
        """
        if data_dir is None:
            data_dir = Path(__file__).parent
        self.data_dir = data_dir
        self._cached_runbooks = None
    
    def load_all_runbooks(self) -> List[Dict[str, Any]]:
        """Load all mock runbook data from JSON files.
        
        Returns:
            List of runbook dictionaries with complete metadata and content.
        """
        if self._cached_runbooks is not None:
            return self._cached_runbooks
            
        runbooks = []
        json_files = list(self.data_dir.glob("*_runbook.json"))
        
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    runbook_data = json.load(f)
                    runbooks.append(runbook_data)
            except Exception as e:
                print(f"Warning: Failed to load {json_file}: {e}")
                continue
        
        self._cached_runbooks = runbooks
        return runbooks
    
    def get_runbook_by_title(self, title: str) -> Optional[Dict[str, Any]]:
        """Get a specific runbook by title.
        
        Args:
            title: The runbook title to search for.
            
        Returns:
            Runbook dictionary if found, None otherwise.
        """
        runbooks = self.load_all_runbooks()
        for runbook in runbooks:
            if runbook.get('metadata', {}).get('title', '').lower() == title.lower():
                return runbook
        return None
    
    def get_runbooks_by_tag(self, tag: str) -> List[Dict[str, Any]]:
        """Get runbooks that contain a specific tag.
        
        Args:
            tag: Tag to search for in runbook metadata.
            
        Returns:
            List of runbooks containing the specified tag.
        """
        runbooks = self.load_all_runbooks()
        matching_runbooks = []
        
        for runbook in runbooks:
            tags = runbook.get('metadata', {}).get('tags', [])
            if tag.lower() in [t.lower() for t in tags]:
                matching_runbooks.append(runbook)
                
        return matching_runbooks
    
    def get_semantic_search_queries(self) -> List[Dict[str, Any]]:
        """Get predefined queries for semantic search testing.
        
        Returns:
            List of test queries with expected matching runbooks.
        """
        return [
            {
                "query": "database connection timeout issues",
                "expected_matches": [
                    "Database Connection Troubleshooting Runbook"
                ],
                "expected_min_results": 1
            },
            {
                "query": "slow query performance optimization",
                "expected_matches": [
                    "Database Performance Monitoring and Optimization"
                ],
                "expected_min_results": 1
            },
            {
                "query": "backup and disaster recovery procedures",
                "expected_matches": [
                    "Database Backup and Recovery Procedures"
                ],
                "expected_min_results": 1
            },
            {
                "query": "database security hardening access control",
                "expected_matches": [
                    "Database Security Hardening and Access Control"
                ],
                "expected_min_results": 1
            },
            {
                "query": "schema migration deployment rollback",
                "expected_matches": [
                    "Database Migration and Schema Changes"
                ],
                "expected_min_results": 1
            },
            {
                "query": "postgresql mysql troubleshooting",
                "expected_matches": [
                    "Database Connection Troubleshooting Runbook",
                    "Database Performance Monitoring and Optimization"
                ],
                "expected_min_results": 2
            }
        ]
    
    def get_confluence_search_queries(self) -> List[Dict[str, Any]]:
        """Get predefined queries for Confluence text search testing.
        
        Returns:
            List of test queries for Confluence API search.
        """
        return [
            {
                "query": "database",
                "space_key": "RUNBOOKS",
                "expected_min_results": 3
            },
            {
                "query": "troubleshooting",
                "space_key": None,
                "expected_min_results": 1
            },
            {
                "query": "performance monitoring",
                "space_key": "RUNBOOKS", 
                "expected_min_results": 1
            },
            {
                "query": "security hardening",
                "space_key": "RUNBOOKS",
                "expected_min_results": 1
            }
        ]
    
    def get_runbook_metadata_samples(self) -> List[Dict[str, Any]]:
        """Get sample runbook metadata for testing runbook management endpoints.
        
        Returns:
            List of runbook metadata dictionaries.
        """
        runbooks = self.load_all_runbooks()
        return [rb.get('metadata', {}) for rb in runbooks]
    
    def get_test_scenarios(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get comprehensive test scenarios for different endpoint types.
        
        Returns:
            Dictionary with test scenarios categorized by endpoint type.
        """
        return {
            "semantic_search": self.get_semantic_search_queries(),
            "confluence_search": self.get_confluence_search_queries(),
            "runbook_management": [
                {
                    "operation": "create",
                    "data": self.get_runbook_by_title("Database Connection Troubleshooting Runbook")
                },
                {
                    "operation": "update", 
                    "runbook_id": "test_runbook_123",
                    "updates": {
                        "metadata": {"tags": ["updated", "test"]},
                        "procedures": []
                    }
                },
                {
                    "operation": "delete",
                    "runbook_id": "test_runbook_123"
                }
            ],
            "bulk_operations": [
                {
                    "operation": "bulk_extract",
                    "page_ids": ["123456", "234567", "345678", "456789", "567890"],
                    "expected_success_count": 5
                },
                {
                    "operation": "bulk_index",
                    "runbook_ids": ["rb_001", "rb_002", "rb_003"],
                    "expected_index_count": 3
                }
            ]
        }
    
    def get_error_test_cases(self) -> List[Dict[str, Any]]:
        """Get test cases for error handling validation.
        
        Returns:
            List of test cases that should trigger specific error responses.
        """
        return [
            {
                "endpoint": "/search/runbooks",
                "params": {"query": "", "limit": 5},
                "expected_status": 422,
                "description": "Empty query parameter"
            },
            {
                "endpoint": "/search/runbooks", 
                "params": {"query": "test", "limit": 0},
                "expected_status": 422,
                "description": "Invalid limit (too low)"
            },
            {
                "endpoint": "/search/runbooks",
                "params": {"query": "test", "limit": 25},
                "expected_status": 422,
                "description": "Invalid limit (too high)"
            },
            {
                "endpoint": "/runbooks/nonexistent_id",
                "params": {},
                "expected_status": 404,
                "description": "Runbook not found"
            },
            {
                "endpoint": "/runbooks/%20",
                "params": {},
                "expected_status": 422,
                "description": "Empty runbook ID (whitespace)"
            }
        ]
    
    def get_performance_test_data(self) -> Dict[str, Any]:
        """Get data for performance testing scenarios.
        
        Returns:
            Dictionary containing performance test configuration.
        """
        return {
            "concurrent_searches": {
                "query_count": 10,
                "concurrent_users": 3,
                "queries": [
                    "database connection",
                    "performance monitoring", 
                    "backup recovery",
                    "security hardening",
                    "schema migration"
                ]
            },
            "bulk_operations": {
                "large_extraction": {
                    "page_count": 50,
                    "expected_max_time": 120.0  # seconds
                },
                "concurrent_extractions": {
                    "job_count": 5,
                    "pages_per_job": 10
                }
            },
            "search_performance": {
                "max_response_time": 2.0,  # seconds
                "queries_for_timing": [
                    "database troubleshooting performance",
                    "postgresql mysql connection timeout",
                    "backup recovery disaster procedures"
                ]
            }
        }


# Global instance for easy access in tests
mock_data_loader = MockRunbookDataLoader()


def load_test_runbooks() -> List[Dict[str, Any]]:
    """Convenience function to load all test runbooks."""
    return mock_data_loader.load_all_runbooks()


def get_semantic_test_queries() -> List[Dict[str, Any]]:
    """Convenience function to get semantic search test queries."""
    return mock_data_loader.get_semantic_search_queries()


def get_confluence_test_queries() -> List[Dict[str, Any]]:
    """Convenience function to get Confluence search test queries."""
    return mock_data_loader.get_confluence_search_queries()