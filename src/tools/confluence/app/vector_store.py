"""
Vector database operations for the Confluence Integration Tool.

This module provides the VectorStore class for managing runbook content
in ChromaDB with semantic search capabilities using sentence transformers.
"""

import os
import uuid
import logging
from typing import List, Optional, Dict, Any
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import numpy as np

from .models import RunbookContent, RunbookChunk, SearchResult


logger = logging.getLogger(__name__)


class VectorStore:
    """
    Vector database manager for runbook content storage and retrieval.

    Uses ChromaDB for vector storage and sentence-transformers for embedding generation.
    Provides methods for storing, searching, and managing runbook content chunks.
    """

    def __init__(
        self, collection_name: str = "runbooks", persist_directory: str = None
    ):
        """
        Initialize the VectorStore with ChromaDB client and embedding model.

        Args:
            collection_name: Name of the ChromaDB collection
            persist_directory: Directory for persistent storage (optional)
        """
        self.collection_name = collection_name
        self.persist_directory = persist_directory or os.getenv(
            "CHROMA_PERSIST_DIRECTORY", "/tmp/chroma_db"
        )

        # Initialize ChromaDB client
        self._client = None
        self._collection = None

        # Initialize embedding model
        self._embedding_model = None
        self._embedding_dimension = None

        # Initialize components
        self._initialize_client()
        self._initialize_embedding_model()
        self._initialize_collection()

    def _initialize_client(self) -> None:
        """Initialize ChromaDB client with persistent storage."""
        try:
            settings = Settings(
                persist_directory=self.persist_directory, anonymized_telemetry=False
            )
            self._client = chromadb.PersistentClient(settings=settings)
            logger.info(
                f"ChromaDB client initialized with persist directory: {self.persist_directory}"
            )
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB client: {e}")
            raise

    def _initialize_embedding_model(self) -> None:
        """Initialize sentence transformer model for embeddings."""
        try:
            model_name = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
            self._embedding_model = SentenceTransformer(model_name)

            # Get embedding dimension
            test_embedding = self._embedding_model.encode(["test"])
            self._embedding_dimension = len(test_embedding[0])

            logger.info(
                f"Embedding model '{model_name}' initialized with dimension {self._embedding_dimension}"
            )
        except Exception as e:
            logger.error(f"Failed to initialize embedding model: {e}")
            raise

    def _initialize_collection(self) -> None:
        """Initialize or get existing ChromaDB collection."""
        try:
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "Confluence runbook content chunks"},
            )
            logger.info(f"Collection '{self.collection_name}' initialized")
        except Exception as e:
            logger.error(f"Failed to initialize collection: {e}")
            raise

    def _generate_embeddings(self, text: str) -> List[float]:
        """
        Generate embeddings for the given text using sentence transformers.

        Args:
            text: Text to generate embeddings for

        Returns:
            List of float values representing the embedding vector

        Raises:
            ValueError: If text is empty
            RuntimeError: If embedding generation fails
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty for embedding generation")

        try:
            # Generate embedding
            embedding = self._embedding_model.encode([text.strip()])

            # Convert to list and ensure proper format
            if hasattr(embedding[0], "tolist"):
                embedding_list = embedding[0].tolist()
            else:
                embedding_list = list(embedding[0])

            # Validate embedding
            if not embedding_list or len(embedding_list) != self._embedding_dimension:
                raise RuntimeError(
                    f"Invalid embedding dimension: {len(embedding_list)}"
                )

            return embedding_list

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise RuntimeError(f"Embedding generation failed: {e}")

    def _chunk_content(
        self, content: str, chunk_size: int = 1000, overlap: int = 100
    ) -> List[str]:
        """
        Split content into overlapping chunks for optimal vector storage.

        Args:
            content: Text content to chunk
            chunk_size: Maximum size of each chunk in characters
            overlap: Number of characters to overlap between chunks

        Returns:
            List of content chunks

        Raises:
            ValueError: If parameters are invalid
        """
        if not content or not content.strip():
            raise ValueError("Content cannot be empty for chunking")

        if chunk_size <= 0:
            raise ValueError("Chunk size must be positive")

        if overlap < 0 or overlap >= chunk_size:
            raise ValueError("Overlap must be non-negative and less than chunk size")

        content = content.strip()

        # If content is smaller than chunk size, return as single chunk
        if len(content) <= chunk_size:
            return [content]

        chunks = []
        start = 0

        while start < len(content):
            # Calculate end position
            end = start + chunk_size

            # If this is not the last chunk, try to break at word boundary
            if end < len(content):
                # Look for the last space within the chunk to avoid breaking words
                last_space = content.rfind(" ", start, end)
                if last_space > start:
                    end = last_space

            # Extract chunk
            chunk = content[start:end].strip()
            if chunk:  # Only add non-empty chunks
                chunks.append(chunk)

            # Move start position with overlap
            start = end - overlap

            # Ensure we don't go backwards
            if start <= (len(chunks[-1]) if chunks else 0):
                start = end

        return chunks

    def add_runbook(self, runbook_data: RunbookContent) -> str:
        """
        Add runbook content to the vector database with embeddings.

        Args:
            runbook_data: RunbookContent object containing the runbook information

        Returns:
            Unique runbook identifier

        Raises:
            ValueError: If runbook data is invalid
            RuntimeError: If storage operation fails
        """
        if not runbook_data:
            raise ValueError("Runbook data cannot be None")

        try:
            # Generate unique runbook ID
            runbook_id = str(uuid.uuid4())

            # Prepare content for chunking
            all_content = []

            # Add different types of content with section labels
            if runbook_data.procedures:
                for i, procedure in enumerate(runbook_data.procedures):
                    all_content.append(f"PROCEDURE {i+1}: {procedure}")

            if runbook_data.troubleshooting_steps:
                for i, step in enumerate(runbook_data.troubleshooting_steps):
                    all_content.append(f"TROUBLESHOOTING {i+1}: {step}")

            if runbook_data.prerequisites:
                for i, prereq in enumerate(runbook_data.prerequisites):
                    all_content.append(f"PREREQUISITE {i+1}: {prereq}")

            # Add structured sections
            for (
                section_name,
                section_content,
            ) in runbook_data.structured_sections.items():
                all_content.append(f"{section_name.upper()}: {section_content}")

            # Add raw content if no structured content available
            if not all_content and runbook_data.raw_content:
                all_content.append(runbook_data.raw_content)

            if not all_content:
                raise ValueError("No content available for chunking")

            # Combine all content
            combined_content = "\n\n".join(all_content)

            # Generate chunks
            chunks = self._chunk_content(combined_content)

            # Process each chunk
            chunk_ids = []
            embeddings = []
            documents = []
            metadatas = []

            for i, chunk_content in enumerate(chunks):
                # Generate chunk ID
                chunk_id = f"{runbook_id}_chunk_{i}"
                chunk_ids.append(chunk_id)

                # Generate embedding
                embedding = self._generate_embeddings(chunk_content)
                embeddings.append(embedding)

                # Store document content
                documents.append(chunk_content)

                # Prepare metadata
                metadata = {
                    "runbook_id": runbook_id,
                    "chunk_index": i,
                    "title": runbook_data.metadata.title,
                    "author": runbook_data.metadata.author or "",
                    "space_key": runbook_data.metadata.space_key,
                    "page_id": runbook_data.metadata.page_id,
                    "page_url": str(runbook_data.metadata.page_url),
                    "last_modified": runbook_data.metadata.last_modified.isoformat(),
                    "tags": (
                        ",".join(runbook_data.metadata.tags)
                        if runbook_data.metadata.tags
                        else ""
                    ),
                }
                metadatas.append(metadata)

            # Add to ChromaDB collection
            self._collection.add(
                ids=chunk_ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
            )

            logger.info(f"Added runbook {runbook_id} with {len(chunks)} chunks")
            return runbook_id

        except Exception as e:
            logger.error(f"Failed to add runbook: {e}")
            raise RuntimeError(f"Failed to store runbook: {e}")

    def search_runbooks(
        self, query: str, n_results: int = 5, filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """
        Search runbooks using semantic similarity with optional metadata filters.

        Args:
            query: Search query text
            n_results: Maximum number of results to return
            filters: Optional metadata filters (e.g., {"space_key": "PROD", "author": "admin"})

        Returns:
            List of SearchResult objects ordered by relevance

        Raises:
            ValueError: If query is invalid
            RuntimeError: If search operation fails
        """
        if not query or not query.strip():
            raise ValueError("Search query cannot be empty")

        if n_results <= 0 or n_results > 20:
            raise ValueError("Number of results must be between 1 and 20")

        try:
            # Generate query embedding
            query_embedding = self._generate_embeddings(query.strip())

            # Prepare search parameters
            search_params = {
                "query_embeddings": [query_embedding],
                "n_results": min(n_results, self._collection.count()),
                "include": ["documents", "metadatas", "distances"],
            }

            # Add filters if provided
            if filters:
                # Validate and clean filters
                valid_filters = {}
                for key, value in filters.items():
                    if key in ["space_key", "author", "title", "page_id"] and value:
                        valid_filters[key] = str(value).strip()

                if valid_filters:
                    search_params["where"] = valid_filters

            # Perform similarity search
            results = self._collection.query(**search_params)

            # Process results
            search_results = []

            if results["ids"] and results["ids"][0]:
                for i in range(len(results["ids"][0])):
                    chunk_id = results["ids"][0][i]
                    document = results["documents"][0][i]
                    metadata = results["metadatas"][0][i]
                    distance = results["distances"][0][i]

                    # Convert distance to similarity score (0-1, higher is better)
                    relevance_score = max(0.0, 1.0 - distance)

                    # Create SearchResult
                    search_result = SearchResult(
                        runbook_id=metadata["runbook_id"],
                        chunk_id=chunk_id,
                        content=document,
                        relevance_score=relevance_score,
                        metadata=self._metadata_dict_to_runbook_metadata(metadata),
                    )

                    search_results.append(search_result)

            filter_info = f" with filters {filters}" if filters else ""
            logger.info(
                f"Search for '{query}'{filter_info} returned {len(search_results)} results"
            )
            return search_results

        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise RuntimeError(f"Search operation failed: {e}")

    def get_runbook_by_id(self, runbook_id: str) -> Optional[RunbookContent]:
        """
        Retrieve a complete runbook by its ID.

        Args:
            runbook_id: Unique runbook identifier

        Returns:
            RunbookContent object if found, None otherwise

        Raises:
            ValueError: If runbook_id is invalid
            RuntimeError: If retrieval operation fails
        """
        if not runbook_id or not runbook_id.strip():
            raise ValueError("Runbook ID cannot be empty")

        try:
            # Query all chunks for this runbook
            results = self._collection.get(
                where={"runbook_id": runbook_id.strip()},
                include=["documents", "metadatas"],
            )

            if not results["ids"]:
                return None

            # Reconstruct runbook from chunks
            chunks = []
            metadata = None

            for i in range(len(results["ids"])):
                chunk_metadata = results["metadatas"][i]
                document = results["documents"][i]

                # Use first chunk's metadata for runbook metadata
                if metadata is None:
                    metadata = self._metadata_dict_to_runbook_metadata(chunk_metadata)

                chunks.append(document)

            # Combine chunks back into content
            combined_content = "\n\n".join(chunks)

            # Create RunbookContent (simplified reconstruction)
            runbook_content = RunbookContent(
                metadata=metadata,
                raw_content=combined_content,
                procedures=[],  # Would need more sophisticated parsing to reconstruct
                troubleshooting_steps=[],
                prerequisites=[],
                structured_sections={},
            )

            return runbook_content

        except Exception as e:
            logger.error(f"Failed to retrieve runbook {runbook_id}: {e}")
            raise RuntimeError(f"Failed to retrieve runbook: {e}")

    def update_runbook(self, runbook_id: str, runbook_data: RunbookContent) -> None:
        """
        Update an existing runbook with new content and regenerate embeddings.

        Args:
            runbook_id: Unique runbook identifier
            runbook_data: Updated RunbookContent object

        Raises:
            ValueError: If parameters are invalid
            RuntimeError: If update operation fails
        """
        if not runbook_id or not runbook_id.strip():
            raise ValueError("Runbook ID cannot be empty")

        if not runbook_data:
            raise ValueError("Runbook data cannot be None")

        try:
            runbook_id = runbook_id.strip()
            
            # Check if runbook exists
            existing_runbook = self.get_runbook_by_id(runbook_id)
            if existing_runbook is None:
                raise ValueError(f"Runbook with ID '{runbook_id}' not found")

            # Delete existing chunks
            results = self._collection.get(
                where={"runbook_id": runbook_id}, include=["metadatas"]
            )

            if results["ids"]:
                self._collection.delete(ids=results["ids"])

            # Prepare content for chunking (same logic as add_runbook)
            all_content = []

            # Add different types of content with section labels
            if runbook_data.procedures:
                for i, procedure in enumerate(runbook_data.procedures):
                    all_content.append(f"PROCEDURE {i+1}: {procedure}")

            if runbook_data.troubleshooting_steps:
                for i, step in enumerate(runbook_data.troubleshooting_steps):
                    all_content.append(f"TROUBLESHOOTING {i+1}: {step}")

            if runbook_data.prerequisites:
                for i, prereq in enumerate(runbook_data.prerequisites):
                    all_content.append(f"PREREQUISITE {i+1}: {prereq}")

            # Add structured sections
            for (
                section_name,
                section_content,
            ) in runbook_data.structured_sections.items():
                all_content.append(f"{section_name.upper()}: {section_content}")

            # Add raw content if no structured content available
            if not all_content and runbook_data.raw_content:
                all_content.append(runbook_data.raw_content)

            if not all_content:
                raise ValueError("No content available for chunking")

            # Combine all content
            combined_content = "\n\n".join(all_content)

            # Generate chunks
            chunks = self._chunk_content(combined_content)

            # Process each chunk with the same runbook ID
            chunk_ids = []
            embeddings = []
            documents = []
            metadatas = []

            for i, chunk_content in enumerate(chunks):
                # Generate chunk ID with preserved runbook ID
                chunk_id = f"{runbook_id}_chunk_{i}"
                chunk_ids.append(chunk_id)

                # Generate embedding
                embedding = self._generate_embeddings(chunk_content)
                embeddings.append(embedding)

                # Store document content
                documents.append(chunk_content)

                # Prepare metadata
                metadata = {
                    "runbook_id": runbook_id,
                    "chunk_index": i,
                    "title": runbook_data.metadata.title,
                    "author": runbook_data.metadata.author or "",
                    "space_key": runbook_data.metadata.space_key,
                    "page_id": runbook_data.metadata.page_id,
                    "page_url": str(runbook_data.metadata.page_url),
                    "last_modified": runbook_data.metadata.last_modified.isoformat(),
                    "tags": (
                        ",".join(runbook_data.metadata.tags)
                        if runbook_data.metadata.tags
                        else ""
                    ),
                }
                metadatas.append(metadata)

            # Add updated chunks to ChromaDB collection
            self._collection.add(
                ids=chunk_ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
            )

            logger.info(f"Updated runbook {runbook_id} with {len(chunks)} chunks")

        except ValueError:
            # Re-raise ValueError as-is for validation errors
            raise
        except Exception as e:
            logger.error(f"Failed to update runbook {runbook_id}: {e}")
            raise RuntimeError(f"Failed to update runbook: {e}")

    def delete_runbook(self, runbook_id: str) -> None:
        """
        Delete a runbook and all its associated chunks.

        Args:
            runbook_id: Unique runbook identifier

        Raises:
            ValueError: If runbook_id is invalid
            RuntimeError: If deletion operation fails
        """
        if not runbook_id or not runbook_id.strip():
            raise ValueError("Runbook ID cannot be empty")

        try:
            # Get all chunk IDs for this runbook
            results = self._collection.get(
                where={"runbook_id": runbook_id.strip()}, include=["metadatas"]
            )

            if not results["ids"]:
                logger.warning(f"Runbook {runbook_id} not found for deletion")
                return

            # Delete all chunks
            self._collection.delete(ids=results["ids"])

            logger.info(
                f"Deleted runbook {runbook_id} with {len(results['ids'])} chunks"
            )

        except Exception as e:
            logger.error(f"Failed to delete runbook {runbook_id}: {e}")
            raise RuntimeError(f"Failed to delete runbook: {e}")

    def list_runbooks(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        List all runbooks with pagination support.

        Args:
            limit: Maximum number of runbooks to return
            offset: Number of runbooks to skip

        Returns:
            List of runbook summary dictionaries

        Raises:
            ValueError: If parameters are invalid
            RuntimeError: If listing operation fails
        """
        if limit <= 0 or limit > 1000:
            raise ValueError("Limit must be between 1 and 1000")

        if offset < 0:
            raise ValueError("Offset must be non-negative")

        try:
            # Get all runbook metadata (this is simplified - in production you'd want
            # more efficient pagination)
            results = self._collection.get(include=["metadatas"])

            # Group by runbook_id to get unique runbooks
            runbooks = {}
            for metadata in results["metadatas"]:
                runbook_id = metadata["runbook_id"]
                if runbook_id not in runbooks:
                    runbooks[runbook_id] = {
                        "runbook_id": runbook_id,
                        "title": metadata["title"],
                        "author": metadata["author"],
                        "space_key": metadata["space_key"],
                        "page_id": metadata["page_id"],
                        "last_modified": metadata["last_modified"],
                        "chunk_count": 0,
                    }
                runbooks[runbook_id]["chunk_count"] += 1

            # Apply pagination
            runbook_list = list(runbooks.values())
            paginated_results = runbook_list[offset : offset + limit]

            return paginated_results

        except Exception as e:
            logger.error(f"Failed to list runbooks: {e}")
            raise RuntimeError(f"Failed to list runbooks: {e}")

    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the vector database collection.

        Returns:
            Dictionary containing collection statistics
        """
        try:
            count = self._collection.count()

            return {
                "collection_name": self.collection_name,
                "total_chunks": count,
                "embedding_dimension": self._embedding_dimension,
                "persist_directory": self.persist_directory,
            }

        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {
                "collection_name": self.collection_name,
                "total_chunks": 0,
                "embedding_dimension": self._embedding_dimension,
                "persist_directory": self.persist_directory,
                "error": str(e),
            }

    def health_check(self) -> bool:
        """
        Check if the vector database is healthy and accessible.

        Returns:
            True if healthy, False otherwise
        """
        try:
            # Try to get collection count
            self._collection.count()
            return True
        except Exception as e:
            logger.error(f"Vector database health check failed: {e}")
            return False

    def _metadata_dict_to_runbook_metadata(self, metadata_dict: Dict[str, Any]):
        """
        Convert ChromaDB metadata dictionary to RunbookMetadata object.

        Args:
            metadata_dict: Dictionary containing metadata from ChromaDB

        Returns:
            RunbookMetadata object
        """
        from datetime import datetime
        from .models import RunbookMetadata

        return RunbookMetadata(
            title=metadata_dict["title"],
            author=metadata_dict["author"] if metadata_dict["author"] else None,
            last_modified=datetime.fromisoformat(metadata_dict["last_modified"]),
            space_key=metadata_dict["space_key"],
            page_id=metadata_dict["page_id"],
            page_url=metadata_dict["page_url"],
            tags=metadata_dict["tags"].split(",") if metadata_dict["tags"] else [],
        )
