"""
Database Decommissioning Business Rules Module.

This module provides business rules and validation logic for database decommissioning
workflows with Manager integration while preserving GraphMCP framework compatibility.

Manager Integration:
- Enhanced business rules with Manager context
- Tenant-aware validation logic
- Manager-specific logging and metrics
- Database client integration for rule persistence

GraphMCP Preservation:
- Full GraphMCP validation patterns
- Standard rule compliance checking
- Database reference validation
- Service integrity assessment
"""

from .validation_rules import (
    DatabaseReferenceValidator,
    RuleComplianceValidator,
    ServiceIntegrityValidator,
    generate_decommissioning_recommendations,
)

from .quality_rules import (
    QualityAssuranceRules,
    DecommissioningQualityGates,
    generate_quality_recommendations,
)

from .risk_assessment import (
    DecommissioningRiskAssessor,
    RiskLevel,
    generate_risk_recommendations,
)

__all__ = [
    "DatabaseReferenceValidator",
    "RuleComplianceValidator", 
    "ServiceIntegrityValidator",
    "generate_decommissioning_recommendations",
    "QualityAssuranceRules",
    "DecommissioningQualityGates",
    "generate_quality_recommendations",
    "DecommissioningRiskAssessor",
    "RiskLevel",
    "generate_risk_recommendations",
]