"""
Database Decommissioning Risk Assessment.

This module provides risk assessment capabilities for database decommissioning
workflows with Manager integration while preserving GraphMCP framework compatibility.

Manager Integration:
- Enhanced risk assessment with Manager context
- Tenant-aware risk analysis and thresholds
- Manager-specific risk metrics and reporting
- Risk tracking and persistence

GraphMCP Preservation:
- Full GraphMCP risk assessment patterns
- Standard risk calculation methodologies
- Risk classification and scoring
- Risk mitigation recommendations
"""

import time
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

# Local imports
from ..models import ValidationResult
from ..utils import create_logger_for_workflow, get_manager_database_client


class RiskLevel(Enum):
    """Risk levels for database decommissioning."""
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"
    CRITICAL = "critical"


class RiskCategory(Enum):
    """Categories of risk."""
    OPERATIONAL = "operational"
    TECHNICAL = "technical"
    BUSINESS = "business"
    COMPLIANCE = "compliance"
    SECURITY = "security"


class RiskFactor(Enum):
    """Specific risk factors."""
    FILE_IMPACT = "file_impact"
    REFERENCE_DENSITY = "reference_density"
    CRITICAL_SYSTEM_IMPACT = "critical_system_impact"
    SERVICE_DEPENDENCIES = "service_dependencies"
    DATA_INTEGRITY = "data_integrity"
    ROLLBACK_COMPLEXITY = "rollback_complexity"
    TENANT_IMPACT = "tenant_impact"
    COMPLIANCE_RISK = "compliance_risk"


@dataclass
class RiskAssessment:
    """Comprehensive risk assessment result."""
    overall_risk_level: RiskLevel
    overall_risk_score: float  # 0.0 to 100.0
    risk_factors: Dict[RiskFactor, float]
    risk_categories: Dict[RiskCategory, float]
    mitigation_recommendations: List[str]
    tenant_specific_risks: Optional[Dict[str, Any]] = None
    execution_context: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "overall_risk_level": self.overall_risk_level.value,
            "overall_risk_score": self.overall_risk_score,
            "risk_factors": {factor.value: score for factor, score in self.risk_factors.items()},
            "risk_categories": {category.value: score for category, score in self.risk_categories.items()},
            "mitigation_recommendations": self.mitigation_recommendations,
            "tenant_specific_risks": self.tenant_specific_risks,
            "execution_context": self.execution_context,
        }


class DecommissioningRiskAssessor:
    """
    Risk assessor for database decommissioning workflows.
    
    Provides comprehensive risk analysis with Manager integration.
    """

    def __init__(
        self, 
        database_name: str, 
        tenant_id: Optional[str] = None, 
        workflow_id: Optional[str] = None
    ):
        """
        Initialize risk assessor.

        Args:
            database_name: Name of database being decommissioned
            tenant_id: Optional tenant identifier
            workflow_id: Optional workflow identifier
        """
        self.database_name = database_name
        self.tenant_id = tenant_id
        self.workflow_id = workflow_id or f"risk_assessment_{int(time.time())}"
        
        # Initialize logging
        self.logger = create_logger_for_workflow(
            self.workflow_id, database_name, tenant_id
        )
        
        # Initialize Manager database client
        self.db_client = get_manager_database_client()
        
        # Risk assessment configuration
        self.risk_weights = self._get_risk_weights()
        self.tenant_risk_factors = self._get_tenant_risk_factors() if tenant_id else {}

    def _get_risk_weights(self) -> Dict[RiskFactor, float]:
        """Get risk factor weights for scoring."""
        return {
            RiskFactor.FILE_IMPACT: 0.20,
            RiskFactor.REFERENCE_DENSITY: 0.18,
            RiskFactor.CRITICAL_SYSTEM_IMPACT: 0.25,
            RiskFactor.SERVICE_DEPENDENCIES: 0.15,
            RiskFactor.DATA_INTEGRITY: 0.12,
            RiskFactor.ROLLBACK_COMPLEXITY: 0.10,
            RiskFactor.TENANT_IMPACT: 0.15 if self.tenant_id else 0.0,
            RiskFactor.COMPLIANCE_RISK: 0.10,
        }

    def _get_tenant_risk_factors(self) -> Dict[str, Any]:
        """Get tenant-specific risk factors."""
        # In a real implementation, this would load from tenant configuration
        return {
            "criticality_level": "standard",  # low, standard, high, critical
            "sla_requirements": 99.9,
            "compliance_requirements": ["SOX", "GDPR"],
            "business_impact_tolerance": "medium",  # low, medium, high
            "rollback_time_limit": 30,  # minutes
        }

    async def assess_comprehensive_risk(
        self,
        discovery_result: Dict[str, Any],
        validation_results: List[Dict[str, Any]],
        quality_results: Optional[Dict[str, Any]] = None,
    ) -> RiskAssessment:
        """
        Perform comprehensive risk assessment.

        Args:
            discovery_result: Results from pattern discovery
            validation_results: Results from validation checks
            quality_results: Optional quality assessment results

        Returns:
            Comprehensive risk assessment
        """
        start_time = time.time()
        
        self.logger.log_info("Starting comprehensive risk assessment")

        try:
            # Assess individual risk factors
            risk_factors = {}
            
            # File impact risk
            risk_factors[RiskFactor.FILE_IMPACT] = await self._assess_file_impact_risk(
                discovery_result
            )
            
            # Reference density risk
            risk_factors[RiskFactor.REFERENCE_DENSITY] = await self._assess_reference_density_risk(
                validation_results
            )
            
            # Critical system impact risk
            risk_factors[RiskFactor.CRITICAL_SYSTEM_IMPACT] = await self._assess_critical_system_risk(
                discovery_result, validation_results
            )
            
            # Service dependencies risk
            risk_factors[RiskFactor.SERVICE_DEPENDENCIES] = await self._assess_service_dependencies_risk(
                discovery_result
            )
            
            # Data integrity risk
            risk_factors[RiskFactor.DATA_INTEGRITY] = await self._assess_data_integrity_risk(
                discovery_result, validation_results
            )
            
            # Rollback complexity risk
            risk_factors[RiskFactor.ROLLBACK_COMPLEXITY] = await self._assess_rollback_complexity_risk(
                discovery_result
            )
            
            # Tenant impact risk (if applicable)
            if self.tenant_id:
                risk_factors[RiskFactor.TENANT_IMPACT] = await self._assess_tenant_impact_risk(
                    discovery_result, validation_results
                )
            
            # Compliance risk
            risk_factors[RiskFactor.COMPLIANCE_RISK] = await self._assess_compliance_risk(
                discovery_result
            )
            
            # Calculate overall risk score
            overall_risk_score = self._calculate_overall_risk_score(risk_factors)
            overall_risk_level = self._determine_risk_level(overall_risk_score)
            
            # Calculate risk by category
            risk_categories = self._calculate_risk_categories(risk_factors)
            
            # Generate mitigation recommendations
            mitigation_recommendations = self._generate_mitigation_recommendations(
                risk_factors, overall_risk_level
            )
            
            # Assess tenant-specific risks
            tenant_specific_risks = None
            if self.tenant_id:
                tenant_specific_risks = await self._assess_tenant_specific_risks(
                    risk_factors, discovery_result, validation_results
                )
            
            # Create comprehensive risk assessment
            risk_assessment = RiskAssessment(
                overall_risk_level=overall_risk_level,
                overall_risk_score=overall_risk_score,
                risk_factors=risk_factors,
                risk_categories=risk_categories,
                mitigation_recommendations=mitigation_recommendations,
                tenant_specific_risks=tenant_specific_risks,
                execution_context={
                    "database_name": self.database_name,
                    "tenant_id": self.tenant_id,
                    "workflow_id": self.workflow_id,
                    "assessment_duration": time.time() - start_time,
                },
            )
            
            # Store risk assessment
            await self._store_risk_assessment(risk_assessment)
            
            self.logger.log_info(
                "Risk assessment completed",
                {
                    "overall_risk_level": overall_risk_level.value,
                    "overall_risk_score": overall_risk_score,
                    "tenant_id": self.tenant_id,
                }
            )
            
            return risk_assessment
            
        except Exception as e:
            self.logger.log_error("Risk assessment failed", e)
            return RiskAssessment(
                overall_risk_level=RiskLevel.CRITICAL,
                overall_risk_score=100.0,
                risk_factors={},
                risk_categories={},
                mitigation_recommendations=[f"Risk assessment failed: {str(e)}"],
                execution_context={"error": str(e)},
            )

    async def _assess_file_impact_risk(self, discovery_result: Dict[str, Any]) -> float:
        """Assess risk based on file impact."""
        files = discovery_result.get("files", [])
        files_by_type = discovery_result.get("files_by_type", {})
        
        if not files:
            return 0.0
        
        # High-impact file types
        high_impact_types = ["sql", "infrastructure", "terraform", "kubernetes"]
        medium_impact_types = ["python", "config", "docker"]
        
        total_files = len(files)
        high_impact_count = sum(len(files_by_type.get(file_type, [])) for file_type in high_impact_types)
        medium_impact_count = sum(len(files_by_type.get(file_type, [])) for file_type in medium_impact_types)
        
        # Calculate impact ratio
        high_impact_ratio = high_impact_count / total_files if total_files > 0 else 0
        medium_impact_ratio = medium_impact_count / total_files if total_files > 0 else 0
        
        # Calculate risk score (0-100)
        risk_score = (high_impact_ratio * 80) + (medium_impact_ratio * 40)
        
        return min(100.0, risk_score)

    async def _assess_reference_density_risk(self, validation_results: List[Dict[str, Any]]) -> float:
        """Assess risk based on database reference density."""
        reference_validation = next(
            (result for result in validation_results 
             if result.get("rule_type") == "database_reference"),
            {}
        )
        
        details = reference_validation.get("details", {})
        total_files = details.get("total_files", 0)
        references_found = details.get("references_found", 0)
        
        if total_files == 0:
            return 0.0
        
        reference_density = references_found / total_files
        
        # Higher reference density = higher risk for decommissioning
        risk_score = reference_density * 100
        
        return min(100.0, risk_score)

    async def _assess_critical_system_risk(
        self, discovery_result: Dict[str, Any], validation_results: List[Dict[str, Any]]
    ) -> float:
        """Assess risk to critical systems."""
        files_by_type = discovery_result.get("files_by_type", {})
        
        # Critical system indicators
        critical_indicators = {
            "sql": 0.9,
            "infrastructure": 0.85,
            "terraform": 0.8,
            "kubernetes": 0.75,
            "config": 0.6,
        }
        
        total_files = sum(len(files) for files in files_by_type.values())
        critical_score = 0.0
        
        for file_type, weight in critical_indicators.items():
            if file_type in files_by_type:
                file_count = len(files_by_type[file_type])
                file_ratio = file_count / total_files if total_files > 0 else 0
                critical_score += file_ratio * weight * 100
        
        return min(100.0, critical_score)

    async def _assess_service_dependencies_risk(self, discovery_result: Dict[str, Any]) -> float:
        """Assess risk from service dependencies."""
        files_by_type = discovery_result.get("files_by_type", {})
        
        # Service dependency indicators
        dependency_types = ["config", "kubernetes", "docker", "infrastructure"]
        
        total_files = sum(len(files) for files in files_by_type.values())
        dependency_count = sum(len(files_by_type.get(file_type, [])) for file_type in dependency_types)
        
        if total_files == 0:
            return 0.0
        
        dependency_ratio = dependency_count / total_files
        risk_score = dependency_ratio * 70  # Dependencies are concerning but not always critical
        
        return min(100.0, risk_score)

    async def _assess_data_integrity_risk(
        self, discovery_result: Dict[str, Any], validation_results: List[Dict[str, Any]]
    ) -> float:
        """Assess data integrity risk."""
        files_by_type = discovery_result.get("files_by_type", {})
        
        # Data integrity risk factors
        sql_files = len(files_by_type.get("sql", []))
        config_files = len(files_by_type.get("config", []))
        
        total_files = sum(len(files) for files in files_by_type.values())
        
        if total_files == 0:
            return 0.0
        
        # SQL files pose highest data integrity risk
        sql_ratio = sql_files / total_files
        config_ratio = config_files / total_files
        
        risk_score = (sql_ratio * 90) + (config_ratio * 30)
        
        return min(100.0, risk_score)

    async def _assess_rollback_complexity_risk(self, discovery_result: Dict[str, Any]) -> float:
        """Assess rollback complexity risk."""
        files_by_type = discovery_result.get("files_by_type", {})
        
        # Complex rollback types
        complex_rollback_types = {
            "sql": 0.9,
            "infrastructure": 0.8,
            "terraform": 0.85,
            "kubernetes": 0.7,
        }
        
        total_files = sum(len(files) for files in files_by_type.values())
        complexity_score = 0.0
        
        for file_type, weight in complex_rollback_types.items():
            if file_type in files_by_type:
                file_count = len(files_by_type[file_type])
                file_ratio = file_count / total_files if total_files > 0 else 0
                complexity_score += file_ratio * weight * 100
        
        return min(100.0, complexity_score)

    async def _assess_tenant_impact_risk(
        self, discovery_result: Dict[str, Any], validation_results: List[Dict[str, Any]]
    ) -> float:
        """Assess tenant-specific impact risk."""
        if not self.tenant_id or not self.tenant_risk_factors:
            return 0.0
        
        # Base risk from discovery results
        base_risk = await self._assess_file_impact_risk(discovery_result)
        
        # Apply tenant-specific factors
        criticality_multipliers = {
            "low": 0.7,
            "standard": 1.0,
            "high": 1.3,
            "critical": 1.6,
        }
        
        criticality = self.tenant_risk_factors.get("criticality_level", "standard")
        multiplier = criticality_multipliers.get(criticality, 1.0)
        
        sla_requirements = self.tenant_risk_factors.get("sla_requirements", 99.9)
        if sla_requirements >= 99.99:
            multiplier *= 1.2
        elif sla_requirements >= 99.9:
            multiplier *= 1.1
        
        tenant_risk = base_risk * multiplier
        
        return min(100.0, tenant_risk)

    async def _assess_compliance_risk(self, discovery_result: Dict[str, Any]) -> float:
        """Assess compliance-related risk."""
        files_by_type = discovery_result.get("files_by_type", {})
        
        # Compliance-sensitive file types
        compliance_types = ["sql", "config", "infrastructure"]
        
        total_files = sum(len(files) for files in files_by_type.values())
        compliance_count = sum(len(files_by_type.get(file_type, [])) for file_type in compliance_types)
        
        if total_files == 0:
            return 0.0
        
        compliance_ratio = compliance_count / total_files
        
        # Apply tenant compliance requirements if available
        base_risk = compliance_ratio * 50  # Base compliance risk
        
        if self.tenant_risk_factors:
            compliance_reqs = self.tenant_risk_factors.get("compliance_requirements", [])
            if "SOX" in compliance_reqs:
                base_risk *= 1.3
            if "GDPR" in compliance_reqs:
                base_risk *= 1.2
            if "HIPAA" in compliance_reqs:
                base_risk *= 1.4
        
        return min(100.0, base_risk)

    def _calculate_overall_risk_score(self, risk_factors: Dict[RiskFactor, float]) -> float:
        """Calculate weighted overall risk score."""
        total_weighted_score = 0.0
        total_weight = 0.0
        
        for factor, score in risk_factors.items():
            weight = self.risk_weights.get(factor, 0.0)
            total_weighted_score += score * weight
            total_weight += weight
        
        if total_weight == 0:
            return 0.0
        
        return total_weighted_score / total_weight

    def _determine_risk_level(self, risk_score: float) -> RiskLevel:
        """Determine risk level from score."""
        if risk_score >= 90:
            return RiskLevel.CRITICAL
        elif risk_score >= 75:
            return RiskLevel.VERY_HIGH
        elif risk_score >= 60:
            return RiskLevel.HIGH
        elif risk_score >= 40:
            return RiskLevel.MEDIUM
        elif risk_score >= 20:
            return RiskLevel.LOW
        else:
            return RiskLevel.VERY_LOW

    def _calculate_risk_categories(self, risk_factors: Dict[RiskFactor, float]) -> Dict[RiskCategory, float]:
        """Calculate risk scores by category."""
        category_mapping = {
            RiskCategory.OPERATIONAL: [
                RiskFactor.FILE_IMPACT,
                RiskFactor.SERVICE_DEPENDENCIES,
                RiskFactor.ROLLBACK_COMPLEXITY,
            ],
            RiskCategory.TECHNICAL: [
                RiskFactor.REFERENCE_DENSITY,
                RiskFactor.CRITICAL_SYSTEM_IMPACT,
                RiskFactor.DATA_INTEGRITY,
            ],
            RiskCategory.BUSINESS: [
                RiskFactor.TENANT_IMPACT,
            ],
            RiskCategory.COMPLIANCE: [
                RiskFactor.COMPLIANCE_RISK,
            ],
            RiskCategory.SECURITY: [
                RiskFactor.DATA_INTEGRITY,
                RiskFactor.COMPLIANCE_RISK,
            ],
        }
        
        category_scores = {}
        
        for category, factors in category_mapping.items():
            scores = [risk_factors.get(factor, 0.0) for factor in factors if factor in risk_factors]
            if scores:
                category_scores[category] = sum(scores) / len(scores)
            else:
                category_scores[category] = 0.0
        
        return category_scores

    def _generate_mitigation_recommendations(
        self, risk_factors: Dict[RiskFactor, float], overall_risk_level: RiskLevel
    ) -> List[str]:
        """Generate risk mitigation recommendations."""
        recommendations = []
        
        # Overall risk level recommendations
        if overall_risk_level == RiskLevel.CRITICAL:
            recommendations.extend([
                "CRITICAL RISK: Do not proceed without comprehensive risk mitigation",
                "Implement extensive testing and validation procedures",
                "Establish 24/7 monitoring and support during deployment",
                "Create detailed incident response and rollback procedures",
            ])
        elif overall_risk_level == RiskLevel.VERY_HIGH:
            recommendations.extend([
                "VERY HIGH RISK: Proceed only with extensive precautions",
                "Implement comprehensive testing in staging environment",
                "Establish enhanced monitoring and alerting",
                "Prepare detailed rollback procedures",
            ])
        elif overall_risk_level == RiskLevel.HIGH:
            recommendations.extend([
                "HIGH RISK: Implement additional safety measures",
                "Perform thorough testing and validation",
                "Enhance monitoring during deployment",
                "Have rollback procedures ready",
            ])
        
        # Factor-specific recommendations
        high_risk_factors = {factor: score for factor, score in risk_factors.items() if score >= 70}
        
        for factor, score in high_risk_factors.items():
            if factor == RiskFactor.FILE_IMPACT:
                recommendations.append(
                    "High file impact detected - review all file changes with appropriate teams"
                )
            elif factor == RiskFactor.REFERENCE_DENSITY:
                recommendations.append(
                    "High reference density - validate database usage thoroughly"
                )
            elif factor == RiskFactor.CRITICAL_SYSTEM_IMPACT:
                recommendations.append(
                    "Critical system impact - coordinate with infrastructure teams"
                )
            elif factor == RiskFactor.TENANT_IMPACT:
                recommendations.append(
                    f"High tenant impact - coordinate extensively with tenant {self.tenant_id}"
                )
            elif factor == RiskFactor.COMPLIANCE_RISK:
                recommendations.append(
                    "Compliance risk detected - ensure regulatory requirements are met"
                )
        
        return recommendations

    async def _assess_tenant_specific_risks(
        self, 
        risk_factors: Dict[RiskFactor, float],
        discovery_result: Dict[str, Any],
        validation_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Assess tenant-specific risks."""
        if not self.tenant_id:
            return {}
        
        tenant_risks = {
            "tenant_id": self.tenant_id,
            "risk_factors": self.tenant_risk_factors,
            "specific_concerns": [],
            "mitigation_actions": [],
        }
        
        # Assess specific tenant concerns
        if self.tenant_risk_factors.get("criticality_level") in ["high", "critical"]:
            tenant_risks["specific_concerns"].extend([
                "High criticality tenant - extensive coordination required",
                "Enhanced monitoring and support needed",
            ])
        
        sla_requirements = self.tenant_risk_factors.get("sla_requirements", 99.9)
        if sla_requirements >= 99.99:
            tenant_risks["specific_concerns"].append(
                "Extremely high SLA requirements - minimize downtime risk"
            )
        
        # Tenant-specific mitigation actions
        tenant_risks["mitigation_actions"].extend([
            f"Coordinate deployment schedule with tenant {self.tenant_id}",
            "Implement tenant-specific monitoring during deployment",
            "Establish direct communication channel with tenant teams",
            "Prepare tenant-specific rollback procedures",
        ])
        
        return tenant_risks

    async def _store_risk_assessment(self, risk_assessment: RiskAssessment):
        """Store risk assessment in Manager database."""
        if not self.db_client:
            return
        
        try:
            collection = self.db_client.database["risk_assessments"]
            document = {
                "workflow_id": self.workflow_id,
                "database_name": self.database_name,
                "tenant_id": self.tenant_id,
                "assessment": risk_assessment.to_dict(),
                "created_at": time.time(),
            }
            
            await collection.insert_one(document)
            self.logger.log_info("Risk assessment stored in Manager database")
            
        except Exception as e:
            self.logger.log_error("Failed to store risk assessment", e)


def generate_risk_recommendations(
    risk_assessment: RiskAssessment,
    validation_results: List[Dict[str, Any]],
    quality_results: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """
    Generate comprehensive risk-based recommendations.

    Args:
        risk_assessment: Risk assessment result
        validation_results: Validation results
        quality_results: Optional quality results

    Returns:
        List of risk-based recommendation strings
    """
    recommendations = []
    
    # Use existing mitigation recommendations from assessment
    recommendations.extend(risk_assessment.mitigation_recommendations)
    
    # Add validation-based risk recommendations
    failed_validations = [
        result for result in validation_results
        if result.get("status") == ValidationResult.FAILED.value
    ]
    
    if failed_validations:
        recommendations.extend([
            "Address failed validations to reduce overall risk",
            "Failed validations increase deployment risk significantly",
        ])
    
    # Add quality-based risk recommendations
    if quality_results:
        quality_score = quality_results.get("quality_score", 0)
        if quality_score < 70:
            recommendations.extend([
                "Low quality scores increase risk - improve quality before deployment",
                "Quality issues may lead to unexpected deployment problems",
            ])
    
    # Risk category specific recommendations
    risk_categories = risk_assessment.risk_categories
    
    if risk_categories.get(RiskCategory.OPERATIONAL, 0) >= 60:
        recommendations.extend([
            "High operational risk - enhance operational readiness",
            "Prepare comprehensive operational support procedures",
        ])
    
    if risk_categories.get(RiskCategory.TECHNICAL, 0) >= 60:
        recommendations.extend([
            "High technical risk - implement additional technical safeguards",
            "Consider technical debt remediation before deployment",
        ])
    
    if risk_categories.get(RiskCategory.BUSINESS, 0) >= 60:
        recommendations.extend([
            "High business risk - ensure business stakeholder alignment",
            "Implement business continuity measures",
        ])
    
    # Final risk-based recommendations
    if risk_assessment.overall_risk_level in [RiskLevel.HIGH, RiskLevel.VERY_HIGH, RiskLevel.CRITICAL]:
        recommendations.extend([
            "Consider phased deployment approach to minimize risk",
            "Implement continuous risk monitoring throughout deployment",
            "Establish clear escalation procedures for risk events",
        ])
    
    return recommendations