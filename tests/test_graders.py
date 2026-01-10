"""
Unit tests for all grader agents.

Tests cover:
- DocumentGrader (document relevance)
- HallucinationGrader (answer grounding)
- AnswerGrader (answer usefulness)
"""

import pytest
from langchain_core.documents import Document

from src.agents.graders import (
    DocumentGrader,
    HallucinationGrader,
    AnswerGrader
)


class TestDocumentGrader:
    """Test DocumentGrader for document relevance evaluation."""

    @pytest.fixture
    def grader(self):
        """Create a DocumentGrader instance."""
        return DocumentGrader()

    def test_initialization(self, grader):
        """Test that DocumentGrader initializes correctly."""
        assert grader is not None
        assert grader.llm is not None

    def test_relevant_document(self, grader):
        """Test grading a relevant document."""
        question = "What is LangGraph?"
        document = Document(
            page_content="LangGraph is a library for building stateful, multi-actor applications with LLMs.",
            metadata={"source": "test1"}
        )

        result = grader.grade(question, document)

        # Should return "yes" or "no"
        assert result in ["yes", "no"]
        # For relevant document, expect "yes"
        assert result == "yes"

    def test_irrelevant_document(self, grader):
        """Test grading an irrelevant document."""
        question = "What is Python programming?"
        document = Document(
            page_content="LangGraph is a library for building stateful, multi-actor applications with LLMs.",
            metadata={"source": "test1"}
        )

        result = grader.grade(question, document)

        # Should return "yes" or "no"
        assert result in ["yes", "no"]
        # For irrelevant document, expect "no"
        assert result == "no"

    def test_keyword_match(self, grader):
        """Test that keyword matching works."""
        question = "What is LangGraph?"
        document = Document(
            page_content="LangGraph provides a state machine for agents.",
            metadata={"source": "test2"}
        )

        result = grader.grade(question, document)

        # Keyword "LangGraph" in both should be relevant
        assert result == "yes"

    def test_semantic_relevance(self, grader):
        """Test semantic relevance without keyword match."""
        question = "How do I build agents with LLMs?"
        document = Document(
            page_content="LangGraph enables the creation of stateful, multi-actor applications using large language models.",
            metadata={"source": "test3"}
        )

        result = grader.grade(question, document)

        # Semantically relevant even without exact keyword
        assert result == "yes"


class TestHallucinationGrader:
    """Test HallucinationGrader for answer grounding verification."""

    @pytest.fixture
    def grader(self):
        """Create a HallucinationGrader instance."""
        return HallucinationGrader()

    def test_initialization(self, grader):
        """Test that HallucinationGrader initializes correctly."""
        assert grader is not None
        assert grader.llm is not None

    def test_grounded_answer(self, grader):
        """Test grading a grounded answer."""
        generation = "LangGraph is used for building agent workflows."
        documents = [
            Document(
                page_content="LangGraph is a library for building stateful applications.",
                metadata={"source": "test1"}
            ),
            Document(
                page_content="Agents use LangGraph for workflow management.",
                metadata={"source": "test2"}
            )
        ]

        result = grader.grade(generation, documents)

        # Should return "yes" or "no"
        assert result in ["yes", "no"]
        # Grounded answer should return "yes"
        assert result == "yes"

    def test_hallucinated_answer(self, grader):
        """Test grading a hallucinated answer."""
        generation = "LangGraph was created in 2050 by aliens from Mars."
        documents = [
            Document(
                page_content="LangGraph is a library for building stateful applications.",
                metadata={"source": "test1"}
            )
        ]

        result = grader.grade(generation, documents)

        # Should return "yes" or "no"
        assert result in ["yes", "no"]
        # Hallucinated answer should return "no"
        assert result == "no"

    def test_partial_grounding(self, grader):
        """Test grading an answer with partial grounding."""
        generation = "LangGraph is a library for building agents (true) and was created by Google (false)."
        documents = [
            Document(
                page_content="LangGraph is a library for building agents.",
                metadata={"source": "test1"}
            )
        ]

        result = grader.grade(generation, documents)

        # Partial grounding should still be detected as not fully grounded
        assert result == "no"

    def test_no_documents(self, grader):
        """Test grading with no documents."""
        generation = "LangGraph is a library."
        documents = []

        # Should handle gracefully
        result = grader.grade(generation, documents)
        assert result == "no"  # No docs = not grounded


class TestAnswerGrader:
    """Test AnswerGrader for answer usefulness evaluation."""

    @pytest.fixture
    def grader(self):
        """Create an AnswerGrader instance."""
        return AnswerGrader()

    def test_initialization(self, grader):
        """Test that AnswerGrader initializes correctly."""
        assert grader is not None
        assert grader.llm is not None

    def test_useful_answer(self, grader):
        """Test grading a useful answer."""
        question = "What is LangGraph?"
        generation = "LangGraph is a library for building stateful, multi-actor applications with LLMs, enabling complex agent workflows."

        result = grader.grade(question, generation)

        # Should return "yes" or "no"
        assert result in ["yes", "no"]
        # Useful answer should return "yes"
        assert result == "yes"

    def test_not_useful_answer(self, grader):
        """Test grading a not useful answer."""
        question = "What is LangGraph?"
        generation = "I don't know."

        result = grader.grade(question, generation)

        # Should return "yes" or "no"
        assert result in ["yes", "no"]
        # Not useful answer should return "no"
        assert result == "no"

    def test_irrelevant_answer(self, grader):
        """Test grading an irrelevant answer."""
        question = "How does document grading work?"
        generation = "Python is a programming language created by Guido van Rossum."

        result = grader.grade(question, generation)

        # Should return "yes" or "no"
        assert result in ["yes", "no"]
        # Irrelevant answer should return "no"
        assert result == "no"

    def test_incomplete_answer(self, grader):
        """Test grading an incomplete answer."""
        question = "Explain the complete workflow of the system."
        generation = "The system has multiple components."

        result = grader.grade(question, generation)

        # Incomplete answer should return "no"
        assert result == "no"


class TestGraderIntegration:
    """Integration tests for multiple graders working together."""

    @pytest.fixture
    def doc_grader(self):
        """Create DocumentGrader."""
        return DocumentGrader()

    @pytest.fixture
    def hallucination_grader(self):
        """Create HallucinationGrader."""
        return HallucinationGrader()

    @pytest.fixture
    def answer_grader(self):
        """Create AnswerGrader."""
        return AnswerGrader()

    def test_full_grading_pipeline(self, doc_grader, hallucination_grader, answer_grader):
        """Test complete grading pipeline."""
        question = "What is LangGraph?"

        # Step 1: Grade documents
        documents = [
            Document(
                page_content="LangGraph is a library for building agents.",
                metadata={"source": "test1"}
            ),
            Document(
                page_content="Python is a programming language.",
                metadata={"source": "test2"}
            )
        ]

        relevance_scores = []
        for doc in documents:
            score = doc_grader.grade(question, doc)
            relevance_scores.append(score)

        # Should have one relevant, one irrelevant
        assert "yes" in relevance_scores
        assert "no" in relevance_scores

        # Step 2: Generate answer (simulated)
        generation = "LangGraph is a library for building stateful applications with LLMs."

        # Step 3: Check hallucination
        hallucination_score = hallucination_grader.grade(generation, documents)
        assert hallucination_score == "yes"  # Should be grounded

        # Step 4: Check usefulness
        usefulness_score = answer_grader.grade(question, generation)
        assert usefulness_score == "yes"  # Should be useful

        # Full pipeline successful
        assert True
