#!/usr/bin/env python3
"""
CLI Interface for Runbook Discovery

This script provides a command-line interface for discovering runbooks from
Confluence and populating ChromaDB for the DB Runbook Finder workflow.
"""

import argparse
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


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Discover runbooks from Confluence and populate ChromaDB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run - discover without populating ChromaDB
  python discover_runbooks.py --dry-run
  
  # Full discovery and population
  python discover_runbooks.py --collection-name mcdb-runbooks
  
  # Debug mode with verbose logging
  python discover_runbooks.py --log-level DEBUG --dry-run
  
  # Custom collection with summary output
  python discover_runbooks.py --collection-name custom-runbooks --summary-only
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
        default=3,
        help='Maximum traversal depth for hierarchical discovery (default: 3)'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    logger = setup_logging(args.log_level)
    
    try:
        logger.info("Starting Confluence Runbook Discovery CLI")
        logger.info(f"Collection: {args.collection_name}")
        logger.info(f"Dry run: {args.dry_run}")
        logger.info(f"Max depth: {args.max_depth}")
        
        # Initialize discovery service
        service = RunbookDiscoveryService(collection_name=args.collection_name)
        
        # Override max depth if provided (would need to modify service to support this)
        logger.info(f"Using max traversal depth: {args.max_depth}")
        
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


if __name__ == "__main__":
    main()