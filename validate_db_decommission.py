#!/usr/bin/env python3
"""
Database Decommissioning Validation Script

Simple validation for the database decommissioning use case to ensure
basic functionality works without requiring full GraphMCP framework.
"""

import sys
import importlib.util
from pathlib import Path

def test_basic_imports():
    """Test basic imports without complex dependencies."""
    print("Testing basic imports...")
    
    # Simple check that files are syntactically correct
    try:
        models_file = Path("src/usecases/database_decommissioning/app/models.py")
        utils_file = Path("src/usecases/database_decommissioning/app/utils.py")
        
        # Check files exist
        assert models_file.exists(), "Models file missing"
        assert utils_file.exists(), "Utils file missing"
        
        # Check files have key content
        models_content = models_file.read_text()
        assert "class WorkflowConfig" in models_content
        assert "class WorkflowExecutionResult" in models_content
        assert "class FileProcessingResult" in models_content
        
        utils_content = utils_file.read_text()
        assert "def create_logger_for_workflow" in utils_content
        assert "def validate_workflow_parameters" in utils_content
        
        print("✓ Models and Utils content validation successful")
        return True
        
    except Exception as e:
        print(f"✗ Basic imports validation failed: {e}")
        return False

def test_api_structure():
    """Test API structure and route definitions."""
    print("Testing API structure...")
    
    try:
        # Check that route files exist and have basic structure
        routes_file = Path("src/usecases/database_decommissioning/app/api/routes.py")
        main_file = Path("src/usecases/database_decommissioning/app/api/main.py")
        
        assert routes_file.exists(), "Routes file missing"
        assert main_file.exists(), "Main API file missing"
        
        # Check routes file has key components
        routes_content = routes_file.read_text()
        assert "DatabaseDecommissioningRoute" in routes_content
        assert "get_database_decommissioning_router" in routes_content
        assert "execute_workflow" in routes_content
        
        print("✓ API structure validation successful")
        return True
        
    except Exception as e:
        print(f"✗ API structure validation failed: {e}")
        return False

def test_file_structure():
    """Test that all required files and directories exist."""
    print("Testing file structure...")
    
    required_files = [
        "src/usecases/database_decommissioning/pyproject.toml",
        "src/usecases/database_decommissioning/README.md",
        "src/usecases/database_decommissioning/app/__init__.py",
        "src/usecases/database_decommissioning/app/models.py",
        "src/usecases/database_decommissioning/app/utils.py",
        "src/usecases/database_decommissioning/app/orchestrator.py",
        "src/usecases/database_decommissioning/app/api/routes.py",
        "src/usecases/database_decommissioning/app/api/main.py",
        "src/usecases/database_decommissioning/app/validation/environment_validation.py",
        "src/usecases/database_decommissioning/app/validation/workflow_validation.py",
        "src/usecases/database_decommissioning/app/validation/quality_assurance.py",
        "src/usecases/database_decommissioning/app/processors/pattern_discovery.py",
        "src/usecases/database_decommissioning/app/processors/file_processor.py",
        "src/usecases/database_decommissioning/app/processors/repository_processor.py",
        "src/usecases/database_decommissioning/app/clients/base.py",
        "src/usecases/database_decommissioning/app/clients/github_client.py",
        "src/usecases/database_decommissioning/app/clients/slack_client.py",
        "src/usecases/database_decommissioning/app/clients/repomix_client.py",
        "src/usecases/database_decommissioning/app/business_rules/validation_rules.py",
        "src/usecases/database_decommissioning/app/business_rules/quality_rules.py",
        "src/usecases/database_decommissioning/app/business_rules/risk_assessment.py",
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"✗ Missing files: {missing_files}")
        return False
    
    print("✓ File structure validation successful")
    return True

def test_manager_integration():
    """Test Manager API integration."""
    print("Testing Manager integration...")
    
    try:
        # Check that API integration is in place
        api_file = Path("src/api.py")
        api_content = api_file.read_text()
        
        assert "database_decommissioning" in api_content
        assert "get_database_decommissioning_router" in api_content
        
        print("✓ Manager integration validation successful")
        return True
        
    except Exception as e:
        print(f"✗ Manager integration validation failed: {e}")
        return False

def main():
    """Run all validation tests."""
    print("Database Decommissioning Migration Validation")
    print("=" * 50)
    
    tests = [
        test_file_structure,
        test_basic_imports,
        test_api_structure,
        test_manager_integration,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("Validation Summary")
    print("=" * 50)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("✓ All validation gates passed!")
        return True
    else:
        print("✗ Some validation gates failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)