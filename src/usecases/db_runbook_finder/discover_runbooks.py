#!/usr/bin/env python3
"""
CLI Interface for Runbook Discovery

This script provides a command-line interface for discovering runbooks from
Confluence and populating ChromaDB for the DB Runbook Finder workflow.
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add manager src to path
manager_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(manager_root))

# Load environment variables from .env file
env_file = manager_root.parent / ".env"
if env_file.exists():
    load_dotenv(env_file)

from usecases.db_runbook_finder.runbook_discovery_service import RunbookDiscoveryService  # noqa: E402


def setup_logging(level: str = "INFO") -> logging.Logger:
    """
    Setup logging configuration.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        
    Returns:
        Configured logger
    """
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('runbook_discovery.log')
        ]
    )
    
    return logging.getLogger(__name__)


async def handle_collection_clearing(
    service, 
    dry_run: bool, 
    no_confirm: bool
) -> None:
    """
    Handle collection clearing with appropriate safety checks.
    
    Args:
        service: RunbookDiscoveryService instance
        dry_run: Whether this is a dry run
        no_confirm: Whether to skip confirmation prompts
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Get collection statistics
        stats = await service.get_collection_stats()
        
        # Display clearing preview
        print("\n" + "=" * 60)
        print("COLLECTION CLEARING PREVIEW")
        print("=" * 60)
        print(f"Collection Name: {stats.collection_name}")
        print(f"Current Documents: {stats.document_count}")
        
        if stats.sample_documents:
            print("Sample Documents:")
            for i, title in enumerate(stats.sample_documents, 1):
                print(f"  {i}. {title}")
        
        if dry_run:
            print("\n🔍 DRY RUN MODE: Collection would be cleared but no actual changes will be made")
            print("=" * 60)
            return
        
        # Confirmation logic
        if stats.document_count > 0:
            if no_confirm:
                print("\n⚠️  --no-confirm specified: Clearing without user confirmation")
                confirmation = True
            else:
                print(f"\n⚠️  This will permanently delete {stats.document_count} documents from '{stats.collection_name}'")
                response = input("Are you sure you want to proceed? (type 'yes' to confirm): ")
                confirmation = response.lower() == 'yes'
                
                if not confirmation:
                    print("❌ Clearing cancelled by user")
                    sys.exit(0)
        else:
            print("\n✅ Collection is already empty, no clearing needed")
            print("=" * 60)
            return
        
        # Perform clearing
        print(f"\n🧹 Clearing collection '{stats.collection_name}'...")
        clearing_result = await service.clear_collection(confirmation=confirmation)
        
        if clearing_result.success:
            print(f"✅ Successfully cleared {clearing_result.documents_cleared} documents in {clearing_result.clearing_time:.2f}s")
        else:
            print(f"❌ Clearing failed: {clearing_result.error_message}")
            sys.exit(1)
            
        print("=" * 60)
        
    except Exception as e:
        logger.error(f"Collection clearing failed: {e}")
        raise


async def main_async():
    """Enhanced async main function with clearing capabilities."""
    parser = argparse.ArgumentParser(
        description="Discover runbooks from Confluence and populate ChromaDB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Clear existing collection and repopulate
  python discover_runbooks.py --clear-existing --collection-name mcdb-runbooks
  
  # Dry run showing what would be cleared
  python discover_runbooks.py --dry-run --clear-existing
  
  # Force clearing without confirmation (automation use)
  python discover_runbooks.py --clear-existing --no-confirm --collection-name prod-runbooks
  python discover_runbooks.py --clear-existing -y --collection-name prod-runbooks
  python discover_runbooks.py --clear-existing --yes --collection-name prod-runbooks
  
  # Clear and debug with verbose logging
  python discover_runbooks.py --clear-existing --log-level DEBUG
  
  # Full discovery and population (existing behavior)
  python discover_runbooks.py --collection-name mcdb-runbooks
  
  # Dry run - discover without populating ChromaDB
  python discover_runbooks.py --dry-run
        """
    )
    
    parser.add_argument(
        '--collection-name',
        default='mcdb-runbooks',
        help='ChromaDB collection name (default: mcdb-runbooks)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Discover runbooks without populating ChromaDB'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Set logging level (default: INFO)'
    )
    
    parser.add_argument(
        '--summary-only',
        action='store_true',
        help='Show only summary statistics, not detailed runbook info'
    )
    
    parser.add_argument(
        '--max-depth',
        type=int,
        default=5,
        help='Maximum traversal depth for hierarchical discovery (default: 5)'
    )
    
    parser.add_argument(
        '--clear-existing',
        action='store_true',
        help='Clear existing ChromaDB collection before discovery (requires confirmation unless --no-confirm)'
    )
    
    parser.add_argument(
        '--no-confirm', '-y', '--yes',
        action='store_true',
        help='Skip confirmation prompts for automation (use with caution)'
    )
    
    parser.add_argument(
        '--clear-existing',
        action='store_true',
        help='Clear existing ChromaDB collection before discovery (requires confirmation unless --no-confirm)'
    )
    
    parser.add_argument(
        '--no-confirm', '-y', '--yes',
        action='store_true',
        help='Skip confirmation prompts for automation (use with caution)'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    logger = setup_logging(args.log_level)
    
    # Validation
    if args.clear_existing and args.dry_run:
        logger.info("Dry run mode: Will show clearing preview without actually clearing data")
    
    try:
        logger.info("Starting Confluence Runbook Discovery CLI")
        logger.info(f"Collection: {args.collection_name}")
        logger.info(f"Dry run: {args.dry_run}")
        logger.info(f"Max depth: {args.max_depth}")
        
        # Initialize discovery service
        service = RunbookDiscoveryService(collection_name=args.collection_name)
        
        # Set max depth for discovery
        service.max_depth = args.max_depth
        logger.info(f"Using max traversal depth: {args.max_depth}")
        
        # Handle clearing if requested
        if args.clear_existing:
            await handle_collection_clearing(service, args.dry_run, args.no_confirm)
        
        # Run discovery
        result = service.discover_and_populate(dry_run=args.dry_run)
        
        # Display results
        print("\\n" + "=" * 80)
        print("RUNBOOK DISCOVERY RESULTS")
        print("=" * 80)
        
        print(f"Total discovered: {result.total_discovered}")
        print(f"Successful discoveries: {result.successful_discoveries}")
        print(f"Failed discoveries: {result.failed_discoveries}")
        print(f"Processing time: {result.processing_time:.2f}s")
        
        print("\\nClient Statistics:")
        for client, count in result.client_stats.items():
            print(f"  {client.title()}: {count} runbooks")
        
        if not args.dry_run and result.discovered_runbooks:
            # Show population statistics (would be available if population was run)
            print(f"\\nChromaDB Collection: {args.collection_name}")
            print("Note: Population statistics are included in the overall processing time")
        
        if result.errors:
            print(f"\\nErrors ({len(result.errors)}):")
            for i, error in enumerate(result.errors, 1):
                print(f"  {i}. {error}")
        
        if not args.summary_only and result.discovered_runbooks:
            print(f"\\nDiscovered Runbooks ({len(result.discovered_runbooks)}):")
            for i, runbook in enumerate(result.discovered_runbooks, 1):
                metadata = runbook.metadata
                print(f"  {i}. {metadata.title}")
                print(f"     ID: {metadata.page_id}")
                print(f"     Space: {metadata.space_key}")
                print(f"     URL: {metadata.page_url}")
                print(f"     Tags: {', '.join(metadata.tags) if metadata.tags else 'None'}")
                print(f"     Content Length: {len(runbook.raw_content)} chars")
                print()
        
        print("=" * 80)
        
        # Exit with appropriate code
        if result.failed_discoveries > 0:
            logger.warning(f"Discovery completed with {result.failed_discoveries} failures")
            sys.exit(1)
        else:
            logger.info("Discovery completed successfully")
            sys.exit(0)
            
    except KeyboardInterrupt:
        logger.info("Discovery cancelled by user")
        sys.exit(130)
        
    except Exception as e:
        logger.error(f"Discovery failed: {e}", exc_info=True)
        sys.exit(1)


def main():
    """Synchronous main entry point that runs the async main function."""
    asyncio.run(main_async())


if __name__ == "__main__":
    main()