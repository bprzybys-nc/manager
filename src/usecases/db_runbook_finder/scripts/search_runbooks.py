#!/usr/bin/env python3
"""
Semantic search for runbooks in the mcdb-runbooks ChromaDB collection.

This script performs semantic search on discovered runbooks using vector embeddings.
"""

import sys
from pathlib import Path
from dotenv import load_dotenv

# Add manager src to path and load environment
manager_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(manager_root / "src"))
load_dotenv(manager_root / ".env")

from tools.confluence.app.vector_store import VectorStore


def main():
    """Perform semantic search on runbooks."""
    if len(sys.argv) < 2:
        print("🔍 Runbook Semantic Search")
        print("="*40)
        print("Usage: python search_runbooks.py '<search_text>'")
        print()
        print("Example searches:")
        print("  python search_runbooks.py 'database access'")
        print("  python search_runbooks.py 'backup restore procedures'")
        print("  python search_runbooks.py 'DB2 troubleshooting'")
        print("  python search_runbooks.py 'oracle monitoring'")
        print("  python search_runbooks.py 'onboarding checklist'")
        sys.exit(1)
    
    query = " ".join(sys.argv[1:])
    
    try:
        # Initialize vector store
        vs = VectorStore(collection_name='mcdb-runbooks')
        
        # Check if collection has data
        count = vs._collection.count()
        if count == 0:
            print("❌ No runbooks found in collection.")
            print("Run discovery first:")
            print("uv run python -m usecases.db_runbook_finder.discover_runbooks --collection-name mcdb-runbooks")
            return
        
        print(f'🔍 Searching: "{query}"')
        print(f'📊 Collection: mcdb-runbooks ({count} chunks)')
        print('='*60)
        
        # Perform semantic search
        results = vs.search_runbooks(query, n_results=5)
        
        if not results:
            print("🤷 No results found for your query.")
            print()
            print("💡 Tips:")
            print("- Try different keywords")
            print("- Use broader search terms")
            print("- Check spelling")
            return
        
        print(f'📋 Found {len(results)} relevant results:')
        print()
        
        for i, result in enumerate(results, 1):
            # Determine client from tags
            client = "🏢 Helvetia" if "helvetia" in result.metadata.tags else "🏢 Neste" if "neste" in result.metadata.tags else "❓ Unknown"
            
            # Relevance indicator for aggregate score
            score = result.relevance_score
            if score >= 0.8:
                relevance = "🎯 Very Relevant"
            elif score >= 0.6:
                relevance = "✅ Relevant"  
            elif score >= 0.4:
                relevance = "⚠️ Somewhat Relevant"
            else:
                relevance = "❌ Low Relevance"
            
            # Runbook-level information
            print(f'{i}. 📖 {result.metadata.title}')
            print(f'   {client} | {relevance} ({score:.3f})')
            print(f'   📄 Page ID: {result.metadata.page_id}')
            
            # Show aggregation stats if available
            if hasattr(result, '_chunk_count'):
                chunk_count = result._chunk_count
                max_score = result._max_chunk_score
                avg_score = result._avg_chunk_score
                print(f'   📊 Aggregate Score: {score:.3f} (best: {max_score:.3f}, avg: {avg_score:.3f}, {chunk_count} chunks)')
                
                # Show best matching content (truncated)
                content = result.content.strip()
                if len(content) > 200:
                    content = content[:200] + "..."
                print(f'   💬 Best Match: {content}')
                
                # Show supporting chunks in tree format
                if hasattr(result, '_supporting_chunks') and result._supporting_chunks:
                    print(f'   🧩 Supporting Evidence:')
                    for j, chunk in enumerate(result._supporting_chunks[:3], 1):  # Show top 3
                        chunk_content = chunk['content'].strip()
                        if len(chunk_content) > 150:
                            chunk_content = chunk_content[:150] + "..."
                        chunk_score = chunk['score']
                        chunk_relevance = "🎯" if chunk_score >= 0.8 else "✅" if chunk_score >= 0.6 else "⚠️" if chunk_score >= 0.4 else "❌"
                        print(f'      └─ {j}. {chunk_relevance} ({chunk_score:.3f}) {chunk_content}')
            else:
                # Fallback for non-aggregated results
                content = result.content.strip()
                if len(content) > 200:
                    content = content[:200] + "..."
                print(f'   💬 Content: {content}')
            
            print(f'   🔗 URL: {result.metadata.page_url}')
            print()
        
        print('='*60)
        print(f'✅ Search completed - {len(results)} results')
        
        # Suggest related searches based on results
        if results:
            print()
            print("💡 Try related searches:")
            if any("access" in r.metadata.title.lower() for r in results):
                print("  python search_runbooks.py 'server login credentials'")
            if any("restore" in r.metadata.title.lower() for r in results):
                print("  python search_runbooks.py 'backup recovery procedures'")
            if any("db2" in r.metadata.title.lower() for r in results):
                print("  python search_runbooks.py 'DB2 administration'")
            if any("oracle" in r.metadata.title.lower() for r in results):
                print("  python search_runbooks.py 'oracle database management'")
        
    except Exception as e:
        print(f'❌ Error performing search: {e}')
        print("\nTroubleshooting:")
        print("1. Make sure ChromaDB is accessible")
        print("2. Check if runbooks are populated in collection")
        print("3. Verify .env file configuration")
        sys.exit(1)


if __name__ == "__main__":
    main()