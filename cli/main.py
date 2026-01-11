"""
Command-Line Interface for Agentic RAG System

This module provides a user-friendly CLI for interacting with the
Agentic RAG system using Click and Rich for beautiful terminal output.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich.text import Text

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.graph.workflow import AgenticRAGWorkflow
from src.loaders.document_loader import DocumentLoader
from src.vectorstore.chroma_store import get_vector_store, add_documents
from config.settings import settings

# Import A/B test commands
from cli.ab_test_commands import ab_test


# Initialize Rich console
console = Console()

# Configure logging
logging.basicConfig(
    level=logging.WARNING,  # Reduce noise in CLI
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """
    Agentic RAG System - CLI Interface

    A production-ready RAG system with self-correction capabilities.
    """
    pass


# Add A/B test command group
cli.add_command(ab_test)


@cli.command()
@click.argument("question", required=False)
@click.option("--verbose", "-v", is_flag=True, help="Show detailed execution steps")
@click.option("--stream", "-s", is_flag=True, help="Stream execution in real-time")
def query(question: Optional[str], verbose: bool, stream: bool):
    """
    Ask a question and get an answer from the Agentic RAG system.

    If no question is provided, enters interactive mode.
    """
    if not question:
        interactive_mode(verbose=verbose, stream=stream)
    else:
        ask_question(question, verbose=verbose, stream=stream)


def interactive_mode(verbose: bool = False, stream: bool = False):
    """Interactive mode for asking multiple questions."""
    console.print(Panel(
        "[bold cyan]Agentic RAG System[/bold cyan]\n\n"
        "Interactive Mode - Type your questions below.\n"
        "Commands: [bold green]/clear[/bold green], [bold green]/exit[/bold green], [bold green]/quit[/bold green]\n"
        "Options: [bold]verbose[/bold] to toggle, [bold]stream[/bold] for real-time updates",
        title="🤖 Welcome",
        border_style="cyan"
    ))

    rag = None
    try:
        # Initialize workflow once
        with console.status("[bold cyan]Initializing Agentic RAG System...[/bold cyan]"):
            rag = AgenticRAGWorkflow()

        console.print("[green]✓[/green] System ready!\n")

        while True:
            try:
                # Get user input
                question = console.input("[bold yellow]Question[/bold yellow] (or /exit): ")

                if not question.strip():
                    continue

                # Handle commands
                if question.lower() in ['/exit', '/quit', '/q']:
                    console.print("[cyan]Goodbye! 👋[/cyan]")
                    break

                if question.lower() == '/clear':
                    console.clear()
                    continue

                if question.lower() == '/verbose':
                    verbose = not verbose
                    console.print(f"[cyan]Verbose mode: {'enabled' if verbose else 'disabled'}[/cyan]")
                    continue

                if question.lower() == '/stream':
                    stream = not stream
                    console.print(f"[cyan]Stream mode: {'enabled' if stream else 'disabled'}[/cyan]")
                    continue

                # Ask the question
                console.print()
                ask_question(question, verbose=verbose, stream=stream, rag=rag)
                console.print()

            except KeyboardInterrupt:
                console.print("\n[cyan]Use /exit to quit[/cyan]")
            except EOFError:
                break

    except Exception as e:
        console.print(f"[red]Error initializing system: {e}[/red]")
        sys.exit(1)


def ask_question(question: str, verbose: bool = False, stream: bool = False, rag: Optional[AgenticRAGWorkflow] = None):
    """
    Process a single question through the RAG system.

    Args:
        question: User's question
        verbose: Whether to show detailed steps
        stream: Whether to stream execution
        rag: Pre-initialized workflow (optional)
    """
    # Show question
    console.print(Panel(
        Text(question, style="bold yellow"),
        title="❓ Question",
        border_style="yellow"
    ))

    try:
        # Initialize workflow if not provided
        if rag is None:
            with console.status("[bold cyan]Initializing system...[/bold cyan]"):
                rag = AgenticRAGWorkflow()

        if stream:
            # Stream execution
            console.print("\n[bold]Executing workflow:[/bold]\n")

            for event in rag.stream(question):
                for node_name, state in event.items():
                    # Show node execution
                    icon = {"retrieve": "📚", "grade_documents": "✅",
                           "generate": "💡", "transform_query": "🔄",
                           "check_hallucination": "🔍", "check_usefulness": "🎯"}.get(node_name, "⚙️")

                    console.print(f"{icon} [bold cyan]{node_name}[/bold cyan]")

                    # Show relevant state info
                    if verbose:
                        if 'documents' in state:
                            console.print(f"  └─ Documents: {len(state['documents'])}")

                        if 'relevance_scores' in state and state['relevance_scores']:
                            relevant = sum(1 for s in state['relevance_scores'] if s == 'yes')
                            total = len(state['relevance_scores'])
                            console.print(f"  └─ Relevant: {relevant}/{total}")

                        if 'generation' in state and state['generation']:
                            preview = state['generation'][:100] + "..." if len(state['generation']) > 100 else state['generation']
                            console.print(f"  └─ Generation: {preview}")

                        if 'hallucination_check' in state and state['hallucination_check']:
                            grounded = state['hallucination_check']
                            icon = "✓" if grounded == "grounded" else "✗"
                            console.print(f"  └─ Grounded: {icon} {grounded}")

                        if 'usefulness_check' in state and state['usefulness_check']:
                            useful = state['usefulness_check']
                            icon = "✓" if useful == "useful" else "✗"
                            console.print(f"  └─ Useful: {icon} {useful}")

                    console.print()

            # Get final result
            result = event[list(event.keys())[-1]]  # Last state in stream
        else:
            # Run without streaming (show progress)
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True,
            ) as progress:
                task = progress.add_task("Processing question...", total=None)

                result = rag.run(question)

                if verbose:
                    progress.update(task, completed=True)
                    console.print()  # Add space after progress bar

        # Display result
        display_result(result, verbose)

    except Exception as e:
        console.print(f"\n[red]✗[/red] [bold red]Error:[/bold red] {e}")
        if verbose:
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)


def display_result(result: dict, verbose: bool = False):
    """
    Display the final result with rich formatting.

    Args:
        result: Final state from workflow
        verbose: Whether to show detailed metadata
    """
    # Main answer
    generation = result.get('generation', 'No generation available')
    console.print(Panel(
        Markdown(generation),
        title="✨ Answer",
        border_style="green"
    ))

    # Metadata
    if verbose:
        console.print("\n[bold]Metadata:[/bold]")

        # Create metadata table
        table = Table(show_header=False, box=None)
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="yellow")

        table.add_row("Documents Retrieved", str(len(result.get('documents', []))))
        table.add_row("Relevant Documents",
                      str(sum(1 for s in result.get('relevance_scores', []) if s == 'yes')) + "/" + str(len(result.get('relevance_scores', []))))
        table.add_row("Query Retries", str(result.get('retry_count', 0)))
        table.add_row("Web Search Used", result.get('web_search', 'No'))
        table.add_row("Hallucination Check", result.get('hallucination_check', 'N/A'))
        table.add_row("Usefulness Check", result.get('usefulness_check', 'N/A'))

        console.print(table)

        # Show sources if available
        documents = result.get('documents', [])
        if documents and len(documents) > 0:
            console.print("\n[bold]Sources:[/bold]")
            for i, doc in enumerate(documents[:3], 1):  # Show top 3
                source = doc.metadata.get('source', 'Unknown')
                title = doc.metadata.get('title', source)
                console.print(f"  {i}. [link]{title}[/link]")
                console.print(f"     Source: {source}")


@cli.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--chunk-size", default=1000, help="Character size for chunks")
@click.option("--chunk-overlap", default=200, help="Character overlap between chunks")
def load(path: str, chunk_size: int, chunk_overlap: int):
    """
    Load documents into the vector store.

    PATH can be a file or directory containing documents.
    Supported formats: PDF, Markdown, Plain Text
    """
    console.print(f"[cyan]Loading documents from:[/cyan] {path}\n")

    try:
        # Load documents
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task1 = progress.add_task("Loading documents...", total=None)

            loader = DocumentLoader(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )

            # Check if path is a file or directory
            from pathlib import Path
            path_obj = Path(path)

            if path_obj.is_file():
                raw_documents = loader.load_document(path)
            else:
                raw_documents = loader.load_documents(path)

            # Chunk the documents
            documents = loader.chunk_documents(raw_documents)

            progress.update(task1, completed=True)
            task2 = progress.add_task("Indexing documents...", total=None)

            # Initialize vectorstore and add documents
            vectorstore = get_vector_store()

            # Add documents to vectorstore
            add_documents(documents)

            progress.update(task2, completed=True)

        console.print(f"[green]✓[/green] Successfully loaded [bold green]{len(documents)}[/bold green] document chunks")
        console.print(f"[green]✓[/green] Vector store updated: [bold]{settings.CHROMA_PERSIST_DIR}[/bold]")

    except Exception as e:
        console.print(f"[red]✗[/red] [bold red]Error loading documents:[/bold red] {e}")
        import traceback
        console.print(traceback.format_exc())
        sys.exit(1)


@cli.command()
def status():
    """
    Show system status and configuration.
    """
    try:
        # Create info table
        table = Table(title="System Status", show_header=True)
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="bold")
        table.add_column("Details", style="yellow")

        # Ollama status
        try:
            import requests
            response = requests.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=2)
            ollama_status = "✅ Running" if response.status_code == 200 else "❌ Error"
            ollama_details = f"{settings.OLLAMA_BASE_URL}"
        except:
            ollama_status = "❌ Not Running"
            ollama_details = "Start with: ollama serve"

        table.add_row("Ollama", ollama_status, ollama_details)

        # Vector store status
        chroma_path = settings.get_chroma_persist_path()
        if chroma_path.exists():
            chroma_status = "✅ Initialized"
            chroma_details = f"{chroma_path}"
        else:
            chroma_status = "⚠️  Not Found"
            chroma_details = "Run: python scripts/load_documents.py"

        table.add_row("ChromaDB", chroma_status, chroma_details)

        # Models
        table.add_row("Generation Model", "✅ Configured", settings.GENERATION_MODEL)
        table.add_row("Embedding Model", "✅ Configured", settings.EMBEDDING_MODEL)
        table.add_row("Grading Model", "✅ Configured", settings.GRADING_MODEL)

        # Retrieval settings
        table.add_row("Retrieval K", "✅ Configured", str(settings.RETRIEVAL_K))
        table.add_row("Chunk Size", "✅ Configured", str(settings.CHUNK_SIZE))
        table.add_row("Max Retries", "✅ Configured", str(settings.MAX_RETRIES))

        console.print(table)

        # Self-correction mechanisms
        console.print("\n[bold]Self-Correction Mechanisms:[/bold]")

        # Check web search availability
        try:
            from src.agents.web_searcher import WebSearcher
            searcher = WebSearcher()
            web_search_status = "✅ Active" if searcher.is_available() else "⚠️  Unavailable (no API key or packages)"
        except Exception:
            web_search_status = "⚠️  Unavailable"

        mechanisms = [
            ("Document Relevance Grading", "✅ Active"),
            ("Query Rewriting", "✅ Active"),
            ("Hallucination Detection", "✅ Active"),
            ("Answer Usefulness Check", "✅ Active"),
            ("Web Search Fallback", web_search_status),
        ]

        for mechanism, status in mechanisms:
            console.print(f"  {status} {mechanism}")

        # Workflow info
        console.print("\n[bold]Workflow Graph:[/bold]")
        rag = AgenticRAGWorkflow()
        info = rag.get_graph_info()

        console.print(f"  Nodes: {len(info['nodes'])}")
        for node in info['nodes']:
            console.print(f"    • {node}")

        console.print(f"  Edges: {len(info['edges'])}")

    except Exception as e:
        console.print(f"[red]✗[/red] Error checking status: {e}")
        sys.exit(1)


@cli.command()
@click.option("--count", default=3, help="Number of sample questions")
def test(count: int):
    """
    Run sample questions to test the system.
    """
    sample_questions = [
        "What is Agentic RAG?",
        "How does document grading work?",
        "What are the main components?",
    ]

    questions = sample_questions[:count]

    console.print(Panel(
        f"[bold cyan]Running {len(questions)} test questions...[/bold cyan]",
        title="🧪 Test Mode",
        border_style="cyan"
    ))

    rag = None
    try:
        with console.status("[bold cyan]Initializing system...[/bold cyan]"):
            rag = AgenticRAGWorkflow()

        for i, question in enumerate(questions, 1):
            console.print(f"\n[bold]Test {i}/{len(questions)}[/bold]")
            ask_question(question, verbose=False, stream=False, rag=rag)

        console.print(f"\n[green]✓[/green] [bold green]All {len(questions)} tests completed![/bold green]")

    except Exception as e:
        console.print(f"[red]✗[/red] Test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli()
