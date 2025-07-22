"""
Mock Vector Storage Strategy Implementation.

This module provides a mock implementation of VectorStorageStrategy using
in-memory storage and simulated embeddings for development and testing.
"""

import asyncio
import logging
import time
import math
import random
from typing import List, Dict, Any, Optional
from datetime import datetime

from .protocols import AbstractVectorStrategy
from ..exceptions import MCPRunbookError, VectorSearchError

logger = logging.getLogger(__name__)


class MockVectorStrategy(AbstractVectorStrategy):
    """
    Mock vector storage strategy implementation.
    
    Uses in-memory storage with simulated vector embeddings for development
    and testing. Implements VectorStorageStrategy protocol through structural
    subtyping.
    """
    
    def __init__(self, vector_dimension: int = 384):
        """
        Initialize mock vector strategy.
        
        Args:
            vector_dimension: Dimension of mock embeddings (matches all-MiniLM-L6-v2)
        """
        self.vector_dimension = vector_dimension
        
        # In-memory storage
        self._stored_embeddings: Dict[str, Dict[str, Any]] = {}
        self._embedding_cache: Dict[str, List[float]] = {}
        
        # Mock collection stats
        self._collection_stats = {
            "total_runbooks": 0,
            "total_chunks": 0,
            "collections_count": 1,
            "vector_dimensions": vector_dimension,
            "embedding_model": "mock-all-MiniLM-L6-v2",
            "database_status": "healthy",
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Load some initial test embeddings
        self._initialize_test_embeddings()
        
        logger.info(f"MockVectorStrategy initialized with {vector_dimension}D embeddings")
    
    def _initialize_test_embeddings(self) -> None:
        """Initialize with some test embeddings from mock data."""
        try:
            # Import test data
            import sys
            import os
            sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "tests", "data"))
            
            from test_data_loader import load_test_runbooks
            
            test_runbooks = load_test_runbooks()
            
            # Create mock embeddings for each test runbook
            for runbook in test_runbooks:
                metadata = runbook.get("metadata", {})
                runbook_id = metadata.get("page_id", f"mock_{hash(str(runbook))}")
                content = runbook.get("raw_content", metadata.get("title", ""))
                
                # Store mock embedding
                embedding_data = {
                    "runbook_id": runbook_id,
                    "content": content,
                    "metadata": metadata,
                    "embedding": self._generate_mock_embedding(content),
                    "chunks": self._create_mock_chunks(content),
                    "stored_at": datetime.utcnow().isoformat(),
                    "source": "mock_initialization"
                }
                
                self._stored_embeddings[runbook_id] = embedding_data
                
            self._update_collection_stats()
            
            logger.info(f"Initialized {len(self._stored_embeddings)} mock embeddings")
            
        except Exception as e:
            logger.warning(f"Could not load test embeddings, using minimal data: {e}")
            
            # Fallback: create minimal mock embeddings
            mock_runbooks = [
                ("mock_db_001", "Database Connection Troubleshooting", "database connection timeout issues"),
                ("mock_perf_001", "Performance Optimization", "slow query performance optimization"),
                ("mock_backup_001", "Backup Recovery", "backup and disaster recovery procedures")
            ]
            
            for runbook_id, title, content in mock_runbooks:
                embedding_data = {
                    "runbook_id": runbook_id,
                    "content": content,
                    "metadata": {
                        "title": title,
                        "page_id": runbook_id,
                        "tags": content.split()[:3]
                    },
                    "embedding": self._generate_mock_embedding(content),
                    "chunks": self._create_mock_chunks(content),
                    "stored_at": datetime.utcnow().isoformat(),
                    "source": "mock_fallback"
                }
                
                self._stored_embeddings[runbook_id] = embedding_data
            
            self._update_collection_stats()
    
    def _generate_mock_embedding(self, text: str) -> List[float]:
        """
        Generate mock embedding vector based on text content.
        
        Args:
            text: Text content to embed
            
        Returns:
            Mock embedding vector
        """
        # Use text hash to generate consistent embeddings
        text_hash = hash(text)
        random.seed(text_hash)
        
        # Generate mock embedding with some semantic structure
        embedding = []
        text_lower = text.lower()
        
        # Base random vector
        for i in range(self.vector_dimension):
            embedding.append(random.uniform(-1.0, 1.0))
        
        # Add semantic hints based on keywords
        keyword_boosts = {
            "database": [0.8, 0.6, 0.4, 0.2],
            "connection": [0.7, 0.5, 0.3],
            "performance": [0.9, 0.7, 0.5],
            "troubleshooting": [0.6, 0.8, 0.4],
            "backup": [0.5, 0.7, 0.9, 0.3],
            "security": [0.8, 0.4, 0.6, 0.7]
        }
        
        for keyword, boosts in keyword_boosts.items():
            if keyword in text_lower:
                for i, boost in enumerate(boosts):
                    if i < len(embedding):
                        embedding[i] += boost
        
        # Normalize vector
        magnitude = math.sqrt(sum(x * x for x in embedding))
        if magnitude > 0:
            embedding = [x / magnitude for x in embedding]
        
        return embedding
    
    def _create_mock_chunks(self, content: str) -> List[Dict[str, Any]]:
        """
        Create mock chunks from content.
        
        Args:
            content: Text content to chunk
            
        Returns:
            List of mock chunk dictionaries
        """
        # Simple chunking by sentences or paragraphs
        sentences = content.split('. ')
        chunks = []
        
        chunk_size = 100  # characters
        current_chunk = ""
        chunk_id = 0
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) > chunk_size and current_chunk:
                chunks.append({
                    "chunk_id": f"chunk_{chunk_id}",
                    "content": current_chunk.strip(),
                    "embedding": self._generate_mock_embedding(current_chunk),
                    "start_pos": chunk_id * chunk_size,
                    "end_pos": chunk_id * chunk_size + len(current_chunk)
                })
                current_chunk = sentence
                chunk_id += 1
            else:
                current_chunk += sentence + ". "
        
        # Add final chunk
        if current_chunk.strip():
            chunks.append({
                "chunk_id": f"chunk_{chunk_id}",
                "content": current_chunk.strip(),
                "embedding": self._generate_mock_embedding(current_chunk),
                "start_pos": chunk_id * chunk_size,
                "end_pos": chunk_id * chunk_size + len(current_chunk)
            })
        
        return chunks
    
    def _calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Calculate cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Similarity score between 0 and 1
        """
        if len(embedding1) != len(embedding2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
        magnitude1 = math.sqrt(sum(a * a for a in embedding1))
        magnitude2 = math.sqrt(sum(b * b for b in embedding2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        similarity = dot_product / (magnitude1 * magnitude2)
        # Convert from [-1, 1] to [0, 1]
        return (similarity + 1) / 2
    
    def _update_collection_stats(self) -> None:
        """Update collection statistics."""
        total_chunks = sum(len(data.get("chunks", [])) for data in self._stored_embeddings.values())
        
        self._collection_stats.update({
            "total_runbooks": len(self._stored_embeddings),
            "total_chunks": total_chunks,
            "last_updated": datetime.utcnow().isoformat()
        })
    
    async def health_check(self) -> bool:
        """
        Mock health check - always returns True.
        
        Returns:
            True (mock implementation is always healthy)
        """
        return True
    
    # VectorStorageStrategy Protocol Implementation
    async def store_runbook_embedding(self, runbook_id: str, content: str, 
                                    metadata: Dict[str, Any]) -> bool:
        """
        Store mock runbook with vector embedding.
        
        Args:
            runbook_id: Unique identifier for the runbook
            content: Text content to embed
            metadata: Associated metadata
            
        Returns:
            True if storage successful
        """
        try:
            # Simulate some processing time
            await asyncio.sleep(0.02)
            
            # Generate mock embedding
            embedding = self._generate_mock_embedding(content)
            chunks = self._create_mock_chunks(content)
            
            # Store embedding data
            embedding_data = {
                "runbook_id": runbook_id,
                "content": content,
                "metadata": metadata,
                "embedding": embedding,
                "chunks": chunks,
                "stored_at": datetime.utcnow().isoformat(),
                "source": "mock_storage"
            }
            
            self._stored_embeddings[runbook_id] = embedding_data
            self._update_collection_stats()
            
            logger.info(f"Mock stored runbook embedding: {runbook_id}")
            return True
            
        except Exception as e:
            logger.error(f"Mock failed to store runbook embedding {runbook_id}: {e}")
            raise MCPRunbookError(f"Failed to store runbook embedding: {e}")
    
    async def search_similar_runbooks(self, query: str, limit: int = 5, 
                                    min_score: float = 0.0) -> List[Dict[str, Any]]:
        """
        Perform mock semantic search for similar runbooks.
        
        Args:
            query: Search query for similarity matching
            limit: Maximum number of results to return
            min_score: Minimum similarity score threshold
            
        Returns:
            List of similar runbooks with similarity scores
        """
        start_time = time.time()
        
        try:
            # Simulate some processing time
            await asyncio.sleep(0.01)
            
            # Generate query embedding
            query_embedding = self._generate_mock_embedding(query)
            
            # Calculate similarities
            similarities = []
            for runbook_id, embedding_data in self._stored_embeddings.items():
                runbook_embedding = embedding_data.get("embedding", [])
                
                if runbook_embedding:
                    similarity_score = self._calculate_similarity(query_embedding, runbook_embedding)
                    
                    if similarity_score >= min_score:
                        result = {
                            "runbook_id": runbook_id,
                            "title": embedding_data.get("metadata", {}).get("title", "Unknown"),
                            "content_preview": embedding_data.get("content", "")[:200] + "..." if embedding_data.get("content") else "",
                            "similarity_score": similarity_score,
                            "metadata": embedding_data.get("metadata", {}),
                            "source": "mock_chromadb",
                            "search_query": query,
                            "chunk_id": "",
                            "distance": 1.0 - similarity_score,  # Convert similarity to distance
                            "matched_at": datetime.utcnow().isoformat()
                        }
                        similarities.append(result)
            
            # Sort by similarity score (descending)
            similarities.sort(key=lambda x: x["similarity_score"], reverse=True)
            
            # Apply limit
            results = similarities[:limit]
            
            # Check performance requirement
            total_time = time.time() - start_time
            if total_time > 0.05:  # 50ms
                logger.warning(f"Mock vector search exceeded 50ms target: {total_time:.3f}s")
            
            logger.info(f"Mock vector search completed in {total_time:.3f}s, found {len(results)} results")
            return results
            
        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"Mock vector search failed after {total_time:.3f}s: {e}")
            raise VectorSearchError(query, str(e))
    
    async def update_runbook_embedding(self, runbook_id: str, content: str, 
                                     metadata: Dict[str, Any]) -> bool:
        """
        Update existing mock runbook embedding.
        
        Args:
            runbook_id: Unique identifier for the runbook
            content: Updated text content
            metadata: Updated metadata
            
        Returns:
            True if update successful
        """
        try:
            # Simulate some processing time
            await asyncio.sleep(0.02)
            
            if runbook_id in self._stored_embeddings:
                # Update existing embedding
                existing_data = self._stored_embeddings[runbook_id]
                
                # Generate new embedding
                new_embedding = self._generate_mock_embedding(content)
                new_chunks = self._create_mock_chunks(content)
                
                # Update data
                existing_data.update({
                    "content": content,
                    "metadata": metadata,
                    "embedding": new_embedding,
                    "chunks": new_chunks,
                    "updated_at": datetime.utcnow().isoformat(),
                    "source": "mock_update"
                })
                
                self._update_collection_stats()
                
                logger.info(f"Mock updated runbook embedding: {runbook_id}")
                return True
            else:
                # Store as new if not found
                logger.warning(f"Mock runbook not found for update, storing as new: {runbook_id}")
                return await self.store_runbook_embedding(runbook_id, content, metadata)
                
        except Exception as e:
            logger.error(f"Mock failed to update runbook embedding {runbook_id}: {e}")
            raise MCPRunbookError(f"Failed to update runbook embedding: {e}")
    
    async def delete_runbook_embedding(self, runbook_id: str) -> bool:
        """
        Delete mock runbook from vector store.
        
        Args:
            runbook_id: Unique identifier for the runbook
            
        Returns:
            True if deletion successful
        """
        try:
            # Simulate some processing time
            await asyncio.sleep(0.01)
            
            if runbook_id in self._stored_embeddings:
                del self._stored_embeddings[runbook_id]
                self._update_collection_stats()
                
                logger.info(f"Mock deleted runbook embedding: {runbook_id}")
                return True
            else:
                logger.warning(f"Mock runbook not found for deletion: {runbook_id}")
                return True  # Consider not found as successful deletion
                
        except Exception as e:
            logger.error(f"Mock failed to delete runbook embedding {runbook_id}: {e}")
            raise MCPRunbookError(f"Failed to delete runbook embedding: {e}")
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get mock collection statistics and health metrics.
        
        Returns:
            Mock statistics dictionary with collection info
        """
        try:
            # Update stats before returning
            self._update_collection_stats()
            
            stats = self._collection_stats.copy()
            stats["retrieved_at"] = datetime.utcnow().isoformat()
            
            return stats
            
        except Exception as e:
            logger.error(f"Mock failed to get collection stats: {e}")
            raise MCPRunbookError(f"Failed to get collection statistics: {e}")
    
    async def list_stored_runbooks(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        List all stored mock runbooks with pagination.
        
        Args:
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of stored mock runbook metadata
        """
        try:
            # Simulate some processing time
            await asyncio.sleep(0.01)
            
            all_runbooks = []
            for runbook_id, embedding_data in self._stored_embeddings.items():
                metadata = embedding_data.get("metadata", {})
                
                runbook_info = {
                    "runbook_id": runbook_id,
                    "title": metadata.get("title", "Unknown"),
                    "metadata": metadata,
                    "created_at": embedding_data.get("stored_at", ""),
                    "updated_at": embedding_data.get("updated_at", embedding_data.get("stored_at", "")),
                    "chunk_count": len(embedding_data.get("chunks", [])),
                    "content_length": len(embedding_data.get("content", "")),
                    "source": embedding_data.get("source", "mock")
                }
                all_runbooks.append(runbook_info)
            
            # Sort by created_at (newest first)
            all_runbooks.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            
            # Apply pagination
            paginated_runbooks = all_runbooks[offset:offset + limit]
            
            logger.info(f"Mock listed {len(paginated_runbooks)} runbooks (offset: {offset}, limit: {limit})")
            return paginated_runbooks
            
        except Exception as e:
            logger.error(f"Mock failed to list stored runbooks: {e}")
            raise MCPRunbookError(f"Failed to list stored runbooks: {e}")
    
    # Additional Mock-specific Methods
    def get_all_embeddings(self) -> Dict[str, Dict[str, Any]]:
        """Get all stored embeddings for testing and debugging."""
        return self._stored_embeddings.copy()
    
    def clear_all_embeddings(self) -> None:
        """Clear all embeddings and reinitialize."""
        self._stored_embeddings.clear()
        self._initialize_test_embeddings()
        logger.info("Mock vector storage cleared and reinitialized")
    
    def add_mock_embedding(self, runbook_id: str, content: str, metadata: Dict[str, Any]) -> None:
        """Add a mock embedding directly for testing."""
        embedding_data = {
            "runbook_id": runbook_id,
            "content": content,
            "metadata": metadata,
            "embedding": self._generate_mock_embedding(content),
            "chunks": self._create_mock_chunks(content),
            "stored_at": datetime.utcnow().isoformat(),
            "source": "mock_manual"
        }
        
        self._stored_embeddings[runbook_id] = embedding_data
        self._update_collection_stats()
        
        logger.info(f"Manually added mock embedding: {runbook_id}")
    
    def get_embedding_by_id(self, runbook_id: str) -> Optional[Dict[str, Any]]:
        """Get specific embedding data by ID for testing."""
        return self._stored_embeddings.get(runbook_id)
    
    def simulate_performance_degradation(self, delay_seconds: float = 0.1) -> None:
        """Simulate performance issues for testing."""
        logger.warning(f"Simulating {delay_seconds}s performance degradation")
        # This would be used in tests to simulate slow responses
        # The delay would be added to async operations