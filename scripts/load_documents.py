#!/usr/bin/env python3
"""
Document loading script for the Agentic RAG system.

This script loads documents from a file or directory, chunks them,
and stores them in the ChromaDB vector store for retrieval.
"""

import sys
from pathlib import Path
from typing import List

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn, TimeRemainingColumn
from rich.table import Table

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import settings
from src.loaders.document_loader import DocumentLoader
from src.vectorstore.chroma_store import add_documents, clear_collection, get_collection_count

console = Console()


def print_statistics(documents: List, chunks: List, verbose: bool = False):
    """
    Print loading statistics in a formatted table.

    Args:
        documents: List of original documents
        chunks: List of chunked documents
        verbose: Whether to show detailed information
    """
    console.print("\n[bold cyan]Loading Statistics[/bold cyan]")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan", width=30)
    table.add_column("Value", style="yellow")

    # Document statistics
    table.add_row("Original Documents", str(len(documents)))

    # Chunk statistics
    table.add_row("Chunks Created", str(len(chunks)))

    if chunks:
        # Calculate chunk sizes
        chunk_sizes = [len(chunk.page_content) for chunk in chunks]
        avg_size = sum(chunk_sizes) / len(chunk_sizes)

        table.add_row("Average Chunk Size", f"{avg_size:.1f} characters")
        table.add_row("Min Chunk Size", f"{min(chunk_sizes)} characters")
        table.add_row("Max Chunk Size", f"{max(chunk_sizes)} characters")

    # Vector store statistics
    total_docs = get_collection_count()
    table.add_row("Total Documents in Store", str(total_docs))

    console.print(table)

    if verbose and chunks:
        console.print("\n[bold cyan]Sample Chunks[/bold cyan]")

        for i, chunk in enumerate(chunks[:3], 1):
            console.print(
                Panel(
                    chunk.page_content[:300] + "..."
                    if len(chunk.page_content) > 300
                    else chunk.page_content,
                    title=f"Chunk {i}",
                    border_style="cyan",
                )
            )

            if i < len(chunks) and i < 3:
                console.print()


@click.command()
@click.argument("path", type=click.Path(exists=True))
@click.option(
    "--replace",
    is_flag=True,
    help="Clear existing documents before loading (default: append)",
)
@click.option(
    "--verbose", "-v", is_flag=True, help="Show detailed chunk information"
)
def main(path: str, replace: bool, verbose: bool):
    """
    Load documents into the vector store.

    PATH: Path to a document file or directory containing documents

    Example usage:

        # Load all documents from a directory
        python scripts/load_documents.py data/raw/

        # Load a single file
        python scripts/load_documents.py data/raw/document.pdf

        # Replace existing documents
        python scripts/load_documents.py data/raw/ --replace

        # Show verbose output
        python scripts/load_documents.py data/raw/ --verbose
    """
    console.print(
        Panel(
            "[bold cyan]Agentic RAG - Document Loader[/bold cyan]\n"
            f"Loading documents from: [yellow]{path}[/yellow]",
            title="📄 Document Loader",
            border_style="cyan",
        )
    )

    try:
        # Step 1: Clear existing documents if requested
        if replace:
            console.print("\n[yellow]Clearing existing documents...[/yellow]")
            clear_collection()
            console.print("✅ [green]Cleared existing documents[/green]")

        # Step 2: Load documents
        console.print("\n[bold blue]Loading documents...[/bold blue]")

        loader = DocumentLoader()

        # Check if path is file or directory
        path_obj = Path(path)
        if path_obj.is_file():
            console.print(f"Loading single file: {path}")
            documents = loader.load_document(path)
        else:
            console.print(f"Loading all documents from directory: {path}")
            documents = loader.load_documents(path)

        if not documents:
            console.print(
                "\n❌ [red]No documents found or loaded.[/red]\n"
                "Please check the path and ensure it contains supported files "
                "(.pdf, .md, .markdown, .txt)"
            )
            sys.exit(1)

        console.print(f"✅ [green]Loaded {len(documents)} document(s)[/green]")

        # Step 3: Chunk documents
        console.print("\n[bold blue]Chunking documents...[/bold blue]")

        chunks = loader.chunk_documents(documents)

        if not chunks:
            console.print("\n❌ [red]Failed to chunk documents.[/red]")
            sys.exit(1)

        console.print(f"✅ [green]Created {len(chunks)} chunk(s)[/green]")

        # Step 4: Add to vector store with progress bar
        console.print("\n[bold blue]Adding chunks to vector store...[/bold blue]")

        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(
                "Embedding and storing...", total=len(chunks)
            )

            # Add documents in batches for better progress tracking
            batch_size = 10
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i : i + batch_size]
                add_documents(batch)
                progress.update(task, advance=len(batch))

        console.print("✅ [green]All chunks added to vector store[/green]")

        # Step 5: Print statistics
        print_statistics(documents, chunks, verbose=verbose)

        # Success message
        console.print(
            "\n✅ [bold green]Document loading completed successfully![/bold green]\n"
            "[yellow]Next steps:[/yellow]\n"
            "1. Test retrieval: python cli/main.py query\n"
            "2. Or run a test: python -m pytest tests/"
        )

    except FileNotFoundError as e:
        console.print(f"\n❌ [red]File not found: {e}[/red]")
        sys.exit(1)

    except ValueError as e:
        console.print(f"\n❌ [red]Invalid input: {e}[/red]")
        sys.exit(1)

    except Exception as e:
        console.print(
            f"\n❌ [red]An error occurred:[/red]\n"
            f"   {type(e).__name__}: {e}"
        )
        console.print(
            "\n[yellow]For more information, run with --verbose[/yellow]"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
