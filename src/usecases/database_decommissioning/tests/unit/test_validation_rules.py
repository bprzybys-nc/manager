"""
Unit tests for database decommissioning validation rules.

Tests the business validation rules with Manager integration while preserving GraphMCP patterns.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from app.business_rules.validation_rules import (
    DatabaseReferenceValidator,
    RuleComplianceValidator,
    ServiceIntegrityValidator,
    ValidationRuleType,
    ValidationRuleResult,
    generate_decommissioning_recommendations,
)
from app.models import ValidationResult


@pytest.mark.unit
@pytest.mark.asyncio
class TestDatabaseReferenceValidator:
    """Test DatabaseReferenceValidator business rule."""

    def test_validator_initialization(self, postgres_air_database, test_tenant_id, test_workflow_id):
        """Test validator initialization."""
        validator = DatabaseReferenceValidator(
            postgres_air_database, test_tenant_id, test_workflow_id
        )
        
        assert validator.database_name == postgres_air_database
        assert validator.tenant_id == test_tenant_id
        assert validator.workflow_id == test_workflow_id
        assert validator.logger is not None

    @patch('...app.business_rules.validation_rules.get_manager_database_client')
    def test_validator_with_db_client(self, mock_get_client, postgres_air_database, mock_database_client):
        """Test validator with database client."""
        mock_get_client.return_value = mock_database_client
        
        validator = DatabaseReferenceValidator(postgres_air_database)
        
        assert validator.db_client == mock_database_client

    async def test_validate_no_references(self, postgres_air_database, test_tenant_id):
        """Test validation with no database references."""
        validator = DatabaseReferenceValidator(postgres_air_database, test_tenant_id)
        
        # Discovery result with no references
        discovery_result = {
            "files": [
                {
                    "path": "app/utils.py",
                    "content": "import os\nprint('Hello world')",
                    "source_type": "python",
                },
                {
                    "path": "config/app.yml",
                    "content": "app:\n  name: myapp",
                    "source_type": "config",
                },
            ],
            "files_by_type": {
                "python": [{"path": "app/utils.py"}],
                "config": [{"path": "config/app.yml"}],
            },
        }
        
        result = await validator.validate_database_references(discovery_result)
        
        assert isinstance(result, ValidationRuleResult)
        assert result.rule_type == ValidationRuleType.DATABASE_REFERENCE
        assert result.status == ValidationResult.PASSED
        assert result.confidence >= 90
        assert result.tenant_id == test_tenant_id
        assert "No direct references" in result.description

    async def test_validate_with_references(self, postgres_air_database):
        """Test validation with database references found."""
        validator = DatabaseReferenceValidator(postgres_air_database)
        
        # Discovery result with references
        discovery_result = {
            "files": [
                {
                    "path": "app/models.py",
                    "content": f"from {postgres_air_database} import connection\ndata = {postgres_air_database}.query()",
                    "source_type": "python",
                },
                {
                    "path": "sql/schema.sql",
                    "content": f"CREATE DATABASE {postgres_air_database};",
                    "source_type": "sql",
                },
                {
                    "path": "docs/readme.md",
                    "content": "This is documentation",
                    "source_type": "documentation",
                },
            ],
            "files_by_type": {
                "python": [{"path": "app/models.py"}],
                "sql": [{"path": "sql/schema.sql"}],
                "documentation": [{"path": "docs/readme.md"}],
            },
        }
        
        result = await validator.validate_database_references(discovery_result)
        
        assert result.rule_type == ValidationRuleType.DATABASE_REFERENCE
        assert result.status in [ValidationResult.PASSED, ValidationResult.WARNING, ValidationResult.FAILED]
        assert result.details["total_files"] == 3
        assert result.details["references_found"] == 2  # Two files have references

    async def test_validate_high_reference_density(self, postgres_air_database):
        """Test validation with high reference density."""
        validator = DatabaseReferenceValidator(postgres_air_database)
        
        # Create discovery result where most files have references
        files = []
        for i in range(10):
            files.append({
                "path": f"file_{i}.py",
                "content": f"# File {i}\nfrom {postgres_air_database} import connection",
                "source_type": "python",
            })
        
        discovery_result = {
            "files": files,
            "files_by_type": {"python": files},
        }
        
        result = await validator.validate_database_references(discovery_result)
        
        assert result.rule_type == ValidationRuleType.DATABASE_REFERENCE
        assert result.status == ValidationResult.FAILED  # High density should fail
        assert result.confidence < 50
        assert "High impact" in result.description

    async def test_file_risk_score_calculation(self, postgres_air_database):
        """Test file risk score calculation."""
        validator = DatabaseReferenceValidator(postgres_air_database)
        
        # Test different file types
        sql_score = validator._calculate_file_risk_score("sql", 5)
        python_score = validator._calculate_file_risk_score("python", 5)
        doc_score = validator._calculate_file_risk_score("documentation", 5)
        
        # SQL files should have highest risk
        assert sql_score > python_score > doc_score

    async def test_tenant_analysis_generation(self, postgres_air_database, test_tenant_id):
        """Test tenant-specific analysis generation."""
        validator = DatabaseReferenceValidator(postgres_air_database, test_tenant_id)
        
        file_analysis = [
            {"file_path": "app.py", "risk_score": 80},
            {"file_path": "config.py", "risk_score": 60},
            {"file_path": "docs.md", "risk_score": 20},
        ]
        
        tenant_analysis = validator._generate_tenant_analysis(file_analysis)
        
        assert tenant_analysis["tenant_specific"] is True
        assert tenant_analysis["tenant_id"] == test_tenant_id
        assert "risk_distribution" in tenant_analysis
        assert "tenant_recommendations" in tenant_analysis

    async def test_validation_exception_handling(self, postgres_air_database):
        """Test validation with exception."""
        validator = DatabaseReferenceValidator(postgres_air_database)
        
        # Invalid discovery result that will cause an exception
        invalid_discovery_result = None
        
        result = await validator.validate_database_references(invalid_discovery_result)
        
        assert result.rule_type == ValidationRuleType.DATABASE_REFERENCE
        assert result.status == ValidationResult.FAILED
        assert result.confidence == 0
        assert "failed" in result.description.lower()


@pytest.mark.unit
@pytest.mark.asyncio
class TestRuleComplianceValidator:
    """Test RuleComplianceValidator business rule."""

    def test_validator_initialization(self, postgres_air_database, test_tenant_id):
        """Test validator initialization."""
        validator = RuleComplianceValidator(postgres_air_database, test_tenant_id)
        
        assert validator.database_name == postgres_air_database
        assert validator.tenant_id == test_tenant_id
        assert validator.logger is not None

    async def test_validate_high_quality_discovery(self, postgres_air_database):
        """Test validation with high quality pattern discovery."""
        validator = RuleComplianceValidator(postgres_air_database)
        
        discovery_result = {
            "files": [{"path": f"file_{i}.py"} for i in range(10)],
            "files_by_type": {"python": [{"path": f"file_{i}.py"} for i in range(10)]},
            "confidence_distribution": {"high": 8, "medium": 2, "low": 0},
        }
        
        result = await validator.validate_rule_compliance(discovery_result)
        
        assert result.rule_type == ValidationRuleType.RULE_COMPLIANCE
        assert result.status == ValidationResult.PASSED
        assert result.confidence >= 85

    async def test_validate_medium_quality_discovery(self, postgres_air_database):
        """Test validation with medium quality pattern discovery."""
        validator = RuleComplianceValidator(postgres_air_database)
        
        discovery_result = {
            "files": [{"path": f"file_{i}.py"} for i in range(10)],
            "files_by_type": {"python": [{"path": f"file_{i}.py"} for i in range(10)]},
            "confidence_distribution": {"high": 3, "medium": 4, "low": 3},
        }
        
        result = await validator.validate_rule_compliance(discovery_result)
        
        assert result.rule_type == ValidationRuleType.RULE_COMPLIANCE
        assert result.status in [ValidationResult.PASSED, ValidationResult.WARNING]
        assert 50 <= result.confidence <= 85

    async def test_validate_poor_quality_discovery(self, postgres_air_database):
        """Test validation with poor quality pattern discovery."""
        validator = RuleComplianceValidator(postgres_air_database)
        
        discovery_result = {
            "files": [{"path": f"file_{i}.py"} for i in range(10)],
            "files_by_type": {"python": [{"path": f"file_{i}.py"} for i in range(10)]},
            "confidence_distribution": {"high": 1, "medium": 2, "low": 7},
        }
        
        result = await validator.validate_rule_compliance(discovery_result)
        
        assert result.rule_type == ValidationRuleType.RULE_COMPLIANCE
        assert result.status == ValidationResult.FAILED
        assert result.confidence < 50

    async def test_validate_no_confidence_data(self, postgres_air_database):
        """Test validation with no confidence data."""
        validator = RuleComplianceValidator(postgres_air_database)
        
        discovery_result = {
            "files": [{"path": f"file_{i}.py"} for i in range(5)],
            "files_by_type": {"python": [{"path": f"file_{i}.py"} for i in range(5)]},
            "confidence_distribution": {},
        }
        
        result = await validator.validate_rule_compliance(discovery_result)
        
        assert result.rule_type == ValidationRuleType.RULE_COMPLIANCE
        assert result.status == ValidationResult.WARNING
        assert result.confidence == 50

    def test_compliance_recommendations_generation(self, postgres_air_database):
        """Test compliance recommendations generation."""
        validator = RuleComplianceValidator(postgres_air_database)
        
        # Test low confidence recommendations
        low_confidence_recs = validator._generate_compliance_recommendations(
            confidence=30, file_types_count=2, files_by_type={"python": [], "config": []}
        )
        
        assert any("re-running pattern discovery" in rec for rec in low_confidence_recs)
        
        # Test SQL-specific recommendations
        sql_recs = validator._generate_compliance_recommendations(
            confidence=80, file_types_count=3, files_by_type={"sql": [{"path": "test.sql"}]}
        )
        
        assert any("database administration" in rec for rec in sql_recs)


@pytest.mark.unit
@pytest.mark.asyncio
class TestServiceIntegrityValidator:
    """Test ServiceIntegrityValidator business rule."""

    def test_validator_initialization(self, postgres_air_database, test_tenant_id):
        """Test validator initialization."""
        validator = ServiceIntegrityValidator(postgres_air_database, test_tenant_id)
        
        assert validator.database_name == postgres_air_database
        assert validator.tenant_id == test_tenant_id
        assert validator.logger is not None

    async def test_validate_low_impact_files(self, postgres_air_database):
        """Test validation with low impact files."""
        validator = ServiceIntegrityValidator(postgres_air_database)
        
        discovery_result = {
            "files_by_type": {
                "documentation": [{"path": "README.md"}, {"path": "CHANGELOG.md"}],
                "text": [{"path": "notes.txt"}],
            }
        }
        
        result = await validator.validate_service_integrity(discovery_result)
        
        assert result.rule_type == ValidationRuleType.SERVICE_INTEGRITY
        assert result.status == ValidationResult.PASSED
        assert result.confidence >= 80

    async def test_validate_medium_impact_files(self, postgres_air_database):
        """Test validation with medium impact files."""
        validator = ServiceIntegrityValidator(postgres_air_database)
        
        discovery_result = {
            "files_by_type": {
                "python": [{"path": "app.py"}, {"path": "utils.py"}],
                "config": [{"path": "config.yml"}],
                "documentation": [{"path": "README.md"}],
            }
        }
        
        result = await validator.validate_service_integrity(discovery_result)
        
        assert result.rule_type == ValidationRuleType.SERVICE_INTEGRITY
        assert result.status in [ValidationResult.PASSED, ValidationResult.WARNING]
        assert result.details["risk_assessment"]["level"] in ["LOW", "MEDIUM"]

    async def test_validate_high_impact_files(self, postgres_air_database):
        """Test validation with high impact files."""
        validator = ServiceIntegrityValidator(postgres_air_database)
        
        discovery_result = {
            "files_by_type": {
                "sql": [{"path": "schema.sql"}, {"path": "migrations.sql"}],
                "infrastructure": [{"path": "terraform.tf"}, {"path": "ansible.yml"}],
                "python": [{"path": "app.py"}],
                "config": [{"path": "config.yml"}],
            }
        }
        
        result = await validator.validate_service_integrity(discovery_result)
        
        assert result.rule_type == ValidationRuleType.SERVICE_INTEGRITY
        assert result.details["risk_assessment"]["level"] in ["MEDIUM", "HIGH", "VERY_HIGH"]

    async def test_validate_no_files(self, postgres_air_database):
        """Test validation with no files."""
        validator = ServiceIntegrityValidator(postgres_air_database)
        
        discovery_result = {"files_by_type": {}}
        
        result = await validator.validate_service_integrity(discovery_result)
        
        assert result.rule_type == ValidationRuleType.SERVICE_INTEGRITY
        assert result.status == ValidationResult.FAILED
        assert result.confidence == 0

    def test_integrity_recommendations_generation(self, postgres_air_database):
        """Test integrity recommendations generation."""
        validator = ServiceIntegrityValidator(postgres_air_database)
        
        critical_files = [
            {"type": "sql", "description": "Database schema", "file_count": 2, "weight": 1.0},
            {"type": "infrastructure", "description": "Infrastructure", "file_count": 1, "weight": 0.95},
        ]
        
        # Test high risk recommendations
        high_risk_recs = validator._generate_integrity_recommendations(
            critical_files, "VERY_HIGH", None
        )
        
        assert any("comprehensive testing" in rec for rec in high_risk_recs)
        assert any("rollback plan" in rec for rec in high_risk_recs)
        
        # Test file-type specific recommendations
        assert any("DBA team" in rec for rec in high_risk_recs)
        assert any("infrastructure" in rec for rec in high_risk_recs)

    def test_tenant_impact_assessment(self, postgres_air_database, test_tenant_id):
        """Test tenant-specific impact assessment."""
        validator = ServiceIntegrityValidator(postgres_air_database, test_tenant_id)
        
        critical_files = [
            {"type": "sql", "weight": 1.0, "impact_contribution": 5.0},
            {"type": "config", "weight": 0.8, "impact_contribution": 2.0},
        ]
        
        tenant_impact = validator._assess_tenant_impact(critical_files, "HIGH")
        
        assert tenant_impact["tenant_id"] == test_tenant_id
        assert tenant_impact["risk_level"] == "HIGH"
        assert tenant_impact["tenant_coordination_required"] is True
        assert "estimated_downtime" in tenant_impact
        assert "recovery_complexity" in tenant_impact

    def test_downtime_estimation(self, postgres_air_database):
        """Test downtime estimation for different risk levels."""
        validator = ServiceIntegrityValidator(postgres_air_database)
        
        very_low_downtime = validator._estimate_tenant_downtime("VERY_LOW")
        high_downtime = validator._estimate_tenant_downtime("HIGH")
        very_high_downtime = validator._estimate_tenant_downtime("VERY_HIGH")
        
        assert "< 5" in very_low_downtime
        assert "30-60" in high_downtime
        assert "> 60" in very_high_downtime

    def test_recovery_complexity_assessment(self, postgres_air_database):
        """Test recovery complexity assessment."""
        validator = ServiceIntegrityValidator(postgres_air_database)
        
        # High complexity files
        high_complexity = validator._assess_recovery_complexity([
            {"type": "sql"}, {"type": "infrastructure"}
        ])
        
        # Medium complexity files
        medium_complexity = validator._assess_recovery_complexity([
            {"type": "config"}, {"type": "kubernetes"}
        ])
        
        # Low complexity files
        low_complexity = validator._assess_recovery_complexity([
            {"type": "python"}, {"type": "documentation"}
        ])
        
        assert high_complexity == "High"
        assert medium_complexity == "Medium"
        assert low_complexity == "Low"


@pytest.mark.unit
class TestRecommendationGeneration:
    """Test recommendation generation functions."""

    def test_generate_decommissioning_recommendations_basic(self, mock_validation_results, mock_discovery_result):
        """Test basic recommendation generation."""
        recommendations = generate_decommissioning_recommendations(
            mock_validation_results, mock_discovery_result
        )
        
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        assert any("backup" in rec.lower() for rec in recommendations)

    def test_generate_recommendations_with_failures(self, postgres_air_database):
        """Test recommendations with failed validations."""
        failed_results = [
            ValidationRuleResult(
                rule_type=ValidationRuleType.DATABASE_REFERENCE,
                status=ValidationResult.FAILED,
                confidence=30,
                description="High reference density",
                details={},
            )
        ]
        
        discovery_result = {"files_by_type": {"sql": [{"path": "test.sql"}]}}
        
        recommendations = generate_decommissioning_recommendations(
            failed_results, discovery_result
        )
        
        assert any("CRITICAL" in rec for rec in recommendations)
        assert any("failed validations" in rec for rec in recommendations)

    def test_generate_recommendations_with_warnings(self, postgres_air_database):
        """Test recommendations with warning validations."""
        warning_results = [
            ValidationRuleResult(
                rule_type=ValidationRuleType.SERVICE_INTEGRITY,
                status=ValidationResult.WARNING,
                confidence=60,
                description="Medium impact",
                details={},
            )
        ]
        
        discovery_result = {"files_by_type": {"infrastructure": [{"path": "terraform.tf"}]}}
        
        recommendations = generate_decommissioning_recommendations(
            warning_results, discovery_result
        )
        
        assert any("monitor" in rec.lower() for rec in recommendations)
        assert any("rollback" in rec.lower() for rec in recommendations)

    def test_generate_recommendations_with_tenant(self, postgres_air_database, test_tenant_id):
        """Test recommendations with tenant context."""
        results = [
            ValidationRuleResult(
                rule_type=ValidationRuleType.DATABASE_REFERENCE,
                status=ValidationResult.PASSED,
                confidence=90,
                description="No references",
                details={},
                tenant_id=test_tenant_id,
            )
        ]
        
        discovery_result = {"files_by_type": {}}
        
        recommendations = generate_decommissioning_recommendations(
            results, discovery_result, test_tenant_id
        )
        
        assert any(test_tenant_id in rec for rec in recommendations)
        assert any("tenant" in rec.lower() for rec in recommendations)

    def test_generate_recommendations_file_type_specific(self, postgres_air_database):
        """Test file type specific recommendations."""
        results = [
            ValidationRuleResult(
                rule_type=ValidationRuleType.DATABASE_REFERENCE,
                status=ValidationResult.PASSED,
                confidence=90,
                description="Low impact",
                details={},
            )
        ]
        
        # Test SQL files
        sql_discovery = {"files_by_type": {"sql": [{"path": "schema.sql"}]}}
        sql_recommendations = generate_decommissioning_recommendations(
            results, sql_discovery
        )
        assert any("database administration" in rec for rec in sql_recommendations)
        
        # Test infrastructure files
        infra_discovery = {"files_by_type": {"infrastructure": [{"path": "terraform.tf"}]}}
        infra_recommendations = generate_decommissioning_recommendations(
            results, infra_discovery
        )
        assert any("infrastructure" in rec for rec in infra_recommendations)
        
        # Test config files
        config_discovery = {"files_by_type": {"config": [{"path": "app.yml"}]}}
        config_recommendations = generate_decommissioning_recommendations(
            results, config_discovery
        )
        assert any("configuration" in rec for rec in config_recommendations)


@pytest.mark.unit
@pytest.mark.manager
class TestValidationRulesManagerIntegration:
    """Test Manager-specific validation rules integration."""

    @patch('...app.business_rules.validation_rules.get_manager_database_client')
    async def test_database_storage_integration(self, mock_get_client, postgres_air_database, mock_database_client):
        """Test database storage integration."""
        mock_get_client.return_value = mock_database_client
        
        validator = DatabaseReferenceValidator(postgres_air_database)
        
        discovery_result = {
            "files": [],
            "files_by_type": {},
        }
        
        result = await validator.validate_database_references(discovery_result)
        
        # Verify that storage was attempted
        assert mock_database_client.database["validation_results"].insert_one.called

    async def test_tenant_aware_validation(self, postgres_air_database, test_tenant_id):
        """Test tenant-aware validation results."""
        validator = DatabaseReferenceValidator(postgres_air_database, test_tenant_id)
        
        discovery_result = {
            "files": [
                {
                    "path": "app.py",
                    "content": f"import {postgres_air_database}",
                    "source_type": "python",
                }
            ],
            "files_by_type": {"python": [{"path": "app.py"}]},
        }
        
        result = await validator.validate_database_references(discovery_result)
        
        assert result.tenant_id == test_tenant_id
        assert result.details["tenant_analysis"]["tenant_specific"] is True
        assert result.details["tenant_analysis"]["tenant_id"] == test_tenant_id

    def test_validation_rule_result_serialization(self, postgres_air_database, test_tenant_id):
        """Test ValidationRuleResult serialization for Manager storage."""
        result = ValidationRuleResult(
            rule_type=ValidationRuleType.DATABASE_REFERENCE,
            status=ValidationResult.PASSED,
            confidence=95,
            description="Test result",
            details={"test": "data"},
            tenant_id=test_tenant_id,
            execution_time=1.5,
        )
        
        dict_result = result.to_dict()
        
        assert isinstance(dict_result, dict)
        assert dict_result["rule_type"] == "database_reference"
        assert dict_result["status"] == "passed"
        assert dict_result["tenant_id"] == test_tenant_id
        assert dict_result["execution_time"] == 1.5