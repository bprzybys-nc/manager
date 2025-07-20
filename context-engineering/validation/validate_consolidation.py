#!/usr/bin/env python3
"""
Validation script for Manager Context Engineering consolidation.
Checks that all required files exist and contain proper content.
"""

import os
import sys
from pathlib import Path

def validate_file_exists(file_path: str, description: str) -> bool:
    """Validate that a file exists and is readable."""
    path = Path(file_path)
    if path.exists() and path.is_file():
        print(f"✅ {description}: {file_path}")
        return True
    else:
        print(f"❌ {description}: {file_path} (NOT FOUND)")
        return False

def validate_directory_exists(dir_path: str, description: str) -> bool:
    """Validate that a directory exists."""
    path = Path(dir_path)
    if path.exists() and path.is_dir():
        print(f"✅ {description}: {dir_path}")
        return True
    else:
        print(f"❌ {description}: {dir_path} (NOT FOUND)")
        return False

def validate_file_content(file_path: str, required_content: list, description: str) -> bool:
    """Validate that a file contains required content."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        missing_content = []
        for required in required_content:
            if required not in content:
                missing_content.append(required)
        
        if not missing_content:
            print(f"✅ {description}: Content validation passed")
            return True
        else:
            print(f"❌ {description}: Missing content: {missing_content}")
            return False
    except Exception as e:
        print(f"❌ {description}: Error reading file: {e}")
        return False

def main():
    """Run consolidation validation."""
    print("🔍 Validating Manager Context Engineering Consolidation")
    print("=" * 60)
    
    # Get the manager directory (parent of context-engineering)
    manager_dir = Path(__file__).parent.parent.parent
    print(f"Manager directory: {manager_dir}")
    
    validation_results = []
    
    # 1. Validate core documentation files
    print("\n📚 Core Documentation Files:")
    validation_results.append(validate_file_exists(
        manager_dir / "CLAUDE.md", 
        "Manager CLAUDE.md"
    ))
    validation_results.append(validate_file_exists(
        manager_dir / "INITIAL.md", 
        "Manager INITIAL.md"
    ))
    validation_results.append(validate_file_exists(
        manager_dir / "VALIDATION.md", 
        "Manager VALIDATION.md"
    ))
    
    # 2. Validate context engineering directory structure
    print("\n🏗️  Context Engineering Structure:")
    ce_dir = manager_dir / "context-engineering"
    validation_results.append(validate_directory_exists(
        ce_dir, 
        "Context Engineering directory"
    ))
    validation_results.append(validate_file_exists(
        ce_dir / "README.md", 
        "Context Engineering README"
    ))
    
    # 3. Validate commands
    print("\n⚡ Context Engineering Commands:")
    commands_dir = ce_dir / "commands"
    validation_results.append(validate_directory_exists(
        commands_dir, 
        "Commands directory"
    ))
    validation_results.append(validate_file_exists(
        commands_dir / "execute-prp.md", 
        "Execute PRP command"
    ))
    validation_results.append(validate_file_exists(
        commands_dir / "generate-prp.md", 
        "Generate PRP command"
    ))
    validation_results.append(validate_file_exists(
        commands_dir / "run_demo.md", 
        "Run demo command"
    ))
    
    # 4. Validate templates
    print("\n📋 Templates:")
    templates_dir = ce_dir / "templates"
    validation_results.append(validate_directory_exists(
        templates_dir, 
        "Templates directory"
    ))
    validation_results.append(validate_file_exists(
        templates_dir / "feature_request_template.md", 
        "Manager feature request template"
    ))
    
    # 5. Validate PRP structure
    print("\n📝 PRP Structure:")
    prp_dir = ce_dir / "PRPs"
    validation_results.append(validate_directory_exists(
        prp_dir, 
        "PRPs directory"
    ))
    validation_results.append(validate_directory_exists(
        prp_dir / "active", 
        "Active PRPs directory"
    ))
    validation_results.append(validate_directory_exists(
        prp_dir / "completed", 
        "Completed PRPs directory"
    ))
    
    # 6. Validate content quality
    print("\n📖 Content Quality Validation:")
    
    # Check CLAUDE.md for context engineering content
    validation_results.append(validate_file_content(
        manager_dir / "CLAUDE.md",
        [
            "Context Engineering Enabled",
            "GraphMCP Framework",
            "Context Engineering Workflow",
            "Manager Component"
        ],
        "CLAUDE.md context engineering content"
    ))
    
    # Check INITIAL.md for Manager context
    validation_results.append(validate_file_content(
        manager_dir / "INITIAL.md",
        [
            "Manager Component",
            "GraphMCP Framework",
            "Context Engineering",
            "Cross-Component"
        ],
        "INITIAL.md Manager context"
    ))
    
    # Check context engineering README
    validation_results.append(validate_file_content(
        ce_dir / "README.md",
        [
            "Manager Context Engineering",
            "GraphMCP Framework",
            "Manager-Specific",
            "Cross-Component"
        ],
        "Context Engineering README Manager content"
    ))
    
    # 7. Check GraphMCP framework exists
    print("\n🔗 GraphMCP Framework Integration:")
    graphmcp_dir = manager_dir / "src" / "frameworks" / "graphmcp"
    validation_results.append(validate_directory_exists(
        graphmcp_dir, 
        "GraphMCP framework directory"
    ))
    validation_results.append(validate_file_exists(
        graphmcp_dir / "CLAUDE.md", 
        "GraphMCP CLAUDE.md (preserved)"
    ))
    
    # 8. Summary
    print("\n" + "=" * 60)
    print("📊 VALIDATION SUMMARY")
    print("=" * 60)
    
    passed = sum(validation_results)
    total = len(validation_results)
    success_rate = (passed / total) * 100
    
    print(f"Validation Results: {passed}/{total} checks passed ({success_rate:.1f}%)")
    
    if success_rate >= 90:
        print("🎉 CONSOLIDATION SUCCESS: Manager context engineering is properly set up!")
        return 0
    elif success_rate >= 75:
        print("⚠️  CONSOLIDATION PARTIAL: Most components are working, minor issues found")
        return 1
    else:
        print("❌ CONSOLIDATION ISSUES: Significant problems found, review required")
        return 2

if __name__ == "__main__":
    sys.exit(main())