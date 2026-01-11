"""
ChromaDB vector store integration for the Agentic RAG system.

This module manages ChromaDB integration with Ollama embeddings for document storage
and retrieval. Implements a singleton pattern for thread-safe access.
"""

import logging
from typing import List, Optional

from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStoreRetriever

from config.settings import settings

# Configure logging
logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

# Global singleton instance
_vector_store: Optional[Chroma] = None


def get_embeddings() -> OllamaEmbeddings:
    """
    Get Ollama embeddings instance for generating embeddings.

    Returns:
        OllamaEmbeddings instance configured with settings
    """
    return OllamaEmbeddings(
        model=settings.EMBEDDING_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
    )


def get_vector_store() -> Chroma:
    """
    Get or create the singleton ChromaDB vector store instance.

    This function implements lazy initialization - the vector store is created
    on first call and reused for subsequent calls.

    Returns:
        Chroma vector store instance

    Raises:
        Exception: If vector store initialization fails
    """
    global _vector_store

    if _vector_store is None:
        try:
            logger.info("Initializing ChromaDB vector store...")

            # Get embeddings
            embeddings = get_embeddings()

            # Get persist directory path
            persist_dir = settings.get_chroma_persist_path()

            # Initialize ChromaDB with persistent storage
            _vector_store = Chroma(
                collection_name=settings.CHROMA_COLLECTION,
                embedding_function=embeddings,
                persist_directory=str(persist_dir),
            )

            logger.info(
                f"ChromaDB initialized: collection='{settings.CHROMA_COLLECTION}', "
                f"path='{persist_dir}'"
            )

        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise

    return _vector_store


def add_documents(documents: List[Document]) -> None:
    """
    Add documents to the vector store with embeddings.

    Documents are automatically embedded using Ollama and stored in ChromaDB.

    Args:
        documents: List of Document objects to add

    Raises:
        Exception: If document addition fails
    """
    if not documents:
        logger.warning("No documents to add to vector store")
        return

    try:
        vector_store = get_vector_store()

        logger.info(f"Adding {len(documents)} documents to vector store...")

        # Add documents with embeddings (auto-persisted in langchain-chroma)
        vector_store.add_documents(documents)

        logger.info(f"Successfully added {len(documents)} documents to vector store")

    except Exception as e:
        logger.error(f"Failed to add documents to vector store: {e}")
        raise


def get_retriever(k: Optional[int] = None) -> VectorStoreRetriever:
    """
    Get a retriever for similarity search from the vector store.

    Args:
        k: Number of documents to retrieve (default: from settings)

    Returns:
        VectorStoreRetriever configured for similarity search

    Raises:
        Exception: If retriever creation fails
    """
    try:
        vector_store = get_vector_store()

        # Use provided k or default from settings
        retrieval_k = k or settings.RETRIEVAL_K

        # Create retriever with search kwargs
        retriever = vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": retrieval_k},
        )

        logger.debug(f"Created retriever with k={retrieval_k}")

        return retriever

    except Exception as e:
        logger.error(f"Failed to create retriever: {e}")
        raise


def similarity_search(query: str, k: Optional[int] = None) -> List[Document]:
    """
    Perform similarity search for a query.

    Args:
        query: Search query string
        k: Number of documents to retrieve (default: from settings)

    Returns:
        List of similar Document objects

    Raises:
        Exception: If search fails
    """
    try:
        vector_store = get_vector_store()

        # Use provided k or default from settings
        retrieval_k = k or settings.RETRIEVAL_K

        logger.debug(f"Performing similarity search for: '{query}' (k={retrieval_k})")

        # Perform similarity search
        results = vector_store.similarity_search(query, k=retrieval_k)

        logger.debug(f"Retrieved {len(results)} documents")

        return results

    except Exception as e:
        logger.error(f"Similarity search failed: {e}")
        raise


def clear_collection() -> None:
    """
    Clear all documents from the vector store collection.

    This is useful for resetting the knowledge base.

    Raises:
        Exception: If clearing fails
    """
    try:
        global _vector_store

        # If vector store exists, delete the collection
        if _vector_store is not None:
            logger.warning(f"Deleting collection '{settings.CHROMA_COLLECTION}'...")
            _vector_store.delete_collection()
            _vector_store = None

        # Recreate empty vector store
        get_vector_store()

        logger.info("Collection cleared successfully")

    except Exception as e:
        logger.error(f"Failed to clear collection: {e}")
        raise


def get_collection_count() -> int:
    """
    Get the number of documents in the vector store.

    Returns:
        Number of documents in the collection

    Raises:
        Exception: If count retrieval fails
    """
    try:
        vector_store = get_vector_store()
        count = vector_store._collection.count()

        logger.debug(f"Collection contains {count} documents")

        return count

    except Exception as e:
        logger.error(f"Failed to get collection count: {e}")
        raise


def get_collection_stats() -> dict:
    """
    Get detailed statistics about the document collection.

    Returns:
        Dictionary containing:
            - total_chunks: Total number of document chunks
            - unique_sources: Number of unique source documents
            - sources: List of unique source file paths

    Raises:
        Exception: If stats retrieval fails
    """
    try:
        vector_store = get_vector_store()

        # Get total count
        total_chunks = vector_store._collection.count()

        # Get all documents to analyze sources
        if total_chunks > 0:
            # Get all metadata
            results = vector_store._collection.get(
                include=["metadatas"]
            )

            # Extract unique sources
            sources = set()
            if results and results.get("metadatas"):
                for metadata in results["metadatas"]:
                    if metadata and "source" in metadata:
                        sources.add(metadata["source"])

            unique_sources = len(sources)
            source_list = sorted(list(sources))
        else:
            unique_sources = 0
            source_list = []

        stats = {
            "total_chunks": total_chunks,
            "unique_sources": unique_sources,
            "sources": source_list
        }

        logger.debug(f"Collection stats: {total_chunks} chunks from {unique_sources} sources")

        return stats

    except Exception as e:
        logger.error(f"Failed to get collection stats: {e}")
        raise


if __name__ == "__main__":
    """Test the vector store functionality."""
    print("Testing ChromaDB vector store...")

    # Test embeddings
    print("\n1. Testing embeddings...")
    embeddings = get_embeddings()
    test_text = "This is a test document."
    vector = embeddings.embed_query(test_text)
    print(f"   Embedding dimension: {len(vector)}")

    # Test vector store initialization
    print("\n2. Testing vector store initialization...")
    vector_store = get_vector_store()
    print(f"   Collection name: {settings.CHROMA_COLLECTION}")
    print(f"   Persist directory: {settings.get_chroma_persist_path()}")

    # Test collection count
    print("\n3. Testing collection count...")
    count = get_collection_count()
    print(f"   Documents in collection: {count}")

    # Test retriever creation
    print("\n4. Testing retriever creation...")
    retriever = get_retriever()
    print(f"   Retriever created: {type(retriever)}")
    print(f"   Retrieval k: {settings.RETRIEVAL_K}")

    print("\n✅ All tests passed!")
