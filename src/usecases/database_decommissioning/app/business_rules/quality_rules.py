"""
Database Decommissioning Quality Rules.

This module contains quality assurance rules and gates for database decommissioning
workflows with Manager integration while preserving GraphMCP framework compatibility.

Manager Integration:
- Enhanced quality rules with Manager context
- Tenant-aware quality gates and thresholds
- Manager-specific quality metrics and reporting
- Quality tracking and persistence

GraphMCP Preservation:
- Full GraphMCP quality patterns and standards
- Standard quality gate definitions
- Quality metric calculations
- Quality compliance checking
"""

import time
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from enum import Enum

# Local imports
from ..models import ValidationResult, QualityAssuranceResult
from ..utils import create_logger_for_workflow


class QualityGateType(Enum):
    """Types of quality gates."""
    COVERAGE_GATE = "coverage_gate"
    ACCURACY_GATE = "accuracy_gate"
    COMPLETENESS_GATE = "completeness_gate"
    CONSISTENCY_GATE = "consistency_gate"
    PERFORMANCE_GATE = "performance_gate"


class QualityMetric(Enum):
    """Quality metrics for database decommissioning."""
    FILE_COVERAGE = "file_coverage"
    PATTERN_ACCURACY = "pattern_accuracy"
    REFERENCE_COMPLETENESS = "reference_completeness"
    VALIDATION_CONSISTENCY = "validation_consistency"
    PROCESSING_PERFORMANCE = "processing_performance"


@dataclass
class QualityGateResult:
    """Result from quality gate evaluation."""
    gate_type: QualityGateType
    metric: QualityMetric
    score: float  # 0.0 to 100.0
    threshold: float
    passed: bool
    description: str
    details: Dict[str, Any]
    tenant_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "gate_type": self.gate_type.value,
            "metric": self.metric.value,
            "score": self.score,
            "threshold": self.threshold,
            "passed": self.passed,
            "description": self.description,
            "details": self.details,
            "tenant_id": self.tenant_id,
        }


class QualityAssuranceRules:
    """
    Quality assurance rules engine for database decommissioning.
    
    Provides comprehensive quality validation with Manager enhancements.
    """

    def __init__(
        self, 
        database_name: str, 
        tenant_id: Optional[str] = None, 
        workflow_id: Optional[str] = None
    ):
        """
        Initialize quality assurance rules engine.

        Args:
            database_name: Name of database being decommissioned
            tenant_id: Optional tenant identifier
            workflow_id: Optional workflow identifier
        """
        self.database_name = database_name
        self.tenant_id = tenant_id
        self.workflow_id = workflow_id or f"qa_rules_{int(time.time())}"
        
        # Initialize logging
        self.logger = create_logger_for_workflow(
            self.workflow_id, database_name, tenant_id
        )
        
        # Quality thresholds (configurable by tenant)
        self.quality_thresholds = self._get_quality_thresholds()

    def _get_quality_thresholds(self) -> Dict[QualityMetric, float]:
        """Get quality thresholds, potentially tenant-specific."""
        # Default thresholds
        thresholds = {
            QualityMetric.FILE_COVERAGE: 80.0,
            QualityMetric.PATTERN_ACCURACY: 85.0,
            QualityMetric.REFERENCE_COMPLETENESS: 90.0,
            QualityMetric.VALIDATION_CONSISTENCY: 95.0,
            QualityMetric.PROCESSING_PERFORMANCE: 70.0,
        }
        
        # Tenant-specific threshold adjustments
        if self.tenant_id:
            tenant_adjustments = self._get_tenant_threshold_adjustments()
            for metric, adjustment in tenant_adjustments.items():
                if metric in thresholds:
                    thresholds[metric] = max(50.0, min(100.0, thresholds[metric] + adjustment))
        
        return thresholds

    def _get_tenant_threshold_adjustments(self) -> Dict[QualityMetric, float]:
        """Get tenant-specific threshold adjustments."""
        # In a real implementation, this would load from tenant configuration
        # For now, return default adjustments
        return {
            QualityMetric.FILE_COVERAGE: 0.0,
            QualityMetric.PATTERN_ACCURACY: 0.0,
            QualityMetric.REFERENCE_COMPLETENESS: 0.0,
            QualityMetric.VALIDATION_CONSISTENCY: 0.0,
            QualityMetric.PROCESSING_PERFORMANCE: 0.0,
        }

    async def evaluate_file_coverage_quality(
        self, discovery_result: Dict[str, Any]
    ) -> QualityGateResult:
        """
        Evaluate file coverage quality.

        Args:
            discovery_result: Results from pattern discovery

        Returns:
            Quality gate result for file coverage
        """
        try:
            files = discovery_result.get("files", [])
            files_by_type = discovery_result.get("files_by_type", {})
            repository_stats = discovery_result.get("repository_stats", {})
            
            total_discovered = len(files)
            total_repository = repository_stats.get("total_files", total_discovered)
            
            # Calculate coverage score
            if total_repository == 0:
                coverage_score = 0.0
            else:
                coverage_score = (total_discovered / total_repository) * 100
            
            threshold = self.quality_thresholds[QualityMetric.FILE_COVERAGE]
            passed = coverage_score >= threshold
            
            # Enhanced analysis
            coverage_analysis = self._analyze_coverage_distribution(files_by_type)
            
            description = (
                f"File coverage: {coverage_score:.1f}% "
                f"({total_discovered}/{total_repository} files)"
            )
            
            if passed:
                description += " - PASSED"
            else:
                description += f" - FAILED (threshold: {threshold}%)"
            
            return QualityGateResult(
                gate_type=QualityGateType.COVERAGE_GATE,
                metric=QualityMetric.FILE_COVERAGE,
                score=coverage_score,
                threshold=threshold,
                passed=passed,
                description=description,
                details={
                    "total_discovered": total_discovered,
                    "total_repository": total_repository,
                    "coverage_percentage": coverage_score,
                    "file_type_distribution": files_by_type,
                    "coverage_analysis": coverage_analysis,
                },
                tenant_id=self.tenant_id,
            )
            
        except Exception as e:
            self.logger.log_error("File coverage quality evaluation failed", e)
            return QualityGateResult(
                gate_type=QualityGateType.COVERAGE_GATE,
                metric=QualityMetric.FILE_COVERAGE,
                score=0.0,
                threshold=self.quality_thresholds[QualityMetric.FILE_COVERAGE],
                passed=False,
                description=f"Coverage evaluation failed: {str(e)}",
                details={"error": str(e)},
                tenant_id=self.tenant_id,
            )

    async def evaluate_pattern_accuracy_quality(
        self, discovery_result: Dict[str, Any]
    ) -> QualityGateResult:
        """
        Evaluate pattern matching accuracy quality.

        Args:
            discovery_result: Results from pattern discovery

        Returns:
            Quality gate result for pattern accuracy
        """
        try:
            confidence_dist = discovery_result.get("confidence_distribution", {})
            files = discovery_result.get("files", [])
            
            # Calculate accuracy based on confidence distribution
            high_confidence = confidence_dist.get("high", 0)
            medium_confidence = confidence_dist.get("medium", 0)
            low_confidence = confidence_dist.get("low", 0)
            
            total_analyzed = high_confidence + medium_confidence + low_confidence
            
            if total_analyzed == 0:
                accuracy_score = 0.0
            else:
                # Weighted accuracy calculation
                weighted_score = (
                    (high_confidence * 1.0) +
                    (medium_confidence * 0.7) +
                    (low_confidence * 0.4)
                ) / total_analyzed
                accuracy_score = weighted_score * 100
            
            threshold = self.quality_thresholds[QualityMetric.PATTERN_ACCURACY]
            passed = accuracy_score >= threshold
            
            # Enhanced accuracy analysis
            accuracy_analysis = self._analyze_pattern_accuracy(
                files, confidence_dist, accuracy_score
            )
            
            description = (
                f"Pattern accuracy: {accuracy_score:.1f}% "
                f"(based on {total_analyzed} analyzed files)"
            )
            
            if passed:
                description += " - PASSED"
            else:
                description += f" - FAILED (threshold: {threshold}%)"
            
            return QualityGateResult(
                gate_type=QualityGateType.ACCURACY_GATE,
                metric=QualityMetric.PATTERN_ACCURACY,
                score=accuracy_score,
                threshold=threshold,
                passed=passed,
                description=description,
                details={
                    "confidence_distribution": confidence_dist,
                    "total_analyzed": total_analyzed,
                    "weighted_accuracy": accuracy_score,
                    "accuracy_analysis": accuracy_analysis,
                },
                tenant_id=self.tenant_id,
            )
            
        except Exception as e:
            self.logger.log_error("Pattern accuracy quality evaluation failed", e)
            return QualityGateResult(
                gate_type=QualityGateType.ACCURACY_GATE,
                metric=QualityMetric.PATTERN_ACCURACY,
                score=0.0,
                threshold=self.quality_thresholds[QualityMetric.PATTERN_ACCURACY],
                passed=False,
                description=f"Accuracy evaluation failed: {str(e)}",
                details={"error": str(e)},
                tenant_id=self.tenant_id,
            )

    async def evaluate_reference_completeness_quality(
        self, discovery_result: Dict[str, Any], validation_results: List[Dict[str, Any]]
    ) -> QualityGateResult:
        """
        Evaluate reference completeness quality.

        Args:
            discovery_result: Results from pattern discovery
            validation_results: Results from validation checks

        Returns:
            Quality gate result for reference completeness
        """
        try:
            files = discovery_result.get("files", [])
            
            # Analyze reference completeness from validation results
            reference_validation = next(
                (result for result in validation_results 
                 if result.get("rule_type") == "database_reference"),
                {}
            )
            
            reference_details = reference_validation.get("details", {})
            total_files = reference_details.get("total_files", len(files))
            references_found = reference_details.get("references_found", 0)
            
            # Calculate completeness score (inverse of reference density for decommissioning)
            if total_files == 0:
                completeness_score = 100.0  # No files means complete
            else:
                reference_density = references_found / total_files
                # For decommissioning, lower reference density = higher completeness
                completeness_score = max(0.0, (1.0 - reference_density) * 100)
            
            threshold = self.quality_thresholds[QualityMetric.REFERENCE_COMPLETENESS]
            passed = completeness_score >= threshold
            
            # Enhanced completeness analysis
            completeness_analysis = self._analyze_reference_completeness(
                reference_validation, discovery_result
            )
            
            description = (
                f"Reference completeness: {completeness_score:.1f}% "
                f"({references_found} references in {total_files} files)"
            )
            
            if passed:
                description += " - PASSED"
            else:
                description += f" - FAILED (threshold: {threshold}%)"
            
            return QualityGateResult(
                gate_type=QualityGateType.COMPLETENESS_GATE,
                metric=QualityMetric.REFERENCE_COMPLETENESS,
                score=completeness_score,
                threshold=threshold,
                passed=passed,
                description=description,
                details={
                    "total_files": total_files,
                    "references_found": references_found,
                    "reference_density": references_found / total_files if total_files > 0 else 0,
                    "completeness_score": completeness_score,
                    "completeness_analysis": completeness_analysis,
                },
                tenant_id=self.tenant_id,
            )
            
        except Exception as e:
            self.logger.log_error("Reference completeness quality evaluation failed", e)
            return QualityGateResult(
                gate_type=QualityGateType.COMPLETENESS_GATE,
                metric=QualityMetric.REFERENCE_COMPLETENESS,
                score=0.0,
                threshold=self.quality_thresholds[QualityMetric.REFERENCE_COMPLETENESS],
                passed=False,
                description=f"Completeness evaluation failed: {str(e)}",
                details={"error": str(e)},
                tenant_id=self.tenant_id,
            )

    def _analyze_coverage_distribution(self, files_by_type: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze file coverage distribution."""
        total_files = sum(len(files) for files in files_by_type.values())
        
        if total_files == 0:
            return {"coverage_quality": "poor", "reason": "no_files_found"}
        
        type_count = len(files_by_type)
        
        # Analyze coverage quality
        if type_count >= 5:
            coverage_quality = "excellent"
        elif type_count >= 3:
            coverage_quality = "good"
        elif type_count >= 2:
            coverage_quality = "fair"
        else:
            coverage_quality = "poor"
        
        # Calculate distribution statistics
        file_counts = [len(files) for files in files_by_type.values()]
        avg_files_per_type = sum(file_counts) / len(file_counts) if file_counts else 0
        
        return {
            "coverage_quality": coverage_quality,
            "file_types_count": type_count,
            "total_files": total_files,
            "avg_files_per_type": round(avg_files_per_type, 1),
            "type_distribution": {
                file_type: len(files) for file_type, files in files_by_type.items()
            },
        }

    def _analyze_pattern_accuracy(
        self, files: List[Dict[str, Any]], confidence_dist: Dict[str, int], accuracy_score: float
    ) -> Dict[str, Any]:
        """Analyze pattern matching accuracy."""
        total_files = len(files)
        total_analyzed = sum(confidence_dist.values())
        
        analysis_coverage = (total_analyzed / total_files * 100) if total_files > 0 else 0
        
        # Determine accuracy quality
        if accuracy_score >= 90:
            accuracy_quality = "excellent"
        elif accuracy_score >= 80:
            accuracy_quality = "good"
        elif accuracy_score >= 70:
            accuracy_quality = "fair"
        else:
            accuracy_quality = "poor"
        
        # Calculate confidence distribution percentages
        confidence_percentages = {}
        if total_analyzed > 0:
            for level, count in confidence_dist.items():
                confidence_percentages[level] = round((count / total_analyzed) * 100, 1)
        
        return {
            "accuracy_quality": accuracy_quality,
            "analysis_coverage": round(analysis_coverage, 1),
            "confidence_percentages": confidence_percentages,
            "high_confidence_ratio": confidence_percentages.get("high", 0),
            "low_confidence_ratio": confidence_percentages.get("low", 0),
        }

    def _analyze_reference_completeness(
        self, reference_validation: Dict[str, Any], discovery_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze reference completeness."""
        reference_details = reference_validation.get("details", {})
        file_analysis = reference_details.get("file_analysis", [])
        files_by_type = reference_details.get("files_by_type", {})
        
        # Analyze reference distribution by file type
        reference_by_type = {}
        for file_info in file_analysis:
            file_type = file_info.get("file_type", "unknown")
            if file_type not in reference_by_type:
                reference_by_type[file_type] = 0
            reference_by_type[file_type] += 1
        
        # Calculate completeness quality
        total_files = reference_details.get("total_files", 0)
        references_found = reference_details.get("references_found", 0)
        
        if total_files == 0:
            completeness_quality = "excellent"
        elif references_found == 0:
            completeness_quality = "excellent"
        elif references_found / total_files < 0.1:
            completeness_quality = "good"
        elif references_found / total_files < 0.3:
            completeness_quality = "fair"
        else:
            completeness_quality = "poor"
        
        return {
            "completeness_quality": completeness_quality,
            "reference_distribution": reference_by_type,
            "total_reference_types": len(reference_by_type),
            "most_referenced_type": max(reference_by_type.items(), key=lambda x: x[1])[0] if reference_by_type else None,
            "reference_density_by_type": {
                file_type: round(count / len(files_by_type.get(file_type, [])) * 100, 1)
                for file_type, count in reference_by_type.items()
                if file_type in files_by_type and len(files_by_type[file_type]) > 0
            },
        }


class DecommissioningQualityGates:
    """
    Quality gates controller for database decommissioning workflows.
    
    Manages and executes quality gates with Manager integration.
    """

    def __init__(
        self, 
        database_name: str, 
        tenant_id: Optional[str] = None, 
        workflow_id: Optional[str] = None
    ):
        """Initialize quality gates controller."""
        self.database_name = database_name
        self.tenant_id = tenant_id
        self.workflow_id = workflow_id or f"quality_gates_{int(time.time())}"
        
        self.logger = create_logger_for_workflow(
            self.workflow_id, database_name, tenant_id
        )
        
        # Initialize quality rules engine
        self.qa_rules = QualityAssuranceRules(database_name, tenant_id, workflow_id)

    async def execute_all_quality_gates(
        self, 
        discovery_result: Dict[str, Any],
        validation_results: List[Dict[str, Any]],
    ) -> QualityAssuranceResult:
        """
        Execute all quality gates for database decommissioning.

        Args:
            discovery_result: Results from pattern discovery
            validation_results: Results from validation checks

        Returns:
            Comprehensive quality assurance result
        """
        start_time = time.time()
        
        self.logger.log_info("Executing all quality gates")

        try:
            # Execute individual quality gates
            quality_gate_results = []
            
            # File coverage quality gate
            coverage_result = await self.qa_rules.evaluate_file_coverage_quality(discovery_result)
            quality_gate_results.append(coverage_result)
            
            # Pattern accuracy quality gate
            accuracy_result = await self.qa_rules.evaluate_pattern_accuracy_quality(discovery_result)
            quality_gate_results.append(accuracy_result)
            
            # Reference completeness quality gate
            completeness_result = await self.qa_rules.evaluate_reference_completeness_quality(
                discovery_result, validation_results
            )
            quality_gate_results.append(completeness_result)
            
            # Calculate overall quality assessment
            overall_assessment = self._calculate_overall_assessment(quality_gate_results)
            
            # Generate quality recommendations
            quality_recommendations = generate_quality_recommendations(
                quality_gate_results, overall_assessment, self.tenant_id
            )
            
            # Create comprehensive quality result
            qa_result = QualityAssuranceResult(
                overall_status=overall_assessment["status"],
                quality_score=overall_assessment["score"],
                gates_passed=overall_assessment["gates_passed"],
                total_gates=len(quality_gate_results),
                gate_results=[result.to_dict() for result in quality_gate_results],
                recommendations=quality_recommendations,
                details={
                    "execution_time": time.time() - start_time,
                    "database_name": self.database_name,
                    "tenant_id": self.tenant_id,
                    "workflow_id": self.workflow_id,
                    "overall_assessment": overall_assessment,
                },
            )
            
            self.logger.log_info(
                "Quality gates execution completed",
                {
                    "overall_status": overall_assessment["status"].value,
                    "quality_score": overall_assessment["score"],
                    "gates_passed": overall_assessment["gates_passed"],
                    "total_gates": len(quality_gate_results),
                }
            )
            
            return qa_result
            
        except Exception as e:
            self.logger.log_error("Quality gates execution failed", e)
            return QualityAssuranceResult(
                overall_status=ValidationResult.FAILED,
                quality_score=0.0,
                gates_passed=0,
                total_gates=0,
                gate_results=[],
                recommendations=[f"Quality assessment failed: {str(e)}"],
                details={"error": str(e)},
            )

    def _calculate_overall_assessment(
        self, quality_gate_results: List[QualityGateResult]
    ) -> Dict[str, Any]:
        """Calculate overall quality assessment."""
        total_gates = len(quality_gate_results)
        gates_passed = sum(1 for result in quality_gate_results if result.passed)
        
        if total_gates == 0:
            overall_score = 0.0
            overall_status = ValidationResult.FAILED
        else:
            # Calculate weighted quality score
            score_sum = sum(result.score for result in quality_gate_results)
            overall_score = score_sum / total_gates
            
            # Determine overall status
            pass_rate = gates_passed / total_gates
            
            if pass_rate == 1.0 and overall_score >= 80.0:
                overall_status = ValidationResult.PASSED
            elif pass_rate >= 0.8 and overall_score >= 70.0:
                overall_status = ValidationResult.WARNING
            else:
                overall_status = ValidationResult.FAILED
        
        return {
            "status": overall_status,
            "score": round(overall_score, 1),
            "gates_passed": gates_passed,
            "pass_rate": round(gates_passed / total_gates * 100, 1) if total_gates > 0 else 0,
            "gate_summary": {
                result.gate_type.value: {
                    "passed": result.passed,
                    "score": result.score,
                    "threshold": result.threshold,
                }
                for result in quality_gate_results
            },
        }


def generate_quality_recommendations(
    quality_gate_results: List[QualityGateResult],
    overall_assessment: Dict[str, Any],
    tenant_id: Optional[str] = None,
) -> List[str]:
    """
    Generate quality-focused recommendations.

    Args:
        quality_gate_results: List of quality gate results
        overall_assessment: Overall quality assessment
        tenant_id: Optional tenant identifier

    Returns:
        List of quality recommendation strings
    """
    recommendations = []

    # Overall quality recommendations
    overall_score = overall_assessment.get("score", 0)
    overall_status = overall_assessment.get("status")
    
    if overall_status == ValidationResult.FAILED:
        recommendations.extend([
            "CRITICAL: Quality gates have failed - review and address quality issues",
            "Do not proceed with decommissioning until quality standards are met",
            "Consider re-running discovery and validation processes",
        ])
    elif overall_status == ValidationResult.WARNING:
        recommendations.extend([
            "Quality gates show warnings - proceed with caution",
            "Implement additional monitoring and validation steps",
            "Consider manual review of warning areas",
        ])
    elif overall_status == ValidationResult.PASSED:
        recommendations.extend([
            "Quality gates passed - decommissioning can proceed",
            "Maintain quality monitoring throughout deployment",
        ])

    # Gate-specific recommendations
    failed_gates = [result for result in quality_gate_results if not result.passed]
    
    for gate_result in failed_gates:
        if gate_result.gate_type == QualityGateType.COVERAGE_GATE:
            recommendations.extend([
                "Improve file coverage by expanding repository analysis",
                "Review discovery parameters and patterns",
                "Consider additional repository scanning techniques",
            ])
        elif gate_result.gate_type == QualityGateType.ACCURACY_GATE:
            recommendations.extend([
                "Improve pattern matching accuracy",
                "Review and refine search patterns",
                "Consider manual validation of low-confidence matches",
            ])
        elif gate_result.gate_type == QualityGateType.COMPLETENESS_GATE:
            recommendations.extend([
                "Address incomplete reference analysis",
                "Expand database reference detection patterns",
                "Perform additional manual reference verification",
            ])

    # Tenant-specific quality recommendations
    if tenant_id:
        recommendations.extend([
            f"Coordinate quality validation with tenant {tenant_id} teams",
            "Implement tenant-specific quality monitoring",
            "Schedule tenant quality acceptance testing",
        ])

    # Quality improvement recommendations
    if overall_score < 80:
        recommendations.extend([
            "Implement continuous quality monitoring",
            "Establish quality feedback loops",
            "Document quality improvement opportunities",
        ])

    return recommendations