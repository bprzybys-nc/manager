"""
Quality Assurance Validation for Database Decommissioning.

This module provides quality assurance validation functionality for database decommissioning
workflows, ensuring proper database reference handling, rule compliance, and service integrity.

Manager Integration:
- Enhanced QA metrics and reporting
- Manager-specific validation criteria
- Integration with Manager monitoring systems

GraphMCP Preservation:
- Original QA check logic and patterns
- Validation result structures
- Recommendation generation
"""

import time
from typing import Any, Dict, List, Optional

# GraphMCP framework imports (preserved)
from src.frameworks.graphmcp.graphmcp_logging import get_logger, LoggingConfig

# Local imports
from ..models import ValidationResult, QualityAssuranceResult


class QualityAssuranceValidator:
    """
    Quality assurance validator for database decommissioning workflows.
    
    Performs comprehensive QA checks on discovery results and workflow outcomes.
    """

    def __init__(self, database_name: str, workflow_id: Optional[str] = None):
        """
        Initialize quality assurance validator.

        Args:
            database_name: Name of database being decommissioned
            workflow_id: Optional workflow identifier
        """
        self.database_name = database_name
        self.workflow_id = workflow_id or f"qa_validation_{int(time.time())}"
        
        # Initialize logger
        config = LoggingConfig.from_env()
        self.logger = get_logger(workflow_id=self.workflow_id, config=config)

    async def perform_database_reference_check(
        self, discovery_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Check if database references were properly identified and handled.

        Args:
            discovery_result: Results from pattern discovery

        Returns:
            Dict containing check results and confidence metrics
        """
        try:
            files = discovery_result.get("files", [])
            matched_files = discovery_result.get("matched_files", 0)
            total_files = discovery_result.get("total_files", 0)

            self.logger.log_info(f"Database reference check: {matched_files} matched files out of {total_files} total")

            if total_files == 0:
                return {
                    "status": ValidationResult.FAILED.value,
                    "confidence": 0,
                    "description": "No files were analyzed - repository may be empty or inaccessible",
                    "details": {"total_files": 0, "matched_files": 0},
                }

            if matched_files == 0:
                return {
                    "status": ValidationResult.WARNING.value,
                    "confidence": 50,
                    "description": f"No {self.database_name} references found - database may already be removed or not used",
                    "details": {"total_files": total_files, "matched_files": 0},
                }

            # Check confidence distribution
            confidence_dist = discovery_result.get("confidence_distribution", {})
            high_confidence = confidence_dist.get("high_confidence", 0)
            total_matches = matched_files

            if total_matches > 0 and high_confidence / total_matches >= 0.8:
                return {
                    "status": ValidationResult.PASSED.value,
                    "confidence": 95,
                    "description": f"Database references properly identified with high confidence ({high_confidence}/{total_matches} files)",
                    "details": {
                        "total_files": total_files,
                        "matched_files": matched_files,
                        "high_confidence": high_confidence,
                        "confidence_ratio": high_confidence / total_matches,
                    },
                }
            elif total_matches > 0:
                return {
                    "status": ValidationResult.WARNING.value,
                    "confidence": 70,
                    "description": f"Database references found but some have low confidence ({high_confidence}/{total_matches} high confidence)",
                    "details": {
                        "total_files": total_files,
                        "matched_files": matched_files,
                        "high_confidence": high_confidence,
                        "confidence_ratio": high_confidence / total_matches,
                    },
                }
            else:
                return {
                    "status": ValidationResult.PASSED.value,
                    "confidence": 85,
                    "description": f"Database references analysis completed ({matched_files} files processed)",
                    "details": {"total_files": total_files, "matched_files": matched_files},
                }

        except Exception as e:
            self.logger.log_error("Database reference check failed", e)
            return {
                "status": ValidationResult.FAILED.value,
                "confidence": 0,
                "description": f"Database reference check error: {str(e)}",
                "details": {"error": str(e)},
            }

    async def perform_rule_compliance_check(
        self, discovery_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Check if pattern discovery followed proper rules and classification.

        Args:
            discovery_result: Results from pattern discovery

        Returns:
            Dict containing rule compliance results
        """
        try:
            files_by_type = discovery_result.get("files_by_type", {})

            self.logger.log_info(f"Rule compliance check: {len(files_by_type)} file types found")

            if not files_by_type:
                return {
                    "status": ValidationResult.WARNING.value,
                    "confidence": 40,
                    "description": "No file type classification available for rule compliance validation",
                    "details": {"file_types": 0},
                }

            # Check for proper file type diversity
            file_type_count = len(files_by_type)
            total_files = sum(len(files) for files in files_by_type.values())

            # Enhanced rule compliance checks for Manager integration
            rule_compliance_score = self._calculate_rule_compliance_score(files_by_type, discovery_result)

            if file_type_count >= 3 and total_files >= 5 and rule_compliance_score >= 80:
                return {
                    "status": ValidationResult.PASSED.value,
                    "confidence": 90,
                    "description": f"Pattern discovery properly classified {file_type_count} file types across {total_files} files with {rule_compliance_score}% compliance",
                    "details": {
                        "file_types": file_type_count,
                        "total_classified": total_files,
                        "types": list(files_by_type.keys()),
                        "compliance_score": rule_compliance_score,
                    },
                }
            elif file_type_count >= 2 and rule_compliance_score >= 60:
                return {
                    "status": ValidationResult.PASSED.value,
                    "confidence": 75,
                    "description": f"Pattern discovery classified {file_type_count} file types with reasonable coverage ({rule_compliance_score}% compliance)",
                    "details": {
                        "file_types": file_type_count,
                        "total_classified": total_files,
                        "types": list(files_by_type.keys()),
                        "compliance_score": rule_compliance_score,
                    },
                }
            else:
                return {
                    "status": ValidationResult.WARNING.value,
                    "confidence": 60,
                    "description": f"Limited file type diversity found ({file_type_count} types, {rule_compliance_score}% compliance) - may indicate narrow scope",
                    "details": {
                        "file_types": file_type_count,
                        "total_classified": total_files,
                        "types": list(files_by_type.keys()),
                        "compliance_score": rule_compliance_score,
                    },
                }

        except Exception as e:
            self.logger.log_error("Rule compliance check failed", e)
            return {
                "status": ValidationResult.FAILED.value,
                "confidence": 0,
                "description": f"Rule compliance check error: {str(e)}",
                "details": {"error": str(e)},
            }

    def _calculate_rule_compliance_score(
        self, files_by_type: Dict[str, List], discovery_result: Dict[str, Any]
    ) -> float:
        """
        Calculate rule compliance score based on file classification quality.

        Args:
            files_by_type: Files grouped by type
            discovery_result: Complete discovery results

        Returns:
            Compliance score (0-100)
        """
        try:
            score = 0.0
            total_weight = 0.0

            # Score based on file type diversity (0-30 points)
            type_diversity_score = min(len(files_by_type) * 10, 30)
            score += type_diversity_score
            total_weight += 30

            # Score based on proper categorization (0-40 points)
            expected_types = {'infrastructure', 'configuration', 'code', 'documentation'}
            found_types = set(files_by_type.keys())
            categorization_score = (len(found_types.intersection(expected_types)) / len(expected_types)) * 40
            score += categorization_score
            total_weight += 40

            # Score based on processing quality (0-30 points)
            processing_quality = discovery_result.get("processing_quality", {})
            if processing_quality:
                success_rate = processing_quality.get("success_rate", 0)
                quality_score = success_rate * 30 / 100
                score += quality_score
            total_weight += 30

            return (score / total_weight) * 100 if total_weight > 0 else 0

        except Exception:
            return 50.0  # Default moderate score on error

    async def perform_service_integrity_check(
        self, discovery_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Assess risk to service integrity based on types of files that reference the database.

        Args:
            discovery_result: Results from pattern discovery

        Returns:
            Dict containing service integrity risk assessment
        """
        try:
            files_by_type = discovery_result.get("files_by_type", {})

            self.logger.log_info(f"Service integrity check: analyzing {len(files_by_type)} file types")

            if not files_by_type:
                return {
                    "status": ValidationResult.PASSED.value,
                    "confidence": 80,
                    "description": "No classified files found - minimal service integrity risk",
                    "details": {"risk_level": "low", "critical_files": 0},
                }

            # Enhanced risk assessment for Manager integration
            risk_assessment = self._assess_service_integrity_risk(files_by_type, discovery_result)

            return {
                "status": risk_assessment["status"],
                "confidence": risk_assessment["confidence"],
                "description": risk_assessment["description"],
                "details": risk_assessment["details"],
            }

        except Exception as e:
            self.logger.log_error("Service integrity check failed", e)
            return {
                "status": ValidationResult.FAILED.value,
                "confidence": 0,
                "description": f"Service integrity check error: {str(e)}",
                "details": {"error": str(e)},
            }

    def _assess_service_integrity_risk(
        self, files_by_type: Dict[str, List], discovery_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Perform enhanced service integrity risk assessment.

        Args:
            files_by_type: Files grouped by type
            discovery_result: Complete discovery results

        Returns:
            Dict containing detailed risk assessment
        """
        # Categorize file types by risk level
        critical_types = ["python", "java", "javascript", "typescript", "go", "rust", "cpp"]  # Application code
        high_risk_types = ["sql", "migration", "schema"]  # Database-specific files
        infrastructure_types = ["yaml", "terraform", "docker", "shell"]  # Infrastructure
        config_types = ["json", "ini", "conf", "env", "properties"]  # Configuration

        critical_files = sum(len(files_by_type.get(ftype, [])) for ftype in critical_types)
        high_risk_files = sum(len(files_by_type.get(ftype, [])) for ftype in high_risk_types)
        infrastructure_files = sum(len(files_by_type.get(ftype, [])) for ftype in infrastructure_types)
        config_files = sum(len(files_by_type.get(ftype, [])) for ftype in config_types)

        total_files = critical_files + high_risk_files + infrastructure_files + config_files

        # Calculate risk score (0-100, higher = more risk)
        risk_score = 0
        risk_score += critical_files * 20  # Critical application code
        risk_score += high_risk_files * 30  # Database-specific files
        risk_score += infrastructure_files * 10  # Infrastructure files
        risk_score += config_files * 5  # Configuration files

        # Normalize risk score based on total files
        if total_files > 0:
            risk_score = min(risk_score / total_files, 100)

        # Determine risk level and status
        if risk_score >= 70 or critical_files > 10:
            return {
                "status": ValidationResult.WARNING.value,
                "confidence": 85,
                "description": f"High service integrity risk - {critical_files} application code files + {high_risk_files} database files reference database (risk score: {risk_score:.1f})",
                "details": {
                    "risk_level": "high",
                    "risk_score": risk_score,
                    "critical_files": critical_files,
                    "high_risk_files": high_risk_files,
                    "infrastructure_files": infrastructure_files,
                    "config_files": config_files,
                    "total_files": total_files,
                },
            }
        elif risk_score >= 40 or critical_files > 0:
            return {
                "status": ValidationResult.WARNING.value,
                "confidence": 80,
                "description": f"Moderate service integrity risk - {critical_files} application files + {high_risk_files} database files affected (risk score: {risk_score:.1f})",
                "details": {
                    "risk_level": "moderate",
                    "risk_score": risk_score,
                    "critical_files": critical_files,
                    "high_risk_files": high_risk_files,
                    "infrastructure_files": infrastructure_files,
                    "config_files": config_files,
                    "total_files": total_files,
                },
            }
        elif infrastructure_files > 0 or config_files > 0:
            return {
                "status": ValidationResult.PASSED.value,
                "confidence": 90,
                "description": f"Low service integrity risk - mainly infrastructure/config files ({infrastructure_files + config_files} files, risk score: {risk_score:.1f})",
                "details": {
                    "risk_level": "low",
                    "risk_score": risk_score,
                    "critical_files": 0,
                    "high_risk_files": high_risk_files,
                    "infrastructure_files": infrastructure_files,
                    "config_files": config_files,
                    "total_files": total_files,
                },
            }
        else:
            return {
                "status": ValidationResult.PASSED.value,
                "confidence": 95,
                "description": "Minimal service integrity risk - no critical application files affected",
                "details": {
                    "risk_level": "minimal",
                    "risk_score": 0,
                    "critical_files": 0,
                    "high_risk_files": 0,
                    "infrastructure_files": 0,
                    "config_files": 0,
                    "total_files": 0,
                },
            }

    def generate_recommendations(
        self, qa_checks: List[Dict[str, Any]], discovery_result: Dict[str, Any]
    ) -> List[str]:
        """
        Generate actionable recommendations based on QA check results.

        Args:
            qa_checks: List of QA check results
            discovery_result: Results from pattern discovery

        Returns:
            List of actionable recommendations
        """
        try:
            recommendations = []

            # Base recommendations for Manager integration
            recommendations.append("Monitor application logs for any database connection errors")
            recommendations.append("Update documentation to reflect database decommissioning")
            recommendations.append("Review Manager monitoring dashboards for service health")

            # Risk-based recommendations
            for check in qa_checks:
                if check["check"] == "service_integrity":
                    risk_level = check.get("details", {}).get("risk_level", "low")
                    risk_score = check.get("details", {}).get("risk_score", 0)
                    
                    if risk_level == "high":
                        recommendations.append("⚠️ HIGH RISK: Thoroughly test application functionality before deploying changes")
                        recommendations.append("Consider phased rollout with rollback plan")
                        recommendations.append("Set up enhanced monitoring during deployment")
                        if risk_score > 80:
                            recommendations.append("🚨 CRITICAL: Consider delaying deployment until impact is fully assessed")
                    elif risk_level == "moderate":
                        recommendations.append("Test affected services in staging environment")
                        recommendations.append("Prepare rollback procedures")

                elif check["check"] == "database_reference_removal":
                    if check["status"] == "warning":
                        confidence = check.get("confidence", 0)
                        if confidence < 70:
                            recommendations.append("Review low-confidence matches manually for accuracy")
                            recommendations.append("Consider expanding search patterns for better coverage")

                elif check["check"] == "rule_compliance":
                    if check["status"] == "warning":
                        compliance_score = check.get("details", {}).get("compliance_score", 0)
                        if compliance_score < 60:
                            recommendations.append("Consider expanding search patterns for more comprehensive coverage")
                            recommendations.append("Review file classification rules for accuracy")

            # Manager-specific recommendations
            recommendations.append("Update Manager configuration documentation")
            recommendations.append("Verify Prometheus metrics are collecting decommissioning data")
            
            # Add tenant-specific recommendations if applicable
            tenant_recommendations = self._get_tenant_specific_recommendations(discovery_result)
            recommendations.extend(tenant_recommendations)

            return recommendations

        except Exception as e:
            self.logger.log_error("Recommendation generation failed", e)
            return [
                "Monitor application logs for any database connection errors",
                "Update documentation to reflect database decommissioning",
                "Review service health after decommissioning",
            ]

    def _get_tenant_specific_recommendations(self, discovery_result: Dict[str, Any]) -> List[str]:
        """
        Generate tenant-specific recommendations for Manager integration.

        Args:
            discovery_result: Results from pattern discovery

        Returns:
            List of tenant-specific recommendations
        """
        recommendations = []

        # Check for multi-tenant patterns
        files_by_type = discovery_result.get("files_by_type", {})
        
        # Look for tenant-specific configurations
        config_files = files_by_type.get("configuration", []) + files_by_type.get("json", [])
        if len(config_files) > 5:
            recommendations.append("Review tenant-specific configurations for database references")

        # Look for infrastructure files that might affect multiple tenants
        infra_files = files_by_type.get("infrastructure", []) + files_by_type.get("terraform", [])
        if len(infra_files) > 0:
            recommendations.append("Verify infrastructure changes don't affect other tenant databases")

        return recommendations

    async def perform_comprehensive_qa(self, discovery_result: Dict[str, Any]) -> QualityAssuranceResult:
        """
        Perform comprehensive quality assurance validation.

        Args:
            discovery_result: Results from pattern discovery

        Returns:
            QualityAssuranceResult containing all QA checks
        """
        start_time = time.time()

        self.logger.log_step_start(
            "quality_assurance",
            "Comprehensive quality assurance checks",
            {"database_name": self.database_name},
        )

        try:
            # Perform all QA checks
            db_ref_check = await self.perform_database_reference_check(discovery_result)
            rule_check = await self.perform_rule_compliance_check(discovery_result)
            integrity_check = await self.perform_service_integrity_check(discovery_result)

            # Create QA checks list for recommendation generation
            qa_checks = [
                {"check": "database_reference_removal", **db_ref_check},
                {"check": "rule_compliance", **rule_check},
                {"check": "service_integrity", **integrity_check},
            ]

            # Generate recommendations
            recommendations = self.generate_recommendations(qa_checks, discovery_result)

            # Calculate overall quality score
            passed_checks = sum(
                1 for check in qa_checks if check["status"] == ValidationResult.PASSED.value
            )
            quality_score = (passed_checks / len(qa_checks)) * 100

            # Determine overall status
            failed_checks = [check for check in qa_checks if check["status"] == ValidationResult.FAILED.value]
            overall_status = ValidationResult.PASSED if len(failed_checks) == 0 else ValidationResult.WARNING

            # Create comprehensive QA result
            qa_result = QualityAssuranceResult(
                database_reference_check=ValidationResult(db_ref_check["status"]),
                rule_compliance_check=ValidationResult(rule_check["status"]),
                service_integrity_check=ValidationResult(integrity_check["status"]),
                overall_status=overall_status,
                details={
                    "quality_score": quality_score,
                    "checks_passed": passed_checks,
                    "total_checks": len(qa_checks),
                    "database_name": self.database_name,
                    "workflow_id": self.workflow_id,
                    "qa_checks": qa_checks,
                },
                recommendations=recommendations,
            )

            # Log QA summary
            self.logger.log_quality_assurance_summary([
                {
                    "check_name": check["check"].replace("_", " ").title(),
                    "status": "passed" if check["status"] == ValidationResult.PASSED.value else "failed",
                    "confidence": check.get("confidence", 0),
                    "description": check.get("description", ""),
                }
                for check in qa_checks
            ])

            # Log detailed table
            self.logger.log_table(
                "Quality Assurance Results",
                [
                    {
                        "check": check["check"].replace("_", " ").title(),
                        "status": check["status"],
                        "confidence": f"{check.get('confidence', 0):.0f}%",
                        "description": check.get("description", ""),
                    }
                    for check in qa_checks
                ],
            )

            self.logger.log_step_end(
                "quality_assurance",
                {"quality_score": quality_score, "overall_status": overall_status.value},
                success=True
            )

            return qa_result

        except Exception as e:
            self.logger.log_error("Comprehensive QA validation failed", e)
            raise


# Legacy compatibility functions for GraphMCP integration
async def perform_database_reference_check(
    discovery_result: Dict[str, Any], database_name: str
) -> Dict[str, Any]:
    """Legacy compatibility function for database reference check."""
    validator = QualityAssuranceValidator(database_name)
    return await validator.perform_database_reference_check(discovery_result)


async def perform_rule_compliance_check(
    discovery_result: Dict[str, Any], database_name: str
) -> Dict[str, Any]:
    """Legacy compatibility function for rule compliance check."""
    validator = QualityAssuranceValidator(database_name)
    return await validator.perform_rule_compliance_check(discovery_result)


async def perform_service_integrity_check(
    discovery_result: Dict[str, Any], database_name: str
) -> Dict[str, Any]:
    """Legacy compatibility function for service integrity check."""
    validator = QualityAssuranceValidator(database_name)
    return await validator.perform_service_integrity_check(discovery_result)


def generate_recommendations(
    qa_checks: List[Dict[str, Any]], discovery_result: Dict[str, Any]
) -> List[str]:
    """Legacy compatibility function for recommendation generation."""
    validator = QualityAssuranceValidator("legacy_db")
    return validator.generate_recommendations(qa_checks, discovery_result)