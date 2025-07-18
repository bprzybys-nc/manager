"""
Performance tests for Confluence Integration Tool.

This module contains performance-focused tests for bulk operations,
search response times, and system scalability.
"""

import pytest
import time
import tempfile
import shutil
import statistics
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any

from .vector_store import VectorStore
from .models import RunbookContent, RunbookMetadata


class TestBulkOperationPerformance:
    """Performance tests for bulk operations."""
    
    @pytest.fixture(scope="class")
    def temp_db_dir(self):
        """Create temporary directory for performance test database."""
        temp_dir = tempfile.mkdtemp(prefix="confluence_bulk_perf_")
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture(scope="class")
    def vector_store(self, temp_db_dir):
        """Create VectorStore instance for performance testing."""
        return VectorStore(
            collection_name="bulk_perf_runbooks",
            persist_directory=temp_db_dir
        )
    
    def create_test_runbook(self, index: int, content_size: str = "medium") -> RunbookContent:
        """Create test runbook with specified content size."""
        content_multipliers = {
            "small": 10,
            "medium": 50,
            "large": 200
        }
        multiplier = content_multipliers.get(content_size, 50)
        
        base_content = f"This is test runbook {index} with detailed procedures and troubleshooting steps. "
        content = base_content * multiplier
        
        metadata = RunbookMetadata(
            title=f"Bulk Performance Test Runbook {index}",
            author=f"Performance Tester {index % 5}",  # Vary authors
            last_modified=datetime.utcnow(),
            space_key=f"PERF{index % 3}",  # Vary spaces
            page_id=f"bulk_perf_test_{index}",
            page_url=f"https://example.com/bulk_perf_test_{index}",
            tags=[f"bulk", f"performance", f"test_{index}", f"category_{index % 10}"]
        )
        
        return RunbookContent(
            metadata=metadata,
            procedures=[
                f"Step {i}: Perform bulk operation {i} for runbook {index}"
                for i in range(1, 6)
            ],
            troubleshooting_steps=[
                f"Issue {i}: Troubleshoot bulk problem {i} in runbook {index}"
                for i in range(1, 4)
            ],
            prerequisites=[
                f"Requirement {i} for bulk runbook {index}"
                for i in range(1, 3)
            ],
            raw_content=content,
            structured_sections={
                "overview": f"Bulk performance test runbook {index}",
                "procedures": f"Detailed procedures for bulk test {index}",
                "troubleshooting": f"Troubleshooting guide for bulk test {index}"
            }
        )
    
    @pytest.mark.performance
    def test_sequential_bulk_addition(self, vector_store):
        """Test sequential addition of multiple runbooks."""
        num_runbooks = 20
        runbooks = [self.create_test_runbook(i) for i in range(num_runbooks)]
        
        # Measure sequential addition
        start_time = time.time()
        runbook_ids = []
        
        for runbook in runbooks:
            runbook_id = vector_store.add_runbook(runbook)
            runbook_ids.append(runbook_id)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Performance assertions
        assert len(runbook_ids) == num_runbooks
        assert all(runbook_id is not None for runbook_id in runbook_ids)
        
        # Performance benchmarks
        avg_time_per_runbook = total_time / num_runbooks
        assert avg_time_per_runbook < 2.0, f"Average time per runbook too slow: {avg_time_per_runbook:.3f}s"
        assert total_time < 40.0, f"Total sequential addition time too slow: {total_time:.2f}s"
        
        print(f"Sequential addition: {num_runbooks} runbooks in {total_time:.2f}s "
              f"({avg_time_per_runbook:.3f}s per runbook)")
        
        return runbook_ids
    
    @pytest.mark.performance
    def test_concurrent_bulk_addition(self, vector_store):
        """Test concurrent addition of multiple runbooks."""
        num_runbooks = 15
        max_workers = 5
        runbooks = [self.create_test_runbook(i + 100) for i in range(num_runbooks)]
        
        def add_runbook_task(runbook):
            """Task function for concurrent execution."""
            return vector_store.add_runbook(runbook)
        
        # Measure concurrent addition
        start_time = time.time()
        runbook_ids = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_runbook = {
                executor.submit(add_runbook_task, runbook): runbook
                for runbook in runbooks
            }
            
            for future in as_completed(future_to_runbook):
                runbook_id = future.result()
                runbook_ids.append(runbook_id)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Performance assertions
        assert len(runbook_ids) == num_runbooks
        assert all(runbook_id is not None for runbook_id in runbook_ids)
        
        # Concurrent should be faster than sequential for same number of items
        avg_time_per_runbook = total_time / num_runbooks
        assert avg_time_per_runbook < 1.5, f"Concurrent average time too slow: {avg_time_per_runbook:.3f}s"
        assert total_time < 20.0, f"Total concurrent addition time too slow: {total_time:.2f}s"
        
        print(f"Concurrent addition: {num_runbooks} runbooks in {total_time:.2f}s "
              f"({avg_time_per_runbook:.3f}s per runbook, {max_workers} workers)")
        
        return runbook_ids
    
    @pytest.mark.performance
    def test_bulk_search_performance(self, vector_store):
        """Test search performance with bulk data."""
        # First add bulk data
        num_runbooks = 25
        runbooks = [self.create_test_runbook(i + 200) for i in range(num_runbooks)]
        
        for runbook in runbooks:
            vector_store.add_runbook(runbook)
        
        # Wait for indexing
        time.sleep(2.0)
        
        # Test various search queries
        search_queries = [
            "bulk performance test",
            "troubleshooting steps",
            "detailed procedures",
            "performance tester",
            "runbook category",
            "bulk operation",
            "test requirements",
            "structured sections"
        ]
        
        search_times = []
        total_results = 0
        
        for query in search_queries:
            start_time = time.time()
            results = vector_store.search_runbooks(query, n_results=10)
            end_time = time.time()
            
            search_time = end_time - start_time
            search_times.append(search_time)
            total_results += len(results)
            
            # Individual search performance
            assert search_time < 3.0, f"Search for '{query}' too slow: {search_time:.3f}s"
            assert isinstance(results, list)
        
        # Overall search performance statistics
        avg_search_time = statistics.mean(search_times)
        max_search_time = max(search_times)
        min_search_time = min(search_times)
        
        assert avg_search_time < 1.5, f"Average search time too slow: {avg_search_time:.3f}s"
        assert max_search_time < 3.0, f"Maximum search time too slow: {max_search_time:.3f}s"
        
        print(f"Bulk search performance: {len(search_queries)} queries, "
              f"avg: {avg_search_time:.3f}s, max: {max_search_time:.3f}s, "
              f"min: {min_search_time:.3f}s, total results: {total_results}")
    
    @pytest.mark.performance
    def test_bulk_update_performance(self, vector_store):
        """Test bulk update operations performance."""
        # Add initial runbooks
        num_runbooks = 10
        runbooks = [self.create_test_runbook(i + 300) for i in range(num_runbooks)]
        
        runbook_ids = []
        for runbook in runbooks:
            runbook_id = vector_store.add_runbook(runbook)
            runbook_ids.append(runbook_id)
        
        # Prepare updated runbooks
        updated_runbooks = []
        for i, runbook in enumerate(runbooks):
            updated_runbook = runbook.model_copy()
            updated_runbook.metadata.title = f"Updated {updated_runbook.metadata.title}"
            updated_runbook.procedures.append(f"Updated step: Additional procedure {i}")
            updated_runbooks.append(updated_runbook)
        
        # Measure bulk update performance
        start_time = time.time()
        
        for runbook_id, updated_runbook in zip(runbook_ids, updated_runbooks):
            vector_store.update_runbook(runbook_id, updated_runbook)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Performance assertions
        avg_update_time = total_time / num_runbooks
        assert avg_update_time < 3.0, f"Average update time too slow: {avg_update_time:.3f}s"
        assert total_time < 25.0, f"Total update time too slow: {total_time:.2f}s"
        
        # Verify updates
        for runbook_id, original_runbook in zip(runbook_ids, runbooks):
            updated_runbook = vector_store.get_runbook_by_id(runbook_id)
            assert updated_runbook is not None
            assert "Updated" in updated_runbook.metadata.title
            assert len(updated_runbook.procedures) > len(original_runbook.procedures)
        
        print(f"Bulk update: {num_runbooks} runbooks in {total_time:.2f}s "
              f"({avg_update_time:.3f}s per update)")
    
    @pytest.mark.performance
    def test_bulk_deletion_performance(self, vector_store):
        """Test bulk deletion performance."""
        # Add runbooks to delete
        num_runbooks = 15
        runbooks = [self.create_test_runbook(i + 400) for i in range(num_runbooks)]
        
        runbook_ids = []
        for runbook in runbooks:
            runbook_id = vector_store.add_runbook(runbook)
            runbook_ids.append(runbook_id)
        
        # Verify they exist
        for runbook_id in runbook_ids:
            runbook = vector_store.get_runbook_by_id(runbook_id)
            assert runbook is not None
        
        # Measure bulk deletion performance
        start_time = time.time()
        
        for runbook_id in runbook_ids:
            vector_store.delete_runbook(runbook_id)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Performance assertions
        avg_deletion_time = total_time / num_runbooks
        assert avg_deletion_time < 1.0, f"Average deletion time too slow: {avg_deletion_time:.3f}s"
        assert total_time < 15.0, f"Total deletion time too slow: {total_time:.2f}s"
        
        # Verify deletions
        for runbook_id in runbook_ids:
            runbook = vector_store.get_runbook_by_id(runbook_id)
            assert runbook is None
        
        print(f"Bulk deletion: {num_runbooks} runbooks in {total_time:.2f}s "
              f"({avg_deletion_time:.3f}s per deletion)")


class TestSearchPerformance:
    """Performance tests for search operations."""
    
    @pytest.fixture(scope="class")
    def temp_db_dir(self):
        """Create temporary directory for search performance test database."""
        temp_dir = tempfile.mkdtemp(prefix="confluence_search_perf_")
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture(scope="class")
    def populated_vector_store(self, temp_db_dir):
        """Create and populate VectorStore for search performance testing."""
        vector_store = VectorStore(
            collection_name="search_perf_runbooks",
            persist_directory=temp_db_dir
        )
        
        # Populate with diverse content
        categories = ["database", "network", "security", "monitoring", "deployment"]
        operations = ["backup", "restore", "configure", "troubleshoot", "optimize"]
        
        runbook_count = 0
        for category in categories:
            for operation in operations:
                for variant in range(3):  # 3 variants per category-operation combo
                    metadata = RunbookMetadata(
                        title=f"{category.title()} {operation.title()} Runbook v{variant + 1}",
                        author=f"{category.title()} Team",
                        last_modified=datetime.utcnow(),
                        space_key=category.upper()[:4],
                        page_id=f"{category}_{operation}_{variant}",
                        page_url=f"https://example.com/{category}_{operation}_{variant}",
                        tags=[category, operation, f"variant_{variant}", "performance_test"]
                    )
                    
                    content_base = f"""
                    This runbook covers {operation} procedures for {category} systems.
                    It includes step-by-step instructions, troubleshooting guides,
                    and best practices for {category} {operation} operations.
                    """
                    
                    runbook = RunbookContent(
                        metadata=metadata,
                        procedures=[
                            f"Step 1: Prepare {category} system for {operation}",
                            f"Step 2: Execute {operation} on {category} components",
                            f"Step 3: Verify {operation} completion for {category}",
                            f"Step 4: Document {operation} results for {category}"
                        ],
                        troubleshooting_steps=[
                            f"Check {category} system logs for {operation} errors",
                            f"Verify {category} connectivity during {operation}",
                            f"Restart {category} services if {operation} fails"
                        ],
                        prerequisites=[
                            f"Access to {category} systems",
                            f"Permissions for {operation} operations",
                            f"Knowledge of {category} architecture"
                        ],
                        raw_content=content_base * (variant + 1),  # Vary content length
                        structured_sections={
                            "overview": f"{category.title()} {operation} overview",
                            "procedures": f"Detailed {operation} procedures",
                            "troubleshooting": f"{category.title()} troubleshooting guide"
                        }
                    )
                    
                    vector_store.add_runbook(runbook)
                    runbook_count += 1
        
        # Wait for indexing
        time.sleep(3.0)
        
        print(f"Populated vector store with {runbook_count} runbooks for search performance testing")
        return vector_store
    
    @pytest.mark.performance
    def test_search_response_times(self, populated_vector_store):
        """Test search response times with various query types."""
        test_queries = [
            # Simple keyword searches
            ("database", "simple_keyword"),
            ("backup", "simple_keyword"),
            ("network", "simple_keyword"),
            
            # Multi-word searches
            ("database backup", "multi_word"),
            ("network troubleshoot", "multi_word"),
            ("security configure", "multi_word"),
            
            # Complex queries
            ("database backup troubleshooting steps", "complex"),
            ("network configuration best practices", "complex"),
            ("security monitoring deployment procedures", "complex"),
            
            # Specific technical terms
            ("troubleshooting connectivity", "technical"),
            ("system logs errors", "technical"),
            ("restart services", "technical")
        ]
        
        results_by_category = {}
        
        for query, category in test_queries:
            if category not in results_by_category:
                results_by_category[category] = []
            
            # Test different result limits
            for n_results in [5, 10, 15]:
                start_time = time.time()
                results = populated_vector_store.search_runbooks(query, n_results=n_results)
                end_time = time.time()
                
                search_time = end_time - start_time
                results_by_category[category].append(search_time)
                
                # Performance assertions
                assert search_time < 2.0, f"Search '{query}' (n={n_results}) too slow: {search_time:.3f}s"
                assert isinstance(results, list)
                assert len(results) <= n_results
                
                # Verify result quality
                if results:
                    for result in results:
                        assert hasattr(result, 'relevance_score')
                        assert 0.0 <= result.relevance_score <= 1.0
        
        # Analyze performance by category
        for category, times in results_by_category.items():
            avg_time = statistics.mean(times)
            max_time = max(times)
            min_time = min(times)
            
            print(f"{category} searches: avg={avg_time:.3f}s, max={max_time:.3f}s, min={min_time:.3f}s")
            
            # Category-specific performance requirements
            if category == "simple_keyword":
                assert avg_time < 0.5, f"Simple keyword searches too slow: {avg_time:.3f}s"
            elif category == "complex":
                assert avg_time < 1.0, f"Complex searches too slow: {avg_time:.3f}s"
    
    @pytest.mark.performance
    def test_concurrent_search_performance(self, populated_vector_store):
        """Test concurrent search performance."""
        search_queries = [
            "database backup procedures",
            "network troubleshooting guide",
            "security configuration steps",
            "monitoring system setup",
            "deployment best practices"
        ]
        
        def search_task(query):
            """Task function for concurrent search execution."""
            start_time = time.time()
            results = populated_vector_store.search_runbooks(query, n_results=10)
            end_time = time.time()
            return query, end_time - start_time, len(results)
        
        # Test concurrent searches
        max_workers = 5
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_query = {
                executor.submit(search_task, query): query
                for query in search_queries
            }
            
            search_results = []
            for future in as_completed(future_to_query):
                query, search_time, result_count = future.result()
                search_results.append((query, search_time, result_count))
        
        total_time = time.time() - start_time
        
        # Performance analysis
        search_times = [result[1] for result in search_results]
        avg_search_time = statistics.mean(search_times)
        max_search_time = max(search_times)
        
        # Concurrent performance assertions
        assert avg_search_time < 1.0, f"Concurrent average search time too slow: {avg_search_time:.3f}s"
        assert max_search_time < 2.0, f"Concurrent max search time too slow: {max_search_time:.3f}s"
        assert total_time < 5.0, f"Total concurrent search time too slow: {total_time:.2f}s"
        
        print(f"Concurrent search: {len(search_queries)} queries in {total_time:.2f}s "
              f"(avg: {avg_search_time:.3f}s, max: {max_search_time:.3f}s)")
        
        # Verify all searches returned results
        total_results = sum(result[2] for result in search_results)
        assert total_results > 0, "No results returned from concurrent searches"
    
    @pytest.mark.performance
    def test_search_with_filters_performance(self, populated_vector_store):
        """Test search performance with metadata filters."""
        filter_test_cases = [
            # Single filter
            ({"space_key": "DATA"}, "single_filter"),
            ({"author": "Database Team"}, "single_filter"),
            
            # Multiple filters
            ({"space_key": "NETW", "author": "Network Team"}, "multiple_filters"),
            ({"space_key": "SECU", "tags": "security"}, "multiple_filters"),
            
            # Complex filters
            ({"space_key": "MONI", "author": "Monitoring Team", "tags": "performance_test"}, "complex_filters")
        ]
        
        base_query = "troubleshooting procedures"
        
        for filters, filter_type in filter_test_cases:
            start_time = time.time()
            results = populated_vector_store.search_runbooks(
                base_query,
                n_results=10,
                filters=filters
            )
            end_time = time.time()
            
            search_time = end_time - start_time
            
            # Performance assertions for filtered searches
            assert search_time < 2.5, f"Filtered search too slow: {search_time:.3f}s ({filter_type})"
            assert isinstance(results, list)
            
            # Verify filter effectiveness
            if results:
                for result in results:
                    metadata = result.metadata
                    for filter_key, filter_value in filters.items():
                        if filter_key == "tags":
                            assert filter_value in metadata.tags, f"Filter {filter_key}={filter_value} not applied"
                        else:
                            assert getattr(metadata, filter_key) == filter_value, f"Filter {filter_key}={filter_value} not applied"
            
            print(f"Filtered search ({filter_type}): {search_time:.3f}s, {len(results)} results")


class TestScalabilityPerformance:
    """Performance tests for system scalability."""
    
    @pytest.fixture(scope="class")
    def temp_db_dir(self):
        """Create temporary directory for scalability test database."""
        temp_dir = tempfile.mkdtemp(prefix="confluence_scale_perf_")
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture(scope="class")
    def vector_store(self, temp_db_dir):
        """Create VectorStore instance for scalability testing."""
        return VectorStore(
            collection_name="scale_perf_runbooks",
            persist_directory=temp_db_dir
        )
    
    @pytest.mark.performance
    @pytest.mark.slow
    def test_large_dataset_performance(self, vector_store):
        """Test performance with large dataset."""
        # Create large dataset
        num_runbooks = 100
        batch_size = 10
        
        total_addition_time = 0
        runbook_ids = []
        
        for batch_start in range(0, num_runbooks, batch_size):
            batch_runbooks = []
            for i in range(batch_start, min(batch_start + batch_size, num_runbooks)):
                metadata = RunbookMetadata(
                    title=f"Large Dataset Runbook {i}",
                    author=f"Author {i % 10}",
                    last_modified=datetime.utcnow(),
                    space_key=f"SCALE{i % 5}",
                    page_id=f"large_dataset_{i}",
                    page_url=f"https://example.com/large_dataset_{i}",
                    tags=[f"large", f"dataset", f"batch_{batch_start // batch_size}", f"item_{i}"]
                )
                
                # Vary content size
                content_multiplier = (i % 5) + 1
                base_content = f"Large dataset runbook {i} content. " * (20 * content_multiplier)
                
                runbook = RunbookContent(
                    metadata=metadata,
                    procedures=[f"Large dataset procedure {j} for runbook {i}" for j in range(1, 6)],
                    troubleshooting_steps=[f"Large dataset troubleshooting {j} for runbook {i}" for j in range(1, 4)],
                    prerequisites=[f"Large dataset requirement {j} for runbook {i}" for j in range(1, 3)],
                    raw_content=base_content,
                    structured_sections={
                        "overview": f"Large dataset runbook {i} overview",
                        "details": f"Detailed information for runbook {i}"
                    }
                )
                batch_runbooks.append(runbook)
            
            # Add batch and measure time
            batch_start_time = time.time()
            for runbook in batch_runbooks:
                runbook_id = vector_store.add_runbook(runbook)
                runbook_ids.append(runbook_id)
            batch_end_time = time.time()
            
            batch_time = batch_end_time - batch_start_time
            total_addition_time += batch_time
            
            print(f"Added batch {batch_start // batch_size + 1}/{(num_runbooks + batch_size - 1) // batch_size}: "
                  f"{len(batch_runbooks)} runbooks in {batch_time:.2f}s")
        
        # Performance assertions for large dataset
        avg_time_per_runbook = total_addition_time / num_runbooks
        assert avg_time_per_runbook < 3.0, f"Large dataset addition too slow: {avg_time_per_runbook:.3f}s per runbook"
        
        print(f"Large dataset addition: {num_runbooks} runbooks in {total_addition_time:.2f}s "
              f"({avg_time_per_runbook:.3f}s per runbook)")
        
        # Test search performance with large dataset
        time.sleep(5.0)  # Allow for indexing
        
        search_queries = [
            "large dataset runbook",
            "troubleshooting procedures",
            "detailed information",
            "batch content"
        ]
        
        search_times = []
        for query in search_queries:
            start_time = time.time()
            results = vector_store.search_runbooks(query, n_results=20)
            end_time = time.time()
            
            search_time = end_time - start_time
            search_times.append(search_time)
            
            assert search_time < 3.0, f"Large dataset search too slow: {search_time:.3f}s"
            assert len(results) > 0, f"No results for query: {query}"
        
        avg_search_time = statistics.mean(search_times)
        print(f"Large dataset search: avg {avg_search_time:.3f}s per query")
        
        return runbook_ids
    
    @pytest.mark.performance
    def test_memory_usage_scalability(self, vector_store):
        """Test memory usage with increasing dataset size."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Add runbooks in increments and monitor memory
        increment_size = 10
        max_runbooks = 50
        memory_measurements = []
        
        for i in range(0, max_runbooks, increment_size):
            # Add increment of runbooks
            for j in range(increment_size):
                runbook_index = i + j
                metadata = RunbookMetadata(
                    title=f"Memory Test Runbook {runbook_index}",
                    author="Memory Tester",
                    last_modified=datetime.utcnow(),
                    space_key="MEM",
                    page_id=f"memory_test_{runbook_index}",
                    page_url=f"https://example.com/memory_test_{runbook_index}",
                    tags=["memory", "test", f"increment_{i // increment_size}"]
                )
                
                runbook = RunbookContent(
                    metadata=metadata,
                    procedures=[f"Memory test procedure {k}" for k in range(1, 4)],
                    troubleshooting_steps=[f"Memory test troubleshooting {k}" for k in range(1, 3)],
                    prerequisites=["Memory test access"],
                    raw_content=f"Memory test content for runbook {runbook_index} " * 100,
                    structured_sections={"memory": f"Memory test {runbook_index}"}
                )
                
                vector_store.add_runbook(runbook)
            
            # Measure memory usage
            current_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = current_memory - initial_memory
            memory_measurements.append((i + increment_size, memory_increase))
            
            print(f"After {i + increment_size} runbooks: {memory_increase:.1f} MB increase")
        
        # Analyze memory growth
        if len(memory_measurements) > 1:
            memory_per_runbook = memory_measurements[-1][1] / memory_measurements[-1][0]
            
            # Memory usage should be reasonable
            assert memory_per_runbook < 5.0, f"Memory usage too high: {memory_per_runbook:.2f} MB per runbook"
            
            print(f"Memory usage: {memory_per_runbook:.2f} MB per runbook")


if __name__ == "__main__":
    # Run performance tests
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-m", "performance"
    ])