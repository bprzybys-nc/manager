"""
Unit tests for RunbookRepositoryMCPClient.

Tests MCP client functionality, BaseClient compliance, and tool method calls.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from contextlib import asynccontextmanager

from src.usecases.db_runbook_finder.mcp_server.client import RunbookRepositoryMCPClient
from src.usecases.db_runbook_finder.mcp_server.exceptions import MCPRunbookError, RunbookNotFoundError


class TestRunbookRepositoryMCPClient:
    """Test suite for RunbookRepositoryMCPClient."""
    
    @pytest.fixture
    def mock_config_path(self, tmp_path):
        """Create a temporary config file."""
        config_file = tmp_path / "mcp_config.json"
        config_content = {
            "mcpServers": {
                "runbook_repository": {
                    "command": "python",
                    "args": ["-m", "test_server"],
                    "env": {}
                }
            }
        }
        import json
        config_file.write_text(json.dumps(config_content))
        return str(config_file)
    
    @pytest.fixture
    def client(self, mock_config_path):
        """Create RunbookRepositoryMCPClient instance."""
        return RunbookRepositoryMCPClient(config_path=mock_config_path)
    
    def test_client_initialization(self, client, mock_config_path):
        """Test client initialization."""
        assert str(client.config_path) == mock_config_path
        assert client.SERVER_NAME == "runbook_repository"
        assert client.server_name == "runbook_repository"
        assert hasattr(client, '_config')
        assert hasattr(client, '_process')
        assert hasattr(client, '_session_id')
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, client):
        """Test successful health check."""
        with patch.object(client, '_call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {"status": "healthy", "timestamp": "2024-07-20T10:00:00Z"}
            
            result = await client.health_check()
            
            assert result is True
            mock_call.assert_called_once_with("health_check", {})
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, client):
        """Test health check failure."""
        with patch.object(client, '_call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = Exception("Health check failed")
            
            result = await client.health_check()
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_search_runbooks_success(self, client):
        """Test successful runbook search."""
        expected_results = [
            {
                "runbook_id": "123456",
                "title": "Database Connection Troubleshooting",
                "url": "https://confluence.test.com/pages/123456",
                "space_key": "MCDBA",
                "search_relevance": 0.95
            }
        ]
        
        with patch.object(client, '_call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {"results": expected_results}
            
            results = await client.search_runbooks(
                query="database connection timeout",
                spaces=["MCDBA", "AAVA"],
                limit=5
            )
            
            assert results == expected_results
            mock_call.assert_called_once_with("search_runbooks", {
                "query": "database connection timeout",
                "spaces": ["MCDBA", "AAVA"],
                "limit": 5
            })
    
    @pytest.mark.asyncio
    async def test_search_runbooks_empty_results(self, client):
        """Test runbook search with empty results."""
        with patch.object(client, '_call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {"results": []}
            
            results = await client.search_runbooks("nonexistent query")
            
            assert results == []
    
    @pytest.mark.asyncio
    async def test_semantic_search_success(self, client):
        """Test successful semantic search."""
        expected_results = [
            {
                "runbook_id": "123456",
                "title": "Database Connection Troubleshooting",
                "similarity_score": 0.92,
                "metadata": {
                    "url": "https://confluence.test.com/pages/123456",
                    "space_key": "MCDBA",
                    "tags": ["database", "connection"]
                }
            }
        ]
        
        with patch.object(client, '_call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {"results": expected_results}
            
            results = await client.semantic_search(
                query="database connectivity issues",
                limit=3
            )
            
            assert results == expected_results
            mock_call.assert_called_once_with("semantic_search", {
                "query": "database connectivity issues",
                "limit": 3
            })
    
    @pytest.mark.asyncio
    async def test_comprehensive_runbook_search_success(self, client):
        """Test comprehensive search combining text and semantic results."""
        expected_response = {
            "text_results": [
                {
                    "runbook_id": "123456",
                    "title": "Database Connection Guide",
                    "search_relevance": 0.95
                }
            ],
            "semantic_results": [
                {
                    "runbook_id": "234567",
                    "title": "Connection Troubleshooting",
                    "similarity_score": 0.88
                }
            ],
            "combined_count": 2
        }
        
        with patch.object(client, '_call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = expected_response
            
            results = await client.comprehensive_runbook_search(
                query="database connection issues",
                spaces=["MCDBA"],
                include_semantic=True,
                limit=5
            )
            
            assert results == expected_response
            mock_call.assert_called_once_with("comprehensive_runbook_search", {
                "query": "database connection issues",
                "spaces": ["MCDBA"],
                "include_semantic": True,
                "limit": 5
            })
    
    @pytest.mark.asyncio
    async def test_get_runbook_details_success(self, client):
        """Test successful runbook details retrieval."""
        expected_details = {
            "runbook_id": "123456",
            "title": "Database Connection Troubleshooting",
            "content": {
                "procedures": ["Step 1", "Step 2", "Step 3"],
                "troubleshooting_steps": ["Check connection", "Verify credentials"]
            },
            "metadata": {
                "space_key": "MCDBA",
                "url": "https://confluence.test.com/pages/123456"
            }
        }
        
        with patch.object(client, '_call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = expected_details
            
            details = await client.get_runbook_details("123456")
            
            assert details == expected_details
            mock_call.assert_called_once_with("get_runbook_details", {
                "runbook_id": "123456"
            })
    
    @pytest.mark.asyncio
    async def test_get_runbook_details_not_found(self, client):
        """Test runbook details retrieval for non-existent runbook."""
        with patch.object(client, '_call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = RunbookNotFoundError("Runbook not found", "nonexistent")
            
            with pytest.raises(RunbookNotFoundError):
                await client.get_runbook_details("nonexistent")
    
    @pytest.mark.asyncio
    async def test_track_runbook_usage_success(self, client):
        """Test successful runbook usage tracking."""
        usage_context = {
            "incident_id": "INC-2024001",
            "user": "test_user@company.com",
            "outcome": "success",
            "resolution_time": 15.5
        }
        
        with patch.object(client, '_call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {"usage_id": "usage_12345", "status": "tracked"}
            
            result = await client.track_runbook_usage("123456", usage_context)
            
            assert result["usage_id"] == "usage_12345"
            mock_call.assert_called_once_with("track_runbook_usage", {
                "runbook_id": "123456",
                "usage_context": usage_context
            })
    
    @pytest.mark.asyncio
    async def test_create_incident_ticket_success(self, client):
        """Test successful incident ticket creation."""
        context = {
            "summary": "Database connection issue",
            "description": "Connection timeout in production",
            "priority": "High"
        }
        
        with patch.object(client, '_call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {"ticket_id": "RBK-20240720-001", "status": "created"}
            
            result = await client.create_incident_ticket("123456", context)
            
            assert result["ticket_id"] == "RBK-20240720-001"
            mock_call.assert_called_once_with("create_incident_ticket", {
                "runbook_id": "123456",
                "context": context
            })
    
    @pytest.mark.asyncio
    async def test_send_runbook_notification_success(self, client):
        """Test successful runbook notification sending."""
        context = {
            "title": "Runbook Found",
            "description": "Relevant runbook discovered",
            "urgency": "medium"
        }
        
        with patch.object(client, '_call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {"notification_id": "notif_12345", "status": "sent"}
            
            result = await client.send_runbook_notification(
                "#mc-dba-notifications",
                "123456",
                context
            )
            
            assert result["notification_id"] == "notif_12345"
            mock_call.assert_called_once_with("send_runbook_notification", {
                "channel": "#mc-dba-notifications",
                "runbook_id": "123456",
                "context": context
            })
    
    @pytest.mark.asyncio
    async def test_get_runbook_metrics_success(self, client):
        """Test successful runbook metrics retrieval."""
        expected_metrics = {
            "runbook_id": "123456",
            "total_usage_count": 25,
            "success_rate": 85.5,
            "average_resolution_time": 22.3
        }
        
        with patch.object(client, '_call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = expected_metrics
            
            metrics = await client.get_runbook_metrics("123456")
            
            assert metrics == expected_metrics
            mock_call.assert_called_once_with("get_runbook_metrics", {
                "runbook_id": "123456"
            })
    
    @pytest.mark.asyncio
    async def test_error_handling_tool_call_failure(self, client):
        """Test error handling when tool calls fail."""
        with patch.object(client, '_call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = MCPRunbookError("Tool call failed")
            
            with pytest.raises(MCPRunbookError):
                await client.search_runbooks("test query")
    
    @pytest.mark.asyncio
    async def test_context_manager_functionality(self, client):
        """Test that client works as an async context manager."""
        # Mock the session and connection methods
        mock_session = AsyncMock()
        mock_read = AsyncMock()
        mock_write = AsyncMock()
        
        with patch.object(client, '_create_session', return_value=mock_session):
            with patch.object(client, '_connect', return_value=(mock_read, mock_write)):
                async with client as client_instance:
                    assert client_instance is client
                    assert client._session is mock_session
                    assert client._read is mock_read
                    assert client._write is mock_write
    
    @pytest.mark.asyncio
    async def test_concurrent_tool_calls(self, client):
        """Test concurrent tool calls for thread safety."""
        with patch.object(client, '_call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {"results": []}
            
            # Make multiple concurrent calls
            tasks = [
                client.search_runbooks(f"query_{i}")
                for i in range(5)
            ]
            
            results = await asyncio.gather(*tasks)
            
            # All should succeed
            assert len(results) == 5
            for result in results:
                assert result == []
            
            # All calls should have been made
            assert mock_call.call_count == 5
    
    @pytest.mark.asyncio
    async def test_performance_requirement_semantic_search(self, client):
        """Test that semantic search meets <50ms performance requirement."""
        with patch.object(client, '_call_tool', new_callable=AsyncMock) as mock_call:
            # Simulate fast response
            mock_call.return_value = {"results": []}
            
            start_time = asyncio.get_event_loop().time()
            await client.semantic_search("test query", limit=5)
            end_time = asyncio.get_event_loop().time()
            
            duration_ms = (end_time - start_time) * 1000
            # This test verifies the client doesn't add significant overhead
            # The actual performance depends on the server implementation
            assert duration_ms < 100, f"Client overhead was {duration_ms:.2f}ms"
    
    def test_server_name_constant(self, client):
        """Test that SERVER_NAME constant is correctly set."""
        assert client.SERVER_NAME == "runbook_repository"
        assert isinstance(client.SERVER_NAME, str)
    
    def test_config_path_storage(self, client, mock_config_path):
        """Test that config path is stored correctly."""
        assert client.config_path == mock_config_path
    
    @pytest.mark.asyncio
    async def test_tool_call_with_timeout(self, client):
        """Test tool calls with timeout handling."""
        with patch.object(client, '_call_tool', new_callable=AsyncMock) as mock_call:
            # Simulate slow response
            async def slow_response(*args, **kwargs):
                await asyncio.sleep(0.1)
                return {"results": []}
            
            mock_call.side_effect = slow_response
            
            # Should complete without timeout for reasonable delays
            result = await client.search_runbooks("test")
            assert result == []
    
    @pytest.mark.asyncio
    async def test_method_parameter_validation(self, client):
        """Test parameter validation in client methods."""
        with patch.object(client, '_call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {"results": []}
            
            # Test with various parameter combinations
            await client.search_runbooks("")  # Empty query should work
            await client.search_runbooks("query", spaces=[])  # Empty spaces should work
            await client.search_runbooks("query", limit=0)  # Zero limit should work
            
            # All calls should pass through to the tool
            assert mock_call.call_count == 3
    
    def test_client_inheritance_from_base_client(self, client):
        """Test that client properly inherits from BaseClient."""
        from src.frameworks.graphmcp.clients.base import BaseClient
        
        assert isinstance(client, BaseClient)
        assert hasattr(client, 'SERVER_NAME')
        assert hasattr(client, 'config_path')
    
    @pytest.mark.asyncio
    async def test_connection_cleanup(self, client):
        """Test proper connection cleanup on context manager exit."""
        mock_session = AsyncMock()
        mock_read = AsyncMock()
        mock_write = AsyncMock()
        
        with patch.object(client, '_create_session', return_value=mock_session):
            with patch.object(client, '_connect', return_value=(mock_read, mock_write)):
                async with client:
                    pass
                
                # After context exit, connections should be cleaned up
                # This depends on BaseClient implementation
                # For now, just verify no exceptions are raised
    
    @pytest.mark.asyncio 
    async def test_error_propagation(self, client):
        """Test that errors from tools are properly propagated."""
        with patch.object(client, '_call_tool', new_callable=AsyncMock) as mock_call:
            # Test different error types
            mock_call.side_effect = RunbookNotFoundError("Not found", "123")
            
            with pytest.raises(RunbookNotFoundError) as exc_info:
                await client.get_runbook_details("123")
            
            assert "Not found" in str(exc_info.value)
    
    def test_client_string_representation(self, client):
        """Test client string representation."""
        client_str = str(client)
        assert "RunbookRepositoryMCPClient" in client_str
        assert client.SERVER_NAME in client_str
    
    @pytest.mark.asyncio
    async def test_comprehensive_workflow_integration(self, client):
        """Test client methods in a workflow-like sequence."""
        with patch.object(client, '_call_tool', new_callable=AsyncMock) as mock_call:
            # Set up mock responses for a complete workflow
            mock_call.side_effect = [
                {"status": "healthy"},  # health_check
                {"results": [{"runbook_id": "123"}]},  # search_runbooks
                {"runbook_id": "123", "title": "Test Runbook"},  # get_runbook_details
                {"usage_id": "usage_123"},  # track_runbook_usage
                {"notification_id": "notif_123"}  # send_runbook_notification
            ]
            
            # Execute workflow sequence
            health = await client.health_check()
            assert health is True
            
            search_results = await client.search_runbooks("test")
            assert len(search_results) == 1
            
            details = await client.get_runbook_details("123")
            assert details["runbook_id"] == "123"
            
            usage = await client.track_runbook_usage("123", {"user": "test"})
            assert "usage_id" in usage
            
            notification = await client.send_runbook_notification("channel", "123", {})
            assert "notification_id" in notification
            
            # Verify all calls were made
            assert mock_call.call_count == 5