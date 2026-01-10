#!/usr/bin/env python3
"""
Setup script for initializing and verifying the ChromaDB vector store.

This script creates the necessary directories, initializes ChromaDB,
and verifies that Ollama and the embedding model are properly configured.
"""

import sys
from pathlib import Path

import requests
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import settings
from src.vectorstore.chroma_store import get_embeddings, get_vector_store

console = Console()


def verify_ollama() -> bool:
    """
    Verify that Ollama is running and accessible.

    Returns:
        True if Ollama is accessible, False otherwise
    """
    console.print("\n[bold blue]Verifying Ollama connection...[/bold blue]")

    try:
        response = requests.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=5)

        if response.status_code == 200:
            console.print("✅ [green]Ollama is running[/green]")

            # Check if embedding model is available
            data = response.json()
            models = [model["name"] for model in data.get("models", [])]

            console.print(f"   Available models: {', '.join(models)}")

            # Check for embedding model (match with or without tag)
            model_found = any(
                settings.EMBEDDING_MODEL in model or model in settings.EMBEDDING_MODEL
                for model in models
            )

            if model_found:
                console.print(
                    f"✅ [green]Embedding model '{settings.EMBEDDING_MODEL}' is available[/green]"
                )
                return True
            else:
                console.print(
                    f"❌ [red]Embedding model '{settings.EMBEDDING_MODEL}' not found[/red]"
                )
                console.print(
                    f"\n[yellow]To pull the model, run:[/yellow]\n"
                    f"   ollama pull {settings.EMBEDDING_MODEL}"
                )
                return False

        else:
            console.print(
                f"❌ [red]Ollama returned status {response.status_code}[/red]"
            )
            return False

    except requests.exceptions.ConnectionError:
        console.print(
            "❌ [red]Cannot connect to Ollama[/red]\n"
            "\n[yellow]Please make sure Ollama is running:[/yellow]\n"
            "   ollama serve"
        )
        return False

    except Exception as e:
        console.print(f"❌ [red]Error connecting to Ollama: {e}[/red]")
        return False


def verify_embeddings() -> bool:
    """
    Verify that embeddings can be generated.

    Returns:
        True if embeddings work, False otherwise
    """
    console.print("\n[bold blue]Testing embedding generation...[/bold blue]")

    try:
        embeddings = get_embeddings()
        test_text = "This is a test document for embedding generation."

        console.print(f"   Generating embedding for: '{test_text}'")
        vector = embeddings.embed_query(test_text)

        console.print(
            f"✅ [green]Embedding generated successfully[/green]\n"
            f"   Embedding dimension: {len(vector)}"
        )

        # Verify embedding dimension (nomic-embed-text should be 1024)
        if len(vector) == 1024:
            console.print("   ✅ [green]Embedding dimension is correct (1024)[/green]")
        else:
            console.print(
                f"   ⚠️  [yellow]Warning: Expected dimension 1024, got {len(vector)}[/yellow]"
            )

        return True

    except Exception as e:
        console.print(f"❌ [red]Failed to generate embeddings: {e}[/red]")
        return False


def verify_chromadb() -> bool:
    """
    Verify that ChromaDB can be initialized.

    Returns:
        True if ChromaDB works, False otherwise
    """
    console.print("\n[bold blue]Verifying ChromaDB initialization...[/bold blue]")

    try:
        vector_store = get_vector_store()

        console.print(
            f"✅ [green]ChromaDB initialized successfully[/green]\n"
            f"   Collection name: {settings.CHROMA_COLLECTION}\n"
            f"   Persist directory: {settings.get_chroma_persist_path()}"
        )

        # Get collection count
        count = vector_store._collection.count()
        console.print(f"   Documents in collection: {count}")

        return True

    except Exception as e:
        console.print(f"❌ [red]Failed to initialize ChromaDB: {e}[/red]")
        return False


def display_configuration():
    """Display the current configuration."""
    console.print("\n[bold blue]Current Configuration[/bold blue]")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Setting", style="cyan", width=30)
    table.add_column("Value", style="yellow")

    table.add_row("Ollama Base URL", settings.OLLAMA_BASE_URL)
    table.add_row("Embedding Model", settings.EMBEDDING_MODEL)
    table.add_row("Generation Model", settings.GENERATION_MODEL)
    table.add_row("Grading Model", settings.GRADING_MODEL)
    table.add_row("ChromaDB Collection", settings.CHROMA_COLLECTION)
    table.add_row("ChromaDB Path", str(settings.get_chroma_persist_path()))
    table.add_row("Retrieval K", str(settings.RETRIEVAL_K))
    table.add_row("Chunk Size", str(settings.CHUNK_SIZE))
    table.add_row("Chunk Overlap", str(settings.CHUNK_OVERLAP))
    table.add_row("Max Retries", str(settings.MAX_RETRIES))
    table.add_row("Log Level", settings.LOG_LEVEL)

    console.print(table)


def main():
    """Main setup function."""
    console.print(
        Panel(
            "[bold cyan]Agentic RAG - Vector Store Setup[/bold cyan]\n"
            "This script will verify your configuration and initialize ChromaDB.",
            title="🔧 Setup",
            border_style="cyan",
        )
    )

    # Display configuration
    display_configuration()

    # Run verifications
    results = {
        "Ollama Connection": verify_ollama(),
        "Embedding Generation": verify_embeddings(),
        "ChromaDB Initialization": verify_chromadb(),
    }

    # Display summary
    console.print("\n[bold blue]Setup Summary[/bold blue]")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Component", style="cyan", width=30)
    table.add_column("Status", style="bold")

    all_passed = True
    for component, passed in results.items():
        status = "✅ [green]PASS[/green]" if passed else "❌ [red]FAIL[/red]"
        table.add_row(component, status)
        if not passed:
            all_passed = False

    console.print(table)

    if all_passed:
        console.print(
            "\n✅ [bold green]All checks passed![/bold green]\n"
            "Your vector store is ready to use.\n"
            "\n[yellow]Next steps:[/yellow]\n"
            "1. Load documents: python scripts/load_documents.py <path_to_documents>\n"
            "2. Or use the CLI: python cli/main.py load <path_to_documents>"
        )
        return 0
    else:
        console.print(
            "\n❌ [bold red]Some checks failed.[/bold red]\n"
            "Please fix the issues above before continuing."
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
