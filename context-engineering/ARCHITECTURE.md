# Manager Component Architecture

## Overview

This document captures the architecture decisions, design rationale, and evolution history of the Ovora Manager component. It serves as the definitive source for understanding why architectural choices were made and their impact on the system.

## Architecture Philosophy

### Design Principles

1. **Async-First**: All I/O operations use async/await patterns for maximum concurrency
2. **Microservice Isolation**: External integrations are isolated as independent services
3. **Context Engineering**: AI assistance is enhanced through comprehensive context engineering
4. **Graceful Degradation**: System continues operating when non-critical services fail
5. **Observable by Default**: Comprehensive logging, metrics, and tracing built-in

### Key Architectural Decisions

#### ADR-001: Microservice Tool Architecture
**Date**: 2024-Q1  
**Status**: Active  
**Decision**: Implement external service integrations as separate microservices

**Context**:
The Manager component needs to integrate with multiple external services (Confluence, Jira, command execution, database management). These integrations have different:
- Rate limiting requirements
- Authentication mechanisms
- Failure modes and recovery patterns
- Scaling characteristics

**Decision**:
Extract each external integration into a separate FastAPI microservice with:
- Independent deployment and scaling
- Standardized API patterns
- Docker containerization
- Individual dependency management

**Rationale**:
- **Fault Isolation**: Failure in one integration doesn't affect others
- **Independent Scaling**: Scale services based on actual usage patterns
- **Technology Diversity**: Each service can use optimal libraries and patterns
- **Team Autonomy**: Different teams can own different integrations
- **Deployment Flexibility**: Deploy and update services independently

**Consequences**:
- ✅ **Positive**: Better fault tolerance, clearer ownership, easier testing
- ❌ **Negative**: Additional operational complexity, network latency between services
- ⚠️ **Neutral**: Need for service discovery and inter-service communication patterns

**Implementation Pattern**:
```
Manager Core (Port 9123)
├── Confluence Tool (Port 8000)
├── Jira Tool (Port 8001)
├── CMD Exec Tool (Port 8002)
└── DB Servers CMDB (Port 8003)
```

#### ADR-002: GraphMCP Framework Adoption
**Date**: 2024-Q1  
**Status**: Active  
**Decision**: Use GraphMCP framework for complex workflow orchestration

**Context**:
Manager component needs to execute complex, multi-step workflows involving:
- Multiple external services (GitHub, Slack, repository analysis)
- AI-powered decision making
- Error handling and recovery
- Progress tracking and observability

**Decision**:
Adopt GraphMCP framework as the primary workflow orchestration engine with:
- Multi-client MCP (Model Context Protocol) integration
- Fluent workflow builder API
- Async execution with proper resource management
- Structured logging and monitoring

**Rationale**:
- **Proven Patterns**: Framework embodies proven workflow patterns
- **AI Integration**: Native support for AI-powered workflow steps
- **Observability**: Built-in logging, metrics, and progress tracking
- **Extensibility**: Easy to add new MCP clients and workflow patterns
- **Error Handling**: Robust error handling with retry logic and graceful degradation

**Consequences**:
- ✅ **Positive**: Rapid workflow development, consistent patterns, excellent observability
- ❌ **Negative**: Framework dependency, learning curve for new developers
- ⚠️ **Neutral**: Need to maintain framework compatibility and updates

**Current Usage**:
- Database decommissioning workflows
- Repository analysis and pattern discovery
- Multi-service integration scenarios

#### ADR-003: MongoDB as Primary Database
**Date**: 2024-Q1  
**Status**: Active  
**Decision**: Use MongoDB as the primary database with structured collections

**Context**:
Manager component needs to store:
- Incident data with flexible metadata
- Inventory information with varying schemas
- Workflow state and progress
- Task queue information

**Decision**:
Use MongoDB with:
- Dedicated collections for each domain (incidents, inventory, tasks)
- Structured data models despite NoSQL flexibility
- Connection pooling and async drivers
- Environment-based configuration

**Rationale**:
- **Schema Flexibility**: Accommodate evolving data models without migrations
- **Async Support**: Excellent async driver support for Python
- **Aggregation**: Powerful aggregation pipeline for complex queries
- **Scalability**: Horizontal scaling capabilities for future growth
- **JSON Native**: Natural fit for API-first architecture

**Consequences**:
- ✅ **Positive**: Rapid development, flexible data models, excellent Python integration
- ❌ **Negative**: NoSQL learning curve, eventual consistency considerations
- ⚠️ **Neutral**: Need for data validation patterns, indexing strategy

**Data Architecture**:
```
MongoDB Instance
├── incidents (Incident management)
├── inventory (Asset tracking)
├── tasks (Background jobs)
├── questions (Q&A data)
└── checkpoints (Workflow state)
```

#### ADR-004: Azure OpenAI Integration
**Date**: 2024-Q1  
**Status**: Active  
**Decision**: Azure OpenAI as the primary AI service provider

**Context**:
Manager component requires AI capabilities for:
- Incident analysis and response recommendations
- Code quality assessment
- Decision support systems
- Automated summarization and classification

**Decision**:
Integrate with Azure OpenAI using:
- LangChain for structured AI interactions
- Pydantic models for structured outputs
- Comprehensive error handling and retry logic
- Token usage tracking and cost management

**Rationale**:
- **Enterprise Ready**: Enterprise-grade security and compliance
- **Cost Control**: Predictable pricing and usage controls
- **Performance**: Low latency and high availability
- **Integration**: Excellent Python SDK and LangChain support
- **Model Variety**: Access to latest GPT models and capabilities

**Consequences**:
- ✅ **Positive**: Reliable AI capabilities, enterprise security, cost predictability
- ❌ **Negative**: Vendor lock-in, dependency on external service
- ⚠️ **Neutral**: Need for prompt engineering expertise, token usage optimization

**AI Architecture**:
```
AI Integration Layer
├── Configuration Management
├── Service Abstractions (Incident, Code, Decision)
├── Prompt Engineering Templates
└── Response Parsing (Pydantic models)
```

#### ADR-005: Context Engineering Implementation
**Date**: 2024-Q2  
**Status**: Active  
**Decision**: Implement comprehensive context engineering for AI-assisted development

**Context**:
Development productivity with AI assistance was limited by:
- Inconsistent context provision
- Lack of structured development patterns
- No systematic approach to AI-assisted coding
- Limited knowledge sharing and pattern reuse

**Decision**:
Implement Coleman Context Engineering framework with:
- Structured documentation (CLAUDE.md, INITIAL.md templates)
- Comprehensive examples and patterns library
- PRP (Product Requirements Prompt) system
- Validation and quality assurance framework

**Rationale**:
- **Productivity**: 10x improvement in AI-assisted development effectiveness
- **Consistency**: Standardized patterns across all development work
- **Quality**: Systematic validation ensures high-quality outputs
- **Knowledge Sharing**: Reusable patterns and comprehensive documentation
- **Onboarding**: New developers productive immediately

**Consequences**:
- ✅ **Positive**: Dramatic productivity improvement, consistent quality, excellent onboarding
- ❌ **Negative**: Initial setup overhead, documentation maintenance burden
- ⚠️ **Neutral**: Need for continuous pattern evolution and improvement

**Context Engineering Structure**:
```
context-engineering/
├── README.md (System overview)
├── examples/ (Implementation patterns)
├── templates/ (Feature and workflow templates)
├── commands/ (PRP generation and execution)
├── patterns/ (Architecture patterns)
├── validation/ (Quality assurance)
└── PRPs/ (Product Requirements Prompts)
```

## System Architecture

### High-Level Component View

```
┌─────────────────────────────────────────────────────────────────┐
│                        Ovora System                             │
├─────────────────┬─────────────────┬─────────────────────────────┤
│   UI Component  │  Manager Comp   │      Agent Component        │
│   (Streamlit)   │   (FastAPI)     │        (Go Binary)          │
│                 │                 │                             │
│ ┌─────────────┐ │ ┌─────────────┐ │ ┌─────────────────────────┐ │
│ │ Dashboard   │←┼→│ API Gateway │←┼→│ Data Collection         │ │
│ │ Auth0       │ │ │ Celery      │ │ │ Node Exporter           │ │
│ │ Visualiz    │ │ │ MongoDB     │ │ │ System Metrics          │ │
│ └─────────────┘ │ │ GraphMCP    │ │ └─────────────────────────┘ │
│                 │ │ Microservic │ │                             │
│                 │ └─────────────┘ │                             │
└─────────────────┴─────────────────┴─────────────────────────────┘
                           │
                    ┌─────────────┐
                    │  External   │
                    │  Services   │
                    │             │
                    │ ┌─────────┐ │
                    │ │Conflu   │ │
                    │ │Jira     │ │
                    │ │GitHub   │ │
                    │ │Slack    │ │
                    │ │Promethe │ │
                    │ └─────────┘ │
                    └─────────────┘
```

### Manager Component Internal Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Manager Component                            │
├─────────────────────────────────────────────────────────────────┤
│                     API Layer (FastAPI)                        │
├─────────────────────────────────────────────────────────────────┤
│  Business Logic Layer                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │   Modules    │  │  Use Cases   │  │    GraphMCP          │  │
│  │              │  │              │  │    Framework         │  │
│  │ • Incident   │  │ • DB Decomm  │  │                      │  │
│  │ • Inventory  │  │ • Runbook    │  │ • Workflow Builder   │  │
│  │ • Metrics    │  │   Finder     │  │ • MCP Clients        │  │
│  │ • Tasks      │  │              │  │ • Context Mgmt       │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│  Integration Layer                                              │
│  ┌────────────┐  ┌─────────────┐  ┌──────────────────────────┐  │
│  │ Database   │  │ AI Services │  │   Microservice Tools     │  │
│  │            │  │             │  │                          │  │
│  │ • MongoDB  │  │ • Azure     │  │ • Confluence (8000)     │  │
│  │ • Async    │  │   OpenAI    │  │ • Jira (8001)           │  │
│  │   Driver   │  │ • LangChain │  │ • CMD Exec (8002)       │  │
│  │ • Connect  │  │ • Pydantic  │  │ • DB CMDB (8003)        │  │
│  │   Pool     │  │   Models    │  │                          │  │
│  └────────────┘  └─────────────┘  └──────────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│  Infrastructure Layer                                          │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────────────┐ │
│  │   Celery    │  │  Monitoring │  │     Configuration        │ │
│  │   + Redis   │  │             │  │                          │ │
│  │             │  │ • Logging   │  │ • Environment Vars       │ │
│  │ • Task      │  │ • Metrics   │  │ • Pydantic Settings      │ │
│  │   Queue     │  │ • Health    │  │ • Service Discovery      │ │
│  │ • Schedul   │  │   Checks    │  │                          │ │
│  └─────────────┘  └─────────────┘  └──────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Data Architecture

### Database Schema Design

```
MongoDB Collections:

incidents
├── _id: ObjectId
├── title: str
├── description: str
├── severity: enum[low, medium, high, critical]
├── status: enum[open, in_progress, resolved, closed]
├── source: str
├── metadata: dict
├── created_at: datetime
├── updated_at: datetime
└── tags: list[str]

inventory
├── _id: ObjectId
├── asset_id: str (unique)
├── asset_type: enum[server, database, application, service]
├── name: str
├── environment: enum[dev, staging, prod]
├── owner: str
├── properties: dict (flexible schema)
├── discovered_at: datetime
└── last_seen: datetime

tasks
├── _id: ObjectId
├── task_id: str (unique)
├── task_type: str
├── status: enum[pending, running, completed, failed]
├── parameters: dict
├── result: dict
├── error_message: str (optional)
├── created_at: datetime
├── started_at: datetime (optional)
└── completed_at: datetime (optional)

questions (AI Q&A)
├── _id: ObjectId
├── question: str
├── context: dict
├── answer: str
├── confidence: float
├── model_used: str
├── tokens_used: int
├── created_at: datetime
└── feedback: dict (optional)

checkpoints (Workflow state)
├── _id: ObjectId
├── workflow_id: str
├── step_name: str
├── status: enum[pending, running, completed, failed, skipped]
├── input_data: dict
├── output_data: dict
├── error_info: dict (optional)
├── started_at: datetime
└── completed_at: datetime (optional)
```

### Data Flow Architecture

```
Data Flow Patterns:

1. Incident Management Flow
   Agent → Manager API → MongoDB → UI Dashboard
   
2. Workflow Execution Flow
   Trigger → GraphMCP → MCP Clients → External Services
          ↓
   MongoDB (checkpoints) → Progress Tracking → UI/Slack

3. AI Processing Flow
   Input → Manager → Azure OpenAI → Structured Response
        ↓
   MongoDB (questions) → Analytics → Improvement

4. Microservice Integration Flow
   Manager → Microservice Tool → External API → Response
                              ↓
   Caching Layer → Performance Optimization
```

## Security Architecture

### Authentication and Authorization

```
Security Layers:

1. External Access
   ├── UI: Auth0 integration with JWT tokens
   ├── API: API key authentication for service-to-service
   └── Agent: Shared secret or mutual TLS

2. Internal Security
   ├── Service-to-service: Internal API keys
   ├── Database: Connection string security
   └── AI Services: Azure OpenAI key management

3. Data Protection
   ├── Secrets: Environment variables, no hardcoding
   ├── Logs: Secret masking and sanitization
   └── Transit: HTTPS/TLS for all communications
```

### Security Decisions

**Secret Management**:
- Environment variable based configuration
- No secrets in code or version control
- Automatic secret masking in logs
- Rotation procedures for API keys

**Network Security**:
- HTTPS only for external communication
- Internal service communication over private networks
- Firewall rules for service isolation
- VPN access for development and operations

## Performance Architecture

### Async-First Design

All I/O operations use async/await patterns:

```python
# Database operations
async with DatabaseClient() as db:
    incidents = await db.incidents.find(query).to_list()

# HTTP requests
async with httpx.AsyncClient() as client:
    response = await client.post(url, json=data)

# AI processing
response = await openai_client.ainvoke(messages)
```

### Caching Strategy

```
Caching Layers:

1. Application Cache (In-Memory)
   ├── Configuration caching
   ├── Frequently accessed data
   └── AI response caching

2. Distributed Cache (Redis)
   ├── Session storage
   ├── Task queue state
   └── Cross-service data sharing

3. HTTP Response Caching
   ├── Static data endpoints
   ├── Dashboard data with TTL
   └── Health check optimization
```

### Performance Metrics

Target Performance Characteristics:
- API Response Time: < 2 seconds (95th percentile)
- Database Query Time: < 500ms (95th percentile)
- Workflow Execution: Variable based on complexity
- Memory Usage: < 512MB per service under normal load
- CPU Usage: < 70% under normal load

## Monitoring and Observability

### Logging Architecture

```
Logging Layers:

1. Application Logging
   ├── Structured JSON logs
   ├── Correlation IDs for request tracking
   ├── Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
   └── Sensitive data masking

2. GraphMCP Framework Logging
   ├── Workflow execution tracking
   ├── Step-by-step progress logging
   ├── Performance metrics collection
   └── Error context preservation

3. External Service Logging
   ├── API call logging with timing
   ├── Authentication success/failure
   ├── Rate limiting information
   └── Service health monitoring
```

### Metrics Collection

```
Prometheus Metrics:

1. Application Metrics
   ├── Request count and duration
   ├── Error rates by endpoint
   ├── Active connections and sessions
   └── Resource usage (CPU, memory)

2. Business Metrics
   ├── Incidents created/resolved
   ├── Workflow success/failure rates
   ├── AI processing metrics
   └── User activity patterns

3. Infrastructure Metrics
   ├── Database connection pool usage
   ├── Queue depth and processing time
   ├── Cache hit/miss rates
   └── Service dependency health
```

## Deployment Architecture

### Container Strategy

```
Container Architecture:

Manager Core:
├── Base: python:3.12-slim
├── Package Manager: uv (faster than pip)
├── Dependencies: pyproject.toml
├── Health Checks: /health endpoint
└── Resource Limits: CPU 1 core, Memory 1GB

Microservice Tools:
├── Independent containers per tool
├── Standard FastAPI base
├── Individual pyproject.toml
├── Service-specific health checks
└── Minimal resource allocation
```

### Orchestration Strategy

```
Kubernetes Deployment:

Manager Namespace:
├── manager-api (Deployment + Service)
├── manager-worker (Deployment for Celery)
├── manager-scheduler (Deployment for beat)
├── confluence-tool (Deployment + Service)
├── jira-tool (Deployment + Service)
├── cmd-exec-tool (Deployment + Service)
└── db-cmdb-tool (Deployment + Service)

Supporting Services:
├── mongodb (StatefulSet)
├── redis (Deployment + Service)
├── prometheus (Deployment + Service)
└── grafana (Deployment + Service)
```

## Evolution History

### Phase 1: Monolithic Start (2024-Q1)
- Single FastAPI application with all functionality
- Direct integration with external services
- Basic async patterns implementation
- MongoDB for data persistence

### Phase 2: Microservice Extraction (2024-Q1)
- Extracted external integrations to separate services
- Implemented service discovery patterns
- Added comprehensive health checking
- Containerized all services

### Phase 3: GraphMCP Integration (2024-Q1)
- Adopted GraphMCP for complex workflows
- Implemented structured workflow patterns
- Added comprehensive observability
- AI-powered workflow capabilities

### Phase 4: Context Engineering (2024-Q2)
- Implemented Coleman Context Engineering framework
- Added comprehensive documentation and examples
- Created systematic AI-assisted development process
- Established quality assurance patterns

### Phase 5: Production Hardening (2024-Q2)
- Enhanced security and authentication
- Implemented comprehensive monitoring
- Added performance optimization
- Established deployment automation

## Future Architecture Plans

### Short Term (6 months)
1. **Enhanced AI Capabilities**
   - Multi-model AI support (Claude, GPT-4, local models)
   - Advanced prompt engineering and context management
   - AI model performance comparison and optimization

2. **Event-Driven Architecture**
   - Implement event streaming with Apache Kafka
   - Async event processing between services
   - Event sourcing for audit trails

3. **Advanced Observability**
   - Distributed tracing with Jaeger
   - Advanced alerting and incident response
   - Performance profiling and optimization

### Medium Term (12 months)
1. **Multi-Region Deployment**
   - Geographic distribution of services
   - Data replication and consistency strategies
   - Disaster recovery and business continuity

2. **GraphQL API Layer**
   - Unified GraphQL endpoint for UI
   - Efficient data fetching and real-time subscriptions
   - Backward compatibility with REST APIs

3. **Advanced Workflow Engine**
   - Visual workflow builder
   - Conditional branching and parallel execution
   - Workflow versioning and rollback

### Long Term (18+ months)
1. **Machine Learning Platform**
   - Model training and deployment pipeline
   - Feature store and experiment tracking
   - A/B testing for AI-powered features

2. **Service Mesh Architecture**
   - Istio for advanced service communication
   - Zero-trust security model
   - Advanced traffic management

3. **Cloud-Native Optimization**
   - Serverless computing for batch workloads
   - Auto-scaling based on business metrics
   - Cost optimization through resource rightsizing

## References

### Architecture Documentation
- [Manager Architecture Patterns](./patterns/manager_architecture_patterns.md)
- [Context Engineering Framework](./README.md)
- [GraphMCP Framework](../src/frameworks/graphmcp/README.md)

### External Influences
- Domain-Driven Design by Eric Evans
- Building Microservices by Sam Newman
- Designing Data-Intensive Applications by Martin Kleppmann
- Site Reliability Engineering by Google

### Technology Choices
- [FastAPI](https://fastapi.tiangolo.com/) - Async web framework
- [MongoDB](https://www.mongodb.com/) - Document database
- [Azure OpenAI](https://azure.microsoft.com/en-us/products/ai-services/openai-service) - AI services
- [GraphMCP Framework](../src/frameworks/graphmcp/) - Workflow orchestration

### Architecture Reviews
- Monthly architecture review meetings
- Quarterly technology radar updates
- Annual architecture fitness review
- Continuous improvement through ADR process