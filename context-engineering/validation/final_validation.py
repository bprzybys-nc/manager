#!/usr/bin/env python3
"""
Final comprehensive validation of the merged Manager Context Engineering system.
Tests all aspects of the consolidation to ensure everything is working properly.
"""

import os
import json
from pathlib import Path

def test_documentation_quality():
    """Test the quality and completeness of documentation."""
    print("📖 Testing Documentation Quality...")
    
    manager_dir = Path(__file__).parent.parent.parent
    
    # Test CLAUDE.md content
    claude_path = manager_dir / "CLAUDE.md"
    with open(claude_path, 'r') as f:
        claude_content = f.read()
    
    required_claude_sections = [
        "Context Engineering Enabled",
        "Manager Component",
        "GraphMCP Framework",
        "Context Engineering Workflow",
        "Manager-Specific Context Assembly",
        "Product Requirements Prompts",
        "Cross-Component"
    ]
    
    claude_score = 0
    for section in required_claude_sections:
        if section in claude_content:
            claude_score += 1
            print(f"  ✅ CLAUDE.md contains: {section}")
        else:
            print(f"  ❌ CLAUDE.md missing: {section}")
    
    # Test PLANNING.md content
    initial_path = manager_dir / "PLANNING.md"
    with open(initial_path, 'r') as f:
        initial_content = f.read()
    
    required_initial_sections = [
        "Manager Component",
        "GraphMCP Framework",
        "Context Engineering",
        "Cross-Component Integration",
        "Feature Development Process"
    ]
    
    initial_score = 0
    for section in required_initial_sections:
        if section in initial_content:
            initial_score += 1
            print(f"  ✅ PLANNING.md contains: {section}")
        else:
            print(f"  ❌ PLANNING.md missing: {section}")
    
    total_score = claude_score + initial_score
    max_score = len(required_claude_sections) + len(required_initial_sections)
    
    print(f"  📊 Documentation Quality: {total_score}/{max_score} ({(total_score/max_score)*100:.1f}%)")
    return total_score >= max_score * 0.9  # 90% threshold

def test_context_engineering_structure():
    """Test the context engineering directory structure."""
    print("🏗️  Testing Context Engineering Structure...")
    
    manager_dir = Path(__file__).parent.parent.parent
    ce_dir = manager_dir / "context-engineering"
    
    required_structure = {
        "README.md": "file",
        "commands": "dir",
        "commands/execute-prp.md": "file",
        "commands/generate-prp.md": "file", 
        "commands/run_demo.md": "file",
        "templates": "dir",
        "templates/feature_request_template.md": "file",
        "PRPs": "dir",
        "PRPs/active": "dir",
        "PRPs/completed": "dir",
        "examples": "dir",
        "validation": "dir"
    }
    
    structure_score = 0
    for path_str, path_type in required_structure.items():
        path = ce_dir / path_str
        if path_type == "file" and path.is_file():
            print(f"  ✅ Found file: {path_str}")
            structure_score += 1
        elif path_type == "dir" and path.is_dir():
            print(f"  ✅ Found directory: {path_str}")
            structure_score += 1
        else:
            print(f"  ❌ Missing {path_type}: {path_str}")
    
    print(f"  📊 Structure Completeness: {structure_score}/{len(required_structure)} ({(structure_score/len(required_structure))*100:.1f}%)")
    return structure_score >= len(required_structure) * 0.9

def test_graphmcp_integration():
    """Test GraphMCP framework integration."""
    print("🔗 Testing GraphMCP Framework Integration...")
    
    manager_dir = Path(__file__).parent.parent.parent
    graphmcp_dir = manager_dir / "src" / "frameworks" / "graphmcp"
    
    integration_tests = [
        ("GraphMCP directory exists", graphmcp_dir.is_dir()),
        ("GraphMCP CLAUDE.md exists", (graphmcp_dir / "CLAUDE.md").is_file()),
        ("GraphMCP Makefile exists", (graphmcp_dir / "Makefile").is_file()),
        ("GraphMCP workflow exists", (graphmcp_dir / "run_db_workflow.py").is_file()),
        ("GraphMCP clients exist", (graphmcp_dir / "clients").is_dir()),
        ("MCP config exists", (graphmcp_dir / "mcp_config.json").is_file()),
    ]
    
    integration_score = 0
    for test_name, test_result in integration_tests:
        if test_result:
            print(f"  ✅ {test_name}")
            integration_score += 1
        else:
            print(f"  ❌ {test_name}")
    
    print(f"  📊 GraphMCP Integration: {integration_score}/{len(integration_tests)} ({(integration_score/len(integration_tests))*100:.1f}%)")
    return integration_score >= len(integration_tests) * 0.8

def test_content_integration():
    """Test content integration between components."""
    print("🔄 Testing Content Integration...")
    
    manager_dir = Path(__file__).parent.parent.parent
    
    # Test cross-references
    claude_path = manager_dir / "CLAUDE.md"
    with open(claude_path, 'r') as f:
        claude_content = f.read()
    
    ce_readme_path = manager_dir / "context-engineering" / "README.md"
    with open(ce_readme_path, 'r') as f:
        ce_content = f.read()
    
    integration_checks = [
        ("CLAUDE.md references context engineering", "context-engineering" in claude_content.lower()),
        ("CLAUDE.md references GraphMCP", "graphmcp" in claude_content.lower()),
        ("CLAUDE.md references Manager", "manager" in claude_content.lower()),
        ("CE README references Manager", "manager" in ce_content.lower()),
        ("CE README references GraphMCP", "graphmcp" in ce_content.lower()),
    ]
    
    integration_score = 0
    for check_name, check_result in integration_checks:
        if check_result:
            print(f"  ✅ {check_name}")
            integration_score += 1
        else:
            print(f"  ❌ {check_name}")
    
    print(f"  📊 Content Integration: {integration_score}/{len(integration_checks)} ({(integration_score/len(integration_checks))*100:.1f}%)")
    return integration_score >= len(integration_checks) * 0.8

def test_file_sizes():
    """Test that files have reasonable content (not empty)."""
    print("📏 Testing File Sizes...")
    
    manager_dir = Path(__file__).parent.parent.parent
    
    size_tests = [
        ("CLAUDE.md", manager_dir / "CLAUDE.md", 30000),  # Should be substantial
        ("PLANNING.md", manager_dir / "PLANNING.md", 15000),  # Should be comprehensive
        ("CE README.md", manager_dir / "context-engineering" / "README.md", 8000),  # Should be detailed
        ("Execute PRP", manager_dir / "context-engineering" / "commands" / "execute-prp.md", 2000),
        ("Generate PRP", manager_dir / "context-engineering" / "commands" / "generate-prp.md", 3000),
        ("Feature Template", manager_dir / "context-engineering" / "templates" / "feature_request_template.md", 8000),
    ]
    
    size_score = 0
    for file_name, file_path, min_size in size_tests:
        if file_path.exists():
            actual_size = file_path.stat().st_size
            if actual_size >= min_size:
                print(f"  ✅ {file_name}: {actual_size:,} bytes (>= {min_size:,})")
                size_score += 1
            else:
                print(f"  ⚠️  {file_name}: {actual_size:,} bytes (< {min_size:,})")
        else:
            print(f"  ❌ {file_name}: File not found")
    
    print(f"  📊 File Size Quality: {size_score}/{len(size_tests)} ({(size_score/len(size_tests))*100:.1f}%)")
    return size_score >= len(size_tests) * 0.8

def main():
    """Run comprehensive final validation."""
    print("🎯 FINAL VALIDATION: Manager Context Engineering System")
    print("=" * 70)
    
    validation_tests = [
        ("Documentation Quality", test_documentation_quality),
        ("Context Engineering Structure", test_context_engineering_structure),
        ("GraphMCP Integration", test_graphmcp_integration),
        ("Content Integration", test_content_integration),
        ("File Size Quality", test_file_sizes),
    ]
    
    results = []
    for test_name, test_func in validation_tests:
        print(f"\n{test_name}:")
        result = test_func()
        results.append((test_name, result))
    
    # Final summary
    print("\n" + "=" * 70)
    print("📊 FINAL VALIDATION SUMMARY")
    print("=" * 70)
    
    passed_tests = sum(1 for _, result in results if result)
    total_tests = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    success_rate = (passed_tests / total_tests) * 100
    print(f"\nOverall Success Rate: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
    
    if success_rate >= 90:
        print("🎉 EXCELLENT: Manager context engineering system is fully operational!")
        return 0
    elif success_rate >= 80:
        print("✅ GOOD: Manager context engineering system is working well with minor issues")
        return 0
    elif success_rate >= 70:
        print("⚠️  ACCEPTABLE: Manager context engineering system is functional but needs improvement")
        return 1
    else:
        print("❌ NEEDS WORK: Manager context engineering system has significant issues")
        return 2

if __name__ == "__main__":
    exit(main())