"""
Database Decommissioning Validation Rules.

This module contains business validation rules for database decommissioning workflows,
enhanced for Manager integration while preserving GraphMCP framework compatibility.

Manager Integration:
- Enhanced validation with Manager context
- Tenant-aware validation rules
- Manager-specific logging and metrics
- Database client integration for rule persistence

GraphMCP Preservation:
- Full GraphMCP validation patterns and logic
- Standard reference checking algorithms
- Service integrity assessment patterns
- Quality compliance validation rules
"""

import re
import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

# Manager imports
import src.config as manager_config
from src.database.client import DatabaseClient

# Local imports
from ..models import ValidationResult
from ..utils import create_logger_for_workflow, get_manager_database_client


class ValidationRuleType(Enum):
    """Types of validation rules."""
    DATABASE_REFERENCE = "database_reference"
    RULE_COMPLIANCE = "rule_compliance"
    SERVICE_INTEGRITY = "service_integrity"
    RISK_ASSESSMENT = "risk_assessment"


@dataclass
class ValidationRuleResult:
    """Result from executing a validation rule."""
    rule_type: ValidationRuleType
    status: ValidationResult
    confidence: int
    description: str
    details: Dict[str, Any]
    tenant_id: Optional[str] = None
    execution_time: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "rule_type": self.rule_type.value,
            "status": self.status.value,
            "confidence": self.confidence,
            "description": self.description,
            "details": self.details,
            "tenant_id": self.tenant_id,
            "execution_time": self.execution_time,
        }


class DatabaseReferenceValidator:
    """
    Validator for database references in discovered files.
    
    Performs comprehensive analysis of database references with Manager enhancements.
    """

    def __init__(self, database_name: str, tenant_id: Optional[str] = None, workflow_id: Optional[str] = None):
        """
        Initialize database reference validator.

        Args:
            database_name: Name of database being decommissioned
            tenant_id: Optional tenant identifier
            workflow_id: Optional workflow identifier
        """
        self.database_name = database_name
        self.tenant_id = tenant_id
        self.workflow_id = workflow_id or f"db_ref_validation_{int(time.time())}"
        
        # Initialize logging
        self.logger = create_logger_for_workflow(
            self.workflow_id, database_name, tenant_id
        )
        
        # Initialize Manager database client
        self.db_client = get_manager_database_client()

    async def validate_database_references(
        self, discovery_result: Dict[str, Any]
    ) -> ValidationRuleResult:
        """
        Perform database reference validation on discovered files.

        Args:
            discovery_result: Results from pattern discovery

        Returns:
            Validation result with Manager enhancements
        """
        start_time = time.time()
        
        self.logger.log_info(
            f"Starting database reference validation for '{self.database_name}'",
            {"discovery_files": len(discovery_result.get("files", []))}
        )

        try:
            files = discovery_result.get("files", [])
            files_by_type = discovery_result.get("files_by_type", {})

            total_files = len(files)
            references_found = 0
            file_analysis = []

            # Enhanced reference patterns for better detection
            reference_patterns = [
                rf"\b{re.escape(self.database_name)}\b",  # Exact word match
                rf"['\"]?{re.escape(self.database_name)}['\"]?",  # With quotes
                rf"database.*{re.escape(self.database_name)}",  # Database context
                rf"{re.escape(self.database_name)}.*database",  # Reverse context
            ]

            # Check for database name references in files
            for file_info in files:
                file_path = file_info.get("path", "")
                file_content = file_info.get("content", "")
                file_type = file_info.get("source_type", "unknown")

                # Count references using multiple patterns
                total_references = 0
                pattern_matches = {}
                
                for i, pattern in enumerate(reference_patterns):
                    matches = len(re.findall(pattern, file_content, re.IGNORECASE))
                    total_references += matches
                    if matches > 0:
                        pattern_matches[f"pattern_{i+1}"] = matches

                if total_references > 0:
                    references_found += 1
                    file_analysis.append({
                        "file_path": file_path,
                        "reference_count": total_references,
                        "file_type": file_type,
                        "pattern_matches": pattern_matches,
                        "risk_score": self._calculate_file_risk_score(file_type, total_references),
                    })

            # Enhanced confidence calculation with Manager context
            confidence, status, description = self._calculate_reference_confidence(
                total_files, references_found, file_analysis
            )

            # Store validation result in Manager database
            result = ValidationRuleResult(
                rule_type=ValidationRuleType.DATABASE_REFERENCE,
                status=status,
                confidence=confidence,
                description=description,
                details={
                    "total_files": total_files,
                    "references_found": references_found,
                    "file_analysis": file_analysis,
                    "files_by_type": files_by_type,
                    "database_name": self.database_name,
                    "tenant_analysis": self._generate_tenant_analysis(file_analysis),
                },
                tenant_id=self.tenant_id,
                execution_time=time.time() - start_time,
            )

            await self._store_validation_result(result)

            self.logger.log_info(
                f"Database reference validation completed",
                {
                    "status": status.value,
                    "confidence": confidence,
                    "references_found": references_found,
                    "total_files": total_files,
                }
            )

            return result

        except Exception as e:
            self.logger.log_error(f"Database reference validation failed", e)
            return ValidationRuleResult(
                rule_type=ValidationRuleType.DATABASE_REFERENCE,
                status=ValidationResult.FAILED,
                confidence=0,
                description=f"Database reference validation failed: {str(e)}",
                details={"error": str(e)},
                tenant_id=self.tenant_id,
                execution_time=time.time() - start_time,
            )

    def _calculate_file_risk_score(self, file_type: str, reference_count: int) -> int:
        """Calculate risk score for file based on type and reference count."""
        # File type risk weights
        type_weights = {
            "python": 0.8,
            "sql": 0.9,
            "infrastructure": 0.9,
            "config": 0.7,
            "documentation": 0.3,
            "unknown": 0.5,
        }
        
        base_weight = type_weights.get(file_type, 0.5)
        reference_weight = min(reference_count / 10.0, 1.0)  # Cap at 10 references
        
        return int((base_weight + reference_weight) * 50)  # Scale to 0-100

    def _calculate_reference_confidence(
        self, total_files: int, references_found: int, file_analysis: List[Dict[str, Any]]
    ) -> tuple[int, ValidationResult, str]:
        """Calculate confidence level with enhanced Manager logic."""
        if total_files == 0:
            return 0, ValidationResult.FAILED, "No files found to analyze"
        
        if references_found == 0:
            return 95, ValidationResult.PASSED, f"No direct references to '{self.database_name}' found in {total_files} files"
        
        # Calculate risk-weighted reference density
        high_risk_files = sum(1 for f in file_analysis if f.get("risk_score", 0) > 70)
        reference_density = references_found / total_files
        risk_density = high_risk_files / total_files if total_files > 0 else 0
        
        # Enhanced confidence calculation
        if reference_density < 0.05 and risk_density < 0.1:  # Very low impact
            confidence = 90
            status = ValidationResult.PASSED
            description = f"Very low impact: {references_found}/{total_files} files contain references"
        elif reference_density < 0.1 and risk_density < 0.2:  # Low impact
            confidence = 85
            status = ValidationResult.PASSED
            description = f"Low impact: {references_found}/{total_files} files contain references"
        elif reference_density < 0.3 and risk_density < 0.4:  # Medium impact
            confidence = 70
            status = ValidationResult.WARNING
            description = f"Medium impact: {references_found}/{total_files} files contain references"
        else:  # High impact
            confidence = 40
            status = ValidationResult.FAILED
            description = f"High impact: {references_found}/{total_files} files contain references"
        
        return confidence, status, description

    def _generate_tenant_analysis(self, file_analysis: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate tenant-specific analysis for Manager integration."""
        if not self.tenant_id:
            return {"tenant_specific": False}
        
        high_risk_count = sum(1 for f in file_analysis if f.get("risk_score", 0) > 70)
        medium_risk_count = sum(1 for f in file_analysis if 40 <= f.get("risk_score", 0) <= 70)
        low_risk_count = len(file_analysis) - high_risk_count - medium_risk_count
        
        return {
            "tenant_specific": True,
            "tenant_id": self.tenant_id,
            "risk_distribution": {
                "high_risk": high_risk_count,
                "medium_risk": medium_risk_count,
                "low_risk": low_risk_count,
            },
            "tenant_recommendations": self._generate_tenant_recommendations(
                high_risk_count, medium_risk_count, low_risk_count
            ),
        }

    def _generate_tenant_recommendations(
        self, high_risk: int, medium_risk: int, low_risk: int
    ) -> List[str]:
        """Generate tenant-specific recommendations."""
        recommendations = []
        
        if high_risk > 0:
            recommendations.extend([
                f"Review {high_risk} high-risk files with tenant application team",
                "Coordinate with tenant stakeholders for deployment approval",
                "Schedule tenant-specific testing and validation",
            ])
        
        if medium_risk > 0:
            recommendations.append(
                f"Monitor {medium_risk} medium-risk files during deployment"
            )
        
        if low_risk > 0:
            recommendations.append(
                f"Standard monitoring for {low_risk} low-risk files"
            )
        
        return recommendations

    async def _store_validation_result(self, result: ValidationRuleResult):
        """Store validation result in Manager database."""
        if not self.db_client:
            return
        
        try:
            collection = self.db_client.database["validation_results"]
            document = {
                "workflow_id": self.workflow_id,
                "rule_type": result.rule_type.value,
                "database_name": self.database_name,
                "tenant_id": self.tenant_id,
                "result": result.to_dict(),
                "created_at": time.time(),
            }
            
            await collection.insert_one(document)
            self.logger.log_info("Validation result stored in Manager database")
            
        except Exception as e:
            self.logger.log_error("Failed to store validation result", e)


class RuleComplianceValidator:
    """
    Validator for rule compliance in pattern discovery results.
    
    Assesses the quality and compliance of pattern discovery with Manager enhancements.
    """

    def __init__(self, database_name: str, tenant_id: Optional[str] = None, workflow_id: Optional[str] = None):
        """Initialize rule compliance validator."""
        self.database_name = database_name
        self.tenant_id = tenant_id
        self.workflow_id = workflow_id or f"rule_compliance_{int(time.time())}"
        
        self.logger = create_logger_for_workflow(
            self.workflow_id, database_name, tenant_id
        )

    async def validate_rule_compliance(
        self, discovery_result: Dict[str, Any]
    ) -> ValidationRuleResult:
        """
        Perform rule compliance validation on pattern discovery results.

        Args:
            discovery_result: Results from pattern discovery

        Returns:
            Validation result with compliance assessment
        """
        start_time = time.time()
        
        self.logger.log_info("Starting rule compliance validation")

        try:
            files = discovery_result.get("files", [])
            files_by_type = discovery_result.get("files_by_type", {})
            confidence_dist = discovery_result.get("confidence_distribution", {})

            # Analyze pattern discovery quality
            total_files = len(files)
            file_types_count = len(files_by_type)

            # Enhanced confidence distribution analysis
            high_confidence = confidence_dist.get("high", 0)
            medium_confidence = confidence_dist.get("medium", 0)
            low_confidence = confidence_dist.get("low", 0)

            total_confidence_files = high_confidence + medium_confidence + low_confidence

            confidence, status, description = self._calculate_compliance_score(
                total_confidence_files, high_confidence, medium_confidence, low_confidence
            )

            # Generate compliance recommendations
            compliance_recommendations = self._generate_compliance_recommendations(
                confidence, file_types_count, files_by_type
            )

            result = ValidationRuleResult(
                rule_type=ValidationRuleType.RULE_COMPLIANCE,
                status=status,
                confidence=confidence,
                description=description,
                details={
                    "total_files": total_files,
                    "file_types_count": file_types_count,
                    "pattern_quality": {
                        "high_confidence": high_confidence,
                        "medium_confidence": medium_confidence,
                        "low_confidence": low_confidence,
                    },
                    "confidence_analysis": {
                        "weighted_score": confidence,
                        "coverage": f"{total_confidence_files}/{total_files} files analyzed",
                    },
                    "compliance_recommendations": compliance_recommendations,
                },
                tenant_id=self.tenant_id,
                execution_time=time.time() - start_time,
            )

            self.logger.log_info(
                "Rule compliance validation completed",
                {"status": status.value, "confidence": confidence}
            )

            return result

        except Exception as e:
            self.logger.log_error("Rule compliance validation failed", e)
            return ValidationRuleResult(
                rule_type=ValidationRuleType.RULE_COMPLIANCE,
                status=ValidationResult.FAILED,
                confidence=0,
                description=f"Rule compliance validation failed: {str(e)}",
                details={"error": str(e)},
                tenant_id=self.tenant_id,
                execution_time=time.time() - start_time,
            )

    def _calculate_compliance_score(
        self, total_confidence_files: int, high_confidence: int, 
        medium_confidence: int, low_confidence: int
    ) -> tuple[int, ValidationResult, str]:
        """Calculate compliance score with enhanced logic."""
        if total_confidence_files == 0:
            return 50, ValidationResult.WARNING, "No confidence data available for pattern discovery"
        
        # Calculate weighted confidence score with Manager enhancements
        weighted_confidence = (
            (high_confidence * 1.0) + 
            (medium_confidence * 0.7) + 
            (low_confidence * 0.4)
        ) / total_confidence_files

        confidence = int(weighted_confidence * 100)

        # Enhanced thresholds for Manager integration
        if confidence >= 85:
            status = ValidationResult.PASSED
            description = f"Excellent pattern discovery quality: {confidence}% confidence"
        elif confidence >= 70:
            status = ValidationResult.PASSED
            description = f"Good pattern discovery quality: {confidence}% confidence"
        elif confidence >= 50:
            status = ValidationResult.WARNING
            description = f"Acceptable pattern discovery quality: {confidence}% confidence"
        else:
            status = ValidationResult.FAILED
            description = f"Poor pattern discovery quality: {confidence}% confidence"

        return confidence, status, description

    def _generate_compliance_recommendations(
        self, confidence: int, file_types_count: int, files_by_type: Dict[str, Any]
    ) -> List[str]:
        """Generate compliance-specific recommendations."""
        recommendations = []

        if confidence < 50:
            recommendations.extend([
                "Consider re-running pattern discovery with adjusted parameters",
                "Manually review discovery results for accuracy",
                "Validate pattern matching rules for this repository type",
            ])
        elif confidence < 70:
            recommendations.extend([
                "Review medium and low confidence matches manually",
                "Consider additional validation steps before proceeding",
            ])

        if file_types_count < 3:
            recommendations.append(
                "Limited file type diversity detected - ensure comprehensive analysis"
            )

        if "sql" in files_by_type:
            recommendations.append(
                "Review SQL file changes with database administration team"
            )

        return recommendations


class ServiceIntegrityValidator:
    """
    Validator for service integrity based on file types and patterns.
    
    Assesses the potential impact on service integrity with Manager enhancements.
    """

    def __init__(self, database_name: str, tenant_id: Optional[str] = None, workflow_id: Optional[str] = None):
        """Initialize service integrity validator."""
        self.database_name = database_name
        self.tenant_id = tenant_id
        self.workflow_id = workflow_id or f"service_integrity_{int(time.time())}"
        
        self.logger = create_logger_for_workflow(
            self.workflow_id, database_name, tenant_id
        )

    async def validate_service_integrity(
        self, discovery_result: Dict[str, Any]
    ) -> ValidationRuleResult:
        """
        Perform service integrity validation based on file types and patterns.

        Args:
            discovery_result: Results from pattern discovery

        Returns:
            Validation result with integrity assessment
        """
        start_time = time.time()
        
        self.logger.log_info("Starting service integrity validation")

        try:
            files_by_type = discovery_result.get("files_by_type", {})

            # Enhanced critical file types with Manager context
            critical_types = {
                "python": {"description": "Application code", "weight": 0.9},
                "sql": {"description": "Database schema", "weight": 1.0},
                "infrastructure": {"description": "Infrastructure configuration", "weight": 0.95},
                "config": {"description": "Configuration files", "weight": 0.8},
                "terraform": {"description": "Infrastructure as code", "weight": 0.9},
                "kubernetes": {"description": "Container orchestration", "weight": 0.85},
                "docker": {"description": "Container definitions", "weight": 0.7},
            }

            critical_files = []
            total_critical_files = 0
            weighted_impact_score = 0.0

            for file_type, info in critical_types.items():
                if file_type in files_by_type:
                    file_count = len(files_by_type[file_type])
                    if file_count > 0:
                        impact_contribution = file_count * info["weight"]
                        weighted_impact_score += impact_contribution
                        
                        critical_files.append({
                            "type": file_type,
                            "description": info["description"],
                            "file_count": file_count,
                            "weight": info["weight"],
                            "impact_contribution": impact_contribution,
                        })
                        total_critical_files += file_count

            # Calculate enhanced risk assessment
            total_files = sum(len(files) for files in files_by_type.values())
            
            confidence, status, description, risk_level = self._calculate_integrity_risk(
                total_files, total_critical_files, weighted_impact_score, critical_files
            )

            result = ValidationRuleResult(
                rule_type=ValidationRuleType.SERVICE_INTEGRITY,
                status=status,
                confidence=confidence,
                description=description,
                details={
                    "total_files": total_files,
                    "critical_files": critical_files,
                    "total_critical_files": total_critical_files,
                    "risk_assessment": {
                        "level": risk_level,
                        "weighted_impact_score": round(weighted_impact_score, 2),
                        "critical_ratio": (
                            round(total_critical_files / total_files * 100, 1)
                            if total_files > 0 else 0
                        ),
                        "recommendations": self._generate_integrity_recommendations(
                            critical_files, risk_level, self.tenant_id
                        ),
                    },
                    "tenant_impact": self._assess_tenant_impact(
                        critical_files, risk_level
                    ) if self.tenant_id else None,
                },
                tenant_id=self.tenant_id,
                execution_time=time.time() - start_time,
            )

            self.logger.log_info(
                "Service integrity validation completed",
                {
                    "status": status.value,
                    "risk_level": risk_level,
                    "critical_files": total_critical_files,
                }
            )

            return result

        except Exception as e:
            self.logger.log_error("Service integrity validation failed", e)
            return ValidationRuleResult(
                rule_type=ValidationRuleType.SERVICE_INTEGRITY,
                status=ValidationResult.FAILED,
                confidence=0,
                description=f"Service integrity validation failed: {str(e)}",
                details={"error": str(e)},
                tenant_id=self.tenant_id,
                execution_time=time.time() - start_time,
            )

    def _calculate_integrity_risk(
        self, total_files: int, total_critical_files: int, 
        weighted_impact_score: float, critical_files: List[Dict[str, Any]]
    ) -> tuple[int, ValidationResult, str, str]:
        """Calculate integrity risk with enhanced scoring."""
        if total_files == 0:
            return 0, ValidationResult.FAILED, "No files found to analyze", "UNKNOWN"
        
        if total_critical_files == 0:
            return 90, ValidationResult.PASSED, "No critical file types found", "LOW"
        
        # Enhanced risk calculation with weighted scoring
        critical_ratio = total_critical_files / total_files
        normalized_impact = weighted_impact_score / total_critical_files if total_critical_files > 0 else 0
        
        # Combined risk score
        risk_score = (critical_ratio * 0.6) + (normalized_impact * 0.4)
        
        if risk_score < 0.15:  # Very low risk
            confidence = 85
            status = ValidationResult.PASSED
            description = f"Very low impact: {total_critical_files}/{total_files} critical files"
            risk_level = "VERY_LOW"
        elif risk_score < 0.3:  # Low risk
            confidence = 80
            status = ValidationResult.PASSED
            description = f"Low impact: {total_critical_files}/{total_files} critical files"
            risk_level = "LOW"
        elif risk_score < 0.5:  # Medium risk
            confidence = 60
            status = ValidationResult.WARNING
            description = f"Medium impact: {total_critical_files}/{total_files} critical files"
            risk_level = "MEDIUM"
        elif risk_score < 0.7:  # High risk
            confidence = 40
            status = ValidationResult.WARNING
            description = f"High impact: {total_critical_files}/{total_files} critical files"
            risk_level = "HIGH"
        else:  # Very high risk
            confidence = 20
            status = ValidationResult.FAILED
            description = f"Very high impact: {total_critical_files}/{total_files} critical files"
            risk_level = "VERY_HIGH"

        return confidence, status, description, risk_level

    def _generate_integrity_recommendations(
        self, critical_files: List[Dict[str, Any]], risk_level: str, tenant_id: Optional[str]
    ) -> List[str]:
        """Generate enhanced integrity recommendations."""
        recommendations = []

        # Risk level based recommendations
        if risk_level in ["VERY_HIGH", "HIGH"]:
            recommendations.extend([
                "Perform comprehensive testing in staging environment",
                "Create detailed rollback plan with database restore procedures",
                "Coordinate with application teams for extended deployment window",
                "Implement continuous monitoring during deployment",
                "Consider phased deployment approach",
            ])
        elif risk_level == "MEDIUM":
            recommendations.extend([
                "Review critical file changes with application teams",
                "Test application functionality in staging environment",
                "Prepare enhanced monitoring alerts for potential issues",
                "Have rollback procedures readily available",
            ])
        elif risk_level in ["LOW", "VERY_LOW"]:
            recommendations.extend([
                "Standard deployment procedures should be sufficient",
                "Monitor application health metrics after deployment",
                "Document changes for future reference",
            ])

        # File-type specific recommendations
        file_types = {f["type"] for f in critical_files}

        if "sql" in file_types:
            recommendations.extend([
                "Review database schema changes with DBA team",
                "Validate database migration scripts",
                "Ensure proper backup procedures are in place",
            ])

        if "infrastructure" in file_types or "terraform" in file_types:
            recommendations.extend([
                "Validate infrastructure configuration changes",
                "Review infrastructure dependencies",
                "Update infrastructure documentation",
            ])

        if "config" in file_types:
            recommendations.extend([
                "Update configuration management documentation",
                "Validate configuration changes in all environments",
            ])

        if "kubernetes" in file_types:
            recommendations.extend([
                "Review Kubernetes resource definitions",
                "Validate container deployment configurations",
            ])

        # Tenant-specific recommendations
        if tenant_id:
            recommendations.extend([
                f"Coordinate with tenant {tenant_id} stakeholders",
                "Schedule tenant-specific validation testing",
                "Notify tenant administrators of upcoming changes",
            ])

        return recommendations

    def _assess_tenant_impact(
        self, critical_files: List[Dict[str, Any]], risk_level: str
    ) -> Dict[str, Any]:
        """Assess tenant-specific impact."""
        if not self.tenant_id:
            return {}
        
        # Calculate tenant-specific impact metrics
        high_impact_types = sum(
            1 for f in critical_files 
            if f.get("weight", 0) >= 0.9
        )
        
        total_impact_score = sum(
            f.get("impact_contribution", 0) for f in critical_files
        )
        
        return {
            "tenant_id": self.tenant_id,
            "risk_level": risk_level,
            "high_impact_types": high_impact_types,
            "total_impact_score": round(total_impact_score, 2),
            "tenant_coordination_required": risk_level in ["HIGH", "VERY_HIGH"],
            "estimated_downtime": self._estimate_tenant_downtime(risk_level),
            "recovery_complexity": self._assess_recovery_complexity(critical_files),
        }

    def _estimate_tenant_downtime(self, risk_level: str) -> str:
        """Estimate potential tenant downtime."""
        downtime_estimates = {
            "VERY_LOW": "< 5 minutes",
            "LOW": "5-15 minutes",
            "MEDIUM": "15-30 minutes",
            "HIGH": "30-60 minutes",
            "VERY_HIGH": "> 60 minutes",
        }
        return downtime_estimates.get(risk_level, "Unknown")

    def _assess_recovery_complexity(self, critical_files: List[Dict[str, Any]]) -> str:
        """Assess recovery complexity based on file types."""
        if any(f["type"] in ["sql", "infrastructure", "terraform"] for f in critical_files):
            return "High"
        elif any(f["type"] in ["config", "kubernetes"] for f in critical_files):
            return "Medium"
        else:
            return "Low"


def generate_decommissioning_recommendations(
    validation_results: List[ValidationRuleResult],
    discovery_result: Dict[str, Any],
    tenant_id: Optional[str] = None,
) -> List[str]:
    """
    Generate comprehensive recommendations based on all validation results.

    Args:
        validation_results: List of validation rule results
        discovery_result: Results from pattern discovery
        tenant_id: Optional tenant identifier

    Returns:
        List of comprehensive recommendation strings
    """
    recommendations = []

    # Analyze validation results
    failed_validations = [
        result for result in validation_results
        if result.status == ValidationResult.FAILED
    ]
    warning_validations = [
        result for result in validation_results
        if result.status == ValidationResult.WARNING
    ]

    # Critical failure recommendations
    if failed_validations:
        recommendations.extend([
            "CRITICAL: Address failed validations before proceeding with decommissioning",
            "Review and resolve all identified critical issues",
            "Consider manual verification of high-risk components",
            "Postpone decommissioning until validation issues are resolved",
        ])

    # Warning-level recommendations
    if warning_validations:
        recommendations.extend([
            "Monitor applications closely during and after deployment",
            "Have comprehensive rollback procedures ready",
            "Consider implementing canary deployment approach",
            "Increase monitoring and alerting sensitivity",
        ])

    # General decommissioning recommendations
    recommendations.extend([
        "Create comprehensive backup of all affected systems",
        "Document all changes and modifications made",
        "Notify all stakeholders of decommissioning timeline",
        "Update system documentation and architecture diagrams",
        "Schedule post-deployment verification and monitoring",
    ])

    # Discovery-specific recommendations
    files_by_type = discovery_result.get("files_by_type", {})

    if "sql" in files_by_type:
        recommendations.extend([
            "Coordinate with database administration team",
            "Validate database migration and cleanup scripts",
            "Ensure proper database backup and recovery procedures",
        ])

    if "infrastructure" in files_by_type:
        recommendations.extend([
            "Update infrastructure monitoring and alerting configurations",
            "Review infrastructure dependencies and impact",
            "Plan infrastructure resource cleanup and optimization",
        ])

    if "config" in files_by_type:
        recommendations.extend([
            "Validate configuration changes in all environments",
            "Update configuration management systems",
            "Review application configuration dependencies",
        ])

    # Tenant-specific recommendations
    if tenant_id:
        recommendations.extend([
            f"Coordinate decommissioning schedule with tenant {tenant_id}",
            "Provide tenant-specific communication and updates",
            "Schedule tenant validation and acceptance testing",
            "Establish tenant-specific support procedures during transition",
        ])

    # Final validation and cleanup recommendations
    recommendations.extend([
        "Perform final validation of all changes before deployment",
        "Archive database artifacts according to retention policies",
        "Update inventory and asset management systems",
        "Schedule infrastructure cleanup and resource deallocation",
        "Document lessons learned and process improvements",
    ])

    return recommendations