"""
SQLite database for A/B test results storage.

This module handles all database operations for storing and retrieving
A/B test results for prompt variant comparison.
"""

import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class ABTestDatabase:
    """
    Manage A/B test results in SQLite database.

    This class provides methods to save test runs, retrieve statistics,
    and compare different prompt variants.
    """

    def __init__(self, db_path: str = "./data/ab_test_results.db"):
        """
        Initialize the database connection and create tables.

        Args:
            db_path: Path to SQLite database file (will be created if doesn't exist)

        Example:
            >>> db = ABTestDatabase("./data/test_results.db")
            >>> # Use database...
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Initializing A/B test database at: {self.db_path}")

        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row  # Enable row factory for dict-like access

        self._create_tables()
        logger.info("A/B test database initialized successfully")

    def _create_tables(self):
        """
        Create database tables if they don't exist.

        Creates the main ab_test_runs table and indexes for efficient querying.
        """
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

        # Create indexes for common queries
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

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_rating
            ON ab_test_runs(user_rating)
        """)

        self.conn.commit()
        logger.debug("Database tables and indexes created")

    def save_test_run(self, data: Dict[str, Any]) -> int:
        """
        Save a test run to the database.

        Args:
            data: Dictionary containing test run data with keys:
                - prompt_variant (required): str
                - question (required): str
                - answer (optional): str
                - user_rating (optional): int (1-5)
                - user_feedback (optional): str
                - documents_retrieved (optional): int
                - relevant_documents (optional): int
                - web_search_used (optional): bool
                - query_retries (optional): int
                - hallucination_check (optional): str
                - usefulness_check (optional): str
                - execution_time_ms (optional): int
                - session_id (optional): str

        Returns:
            The ID of the inserted row

        Example:
            >>> db = ABTestDatabase()
            >>> run_id = db.save_test_run({
            ...     "prompt_variant": "baseline",
            ...     "question": "What is LangGraph?",
            ...     "answer": "LangGraph is a library...",
            ...     "user_rating": 5
            ... })
            >>> assert run_id > 0
        """
        cursor = self.conn.cursor()

        try:
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
                1 if data.get("web_search_used") else 0,  # Convert bool to int
                data.get("query_retries"),
                data.get("hallucination_check"),
                data.get("usefulness_check"),
                data.get("execution_time_ms"),
                data.get("session_id")
            ))

            self.conn.commit()
            run_id = cursor.lastrowid

            logger.debug(f"Saved test run {run_id} for variant '{data['prompt_variant']}'")
            return run_id

        except sqlite3.Error as e:
            logger.error(f"Failed to save test run: {e}")
            self.conn.rollback()
            raise

    def get_variant_stats(self, variant: str) -> Dict[str, Any]:
        """
        Get statistics for a specific prompt variant.

        Args:
            variant: The prompt variant name (baseline, detailed, bullets, reasoning)

        Returns:
            Dictionary with statistics:
                - total_runs: Total number of test runs
                - rated_runs: Number of runs with user ratings
                - avg_rating: Average user rating (1-5) or None
                - avg_time_ms: Average execution time in milliseconds or None

        Example:
            >>> db = ABTestDatabase()
            >>> stats = db.get_variant_stats("baseline")
            >>> stats["total_runs"] >= 0
            True
        """
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
            "total_runs": row["total_runs"],
            "avg_rating": round(row["avg_rating"], 2) if row["avg_rating"] else None,
            "rated_runs": row["rated_runs"],
            "avg_time_ms": round(row["avg_time_ms"], 2) if row["avg_time_ms"] else None
        }

    def compare_variants(self, variant1: str, variant2: str) -> Dict[str, Any]:
        """
        Compare two prompt variants side-by-side.

        Args:
            variant1: First variant name
            variant2: Second variant name

        Returns:
            Dictionary with comparison data:
                - variant1: Stats for first variant
                - variant2: Stats for second variant
                - winner: Which variant has higher average rating

        Example:
            >>> db = ABTestDatabase()
            >>> comparison = db.compare_variants("baseline", "detailed")
            >>> "winner" in comparison
            True
        """
        stats1 = self.get_variant_stats(variant1)
        stats2 = self.get_variant_stats(variant2)

        # Determine winner based on average rating
        # If both have no ratings, winner is None
        if stats1["avg_rating"] is None and stats2["avg_rating"] is None:
            winner = None
        elif stats1["avg_rating"] is None:
            winner = variant2
        elif stats2["avg_rating"] is None:
            winner = variant1
        else:
            winner = variant1 if stats1["avg_rating"] > stats2["avg_rating"] else variant2

        return {
            variant1: stats1,
            variant2: stats2,
            "winner": winner
        }

    def get_all_variant_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        Get statistics for all prompt variants.

        Returns:
            Dictionary mapping variant names to their statistics

        Example:
            >>> db = ABTestDatabase()
            >>> all_stats = db.get_all_variant_stats()
            >>> "baseline" in all_stats
            True
        """
        variants = ["baseline", "detailed", "bullets", "reasoning"]
        return {variant: self.get_variant_stats(variant) for variant in variants}

    def get_recent_runs(self, limit: int = 10, variant: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get recent test runs.

        Args:
            limit: Maximum number of runs to return
            variant: Optional filter by specific variant

        Returns:
            List of test run dictionaries

        Example:
            >>> db = ABTestDatabase()
            >>> recent = db.get_recent_runs(limit=5)
            >>> len(recent) <= 5
            True
        """
        cursor = self.conn.cursor()

        if variant:
            cursor.execute("""
                SELECT * FROM ab_test_runs
                WHERE prompt_variant = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (variant, limit))
        else:
            cursor.execute("""
                SELECT * FROM ab_test_runs
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))

        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def get_session_runs(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get all test runs for a specific session.

        Args:
            session_id: Session identifier

        Returns:
            List of test run dictionaries

        Example:
            >>> db = ABTestDatabase()
            >>> runs = db.get_session_runs("abc123")
            >>> all(r["session_id"] == "abc123" for r in runs)
            True
        """
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT * FROM ab_test_runs
            WHERE session_id = ?
            ORDER BY timestamp ASC
        """, (session_id,))

        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def close(self):
        """
        Close the database connection.

        Example:
            >>> db = ABTestDatabase()
            >>> # ... use database ...
            >>> db.close()
        """
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


if __name__ == "__main__":
    """Test the database module."""
    import tempfile

    # Create temporary database for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = f"{tmpdir}/test.db"

        print("Creating test database...")
        db = ABTestDatabase(db_path)

        # Add sample data
        print("Adding sample test runs...")

        sample_runs = [
            {
                "prompt_variant": "baseline",
                "question": "What is LangGraph?",
                "answer": "LangGraph is a library for building agents.",
                "user_rating": 4,
                "documents_retrieved": 4,
                "relevant_documents": 3,
                "web_search_used": False,
                "query_retries": 0,
                "execution_time_ms": 2500,
                "session_id": "test1"
            },
            {
                "prompt_variant": "baseline",
                "question": "What is RAG?",
                "answer": "RAG stands for Retrieval-Augmented Generation.",
                "user_rating": 5,
                "documents_retrieved": 3,
                "relevant_documents": 3,
                "web_search_used": False,
                "query_retries": 0,
                "execution_time_ms": 2000,
                "session_id": "test1"
            },
            {
                "prompt_variant": "detailed",
                "question": "What is LangGraph?",
                "answer": "LangGraph is a sophisticated library designed for building stateful, multi-actor applications with large language models...",
                "user_rating": 5,
                "documents_retrieved": 4,
                "relevant_documents": 3,
                "web_search_used": False,
                "query_retries": 0,
                "execution_time_ms": 3500,
                "session_id": "test2"
            }
        ]

        for run in sample_runs:
            db.save_test_run(run)

        # Test statistics
        print("\nBaseline Stats:")
        baseline_stats = db.get_variant_stats("baseline")
        for key, value in baseline_stats.items():
            print(f"  {key}: {value}")

        print("\nDetailed Stats:")
        detailed_stats = db.get_variant_stats("detailed")
        for key, value in detailed_stats.items():
            print(f"  {key}: {value}")

        # Test comparison
        print("\nComparison:")
        comparison = db.compare_variants("baseline", "detailed")
        print(f"  Baseline avg rating: {comparison['baseline']['avg_rating']}")
        print(f"  Detailed avg rating: {comparison['detailed']['avg_rating']}")
        print(f"  Winner: {comparison['winner']}")

        db.close()
        print("\nDatabase test complete!")
