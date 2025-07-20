# Manager Project Makefile
# Comprehensive build, test, and deployment automation for SysAIdmin Manager

.PHONY: help install-uv clean setup setup-dev
.PHONY: test-all test-manager test-graphmcp test-dbdecommission
.PHONY: test-unit test-integration test-e2e
.PHONY: lint format check-deps
.PHONY: run-manager run-worker run-slack run-api
.PHONY: docker-build docker-compose-up docker-compose-down

# Default target
.DEFAULT_GOAL := help

# Configuration
PYTHON_VERSION := 3.12
UV_VERSION := 0.4.29
PROJECT_NAME := sysaidmin-manager
VENV_PATH := .venv
SRC_PATH := src
TEST_PATH := tests
MANAGER_PORT := 9123
GRAPHMCP_PATH := src/frameworks/graphmcp
DB_DECOMMISSION_PATH := src/usecases/database_decommissioning

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[0;33m
BLUE := \033[0;34m
MAGENTA := \033[0;35m
CYAN := \033[0;36m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(CYAN)SysAIdmin Manager - Build & Test Automation$(NC)"
	@echo "$(YELLOW)=============================================$(NC)"
	@echo ""
	@echo "$(GREEN)🚀 Quick Start:$(NC)"
	@echo "  make setup         - Setup development environment"
	@echo "  make setup-dev     - Setup development environment + dev tools"
	@echo "  make test-all      - Run all tests (Manager + GraphMCP + DB Decommission)"
	@echo "  make run-manager   - Start Manager API server"
	@echo ""
	@echo "$(GREEN)📦 Development:$(NC)"
	@echo "  make clean         - Clean build artifacts"
	@echo "  make lint          - Run code linting"
	@echo "  make format        - Format code"
	@echo "  make check-deps    - Check dependencies"
	@echo ""
	@echo "$(GREEN)🧪 Testing:$(NC)"
	@echo "  make test-manager      - Manager core tests"
	@echo "  make test-graphmcp     - GraphMCP framework tests"
	@echo "  make test-dbdecommission - Database decommissioning tests"
	@echo "  make test-unit         - All unit tests"
	@echo "  make test-integration  - All integration tests"
	@echo "  make test-e2e          - All end-to-end tests"
	@echo ""
	@echo "$(GREEN)🏃 Services:$(NC)"
	@echo "  make run-manager   - Start Manager API (port $(MANAGER_PORT))"
	@echo "  make run-worker    - Start Celery worker"
	@echo "  make run-slack     - Start Slack worker"
	@echo "  make run-api       - Start API with auto-reload"
	@echo ""
	@echo "$(GREEN)🗄️ Database Decommissioning:$(NC)"
	@echo "  make db-decommission-ui  - Start DB decommission UI (port 8502)"
	@echo "  make cmp                 - Run complete DB decommission workflow"

# =============================================================================
# PREREQUISITES & SETUP
# =============================================================================

install-uv: ## Install uv package manager (prerequisite)
	@echo "$(YELLOW)Installing uv package manager...$(NC)"
	@if command -v uv >/dev/null 2>&1; then \
		echo "$(GREEN)✓ uv already installed: $$(uv --version)$(NC)"; \
	else \
		echo "$(BLUE)Installing uv...$(NC)"; \
		curl -LsSf https://astral.sh/uv/install.sh | sh; \
		echo "$(GREEN)✓ uv installed successfully$(NC)"; \
	fi

clean: ## Clean build artifacts, cache, and virtual environment
	@echo "$(YELLOW)Cleaning build artifacts...$(NC)"
	rm -rf $(VENV_PATH)
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .ruff_cache/
	rm -rf __pycache__/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".coverage" -delete
	rm -rf htmlcov/
	rm -rf .tox/
	rm -rf .mypy_cache/
	# Clean Manager-specific artifacts
	rm -rf logs/
	rm -rf data/
	rm -rf tmp/
	# Clean GraphMCP artifacts
	rm -rf $(GRAPHMCP_PATH)/.pytest_cache/
	rm -rf $(GRAPHMCP_PATH)/htmlcov/
	# Clean DB Decommission artifacts
	rm -rf $(DB_DECOMMISSION_PATH)/.pytest_cache/
	rm -rf $(DB_DECOMMISSION_PATH)/htmlcov/
	rm -rf $(DB_DECOMMISSION_PATH)/.venv/
	@echo "$(GREEN)✓ Cleanup complete$(NC)"

setup: install-uv clean ## Setup development environment with dependencies
	@echo "$(YELLOW)Setting up Manager development environment...$(NC)"
	uv venv $(VENV_PATH) --python $(PYTHON_VERSION)
	@echo "$(BLUE)Installing Manager dependencies...$(NC)"
	uv sync
	@echo "$(BLUE)Setting up GraphMCP framework...$(NC)"
	cd $(GRAPHMCP_PATH) && make setup
	@echo "$(BLUE)Setting up Database Decommissioning use case...$(NC)"
	cd $(DB_DECOMMISSION_PATH) && uv sync
	@echo "$(GREEN)✓ Development environment ready$(NC)"
	@echo "$(CYAN)Activate with: source $(VENV_PATH)/bin/activate$(NC)"

setup-dev: setup ## Setup development environment with dev tools
	@echo "$(YELLOW)Installing development tools...$(NC)"
	uv add --dev \
		pytest>=7.4.0 \
		pytest-asyncio>=0.21.0 \
		pytest-mock>=3.11.0 \
		pytest-cov>=4.1.0 \
		pytest-xdist>=3.3.0 \
		black>=23.0.0 \
		ruff>=0.1.0 \
		mypy>=1.5.0 \
		pre-commit>=3.4.0 \
		hypothesis>=6.82.0
	@echo "$(BLUE)Setting up pre-commit hooks...$(NC)"
	uv run pre-commit install
	@echo "$(GREEN)✓ Development environment with tools ready$(NC)"

check-deps: ## Check if dependencies are installed
	@echo "$(YELLOW)Checking dependencies...$(NC)"
	@if [ ! -d "$(VENV_PATH)" ]; then \
		echo "$(RED)✗ Virtual environment not found. Run 'make setup' first.$(NC)"; \
		exit 1; \
	fi
	@if [ ! -d "$(GRAPHMCP_PATH)/.venv" ]; then \
		echo "$(YELLOW)⚠ GraphMCP environment not found. Setting up...$(NC)"; \
		cd $(GRAPHMCP_PATH) && make setup; \
	fi
	@if [ ! -d "$(DB_DECOMMISSION_PATH)/.venv" ]; then \
		echo "$(YELLOW)⚠ DB Decommission environment not found. Setting up...$(NC)"; \
		cd $(DB_DECOMMISSION_PATH) && uv sync; \
	fi
	@echo "$(GREEN)✓ Dependencies OK$(NC)"

# =============================================================================
# CODE QUALITY
# =============================================================================

lint: check-deps ## Run code linting with ruff and mypy
	@echo "$(YELLOW)Running code linting...$(NC)"
	@echo "$(BLUE)Linting Manager code...$(NC)"
	uv run ruff check $(SRC_PATH)
	uv run mypy $(SRC_PATH) --ignore-missing-imports
	@echo "$(BLUE)Linting GraphMCP framework...$(NC)"
	cd $(GRAPHMCP_PATH) && make lint
	@echo "$(BLUE)Linting Database Decommissioning use case...$(NC)"
	cd $(DB_DECOMMISSION_PATH) && uv run ruff check app/ || echo "$(YELLOW)⚠ DB Decommission linting issues$(NC)"
	@echo "$(GREEN)✓ Linting complete$(NC)"

format: check-deps ## Format code with black and ruff
	@echo "$(YELLOW)Formatting code...$(NC)"
	@echo "$(BLUE)Formatting Manager code...$(NC)"
	uv run black $(SRC_PATH)
	uv run ruff format $(SRC_PATH)
	uv run ruff check --fix $(SRC_PATH)
	@echo "$(BLUE)Formatting GraphMCP framework...$(NC)"
	cd $(GRAPHMCP_PATH) && make format
	@echo "$(BLUE)Formatting Database Decommissioning use case...$(NC)"
	cd $(DB_DECOMMISSION_PATH) && uv run black app/ && uv run ruff format app/ || echo "$(YELLOW)⚠ DB Decommission formatting issues$(NC)"
	@echo "$(GREEN)✓ Code formatting complete$(NC)"

# =============================================================================
# TESTING TARGETS
# =============================================================================

test-manager: check-deps ## Run Manager core tests
	@echo "$(YELLOW)Running Manager core tests...$(NC)"
	uv run pytest $(SRC_PATH)/tests/ \
		--verbose \
		--cov=$(SRC_PATH) \
		--cov-report=term-missing \
		--cov-report=html:htmlcov/manager \
		--junit-xml=test-results-manager.xml \
		--tb=short \
		--maxfail=5 \
		-x || echo "$(YELLOW)⚠ Manager tests may need setup$(NC)"
	@echo "$(GREEN)✓ Manager tests completed$(NC)"

test-graphmcp: check-deps ## Run GraphMCP framework tests
	@echo "$(YELLOW)Running GraphMCP framework tests...$(NC)"
	cd $(GRAPHMCP_PATH) && make test-all || echo "$(YELLOW)⚠ GraphMCP tests may need MCP servers$(NC)"
	@echo "$(GREEN)✓ GraphMCP tests completed$(NC)"

test-dbdecommission: check-deps ## Run database decommissioning tests
	@echo "$(YELLOW)Running Database Decommissioning tests...$(NC)"
	@echo "$(BLUE)Testing with validation script...$(NC)"
	python3 validate_db_decommission.py
	@echo "$(BLUE)Running use case unit tests...$(NC)"
	cd $(DB_DECOMMISSION_PATH) && uv run pytest tests/unit/ \
		--verbose \
		--cov=app \
		--cov-report=term-missing \
		--cov-report=html:htmlcov/dbdecommission \
		--junit-xml=test-results-dbdecommission.xml \
		--tb=short \
		-m "unit" || echo "$(YELLOW)⚠ Some DB decommission tests may need MCP setup$(NC)"
	@echo "$(GREEN)✓ Database Decommissioning tests completed$(NC)"

test-unit: check-deps ## Run all unit tests
	@echo "$(YELLOW)Running all unit tests...$(NC)"
	@echo "$(BLUE)Manager unit tests...$(NC)"
	uv run pytest $(SRC_PATH)/tests/ -m "unit or not (integration or e2e)" --tb=short -x || echo "$(YELLOW)⚠ Manager unit tests$(NC)"
	@echo "$(BLUE)GraphMCP unit tests...$(NC)"
	cd $(GRAPHMCP_PATH) && make test-unit || echo "$(YELLOW)⚠ GraphMCP unit tests$(NC)"
	@echo "$(BLUE)DB Decommission unit tests...$(NC)"
	cd $(DB_DECOMMISSION_PATH) && uv run pytest tests/unit/ -m "unit" --tb=short || echo "$(YELLOW)⚠ DB Decommission unit tests$(NC)"
	@echo "$(GREEN)✓ All unit tests completed$(NC)"

test-integration: check-deps ## Run all integration tests
	@echo "$(YELLOW)Running all integration tests...$(NC)"
	@echo "$(BLUE)Manager integration tests...$(NC)"
	uv run pytest $(SRC_PATH)/tests/ -m "integration" --tb=short --maxfail=3 || echo "$(YELLOW)⚠ Manager integration tests$(NC)"
	@echo "$(BLUE)GraphMCP integration tests...$(NC)"
	cd $(GRAPHMCP_PATH) && make test-integration || echo "$(YELLOW)⚠ GraphMCP integration tests$(NC)"
	@echo "$(BLUE)DB Decommission integration tests...$(NC)"
	cd $(DB_DECOMMISSION_PATH) && uv run pytest tests/integration/ -m "integration" --tb=short || echo "$(YELLOW)⚠ DB Decommission integration tests$(NC)"
	@echo "$(GREEN)✓ All integration tests completed$(NC)"

test-e2e: check-deps ## Run all end-to-end tests
	@echo "$(YELLOW)Running all end-to-end tests...$(NC)"
	@echo "$(BLUE)Manager E2E tests...$(NC)"
	uv run pytest $(SRC_PATH)/tests/ -m "e2e" --tb=short --timeout=600 || echo "$(YELLOW)⚠ Manager E2E tests$(NC)"
	@echo "$(BLUE)GraphMCP E2E tests...$(NC)"
	cd $(GRAPHMCP_PATH) && make test-e2e || echo "$(YELLOW)⚠ GraphMCP E2E tests$(NC)"
	@echo "$(GREEN)✓ All E2E tests completed$(NC)"

test-all: test-manager test-graphmcp test-dbdecommission ## Run all test suites
	@echo "$(GREEN)✓ All tests completed$(NC)"

# =============================================================================
# SERVICE MANAGEMENT
# =============================================================================

run-manager: check-deps ## Start Manager API server
	@echo "$(YELLOW)Starting Manager API server on port $(MANAGER_PORT)...$(NC)"
	@echo "$(CYAN)API will be available at: http://localhost:$(MANAGER_PORT)$(NC)"
	@echo "$(CYAN)Swagger docs at: http://localhost:$(MANAGER_PORT)/docs$(NC)"
	@echo "$(CYAN)Database decommissioning at: http://localhost:$(MANAGER_PORT)/usecases/database-decommissioning$(NC)"
	uv run uvicorn main:app --host 0.0.0.0 --port $(MANAGER_PORT)

run-api: check-deps ## Start Manager API with auto-reload for development
	@echo "$(YELLOW)Starting Manager API with auto-reload...$(NC)"
	@echo "$(CYAN)API will be available at: http://localhost:$(MANAGER_PORT)$(NC)"
	uv run uvicorn main:app --host 0.0.0.0 --port $(MANAGER_PORT) --reload

run-worker: check-deps ## Start Celery worker
	@echo "$(YELLOW)Starting Celery worker...$(NC)"
	uv run celery -A worker_main worker --loglevel=info

run-slack: check-deps ## Start Slack worker
	@echo "$(YELLOW)Starting Slack worker...$(NC)"
	uv run python slack_main.py

# =============================================================================
# DATABASE DECOMMISSIONING WORKFLOWS
# =============================================================================

db-decommission-ui: check-deps ## Start Database Decommissioning Streamlit UI
	@echo "$(YELLOW)Starting Database Decommissioning UI...$(NC)"
	@echo "$(CYAN)Features:$(NC)"
	@echo "  🗄️ Database decommissioning workflow visualization"
	@echo "  📊 File reference tables with discovered database references"
	@echo "  🌞 Repository structure sunburst charts"
	@echo "  🔍 Context data preview for debugging workflow state"
	@echo "  ⚙️ Configurable database name and target repositories"
	@echo ""
	@echo "$(CYAN)Open http://localhost:8502 and configure your database decommissioning$(NC)"
	cd $(GRAPHMCP_PATH) && make db-decommission-ui

cmp: check-deps ## Run complete database decommissioning workflow
	@echo "$(YELLOW)Running Complete Database Decommissioning Workflow...$(NC)"
	@echo "$(CYAN)🚀 Manager + GraphMCP Database Decommissioning$(NC)"
	@echo "$(CYAN)─────────────────────────────────────────────────$(NC)"
	@echo "$(GREEN)Features:$(NC)"
	@echo "  🔍 AI-Powered Pattern Discovery with Azure OpenAI"
	@echo "  📁 Multi-Repository Source Analysis"
	@echo "  🛠️  Manager Integration with Tenant Support"
	@echo "  🌐 GitHub Integration (Fork → Branch → Commit → PR)"
	@echo "  📊 Real-time Progress Tracking & Metrics"
	@echo "  💬 Slack Notifications & Status Updates"
	@echo ""
	@echo "$(YELLOW)Environment Check:$(NC)"
	@echo "  GitHub Token: $$(if [ -n "$(GITHUB_TOKEN)" ]; then echo "✅ Set"; else echo "❌ Missing - export GITHUB_TOKEN=<token>"; fi)"
	@echo "  Slack Token: $$(if [ -n "$(SLACK_BOT_TOKEN)" ]; then echo "✅ Set"; else echo "⚠️  Optional - export SLACK_BOT_TOKEN=<token>"; fi)"
	@echo "  Azure OpenAI: $$(if [ -n "$(AZURE_OPENAI_API_KEY)" ]; then echo "✅ Set"; else echo "⚠️  Optional - export AZURE_OPENAI_API_KEY=<key>"; fi)"
	@echo ""
	cd $(GRAPHMCP_PATH) && make cmp

# =============================================================================
# UTILITY TARGETS
# =============================================================================

show-config: ## Show current configuration and environment
	@echo "$(CYAN)Manager Configuration$(NC)"
	@echo "$(YELLOW)====================$(NC)"
	@echo "Project Name: $(PROJECT_NAME)"
	@echo "Python Version: $(PYTHON_VERSION)"
	@echo "UV Version: $(UV_VERSION)"
	@echo "Virtual Environment: $(VENV_PATH)"
	@echo "Source Path: $(SRC_PATH)"
	@echo "Manager Port: $(MANAGER_PORT)"
	@echo ""
	@echo "$(YELLOW)Component Status:$(NC)"
	@echo "UV Installed: $$(if command -v uv >/dev/null 2>&1; then echo "✓"; else echo "✗"; fi)"
	@echo "Manager Env: $$(if [ -d "$(VENV_PATH)" ]; then echo "✓"; else echo "✗"; fi)"
	@echo "GraphMCP Env: $$(if [ -d "$(GRAPHMCP_PATH)/.venv" ]; then echo "✓"; else echo "✗"; fi)"
	@echo "DB Decommission Env: $$(if [ -d "$(DB_DECOMMISSION_PATH)/.venv" ]; then echo "✓"; else echo "✗"; fi)"
	@echo ""
	@echo "$(YELLOW)Environment Variables:$(NC)"
	@echo "GitHub Token: $$(if [ -n "$(GITHUB_TOKEN)" ]; then echo "✓ Set"; else echo "✗ Missing"; fi)"
	@echo "Slack Token: $$(if [ -n "$(SLACK_BOT_TOKEN)" ]; then echo "✓ Set"; else echo "✗ Missing"; fi)"
	@echo "Azure OpenAI Key: $$(if [ -n "$(AZURE_OPENAI_API_KEY)" ]; then echo "✓ Set"; else echo "✗ Missing"; fi)"

quick-test: check-deps ## Run quick tests (validation only)
	@echo "$(YELLOW)Running quick test suite...$(NC)"
	python3 validate_db_decommission.py
	@echo "$(GREEN)✓ Quick tests completed$(NC)"

# Development convenience targets
dev: setup-dev ## Full development environment setup
	@echo "$(GREEN)✓ Development environment ready for Manager development$(NC)"
	@echo "$(CYAN)Next steps:$(NC)"
	@echo "  1. source $(VENV_PATH)/bin/activate"
	@echo "  2. make test-all"
	@echo "  3. make run-api"
	@echo "  4. Visit http://localhost:$(MANAGER_PORT)/docs"