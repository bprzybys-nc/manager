# Ovora Manager: AI-Powered System Administration Platform

## Project Overview and Context

Ovora Manager (SysAIdmin) is a comprehensive AI-powered system administration platform designed to automate incident response, system monitoring, and operational tasks. The Manager component serves as the backend orchestration layer, leveraging Azure OpenAI, advanced workflow orchestration, and microservices architecture to provide intelligent system administration capabilities.

This document provides comprehensive context for developing new features within the Manager component and its integration with the broader Ovora ecosystem.

## Core Architecture

### System Components

1. **Manager (This Component) - Python/FastAPI**
   - Backend API with AI capabilities
   - Task queue processing with Celery
   - Slack integration for notifications
   - Microservices architecture with tool isolation
   - AI-powered incident response and automation
   - GraphMCP framework for workflow orchestration

2. **Agent (Go) - External Component**
   - Lightweight monitoring agent
   - Deployed on target machines
   - Periodic data collection and reporting
   - Secure communication with Manager

3. **UI (Streamlit) - External Component**
   - Web dashboard for visualization
   - Auth0 authentication
   - Real-time metrics and incident management
   - Interactive workflow monitoring

### Manager Component Architecture

The Manager component features a sophisticated microservices architecture:

```
manager/
├── src/
│   ├── frameworks/
│   │   └── graphmcp/              # Advanced workflow orchestration
│   ├── tools/                     # Microservice integrations
│   │   ├── confluence/           # Atlassian Confluence
│   │   ├── jira/                 # Atlassian Jira
│   │   ├── cmd_exec/             # Command execution
│   │   └── db_servers_cmdb/      # Database server CMDB
│   ├── modules/                   # Core business logic
│   ├── usecases/                  # Use case implementations
│   └── api.py                     # Main API routes
├── main.py                        # API service entry point
├── worker_main.py                 # Celery worker entry point
└── slack_main.py                  # Slack integration worker
```

### Key Technologies

- **AI/ML**: Azure OpenAI, LangChain, LangGraph, Langfuse
- **Backend**: FastAPI, Celery, Redis, MongoDB
- **Frontend**: Streamlit, Auth0 (UI component)
- **Monitoring**: Prometheus, custom metrics collection
- **Orchestration**: GraphMCP framework for workflow automation
- **Infrastructure**: Docker, Kubernetes, Helm charts

## Technical Requirements

### System Requirements
- **Python**: 3.12+ for Manager component
- **Go**: 1.21+ for Agent component (external)
- **Node.js**: 18+ for MCP server dependencies
- **Docker**: For containerized deployment
- **Kubernetes**: For production orchestration

### Performance Requirements
- **API Response Time**: < 500ms for standard operations
- **Database Operations**: < 100ms for simple queries
- **AI Operations**: < 30s for complex AI processing
- **Workflow Steps**: < 2 minutes per step (configurable)
- **Memory Usage**: < 512MB per service instance
- **CPU Usage**: < 80% sustained CPU usage

### Security Requirements
- **Authentication**: Auth0 for UI, API tokens for services
- **Data Encryption**: TLS 1.3 for data in transit
- **Secret Management**: Environment-based secret handling
- **Access Control**: Role-based access control
- **Input Validation**: Comprehensive validation and sanitization

## GraphMCP Framework

The GraphMCP framework is the core orchestration system within the Manager component that enables:

### Core Capabilities
- **Multi-Client Coordination**: GitHub, Slack, Repomix, filesystem operations
- **AI-Driven Automation**: Intelligent workflow steps with context awareness
- **Robust Error Handling**: Graceful degradation and comprehensive logging
- **Scalable Architecture**: Async-first design with connection pooling
- **Production-Ready**: Comprehensive testing, monitoring, and deployment

### Framework Architecture
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
│   └── preview_ui/            # Streamlit visualization
├── utils/                      # Reusable utilities
│   ├── parameter_service.py   # Configuration management
│   ├── monitoring.py          # System monitoring
│   └── error_handling.py      # Error handling system
└── graphmcp_logging/           # Structured logging system
```

### Key Patterns

1. **Workflow Builder**: Fluent API for constructing complex workflows
2. **MCP Client Integration**: Seamless integration with Model Context Protocol servers
3. **Strategy-Based Processing**: Intelligent file and data processing strategies
4. **Contextual State Management**: Shared context across workflow steps
5. **Structured Logging**: Comprehensive logging with performance metrics

### Context Engineering Integration

The GraphMCP framework implements advanced context engineering principles:

- **Comprehensive Context Assembly**: Complete context for AI-assisted development
- **Pattern-Based Implementation**: Consistent patterns across all implementations
- **Product Requirements Prompts (PRPs)**: Structured feature development process
- **Validation Gates**: Comprehensive quality assurance framework
- **Documentation-Driven Development**: Extensive examples and patterns

## Manager Component Integration Points

### Internal Architecture

#### Database Layer
- **Primary**: MongoDB via `DatabaseClient` wrapper
- **Collections**: incidents, inventory, tasks, questions, checkpoints
- **Connection**: Context manager pattern with proper cleanup

#### AI Integration
- **Backend**: Azure OpenAI with LangChain/LangGraph
- **Monitoring**: Langfuse for observability
- **Tools**: Structured tool definitions for agent actions

#### Microservices Tools
- Each tool is a separate FastAPI service with own `pyproject.toml`
- Examples: `src/tools/confluence/`, `src/tools/db_servers_cmdb/`
- Pattern: Dockerized services with standardized API

#### Task Processing
- **Queue**: Celery with Redis broker
- **Key tasks**: `run_incident_assistant`, `scheduler.analyze_free_space`
- **Monitoring**: Prometheus metrics for task performance

### External Integration Points

#### With Agent Component
- **Communication**: RESTful API over HTTP/HTTPS
- **Data Flow**: Agent → Manager API → MongoDB
- **Authentication**: API tokens and secure endpoints
- **Monitoring**: Prometheus metrics collection

#### With UI Component
- **Communication**: RESTful API over HTTP/HTTPS
- **Data Flow**: UI → Manager API → Business Logic
- **Authentication**: Auth0 integration for user sessions
- **Real-time Updates**: WebSocket or polling for live data

#### External Services
- **Atlassian**: Confluence and Jira integration via dedicated tools
- **GitHub**: Repository operations and PR management via GraphMCP
- **Slack**: Real-time notifications and interactions via GraphMCP and worker
- **Azure**: OpenAI services and cloud resources
- **Prometheus**: Metrics collection and monitoring

## Development Workflow

### Package Management
- **Python**: Use `uv` for dependency management
- **Go**: Standard `go mod` with version pinning (Agent component)
- **Isolation**: Component-specific dependencies with isolated environments

### Testing Strategy
- **Unit Tests**: Fast, isolated, comprehensive coverage (80% minimum)
- **Integration Tests**: Component interaction testing
- **E2E Tests**: Full workflow validation including external integrations
- **Performance Tests**: Resource usage and timing validation

### Code Organization
- **Modular Structure**: Clear domain separation within Manager
- **Microservices**: Each tool is a separate FastAPI service
- **Standardized APIs**: Consistent patterns across components
- **Documentation**: Comprehensive inline and external documentation

### Context Engineering Workflow

When developing new features for the Manager component:

1. **Feature Request**: Start with detailed `INITIAL.md` template
2. **Research**: Use `/research <feature_area>` to understand existing patterns
3. **Examples**: Use `/examples <pattern_type>` to find relevant patterns
4. **PRP Creation**: Use `/prp <feature_name>` to create comprehensive Product Requirements Prompt
5. **Implementation**: Use `/implement PRPs/active/<feature_name>.md` for structured implementation
6. **Validation**: Use `/validate <feature_name>` for thorough validation

## Configuration and Environment

### Required Environment Variables
- `AZURE_OPENAI_API_KEY`: Azure OpenAI API key
- `AZURE_OPENAI_ENDPOINT`: Azure OpenAI endpoint
- `MONGO_DB_URI`: MongoDB connection string
- `PROMETHEUS_ADDRESS`: Prometheus server address
- `MANAGER_API_ADDRESS`: Manager API address for Prometheus targets

### Optional Environment Variables
- `SLACK_BOT_TOKEN`: Slack bot token
- `SLACK_APP_TOKEN`: Slack app token
- `CELERY_BROKER_URL`: Redis URL (defaults to localhost)
- `CONFLUENCE_URL`: Confluence instance URL
- `JIRA_URL`: Jira instance URL
- `METRICS_DIR`: Directory for metrics storage

### GraphMCP Configuration
- **MCP Servers**: Configured in `src/frameworks/graphmcp/mcp_config.json`
- **Environment Integration**: Supports variable substitution
- **Development vs Production**: Different configurations for different environments

## Feature Development Process

### Context Engineering Process

This project follows context engineering principles for AI-assisted development:

#### 1. Comprehensive Context Assembly
**Always provide complete context:**
- Reference existing patterns from `src/frameworks/graphmcp/examples/` directory
- Include architectural context and constraints
- Specify exact patterns to follow
- Provide detailed implementation requirements

#### 2. Structured Feature Requests
**Use this INITIAL.md template structure for all feature requests:**
- Provide comprehensive feature descriptions
- Include business justification and success criteria
- Specify technical requirements and constraints
- Reference existing patterns and similar features
- Define clear acceptance criteria

#### 3. Product Requirements Prompts (PRPs)
**Create PRPs for all non-trivial features:**
- Research existing codebase patterns thoroughly
- Assemble comprehensive implementation context
- Provide detailed step-by-step implementation plan
- Include validation criteria and testing requirements
- Reference specific code examples and patterns

#### 4. Implementation Guidelines
**Follow established patterns consistently:**
- **MCP Clients**: Use BaseMCPClient pattern with SERVER_NAME
- **Workflows**: Use WorkflowBuilder with step_auto() method
- **Logging**: Use structured logging with get_logger()
- **Testing**: Use pytest with appropriate markers
- **Error Handling**: Use custom exception hierarchies

#### 5. Validation Gates
**Implement comprehensive validation:**
- Code quality validation (lint, format, type-check)
- Functional validation (unit, integration, E2E tests)
- Performance validation (response time, throughput)
- Architecture validation (pattern compliance)
- Documentation validation (completeness, accuracy)

### Feature Development Steps

When developing new features for the Manager component:

1. **Context Analysis**: Understand existing patterns and architecture
2. **Requirements Gathering**: Use this INITIAL.md structure for detailed requirements
3. **Design Review**: Ensure alignment with existing architecture
4. **Implementation**: Follow established patterns and conventions
5. **Testing**: Comprehensive testing at all levels
6. **Validation**: Use validation framework for quality assurance
7. **Documentation**: Update relevant documentation and examples
8. **Integration**: Ensure proper integration with Agent and UI components
9. **Deployment**: Follow established deployment procedures

## Use Cases and Examples

### Database Decommissioning (GraphMCP)
- Automated database reference discovery
- Intelligent code refactoring
- GitHub PR creation and management
- Comprehensive validation and testing

### Incident Response (Manager Core)
- AI-powered incident analysis
- Automated remediation workflows
- Slack notifications and updates
- Metrics collection and reporting

### System Monitoring (Cross-Component)
- Real-time agent data collection (Agent → Manager)
- Threshold-based alerting (Manager logic)
- Performance metrics analysis (Manager processing)
- Dashboard visualization (Manager → UI)

### Atlassian Integration (Manager Tools)
- Confluence content management and search
- Jira ticket lifecycle management
- Automated documentation updates
- Issue tracking and resolution

## Quality Requirements

### Code Quality
- **Type Safety**: Use type hints and validation throughout
- **Error Handling**: Comprehensive error management with context
- **Performance**: Async-first design with intelligent caching
- **Testing**: High test coverage with multiple test types
- **Documentation**: Clear, comprehensive documentation with examples

### Architecture Patterns
- **Microservices**: Service isolation and independence
- **Event-Driven**: Async message passing and event handling
- **Context-Aware**: Shared state and context management
- **Observability**: Comprehensive logging and monitoring
- **Scalability**: Horizontal scaling and load distribution

### Security Considerations
- **Authentication**: Proper authentication for all endpoints
- **Authorization**: Role-based access control
- **Secrets Management**: Environment-based secret handling
- **Network Security**: Service isolation and secure communication
- **Data Protection**: Encryption at rest and in transit
- **Input Validation**: Comprehensive validation and sanitization

## Deployment Architecture

### Development
- Docker Compose for local development
- Local MongoDB, Redis, and Prometheus instances
- Hot-reload for rapid development cycles
- Component isolation for independent development

### Production
- Kubernetes deployment with Helm charts
- Containerized services with health checks
- Horizontal scaling and load balancing
- Comprehensive monitoring and alerting
- Service mesh for secure inter-component communication

### Container Architecture
```bash
# Manager container
docker build -t sysaidmin-manager -f Containerfile .
docker run \
  -e AZURE_OPENAI_API_KEY=${AZURE_OPENAI_API_KEY} \
  -e AZURE_OPENAI_ENDPOINT=${AZURE_OPENAI_ENDPOINT} \
  -e MONGO_DB_URI=${MONGO_DB_URI} \
  -e SLACK_BOT_TOKEN=${SLACK_BOT_TOKEN} \
  sysaidmin-manager:latest
```

## Success Criteria

Features developed for the Manager component should demonstrate:

### Functional Criteria
- **Complete Implementation**: Full implementation of requirements
- **Cross-Component Integration**: Seamless integration with Agent and UI
- **External Service Integration**: Proper integration with external services
- **Business Value**: Clear business value and user benefit

### Technical Criteria
- **Performance**: Meets performance requirements (< 500ms API response)
- **Reliability**: Robust error handling and recovery mechanisms
- **Scalability**: Ability to handle expected load and growth
- **Maintainability**: Clear code structure and comprehensive documentation

### Quality Criteria
- **Security**: Appropriate security considerations and implementations
- **Testing**: Comprehensive test coverage (80% minimum)
- **Documentation**: Complete documentation with usage examples
- **Monitoring**: Proper logging, metrics, and alerting

### Architecture Criteria
- **Pattern Compliance**: Follows established architectural patterns
- **Context Engineering**: Implements context engineering principles
- **Framework Integration**: Proper integration with GraphMCP framework
- **Service Independence**: Maintains microservice independence

## Component Compatibility Requirements

When developing Manager features, ensure compatibility with:

### Agent Component
- **API Contracts**: Maintain stable API contracts for Agent communication
- **Data Formats**: Consistent data formats for metrics and monitoring
- **Authentication**: Compatible authentication mechanisms
- **Deployment**: Independent deployment capabilities

### UI Component
- **API Endpoints**: Provide necessary API endpoints for UI functionality
- **Real-time Data**: Support real-time data updates for dashboard
- **Authentication**: Compatible with Auth0 authentication
- **Data Models**: Consistent data models for UI consumption

### External Dependencies
- **Version Compatibility**: Maintain compatibility with external service versions
- **Configuration**: Flexible configuration for different environments
- **Error Handling**: Graceful handling of external service failures
- **Monitoring**: Comprehensive monitoring of external integrations

This comprehensive context provides the foundation for accurate, efficient, and consistent feature development within the Manager component of the Ovora ecosystem, ensuring proper integration with all system components while maintaining the high standards of the context engineering methodology.

---

## Feature Request Template

Use this structure when requesting new features for the Manager component:

### Basic Information
- **Feature Name**: [Clear, descriptive name]
- **Component**: [Manager/GraphMCP/Tools/Core]
- **Requested By**: [Your name/team]
- **Date**: [YYYY-MM-DD]
- **Priority**: [High/Medium/Low]
- **Estimated Complexity**: [Simple/Medium/Complex]

### Feature Description
- **What**: [Comprehensive description of what the feature should do]
- **Why**: [Business justification and value proposition]
- **When**: [Timeline requirements and dependencies]
- **Who**: [Target users and stakeholders]

### Technical Requirements
- **Architecture Integration**: [How this integrates with Manager architecture]
- **Framework Integration**: [GraphMCP framework integration requirements]
- **Cross-Component Impact**: [Impact on Agent and UI components]
- **Performance Requirements**: [Response time, throughput, resource usage]
- **Security Requirements**: [Authentication, authorization, data protection]

### Implementation Context
- **Similar Features**: [Reference similar features in the codebase]
- **Existing Patterns**: [Reference existing patterns from examples/]
- **Integration Points**: [External services and internal components]

### Acceptance Criteria
- [ ] Functional requirements met
- [ ] Technical requirements satisfied
- [ ] Integration tests passing
- [ ] Performance criteria achieved
- [ ] Security requirements implemented
- [ ] Documentation completed

Following this template and the context engineering process ensures successful feature development within the Manager component.