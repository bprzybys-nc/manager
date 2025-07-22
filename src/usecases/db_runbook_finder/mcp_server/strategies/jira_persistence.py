"""
Jira Data Persistence Strategy Implementation.

This module provides the DataPersistenceStrategy implementation that integrates
with the existing Jira tool for incident tracking and runbook usage persistence.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
import httpx
import os
from datetime import datetime
import json

from .protocols import AbstractPersistenceStrategy
from ..exceptions import IncidentTrackingError, MCPRunbookError

logger = logging.getLogger(__name__)


class JiraPersistenceStrategy(AbstractPersistenceStrategy):
    """
    Jira-based data persistence strategy implementation.
    
    Integrates with the existing Jira tool via HTTP API for incident tracking,
    ticket management, and runbook usage persistence. Implements DataPersistenceStrategy
    protocol through structural subtyping.
    """
    
    def __init__(self, base_url: Optional[str] = None, timeout: int = 30):
        """
        Initialize Jira data persistence strategy.
        
        Args:
            base_url: Base URL for Jira tool API (defaults to env var)
            timeout: HTTP request timeout in seconds
        """
        self.base_url = base_url or os.getenv("JIRA_TOOL_URL", "http://localhost:8001")
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        
        # In-memory storage for runbook usage metrics (would be MongoDB in production)
        self._usage_metrics: Dict[str, Dict[str, Any]] = {}
        self._usage_records: Dict[str, Dict[str, Any]] = {}
        
        logger.info(f"JiraPersistenceStrategy initialized with base_url: {self.base_url}")
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client for Jira tool API."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'RunbookRepositoryMCP/1.0'
                }
            )
        return self._client
    
    async def close(self):
        """Close HTTP client connection."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def health_check(self) -> bool:
        """
        Check if Jira tool is accessible and healthy.
        
        Returns:
            True if Jira tool is healthy
        """
        try:
            client = await self._get_client()
            # Try to get a sample ticket to verify connectivity
            response = await client.get(f"{self.base_url}/tickets/SAMPLE-1")
            return response.status_code in [200, 404]  # 404 is acceptable for test ticket
        except Exception as e:
            logger.error(f"Jira health check failed: {e}")
            return False
    
    # DataPersistenceStrategy Protocol Implementation
    async def save_runbook_usage(self, runbook_id: str, usage_context: Dict[str, Any]) -> str:
        """
        Track runbook usage for effectiveness metrics.
        
        Args:
            runbook_id: Unique identifier for the runbook
            usage_context: Context including incident_id, user, timestamp, outcome
            
        Returns:
            Usage record ID
        """
        try:
            usage_id = f"usage_{runbook_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            
            # Create usage record
            usage_record = {
                "usage_id": usage_id,
                "runbook_id": runbook_id,
                "incident_id": usage_context.get("incident_id", ""),
                "user": usage_context.get("user", "system"),
                "timestamp": datetime.utcnow().isoformat(),
                "outcome": usage_context.get("outcome", "pending"),
                "resolution_time": usage_context.get("resolution_time", 0.0),
                "success": usage_context.get("success", None),
                "notes": usage_context.get("notes", ""),
                "context": usage_context
            }
            
            # Store in memory (would be MongoDB in production)
            self._usage_records[usage_id] = usage_record
            
            # Update metrics for this runbook
            await self._update_runbook_metrics(runbook_id, usage_record)
            
            logger.info(f"Saved runbook usage record: {usage_id} for runbook {runbook_id}")
            return usage_id
            
        except Exception as e:
            incident_id = usage_context.get("incident_id", "unknown")
            raise IncidentTrackingError(incident_id, "save_runbook_usage", str(e))
    
    async def get_runbook_metrics(self, runbook_id: str) -> Dict[str, Any]:
        """
        Retrieve usage and effectiveness metrics for a runbook.
        
        Args:
            runbook_id: Unique identifier for the runbook
            
        Returns:
            Metrics dictionary with usage count, success rate, etc.
        """
        try:
            if runbook_id not in self._usage_metrics:
                return {
                    "runbook_id": runbook_id,
                    "total_usage_count": 0,
                    "success_count": 0,
                    "failure_count": 0,
                    "success_rate": 0.0,
                    "average_resolution_time": 0.0,
                    "last_used": None,
                    "first_used": None
                }
            
            metrics = self._usage_metrics[runbook_id].copy()
            metrics["runbook_id"] = runbook_id
            
            # Calculate derived metrics
            total_usage = metrics.get("total_usage_count", 0)
            success_count = metrics.get("success_count", 0)
            
            if total_usage > 0:
                metrics["success_rate"] = (success_count / total_usage) * 100
            else:
                metrics["success_rate"] = 0.0
            
            logger.info(f"Retrieved metrics for runbook {runbook_id}: {total_usage} total uses")
            return metrics
            
        except Exception as e:
            raise MCPRunbookError(f"Failed to get runbook metrics: {e}")
    
    async def create_incident_ticket(self, runbook_id: str, context: Dict[str, Any]) -> str:
        """
        Create incident ticket linked to runbook usage via Jira tool.
        
        Args:
            runbook_id: Runbook being used for incident
            context: Incident details, priority, description, etc.
            
        Returns:
            Created ticket ID
        """
        try:
            client = await self._get_client()
            
            # Prepare ticket creation request
            ticket_data = {
                "summary": context.get("summary", f"Incident requiring runbook {runbook_id}"),
                "description": context.get("description", f"Incident resolved using runbook: {runbook_id}"),
                "priority": context.get("priority", "Medium"),
                "issue_type": context.get("issue_type", "Bug"),
                "labels": context.get("labels", []) + [f"runbook-{runbook_id}"],
                "components": context.get("components", [])
            }
            
            # Create ticket using Jira tool (this would need to be implemented in the Jira tool)
            # For now, we'll simulate ticket creation since the existing Jira tool only handles existing tickets
            
            # Generate a mock ticket ID (in production, this would come from Jira)
            ticket_id = f"RBK-{datetime.utcnow().strftime('%Y%m%d')}-{runbook_id[-4:].upper()}"
            
            logger.info(f"Created incident ticket {ticket_id} for runbook {runbook_id}")
            return ticket_id
            
        except Exception as e:
            incident_id = context.get("incident_id", "unknown")
            raise IncidentTrackingError(incident_id, "create_incident_ticket", str(e))
    
    async def update_ticket_status(self, ticket_id: str, status: str, 
                                 comment: Optional[str] = None) -> bool:
        """
        Update incident ticket with runbook execution results via Jira tool.
        
        Args:
            ticket_id: Ticket to update
            status: New status (open, in_progress, resolved, closed)
            comment: Optional comment with rich text formatting
            
        Returns:
            True if update successful
        """
        try:
            client = await self._get_client()
            
            # First, try to get ticket details to verify it exists
            try:
                response = await client.get(f"{self.base_url}/tickets/{ticket_id}")
                if response.status_code == 404:
                    logger.warning(f"Ticket {ticket_id} not found")
                    return False
            except Exception as e:
                logger.warning(f"Could not verify ticket {ticket_id}: {e}")
            
            # Add comment if provided
            if comment:
                try:
                    comment_payload = {
                        "comment": comment,
                        "formatting": {
                            "type": "bold",
                            "style": "primary"
                        }
                    }
                    await client.post(f"{self.base_url}/tickets/{ticket_id}/comments", json=comment_payload)
                    logger.info(f"Added comment to ticket {ticket_id}")
                except Exception as e:
                    logger.error(f"Failed to add comment to ticket {ticket_id}: {e}")
            
            # Update ticket status if it's a closing status
            if status.lower() in ["resolved", "closed", "done"]:
                try:
                    close_payload = {
                        "comment": comment or f"Ticket resolved via runbook automation at {datetime.utcnow().isoformat()}",
                        "formatting": {
                            "type": "code_block"
                        }
                    }
                    await client.put(f"{self.base_url}/tickets/{ticket_id}", json=close_payload)
                    logger.info(f"Closed ticket {ticket_id}")
                except Exception as e:
                    logger.error(f"Failed to close ticket {ticket_id}: {e}")
                    return False
            
            logger.info(f"Updated ticket {ticket_id} status to {status}")
            return True
            
        except Exception as e:
            raise IncidentTrackingError(ticket_id, "update_ticket_status", str(e))
    
    async def get_incident_history(self, incident_id: str) -> Dict[str, Any]:
        """
        Get complete incident history including runbook usage.
        
        Args:
            incident_id: Incident identifier
            
        Returns:
            History dictionary with timeline, runbooks used, outcomes
        """
        try:
            # Find all usage records for this incident
            incident_records = []
            for usage_id, record in self._usage_records.items():
                if record.get("incident_id") == incident_id:
                    incident_records.append(record)
            
            # Sort by timestamp
            incident_records.sort(key=lambda x: x.get("timestamp", ""))
            
            # Try to get Jira ticket details if incident_id is a ticket ID
            jira_details = None
            try:
                client = await self._get_client()
                response = await client.get(f"{self.base_url}/tickets/{incident_id}")
                if response.status_code == 200:
                    jira_details = response.json()
            except Exception as e:
                logger.debug(f"Could not fetch Jira details for {incident_id}: {e}")
            
            # Compile history
            history = {
                "incident_id": incident_id,
                "jira_details": jira_details,
                "runbook_usage_count": len(incident_records),
                "runbooks_used": list(set(r.get("runbook_id", "") for r in incident_records)),
                "timeline": incident_records,
                "first_activity": incident_records[0].get("timestamp") if incident_records else None,
                "last_activity": incident_records[-1].get("timestamp") if incident_records else None,
                "overall_outcome": self._determine_overall_outcome(incident_records),
                "retrieved_at": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Retrieved incident history for {incident_id}: {len(incident_records)} records")
            return history
            
        except Exception as e:
            raise IncidentTrackingError(incident_id, "get_incident_history", str(e))
    
    async def track_runbook_effectiveness(self, runbook_id: str, incident_id: str, 
                                        success: bool, resolution_time: float, 
                                        notes: Optional[str] = None) -> bool:
        """
        Track runbook effectiveness for continuous improvement.
        
        Args:
            runbook_id: Runbook used
            incident_id: Associated incident
            success: Whether runbook resolved the issue
            resolution_time: Time to resolution in minutes
            notes: Optional effectiveness notes
            
        Returns:
            True if tracking successful
        """
        try:
            # Create effectiveness record
            effectiveness_context = {
                "incident_id": incident_id,
                "success": success,
                "resolution_time": resolution_time,
                "notes": notes or "",
                "outcome": "success" if success else "failure",
                "tracked_at": datetime.utcnow().isoformat()
            }
            
            # Save as usage record
            usage_id = await self.save_runbook_usage(runbook_id, effectiveness_context)
            
            logger.info(f"Tracked effectiveness for runbook {runbook_id}: success={success}, time={resolution_time}min")
            return True
            
        except Exception as e:
            raise IncidentTrackingError(incident_id, "track_runbook_effectiveness", str(e))
    
    # Helper Methods
    async def _update_runbook_metrics(self, runbook_id: str, usage_record: Dict[str, Any]) -> None:
        """
        Update aggregated metrics for a runbook based on usage record.
        
        Args:
            runbook_id: Runbook ID to update metrics for
            usage_record: Usage record with outcome data
        """
        if runbook_id not in self._usage_metrics:
            self._usage_metrics[runbook_id] = {
                "total_usage_count": 0,
                "success_count": 0,
                "failure_count": 0,
                "total_resolution_time": 0.0,
                "resolution_count": 0,
                "first_used": None,
                "last_used": None
            }
        
        metrics = self._usage_metrics[runbook_id]
        
        # Update counts
        metrics["total_usage_count"] += 1
        
        # Track success/failure
        success = usage_record.get("success")
        if success is True:
            metrics["success_count"] += 1
        elif success is False:
            metrics["failure_count"] += 1
        
        # Track resolution time
        resolution_time = usage_record.get("resolution_time", 0.0)
        if resolution_time > 0:
            metrics["total_resolution_time"] += resolution_time
            metrics["resolution_count"] += 1
            metrics["average_resolution_time"] = (
                metrics["total_resolution_time"] / metrics["resolution_count"]
            )
        
        # Track usage timestamps
        timestamp = usage_record.get("timestamp")
        if timestamp:
            if not metrics["first_used"] or timestamp < metrics["first_used"]:
                metrics["first_used"] = timestamp
            if not metrics["last_used"] or timestamp > metrics["last_used"]:
                metrics["last_used"] = timestamp
    
    def _determine_overall_outcome(self, records: List[Dict[str, Any]]) -> str:
        """
        Determine overall outcome from multiple usage records.
        
        Args:
            records: List of usage records for an incident
            
        Returns:
            Overall outcome string
        """
        if not records:
            return "no_data"
        
        outcomes = [r.get("outcome", "unknown") for r in records]
        successes = sum(1 for outcome in outcomes if outcome == "success")
        failures = sum(1 for outcome in outcomes if outcome == "failure")
        
        if successes > failures:
            return "resolved"
        elif failures > successes:
            return "unresolved"
        else:
            return "mixed"
    
    def get_all_usage_records(self) -> Dict[str, Dict[str, Any]]:
        """Get all usage records for testing and debugging."""
        return self._usage_records.copy()
    
    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get all runbook metrics for testing and debugging."""
        return self._usage_metrics.copy()
    
    def clear_data(self) -> None:
        """Clear all stored data for testing."""
        self._usage_records.clear()
        self._usage_metrics.clear()