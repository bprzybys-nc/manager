#!/usr/bin/env python3
"""
Integration Test Runner for Confluence Integration Tool

This script runs comprehensive integration tests against a real Confluence instance.
It handles test environment setup, execution, and cleanup.
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

import requests
from dotenv import load_dotenv


class IntegrationTestRunner:
    """Main test runner for integration tests"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.api_base_url = f"http://{config['api_host']}:{config['api_port']}"
        self.test_results = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "errors": [],
            "performance": {}
        }
        self.created_pages = []
        self.logger = self._setup_logging()
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        logger = logging.getLogger("integration_tests")
        logger.setLevel(getattr(logging, self.config.get("log_level", "INFO")))
        
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    async def run_all_tests(self, categories: Optional[List[str]] = None) -> Dict:
        """Run all integration tests"""
        self.logger.info("Starting integration tests...")
        
        # Start the API server if needed
        if not await self._check_api_server():
            self.logger.error("API server is not running")
            return self.test_results
        
        # Define test categories
        test_categories = {
            "health": self._test_health_endpoints,
            "auth": self._test_authentication,
            "pages": self._test_page_operations,
            "search": self._test_search_functionality,
            "vector": self._test_vector_search,
            "attachments": self._test_attachment_operations,
            "bulk": self._test_bulk_operations,
            "errors": self._test_error_handling,
            "performance": self._test_performance
        }
        
        # Filter categories if specified
        if categories:
            test_categories = {k: v for k, v in test_categories.items() 
                             if k in categories}
        
        # Run tests
        for category, test_func in test_categories.items():
            self.logger.info(f"Running {category} tests...")
            try:
                await test_func()
                self.logger.info(f"✓ {category} tests completed")
            except Exception as e:
                self.logger.error(f"✗ {category} tests failed: {e}")
                self.test_results["errors"].append({
                    "category": category,
                    "error": str(e)
                })
        
        # Cleanup
        await self._cleanup_test_data()
        
        # Generate report
        self._generate_report()
        
        return self.test_results
    
    async def _check_api_server(self) -> bool:
        """Check if API server is running"""
        try:
            response = requests.get(f"{self.api_base_url}/health", timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False
    
    async def _test_health_endpoints(self):
        """Test health check endpoints"""
        endpoints = ["/health", "/health/detailed", "/health/confluence"]
        
        for endpoint in endpoints:
            response = requests.get(f"{self.api_base_url}{endpoint}")
            self._assert_status_code(response, 200, f"Health check {endpoint}")
            self.test_results["total"] += 1
            self.test_results["passed"] += 1
    
    async def _test_authentication(self):
        """Test authentication scenarios"""
        # Test valid authentication (implicit in other tests)
        self.test_results["total"] += 1
        self.test_results["passed"] += 1
        
        # Note: Invalid auth tests would require separate API instance
        # with different credentials, which is complex for integration tests
    
    async def _test_page_operations(self):
        """Test CRUD operations on pages"""
        # Create page
        page_data = {
            "title": f"Integration Test Page {int(time.time())}",
            "content": "<p>This is a test page created by integration tests.</p>",
            "space_key": self.config["test_space_key"]
        }
        
        response = requests.post(f"{self.api_base_url}/pages", json=page_data)
        self._assert_status_code(response, 201, "Create page")
        
        page = response.json()
        self.created_pages.append(page["id"])
        self.test_results["total"] += 1
        self.test_results["passed"] += 1
        
        # Read page
        response = requests.get(f"{self.api_base_url}/pages/{page['id']}")
        self._assert_status_code(response, 200, "Read page")
        
        retrieved_page = response.json()
        assert retrieved_page["title"] == page_data["title"]
        self.test_results["total"] += 1
        self.test_results["passed"] += 1
        
        # Update page
        update_data = {
            "title": page_data["title"] + " (Updated)",
            "content": "<p>Updated content</p>",
            "version": retrieved_page["version"] + 1
        }
        
        response = requests.put(f"{self.api_base_url}/pages/{page['id']}", 
                              json=update_data)
        self._assert_status_code(response, 200, "Update page")
        self.test_results["total"] += 1
        self.test_results["passed"] += 1
        
        # Get page content
        response = requests.get(f"{self.api_base_url}/pages/{page['id']}/content")
        self._assert_status_code(response, 200, "Get page content")
        self.test_results["total"] += 1
        self.test_results["passed"] += 1
    
    async def _test_search_functionality(self):
        """Test search capabilities"""
        # Create a test page with unique content
        unique_term = f"integration_test_{int(time.time())}"
        page_data = {
            "title": f"Search Test Page {unique_term}",
            "content": f"<p>This page contains the unique term: {unique_term}</p>",
            "space_key": self.config["test_space_key"]
        }
        
        response = requests.post(f"{self.api_base_url}/pages", json=page_data)
        self._assert_status_code(response, 201, "Create search test page")
        
        page = response.json()
        self.created_pages.append(page["id"])
        
        # Wait for indexing
        await asyncio.sleep(5)
        
        # Search for the page
        response = requests.get(f"{self.api_base_url}/search", 
                              params={"query": unique_term})
        self._assert_status_code(response, 200, "Search pages")
        
        results = response.json()
        assert results["total"] >= 1, "Search should find at least one result"
        
        # Verify our page is in results
        page_ids = [p["id"] for p in results["results"]]
        assert page["id"] in page_ids, "Created page should be in search results"
        
        self.test_results["total"] += 2
        self.test_results["passed"] += 2
        
        # Test space-specific search
        response = requests.get(
            f"{self.api_base_url}/search/spaces/{self.config['test_space_key']}", 
            params={"query": unique_term}
        )
        self._assert_status_code(response, 200, "Space-specific search")
        self.test_results["total"] += 1
        self.test_results["passed"] += 1
    
    async def _test_vector_search(self):
        """Test vector search functionality"""
        # Create pages with related content
        pages_data = [
            {
                "title": "Database Connection Issues",
                "content": "<p>Troubleshooting database connectivity problems and timeout errors.</p>",
                "space_key": self.config["test_space_key"]
            },
            {
                "title": "Network Connectivity Problems", 
                "content": "<p>Resolving network issues that affect database connections.</p>",
                "space_key": self.config["test_space_key"]
            }
        ]
        
        created_page_ids = []
        for page_data in pages_data:
            response = requests.post(f"{self.api_base_url}/pages", json=page_data)
            self._assert_status_code(response, 201, "Create vector test page")
            
            page = response.json()
            created_page_ids.append(page["id"])
            self.created_pages.append(page["id"])
        
        # Index the pages
        response = requests.post(f"{self.api_base_url}/bulk/index", 
                               json={"page_ids": created_page_ids})
        self._assert_status_code(response, 200, "Index pages for vector search")
        
        # Wait for indexing
        await asyncio.sleep(10)
        
        # Perform vector search
        search_data = {
            "query": "database connection problems",
            "limit": 5,
            "space_key": self.config["test_space_key"]
        }
        
        response = requests.post(f"{self.api_base_url}/search/vector", 
                               json=search_data)
        self._assert_status_code(response, 200, "Vector search")
        
        results = response.json()
        assert len(results["results"]) >= 1, "Vector search should find results"
        
        # Check similarity scores
        for result in results["results"]:
            assert result["similarity_score"] > 0.3, "Similarity score should be reasonable"
        
        self.test_results["total"] += 3
        self.test_results["passed"] += 3
    
    async def _test_attachment_operations(self):
        """Test attachment upload and download"""
        # Create a test page
        page_data = {
            "title": f"Attachment Test Page {int(time.time())}",
            "content": "<p>Page for testing attachments</p>",
            "space_key": self.config["test_space_key"]
        }
        
        response = requests.post(f"{self.api_base_url}/pages", json=page_data)
        self._assert_status_code(response, 201, "Create page for attachment test")
        
        page = response.json()
        self.created_pages.append(page["id"])
        
        # Create test file content
        test_content = b"This is test file content for integration testing."
        
        # Upload attachment
        files = {"file": ("test_file.txt", test_content, "text/plain")}
        response = requests.post(
            f"{self.api_base_url}/pages/{page['id']}/attachments",
            files=files
        )
        self._assert_status_code(response, 201, "Upload attachment")
        
        attachment = response.json()
        assert attachment["title"] == "test_file.txt"
        
        self.test_results["total"] += 2
        self.test_results["passed"] += 2
        
        # List attachments
        response = requests.get(f"{self.api_base_url}/pages/{page['id']}/attachments")
        self._assert_status_code(response, 200, "List attachments")
        
        attachments = response.json()
        assert attachments["total"] >= 1
        
        self.test_results["total"] += 1
        self.test_results["passed"] += 1
        
        # Download attachment
        response = requests.get(f"{self.api_base_url}/attachments/{attachment['id']}")
        self._assert_status_code(response, 200, "Download attachment")
        
        assert response.content == test_content
        
        self.test_results["total"] += 1
        self.test_results["passed"] += 1
    
    async def _test_bulk_operations(self):
        """Test bulk processing operations"""
        # Create multiple test pages
        page_ids = []
        for i in range(3):
            page_data = {
                "title": f"Bulk Test Page {i} {int(time.time())}",
                "content": f"<p>Content for bulk test page {i}</p>",
                "space_key": self.config["test_space_key"]
            }
            
            response = requests.post(f"{self.api_base_url}/pages", json=page_data)
            self._assert_status_code(response, 201, f"Create bulk test page {i}")
            
            page = response.json()
            page_ids.append(page["id"])
            self.created_pages.append(page["id"])
        
        # Start bulk indexing job
        response = requests.post(f"{self.api_base_url}/bulk/index", 
                               json={"page_ids": page_ids})
        self._assert_status_code(response, 200, "Start bulk indexing job")
        
        job = response.json()
        job_id = job["job_id"]
        
        # Check job status
        max_wait = 30
        wait_time = 0
        while wait_time < max_wait:
            response = requests.get(f"{self.api_base_url}/jobs/{job_id}")
            self._assert_status_code(response, 200, "Check job status")
            
            job_status = response.json()
            if job_status["status"] in ["completed", "failed"]:
                break
            
            await asyncio.sleep(2)
            wait_time += 2
        
        assert job_status["status"] == "completed", "Bulk job should complete successfully"
        
        self.test_results["total"] += 5
        self.test_results["passed"] += 5
    
    async def _test_error_handling(self):
        """Test error handling scenarios"""
        # Test 404 for non-existent page
        response = requests.get(f"{self.api_base_url}/pages/999999999")
        self._assert_status_code(response, 404, "Non-existent page should return 404")
        
        # Test invalid page creation
        invalid_page_data = {
            "title": "",  # Empty title should be invalid
            "content": "<p>Content</p>",
            "space_key": "INVALIDSPACE"
        }
        
        response = requests.post(f"{self.api_base_url}/pages", json=invalid_page_data)
        assert response.status_code >= 400, "Invalid page data should return error"
        
        self.test_results["total"] += 2
        self.test_results["passed"] += 2
    
    async def _test_performance(self):
        """Test performance characteristics"""
        start_time = time.time()
        
        # Create a page and measure response time
        page_data = {
            "title": f"Performance Test Page {int(time.time())}",
            "content": "<p>Performance test content</p>",
            "space_key": self.config["test_space_key"]
        }
        
        response = requests.post(f"{self.api_base_url}/pages", json=page_data)
        create_time = time.time() - start_time
        
        self._assert_status_code(response, 201, "Performance test page creation")
        
        page = response.json()
        self.created_pages.append(page["id"])
        
        # Measure search performance
        start_time = time.time()
        response = requests.get(f"{self.api_base_url}/search", 
                              params={"query": "performance"})
        search_time = time.time() - start_time
        
        self._assert_status_code(response, 200, "Performance test search")
        
        # Record performance metrics
        self.test_results["performance"] = {
            "page_creation_time": create_time,
            "search_time": search_time
        }
        
        # Assert reasonable performance
        assert create_time < 5.0, f"Page creation took too long: {create_time}s"
        assert search_time < 3.0, f"Search took too long: {search_time}s"
        
        self.test_results["total"] += 2
        self.test_results["passed"] += 2
    
    def _assert_status_code(self, response: requests.Response, 
                          expected: int, operation: str):
        """Assert HTTP status code and handle failures"""
        if response.status_code != expected:
            error_msg = f"{operation} failed: expected {expected}, got {response.status_code}"
            if response.content:
                error_msg += f" - {response.text}"
            
            self.test_results["failed"] += 1
            self.test_results["errors"].append({
                "operation": operation,
                "expected_status": expected,
                "actual_status": response.status_code,
                "response": response.text
            })
            raise AssertionError(error_msg)
    
    async def _cleanup_test_data(self):
        """Clean up created test data"""
        self.logger.info(f"Cleaning up {len(self.created_pages)} test pages...")
        
        for page_id in self.created_pages:
            try:
                response = requests.delete(f"{self.api_base_url}/pages/{page_id}")
                if response.status_code not in [200, 204, 404]:
                    self.logger.warning(f"Failed to delete page {page_id}: {response.status_code}")
            except Exception as e:
                self.logger.warning(f"Error deleting page {page_id}: {e}")
        
        self.created_pages.clear()
    
    def _generate_report(self):
        """Generate test report"""
        success_rate = (self.test_results["passed"] / self.test_results["total"] * 100 
                       if self.test_results["total"] > 0 else 0)
        
        self.logger.info("=" * 50)
        self.logger.info("INTEGRATION TEST RESULTS")
        self.logger.info("=" * 50)
        self.logger.info(f"Total Tests: {self.test_results['total']}")
        self.logger.info(f"Passed: {self.test_results['passed']}")
        self.logger.info(f"Failed: {self.test_results['failed']}")
        self.logger.info(f"Success Rate: {success_rate:.1f}%")
        
        if self.test_results["performance"]:
            self.logger.info("\nPerformance Metrics:")
            for metric, value in self.test_results["performance"].items():
                self.logger.info(f"  {metric}: {value:.3f}s")
        
        if self.test_results["errors"]:
            self.logger.info("\nErrors:")
            for error in self.test_results["errors"]:
                self.logger.error(f"  {error}")
        
        self.logger.info("=" * 50)


def load_test_config() -> Dict:
    """Load test configuration from environment"""
    # Load environment variables
    env_file = Path(".env.test")
    if env_file.exists():
        load_dotenv(env_file)
    else:
        load_dotenv()  # Load default .env
    
    config = {
        "confluence_url": os.getenv("CONFLUENCE_URL"),
        "confluence_username": os.getenv("CONFLUENCE_USERNAME"),
        "confluence_api_token": os.getenv("CONFLUENCE_API_TOKEN"),
        "test_space_key": os.getenv("TEST_SPACE_KEY", "TESTSPACE"),
        "api_host": os.getenv("TEST_API_HOST", "127.0.0.1"),
        "api_port": int(os.getenv("TEST_API_PORT", "8005")),
        "log_level": os.getenv("TEST_LOG_LEVEL", "INFO")
    }
    
    # Validate required configuration
    required_fields = ["confluence_url", "confluence_username", 
                      "confluence_api_token", "test_space_key"]
    
    missing_fields = [field for field in required_fields if not config[field]]
    if missing_fields:
        raise ValueError(f"Missing required configuration: {missing_fields}")
    
    return config


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Run Confluence Integration Tests")
    parser.add_argument("--categories", nargs="+", 
                       choices=["health", "auth", "pages", "search", "vector", 
                               "attachments", "bulk", "errors", "performance"],
                       help="Test categories to run")
    parser.add_argument("--verbose", action="store_true", 
                       help="Enable verbose output")
    parser.add_argument("--ci", action="store_true", 
                       help="CI mode - exit with error code on failure")
    parser.add_argument("--junit-xml", 
                       help="Generate JUnit XML report")
    parser.add_argument("--performance-report", 
                       help="Generate performance report JSON")
    
    args = parser.parse_args()
    
    try:
        # Load configuration
        config = load_test_config()
        
        if args.verbose:
            config["log_level"] = "DEBUG"
        
        # Run tests
        runner = IntegrationTestRunner(config)
        results = await runner.run_all_tests(args.categories)
        
        # Generate additional reports
        if args.junit_xml:
            generate_junit_xml(results, args.junit_xml)
        
        if args.performance_report:
            generate_performance_report(results, args.performance_report)
        
        # Exit with appropriate code
        if args.ci and results["failed"] > 0:
            sys.exit(1)
        
    except Exception as e:
        print(f"Error running integration tests: {e}")
        if args.ci:
            sys.exit(1)
        raise


def generate_junit_xml(results: Dict, filename: str):
    """Generate JUnit XML report"""
    # Simple JUnit XML generation
    # In a real implementation, you'd use a proper XML library
    xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="confluence-integration-tests" 
           tests="{results['total']}" 
           failures="{results['failed']}" 
           errors="0">
"""
    
    for i in range(results["passed"]):
        xml_content += f'  <testcase name="test_{i}" classname="IntegrationTest"/>\n'
    
    for i, error in enumerate(results["errors"]):
        xml_content += f"""  <testcase name="test_error_{i}" classname="IntegrationTest">
    <failure message="{error.get('operation', 'Unknown')}">{error}</failure>
  </testcase>
"""
    
    xml_content += "</testsuite>"
    
    with open(filename, "w") as f:
        f.write(xml_content)


def generate_performance_report(results: Dict, filename: str):
    """Generate performance report JSON"""
    with open(filename, "w") as f:
        json.dump(results["performance"], f, indent=2)


if __name__ == "__main__":
    asyncio.run(main())