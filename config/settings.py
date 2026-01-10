"""
Configuration management using Pydantic Settings.

This module centralizes all configuration for the Agentic RAG system,
making it easy to swap models, adjust parameters, and manage environment variables.
"""

from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables or .env file.

    All settings can be overridden via environment variables.
    """

    # Project Paths
    PROJECT_ROOT: Path = Field(default_factory=lambda: Path(__file__).parent.parent)
    DATA_DIR: Path = Field(default_factory=lambda: Path(__file__).parent.parent / "data")

    # Ollama Configuration
    OLLAMA_BASE_URL: str = Field(
        default="http://localhost:11434",
        description="Base URL for Ollama API"
    )
    EMBEDDING_MODEL: str = Field(
        default="nomic-embed-text",
        description="Ollama model for embeddings (1024 dimensions)"
    )
    GENERATION_MODEL: str = Field(
        default="qwen3:30b",
        description="Ollama model for text generation"
    )
    GRADING_MODEL: str = Field(
        default="qwen3:30b",
        description="Ollama model for grading tasks (can use smaller model)"
    )

    # ChromaDB Configuration
    CHROMA_PERSIST_DIR: str = Field(
        default="./data/chroma_db",
        description="Directory for ChromaDB persistence"
    )
    CHROMA_COLLECTION: str = Field(
        default="agentic_rag",
        description="ChromaDB collection name"
    )

    # Retrieval Settings
    RETRIEVAL_K: int = Field(
        default=4,
        ge=1,
        le=20,
        description="Number of documents to retrieve"
    )
    CHUNK_SIZE: int = Field(
        default=1000,
        ge=100,
        le=5000,
        description="Character size for document chunks"
    )
    CHUNK_OVERLAP: int = Field(
        default=200,
        ge=0,
        le=1000,
        description="Character overlap between chunks"
    )
    MAX_RETRIES: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum query rewrite attempts"
    )

    # Web Search Configuration
    TAVILY_API_KEY: Optional[str] = Field(
        default=None,
        description="Tavily API key for web search (optional)"
    )
    WEB_SEARCH_MAX_RESULTS: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum web search results to retrieve"
    )

    # Logging Configuration
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    VERBOSE: bool = Field(
        default=False,
        description="Enable verbose output"
    )

    # Model Configuration
    GENERATION_TEMPERATURE: float = Field(
        default=0.0,
        ge=0.0,
        le=2.0,
        description="Temperature for generation model (0 = deterministic)"
    )
    GRADING_TEMPERATURE: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Temperature for grading model"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    def get_chroma_persist_path(self) -> Path:
        """Get absolute path for ChromaDB persistence directory."""
        path = Path(self.CHROMA_PERSIST_DIR)
        if not path.is_absolute():
            path = self.PROJECT_ROOT / path
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_data_path(self, subdir: str = "") -> Path:
        """Get path within data directory."""
        path = self.DATA_DIR / subdir if subdir else self.DATA_DIR
        path.mkdir(parents=True, exist_ok=True)
        return path


# Global settings instance
settings = Settings()


if __name__ == "__main__":
    """Print current configuration for debugging."""
    print("Current Configuration:")
    print("=" * 50)
    print(f"Ollama Base URL: {settings.OLLAMA_BASE_URL}")
    print(f"Embedding Model: {settings.EMBEDDING_MODEL}")
    print(f"Generation Model: {settings.GENERATION_MODEL}")
    print(f"Grading Model: {settings.GRADING_MODEL}")
    print(f"ChromaDB Path: {settings.get_chroma_persist_path()}")
    print(f"ChromaDB Collection: {settings.CHROMA_COLLECTION}")
    print(f"Retrieval K: {settings.RETRIEVAL_K}")
    print(f"Chunk Size: {settings.CHUNK_SIZE}")
    print(f"Chunk Overlap: {settings.CHUNK_OVERLAP}")
    print(f"Max Retries: {settings.MAX_RETRIES}")
    print(f"Log Level: {settings.LOG_LEVEL}")
    print(f"Verbose: {settings.VERBOSE}")
    print(f"Tavily API Key: {'Set' if settings.TAVILY_API_KEY else 'Not Set'}")
    print("=" * 50)
