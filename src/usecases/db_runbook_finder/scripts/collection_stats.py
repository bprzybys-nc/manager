#!/usr/bin/env python3
"""
Show detailed statistics about the mcdb-runbooks ChromaDB collection.

This script provides comprehensive analytics on the runbook collection including
chunk distribution, client breakdown, and content analysis.
"""

import sys
from pathlib import Path
from dotenv import load_dotenv
from collections import Counter

# Add manager src to path and load environment
manager_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(manager_root / "src"))
load_dotenv(manager_root / ".env")

from tools.confluence.app.vector_store import VectorStore


def main():
    """Show detailed collection statistics."""
    try:
        # Initialize vector store
        vs = VectorStore(collection_name='mcdb-runbooks')
        
        # Get collection info
        collection = vs._collection
        count = collection.count()
        
        print('📊 ChromaDB Collection Analytics: mcdb-runbooks')
        print('='*60)
        
        if count == 0:
            print("❌ Collection is empty. Run discovery first:")
            print("uv run python -m usecases.db_runbook_finder.discover_runbooks --collection-name mcdb-runbooks")
            return
        
        # Get all documents
        results = collection.get(limit=1000)
        
        # Basic stats
        print('📈 BASIC STATISTICS')
        print(f'   Total chunks: {count}')
        print(f'   Documents retrieved: {len(results["ids"])}')
        print()
        
        # Analyze by runbook
        runbook_stats = {}
        client_stats = Counter()
        tag_stats = Counter()
        content_lengths = []
        
        for i, doc_id in enumerate(results['ids']):
            metadata = results['metadatas'][i]
            document = results['documents'][i] if results['documents'] else ""
            
            runbook_id = metadata.get('runbook_id', 'unknown')
            title = metadata.get('title', 'Unknown')
            tags = metadata.get('tags', [])
            
            # Runbook stats
            if runbook_id not in runbook_stats:
                client = 'Helvetia' if 'helvetia' in tags else 'Neste' if 'neste' in tags else 'Unknown'
                runbook_stats[runbook_id] = {
                    'title': title,
                    'client': client,
                    'chunks': 0,
                    'total_content_length': 0,
                    'page_id': metadata.get('page_id', 'Unknown')
                }
            
            runbook_stats[runbook_id]['chunks'] += 1
            runbook_stats[runbook_id]['total_content_length'] += len(document)
            
            # Client and tag stats
            for tag in tags:
                tag_stats[tag] += 1
                if tag in ['helvetia', 'neste']:
                    client_stats[tag.title()] += 1
            
            content_lengths.append(len(document))
        
        # Client breakdown
        print('🏢 CLIENT BREAKDOWN')
        for client, chunk_count in client_stats.items():
            runbook_count = sum(1 for r in runbook_stats.values() if r['client'].lower() == client.lower())
            print(f'   {client}: {runbook_count} runbooks ({chunk_count} chunks)')
        print()
        
        # Chunk distribution
        chunk_counts = [r['chunks'] for r in runbook_stats.values()]
        print('🧩 CHUNK DISTRIBUTION')
        print(f'   Average chunks per runbook: {sum(chunk_counts) / len(chunk_counts):.1f}')
        print(f'   Min chunks: {min(chunk_counts)}')
        print(f'   Max chunks: {max(chunk_counts)}')
        print(f'   Total runbooks: {len(runbook_stats)}')
        print()
        
        # Content length analysis
        print('📝 CONTENT ANALYSIS')
        print(f'   Average chunk length: {sum(content_lengths) / len(content_lengths):.0f} chars')
        print(f'   Shortest chunk: {min(content_lengths)} chars')
        print(f'   Longest chunk: {max(content_lengths)} chars')
        print(f'   Total content: {sum(content_lengths):,} chars')
        print()
        
        # Top runbooks by content
        print('📚 TOP RUNBOOKS BY CONTENT SIZE')
        sorted_runbooks = sorted(runbook_stats.values(), key=lambda x: x['total_content_length'], reverse=True)
        for i, runbook in enumerate(sorted_runbooks[:5], 1):
            print(f'   {i}. {runbook["title"]} ({runbook["client"]})')
            print(f'      {runbook["chunks"]} chunks, {runbook["total_content_length"]:,} chars')
        print()
        
        # Most chunked runbooks
        print('🧩 MOST CHUNKED RUNBOOKS')
        sorted_by_chunks = sorted(runbook_stats.values(), key=lambda x: x['chunks'], reverse=True)
        for i, runbook in enumerate(sorted_by_chunks[:5], 1):
            print(f'   {i}. {runbook["title"]} ({runbook["client"]})')
            print(f'      {runbook["chunks"]} chunks, {runbook["total_content_length"]:,} chars')
        print()
        
        # Tag analysis
        print('🏷️ TAG DISTRIBUTION')
        for tag, count in tag_stats.most_common():
            print(f'   {tag}: {count} chunks')
        print()
        
        print('='*60)
        print(f'✅ Analysis complete - {len(runbook_stats)} runbooks, {count} chunks')
        
    except Exception as e:
        print(f'❌ Error analyzing collection: {e}')
        print("\nTroubleshooting:")
        print("1. Make sure ChromaDB is accessible")
        print("2. Check if runbooks are populated in collection")
        print("3. Verify .env file configuration")
        sys.exit(1)


if __name__ == "__main__":
    main()