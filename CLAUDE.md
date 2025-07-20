# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SysAIdmin (Ovora) Manager is the core backend component of an AI-powered system administration platform. This component handles:

1. **API Services** (Python/FastAPI): REST API with AI capabilities, task queue, and Slack integration
2. **AI Processing**: Azure OpenAI integration with LangChain/LangGraph for intelligent automation
3. **Workflow Orchestration**: GraphMCP framework for complex AI-driven workflows
4. **Microservices Tools**: Independent FastAPI services for specialized functionality

## Core Architecture

### Service Architecture
- **Manager**: Microservices-based with independent processes:
    - `main.py` → API service (FastAPI, port 9123)
  - `worker_main.py` → Celery worker for background tasks
  - `slack_main.py` → Slack integration worker
- **Integration Layer**: Connects with Agent (Go) and UI (Streamlit) components
- **Tool Services**: Independent microservices for specialized operations

### Data Flow
- External Agents → Manager API → MongoDB (storage)
- Manager → Prometheus (metrics) → External UI (visualization)
- Manager → Slack (notifications) → Users
- Manager → Azure OpenAI (AI processing) → Tools execution
- Manager → GraphMCP Framework → Multi-service orchestration

## Common Development Commands

### Manager (Python)
```bash
cd manager
uv sync                                    # Install dependencies
uv run uvicorn main:app --port 9123 --reload  # Run API
uv run celery -A worker_main worker --loglevel=info  # Run worker
uv run celery -A worker_main beat --loglevel=info    # Run scheduler
uv run python slack_main.py               # Run Slack worker
```

### Testing
```bash
cd manager
uv run pytest                            # Run all tests
uv run pytest tests/unit/               # Unit tests only
uv run pytest tests/integration/        # Integration tests only
uv run pytest -k "test_specific"        # Run specific test
```

### Development Environment
```bash
# Start infrastructure services
cd manager && docker-compose up -d      # MongoDB, Redis, Prometheus

# Alternative infrastructure setup (using podman as documented)
podman run -d -p 27017:27017 --name mongo mongo
podman run -d -p 6379:6379 --name redis redis
podman run -d -p 9090:9090 -v $(pwd)/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml --name prom prom/prometheus

# For GraphMCP development (advanced DB decommissioning)
cd manager/src/frameworks/graphmcp
make setup                               # Setup environment
make test-all                           # Run all tests
make demo                               # Run demo workflow
```

## Key Architecture Patterns

### Configuration Management
- Environment variables centralized in `manager/src/config.py`
- Required variables: `AZURE_OPENAI_API_KEY`, `MONGO_DB_URI`, `PROMETHEUS_ADDRESS`
- Optional: `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN`

### Database Patterns
- **Primary**: MongoDB via `DatabaseClient` wrapper
- **Collections**: incidents, inventory, tasks, questions, checkpoints
- **Connection**: Context manager pattern with proper cleanup

### AI Integration
- **Backend**: Azure OpenAI with LangChain/LangGraph
- **Monitoring**: Langfuse for observability
- **Tools**: Structured tool definitions for agent actions

### Microservices Tools
- Each tool is a separate FastAPI service with own `pyproject.toml`
- Examples: `manager/src/tools/confluence/`, `manager/src/tools/db_servers_cmdb/`
- Pattern: Dockerized services with standardized API

### Task Processing
- **Queue**: Celery with Redis broker
- **Key tasks**: `run_incident_assistant`, `scheduler.analyze_free_space`
- **Monitoring**: Prometheus metrics for task performance

## Development Workflow

### Package Management
- **Python components**: Use `uv` (modern pip replacement)
- **Dependencies**: Isolated per component

### Testing Strategy
- **Framework**: pytest with comprehensive configuration
- **Categories**: Unit, integration, performance, E2E (via markers)
- **Coverage**: Enabled with HTML reports
- **Configuration**: `pytest.ini` files in relevant directories

### Code Organization
- **Modular structure**: Clear domain separation (`modules/`, `tools/`, `usecases/`)
- **Database access**: Consistent patterns with dedicated DB classes
- **API structure**: FastAPI with router-based organization

## Important File Locations

### Configuration Files
- `manager/pyproject.toml` - Python dependencies and project config
- `manager/docker-compose.yaml` - Development infrastructure

### Key Source Files
- `manager/src/config.py` - Environment configuration
- `manager/src/api.py` - Main API routes
- `manager/src/database/client.py` - Database connection
- `manager/src/llm/llm.py` - AI integration

### Testing
- `manager/src/tests/` - Test suites
- `conftest.py` - Test configuration and fixtures
- `pytest.ini` - Test runner configuration

## Specialized Components

### GraphMCP Framework
- **Location**: `manager/src/frameworks/graphmcp/`
- **Purpose**: Shared workflow framework for AI-driven automation workflows
- **Features**: Pattern discovery, GitHub integration, workflow orchestration, MCP client coordination
- **Usage**: Available for all use cases via `from frameworks.graphmcp import ...`
- **Development**: `cd manager/src/frameworks/graphmcp && make setup && make demo`

#### Core Architecture
```
GraphMCP Framework
├── clients/                    # MCP client implementations
│   ├── base.py                # Abstract base client with connection management
│   ├── github.py              # GitHub repository operations
│   ├── slack.py               # Slack notifications
│   ├── repomix.py             # Repository packaging and analysis
│   └── filesystem.py          # File system operations
├── workflows/                  # Workflow orchestration engine
│   ├── builder.py             # Fluent API for workflow construction
│   ├── context.py             # Shared state management
│   └── ruliade/               # Rule-based workflow patterns
├── concrete/                   # Concrete workflow implementations
│   ├── db_decommission/       # Database decommissioning workflow
│   ├── file_decommission_processor.py  # File processing engine
│   └── pattern_discovery.py   # AI-powered pattern detection
├── utils/                      # Reusable utilities
│   ├── parameter_service.py   # Configuration management
│   ├── monitoring.py          # System monitoring
│   └── error_handling.py      # Error handling system
└── graphmcp_logging/           # Structured logging system
```

#### Key Patterns for Future Workflows

**1. Multi-Client Orchestration Pattern**
```python
# Standard pattern for coordinating multiple MCP clients
github_client = GitHubMCPClient(context.config.config_path)
slack_client = SlackMCPClient(context.config.config_path)
repomix_client = RepomixMCPClient(context.config.config_path)

# Cache clients in workflow context
context._clients['ovr_github'] = github_client
context._clients['ovr_slack'] = slack_client
context._clients['ovr_repomix'] = repomix_client
```

**2. Fluent Workflow Builder Pattern**
```python
workflow = (WorkflowBuilder("workflow_name", config_path)
    .with_config(max_parallel_steps=4, default_timeout=120)
    .step_auto("validate", "Validation", validate_step)  # PREFERRED
    .github_analyze_repo("analyze", repo_url)
    .slack_post("notify", channel_id, message)
    .build())
```

**Step Method Preference Order:**
1. `step_auto()` - **PREFERRED** - Automatically wraps functions to match step signature
2. `step()` - Generic step method with delegate parameter
3. `custom_step()` - Legacy method, avoid unless necessary

**3. Strategy-Based File Processing Pattern**
```python
def _determine_strategy(self, file_path: Path) -> str:
    if file_path.suffix in ['.tf']:
        return 'infrastructure'
    elif file_path.suffix in ['.yml', '.yaml']:
        return 'configuration'
    elif file_path.suffix in ['.py', '.sh']:
        return 'code'
    return 'documentation'
```

**4. Graceful Degradation with Caching**
```python
try:
    existing_data = load_cached_data(key, logger)
    if existing_data:
        logger.log_info(f"Using cached data for {key}")
        return existing_data
    else:
        # Fallback to real processing
        result = await client.process_data(params)
        save_to_cache(result, key, logger)
        return result
except Exception as e:
    logger.log_error(f"Processing failed", exception=e)
    return {"success": False, "error": str(e)}
```

**5. MCP Server Configuration Pattern**
```json
{
  "mcpServers": {
    "ovr_github": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-github"],
      "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": "$TOKEN"}
    },
    "ovr_slack": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-slack"],
      "env": {"SLACK_BOT_TOKEN": "$TOKEN"}
    }
  }
}
```

**6. Structured Logging Pattern**
```python
from graphmcp_logging import get_logger, LoggingConfig

config = LoggingConfig.from_env()
logger = get_logger(workflow_id=f"workflow_{name}", config=config)

logger.log_workflow_start(params, config)
logger.log_step_start("step_name", "Description...")
logger.log_table("Results", table_data)
logger.log_step_end("step_name", result, success=True)
```

**Development Commands**:
```bash
# Setup framework
cd manager/src/frameworks/graphmcp
make setup                      # Install dependencies
make test-all                   # Run all tests
make demo                       # Run demo workflow

# Run specific workflows
make cmp DB=postgres_air        # Complete DB decommissioning
python run_workflow.py --name workflow_name --config mcp_config.json
```

### DB Decommissioning Workflow
- **Location**: `manager/src/usecases/unused_db_decommissioning/`
- **Framework**: Uses GraphMCP framework
- **Usage**: Advanced AI-driven database decommissioning automation

### Atlassian Integrations

#### Confluence Tool
- **Location**: `manager/src/tools/confluence/`
- **Main Client**: `app/confluence.py` - Core Confluence REST API client
- **Features**: 
  - Full page management (CRUD operations)
  - Vector search with ChromaDB integration
  - Bulk processing with background jobs
  - Attachment management
  - Health monitoring and detailed status checks
  - Runbook content processing and categorization
- **Dependencies**: `atlassian-python-api>=3.41.0`, `chromadb>=0.4.0`, `sentence-transformers>=2.2.0`

**API Endpoints**:
- `GET/PUT/DELETE/POST /pages/{page_id}` - Page management
- `GET /search` - Text-based search
- `POST /search/vector` - Semantic vector search
- `POST /bulk/process` - Start bulk processing job
- `GET /jobs/{job_id}` - Job status tracking
- `POST /pages/{page_id}/attachments` - Upload attachments
- `GET /health/detailed` - System health check

**Environment Variables**:
- `CONFLUENCE_URL` - Confluence instance URL
- `CONFLUENCE_USERNAME` - Username/email for authentication
- `CONFLUENCE_API_TOKEN` - API token for authentication
- `CONFLUENCE_TIMEOUT` - Request timeout (optional, default: 30s)

#### Jira Tool
- **Location**: `manager/src/tools/jira/`
- **Main Client**: `app/jira.py` - Jira REST API client using `python-jira`
- **Features**:
  - Ticket lifecycle management
  - Rich text formatting in comments (bold, italic, code, code blocks)
  - Workflow state transitions
- **Dependencies**: `jira>=3.6.0`

**API Endpoints**:
- `GET /tickets/{ticket_id}` - Retrieve ticket with description and comments
- `POST /tickets/{ticket_id}/comments` - Add formatted comment to ticket
- `PUT /tickets/{ticket_id}` - Close ticket (optionally with comment)

**Environment Variables**:
- `JIRA_URL` - Jira instance URL
- `JIRA_USERNAME` - Username/email for authentication
- `JIRA_API_TOKEN` - API token for authentication

**Authentication**: Both tools use HTTP Basic Auth with username/email and API tokens

**Development Commands**:
```bash
# Confluence tool
cd manager/src/tools/confluence
uv sync && uv run uvicorn app.api:app --port 8000 --reload

# Jira tool
cd manager/src/tools/jira
uv sync && uv run uvicorn app.api:app --port 8001 --reload
```

### Slack Integration
- **Worker**: `manager/slack_main.py`
- **Features**: Real-time notifications, interactive commands
- **Dependencies**: slack-bolt

## Environment Variables

### Required
- `AZURE_OPENAI_API_KEY` - Azure OpenAI API key
- `AZURE_OPENAI_ENDPOINT` - Azure OpenAI endpoint
- `MONGO_DB_URI` - MongoDB connection string
- `PROMETHEUS_ADDRESS` - Prometheus server address (e.g., http://localhost:9090)
- `MANAGER_API_ADDRESS` - Manager API address for Prometheus targets (e.g., localhost:9123)

### Optional
- `SLACK_BOT_TOKEN` - Slack bot token
- `SLACK_APP_TOKEN` - Slack app token
- `CELERY_BROKER_URL` - Redis URL (defaults to localhost)
- `METRICS_DIR` - Directory for metrics storage

### Atlassian Tools
- `CONFLUENCE_URL` - Confluence instance URL (e.g., https://your-domain.atlassian.net)
- `CONFLUENCE_USERNAME` - Username/email for Confluence authentication
- `CONFLUENCE_API_TOKEN` - API token for Confluence authentication
- `CONFLUENCE_TIMEOUT` - Request timeout (optional, default: 30s)
- `JIRA_URL` - Jira instance URL (e.g., https://your-domain.atlassian.net)
- `JIRA_USERNAME` - Username/email for Jira authentication
- `JIRA_API_TOKEN` - API token for Jira authentication

## Deployment

### Development
```bash
# Start all services
cd manager && docker-compose up -d     # Infrastructure
# Then start individual services as shown above
```

### Production
- **Kubernetes**: Helm charts in `deployment/helm/`
- **Containers**: Containerfiles for manager and UI
- **Monitoring**: Prometheus integration configured

### Container Build and Deploy
```bash
# Manager container
cd manager
docker build -t sysaidmin-manager -f Containerfile .
docker run \
  -e AZURE_OPENAI_API_KEY=${AZURE_OPENAI_API_KEY} \
  -e AZURE_OPENAI_ENDPOINT=${AZURE_OPENAI_ENDPOINT} \
  -e MONGO_DB_URI=${MONGO_DB_URI} \
  -e SLACK_BOT_TOKEN=${SLACK_BOT_TOKEN} \
  sysaidmin-manager:latest
```

## Testing Philosophy

- **Unit tests**: Fast, isolated, no external dependencies
- **Integration tests**: Test component interactions
- **E2E tests**: Full workflow testing
- **Performance tests**: Resource usage and timing
- Use pytest markers to categorize tests appropriately

## Context Engineering Integration

This manager component is part of a larger Ovora ecosystem that implements comprehensive context engineering principles:

### Context Engineering Principles
- **Comprehensive Context**: Full project understanding through structured documentation
- **Detailed Examples**: Real-world implementation patterns and code snippets
- **Validation Gates**: Quality assurance through automated testing and validation
- **Consistent Patterns**: Established conventions across all components

### Development Guidelines
When developing features for the manager component:

1. **Follow Established Patterns**: Reference existing implementations in `src/` directories
2. **Use GraphMCP Framework**: Leverage `frameworks/graphmcp/` for complex workflows
3. **Maintain Testing Standards**: Ensure comprehensive test coverage
4. **Document Thoroughly**: Update relevant documentation and examples
5. **Validate Continuously**: Use validation frameworks for quality assurance

### Integration with Parent Project
The manager maintains compatibility with the broader Ovora ecosystem:
- **Agent Integration**: Secure communication with Go-based monitoring agents
- **UI Integration**: API endpoints for Streamlit dashboard
- **Shared Standards**: Common patterns and conventions across components

## Committing changes with git

When the user asks you to create a new git commit, follow these steps carefully:

1. You have the capability to call multiple tools in a single response. When multiple independent pieces of information are requested, batch your tool calls together for optimal performance. ALWAYS run the following bash commands in parallel, each using the Bash tool:
  - Run a git status command to see all untracked files.
  - Run a git diff command to see both staged and unstaged changes that will be committed.
  - Run a git log command to see recent commit messages, so that you can follow this repository's commit message style.
2. Analyze all staged changes (both previously staged and newly added) and draft a commit message:
  - Summarize the nature of the changes (eg. new feature, enhancement to an existing feature, bug fix, refactoring, test, docs, etc.). Ensure the message accurately reflects the changes and their purpose (i.e. "add" means a wholly new feature, "update" means an enhancement to an existing feature, "fix" means a bug fix, etc.).
  - Check for any sensitive information that shouldn't be committed
  - Draft a concise (1-2 sentences) commit message that focuses on the "why" rather than the "what"
  - Ensure it accurately reflects the changes and their purpose
3. You have the capability to call multiple tools in a single response. When multiple independent pieces of information are requested, batch your tool calls together for optimal performance. ALWAYS run the following commands in parallel:
   - Add relevant untracked files to the staging area.
   - Create the commit with a message ending with:
   🤖 Generated with [Claude Code](https://claude.ai/code)

   Co-Authored-By: Claude <noreply@anthropic.com>
   - Run git status to make sure the commit succeeded.
4. If the commit fails due to pre-commit hook changes, retry the commit ONCE to include these automated changes. If it fails again, it usually means a pre-commit hook is preventing the commit. If the commit succeeds but you notice that files were modified by the pre-commit hook, you MUST amend your commit to include them.

Important notes:
- NEVER update the git config
- NEVER run additional commands to read or explore code, besides git bash commands
- NEVER use the TodoWrite or Task tools
- DO NOT push to the remote repository unless the user explicitly asks you to do so
- IMPORTANT: Never use git commands with the -i flag (like git rebase -i or git add -i) since they require interactive input which is not supported.
- If there are no changes to commit (i.e., no untracked files and no modifications), do not create an empty commit
- In order to ensure good formatting, ALWAYS pass the commit message via a HEREDOC, a la this example:
<example>
git commit -m "$(cat <<'EOF'
   Commit message here.

   🤖 Generated with [Claude Code](https://claude.ai/code)

   Co-Authored-By: Claude <noreply@anthropic.com>
   EOF
   )"
</example>

## Creating pull requests
Use the gh command via the Bash tool for ALL GitHub-related tasks including working with issues, pull requests, checks, and releases. If given a Github URL use the gh command to get the information needed.

IMPORTANT: When the user asks you to create a pull request, follow these steps carefully:

1. You have the capability to call multiple tools in a single response. When multiple independent pieces of information are requested, batch your tool calls together for optimal performance. ALWAYS run the following bash commands in parallel using the Bash tool, in order to understand the current state of the branch since it diverged from the main branch:
   - Run a git status command to see all untracked files
   - Run a git diff command to see both staged and unstaged changes that will be committed
   - Check if the current branch tracks a remote branch and is up to date with the remote, so you know if you need to push to the remote
   - Run a git log command and `git diff [base-branch]...HEAD` to understand the full commit history for the current branch (from the time it diverged from the base branch)
2. Analyze all changes that will be included in the pull request, making sure to look at all relevant commits (NOT just the latest commit, but ALL commits that will be included in the pull request!!!), and draft a pull request summary
3. You have the capability to call multiple tools in a single response. When multiple independent pieces of information are requested, batch your tool calls together for optimal performance. ALWAYS run the following commands in parallel:
   - Create new branch if needed
   - Push to remote with -u flag if needed
   - Create PR using gh pr create with the format below. Use a HEREDOC to pass the body to ensure correct formatting.
<example>
gh pr create --title "the pr title" --body "$(cat <<'EOF'
## Summary
<1-3 bullet points>

## Test plan
[Checklist of TODOs for testing the pull request...]

🤖 Generated with [Claude Code](https://claude.ai/code)
EOF
)"
</example>

Important:
- NEVER update the git config
- DO NOT use the TodoWrite or Task tools
- Return the PR URL when you're done, so the user can see it

## Other common operations
- View comments on a Github PR: gh api repos/foo/bar/pulls/123/comments