"""
Confluence Runbook Discovery and ChromaDB Population System

This module implements a production-ready Confluence runbook discovery system that 
automatically crawls hierarchical runbook structures from multiple root URLs and 
populates ChromaDB with structured runbook content for semantic search.
"""

import logging
import re
import time
from typing import Dict, List, Set

from tools.confluence.app.confluence import ConfluenceClient
from tools.confluence.app.vector_store import VectorStore
from tools.confluence.app.models import RunbookContent, DiscoveryResult, PopulationResult


logger = logging.getLogger(__name__)


class RunbookDiscoveryService:
    """
    Service for discovering runbooks from Confluence hierarchical structures
    and populating ChromaDB for semantic search.
    """
    
    def __init__(self, collection_name: str = "mcdb-runbooks"):
        """
        Initialize the RunbookDiscoveryService.
        
        Args:
            collection_name: ChromaDB collection name (defaults to 'mcdb-runbooks')
        """
        self.confluence_client = ConfluenceClient()  # Uses .env credentials
        self.vector_store = VectorStore(collection_name=collection_name)
        self.collection_name = collection_name
        
        # Root URLs for client-specific runbooks
        self.root_urls = [
            "https://nordcloud.atlassian.net/wiki/spaces/MCDBA/pages/4012343437/Helvetia+Runbooks",
            "https://nordcloud.atlassian.net/wiki/spaces/MCDBA/pages/4322296000/Neste+Runbooks"
        ]
        
        # Runbook detection patterns based on screenshot analysis
        self.include_patterns = [
            r'\brunbook\b',
            r'\binstructions?\b',
            r'\bprocedure\b',
            r'\bguide\b', 
            r'\baccess\b',
            r'\bchecklist\b',
            r'\bmonitoring\b',
            r'\brestore\b',
            r'\bpatching\b',
            r'\bupgrade\b',
            r'\bonboarding\b',
            r'\bhotel\b'
        ]
        
        self.exclude_patterns = [
            r'\brunbooks\b',  # plural form (navigation pages)
            r'\bknown issues\b',
            r'\bgeneral instructions\b'
        ]
        
        # Caching to avoid re-processing unchanged pages
        self._processed_pages: Set[str] = set()
        
    def extract_page_id_from_url(self, url: str) -> str:
        """
        Extract page ID from Confluence URL.
        
        Args:
            url: Confluence page URL (e.g., 'https://nordcloud.atlassian.net/wiki/spaces/MCDBA/pages/4012343437/Helvetia+Runbooks')
            
        Returns:
            Page ID extracted from URL
            
        Raises:
            ValueError: If URL format is invalid or page ID cannot be extracted
        """
        if not url or not url.strip():
            raise ValueError("URL cannot be empty")
        
        # Pattern for Confluence URLs: /pages/{pageId}/
        pattern = r'/pages/(\d+)/'
        match = re.search(pattern, url)
        
        if not match:
            raise ValueError(f"Could not extract page ID from URL: {url}")
        
        return match.group(1)
    
    def get_client_name_from_url(self, url: str) -> str:
        """
        Determine client name from root URL for tagging purposes.
        
        Args:
            url: Root URL being processed
            
        Returns:
            Client name (helvetia, neste, or unknown)
        """
        url_lower = url.lower()
        if 'helvetia' in url_lower:
            return 'helvetia'
        elif 'neste' in url_lower:
            return 'neste'
        else:
            return 'unknown'
    
    def is_likely_runbook(self, page: Dict) -> bool:
        """
        Simple pattern-based runbook detection.
        
        Args:
            page: Page dictionary from Confluence API
            
        Returns:
            True if page is likely a runbook, False otherwise
        """
        if not page or not isinstance(page, dict):
            return False
        
        title = page.get('title', '').lower()
        
        # Check exclude patterns first
        for exclude_pattern in self.exclude_patterns:
            if re.search(exclude_pattern, title, re.IGNORECASE):
                logger.debug(f"Page '{title}' excluded by pattern: {exclude_pattern}")
                return False
        
        # Check include patterns
        for include_pattern in self.include_patterns:
            if re.search(include_pattern, title, re.IGNORECASE):
                logger.debug(f"Page '{title}' included by pattern: {include_pattern}")
                return True
        
        logger.debug(f"Page '{title}' does not match any runbook patterns")
        return False
    
    def discover_runbooks_from_root(self, root_url: str, max_depth: int = 3) -> List[RunbookContent]:
        """
        Simple hierarchical traversal discovery from a root URL.
        
        Args:
            root_url: Root Confluence page URL to start discovery from
            max_depth: Maximum depth to traverse (default: 3)
            
        Returns:
            List of discovered RunbookContent objects
        """
        logger.info(f"Starting runbook discovery from: {root_url}")
        
        try:
            # Extract page ID from URL
            root_page_id = self.extract_page_id_from_url(root_url)
            client_name = self.get_client_name_from_url(root_url)
            
            discovered_runbooks = []
            
            def traverse_hierarchy(current_page_id: str, depth: int = 0, parent_title: str = ""):
                """Recursive function to traverse page hierarchy."""
                
                if depth > max_depth:
                    logger.debug(f"Max depth ({max_depth}) reached at page {current_page_id}")
                    return
                
                # Avoid re-processing the same page
                if current_page_id in self._processed_pages:
                    logger.debug(f"Page {current_page_id} already processed, skipping")
                    return
                
                try:
                    # Get current page info for context
                    current_page = self.confluence_client.get_page_by_id(current_page_id)
                    current_title = current_page.get('title', '')
                    
                    logger.debug(f"Processing page at depth {depth}: '{current_title}' (ID: {current_page_id})")
                    
                    # Get child pages
                    children = self.confluence_client.get_page_children(current_page_id)
                    logger.debug(f"Found {len(children)} child pages for '{current_title}'")
                    
                    for child in children:
                        child_id = child.get('id')
                        child_title = child.get('title', '')
                        
                        if not child_id:
                            logger.warning(f"Child page missing ID, skipping: {child}")
                            continue
                        
                        # Check if this child is likely a runbook
                        if self.is_likely_runbook(child):
                            try:
                                # Get full page content and extract runbook structure
                                page_content = self.confluence_client.get_page_by_id(child_id)
                                runbook_content = self.confluence_client.extract_runbook_content(page_content)
                                
                                # Add client-specific tags
                                existing_tags = runbook_content.metadata.tags or []
                                client_tags = [client_name, "database", "runbook"]
                                all_tags = list(set(existing_tags + client_tags))
                                
                                # Update metadata with client context
                                runbook_content.metadata.tags = all_tags
                                
                                discovered_runbooks.append(runbook_content)
                                self._processed_pages.add(child_id)
                                
                                logger.info(f"✓ Discovered runbook: '{child_title}' (ID: {child_id}, Client: {client_name})")
                                
                            except Exception as e:
                                logger.error(f"Failed to extract runbook content from '{child_title}' (ID: {child_id}): {e}")
                        
                        # Recurse into children regardless of whether current page is a runbook
                        if depth < max_depth:
                            traverse_hierarchy(child_id, depth + 1, child_title)
                
                except Exception as e:
                    logger.error(f"Failed to process page {current_page_id} at depth {depth}: {e}")
            
            # Start traversal from root
            traverse_hierarchy(root_page_id)
            
            logger.info(f"Completed discovery from {root_url}: found {len(discovered_runbooks)} runbooks")
            return discovered_runbooks
            
        except Exception as e:
            logger.error(f"Failed to discover runbooks from {root_url}: {e}")
            return []
    
    def populate_chromadb(self, runbooks: List[RunbookContent]) -> PopulationResult:
        """
        Batch populate ChromaDB with discovered runbooks.
        
        Args:
            runbooks: List of RunbookContent objects to populate
            
        Returns:
            PopulationResult with operation statistics
        """
        start_time = time.time()
        
        logger.info(f"Starting ChromaDB population of {len(runbooks)} runbooks into collection '{self.collection_name}'")
        
        successful_populations = 0
        failed_populations = 0
        populated_runbook_ids = []
        errors = []
        deduplication_stats = {"duplicates_found": 0, "unique_runbooks": 0}
        
        # Track seen runbooks for deduplication by page_id
        seen_page_ids = set()
        unique_runbooks = []
        
        # Deduplication phase
        for runbook in runbooks:
            page_id = runbook.metadata.page_id
            if page_id in seen_page_ids:
                deduplication_stats["duplicates_found"] += 1
                logger.debug(f"Duplicate page_id found: {page_id}, skipping")
            else:
                seen_page_ids.add(page_id)
                unique_runbooks.append(runbook)
        
        deduplication_stats["unique_runbooks"] = len(unique_runbooks)
        
        # Population phase
        for runbook in unique_runbooks:
            try:
                runbook_id = self.vector_store.add_runbook(runbook)
                populated_runbook_ids.append(runbook_id)
                successful_populations += 1
                
                logger.debug(f"✓ Populated runbook: '{runbook.metadata.title}' (ID: {runbook_id})")
                
            except Exception as e:
                failed_populations += 1
                error_msg = f"Failed to populate runbook '{runbook.metadata.title}': {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        processing_time = time.time() - start_time
        
        result = PopulationResult(
            total_runbooks=len(runbooks),
            successful_populations=successful_populations,
            failed_populations=failed_populations,
            processing_time=processing_time,
            collection_name=self.collection_name,
            populated_runbook_ids=populated_runbook_ids,
            errors=errors,
            deduplication_stats=deduplication_stats
        )
        
        logger.info(f"ChromaDB population completed: {successful_populations}/{len(unique_runbooks)} successful, "
                   f"{failed_populations} failed, {processing_time:.2f}s")
        
        return result
    
    def discover_and_populate(self, dry_run: bool = False) -> DiscoveryResult:
        """
        Main entry point for runbook discovery and ChromaDB population.
        
        Args:
            dry_run: If True, only discover runbooks without populating ChromaDB
            
        Returns:
            DiscoveryResult with comprehensive operation statistics
        """
        start_time = time.time()
        
        logger.info(f"Starting runbook discovery and population (dry_run={dry_run})")
        logger.info(f"Root URLs to scan: {self.root_urls}")
        
        all_discovered_runbooks = []
        total_discovered = 0
        successful_discoveries = 0
        failed_discoveries = 0
        errors = []
        client_stats = {}
        
        # Discovery phase - process each root URL
        for root_url in self.root_urls:
            client_name = self.get_client_name_from_url(root_url)
            
            try:
                logger.info(f"Processing {client_name.title()} runbooks from: {root_url}")
                
                client_runbooks = self.discover_runbooks_from_root(root_url)
                client_count = len(client_runbooks)
                
                all_discovered_runbooks.extend(client_runbooks)
                total_discovered += client_count
                successful_discoveries += client_count
                client_stats[client_name] = client_count
                
                logger.info(f"✓ {client_name.title()} discovery completed: {client_count} runbooks found")
                
            except Exception as e:
                failed_discoveries += 1
                error_msg = f"Failed to discover runbooks from {root_url} ({client_name}): {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
                client_stats[client_name] = 0
        
        # Population phase (if not dry run)
        population_result = None
        if not dry_run and all_discovered_runbooks:
            try:
                logger.info("Starting ChromaDB population phase...")
                population_result = self.populate_chromadb(all_discovered_runbooks)
                
                if population_result.errors:
                    errors.extend(population_result.errors)
                    
            except Exception as e:
                error_msg = f"ChromaDB population failed: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        # Create final result
        final_processing_time = time.time() - start_time
        
        result = DiscoveryResult(
            total_discovered=total_discovered,
            successful_discoveries=successful_discoveries,
            failed_discoveries=failed_discoveries,
            processing_time=final_processing_time,
            root_urls=self.root_urls,
            discovered_runbooks=all_discovered_runbooks,
            errors=errors,
            client_stats=client_stats
        )
        
        # Log final summary
        logger.info("=" * 60)
        logger.info("RUNBOOK DISCOVERY SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total discovered: {total_discovered}")
        logger.info(f"Successful discoveries: {successful_discoveries}")
        logger.info(f"Failed discoveries: {failed_discoveries}")
        logger.info(f"Processing time: {final_processing_time:.2f}s")
        logger.info(f"Client statistics: {client_stats}")
        
        if population_result:
            logger.info(f"ChromaDB populations: {population_result.successful_populations}/{population_result.total_runbooks}")
            logger.info(f"Deduplication: {population_result.deduplication_stats}")
        
        if errors:
            logger.warning(f"Errors encountered: {len(errors)}")
            for error in errors:
                logger.warning(f"  - {error}")
        
        logger.info("=" * 60)
        
        return result