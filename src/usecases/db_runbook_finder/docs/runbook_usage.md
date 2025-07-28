# DB Runbook Finder - Complete Usage Guide

> **AI-powered database runbook discovery with Jira and Slack integration**

This guide covers all aspects of using the DB Runbook Finder: from basic runbook searches to automated Jira ticket processing and Slack notifications.

## 🚀 Quick Start

**Prerequisites:**
1. Run from the manager project root directory
2. First-time setup requires populating the runbook database

```bash
# 1. Populate the runbook database (required first)
uv run python -m usecases.db_runbook_finder.discover_runbooks --collection-name mcdb-runbooks

# 2. Search for runbooks
uv run python src/usecases/db_runbook_finder/scripts/search_runbooks.py "database connection problems"
```

---

## 📚 Runbook Search Commands

### 🔍 **Semantic Search** (Primary Method)

```bash
uv run python src/usecases/db_runbook_finder/scripts/search_runbooks.py "your search query"
```

**Common Search Examples:**
```bash
# Connection issues
uv run python src/usecases/db_runbook_finder/scripts/search_runbooks.py "database connection problems"

# Performance troubleshooting  
uv run python src/usecases/db_runbook_finder/scripts/search_runbooks.py "performance monitoring"

# Backup and recovery
uv run python src/usecases/db_runbook_finder/scripts/search_runbooks.py "backup restore"

# Database-specific searches
uv run python src/usecases/db_runbook_finder/scripts/search_runbooks.py "DB2 troubleshooting"
uv run python src/usecases/db_runbook_finder/scripts/search_runbooks.py "oracle monitoring"

# Process documentation
uv run python src/usecases/db_runbook_finder/scripts/search_runbooks.py "onboarding checklist"
```

**Search Results Format:**
```
📚 Found 3 runbooks for query: "database connection problems"

🏢 Helvetia
  📖 Database Connection Troubleshooting Runbook (Score: 0.89 - Very Relevant)
     📁 Space: RUNBOOKS | 🆔 ID: 123456 | 🔗 https://nordcloud.atlassian.net/wiki/spaces/RUNBOOKS/pages/123456
     🏷️ Tags: database, troubleshooting, connection

🏢 Neste  
  📖 Performance Monitoring Best Practices (Score: 0.72 - Relevant)
     📁 Space: ENGINEERING | 🆔 ID: 789012 | 🔗 https://nordcloud.atlassian.net/wiki/spaces/ENGINEERING/pages/789012
     🏷️ Tags: monitoring, performance, database
```

### 📋 **Browse & Analyze Commands**

```bash
# List all available runbooks
uv run python src/usecases/db_runbook_finder/scripts/list_runbooks.py

# View collection statistics
uv run python src/usecases/db_runbook_finder/scripts/collection_stats.py
```

---

## ⚙️ Database Management

### 🔄 **Discovery & Population**

**Basic Discovery:**
```bash
# Standard discovery (recommended)
uv run python src/usecases/db_runbook_finder/discover_runbooks.py --collection-name mcdb-runbooks
```

**Advanced Options:**
```bash
# Clear existing data and repopulate (safe re-runs)
uv run python src/usecases/db_runbook_finder/discover_runbooks.py --clear-existing --collection-name mcdb-runbooks

# Preview what would be cleared (dry run)
uv run python src/usecases/db_runbook_finder/discover_runbooks.py --dry-run --clear-existing

# Automation-friendly (skip confirmation prompts)
uv run python src/usecases/db_runbook_finder/discover_runbooks.py --clear-existing -y
uv run python src/usecases/db_runbook_finder/discover_runbooks.py --clear-existing --yes
uv run python src/usecases/db_runbook_finder/discover_runbooks.py --clear-existing --no-confirm
```

> **Note:** The `--clear-existing` flag safely handles duplicate runbooks by clearing the ChromaDB collection before repopulating with fresh data.

---

## 🎫 Jira Integration

### 🔧 **Environment Setup**

Add these variables to your `.env` file:
```bash
# Required Jira configuration
JIRA_URL=https://your-domain.atlassian.net
JIRA_USERNAME=your-email@domain.com  
JIRA_API_TOKEN=your_jira_api_token
```

### 🔄 **Automated Workflow Usage**

```python
# Process a Jira ticket automatically
from usecases.db_runbook_finder import DBRunbookFinderWorkflow
import asyncio

async def process_ticket():
    workflow = DBRunbookFinderWorkflow()
    result = await workflow.run("AGENT-6")  # Your Jira ticket key
    
    if result.status == "SUCCESS":
        print(f"✅ Found {len(result.runbooks)} runbooks")
    elif result.status == "GAP_DETECTED":
        print("⚠️ No relevant runbooks found - manual intervention needed")
    else:
        print(f"❌ Error: {result.status}")

# Run the workflow
asyncio.run(process_ticket())
```

### 🎯 **What the Workflow Does**

1. **📥 Fetches Jira Ticket**
   - Retrieves incident description, summary, and technical details
   - Maps project keys to clients (AGENT → Helvetia, etc.)
   - Extracts keywords for semantic search

2. **🔍 Searches Runbooks** 
   - Performs semantic search using incident details
   - Ranks results by relevance score (0.6+ threshold)
   - Organizes by client and database type

3. **📝 Updates Jira**
   - Adds formatted comment with top 3 runbook recommendations
   - Includes direct Confluence links and relevance scores
   - Creates gap notification if no relevant runbooks found

4. **📢 Sends Slack Notification**
   - Posts status update to team channel
   - Includes ticket link and runbook summary

---

## 💬 Slack Integration

### 🔧 **Environment Setup**

Add these variables to your `.env` file:
```bash
# Required Slack configuration
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
SLACK_APP_TOKEN=xapp-your-slack-app-token  
SLACK_CHANNEL=C066PQYUYR4  # Channel ID for #mc-dba-jira-notifications
```

### 📨 **Notification Examples**

**✅ Success Notification (Runbooks Found):**
```
✅ **Runbook Recommendations Found** - AGENT-6

Found 3 relevant runbooks for database connection issues:

🏢 **Helvetia**
📖 Database Connection Troubleshooting Runbook (Score: 0.89)
📖 Oracle Server & DB Access (Score: 0.72)

🔗 View ticket: [AGENT-6](https://nordcloud.atlassian.net/browse/AGENT-6)
```

**⚠️ Gap Detection Notification:**
```
⚠️ **Runbook Gap Detected** - AGENT-6

No relevant runbooks found for: "unusual database error"
Manual intervention required.

🔗 View ticket: [AGENT-6](https://nordcloud.atlassian.net/browse/AGENT-6)
```

**❌ Error Notification:**
```
❌ **Workflow Error** - AGENT-6

Workflow failed during execution. Please check logs.

🔗 View ticket: [AGENT-6](https://nordcloud.atlassian.net/browse/AGENT-6)
```

**📍 Default Channel:** Messages are sent to `#mc-dba-jira-notifications` and include ticket status, runbook count, direct links, and client organization details.

---

## 🧪 Testing & Validation

### 🔍 **Connection Tests**

```bash
# Test Jira connection
uv run python -c "from src.tools.jira.app.jira import JiraClient; client = JiraClient(); print('✅ Jira: Connected')"

# Test Slack connection  
uv run python -c "from src.tools.communication.app.slack import SlackClient; client = SlackClient(); print('✅ Slack: Connected')"

# Test complete workflow with mock data
uv run python -c "
from usecases.db_runbook_finder import DBRunbookFinderWorkflow
import asyncio
workflow = DBRunbookFinderWorkflow()
result = asyncio.run(workflow.run('AGENT-TEST'))
print(f'✅ Workflow: {result.status}, Runbooks: {len(result.runbooks)}')
"
```

### 🔄 **Operating Modes**

**🧪 Development Mode** (No API tokens):
- Uses realistic mock Jira ticket data
- Simulates Confluence searches with test results
- Logs Slack notifications instead of sending
- Perfect for development and testing

**🚀 Production Mode** (With API tokens):
- Real Jira API calls for ticket operations
- Live Confluence runbook searches via ChromaDB
- Actual Slack notifications to configured channels
- Full automation with real data

---

## 🎯 Key Features & Performance

**⚡ Performance:**
- **Semantic Search**: <50ms response times using ChromaDB
- **Vector Embeddings**: sentence-transformers all-MiniLM-L6-v2 model
- **Relevance Scoring**: Very Relevant (0.8+), Relevant (0.6-0.8), etc.

**🏢 Client Organization:**
- Automatically organizes results by client (Helvetia, Neste, Grohe, Bravida)
- Maps Jira project keys to client names
- Maintains client-specific runbook collections

**🔄 Reliability:**
- **Mock Confluence Layer**: Works offline with comprehensive test data
- **Graceful Degradation**: Falls back to mock mode when APIs unavailable
- **Duplicate Prevention**: Safe re-runs with `--clear-existing` flag
- **Error Handling**: Comprehensive error tracking and recovery

**🤖 Automation:**
- **Zero-Touch Processing**: Automatic Jira ticket → runbook recommendations
- **Gap Detection**: Identifies missing runbooks for process improvement
- **Team Notifications**: Real-time Slack updates for incident response
- **Audit Trail**: Complete logging for troubleshooting and analytics

---

## 📝 Summary

The DB Runbook Finder provides:
- **🔍 Intelligent Search**: AI-powered semantic search across database runbooks
- **🎫 Jira Automation**: Automatic incident processing and recommendation injection
- **💬 Team Communication**: Real-time Slack notifications for incident updates
- **📊 Analytics**: Performance tracking and gap analysis for process improvement
- **🛡️ Reliability**: Robust error handling and graceful degradation to mock mode

Perfect for database teams needing fast, accurate runbook discovery during incident response with full automation and team communication integration.