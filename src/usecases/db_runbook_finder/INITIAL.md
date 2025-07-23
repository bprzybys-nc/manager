# Confluence Runbook Discovery and ChromaDB Population System

FEATURE:
Create a production-ready Confluence runbook discovery system that automatically crawls hierarchical runbook structures from multiple root URLs and populates ChromaDB with structured runbook content for semantic search. The system implements simple hierarchical traversal to discover runbooks from client-specific root pages (Helvetia, Neste) and indexes them in a shared 'mcdb-runbooks' ChromaDB collection for the DB Runbook Finder workflow.

## Core Requirements

### Root URLs to Scan
- **Helvetia**: `https://nordcloud.atlassian.net/wiki/spaces/MCDBA/pages/4012343437/Helvetia+Runbooks`  
- **Neste**: `https://nordcloud.atlassian.net/wiki/spaces/MCDBA/pages/4322296000/Neste+Runbooks`
- **ChromaDB Collection**: `mcdb-runbooks` (follows kebab-case naming convention)

### Discovery Algorithm
Simple hierarchical traversal with max depth of 3 levels:
```
Root Page → Client Sections → Individual Runbooks
Helvetia+Runbooks → Known Issues → Oracle DB Healthcheck, DB2 Hotel, etc.
```

### Runbook Detection Criteria
Based on screenshot analysis, identify pages containing:
- **Include patterns**: runbook, instructions, procedure, guide, access, checklist, monitoring, restore, patching, upgrade, onboarding, hotel
- **Exclude patterns**: runbooks (plural), known issues, general instructions (navigation pages)

## Implementation Structure

```python
class RunbookDiscoveryService:
    def __init__(self, collection_name: str = "mcdb-runbooks"):
        self.confluence_client = ConfluenceClient()  # Uses .env credentials
        self.vector_store = VectorStore(collection_name=collection_name)
        self.root_urls = [
            "https://nordcloud.atlassian.net/wiki/spaces/MCDBA/pages/4012343437/Helvetia+Runbooks",
            "https://nordcloud.atlassian.net/wiki/spaces/MCDBA/pages/4322296000/Neste+Runbooks"
        ]
    
    def discover_and_populate(self) -> DiscoveryResult:
        """Main entry point for runbook discovery and ChromaDB population."""
        
    def discover_runbooks_from_root(self, root_url: str, max_depth: int = 3) -> List[RunbookContent]:
        """Simple hierarchical traversal discovery."""
        
    def is_likely_runbook(self, page: dict) -> bool:
        """Simple pattern-based runbook detection."""
        
    def populate_chromadb(self, runbooks: List[RunbookContent]) -> PopulationResult:
        """Batch populate ChromaDB with discovered runbooks."""
```

EXAMPLES:
Based on existing patterns in `src/tools/confluence/app/vector_store.py` and `src/usecases/db_runbook_finder/nodes.py`:

1. **VectorStore Integration Pattern**:
```python
# From tools/confluence/app/vector_store.py:310-395
vector_store = VectorStore(collection_name="mcdb-runbooks")
runbook_id = vector_store.add_runbook(runbook_content)
search_results = vector_store.search_runbooks(query, n_results=5)
```

2. **Confluence Client Usage Pattern**:
```python  
# From tools/confluence/app/api.py integration
confluence_client = ConfluenceClient()
children = confluence_client.get_page_children(page_id)
content = confluence_client.get_page_content(page_id)
```

3. **RunbookContent Structure Pattern**:
```python
# From tools/confluence/app/models.py
runbook_content = RunbookContent(
    metadata=RunbookMetadata(
        title=page['title'],
        space_key="MCDBA", 
        page_id=page['id'],
        page_url=page_url,
        tags=["helvetia", "database", "runbook"]
    ),
    procedures=extracted_procedures,
    troubleshooting_steps=extracted_troubleshooting,
    raw_content=page_content
)
```

4. **DB Runbook Finder Integration Pattern**:
```python
# From nodes.py:162-175 - how the discovery system will be used
if self.use_real_tools and self.confluence_configured:
    from src.tools.confluence.app.api import ConfluenceClient
    confluence_client = ConfluenceClient()
    response = await confluence_client.search_runbooks(
        query=query,
        spaces=["MCDBA"], 
        limit=3
    )
    state.runbooks = response.get("results", [])
```

5. **Hierarchical Discovery Pattern**:
```python
def discover_runbooks_simple(root_page_url: str, max_depth: int = 3) -> List[RunbookContent]:
    """Simple runbook discovery using hierarchical traversal."""
    
    # Extract page ID from URL
    page_id = extract_page_id_from_url(root_page_url)
    
    discovered_runbooks = []
    
    def traverse_hierarchy(current_page_id: str, depth: int = 0):
        if depth > max_depth:
            return
            
        # Get child pages
        children = confluence_client.get_page_children(current_page_id)
        
        for child in children:
            # Simple runbook detection criteria
            if is_likely_runbook(child):
                runbook_content = extract_runbook_content(child)
                discovered_runbooks.append(runbook_content)
            
            # Recurse into children
            if depth < max_depth:
                traverse_hierarchy(child['id'], depth + 1)
    
    traverse_hierarchy(page_id)
    return discovered_runbooks
```

DOCUMENTATION:
- **ChromaDB Collection Naming**: Follow kebab-case convention (`mcdb-runbooks` not `mc_runbooks` or `mcRunbooks`)
- **Confluence REST API**: For `get_page_children()`, `get_page_content()` operations
- **VectorStore Documentation**: `src/tools/confluence/app/vector_store.py` - existing ChromaDB integration patterns
- **DB Runbook Finder Integration**: `src/usecases/db_runbook_finder/nodes.py:135-196` - how discovered runbooks are consumed
- **Environment Variables**: `.env` file contains `CONFLUENCE_URL`, `CONFLUENCE_USERNAME`, `CONFLUENCE_API_TOKEN`
- **URL Pattern Analysis**: Based on screenshots showing `nordcloud.atlassian.net/wiki/spaces/MCDBA/pages/{pageId}/{title}` structure
- **Runbook Structure**: Helvetia runbooks show pattern of client → category → individual runbooks (Oracle DB Healthcheck, DB2 Hotel, SQL Server Access, etc.)

OTHER CONSIDERATIONS:
- **Single Environment Rule**: Use manager's unified `.venv` - no separate virtual environments
- **Error Handling**: Graceful handling of missing pages, network failures, and malformed content
- **Batch Processing**: Process multiple root URLs efficiently with proper logging
- **Deduplication**: Handle potential duplicate runbooks across client boundaries  
- **Performance**: Implement basic caching to avoid re-processing unchanged pages
- **ChromaDB Collection Management**: Ensure collection exists and handle empty collection scenarios (existing fix in vector_store.py:338-341)
- **Content Extraction**: Parse Confluence markup to extract structured procedures, troubleshooting steps, and prerequisites
- **Hierarchy Preservation**: Maintain client context (Helvetia vs Neste) in metadata for better search filtering
- **Integration Testing**: Validate discovered runbooks work with existing `search_runbooks_node()` in the workflow
- **Dry Run Mode**: Support discovery preview without ChromaDB population for validation
- **URL Parsing**: Extract page IDs from Confluence URLs (pattern: `/pages/{pageId}/` from the root URLs)
- **Client Tagging**: Add client-specific tags (helvetia, neste) to runbook metadata for filtering
- **Authentication**: Use existing `.env` credentials (`CONFLUENCE_USERNAME`, `CONFLUENCE_API_TOKEN`) from the Confluence tool
- **Existing Tool Integration**: Leverage `src/tools/confluence/app/confluence.py` ConfluenceClient for API operations rather than creating new clients