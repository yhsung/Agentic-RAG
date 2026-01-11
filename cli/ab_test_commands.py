"""
A/B Testing CLI Commands for Agentic RAG System

This module provides CLI commands for running A/B tests on RAG prompt variants,
collecting user feedback, and comparing results.
"""

import time
import uuid
import click
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

from src.storage.ab_test_db import ABTestDatabase
from src.graph.workflow import AgenticRAGWorkflow
from config.prompts_ab import (
    get_prompt_variant,
    get_variant_description,
    list_prompt_variants
)
from config.settings import settings


console = Console()


@click.group(name="ab-test")
def ab_test():
    """
    A/B testing commands for prompt variant comparison.

    These commands allow you to test different RAG prompt variants,
    collect user feedback, and compare performance metrics.
    """
    pass


@ab_test.command()
@click.option(
    '--variant', '-v',
    type=click.Choice(['baseline', 'detailed', 'bullets', 'reasoning']),
    default='baseline',
    help='Prompt variant to test'
)
@click.option(
    '--questions-file', '-f',
    type=click.Path(exists=True),
    help='File containing questions to test (one per line)'
)
@click.option(
    '--count', '-n',
    default=1,
    type=int,
    help='Number of questions to test'
)
@click.option(
    '--session-id', '-s',
    default=None,
    help='Custom session ID (auto-generated if not provided)'
)
def run(variant: str, questions_file: Optional[str], count: int, session_id: Optional[str]):
    """
    Run A/B test with a specific prompt variant.

    This command executes the RAG system with the specified prompt variant
    and collects user feedback for each answer.

    Example:
        rag-cli ab-test run --variant baseline --count 5
        rag-cli ab-test run --variant detailed --questions-file questions.txt
    """
    # Generate or use provided session ID
    session_id = session_id or str(uuid.uuid4())[:8]
    db = ABTestDatabase(settings.AB_TEST_RESULTS_DB)

    # Display test configuration
    console.print(Panel.fit(
        f"[bold blue]A/B Test Session[/bold blue]\n"
        f"Variant: [bold]{variant}[/bold]\n"
        f"Session ID: [bold]{session_id}[/bold]\n"
        f"Questions: [bold]{count}[/bold]",
        title="Test Configuration"
    ))

    # Show variant description
    console.print(f"\n[bold cyan]Variant Description:[/bold cyan]")
    console.print(f"  {get_variant_description(variant)}\n")

    # Get questions
    if questions_file:
        console.print(f"[dim]Loading questions from: {questions_file}[/dim]\n")
        with open(questions_file) as f:
            questions = [line.strip() for line in f if line.strip()][:count]
    else:
        questions = []
        console.print("[bold]Interactive Mode[/bold]\n")
        for i in range(count):
            q = console.input(f"[bold]Question {i+1}/{count} (or /skip):[/bold] ")
            if not q or q.lower() == '/skip':
                break
            questions.append(q)

    if not questions:
        console.print("[yellow]No questions to process. Exiting.[/yellow]")
        return

    # Process each question
    for i, question in enumerate(questions, 1):
        console.print(f"\n{'=' * 80}")
        console.print(f"[bold]Question {i}/{len(question)}:[/bold] {question}")
        console.print('=' * 80)

        try:
            # Create workflow with variant
            workflow = AgenticRAGWorkflow(prompt_variant=variant)

            # Run and time it
            start = time.time()
            result = workflow.run(question)
            exec_time = int((time.time() - start) * 1000)

            answer = result.get("generation", "")

            # Display answer
            console.print(f"\n[green]Answer:[/green]")
            console.print(Panel(answer, title="Generated Answer", border_style="green"))

            # Display metadata
            console.print(f"\n[dim]Metadata:[/dim]")
            console.print(f"  Documents retrieved: {len(result.get('documents', []))}")
            console.print(f"  Relevant documents: {sum(1 for s in result.get('relevance_scores', []) if s == 'yes')}")
            console.print(f"  Execution time: {exec_time}ms")
            console.print(f"  Web search used: {result.get('web_search')}")
            console.print(f"  Query retries: {result.get('retry_count', 0)}")

            # Collect user feedback
            console.print(f"\n[bold yellow]Please rate this answer:[/bold yellow]")
            rating_input = console.input(
                "  Rating (1-5, or 0 to skip): ",
                show_default=False
            )
            try:
                rating = int(rating_input) if rating_input else None
                if rating and not 1 <= rating <= 5:
                    console.print("[dim]Invalid rating. Skipping feedback.[/dim]")
                    rating = None
            except ValueError:
                console.print("[dim]Invalid input. Skipping feedback.[/dim]")
                rating = None

            feedback = None
            if rating:
                feedback_input = console.input(
                    "  Additional feedback (optional, press Enter to skip): ",
                    show_default=False
                )
                feedback = feedback_input or None

            # Save to database
            db.save_test_run({
                "prompt_variant": variant,
                "question": question,
                "answer": answer,
                "user_rating": rating,
                "user_feedback": feedback,
                "documents_retrieved": len(result.get("documents", [])),
                "relevant_documents": sum(1 for s in result.get("relevance_scores", []) if s == "yes"),
                "web_search_used": result.get("web_search") == "Yes",
                "query_retries": result.get("retry_count", 0),
                "hallucination_check": result.get("hallucination_check"),
                "usefulness_check": result.get("usefulness_check"),
                "execution_time_ms": exec_time,
                "session_id": session_id
            })

            console.print(f"\n[dim]✓ Saved to database[/dim]")

        except Exception as e:
            console.print(f"\n[red]Error processing question: {e}[/red]")
            continue

    # Display summary
    console.print(f"\n{'=' * 80}")
    console.print(f"[bold green]Test session complete![/bold green]")
    console.print(f"{'=' * 80}")
    console.print(f"Session ID: [bold]{session_id}[/bold]")
    console.print(f"Variant: [bold]{variant}[/bold]")
    console.print(f"Processed: [bold]{len(questions)}[/bold] questions\n")

    # Show stats for this session
    session_runs = db.get_session_runs(session_id)
    rated_runs = [r for r in session_runs if r.get("user_rating")]
    if rated_runs:
        avg_rating = sum(r["user_rating"] for r in rated_runs) / len(rated_runs)
        console.print(f"[cyan]Session Statistics:[/cyan]")
        console.print(f"  Total runs: {len(session_runs)}")
        console.print(f"  Rated runs: {len(rated_runs)}")
        console.print(f"  Average rating: {avg_rating:.2f}/5\n")


@ab_test.command()
@click.argument('variant1')
@click.argument('variant2')
def compare(variant1: str, variant2: str):
    """
    Compare two prompt variants side-by-side.

    Displays statistics and performance metrics for two variants
    to help determine which performs better.

    Example:
        rag-cli ab-test compare baseline detailed
        rag-cli ab-test compare bullets reasoning
    """
    db = ABTestDatabase(settings.AB_TEST_RESULTS_DB)

    console.print(Panel.fit(
        f"[bold]Comparing variants:[/bold] {variant1} vs {variant2}",
        title="Variant Comparison"
    ))

    comparison = db.compare_variants(variant1, variant2)

    # Create comparison table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan", width=20)
    table.add_column(variant1, style="green", justify="right")
    table.add_column(variant2, style="blue", justify="right")
    table.add_column("Winner", style="bold yellow", justify="center")

    # Add rows
    table.add_row(
        "Total Runs",
        str(comparison[variant1]["total_runs"]),
        str(comparison[variant2]["total_runs"]),
        "-"
    )

    table.add_row(
        "Rated Runs",
        str(comparison[variant1]["rated_runs"]),
        str(comparison[variant2]["rated_runs"]),
        "-"
    )

    avg1 = comparison[variant1]["avg_rating"]
    avg2 = comparison[variant2]["avg_rating"]
    table.add_row(
        "Avg Rating (1-5)",
        f"{avg1:.2f}" if avg1 else "N/A",
        f"{avg2:.2f}" if avg2 else "N/A",
        comparison["winner"] or "-"
    )

    time1 = comparison[variant1]["avg_time_ms"]
    time2 = comparison[variant2]["avg_time_ms"]
    table.add_row(
        "Avg Time (ms)",
        f"{time1:.0f}" if time1 else "N/A",
        f"{time2:.0f}" if time2 else "N/A",
        "-"
    )

    console.print("\n", table)

    # Show variant descriptions
    console.print(f"\n[bold cyan]Variant Descriptions:[/bold cyan]")
    console.print(f"  {variant1}: {get_variant_description(variant1)}")
    console.print(f"  {variant2}: {get_variant_description(variant2)}\n")


@ab_test.command()
def stats():
    """
    Show statistics for all prompt variants.

    Displays a comprehensive table with metrics for all variants
    including total runs, ratings, and execution times.

    Example:
        rag-cli ab-test stats
    """
    db = ABTestDatabase(settings.AB_TEST_RESULTS_DB)

    all_stats = db.get_all_variant_stats()

    console.print(Panel.fit(
        "[bold]A/B Test Statistics for All Variants[/bold]",
        title="Statistics"
    ))

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Variant", style="cyan")
    table.add_column("Total Runs", justify="right")
    table.add_column("Rated Runs", justify="right")
    table.add_column("Avg Rating", justify="right")
    table.add_column("Avg Time (ms)", justify="right")
    table.add_column("Description", style="dim")

    for variant, stats in all_stats.items():
        table.add_row(
            variant,
            str(stats["total_runs"]),
            str(stats["rated_runs"]),
            f"{stats['avg_rating']:.2f}" if stats['avg_rating'] else "N/A",
            f"{stats['avg_time_ms']:.0f}" if stats['avg_time_ms'] else "N/A",
            get_variant_description(variant)
        )

    console.print("\n", table)


@ab_test.command()
@click.option(
    '--limit', '-n',
    default=10,
    type=int,
    help='Maximum number of recent runs to show'
)
@click.option(
    '--variant', '-v',
    type=click.Choice(['baseline', 'detailed', 'bullets', 'reasoning']),
    default=None,
    help='Filter by specific variant'
)
def recent(limit: int, variant: Optional[str]):
    """
    Show recent test runs.

    Displays the most recent test runs with their metadata and ratings.

    Example:
        rag-cli ab-test recent --limit 5
        rag-cli ab-test recent --variant baseline --limit 10
    """
    db = ABTestDatabase(settings.AB_TEST_RESULTS_DB)

    runs = db.get_recent_runs(limit=limit, variant=variant)

    if not runs:
        console.print("[yellow]No test runs found.[/yellow]")
        return

    title = f"Recent {limit} Test Runs"
    if variant:
        title += f" ({variant})"

    console.print(Panel.fit(
        f"[bold]{title}[/bold]",
        title="Recent Runs"
    ))

    table = Table(show_header=True, header_style="bold magenta", show_lines=True)
    table.add_column("ID", style="cyan", width=6)
    table.add_column("Variant", style="green", width=12)
    table.add_column("Question", width=40)
    table.add_column("Rating", justify="center", width=8)
    table.add_column("Time (ms)", justify="right", width=10)
    table.add_column("Session", style="dim", width=10)

    for run in runs:
        question_preview = run["question"][:37] + "..." if len(run["question"]) > 40 else run["question"]
        rating = str(run["user_rating"]) if run["user_rating"] else "-"
        exec_time = str(run["execution_time_ms"]) if run["execution_time_ms"] else "N/A"

        table.add_row(
            str(run["id"]),
            run["prompt_variant"],
            question_preview,
            rating,
            exec_time,
            run["session_id"] or "-"
        )

    console.print("\n", table)


@ab_test.command()
def variants():
    """
    List all available prompt variants with descriptions.

    Example:
        rag-cli ab-test variants
    """
    console.print(Panel.fit(
        "[bold]Available Prompt Variants[/bold]",
        title="Variants"
    ))

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Variant", style="cyan", width=15)
    table.add_column("Description", width=60)

    for variant_name in list_prompt_variants():
        table.add_row(
            variant_name,
            get_variant_description(variant_name)
        )

    console.print("\n", table)


if __name__ == "__main__":
    ab_test()
