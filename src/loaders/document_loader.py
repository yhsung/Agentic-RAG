"""
Document loading and chunking for the Agentic RAG system.

This module provides functionality to load documents from various formats (PDF, Markdown, text)
and split them into chunks for embedding and storage in the vector store.
"""

import logging
from pathlib import Path
from typing import List, Optional

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config.settings import settings

# Configure logging
logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


class DocumentLoader:
    """
    Handles loading and chunking documents from various file formats.

    Supports PDF, Markdown, and plain text files.
    """

    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
    ):
        """
        Initialize the document loader.

        Args:
            chunk_size: Maximum character size for chunks (default: from settings)
            chunk_overlap: Character overlap between chunks (default: from settings)
        """
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP

        # Initialize text splitter with semantic separators
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
            length_function=len,
        )

        logger.info(
            f"DocumentLoader initialized: chunk_size={self.chunk_size}, "
            f"chunk_overlap={self.chunk_overlap}"
        )

    def load_document(self, file_path: str) -> List[Document]:
        """
        Load a single document from a file.

        Args:
            file_path: Path to the document file

        Returns:
            List of Document objects (one for single-page docs, multiple for PDFs)

        Raises:
            ValueError: If file format is not supported
            FileNotFoundError: If file doesn't exist
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if not path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")

        # Select loader based on file extension
        suffix = path.suffix.lower()

        try:
            if suffix == ".pdf":
                logger.debug(f"Loading PDF: {file_path}")
                loader = PyPDFLoader(str(path))
                docs = loader.load()

            elif suffix in [".md", ".markdown", ".txt"]:
                logger.debug(f"Loading text file: {file_path}")
                loader = TextLoader(str(path), encoding="utf-8")
                docs = loader.load()

            else:
                raise ValueError(
                    f"Unsupported file format: {suffix}. "
                    f"Supported formats: .pdf, .md, .markdown, .txt"
                )

            # Add source metadata to each document
            for doc in docs:
                doc.metadata["source"] = str(path)

            logger.info(f"Loaded {len(docs)} document(s) from {file_path}")
            return docs

        except Exception as e:
            logger.error(f"Error loading document {file_path}: {e}")
            raise

    def load_documents(self, directory: str) -> List[Document]:
        """
        Load all supported documents from a directory.

        Args:
            directory: Path to directory containing documents

        Returns:
            List of all loaded Document objects

        Raises:
            ValueError: If directory doesn't exist or isn't a directory
        """
        path = Path(directory)

        if not path.exists():
            raise ValueError(f"Directory not found: {directory}")

        if not path.is_dir():
            raise ValueError(f"Path is not a directory: {directory}")

        # Supported file extensions
        supported_extensions = {".pdf", ".md", ".markdown", ".txt"}

        # Find all supported files
        files = [
            f for f in path.rglob("*")
            if f.is_file() and f.suffix.lower() in supported_extensions
        ]

        if not files:
            logger.warning(f"No supported documents found in {directory}")
            return []

        logger.info(f"Found {len(files)} supported document(s) in {directory}")

        # Load all documents
        all_docs = []
        for file_path in files:
            try:
                docs = self.load_document(str(file_path))
                all_docs.extend(docs)
            except Exception as e:
                logger.error(f"Failed to load {file_path}: {e}")
                continue

        logger.info(f"Successfully loaded {len(all_docs)} document(s) total")
        return all_docs

    def chunk_documents(self, documents: List[Document]) -> List[Document]:
        """
        Split documents into chunks for embedding and retrieval.

        Args:
            documents: List of Document objects to chunk

        Returns:
            List of chunked Document objects
        """
        if not documents:
            logger.warning("No documents to chunk")
            return []

        logger.info(f"Chunking {len(documents)} document(s)...")

        # Split documents into chunks
        chunks = self.text_splitter.split_documents(documents)

        # Add chunk index to metadata
        for i, chunk in enumerate(chunks):
            chunk.metadata["chunk_index"] = i

        logger.info(f"Created {len(chunks)} chunks from {len(documents)} document(s)")

        # Log statistics
        if chunks:
            chunk_sizes = [len(chunk.page_content) for chunk in chunks]
            avg_size = sum(chunk_sizes) / len(chunk_sizes)
            logger.info(
                f"Chunk statistics: min={min(chunk_sizes)}, "
                f"max={max(chunk_sizes)}, avg={avg_size:.1f} characters"
            )

        return chunks


def load_and_chunk(path: str) -> List[Document]:
    """
    Convenience function to load and chunk documents from a file or directory.

    Args:
        path: Path to document file or directory

    Returns:
        List of chunked Document objects
    """
    loader = DocumentLoader()

    # Check if path is file or directory
    if Path(path).is_file():
        documents = loader.load_document(path)
    else:
        documents = loader.load_documents(path)

    chunks = loader.chunk_documents(documents)
    return chunks


if __name__ == "__main__":
    """Test the document loader with sample files."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python document_loader.py <file_or_directory>")
        sys.exit(1)

    test_path = sys.argv[1]

    try:
        chunks = load_and_chunk(test_path)
        print(f"\nLoaded and chunked {len(chunks)} chunks from {test_path}")

        if chunks:
            print(f"\nFirst chunk preview:")
            print("-" * 50)
            print(chunks[0].page_content[:200] + "...")
            print("-" * 50)
            print(f"Metadata: {chunks[0].metadata}")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
