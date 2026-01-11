"""
Configuration management using Pydantic Settings.

This module centralizes all configuration for the Agentic RAG system,
making it easy to swap models, adjust parameters, and manage environment variables.
"""

import os
from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def get_ollama_base_url() -> str:
    """
    Get Ollama base URL with auto-detection for DevContainer.

    Automatically detects if running in a container and returns
    the appropriate URL:
    - Container: http://host.docker.internal:11434
    - Local: http://localhost:11434

    Detection methods (in order of reliability):
    1. Environment variable OLLAMA_BASE_URL (explicit override)
    2. File system checks (/.dockerenv or /proc/1/cgroup)

    Returns:
        str: Ollama base URL

    Example:
        >>> url = get_ollama_base_url()
        >>> assert "localhost" in url or "host.docker.internal" in url
    """
    # Check environment variable OLLAMA_BASE_URL first (explicit override)
    if os.getenv("OLLAMA_BASE_URL"):
        return os.getenv("OLLAMA_BASE_URL")

    # Check for container indicators using file system
    # /.dockerenv is created by Docker/DevContainer
    # /proc/1/cgroup contains container info in Linux containers
    if Path("/.dockerenv").exists():
        return "http://host.docker.internal:11434"

    # Check /proc/1/cgroup for container indicators (more reliable on Linux)
    cgroup_path = Path("/proc/1/cgroup")
    if cgroup_path.exists():
        try:
            cgroup_content = cgroup_path.read_text()
            # Check if running in a container (docker, kubepods, etc.)
            if any(keyword in cgroup_content.lower() for keyword in ["docker", "kubepods", "containerd"]):
                return "http://host.docker.internal:11434"
        except Exception:
            # If we can't read cgroup, continue with default
            pass

    # Default to localhost for local development
    return "http://localhost:11434"


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
        default_factory=get_ollama_base_url,
        description="Base URL for Ollama API (auto-detects DevContainer)"
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
    MAX_REGENERATIONS: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum answer regeneration attempts for hallucination correction"
    )
    WORKFLOW_RECURSION_LIMIT: int = Field(
        default=50,
        ge=25,
        le=200,
        description="Maximum workflow steps before stopping (LangGraph recursion limit)"
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

    # A/B Testing Configuration
    AB_TEST_ENABLED: bool = Field(
        default=False,
        description="Enable A/B testing for prompt variants"
    )
    AB_TEST_RESULTS_DB: str = Field(
        default="./data/ab_test_results.db",
        description="Path to SQLite database for A/B test results"
    )
    AB_TEST_DEFAULT_VARIANT: str = Field(
        default="baseline",
        description="Default prompt variant to use (baseline, detailed, bullets, reasoning)"
    )
    AB_TEST_AUTO_COLLECT: bool = Field(
        default=True,
        description="Automatically collect A/B test data during queries"
    )
    AB_TEST_SESSION_ID: str = Field(
        default="",
        description="Session identifier for grouping A/B test runs"
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
    print(f"Max Regenerations: {settings.MAX_REGENERATIONS}")
    print(f"Workflow Recursion Limit: {settings.WORKFLOW_RECURSION_LIMIT}")
    print(f"Log Level: {settings.LOG_LEVEL}")
    print(f"Verbose: {settings.VERBOSE}")
    print(f"Tavily API Key: {'Set' if settings.TAVILY_API_KEY else 'Not Set'}")
    print(f"\nA/B Testing:")
    print(f"  Enabled: {settings.AB_TEST_ENABLED}")
    print(f"  Results DB: {settings.AB_TEST_RESULTS_DB}")
    print(f"  Default Variant: {settings.AB_TEST_DEFAULT_VARIANT}")
    print(f"  Auto Collect: {settings.AB_TEST_AUTO_COLLECT}")
    print("=" * 50)
