# DB Runbook Finder - Usage Guide

This guide provides the commands to search and interact with runbooks in the DB Runbook Finder usecase.

## Commands to Search Runbooks

### **Primary Search Command** (Semantic Vector Search)
```bash
uv run python src/usecases/db_runbook_finder/scripts/search_runbooks.py "your search query"
```

**Examples:**
```bash
# Database connection issues
uv run python src/usecases/db_runbook_finder/scripts/search_runbooks.py "database connection problems"

# Performance monitoring
uv run python src/usecases/db_runbook_finder/scripts/search_runbooks.py "performance monitoring"

# Backup procedures
uv run python src/usecases/db_runbook_finder/scripts/search_runbooks.py "backup restore"

# DB2 troubleshooting
uv run python src/usecases/db_runbook_finder/scripts/search_runbooks.py "DB2 troubleshooting"

# Oracle monitoring
uv run python src/usecases/db_runbook_finder/scripts/search_runbooks.py "oracle monitoring"

# Onboarding checklist
uv run python src/usecases/db_runbook_finder/scripts/search_runbooks.py "onboarding checklist"
```

### **List All Available Runbooks**
```bash
uv run python src/usecases/db_runbook_finder/scripts/list_runbooks.py
```

### **Collection Statistics**
```bash
uv run python src/usecases/db_runbook_finder/scripts/collection_stats.py
```

### **Discovery and Population** (First-time setup)
```bash
  # Clear existing and repopulate
  uv run python src/usecases/db_runbook_finder/discover_runbooks.py --clear-existing
  --collection-name mcdb-runbooks

  # Dry run preview
  uv run python src/usecases/db_runbook_finder/discover_runbooks.py --dry-run --clear-existing

  # Automation friendly (multiple ways to skip confirmation)
  uv run python src/usecases/db_runbook_finder/discover_runbooks.py --clear-existing --no-confirm
  uv run python src/usecases/db_runbook_finder/discover_runbooks.py --clear-existing -y  
  uv run python src/usecases/db_runbook_finder/discover_runbooks.py --clear-existing --yes
  
```
The implementation addresses the duplicate runbook issue by providing safe, reliable re-runs of
the discovery script with proper collection management.

### **Workflow Integration** (Programmatic Usage)
```python
# Python code integration
from usecases.db_runbook_finder import DBRunbookFinderWorkflow

# Initialize workflow
workflow = DBRunbookFinderWorkflow()

# Process specific Jira ticket
result = await workflow.run("AGENT-6")

# Check results
if result.status == "SUCCESS":
    print(f"Found {len(result.runbooks)} runbooks")
elif result.status == "GAP_DETECTED":
    print("No relevant runbooks found")
```

## Key Features

- **Semantic Search**: Uses ChromaDB with vector embeddings (sentence-transformers all-MiniLM-L6-v2 model)
- **Mock Confluence Layer**: Works offline with comprehensive test data
- **Performance**: <50ms response times for semantic search
- **Relevance Scoring**: Shows relevance scores (Very Relevant 0.8+, Relevant 0.6-0.8, etc.)
- **Client Organization**: Organizes results by client (Helvetia, Neste, etc.)

## Prerequisites

**First run the discovery to populate the database:**
```bash
uv run python -m usecases.db_runbook_finder.discover_runbooks --collection-name mcdb-runbooks
```

**All commands should be run from the manager project root directory** (`/Users/bprzybysz/nc-src/ovora/manager/`)

## Search Results Format

The search returns runbooks with relevance scores and client organization:

```
📚 Found 3 runbooks for query: "database connection problems"

🏢 Helvetia
  📖 Database Connection Troubleshooting Runbook (Score: 0.89 - Very Relevant)
     📁 Space: RUNBOOKS | 🆔 ID: 123456
     🏷️ Tags: database, troubleshooting, connection

🏢 Neste  
  📖 Performance Monitoring Best Practices (Score: 0.72 - Relevant)
     📁 Space: ENGINEERING | 🆔 ID: 789012
     🏷️ Tags: monitoring, performance, database
```

## Notes

- The main search functionality uses semantic vector search across the indexed runbook collection
- Results are organized by client and show relevance scores for better decision making
- The system works offline using mock Confluence data for development and testing