#!/usr/bin/env python3
"""
Comprehensive validation system for Manager Context Engineering.

This validation system checks compliance with Coleman Context Engineering
principles and Claude Code best practices, ensuring the Manager component
has properly configured context engineering infrastructure.

Usage:
    python validate_context_engineering.py
    python validate_context_engineering.py --verbose
    python validate_context_engineering.py --check=structure
"""

import os
import sys
import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
from enum import Enum
import re

class ValidationLevel(Enum):
    """Validation severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

@dataclass
class ValidationResult:
    """Validation result data."""
    check_name: str
    passed: bool
    level: ValidationLevel
    message: str
    details: Optional[str] = None
    suggestions: Optional[List[str]] = None

class ContextEngineeringValidator:
    """
    Comprehensive validator for Manager Context Engineering system.
    
    Validates compliance with:
    - Coleman Context Engineering framework (c_instr, c_know, c_tools, c_mem, c_state, c_query)
    - Claude Code best practices
    - Manager component specific requirements
    - Cross-component integration standards
    """
    
    def __init__(self, manager_dir: Path, verbose: bool = False):
        self.manager_dir = Path(manager_dir)
        self.verbose = verbose
        self.results: List[ValidationResult] = []
        self.context_engineering_dir = self.manager_dir / "context-engineering"
        self.graphmcp_dir = self.manager_dir / "src" / "frameworks" / "graphmcp"
        
    def run_all_validations(self) -> List[ValidationResult]:
        """Run all validation checks."""
        self.results = []
        
        # Coleman Context Engineering Framework Validation
        self._validate_coleman_framework()
        
        # Claude Code Compliance
        self._validate_claude_code_compliance()
        
        # Manager Component Specific
        self._validate_manager_specifics()
        
        # Cross-Component Integration
        self._validate_cross_component_integration()
        
        # Content Quality
        self._validate_content_quality()
        
        # Performance and Usability
        self._validate_performance()
        
        return self.results
    
    def _validate_coleman_framework(self):
        """Validate Coleman Context Engineering framework compliance."""
        self._log("🧠 Validating Coleman Context Engineering Framework...")
        
        # c_instr (Instructions/Rules) - CLAUDE.md and context-engineering/README.md
        self._validate_instructions()
        
        # c_know (Knowledge/Examples) - context-engineering/examples/ and patterns/
        self._validate_knowledge_base()
        
        # c_tools (Tools/Commands) - context-engineering/commands/
        self._validate_tools_commands()
        
        # c_mem (Memory/Templates) - context-engineering/templates/
        self._validate_memory_templates()
        
        # c_state (State/Progress) - context-engineering/PRPs/
        self._validate_state_management()
        
        # c_query (Query/Features) - INITIAL.md and feature specifications
        self._validate_query_system()
    
    def _validate_instructions(self):
        """Validate c_instr component - instructions and rules."""
        # Check CLAUDE.md exists and has proper structure
        claude_md = self.manager_dir / "CLAUDE.md"
        if not claude_md.exists():
            self._add_result("claude_md_exists", False, ValidationLevel.CRITICAL,
                           "CLAUDE.md is missing - core instruction file required",
                           suggestions=["Create CLAUDE.md with project rules and context engineering workflow"])
            return
        
        with open(claude_md, 'r', encoding='utf-8') as f:
            claude_content = f.read()
        
        # Check for essential Coleman sections
        required_sections = {
            "Context Engineering": "Context engineering principles and workflow",
            "Development Scope": "Clear boundaries for AI development",
            "Project Overview": "High-level project understanding",
            "Environment Management": "Python environment and dependency management",
            "context-engineering": "Reference to context engineering directory"
        }
        
        for section, description in required_sections.items():
            if section.lower() in claude_content.lower():
                self._add_result(f"claude_md_section_{section.replace(' ', '_').lower()}", 
                               True, ValidationLevel.HIGH,
                               f"CLAUDE.md contains {description}")
            else:
                self._add_result(f"claude_md_section_{section.replace(' ', '_').lower()}", 
                               False, ValidationLevel.HIGH,
                               f"CLAUDE.md missing {description}",
                               suggestions=[f"Add {section} section to CLAUDE.md"])
        
        # Check context engineering README
        ce_readme = self.context_engineering_dir / "README.md"
        if ce_readme.exists():
            with open(ce_readme, 'r', encoding='utf-8') as f:
                ce_content = f.read()
                
            if "Manager Context Engineering" in ce_content:
                self._add_result("ce_readme_manager_specific", True, ValidationLevel.HIGH,
                               "Context Engineering README is Manager-specific")
            else:
                self._add_result("ce_readme_manager_specific", False, ValidationLevel.MEDIUM,
                               "Context Engineering README should emphasize Manager component focus")
        else:
            self._add_result("ce_readme_exists", False, ValidationLevel.CRITICAL,
                           "context-engineering/README.md is missing",
                           suggestions=["Create comprehensive README.md in context-engineering/"])
    
    def _validate_knowledge_base(self):
        """Validate c_know component - knowledge base and examples."""
        # Check examples directory structure
        examples_dir = self.context_engineering_dir / "examples"
        if not examples_dir.exists():
            self._add_result("examples_dir_exists", False, ValidationLevel.HIGH,
                           "context-engineering/examples/ directory missing",
                           suggestions=["Create examples/ directory with Manager patterns"])
            return
        
        # Check for required example files
        required_examples = {
            "graphmcp_workflow_patterns.py": "GraphMCP workflow implementation patterns",
            "manager_api_patterns.py": "Manager FastAPI patterns and best practices",
            "microservices_patterns.py": "Microservice tool patterns",
            "ai_integration_patterns.py": "Azure OpenAI and LangChain patterns",
            "testing_patterns.py": "Comprehensive testing strategies"
        }
        
        for example_file, description in required_examples.items():
            example_path = examples_dir / example_file
            if example_path.exists():
                # Check file size - should have substantial content
                file_size = example_path.stat().st_size
                if file_size > 5000:  # At least 5KB
                    self._add_result(f"example_{example_file.replace('.py', '')}", 
                                   True, ValidationLevel.MEDIUM,
                                   f"Found comprehensive example: {description}")
                else:
                    self._add_result(f"example_{example_file.replace('.py', '')}_size", 
                                   False, ValidationLevel.MEDIUM,
                                   f"Example {example_file} is too small ({file_size} bytes)")
            else:
                self._add_result(f"example_{example_file.replace('.py', '')}_missing", 
                               False, ValidationLevel.MEDIUM,
                               f"Missing example: {description}",
                               suggestions=[f"Create {example_file} with {description}"])
        
        # Check patterns directory
        patterns_dir = self.context_engineering_dir / "patterns"
        if patterns_dir.exists():
            self._add_result("patterns_dir_exists", True, ValidationLevel.MEDIUM,
                           "Patterns directory exists for architecture patterns")
        else:
            self._add_result("patterns_dir_missing", False, ValidationLevel.LOW,
                           "patterns/ directory could provide additional architecture patterns",
                           suggestions=["Create patterns/ directory for reusable architecture patterns"])
    
    def _validate_tools_commands(self):
        """Validate c_tools component - commands and tools."""
        commands_dir = self.context_engineering_dir / "commands"
        if not commands_dir.exists():
            self._add_result("commands_dir_missing", False, ValidationLevel.HIGH,
                           "context-engineering/commands/ directory missing",
                           suggestions=["Create commands/ directory with PRP generation commands"])
            return
        
        # Check for essential commands
        required_commands = {
            "generate-prp.md": "PRP generation command for creating comprehensive requirements",
            "execute-prp.md": "PRP execution command for implementing features",
            "run_demo.md": "Demo execution command for workflow testing"
        }
        
        for command_file, description in required_commands.items():
            command_path = commands_dir / command_file
            if command_path.exists():
                self._add_result(f"command_{command_file.replace('-', '_').replace('.md', '')}", 
                               True, ValidationLevel.MEDIUM,
                               f"Found command: {description}")
            else:
                self._add_result(f"command_{command_file.replace('-', '_').replace('.md', '')}_missing", 
                               False, ValidationLevel.MEDIUM,
                               f"Missing command: {description}",
                               suggestions=[f"Create {command_file} with {description}"])
        
        # Check Claude settings for slash commands
        claude_settings = self.manager_dir / ".claude" / "settings.local.json"
        if claude_settings.exists():
            self._add_result("claude_settings_exists", True, ValidationLevel.MEDIUM,
                           "Claude Code settings file exists")
        else:
            self._add_result("claude_settings_missing", False, ValidationLevel.MEDIUM,
                           "Claude Code settings could enable slash commands",
                           suggestions=["Create .claude/settings.local.json for Claude Code configuration"])
    
    def _validate_memory_templates(self):
        """Validate c_mem component - templates and memory management."""
        templates_dir = self.context_engineering_dir / "templates"
        if not templates_dir.exists():
            self._add_result("templates_dir_missing", False, ValidationLevel.HIGH,
                           "context-engineering/templates/ directory missing",
                           suggestions=["Create templates/ directory with feature templates"])
            return
        
        # Check for required templates
        required_templates = {
            "feature_request_template.md": "Feature request template for Manager features",
            "workflow_template.md": "GraphMCP workflow template",
            "microservice_template.md": "Microservice tool template",
            "integration_template.md": "External service integration template"
        }
        
        for template_file, description in required_templates.items():
            template_path = templates_dir / template_file
            if template_path.exists():
                # Check template quality
                with open(template_path, 'r', encoding='utf-8') as f:
                    template_content = f.read()
                
                if len(template_content) > 3000:  # Substantial template
                    self._add_result(f"template_{template_file.replace('.md', '')}", 
                                   True, ValidationLevel.MEDIUM,
                                   f"Found comprehensive template: {description}")
                else:
                    self._add_result(f"template_{template_file.replace('.md', '')}_quality", 
                                   False, ValidationLevel.MEDIUM,
                                   f"Template {template_file} is too basic")
            else:
                self._add_result(f"template_{template_file.replace('.md', '')}_missing", 
                               False, ValidationLevel.MEDIUM,
                               f"Missing template: {description}",
                               suggestions=[f"Create {template_file} with {description}"])
        
        # Check INITIAL.template.md
        initial_template = self.manager_dir / "INITIAL.template.md"
        if initial_template.exists():
            self._add_result("initial_template_exists", True, ValidationLevel.HIGH,
                           "INITIAL.template.md exists for feature specifications")
        else:
            self._add_result("initial_template_missing", False, ValidationLevel.HIGH,
                           "INITIAL.template.md missing - needed for feature context engineering",
                           suggestions=["Create INITIAL.template.md for structured feature requests"])
    
    def _validate_state_management(self):
        """Validate c_state component - state and progress management."""
        prps_dir = self.context_engineering_dir / "PRPs"
        if not prps_dir.exists():
            self._add_result("prps_dir_missing", False, ValidationLevel.HIGH,
                           "context-engineering/PRPs/ directory missing",
                           suggestions=["Create PRPs/ directory with active/ and completed/ subdirectories"])
            return
        
        # Check PRP subdirectories
        active_dir = prps_dir / "active"
        completed_dir = prps_dir / "completed"
        
        if active_dir.exists():
            self._add_result("prps_active_dir", True, ValidationLevel.MEDIUM,
                           "PRPs/active/ directory exists for work in progress")
        else:
            self._add_result("prps_active_dir_missing", False, ValidationLevel.MEDIUM,
                           "PRPs/active/ directory missing",
                           suggestions=["Create PRPs/active/ for work in progress"])
        
        if completed_dir.exists():
            self._add_result("prps_completed_dir", True, ValidationLevel.MEDIUM,
                           "PRPs/completed/ directory exists for completed work")
        else:
            self._add_result("prps_completed_dir_missing", False, ValidationLevel.MEDIUM,
                           "PRPs/completed/ directory missing",
                           suggestions=["Create PRPs/completed/ for completed work"])
        
        # Check for PRP templates
        templates_dir = prps_dir / "templates"
        if templates_dir.exists():
            self._add_result("prp_templates_exist", True, ValidationLevel.LOW,
                           "PRP templates directory exists")
        
        # Check validation directory
        validation_dir = self.context_engineering_dir / "validation"
        if validation_dir.exists():
            validation_files = list(validation_dir.glob("*.py"))
            if validation_files:
                self._add_result("validation_scripts_exist", True, ValidationLevel.MEDIUM,
                               f"Found {len(validation_files)} validation scripts")
            else:
                self._add_result("validation_scripts_missing", False, ValidationLevel.MEDIUM,
                               "Validation directory exists but no scripts found")
        else:
            self._add_result("validation_dir_missing", False, ValidationLevel.MEDIUM,
                           "validation/ directory missing",
                           suggestions=["Create validation/ directory with quality assurance scripts"])
    
    def _validate_query_system(self):
        """Validate c_query component - query and feature system."""
        # Check for INITIAL.md files
        initial_files = list(self.manager_dir.glob("INITIAL*.md"))
        if initial_files:
            for initial_file in initial_files:
                with open(initial_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for context engineering structure
                if "Context Engineering" in content:
                    self._add_result(f"initial_{initial_file.stem}_context_engineering", 
                                   True, ValidationLevel.HIGH,
                                   f"{initial_file.name} follows context engineering principles")
                
                # Check for comprehensive content
                if len(content) > 10000:
                    self._add_result(f"initial_{initial_file.stem}_comprehensive", 
                                   True, ValidationLevel.MEDIUM,
                                   f"{initial_file.name} is comprehensive ({len(content)} chars)")
                else:
                    self._add_result(f"initial_{initial_file.stem}_brief", 
                                   False, ValidationLevel.MEDIUM,
                                   f"{initial_file.name} could be more comprehensive")
        else:
            self._add_result("initial_files_missing", False, ValidationLevel.HIGH,
                           "No INITIAL.md files found - needed for feature specifications",
                           suggestions=["Create INITIAL.md files for feature context engineering"])
    
    def _validate_claude_code_compliance(self):
        """Validate Claude Code specific compliance."""
        self._log("⚡ Validating Claude Code Compliance...")
        
        # Check .claude directory structure
        claude_dir = self.manager_dir / ".claude"
        if claude_dir.exists():
            self._add_result("claude_dir_exists", True, ValidationLevel.MEDIUM,
                           ".claude/ directory exists for Claude Code configuration")
            
            # Check settings files
            settings_files = ["settings.json", "settings.local.json"]
            for settings_file in settings_files:
                settings_path = claude_dir / settings_file
                if settings_path.exists():
                    self._add_result(f"claude_{settings_file.replace('.', '_')}", 
                                   True, ValidationLevel.MEDIUM,
                                   f"Claude Code {settings_file} exists")
                    
                    # Validate settings content
                    try:
                        with open(settings_path, 'r') as f:
                            settings = json.load(f)
                        
                        # Check for proper model configuration
                        if "model" in settings:
                            model = settings["model"]
                            if "claude-4" in model:
                                self._add_result("claude_model_config", True, ValidationLevel.MEDIUM,
                                               f"Configured for Claude 4: {model}")
                            else:
                                self._add_result("claude_model_outdated", False, ValidationLevel.LOW,
                                               f"Consider upgrading to Claude 4: {model}")
                        
                        # Check permissions
                        if "permissions" in settings:
                            permissions = settings["permissions"]
                            if "allow" in permissions and isinstance(permissions["allow"], list):
                                allowed_tools = permissions["allow"]
                                essential_tools = ["Read", "Edit", "Write", "Bash(git *)", "Bash(python *)"]
                                missing_tools = [tool for tool in essential_tools 
                                               if not any(tool in allowed for allowed in allowed_tools)]
                                if not missing_tools:
                                    self._add_result("claude_permissions_complete", True, 
                                                   ValidationLevel.MEDIUM,
                                                   "Claude Code permissions include essential tools")
                                else:
                                    self._add_result("claude_permissions_incomplete", False, 
                                                   ValidationLevel.MEDIUM,
                                                   f"Missing permissions: {missing_tools}")
                    except json.JSONDecodeError:
                        self._add_result(f"claude_{settings_file.replace('.', '_')}_invalid", 
                                       False, ValidationLevel.MEDIUM,
                                       f"Claude Code {settings_file} has invalid JSON")
        else:
            self._add_result("claude_dir_missing", False, ValidationLevel.MEDIUM,
                           ".claude/ directory missing - needed for Claude Code configuration",
                           suggestions=["Create .claude/ directory with settings.local.json"])
        
        # Check for memory files
        memory_files = list(self.manager_dir.glob("CLAUDE*.md"))
        if memory_files:
            self._add_result("memory_files_exist", True, ValidationLevel.LOW,
                           f"Found {len(memory_files)} memory files for Claude Code")
    
    def _validate_manager_specifics(self):
        """Validate Manager component specific requirements."""
        self._log("🏗️  Validating Manager Component Specifics...")
        
        # Check src directory structure
        src_dir = self.manager_dir / "src"
        if not src_dir.exists():
            self._add_result("src_dir_missing", False, ValidationLevel.CRITICAL,
                           "src/ directory missing - core Manager component structure")
            return
        
        # Check key Manager directories
        manager_dirs = {
            "frameworks/graphmcp": "GraphMCP framework integration",
            "tools": "Microservice tools directory",
            "usecases": "Use case implementations",
            "modules": "Core Manager modules"
        }
        
        for dir_path, description in manager_dirs.items():
            full_path = src_dir / dir_path
            if full_path.exists():
                self._add_result(f"manager_{dir_path.replace('/', '_')}_exists", 
                               True, ValidationLevel.HIGH,
                               f"Found Manager {description}")
            else:
                self._add_result(f"manager_{dir_path.replace('/', '_')}_missing", 
                               False, ValidationLevel.HIGH,
                               f"Missing Manager {description}",
                               suggestions=[f"Create {dir_path} for {description}"])
        
        # Check GraphMCP framework specifically
        if self.graphmcp_dir.exists():
            graphmcp_claude = self.graphmcp_dir / "CLAUDE.md"
            if graphmcp_claude.exists():
                self._add_result("graphmcp_context_engineering", True, ValidationLevel.HIGH,
                               "GraphMCP framework has its own context engineering")
            
            # Check GraphMCP examples
            graphmcp_examples = self.graphmcp_dir / "examples"
            if graphmcp_examples.exists():
                example_files = list(graphmcp_examples.glob("*.py"))
                self._add_result("graphmcp_examples", True, ValidationLevel.MEDIUM,
                               f"GraphMCP has {len(example_files)} example files")
            
            # Check workflow patterns
            workflow_files = list(self.graphmcp_dir.glob("*workflow*.py"))
            if workflow_files:
                self._add_result("graphmcp_workflows", True, ValidationLevel.MEDIUM,
                               f"GraphMCP has {len(workflow_files)} workflow files")
        
        # Check pyproject.toml for Manager dependencies
        pyproject = self.manager_dir / "pyproject.toml"
        if pyproject.exists():
            with open(pyproject, 'r') as f:
                pyproject_content = f.read()
            
            # Check for key Manager dependencies
            key_deps = ["fastapi", "pydantic", "httpx", "celery", "redis"]
            found_deps = [dep for dep in key_deps if dep in pyproject_content.lower()]
            
            if len(found_deps) >= 3:
                self._add_result("manager_dependencies", True, ValidationLevel.MEDIUM,
                               f"Found key Manager dependencies: {found_deps}")
            else:
                self._add_result("manager_dependencies_incomplete", False, ValidationLevel.MEDIUM,
                               f"Missing some key Manager dependencies")
    
    def _validate_cross_component_integration(self):
        """Validate cross-component integration documentation."""
        self._log("🔗 Validating Cross-Component Integration...")
        
        # Check for Agent integration references
        claude_md = self.manager_dir / "CLAUDE.md"
        if claude_md.exists():
            with open(claude_md, 'r') as f:
                content = f.read()
            
            integration_terms = {
                "Agent": "Go Agent component integration",
                "UI": "Streamlit UI component integration", 
                "API": "API integration patterns",
                "cross-component": "Cross-component integration awareness"
            }
            
            for term, description in integration_terms.items():
                if term.lower() in content.lower():
                    self._add_result(f"integration_{term.lower()}_reference", 
                                   True, ValidationLevel.MEDIUM,
                                   f"CLAUDE.md references {description}")
                else:
                    self._add_result(f"integration_{term.lower()}_missing", 
                                   False, ValidationLevel.LOW,
                                   f"CLAUDE.md could mention {description}")
        
        # Check for parent project integration
        parent_claude = self.manager_dir.parent / "CLAUDE.md"
        if parent_claude.exists():
            self._add_result("parent_claude_exists", True, ValidationLevel.MEDIUM,
                           "Parent project CLAUDE.md exists for integration context")
        
        # Check for deployment integration
        docker_files = list(self.manager_dir.glob("*docker*"))
        k8s_files = list(self.manager_dir.glob("*k8s*"))
        
        if docker_files or k8s_files:
            self._add_result("deployment_integration", True, ValidationLevel.LOW,
                           f"Found deployment files: {len(docker_files)} docker, {len(k8s_files)} k8s")
    
    def _validate_content_quality(self):
        """Validate content quality and comprehensiveness."""
        self._log("📖 Validating Content Quality...")
        
        # Check documentation file sizes for comprehensiveness
        key_files = {
            "CLAUDE.md": 15000,  # Should be comprehensive
            "context-engineering/README.md": 8000,  # Should be detailed
            "INITIAL.md": 10000,  # Should be thorough
        }
        
        for file_path, min_size in key_files.items():
            full_path = self.manager_dir / file_path
            if full_path.exists():
                file_size = full_path.stat().st_size
                if file_size >= min_size:
                    self._add_result(f"content_quality_{file_path.replace('/', '_').replace('.md', '')}", 
                                   True, ValidationLevel.MEDIUM,
                                   f"{file_path} is comprehensive ({file_size:,} bytes)")
                else:
                    self._add_result(f"content_quality_{file_path.replace('/', '_').replace('.md', '')}_brief", 
                                   False, ValidationLevel.MEDIUM,
                                   f"{file_path} could be more comprehensive ({file_size:,} bytes < {min_size:,})")
        
        # Check for code examples in documentation
        examples_found = 0
        for md_file in self.manager_dir.rglob("*.md"):
            if md_file.name.startswith('.'):
                continue
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                if "```python" in content or "```bash" in content or "```json" in content:
                    examples_found += 1
            except Exception:
                continue
        
        if examples_found >= 5:
            self._add_result("code_examples_abundant", True, ValidationLevel.MEDIUM,
                           f"Found code examples in {examples_found} documentation files")
        else:
            self._add_result("code_examples_sparse", False, ValidationLevel.MEDIUM,
                           f"Only found code examples in {examples_found} files - could add more")
    
    def _validate_performance(self):
        """Validate performance and usability aspects."""
        self._log("⚡ Validating Performance and Usability...")
        
        # Check for large files that might slow down Claude Code
        large_files = []
        for file_path in self.manager_dir.rglob("*.md"):
            if file_path.stat().st_size > 100000:  # > 100KB
                large_files.append((file_path, file_path.stat().st_size))
        
        if large_files:
            total_size = sum(size for _, size in large_files)
            if total_size > 500000:  # > 500KB total
                self._add_result("documentation_size_warning", False, ValidationLevel.LOW,
                               f"Documentation is quite large ({total_size:,} bytes) - consider splitting",
                               details=f"Large files: {[(f.name, s) for f, s in large_files]}")
            else:
                self._add_result("documentation_size_reasonable", True, ValidationLevel.LOW,
                               f"Documentation size is reasonable ({total_size:,} bytes)")
        
        # Check directory structure depth
        max_depth = 0
        for path in self.manager_dir.rglob("*"):
            depth = len(path.relative_to(self.manager_dir).parts)
            max_depth = max(max_depth, depth)
        
        if max_depth <= 6:
            self._add_result("directory_depth_reasonable", True, ValidationLevel.LOW,
                           f"Directory structure depth is reasonable ({max_depth})")
        else:
            self._add_result("directory_depth_deep", False, ValidationLevel.LOW,
                           f"Directory structure is quite deep ({max_depth}) - consider flattening")
    
    def _add_result(self, check_name: str, passed: bool, level: ValidationLevel, 
                    message: str, details: str = None, suggestions: List[str] = None):
        """Add validation result."""
        result = ValidationResult(
            check_name=check_name,
            passed=passed,
            level=level,
            message=message,
            details=details,
            suggestions=suggestions or []
        )
        self.results.append(result)
        
        if self.verbose:
            status = "✅" if passed else "❌"
            print(f"  {status} [{level.value.upper()}] {message}")
            if details and self.verbose:
                print(f"    Details: {details}")
    
    def _log(self, message: str):
        """Log message if verbose."""
        if self.verbose:
            print(message)
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive validation report."""
        # Calculate statistics
        total_checks = len(self.results)
        passed_checks = sum(1 for r in self.results if r.passed)
        critical_failures = [r for r in self.results if not r.passed and r.level == ValidationLevel.CRITICAL]
        high_failures = [r for r in self.results if not r.passed and r.level == ValidationLevel.HIGH]
        
        # Calculate Coleman framework coverage
        coleman_checks = [r for r in self.results if any(term in r.check_name.lower() 
                         for term in ['claude_md', 'examples', 'commands', 'templates', 'prps', 'initial'])]
        coleman_passed = sum(1 for r in coleman_checks if r.passed)
        coleman_coverage = (coleman_passed / len(coleman_checks)) * 100 if coleman_checks else 0
        
        # Overall score calculation
        level_weights = {
            ValidationLevel.CRITICAL: 4,
            ValidationLevel.HIGH: 3,
            ValidationLevel.MEDIUM: 2,
            ValidationLevel.LOW: 1
        }
        
        total_weight = sum(level_weights[r.level] for r in self.results)
        passed_weight = sum(level_weights[r.level] for r in self.results if r.passed)
        weighted_score = (passed_weight / total_weight) * 100 if total_weight else 0
        
        return {
            "summary": {
                "total_checks": total_checks,
                "passed_checks": passed_checks,
                "success_rate": (passed_checks / total_checks) * 100 if total_checks else 0,
                "weighted_score": weighted_score,
                "coleman_coverage": coleman_coverage
            },
            "failures": {
                "critical": len(critical_failures),
                "high": len(high_failures),
                "medium": len([r for r in self.results if not r.passed and r.level == ValidationLevel.MEDIUM]),
                "low": len([r for r in self.results if not r.passed and r.level == ValidationLevel.LOW])
            },
            "recommendations": self._generate_recommendations(),
            "coleman_compliance": self._assess_coleman_compliance(),
            "results": [
                {
                    "check": r.check_name,
                    "passed": r.passed,
                    "level": r.level.value,
                    "message": r.message,
                    "details": r.details,
                    "suggestions": r.suggestions
                }
                for r in self.results
            ]
        }
    
    def _generate_recommendations(self) -> List[str]:
        """Generate top recommendations based on validation results."""
        recommendations = []
        
        # Critical issues first
        critical_failures = [r for r in self.results if not r.passed and r.level == ValidationLevel.CRITICAL]
        for failure in critical_failures:
            recommendations.extend(failure.suggestions)
        
        # High priority issues
        high_failures = [r for r in self.results if not r.passed and r.level == ValidationLevel.HIGH]
        for failure in high_failures[:3]:  # Top 3
            recommendations.extend(failure.suggestions)
        
        return list(set(recommendations))  # Remove duplicates
    
    def _assess_coleman_compliance(self) -> Dict[str, Any]:
        """Assess compliance with Coleman Context Engineering framework."""
        components = {
            "c_instr": [r for r in self.results if "claude_md" in r.check_name or "readme" in r.check_name],
            "c_know": [r for r in self.results if "example" in r.check_name or "pattern" in r.check_name],
            "c_tools": [r for r in self.results if "command" in r.check_name or "claude_settings" in r.check_name],
            "c_mem": [r for r in self.results if "template" in r.check_name or "initial" in r.check_name],
            "c_state": [r for r in self.results if "prp" in r.check_name or "validation" in r.check_name],
            "c_query": [r for r in self.results if "initial" in r.check_name or "feature" in r.check_name]
        }
        
        compliance = {}
        for component, checks in components.items():
            if checks:
                passed = sum(1 for c in checks if c.passed)
                total = len(checks)
                compliance[component] = {
                    "score": (passed / total) * 100,
                    "passed": passed,
                    "total": total
                }
            else:
                compliance[component] = {"score": 0, "passed": 0, "total": 0}
        
        overall_coleman = sum(c["score"] for c in compliance.values()) / len(compliance)
        
        return {
            "overall_score": overall_coleman,
            "components": compliance,
            "status": "excellent" if overall_coleman >= 90 else
                     "good" if overall_coleman >= 80 else
                     "needs_improvement" if overall_coleman >= 60 else
                     "critical"
        }

def main():
    """Main validation entry point."""
    parser = argparse.ArgumentParser(
        description="Validate Manager Context Engineering system for Coleman framework and Claude Code compliance"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--check", choices=["all", "structure", "content", "coleman", "claude"], 
                       default="all", help="Validation focus area")
    parser.add_argument("--output", choices=["text", "json"], default="text", help="Output format")
    parser.add_argument("--manager-dir", default=".", help="Manager directory path")
    
    args = parser.parse_args()
    
    # Initialize validator
    manager_dir = Path(args.manager_dir).resolve()
    validator = ContextEngineeringValidator(manager_dir, args.verbose)
    
    print("🎯 MANAGER CONTEXT ENGINEERING VALIDATION")
    print("=" * 60)
    print(f"Manager Directory: {manager_dir}")
    print(f"Focus: {args.check}")
    print("=" * 60)
    
    # Run validations
    results = validator.run_all_validations()
    
    # Generate report
    report = validator.generate_report()
    
    if args.output == "json":
        print(json.dumps(report, indent=2))
        return 0
    
    # Text output
    print("\n📊 VALIDATION SUMMARY")
    print("=" * 60)
    
    summary = report["summary"]
    print(f"Total Checks: {summary['total_checks']}")
    print(f"Passed: {summary['passed_checks']} ({summary['success_rate']:.1f}%)")
    print(f"Weighted Score: {summary['weighted_score']:.1f}%")
    print(f"Coleman Coverage: {summary['coleman_coverage']:.1f}%")
    
    # Show failures by level
    failures = report["failures"]
    if failures["critical"] > 0:
        print(f"❌ Critical Issues: {failures['critical']}")
    if failures["high"] > 0:
        print(f"⚠️  High Priority Issues: {failures['high']}")
    if failures["medium"] > 0:
        print(f"📋 Medium Priority Issues: {failures['medium']}")
    if failures["low"] > 0:
        print(f"💡 Low Priority Issues: {failures['low']}")
    
    # Coleman compliance
    coleman = report["coleman_compliance"]
    print(f"\n🧠 Coleman Framework Compliance: {coleman['overall_score']:.1f}% ({coleman['status']})")
    
    for component, data in coleman["components"].items():
        if data["total"] > 0:
            print(f"  {component}: {data['score']:.1f}% ({data['passed']}/{data['total']})")
    
    # Top recommendations
    recommendations = report["recommendations"]
    if recommendations:
        print(f"\n🎯 TOP RECOMMENDATIONS:")
        for i, rec in enumerate(recommendations[:5], 1):
            print(f"  {i}. {rec}")
    
    # Determine exit code
    if failures["critical"] > 0:
        print("\n❌ CRITICAL ISSUES FOUND - Must be resolved")
        return 2
    elif summary["weighted_score"] >= 85:
        print("\n🎉 EXCELLENT - Context engineering system is well configured!")
        return 0
    elif summary["weighted_score"] >= 70:
        print("\n✅ GOOD - Context engineering system is functional with room for improvement")
        return 0
    else:
        print("\n⚠️  NEEDS IMPROVEMENT - Context engineering system needs attention")
        return 1

if __name__ == "__main__":
    sys.exit(main())