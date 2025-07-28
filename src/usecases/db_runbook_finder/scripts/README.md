# Runbook Discovery Scripts

This directory contains utility scripts for managing and searching the `mcdb-runbooks` ChromaDB collection populated by the Confluence Runbook Discovery system.

## 📋 Available Scripts

### 1. `list_runbooks.py` - List All Runbooks
Shows all runbooks in the collection with metadata and chunk counts, organized by client.

```bash
# Basic usage
uv run python src/usecases/db_runbook_finder/scripts/list_runbooks.py

# Example output:
📚 ChromaDB Collection: mcdb-runbooks
📊 Total chunks: 82
===============================================================
📝 Total unique runbooks: 16

🏢 HELVETIA RUNBOOKS (15):
----------------------------------------
 1. Access to Helvetia environment
    📄 Page ID: 4218814812
    🧩 Chunks: 3
    🔗 URL: https://nordcloud.atlassian.net/spaces/MCDBA/pages/4218814812
```

### 2. `search_runbooks.py` - Semantic Search
Performs semantic search on runbooks using vector embeddings.

```bash
# Basic search
uv run python src/usecases/db_runbook_finder/scripts/search_runbooks.py "database access"

# Examples
uv run python src/usecases/db_runbook_finder/scripts/search_runbooks.py "backup restore procedures"
uv run python src/usecases/db_runbook_finder/scripts/search_runbooks.py "DB2 troubleshooting"
uv run python src/usecases/db_runbook_finder/scripts/search_runbooks.py "oracle monitoring"
uv run python src/usecases/db_runbook_finder/scripts/search_runbooks.py "onboarding checklist"
```

**Example output:**
```
🔍 Searching: "database access"
📊 Collection: mcdb-runbooks (82 chunks)
============================================================
📋 Found 5 relevant results:

1. 📖 Oracle server & DB access
   🏢 Helvetia | 🎯 Very Relevant (0.892)
   📄 Page ID: 4232807146
   💬 Content: This runbook provides step-by-step instructions for accessing Oracle database servers...
   🔗 URL: https://nordcloud.atlassian.net/spaces/MCDBA/pages/4232807146
```

### 3. `collection_stats.py` - Detailed Analytics
Shows comprehensive statistics about the collection including chunk distribution, client breakdown, and content analysis.

```bash
# View collection analytics
uv run python src/usecases/db_runbook_finder/scripts/collection_stats.py

# Example output:
📊 ChromaDB Collection Analytics: mcdb-runbooks
============================================================
📈 BASIC STATISTICS
   Total chunks: 82
   Documents retrieved: 82

🏢 CLIENT BREAKDOWN
   Helvetia: 15 runbooks (81 chunks)
   Neste: 1 runbooks (1 chunks)

🧩 CHUNK DISTRIBUTION
   Average chunks per runbook: 5.1
   Min chunks: 1
   Max chunks: 30
   Total runbooks: 16
```

## 🚀 Quick Start Guide

### Step 1: Discover Runbooks (if not done already)
```bash
# Full discovery and population
uv run python -m usecases.db_runbook_finder.discover_runbooks --collection-name mcdb-runbooks

# Dry run (discovery only, no ChromaDB population)
uv run python -m usecases.db_runbook_finder.discover_runbooks --dry-run
```

### Step 2: Explore Your Collection
```bash
# See what runbooks you have
uv run python src/usecases/db_runbook_finder/scripts/list_runbooks.py

# Get detailed statistics
uv run python src/usecases/db_runbook_finder/scripts/collection_stats.py
```

### Step 3: Search for Runbooks
```bash
# Search for specific topics
uv run python src/usecases/db_runbook_finder/scripts/search_runbooks.py "your search query"
```

## 🔍 Common Search Examples

### Access & Authentication
```bash
uv run python src/usecases/db_runbook_finder/scripts/search_runbooks.py "database access login"
uv run python src/usecases/db_runbook_finder/scripts/search_runbooks.py "server credentials authentication"
uv run python src/usecases/db_runbook_finder/scripts/search_runbooks.py "RDS access AWS"
```

### Backup & Recovery
```bash
uv run python src/usecases/db_runbook_finder/scripts/search_runbooks.py "backup restore database"
uv run python src/usecases/db_runbook_finder/scripts/search_runbooks.py "DB2 restore environment"
uv run python src/usecases/db_runbook_finder/scripts/search_runbooks.py "terraform restore RDS"
```

### Troubleshooting
```bash
uv run python src/usecases/db_runbook_finder/scripts/search_runbooks.py "troubleshooting error debug"
uv run python src/usecases/db_runbook_finder/scripts/search_runbooks.py "pacemaker commands not working"
uv run python src/usecases/db_runbook_finder/scripts/search_runbooks.py "monitoring alerts"
```

### Onboarding & Setup
```bash
uv run python src/usecases/db_runbook_finder/scripts/search_runbooks.py "onboarding checklist new team"
uv run python src/usecases/db_runbook_finder/scripts/search_runbooks.py "oracle setup instructions"
uv run python src/usecases/db_runbook_finder/scripts/search_runbooks.py "environment access setup"
```

### Maintenance & Operations
```bash
uv run python src/usecases/db_runbook_finder/scripts/search_runbooks.py "patching upgrade maintenance"
uv run python src/usecases/db_runbook_finder/scripts/search_runbooks.py "EC2 instance upgrade"
uv run python src/usecases/db_runbook_finder/scripts/search_runbooks.py "monitoring control setup"
```

## 🎯 Understanding Search Results

### Relevance Scores
- **🎯 Very Relevant (0.8+)**: Highly matching content
- **✅ Relevant (0.6-0.8)**: Good match, likely useful
- **⚠️ Somewhat Relevant (0.4-0.6)**: Partial match, may be useful
- **❌ Low Relevance (<0.4)**: Poor match, likely not useful

### Client Indicators
- **🏢 Helvetia**: Runbooks specific to Helvetia client
- **🏢 Neste**: Runbooks specific to Neste client
- **❓ Unknown**: Runbooks without clear client association

## 🛠️ Troubleshooting

### Common Issues

1. **Collection Empty Error**
   ```
   ❌ No runbooks found in collection.
   ```
   **Solution**: Run discovery first:
   ```bash
   uv run python -m usecases.db_runbook_finder.discover_runbooks --collection-name mcdb-runbooks
   ```

2. **Import/Path Errors**
   ```
   ModuleNotFoundError: No module named 'tools'
   ```
   **Solution**: Run from project root directory (`/manager/`)

3. **Environment Configuration**
   ```
   ValueError: Confluence configuration is incomplete
   ```
   **Solution**: Check your `.env` file has:
   - `CONFLUENCE_URL`
   - `CONFLUENCE_USERNAME`
   - `CONFLUENCE_API_TOKEN`

### Performance Tips

- **Large Collections**: Scripts handle up to 1000 runbooks efficiently
- **Search Speed**: Semantic search typically takes 200-500ms
- **Memory Usage**: Each script loads the entire collection into memory

## 📊 Integration with DB Runbook Finder Workflow

These scripts complement the main DB Runbook Finder workflow by providing:

1. **Manual Search**: Test semantic search functionality independently
2. **Content Validation**: Verify discovered runbooks are properly indexed
3. **Analytics**: Monitor collection health and content distribution
4. **Debugging**: Troubleshoot discovery and population issues

The same ChromaDB collection (`mcdb-runbooks`) is used by both the workflow nodes and these utility scripts, ensuring consistency across the system.

## 🔧 Script Customization

All scripts can be modified for specific needs:

- **Change collection name**: Update the `collection_name` parameter
- **Adjust result limits**: Modify `n_results` parameter in search
- **Add filters**: Use metadata filters in vector store queries
- **Custom output formats**: Modify print statements for different formats

## 📝 Logging

Scripts provide detailed error messages and troubleshooting guidance. For more verbose logging during discovery, use:

```bash
uv run python -m usecases.db_runbook_finder.discover_runbooks --log-level DEBUG --collection-name mcdb-runbooks
```