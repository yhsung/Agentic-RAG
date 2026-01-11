# Plan: A/B Testing System for RAG Prompt Variants with User Feedback

## Overview

Implement an A/B testing framework for comparing RAG prompt variants with integrated user feedback collection. This system will allow side-by-side comparison of different answer generation strategies to optimize the most impactful prompt in the system.

**Focus**: RAG_PROMPT variants (affects every user query directly)
**Evaluation Method**: User feedback integration via CLI ratings

---

## Current State Analysis

### Current RAG Prompt
**Location**: `config/prompts.py:73-95`

```python
RAG_PROMPT = """You are an AI assistant tasked with answering questions based on retrieved context.

Question: {question}

Context:
{context}

Instructions:
1. Use ONLY the provided context to answer the question
2. If the context doesn't contain enough information, say "I don't have enough information to answer this"
3. Provide a concise answer in 2-3 sentences maximum
4. Do not make up information beyond what's in the context
5. If the context contradicts itself, acknowledge the uncertainty

Answer:"""
```

### Integration Point
**Location**: `src/agents/generator.py:62`
```python
self.rag_prompt = ChatPromptTemplate.from_template(RAG_PROMPT)
```

### Current Usage
- Executed for every query that reaches the `generate` node
- Temperature: 0.0 (deterministic)
- Model: qwen3:30b (configurable via settings)
- Output: Concise answers (2-3 sentences max)

---

## Proposed RAG Prompt Variants

### Variant A: Baseline (Current)
**Characteristics**: Concise, 2-3 sentences, factual only
**Best For**: Quick factual answers
**Focus**: Brevity and accuracy

### Variant B: Detailed Explanations
**Characteristics**: 4-6 sentences, includes reasoning
**Best For**: Complex questions requiring explanation
**Focus**: Completeness and understanding

```python
RAG_PROMPT_VARIANT_B = """You are an AI assistant tasked with answering questions based on retrieved context.

Question: {question}

Context:
{context}

Instructions:
1. Use ONLY the provided context to answer the question
2. If the context doesn't contain enough information, say "I don't have enough information to answer this"
3. Provide a detailed answer in 4-6 sentences that explains the reasoning
4. Include relevant context and background from the source material
5. Structure your answer logically: main point first, then supporting details
6. If the context contradicts itself, acknowledge the uncertainty

Answer:"""
```

### Variant C: Bullet Point Format
**Characteristics**: Structured with bullet points, easy to scan
**Best For**: Multi-part questions or comparisons
**Focus**: Readability and organization

```python
RAG_PROMPT_VARIANT_C = """You are an AI assistant tasked with answering questions based on retrieved context.

Question: {question}

Context:
{context}

Instructions:
1. Use ONLY the provided context to answer the question
2. If the context doesn't contain enough information, say "I don't have enough information to answer this"
3. Format your answer using bullet points for clarity
4. Start with a brief 1-sentence summary
5. Use 3-5 bullet points for key information
6. Each bullet should be 1-2 sentences
7. If the context contradicts itself, acknowledge the uncertainty

Answer:"""
```

### Variant D: Step-by-Step Reasoning
**Characteristics**: Shows thought process, chains reasoning
**Best For**: Complex analytical questions
**Focus**: Transparency and logic

```python
RAG_PROMPT_VARIANT_D = """You are an AI assistant tasked with answering questions based on retrieved context.

Question: {question}

Context:
{context}

Instructions:
1. Use ONLY the provided context to answer the question
2. Think through the question step-by-step:
   - Identify what the question is asking
   - Extract relevant information from context
   - Synthesize the information into an answer
3. Show your reasoning process clearly
4. Provide a final conclusion based on the reasoning
5. If the context doesn't contain enough information, say "I don't have enough information to answer this"
6. If the context contradicts itself, acknowledge the uncertainty

Answer:"""
```

---

## Implementation Plan

### Phase 1: Infrastructure Setup

#### 1.1 Create Prompt Variant System

**New File**: `config/prompts_ab.py`

```python
"""
A/B Testing Prompt Variants for RAG System
"""

from typing import Dict, Literal

# Define all prompt variants
RAG_PROMPT_VARIANTS: Dict[str, str] = {
    "baseline": RAG_PROMPT,  # Current prompt
    "detailed": RAG_PROMPT_VARIANT_B,
    "bullets": RAG_PROMPT_VARIANT_C,
    "reasoning": RAG_PROMPT_VARIANT_D,
}

PromptVariant = Literal["baseline", "detailed", "bullets", "reasoning"]

def get_prompt_variant(variant: PromptVariant = "baseline") -> str:
    """Get a specific prompt variant."""
    return RAG_PROMPT_VARIANTS.get(variant, RAG_PROMPT_VARIANTS["baseline"])

def list_prompt_variants() -> list[str]:
    """List available prompt variants."""
    return list(RAG_PROMPT_VARIANTS.keys())
```

#### 1.2 SQLite Database for Results

**New File**: `src/storage/ab_test_db.py`

```python
"""
SQLite database for A/B test results storage
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

class ABTestDatabase:
    """Manage A/B test results in SQLite."""

    def __init__(self, db_path: str = "./data/ab_test_results.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self._create_tables()

    def _create_tables(self):
        """Create database tables if they don't exist."""
        cursor = self.conn.cursor()

        # Main test results table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ab_test_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                prompt_variant TEXT NOT NULL,
                question TEXT NOT NULL,
                answer TEXT,
                user_rating INTEGER CHECK(user_rating BETWEEN 1 AND 5),
                user_feedback TEXT,
                documents_retrieved INTEGER,
                relevant_documents INTEGER,
                web_search_used BOOLEAN,
                query_retries INTEGER,
                hallucination_check TEXT,
                usefulness_check TEXT,
                execution_time_ms INTEGER,
                session_id TEXT
            )
        """)

        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_variant
            ON ab_test_runs(prompt_variant)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp
            ON ab_test_runs(timestamp)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_session
            ON ab_test_runs(session_id)
        """)

        self.conn.commit()

    def save_test_run(self, data: Dict[str, Any]) -> int:
        """Save a test run to the database."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO ab_test_runs (
                prompt_variant, question, answer, user_rating, user_feedback,
                documents_retrieved, relevant_documents, web_search_used,
                query_retries, hallucination_check, usefulness_check,
                execution_time_ms, session_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data["prompt_variant"],
            data["question"],
            data.get("answer"),
            data.get("user_rating"),
            data.get("user_feedback"),
            data.get("documents_retrieved"),
            data.get("relevant_documents"),
            data.get("web_search_used"),
            data.get("query_retries"),
            data.get("hallucination_check"),
            data.get("usefulness_check"),
            data.get("execution_time_ms"),
            data.get("session_id")
        ))
        self.conn.commit()
        return cursor.lastrowid

    def get_variant_stats(self, variant: str) -> Dict[str, Any]:
        """Get statistics for a specific variant."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT
                COUNT(*) as total_runs,
                AVG(user_rating) as avg_rating,
                COUNT(user_rating) as rated_runs,
                AVG(execution_time_ms) as avg_time_ms
            FROM ab_test_runs
            WHERE prompt_variant = ?
        """, (variant,))
        row = cursor.fetchone()
        return {
            "total_runs": row[0],
            "avg_rating": row[1],
            "rated_runs": row[2],
            "avg_time_ms": row[3]
        }

    def compare_variants(self, variant1: str, variant2: str) -> Dict[str, Any]:
        """Compare two prompt variants side-by-side."""
        stats1 = self.get_variant_stats(variant1)
        stats2 = self.get_variant_stats(variant2)
        return {
            variant1: stats1,
            variant2: stats2,
            "winner": variant1 if stats1["avg_rating"] > stats2["avg_rating"] else variant2
        }
```

#### 1.3 Configuration Updates

**File**: `config/settings.py`

Add to settings class:

```python
# A/B Testing Configuration
AB_TEST_ENABLED: bool = Field(default=False)
AB_TEST_RESULTS_DB: str = Field(default="./data/ab_test_results.db")
AB_TEST_DEFAULT_VARIANT: str = Field(default="baseline")
AB_TEST_AUTO_COLLECT: bool = Field(default=True)
AB_TEST_SESSION_ID: str = Field(default="")
```

---

### Phase 2: Agent Modifications

#### 2.1 Update AnswerGenerator

**File**: `src/agents/generator.py`

Modify the `__init__` method to accept variant parameter:

```python
def __init__(self, prompt_variant: str = "baseline"):
    """
    Initialize the AnswerGenerator.

    Args:
        prompt_variant: Which RAG prompt variant to use (baseline, detailed, bullets, reasoning)
    """
    logger.info(f"Initializing AnswerGenerator with prompt variant: {prompt_variant}")

    # Load the specified prompt variant
    from config.prompts_ab import get_prompt_variant
    rag_prompt_text = get_prompt_variant(prompt_variant)

    self.llm = ChatOllama(
        model=settings.GENERATION_MODEL,
        temperature=settings.GENERATION_TEMPERATURE
    )
    self.rag_prompt = ChatPromptTemplate.from_template(rag_prompt_text)
    self.prompt_variant = prompt_variant

    logger.info("AnswerGenerator initialized successfully")
```

---

### Phase 3: CLI Integration

#### 3.1 A/B Test Commands

**New File**: `cli/ab_test_commands.py`

```python
"""
A/B Testing CLI Commands
"""

import click
import uuid
from rich.console import Console
from rich.table import Table
from src.storage.ab_test_db import ABTestDatabase
from src.graph.workflow import AgenticRAGWorkflow
from config.settings import settings

console = Console()

@click.group()
def ab_test():
    """A/B testing commands for prompt comparison."""
    pass

@ab_test.command()
@click.option('--variant', '-v', type=click.Choice(['baseline', 'detailed', 'bullets', 'reasoning']),
              default='baseline', help='Prompt variant to test')
@click.option('--questions-file', '-f', type=click.Path(exists=True),
              help='File containing questions to test (one per line)')
@click.option('--count', '-n', default=1, help='Number of questions to test')
def run(variant, questions_file, count):
    """Run A/B test with a specific prompt variant."""
    session_id = str(uuid.uuid4())[:8]
    db = ABTestDatabase(settings.AB_TEST_RESULTS_DB)

    console.print(f"[bold blue]Starting A/B Test Session[/bold blue]")
    console.print(f"Variant: {variant}")
    console.print(f"Session ID: {session_id}\n")

    # Get questions
    if questions_file:
        with open(questions_file) as f:
            questions = [line.strip() for line in f if line.strip()][:count]
    else:
        # Interactive mode
        questions = []
        for i in range(count):
            q = console.input(f"[bold]Question {i+1}/{count}:[/bold] ")
            if not q:
                break
            questions.append(q)

    # Process each question
    for i, question in enumerate(questions, 1):
        console.print(f"\n[bold]Question {i}/{len(questions)}:[/bold] {question}")

        # Create workflow with variant
        workflow = AgenticRAGWorkflow(prompt_variant=variant)

        # Run and time it
        import time
        start = time.time()
        result = workflow.run(question)
        exec_time = int((time.time() - start) * 1000)

        answer = result.get("generation", "")
        console.print(f"[green]Answer:[/green] {answer}\n")

        # Collect user feedback
        rating = console.input(
            f"[bold yellow]Rate this answer (1-5, or 0 to skip):[/bold yellow] ",
            show_default=False
        )
        try:
            rating = int(rating) if rating else None
            if rating and not 1 <= rating <= 5:
                rating = None
        except ValueError:
            rating = None

        feedback = None
        if rating:
            feedback = console.input(
                "[bold yellow]Additional feedback (optional, press Enter to skip):[/bold yellow] ",
                show_default=False
            ) or None

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

        console.print(f"[dim]✓ Saved to database[/dim]\n")

    console.print(f"\n[bold green]Test session complete![/bold green]")
    console.print(f"Session ID: {session_id}")
    console.print(f"Processed {len(questions)} questions\n")

@ab_test.command()
@click.argument('variant1')
@click.argument('variant2')
def compare(variant1, variant2):
    """Compare two prompt variants side-by-side."""
    db = ABTestDatabase(settings.AB_TEST_RESULTS_DB)

    console.print(f"[bold]Comparing variants:[/bold] {variant1} vs {variant2}\n")

    comparison = db.compare_variants(variant1, variant2)

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan")
    table.add_column(variant1, style="green")
    table.add_column(variant2, style="blue")
    table.add_column("Winner", style="bold yellow")

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
    table.add_row(
        "Avg Rating (1-5)",
        f"{comparison[variant1]['avg_rating']:.2f}" if comparison[variant1]['avg_rating'] else "N/A",
        f"{comparison[variant2]['avg_rating']:.2f}" if comparison[variant2]['avg_rating'] else "N/A",
        comparison["winner"]
    )
    table.add_row(
        "Avg Time (ms)",
        f"{comparison[variant1]['avg_time_ms']:.0f}" if comparison[variant1]['avg_time_ms'] else "N/A",
        f"{comparison[variant2]['avg_time_ms']:.0f}" if comparison[variant2]['avg_time_ms'] else "N/A",
        "-"
    )

    console.print(table)

@ab_test.command()
def stats():
    """Show statistics for all prompt variants."""
    db = ABTestDatabase(settings.AB_TEST_RESULTS_DB)

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Variant", style="cyan")
    table.add_column("Total Runs", justify="right")
    table.add_column("Rated Runs", justify="right")
    table.add_column("Avg Rating", justify="right")
    table.add_column("Avg Time (ms)", justify="right")

    variants = ["baseline", "detailed", "bullets", "reasoning"]
    for variant in variants:
        stats = db.get_variant_stats(variant)
        table.add_row(
            variant,
            str(stats["total_runs"]),
            str(stats["rated_runs"]),
            f"{stats['avg_rating']:.2f}" if stats['avg_rating'] else "N/A",
            f"{stats['avg_time_ms']:.0f}" if stats['avg_time_ms'] else "N/A"
        )

    console.print(table)
```

#### 3.2 Update Main CLI

**File**: `cli/main.py`

Add A/B test command group:

```python
# Import the A/B test commands
from cli.ab_test_commands import ab_test

# Add to the CLI group
@click.group()
def cli():
    """Agentic RAG System CLI."""
    pass

# Register the A/B test commands
cli.add_command(ab_test)

# Also add simple shortcut for interactive A/B testing
@cli.command()
@click.option('--variant', '-v', type=click.Choice(['baseline', 'detailed', 'bullets', 'reasoning']),
              default='baseline', help='Prompt variant to use')
def query_ab(variant):
    """Interactive query mode with A/B testing enabled."""
    session_id = str(uuid.uuid4())[:8]
    console.print(f"[bold blue]A/B Testing Mode - Variant: {variant}[/bold blue]")
    console.print(f"[dim]Session ID: {session_id}[/dim]\n")

    db = ABTestDatabase(settings.AB_TEST_RESULTS_DB)
    workflow = AgenticRAGWorkflow(prompt_variant=variant)

    while True:
        question = console.input("\n[bold]Question (or /exit):[/bold] ")
        if question.lower() in ['/exit', '/quit', 'q']:
            break

        if not question.strip():
            continue

        # Process question
        import time
        start = time.time()
        result = workflow.run(question)
        exec_time = int((time.time() - start) * 1000)

        answer = result.get("generation", "")
        console.print(f"\n[green]Answer:[/green] {answer}")

        # Show metadata
        console.print("\n[dim]Metadata:[/dim]")
        console.print(f"  Documents: {len(result.get('documents', []))}")
        console.print(f"  Relevant: {sum(1 for s in result.get('relevance_scores', []) if s == 'yes')}")
        console.print(f"  Time: {exec_time}ms")
        console.print(f"  Web Search: {result.get('web_search')}")

        # Collect feedback
        console.print("\n[yellow]Please rate this answer:[/yellow]")
        rating = console.input("  Rating (1-5, or 0 to skip): ", show_default=False)
        try:
            rating = int(rating) if rating else None
            if rating and not 1 <= rating <= 5:
                rating = None
        except ValueError:
            rating = None

        if rating:
            feedback = console.input("  Feedback (optional): ", show_default=False) or None

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
            console.print("[dim]✓ Feedback saved[/dim]")
```

---

### Phase 4: Workflow Modifications

#### 4.1 Update AgenticRAGWorkflow

**File**: `src/graph/workflow.py`

Modify the workflow to support prompt variants:

```python
class AgenticRAGWorkflow:
    """
    Manages the LangGraph StateGraph for the Agentic RAG system.
    """

    def __init__(self, prompt_variant: str = "baseline"):
        """
        Initialize and build the Agentic RAG workflow.

        Args:
            prompt_variant: Which RAG prompt variant to use for generation
        """
        logger.info(f"Initializing Agentic RAG workflow with variant: {prompt_variant}")
        self.prompt_variant = prompt_variant
        self.workflow = self._build_workflow()
        logger.info("Agentic RAG workflow initialized successfully")
```

Then pass the variant to nodes when needed (or use a global/context approach).

---

## Verification Plan

### 1. Unit Tests

**New File**: `tests/test_ab_test_system.py`

```python
"""
Tests for A/B testing system
"""

import pytest
from src.storage.ab_test_db import ABTestDatabase
from config.prompts_ab import get_prompt_variant, list_prompt_variants

def test_prompt_variants_exist():
    """Test that all prompt variants are defined."""
    variants = list_prompt_variants()
    assert "baseline" in variants
    assert "detailed" in variants
    assert "bullets" in variants
    assert "reasoning" in variants

def test_get_prompt_variant():
    """Test retrieving specific prompt variants."""
    baseline = get_prompt_variant("baseline")
    assert "2-3 sentences maximum" in baseline

    detailed = get_prompt_variant("detailed")
    assert "4-6 sentences" in detailed

    bullets = get_prompt_variant("bullets")
    assert "bullet points" in bullets

    reasoning = get_prompt_variant("reasoning")
    assert "step-by-step" in reasoning

def test_database_initialization(tmp_path):
    """Test database creates tables correctly."""
    db_path = tmp_path / "test.db"
    db = ABTestDatabase(str(db_path))

    # Check table exists
    cursor = db.conn.cursor()
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='ab_test_runs'
    """)
    assert cursor.fetchone() is not None

def test_save_and_retrieve_test_run(tmp_path):
    """Test saving and retrieving test runs."""
    db = ABTestDatabase(str(tmp_path / "test.db"))

    # Save a test run
    data = {
        "prompt_variant": "baseline",
        "question": "Test question",
        "answer": "Test answer",
        "user_rating": 5,
        "documents_retrieved": 4,
        "relevant_documents": 3
    }
    run_id = db.save_test_run(data)
    assert run_id > 0

    # Retrieve stats
    stats = db.get_variant_stats("baseline")
    assert stats["total_runs"] == 1
    assert stats["avg_rating"] == 5.0
```

### 2. Integration Tests

Test the full A/B testing flow:

```bash
# Test baseline variant
python cli/main.py ab-test run --variant baseline --count 3

# Test detailed variant
python cli/main.py ab-test run --variant detailed --count 3

# Compare variants
python cli/main.py ab-test compare baseline detailed

# Show all stats
python cli/main.py ab-test stats
```

### 3. Manual Testing

**Interactive A/B Testing**:
```bash
# Start interactive A/B test mode with baseline
python cli/main.py query-ab --variant baseline

# Ask 5-10 questions, rate each answer
# Then switch to another variant
python cli/main.py query-ab --variant detailed

# Compare results
python cli/main.py ab-test compare baseline detailed
```

**Expected Behavior**:
- System tracks all questions and answers
- User is prompted for rating after each answer
- Results saved to database automatically
- Comparison shows average ratings and execution times

### 4. Evaluation Criteria

**Success Metrics**:
- ✅ Database creates and saves test runs correctly
- ✅ All 4 prompt variants are accessible
- ✅ User feedback is collected and stored
- ✅ Comparison commands show accurate statistics
- ✅ Interactive mode flows smoothly
- ✅ Each variant produces distinctly different answers

---

## File Structure

### New Files
```
├── config/
│   └── prompts_ab.py              # Prompt variant definitions
├── src/
│   └── storage/
│       └── ab_test_db.py          # SQLite database operations
├── cli/
│   └── ab_test_commands.py        # A/B test CLI commands
├── data/
│   ├── ab_test_results.db         # SQLite database (auto-created)
│   └── ab_tests/                  # Test exports (optional)
└── tests/
    └── test_ab_test_system.py     # A/B test unit tests
```

### Modified Files
```
├── config/settings.py             # Add AB test configuration
├── src/agents/generator.py        # Accept prompt_variant parameter
├── src/graph/workflow.py          # Pass variant through workflow
└── cli/main.py                    # Add A/B test commands
```

---

## Implementation Order

### Step 1: Core Infrastructure (Priority: HIGH)
1. Create `config/prompts_ab.py` with 4 prompt variants
2. Create `src/storage/ab_test_db.py` with database operations
3. Update `config/settings.py` with AB test settings
4. Write unit tests for database and prompt variants

### Step 2: Agent Integration (Priority: HIGH)
1. Modify `src/agents/generator.py` to accept variant parameter
2. Modify `src/graph/workflow.py` to pass variant to generator
3. Write integration tests for variant selection

### Step 3: CLI Interface (Priority: HIGH)
1. Create `cli/ab_test_commands.py` with all A/B test commands
2. Update `cli/main.py` to register A/B test commands
3. Add `query-ab` command for interactive testing
4. Test CLI commands manually

### Step 4: Documentation (Priority: MEDIUM)
1. Update README.md with A/B testing usage
2. Add A/B testing section to PROJECT_COMPLETE.md
3. Create example questions file for testing

---

## Estimated Complexity

- **New Code**: ~600 lines (database: 200, prompts: 150, CLI: 250)
- **Modified Code**: ~50 lines across 4 files
- **Tests**: ~150 lines
- **Documentation**: ~100 lines

**Difficulty Level**: ⭐⭐⭐ Medium (involves database, CLI, and prompt engineering)

**Time Estimate**: 4-6 hours for full implementation

---

## Success Criteria

✅ **Infrastructure**:
- [ ] 4 prompt variants defined and accessible
- [ ] SQLite database creates and saves results
- [ ] Configuration settings added

✅ **Integration**:
- [ ] AnswerGenerator accepts variant parameter
- [ ] Workflow passes variant correctly
- [ ] Different variants produce different outputs

✅ **CLI Commands**:
- [ ] `ab-test run` executes tests with feedback collection
- [ ] `ab-test compare` shows side-by-side statistics
- [ ] `ab-test stats` displays all variant metrics
- [ ] `query-ab` provides interactive testing mode

✅ **Testing**:
- [ ] All unit tests pass
- [ ] Manual testing completes successfully
- [ ] User feedback saves to database

✅ **Documentation**:
- [ ] README updated with A/B testing instructions
- [ ] Example questions file provided
- [ ] Usage examples documented

---

## Future Enhancements

After initial implementation:

1. **Statistical Analysis**: Add significance testing (t-test, Mann-Whitney U)
2. **Visualization**: Generate graphs comparing variant performance
3. **Automated Evaluation**: Add LLM-based answer quality scoring
4. **Multi-Variant Testing**: Test more than 2 variants simultaneously
5. **Export Features**: CSV/JSON export of test results
6. **Dashboard**: Web-based dashboard for monitoring A/B tests
7. **Advanced Prompts**: Add more sophisticated prompt variants
8. **Context-Aware Variants**: Different prompts for different question types
