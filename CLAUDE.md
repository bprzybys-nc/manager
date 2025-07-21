# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Context Engineering Enabled

This project uses **Context Engineering** - a systematic approach to providing AI assistants with comprehensive, structured context for dramatically improved code generation and implementation accuracy. This is 10x better than prompt engineering and 100x better than basic AI coding.

### Context Engineering Workflow

1. **Feature Request**: Start with detailed `INITIAL.md` template
2. **Research**: Manually research existing patterns and architecture
3. **PRP Creation**: Use `/generate-prp INITIAL.md` to create comprehensive Product Requirements Prompt
4. **Implementation**: Use `/execute-prp PRPs/active/<feature_name>.md` for structured implementation
5. **Validation**: Follow validation gates defined in the PRP

### Manager-Specific Context Assembly

The Manager component uses specialized context assembly patterns:

- **Comprehensive Component Context**: Full understanding of Manager architecture, GraphMCP framework, and microservices patterns
- **Cross-Component Integration**: Detailed knowledge of Agent (Go) and UI (Streamlit) integration requirements
- **AI-Powered Workflows**: Context for Azure OpenAI, LangChain, and GraphMCP workflow development
- **Database Patterns**: MongoDB interaction patterns and collection management
- **Tool Development**: Microservice tool patterns for external integrations
- **Performance Requirements**: Response time, resource usage, and scalability considerations
- **Security Context**: Authentication, authorization, and data protection patterns

### Context Engineering Commands

- `/generate-prp <initial_file>` - Create comprehensive Product Requirements Prompt
- `/execute-prp <prp_file>` - Execute implementation with full context

See `.claude/commands/` for detailed command documentation.

## Project Overview

SysAIdmin (Ovora) is an AI-powered system administration platform with three main components:

1. **Manager** (Python/FastAPI): Backend API with AI capabilities, task queue, and Slack integration
2. **Agent** (Go): Lightweight monitoring agent deployed on target machines
3. **UI** (Streamlit): Web dashboard for visualization and interaction

### Development Specifics

- **Python Logic Tests**: py logic tests are ran from project's root dir using .venv/bin/python
