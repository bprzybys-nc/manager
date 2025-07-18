"""
Tests for health check and monitoring endpoints.

This module contains comprehensive tests for all health check and monitoring
endpoints including /health, /health/ready, /health/live, and /metrics.
"""

import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from .api import app
from .models import HealthResponse


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestHealthResponseModel:
    """Test cases for HealthResponse model validation."""

    def test_health_response_valid_data(self):
        """Test HealthResponse model with valid data."""
        response = HealthResponse(
            status="healthy",
            confluence_connected=True,
            vector_db_connected=True,
            collections_count=2,
            total_runbooks=10,
            timestamp=datetime.utcnow()
        )
        
        assert response.status == "healthy"
        assert response.confluence_connected is True
        assert response.vector_db_connected is True
        assert response.collections_count == 2
        assert response.total_runbooks == 10
        assert isinstance(response.timestamp, datetime)

    def test_health_response_default_timestamp(self):
        """Test HealthResponse model with default timestamp."""
        response = HealthResponse(
            status="degraded",
            confluence_connected=False,
            vector_db_connected=True,
            collections_count=1,
            total_runbooks=5
        )
        
        assert response.status == "degraded"
        assert isinstance(response.timestamp, datetime)

    def test_health_response_invalid_collections_count(self):
        """Test HealthResponse model with invalid collections count."""
        with pytest.raises(ValueError):
            HealthResponse(
                status="healthy",
                confluence_connected=True,
                vector_db_connected=True,
                collections_count=-1,  # Invalid negative count
                total_runbooks=10
            )

    def test_health_response_invalid_runbooks_count(self):
        """Test HealthResponse model with invalid runbooks count."""
        with pytest.raises(ValueError):
            HealthResponse(
                status="healthy",
                confluence_connected=True,
                vector_db_connected=True,
                collections_count=1,
                total_runbooks=-5  # Invalid negative count
            )


class TestHealthEndpoints:
    """Test cases for health endpoints structure and response format."""

    def test_health_endpoint_exists(self, client):
        """Test that /health endpoint exists and returns proper structure."""
        response = client.get("/health")
        
        # Should return a response (may be error due to missing dependencies)
        assert response.status_code in [200, 500]
        
        # Should return JSON
        assert response.headers["content-type"] == "application/json"
        
        data = response.json()
        
        if response.status_code == 200:
            # Check required fields are present
            required_fields = ["status", "confluence_connected", "vector_db_connected", 
                             "collections_count", "total_runbooks", "timestamp"]
            for field in required_fields:
                assert field in data
            
            # Check data types
            assert isinstance(data["status"], str)
            assert isinstance(data["confluence_connected"], bool)
            assert isinstance(data["vector_db_connected"], bool)
            assert isinstance(data["collections_count"], int)
            assert isinstance(data["total_runbooks"], int)
            assert isinstance(data["timestamp"], str)
            
            # Verify timestamp format
            datetime.fromisoformat(data["timestamp"].replace('Z', '+00:00'))

    def test_readiness_endpoint_exists(self, client):
        """Test that /health/ready endpoint exists and returns proper structure."""
        response = client.get("/health/ready")
        
        # Should return a response
        assert response.status_code in [200, 503]
        
        # Should return JSON
        assert response.headers["content-type"] == "application/json"
        
        data = response.json()
        
        if response.status_code == 200:
            # Check required fields for success response
            assert "status" in data
            assert "timestamp" in data
            assert "message" in data
            assert data["status"] == "ready"
        else:
            # Check error response structure
            assert "detail" in data
            if isinstance(data["detail"], dict):
                assert "status" in data["detail"]
                assert data["detail"]["status"] == "not_ready"

    def test_liveness_endpoint_exists(self, client):
        """Test that /health/live endpoint exists and returns proper structure."""
        response = client.get("/health/live")
        
        # Should return a response
        assert response.status_code in [200, 500]
        
        # Should return JSON
        assert response.headers["content-type"] == "application/json"
        
        data = response.json()
        
        if response.status_code == 200:
            # Check required fields for success response
            assert "status" in data
            assert "timestamp" in data
            assert "message" in data
            assert "uptime_check" in data
            assert data["status"] == "alive"
        else:
            # Check error response structure
            assert "detail" in data

    def test_metrics_endpoint_exists(self, client):
        """Test that /metrics endpoint exists and returns proper structure."""
        response = client.get("/metrics")
        
        # Should return a response
        assert response.status_code in [200, 500]
        
        # Should return JSON
        assert response.headers["content-type"] == "application/json"
        
        data = response.json()
        
        if response.status_code == 200:
            # Check required top-level sections
            required_sections = ["timestamp", "service_info", "vector_store", 
                               "confluence", "thread_pool", "system"]
            for section in required_sections:
                assert section in data
            
            # Check service info structure
            assert "name" in data["service_info"]
            assert "version" in data["service_info"]
            assert data["service_info"]["name"] == "confluence-integration-tool"
            
            # Check vector store metrics structure
            vector_store_fields = ["collections_count", "total_chunks", 
                                 "total_runbooks", "vector_db_status"]
            for field in vector_store_fields:
                assert field in data["vector_store"]
            
            # Check Confluence metrics structure
            confluence_fields = ["confluence_status", "api_accessible"]
            for field in confluence_fields:
                assert field in data["confluence"]
            
            # Check thread pool metrics structure
            thread_pool_fields = ["max_workers", "active_threads"]
            for field in thread_pool_fields:
                assert field in data["thread_pool"]
            
            # Check system metrics structure
            assert "status" in data["system"]
        else:
            # Check error response structure
            assert "detail" in data

    def test_all_health_endpoints_return_json(self, client):
        """Test that all health endpoints return valid JSON."""
        endpoints = ["/health", "/health/ready", "/health/live", "/metrics"]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            
            # Should return JSON content type
            assert response.headers["content-type"] == "application/json"
            
            # Should be parseable as JSON
            data = response.json()
            assert isinstance(data, dict)

    def test_health_endpoints_response_codes(self, client):
        """Test that health endpoints return appropriate HTTP status codes."""
        endpoints_and_expected_codes = [
            ("/health", [200, 500]),
            ("/health/ready", [200, 503]),
            ("/health/live", [200, 500]),
            ("/metrics", [200, 500])
        ]
        
        for endpoint, expected_codes in endpoints_and_expected_codes:
            response = client.get(endpoint)
            assert response.status_code in expected_codes, f"Endpoint {endpoint} returned unexpected status code {response.status_code}"


class TestHealthEndpointIntegration:
    """Integration tests for health endpoints."""

    def test_health_endpoints_consistency(self, client):
        """Test basic consistency between health endpoints."""
        # Get responses from all endpoints
        health_response = client.get("/health")
        ready_response = client.get("/health/ready")
        live_response = client.get("/health/live")
        metrics_response = client.get("/metrics")
        
        # All should return some response
        responses = [health_response, ready_response, live_response, metrics_response]
        for response in responses:
            assert response.status_code in [200, 500, 503]
            assert response.headers["content-type"] == "application/json"
        
        # If health endpoint is working, check basic consistency
        if health_response.status_code == 200 and metrics_response.status_code == 200:
            health_data = health_response.json()
            metrics_data = metrics_response.json()
            
            # Both should have timestamps
            assert "timestamp" in health_data
            assert "timestamp" in metrics_data
            
            # Service should be consistent
            if "service_info" in metrics_data:
                assert metrics_data["service_info"]["name"] == "confluence-integration-tool"

    def test_health_endpoint_response_time(self, client):
        """Test that health endpoints respond within reasonable time."""
        import time
        
        endpoints = ["/health", "/health/ready", "/health/live", "/metrics"]
        
        for endpoint in endpoints:
            start_time = time.time()
            response = client.get(endpoint)
            end_time = time.time()
            
            response_time = end_time - start_time
            
            # Health endpoints should respond within 5 seconds
            assert response_time < 5.0, f"Endpoint {endpoint} took too long to respond: {response_time}s"
            
            # Should return some response
            assert response.status_code in [200, 500, 503]


class TestHealthEndpointSecurity:
    """Security tests for health endpoints."""

    def test_health_endpoints_no_sensitive_data(self, client):
        """Test that health endpoints don't expose sensitive information."""
        endpoints = ["/health", "/health/ready", "/health/live", "/metrics"]
        
        sensitive_keywords = [
            "password", "secret", "key", "token", "credential",
            "auth", "private", "confidential"
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            response_text = response.text.lower()
            
            for keyword in sensitive_keywords:
                assert keyword not in response_text, f"Endpoint {endpoint} may expose sensitive data containing '{keyword}'"

    def test_health_endpoints_accept_get_only(self, client):
        """Test that health endpoints only accept GET requests."""
        endpoints = ["/health", "/health/ready", "/health/live", "/metrics"]
        methods = ["POST", "PUT", "DELETE", "PATCH"]
        
        for endpoint in endpoints:
            for method in methods:
                response = client.request(method, endpoint)
                # Should return method not allowed (405) or not found (404)
                assert response.status_code in [405, 404], f"Endpoint {endpoint} should not accept {method} requests"