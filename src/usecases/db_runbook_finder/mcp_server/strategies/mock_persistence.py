"""
Mock Data Persistence Strategy Implementation.

This module provides a mock implementation of DataPersistenceStrategy using
in-memory storage for development and testing purposes.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import random
import uuid

from .protocols import DataPersistenceStrategy
from ..exceptions import IncidentTrackingError, MCPRunbookError

logger = logging.getLogger(__name__)


class MockDataStrategy:
    """
    Mock data persistence strategy implementation.
    
    Uses in-memory storage to simulate incident tracking, runbook usage metrics,
    and ticket management. Implements DataPersistenceStrategy protocol through
    structural subtyping.
    """
    
    def __init__(self):
        """Initialize mock data strategy with in-memory storage."""
        # In-memory storage for mock data
        self._usage_records: Dict[str, Dict[str, Any]] = {}
        self._usage_metrics: Dict[str, Dict[str, Any]] = {}
        self._incident_tickets: Dict[str, Dict[str, Any]] = {}
        self._incident_history: Dict[str, Dict[str, Any]] = {}
        
        # Initialize with some mock data
        self._initialize_mock_data()
        
        logger.info(f"MockDataStrategy initialized with mock data")
    
    def _initialize_mock_data(self) -> None:
        """Initialize with some mock usage data and metrics."""
        try:
            # Mock runbook IDs (matching test data)
            mock_runbook_ids = [
                "123456",  # Database Connection Troubleshooting
                "234567",  # Performance Monitoring
                "345678",  # Backup Recovery
                "456789",  # Security Hardening
                "567890"   # Migration
            ]
            
            # Generate mock usage records
            for i, runbook_id in enumerate(mock_runbook_ids):
                # Create multiple usage records per runbook
                for j in range(random.randint(3, 8)):
                    usage_id = f"usage_{runbook_id}_{i}_{j}"
                    incident_id = f"INC-{2024000 + (i * 10) + j}"
                    
                    # Vary the timestamps over the last 30 days
                    days_ago = random.randint(0, 30)
                    timestamp = (datetime.utcnow() - timedelta(days=days_ago)).isoformat()
                    
                    usage_record = {
                        "usage_id": usage_id,
                        "runbook_id": runbook_id,
                        "incident_id": incident_id,
                        "user": f"user_{i}@company.com",
                        "timestamp": timestamp,
                        "outcome": random.choice(["success", "failure", "partial"]),
                        "resolution_time": random.uniform(5.0, 120.0),  # 5 to 120 minutes
                        "success": random.choice([True, False, None]),
                        "notes": f"Mock usage record {j} for runbook {runbook_id}",
                        "context": {
                            "incident_type": random.choice(["database_down", "performance_issue", "security_breach", "backup_failure"]),
                            "severity": random.choice(["low", "medium", "high", "critical"]),
                            "environment": random.choice(["production", "staging", "development"])
                        }
                    }
                    
                    self._usage_records[usage_id] = usage_record
                
                # Generate aggregated metrics for each runbook
                runbook_records = [r for r in self._usage_records.values() if r["runbook_id"] == runbook_id]
                success_count = len([r for r in runbook_records if r.get("success") is True])
                failure_count = len([r for r in runbook_records if r.get("success") is False])
                total_resolution_time = sum(r.get("resolution_time", 0) for r in runbook_records if r.get("resolution_time"))
                resolution_count = len([r for r in runbook_records if r.get("resolution_time")])
                
                timestamps = [r["timestamp"] for r in runbook_records]
                timestamps.sort()
                
                self._usage_metrics[runbook_id] = {
                    "total_usage_count": len(runbook_records),
                    "success_count": success_count,
                    "failure_count": failure_count,
                    "total_resolution_time": total_resolution_time,
                    "resolution_count": resolution_count,
                    "average_resolution_time": total_resolution_time / resolution_count if resolution_count > 0 else 0.0,
                    "first_used": timestamps[0] if timestamps else None,
                    "last_used": timestamps[-1] if timestamps else None
                }
            
            # Generate mock incident tickets
            for i, runbook_id in enumerate(mock_runbook_ids[:3]):  # Only for first 3
                ticket_id = f"RBK-{datetime.utcnow().strftime('%Y%m%d')}-{runbook_id[-4:].upper()}"
                
                self._incident_tickets[ticket_id] = {
                    "ticket_id": ticket_id,
                    "runbook_id": runbook_id,
                    "summary": f"Incident requiring runbook {runbook_id}",
                    "description": f"Mock incident resolved using runbook: {runbook_id}",
                    "status": random.choice(["open", "in_progress", "resolved", "closed"]),
                    "priority": random.choice(["Low", "Medium", "High", "Critical"]),
                    "created_at": (datetime.utcnow() - timedelta(days=random.randint(1, 7))).isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                    "comments": [
                        {
                            "comment": f"Ticket created for runbook {runbook_id}",
                            "timestamp": (datetime.utcnow() - timedelta(days=random.randint(1, 5))).isoformat()
                        },
                        {
                            "comment": f"Runbook execution completed with mock results",
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    ]
                }
                
                # Create incident history
                incident_id = f"INC-{2024000 + i}"
                incident_records = [r for r in self._usage_records.values() if r["incident_id"] == incident_id]
                
                if incident_records:
                    self._incident_history[incident_id] = {
                        "incident_id": incident_id,
                        "ticket_id": ticket_id,
                        "runbook_usage_count": len(incident_records),
                        "runbooks_used": list(set(r["runbook_id"] for r in incident_records)),
                        "timeline": incident_records,
                        "first_activity": min(r["timestamp"] for r in incident_records),
                        "last_activity": max(r["timestamp"] for r in incident_records),
                        "overall_outcome": self._determine_overall_outcome(incident_records),
                        "created_at": datetime.utcnow().isoformat()
                    }
            
            logger.info(f"Initialized mock data: {len(self._usage_records)} usage records, "
                       f"{len(self._usage_metrics)} metrics, {len(self._incident_tickets)} tickets")
                       
        except Exception as e:
            logger.warning(f"Could not initialize full mock data: {e}")
            # Minimal fallback data
            self._usage_records = {}
            self._usage_metrics = {}
            self._incident_tickets = {}
            self._incident_history = {}
    
    def _determine_overall_outcome(self, records: List[Dict[str, Any]]) -> str:
        """Determine overall outcome from multiple usage records."""
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
    
    async def health_check(self) -> bool:
        """
        Mock health check - always returns True.
        
        Returns:
            True (mock implementation is always healthy)
        """
        return True
    
    # DataPersistenceStrategy Protocol Implementation
    async def save_runbook_usage(self, runbook_id: str, usage_context: Dict[str, Any]) -> str:
        """
        Track mock runbook usage for effectiveness metrics.
        
        Args:
            runbook_id: Unique identifier for the runbook
            usage_context: Context including incident_id, user, timestamp, outcome
            
        Returns:
            Mock usage record ID
        """
        try:
            # Simulate some processing time
            await asyncio.sleep(0.01)
            
            usage_id = f"usage_{runbook_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{random.randint(1000, 9999)}"
            
            # Create usage record
            usage_record = {
                "usage_id": usage_id,
                "runbook_id": runbook_id,
                "incident_id": usage_context.get("incident_id", f"INC-{random.randint(100000, 999999)}"),
                "user": usage_context.get("user", "mock_user@company.com"),
                "timestamp": datetime.utcnow().isoformat(),
                "outcome": usage_context.get("outcome", "success"),
                "resolution_time": usage_context.get("resolution_time", random.uniform(10.0, 60.0)),
                "success": usage_context.get("success", True),
                "notes": usage_context.get("notes", f"Mock usage tracking for {runbook_id}"),
                "context": usage_context.copy(),
                "source": "mock"
            }
            
            # Store in memory
            self._usage_records[usage_id] = usage_record
            
            # Update metrics for this runbook
            await self._update_runbook_metrics(runbook_id, usage_record)
            
            logger.info(f"Mock saved runbook usage record: {usage_id} for runbook {runbook_id}")
            return usage_id
            
        except Exception as e:
            incident_id = usage_context.get("incident_id", "unknown")
            logger.error(f"Mock failed to save runbook usage: {e}")
            raise IncidentTrackingError(incident_id, "save_runbook_usage", str(e))
    
    async def get_runbook_metrics(self, runbook_id: str) -> Dict[str, Any]:
        """
        Retrieve mock usage and effectiveness metrics for a runbook.
        
        Args:
            runbook_id: Unique identifier for the runbook
            
        Returns:
            Mock metrics dictionary with usage count, success rate, etc.
        """
        try:
            # Simulate some processing time
            await asyncio.sleep(0.01)
            
            if runbook_id not in self._usage_metrics:
                return {
                    "runbook_id": runbook_id,
                    "total_usage_count": 0,
                    "success_count": 0,
                    "failure_count": 0,
                    "success_rate": 0.0,
                    "average_resolution_time": 0.0,
                    "last_used": None,
                    "first_used": None,
                    "source": "mock"
                }
            
            metrics = self._usage_metrics[runbook_id].copy()
            metrics["runbook_id"] = runbook_id
            metrics["source"] = "mock"
            
            # Calculate derived metrics
            total_usage = metrics.get("total_usage_count", 0)
            success_count = metrics.get("success_count", 0)
            
            if total_usage > 0:
                metrics["success_rate"] = (success_count / total_usage) * 100
            else:
                metrics["success_rate"] = 0.0
            
            logger.info(f"Mock retrieved metrics for runbook {runbook_id}: {total_usage} total uses")
            return metrics
            
        except Exception as e:
            logger.error(f"Mock failed to get runbook metrics: {e}")
            raise MCPRunbookError(f"Failed to get runbook metrics: {e}")
    
    async def create_incident_ticket(self, runbook_id: str, context: Dict[str, Any]) -> str:
        """
        Create mock incident ticket linked to runbook usage.
        
        Args:
            runbook_id: Runbook being used for incident
            context: Incident details, priority, description, etc.
            
        Returns:
            Mock created ticket ID
        """
        try:
            # Simulate some processing time
            await asyncio.sleep(0.02)
            
            # Generate a mock ticket ID
            ticket_id = f"RBK-{datetime.utcnow().strftime('%Y%m%d')}-{runbook_id[-4:].upper()}{random.randint(10, 99)}"
            
            # Create mock ticket
            ticket = {
                "ticket_id": ticket_id,
                "runbook_id": runbook_id,
                "summary": context.get("summary", f"Mock incident requiring runbook {runbook_id}"),
                "description": context.get("description", f"Mock incident resolved using runbook: {runbook_id}"),
                "priority": context.get("priority", "Medium"),
                "issue_type": context.get("issue_type", "Bug"),
                "status": "Open",
                "labels": context.get("labels", []) + [f"runbook-{runbook_id}", "mock"],
                "components": context.get("components", []),
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "comments": [
                    {
                        "comment": f"Mock ticket created for runbook {runbook_id}",
                        "timestamp": datetime.utcnow().isoformat(),
                        "author": "mock_system"
                    }
                ],
                "source": "mock"
            }
            
            self._incident_tickets[ticket_id] = ticket
            
            logger.info(f"Mock created incident ticket {ticket_id} for runbook {runbook_id}")
            return ticket_id
            
        except Exception as e:
            incident_id = context.get("incident_id", "unknown")
            logger.error(f"Mock failed to create incident ticket: {e}")
            raise IncidentTrackingError(incident_id, "create_incident_ticket", str(e))
    
    async def update_ticket_status(self, ticket_id: str, status: str, 
                                 comment: Optional[str] = None) -> bool:
        """
        Update mock incident ticket with runbook execution results.
        
        Args:
            ticket_id: Ticket to update
            status: New status (open, in_progress, resolved, closed)
            comment: Optional comment with rich text formatting
            
        Returns:
            True if update successful
        """
        try:
            # Simulate some processing time
            await asyncio.sleep(0.02)
            
            if ticket_id not in self._incident_tickets:
                # Create a mock ticket if it doesn't exist
                self._incident_tickets[ticket_id] = {
                    "ticket_id": ticket_id,
                    "runbook_id": "unknown",
                    "summary": f"Mock ticket {ticket_id}",
                    "description": f"Mock ticket created during status update",
                    "priority": "Medium",
                    "status": "Open",
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                    "comments": [],
                    "source": "mock_auto_created"
                }
                logger.warning(f"Mock auto-created ticket {ticket_id}")
            
            ticket = self._incident_tickets[ticket_id]
            
            # Update ticket status
            ticket["status"] = status
            ticket["updated_at"] = datetime.utcnow().isoformat()
            
            # Add comment if provided
            if comment:
                ticket["comments"].append({
                    "comment": comment,
                    "timestamp": datetime.utcnow().isoformat(),
                    "author": "mock_runbook_system",
                    "formatting": "bold"  # Mock formatting
                })
                
                logger.info(f"Mock added comment to ticket {ticket_id}")
            
            # Add status change comment
            ticket["comments"].append({
                "comment": f"Mock ticket status updated to {status} via runbook automation",
                "timestamp": datetime.utcnow().isoformat(),
                "author": "mock_automation",
                "formatting": "code_block"
            })
            
            logger.info(f"Mock updated ticket {ticket_id} status to {status}")
            return True
            
        except Exception as e:
            logger.error(f"Mock failed to update ticket status: {e}")
            raise IncidentTrackingError(ticket_id, "update_ticket_status", str(e))
    
    async def get_incident_history(self, incident_id: str) -> Dict[str, Any]:
        """
        Get mock complete incident history including runbook usage.
        
        Args:
            incident_id: Incident identifier
            
        Returns:
            Mock history dictionary with timeline, runbooks used, outcomes
        """
        try:
            # Simulate some processing time
            await asyncio.sleep(0.02)
            
            # Find all usage records for this incident
            incident_records = []
            for usage_id, record in self._usage_records.items():
                if record.get("incident_id") == incident_id:
                    incident_records.append(record)
            
            # Sort by timestamp
            incident_records.sort(key=lambda x: x.get("timestamp", ""))
            
            # Try to find associated ticket
            associated_ticket = None
            for ticket_id, ticket in self._incident_tickets.items():
                if incident_id in ticket.get("description", "") or incident_id in ticket.get("summary", ""):
                    associated_ticket = ticket
                    break
            
            # If we have pre-stored incident history, use it, otherwise generate
            if incident_id in self._incident_history:
                history = self._incident_history[incident_id].copy()
            else:
                history = {
                    "incident_id": incident_id,
                    "runbook_usage_count": len(incident_records),
                    "runbooks_used": list(set(r.get("runbook_id", "") for r in incident_records)),
                    "timeline": incident_records,
                    "first_activity": incident_records[0].get("timestamp") if incident_records else None,
                    "last_activity": incident_records[-1].get("timestamp") if incident_records else None,
                    "overall_outcome": self._determine_overall_outcome(incident_records),
                    "created_at": datetime.utcnow().isoformat()
                }
            
            # Add ticket details
            history["associated_ticket"] = associated_ticket
            history["retrieved_at"] = datetime.utcnow().isoformat()
            history["source"] = "mock"
            
            logger.info(f"Mock retrieved incident history for {incident_id}: {len(incident_records)} records")
            return history
            
        except Exception as e:
            logger.error(f"Mock failed to get incident history: {e}")
            raise IncidentTrackingError(incident_id, "get_incident_history", str(e))
    
    async def track_runbook_effectiveness(self, runbook_id: str, incident_id: str, 
                                        success: bool, resolution_time: float, 
                                        notes: Optional[str] = None) -> bool:
        """
        Track mock runbook effectiveness for continuous improvement.
        
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
                "notes": notes or f"Mock effectiveness tracking for {runbook_id}",
                "outcome": "success" if success else "failure",
                "tracked_at": datetime.utcnow().isoformat(),
                "user": "mock_effectiveness_tracker",
                "source": "mock_effectiveness"
            }
            
            # Save as usage record
            usage_id = await self.save_runbook_usage(runbook_id, effectiveness_context)
            
            logger.info(f"Mock tracked effectiveness for runbook {runbook_id}: success={success}, time={resolution_time}min")
            return True
            
        except Exception as e:
            logger.error(f"Mock failed to track effectiveness: {e}")
            raise IncidentTrackingError(incident_id, "track_runbook_effectiveness", str(e))
    
    # Helper Methods
    async def _update_runbook_metrics(self, runbook_id: str, usage_record: Dict[str, Any]) -> None:
        """Update aggregated metrics for a runbook based on usage record."""
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
    
    # Additional Mock-specific Methods
    def get_all_usage_records(self) -> Dict[str, Dict[str, Any]]:
        """Get all usage records for testing and debugging."""
        return self._usage_records.copy()
    
    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get all runbook metrics for testing and debugging."""
        return self._usage_metrics.copy()
    
    def get_all_tickets(self) -> Dict[str, Dict[str, Any]]:
        """Get all incident tickets for testing and debugging."""
        return self._incident_tickets.copy()
    
    def get_all_incident_history(self) -> Dict[str, Dict[str, Any]]:
        """Get all incident history for testing and debugging."""
        return self._incident_history.copy()
    
    def clear_data(self) -> None:
        """Clear all stored data and reinitialize."""
        self._usage_records.clear()
        self._usage_metrics.clear()
        self._incident_tickets.clear()
        self._incident_history.clear()
        self._initialize_mock_data()
        logger.info("Mock persistence storage cleared and reinitialized")
    
    def add_mock_usage_record(self, runbook_id: str, usage_context: Dict[str, Any]) -> str:
        """Add a mock usage record directly for testing."""
        usage_id = f"manual_{runbook_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{random.randint(1000, 9999)}"
        
        usage_record = {
            "usage_id": usage_id,
            "runbook_id": runbook_id,
            "incident_id": usage_context.get("incident_id", f"TEST-{random.randint(1000, 9999)}"),
            "user": usage_context.get("user", "test_user@company.com"),
            "timestamp": datetime.utcnow().isoformat(),
            "outcome": usage_context.get("outcome", "success"),
            "resolution_time": usage_context.get("resolution_time", 30.0),
            "success": usage_context.get("success", True),
            "notes": usage_context.get("notes", f"Manual test record for {runbook_id}"),
            "context": usage_context.copy(),
            "source": "mock_manual"
        }
        
        self._usage_records[usage_id] = usage_record
        # Update metrics synchronously for test convenience
        logger.info(f"Manually added mock usage record: {usage_id}")
        
        return usage_id
    
    def simulate_incident_scenario(self, incident_id: str, runbook_ids: List[str]) -> None:
        """Create a mock incident scenario with multiple runbook usages."""
        base_time = datetime.utcnow() - timedelta(hours=2)
        
        for i, runbook_id in enumerate(runbook_ids):
            usage_context = {
                "incident_id": incident_id,
                "user": f"responder_{i+1}@company.com",
                "outcome": random.choice(["success", "partial", "failure"]),
                "resolution_time": random.uniform(10.0, 90.0),
                "success": random.choice([True, False]),
                "notes": f"Mock incident response step {i+1}",
                "context": {
                    "incident_severity": "high",
                    "environment": "production",
                    "step": i+1,
                    "total_steps": len(runbook_ids)
                }
            }
            
            # Modify timestamp to show progression
            usage_context["timestamp"] = (base_time + timedelta(minutes=i*15)).isoformat()
            
            # Add the usage record directly
            usage_id = self.add_mock_usage_record(runbook_id, usage_context)
        
        logger.info(f"Created mock incident scenario {incident_id} with {len(runbook_ids)} runbook usages")