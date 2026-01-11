"""
Unit Tests for A/B Testing System

This module tests the A/B testing infrastructure including:
- Prompt variant definitions
- Database operations
- Statistics and comparison functions
"""

import pytest
import tempfile
from pathlib import Path

from config.prompts_ab import (
    get_prompt_variant,
    list_prompt_variants,
    get_variant_description,
    RAG_PROMPT_VARIANTS,
    PromptVariant
)
from src.storage.ab_test_db import ABTestDatabase


class TestPromptVariants:
    """Test prompt variant definitions and helper functions."""

    def test_list_prompt_variants(self):
        """Test that all expected variants are defined."""
        variants = list_prompt_variants()

        assert isinstance(variants, list)
        assert len(variants) == 4
        assert "baseline" in variants
        assert "detailed" in variants
        assert "bullets" in variants
        assert "reasoning" in variants

    def test_get_prompt_variant_baseline(self):
        """Test retrieving the baseline prompt variant."""
        prompt = get_prompt_variant("baseline")

        assert isinstance(prompt, str)
        assert len(prompt) > 0
        # Baseline should mention concise/3 sentences
        assert "three sentences maximum" in prompt.lower() or "2-3 sentences" in prompt.lower()

    def test_get_prompt_variant_detailed(self):
        """Test retrieving the detailed prompt variant."""
        prompt = get_prompt_variant("detailed")

        assert isinstance(prompt, str)
        assert len(prompt) > 0
        # Detailed should mention 4-6 sentences
        assert "4-6 sentences" in prompt.lower()

    def test_get_prompt_variant_bullets(self):
        """Test retrieving the bullet points prompt variant."""
        prompt = get_prompt_variant("bullets")

        assert isinstance(prompt, str)
        assert len(prompt) > 0
        # Bullets should mention bullet points
        assert "bullet point" in prompt.lower()

    def test_get_prompt_variant_reasoning(self):
        """Test retrieving the reasoning prompt variant."""
        prompt = get_prompt_variant("reasoning")

        assert isinstance(prompt, str)
        assert len(prompt) > 0
        # Reasoning should mention step-by-step
        assert "step-by-step" in prompt.lower() or "step by step" in prompt.lower()

    def test_get_prompt_variant_invalid(self):
        """Test that invalid variant returns baseline."""
        prompt = get_prompt_variant("invalid_variant")

        # Should fallback to baseline
        baseline_prompt = get_prompt_variant("baseline")
        assert prompt == baseline_prompt

    def test_get_variant_descriptions(self):
        """Test retrieving variant descriptions."""
        variants = list_prompt_variants()

        for variant in variants:
            description = get_variant_description(variant)

            assert isinstance(description, str)
            assert len(description) > 0
            # Description should be meaningful
            assert len(description) > 20

    def test_prompt_variants_dictionary(self):
        """Test that the RAG_PROMPT_VARIANTS dictionary is complete."""
        assert isinstance(RAG_PROMPT_VARIANTS, dict)
        assert len(RAG_PROMPT_VARIANTS) == 4

        for variant_name in list_prompt_variants():
            assert variant_name in RAG_PROMPT_VARIANTS
            assert isinstance(RAG_PROMPT_VARIANTS[variant_name], str)
            assert len(RAG_PROMPT_VARIANTS[variant_name]) > 0


class TestABTestDatabase:
    """Test A/B testing database operations."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = ABTestDatabase(str(db_path))
            yield db
            db.close()

    def test_database_initialization(self, temp_db):
        """Test that database initializes correctly."""
        assert temp_db.conn is not None
        assert temp_db.db_path.exists()

        # Check that tables exist
        cursor = temp_db.conn.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='ab_test_runs'
        """)
        result = cursor.fetchone()
        assert result is not None

    def test_save_test_run_minimal(self, temp_db):
        """Test saving a test run with minimal required fields."""
        data = {
            "prompt_variant": "baseline",
            "question": "Test question?"
        }

        run_id = temp_db.save_test_run(data)

        assert run_id > 0
        assert isinstance(run_id, int)

    def test_save_test_run_complete(self, temp_db):
        """Test saving a test run with all fields."""
        data = {
            "prompt_variant": "detailed",
            "question": "What is Agentic RAG?",
            "answer": "Agentic RAG is a system with self-correction.",
            "user_rating": 5,
            "user_feedback": "Great answer!",
            "documents_retrieved": 4,
            "relevant_documents": 3,
            "web_search_used": False,
            "query_retries": 0,
            "hallucination_check": "grounded",
            "usefulness_check": "useful",
            "execution_time_ms": 2500,
            "session_id": "test_session_123"
        }

        run_id = temp_db.save_test_run(data)

        assert run_id > 0

        # Verify the data was saved correctly
        stats = temp_db.get_variant_stats("detailed")
        assert stats["total_runs"] == 1
        assert stats["rated_runs"] == 1
        assert stats["avg_rating"] == 5.0

    def test_save_multiple_test_runs(self, temp_db):
        """Test saving multiple test runs for the same variant."""
        runs = [
            {
                "prompt_variant": "baseline",
                "question": "Question 1?",
                "user_rating": 4,
                "execution_time_ms": 2000
            },
            {
                "prompt_variant": "baseline",
                "question": "Question 2?",
                "user_rating": 5,
                "execution_time_ms": 2500
            },
            {
                "prompt_variant": "baseline",
                "question": "Question 3?",
                "user_rating": 3,
                "execution_time_ms": 3000
            }
        ]

        for run in runs:
            temp_db.save_test_run(run)

        stats = temp_db.get_variant_stats("baseline")
        assert stats["total_runs"] == 3
        assert stats["rated_runs"] == 3
        assert stats["avg_rating"] == 4.0  # (4 + 5 + 3) / 3

    def test_get_variant_stats_empty(self, temp_db):
        """Test getting stats for a variant with no data."""
        stats = temp_db.get_variant_stats("detailed")

        assert stats["total_runs"] == 0
        assert stats["rated_runs"] == 0
        assert stats["avg_rating"] is None
        assert stats["avg_time_ms"] is None

    def test_compare_variants(self, temp_db):
        """Test comparing two variants side-by-side."""
        # Add data for baseline
        for i in range(3):
            temp_db.save_test_run({
                "prompt_variant": "baseline",
                "question": f"Question {i}?",
                "user_rating": 4,
                "execution_time_ms": 2000
            })

        # Add data for detailed
        for i in range(2):
            temp_db.save_test_run({
                "prompt_variant": "detailed",
                "question": f"Question {i}?",
                "user_rating": 5,
                "execution_time_ms": 3000
            })

        comparison = temp_db.compare_variants("baseline", "detailed")

        assert "baseline" in comparison
        assert "detailed" in comparison
        assert "winner" in comparison

        assert comparison["baseline"]["total_runs"] == 3
        assert comparison["detailed"]["total_runs"] == 2
        assert comparison["winner"] == "detailed"  # 5.0 > 4.0

    def test_compare_variants_no_data(self, temp_db):
        """Test comparing variants when no data exists."""
        comparison = temp_db.compare_variants("baseline", "detailed")

        assert comparison["baseline"]["total_runs"] == 0
        assert comparison["detailed"]["total_runs"] == 0
        assert comparison["winner"] is None

    def test_compare_variants_one_sided(self, temp_db):
        """Test comparing when only one variant has data."""
        temp_db.save_test_run({
            "prompt_variant": "baseline",
            "question": "Test?",
            "user_rating": 4
        })

        comparison = temp_db.compare_variants("baseline", "detailed")

        assert comparison["baseline"]["total_runs"] == 1
        assert comparison["detailed"]["total_runs"] == 0
        assert comparison["winner"] == "baseline"

    def test_get_all_variant_stats(self, temp_db):
        """Test getting statistics for all variants."""
        # Add data for multiple variants
        variants_to_test = ["baseline", "detailed", "bullets", "reasoning"]

        for variant in variants_to_test:
            temp_db.save_test_run({
                "prompt_variant": variant,
                "question": f"Test for {variant}?",
                "user_rating": 4,
                "execution_time_ms": 2500
            })

        all_stats = temp_db.get_all_variant_stats()

        assert isinstance(all_stats, dict)
        assert len(all_stats) == 4

        for variant in variants_to_test:
            assert variant in all_stats
            assert all_stats[variant]["total_runs"] == 1
            assert all_stats[variant]["avg_rating"] == 4.0

    def test_get_recent_runs(self, temp_db):
        """Test retrieving recent test runs."""
        # Add multiple test runs
        for i in range(10):
            temp_db.save_test_run({
                "prompt_variant": "baseline",
                "question": f"Question {i}?",
                "user_rating": i % 5 + 1
            })

        # Get default limit (10)
        recent = temp_db.get_recent_runs()
        assert len(recent) == 10

        # Get limited results
        recent_limited = temp_db.get_recent_runs(limit=5)
        assert len(recent_limited) == 5

        # Verify ordering (most recent first)
        assert recent[0]["id"] > recent[-1]["id"]

    def test_get_recent_runs_filtered(self, temp_db):
        """Test retrieving recent runs filtered by variant."""
        # Add data for multiple variants
        for i in range(5):
            temp_db.save_test_run({
                "prompt_variant": "baseline",
                "question": f"Baseline question {i}?"
            })
            temp_db.save_test_run({
                "prompt_variant": "detailed",
                "question": f"Detailed question {i}?"
            })

        # Filter by baseline
        baseline_runs = temp_db.get_recent_runs(limit=10, variant="baseline")
        assert len(baseline_runs) == 5
        assert all(r["prompt_variant"] == "baseline" for r in baseline_runs)

        # Filter by detailed
        detailed_runs = temp_db.get_recent_runs(limit=10, variant="detailed")
        assert len(detailed_runs) == 5
        assert all(r["prompt_variant"] == "detailed" for r in detailed_runs)

    def test_get_session_runs(self, temp_db):
        """Test retrieving all runs for a specific session."""
        session_id = "test_session_abc"

        # Add runs for the session
        for i in range(3):
            temp_db.save_test_run({
                "prompt_variant": "baseline",
                "question": f"Question {i}?",
                "session_id": session_id
            })

        # Add a run for different session
        temp_db.save_test_run({
            "prompt_variant": "baseline",
            "question": "Other question?",
            "session_id": "other_session"
        })

        # Get runs for the session
        session_runs = temp_db.get_session_runs(session_id)

        assert len(session_runs) == 3
        assert all(r["session_id"] == session_id for r in session_runs)

    def test_database_context_manager(self):
        """Test using database as a context manager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"

            with ABTestDatabase(str(db_path)) as db:
                # Database should be initialized
                assert db.conn is not None

                # Add a test run
                db.save_test_run({
                    "prompt_variant": "baseline",
                    "question": "Test?"
                })

            # Database should be closed after context
            # Note: We can't easily test if connection is closed
            # without accessing private attributes, so we just
            # verify the context manager works without errors


class TestIntegration:
    """Integration tests for A/B testing system."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = ABTestDatabase(str(db_path))
            yield db
            db.close()

    def test_end_to_end_workflow(self, temp_db):
        """Test a complete A/B test workflow."""
        # Simulate testing multiple variants
        variants = ["baseline", "detailed"]
        questions = [
            "What is Agentic RAG?",
            "How does document grading work?"
        ]

        for variant in variants:
            for question in questions:
                temp_db.save_test_run({
                    "prompt_variant": variant,
                    "question": question,
                    "answer": f"Answer for {variant}: {question}",
                    "user_rating": 4 if variant == "baseline" else 5,
                    "documents_retrieved": 4,
                    "relevant_documents": 3,
                    "web_search_used": False,
                    "query_retries": 0,
                    "execution_time_ms": 2500 if variant == "baseline" else 3000,
                    "session_id": f"session_{variant}"
                })

        # Verify statistics
        for variant in variants:
            stats = temp_db.get_variant_stats(variant)
            assert stats["total_runs"] == 2
            assert stats["rated_runs"] == 2

        # Compare variants
        comparison = temp_db.compare_variants("baseline", "detailed")
        assert comparison["winner"] == "detailed"

        # Get all stats
        all_stats = temp_db.get_all_variant_stats()
        assert len(all_stats) == 4  # All 4 variants


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
