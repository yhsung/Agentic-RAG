"""
Unit tests for all graph nodes.

Tests cover:
- retrieve
- grade_documents
- generate
- transform_query
- web_search
- check_hallucination
- check_usefulness
"""

import pytest
from langchain_core.documents import Document
from unittest.mock import Mock, patch, MagicMock

from src.graph.nodes import (
    retrieve,
    grade_documents,
    generate,
    transform_query,
    web_search,
    check_hallucination,
    check_usefulness
)
from src.graph.state import GraphState


class TestRetrieveNode:
    """Test the retrieve node."""

    @patch('src.vectorstore.chroma_store.similarity_search')
    def test_retrieve_returns_documents(self, mock_similarity_search):
        """Test that retrieve node returns documents."""
        # Mock similarity_search to return documents directly
        mock_docs = [
            Document(page_content="Test content 1", metadata={"source": "test1"}),
            Document(page_content="Test content 2", metadata={"source": "test2"})
        ]
        mock_similarity_search.return_value = mock_docs

        # Create state
        state: GraphState = {
            "question": "What is LangGraph?",
            "generation": "",
            "web_search": "No",
            "documents": [],
            "retry_count": 0,
            "relevance_scores": [],
            "hallucination_check": "",
            "usefulness_check": ""
        }

        # Execute node
        result = retrieve(state)

        # Verify
        assert "documents" in result
        assert len(result["documents"]) > 0
        assert isinstance(result["documents"][0], Document)

    @patch('src.vectorstore.chroma_store.similarity_search')
    def test_retrieve_with_empty_question(self, mock_similarity_search):
        """Test retrieve with empty question."""
        mock_similarity_search.return_value = []

        state: GraphState = {
            "question": "",
            "generation": "",
            "web_search": "No",
            "documents": [],
            "retry_count": 0,
            "relevance_scores": [],
            "hallucination_check": "",
            "usefulness_check": ""
        }

        result = retrieve(state)

        # Should handle gracefully
        assert "documents" in result


class TestGradeDocumentsNode:
    """Test the grade_documents node."""

    @patch('src.agents.graders.DocumentGrader')
    def test_grade_documents_all_relevant(self, mock_grader_class):
        """Test grading when all documents are relevant."""
        # Mock grader
        mock_grader = Mock()
        mock_grader.grade_batch.return_value = ["yes", "yes"]
        mock_grader_class.return_value = mock_grader

        # Create state with documents
        documents = [
            Document(page_content="LangGraph is a library.", metadata={"source": "test1"}),
            Document(page_content="LangGraph enables agents.", metadata={"source": "test2"})
        ]

        state: GraphState = {
            "question": "What is LangGraph?",
            "generation": "",
            "web_search": "No",
            "documents": documents,
            "retry_count": 0,
            "relevance_scores": [],
            "hallucination_check": "",
            "usefulness_check": ""
        }

        # Execute node
        result = grade_documents(state)

        # Verify
        assert "relevance_scores" in result
        assert len(result["relevance_scores"]) == len(documents)
        assert all(score == "yes" for score in result["relevance_scores"])

    @patch('src.agents.graders.DocumentGrader')
    def test_grade_documents_mixed_relevance(self, mock_grader_class):
        """Test grading with mixed relevance."""
        # Mock grader to return alternating yes/no
        mock_grader = Mock()
        mock_grader.grade_batch.return_value = ["yes", "no", "yes"]
        mock_grader_class.return_value = mock_grader

        documents = [
            Document(page_content="Relevant content", metadata={"source": "test1"}),
            Document(page_content="Irrelevant content", metadata={"source": "test2"}),
            Document(page_content="More relevant", metadata={"source": "test3"})
        ]

        state: GraphState = {
            "question": "What is LangGraph?",
            "generation": "",
            "web_search": "No",
            "documents": documents,
            "retry_count": 0,
            "relevance_scores": [],
            "hallucination_check": "",
            "usefulness_check": ""
        }

        result = grade_documents(state)

        # Verify mixed scores
        assert len(result["relevance_scores"]) == 3
        assert "yes" in result["relevance_scores"]
        assert "no" in result["relevance_scores"]


class TestGenerateNode:
    """Test the generate node."""

    @patch('src.agents.generator.AnswerGenerator')
    def test_generate_returns_answer(self, mock_generator_class):
        """Test that generate node returns an answer."""
        # Mock generator
        mock_generator = Mock()
        mock_generator.generate.return_value = "LangGraph is a library for building agents."
        mock_generator_class.return_value = mock_generator

        state: GraphState = {
            "question": "What is LangGraph?",
            "generation": "",
            "web_search": "No",
            "documents": [
                Document(page_content="LangGraph content", metadata={"source": "test1"})
            ],
            "retry_count": 0,
            "relevance_scores": ["yes"],
            "hallucination_check": "",
            "usefulness_check": ""
        }

        result = generate(state)

        # Verify
        assert "generation" in result
        assert len(result["generation"]) > 0
        assert isinstance(result["generation"], str)

    @patch('src.agents.generator.AnswerGenerator')
    def test_generate_with_no_documents(self, mock_generator_class):
        """Test generate with no documents."""
        mock_generator = Mock()
        mock_generator.generate.return_value = "I don't have information about that."
        mock_generator_class.return_value = mock_generator

        state: GraphState = {
            "question": "What is LangGraph?",
            "generation": "",
            "web_search": "No",
            "documents": [],
            "retry_count": 0,
            "relevance_scores": [],
            "hallucination_check": "",
            "usefulness_check": ""
        }

        result = generate(state)

        # Should still generate a response
        assert "generation" in result


class TestTransformQueryNode:
    """Test the transform_query node."""

    @patch('src.agents.rewriter.QueryRewriter')
    def test_transform_query_improves_question(self, mock_rewriter_class):
        """Test that transform_query improves the question."""
        # Mock rewriter
        mock_rewriter = Mock()
        mock_rewriter.rewrite.return_value = "What are the key features and capabilities of LangGraph for building agent applications?"
        mock_rewriter_class.return_value = mock_rewriter

        state: GraphState = {
            "question": "What is LangGraph?",
            "generation": "",
            "web_search": "No",
            "documents": [],
            "retry_count": 0,
            "relevance_scores": [],
            "hallucination_check": "",
            "usefulness_check": ""
        }

        result = transform_query(state)

        # Verify
        assert "question" in result
        assert len(result["question"]) > 0
        assert "retry_count" in result
        assert result["retry_count"] == 1

    @patch('src.agents.rewriter.QueryRewriter')
    def test_transform_query_increments_retry(self, mock_rewriter_class):
        """Test that transform_query increments retry count."""
        mock_rewriter = Mock()
        mock_rewriter.rewrite.return_value = "Improved question"
        mock_rewriter_class.return_value = mock_rewriter

        state: GraphState = {
            "question": "Original question",
            "generation": "",
            "web_search": "No",
            "documents": [],
            "retry_count": 2,  # Already tried twice
            "relevance_scores": [],
            "hallucination_check": "",
            "usefulness_check": ""
        }

        result = transform_query(state)

        # Should increment retry count
        assert result["retry_count"] == 3


class TestWebSearchNode:
    """Test the web_search node."""

    @patch('src.agents.web_searcher.WebSearcher')
    def test_web_search_returns_documents(self, mock_searcher_class):
        """Test that web_search returns documents."""
        # Mock searcher
        mock_searcher = Mock()
        mock_searcher.is_available.return_value = True
        mock_searcher.search.return_value = [
            Document(page_content="Web search result 1", metadata={"source": "web1"}),
            Document(page_content="Web search result 2", metadata={"source": "web2"})
        ]
        mock_searcher_class.return_value = mock_searcher

        state: GraphState = {
            "question": "Latest developments in AI",
            "generation": "",
            "web_search": "No",
            "documents": [],
            "retry_count": 0,
            "relevance_scores": [],
            "hallucination_check": "",
            "usefulness_check": ""
        }

        result = web_search(state)

        # Verify
        assert "documents" in result
        assert "web_search" in result
        assert result["web_search"] == "Yes"

    @patch('src.agents.web_searcher.WebSearcher')
    def test_web_search_unavailable(self, mock_searcher_class):
        """Test web_search when service is unavailable."""
        # Mock unavailable searcher
        mock_searcher = Mock()
        mock_searcher.is_available.return_value = False
        mock_searcher_class.return_value = mock_searcher

        state: GraphState = {
            "question": "Test question",
            "generation": "",
            "web_search": "No",
            "documents": [],
            "retry_count": 0,
            "relevance_scores": [],
            "hallucination_check": "",
            "usefulness_check": ""
        }

        result = web_search(state)

        # Should return empty documents and No web_search
        assert result["documents"] == []
        assert result["web_search"] == "No"


class TestCheckHallucinationNode:
    """Test the check_hallucination node."""

    @patch('src.agents.graders.HallucinationGrader')
    def test_check_hallucination_grounded(self, mock_grader_class):
        """Test check_hallucination with grounded answer."""
        # Mock grader
        mock_grader = Mock()
        mock_grader.grade.return_value = "yes"
        mock_grader_class.return_value = mock_grader

        state: GraphState = {
            "question": "What is LangGraph?",
            "generation": "LangGraph is a library for agents.",
            "web_search": "No",
            "documents": [
                Document(page_content="LangGraph is a library.", metadata={"source": "test1"})
            ],
            "retry_count": 0,
            "relevance_scores": ["yes"],
            "hallucination_check": "",
            "usefulness_check": ""
        }

        result = check_hallucination(state)

        # Verify
        assert "hallucination_check" in result
        assert result["hallucination_check"] == "grounded"

    @patch('src.agents.graders.HallucinationGrader')
    def test_check_hallucination_not_grounded(self, mock_grader_class):
        """Test check_hallucination with hallucinated answer."""
        mock_grader = Mock()
        mock_grader.grade.return_value = "no"
        mock_grader_class.return_value = mock_grader

        state: GraphState = {
            "question": "What is LangGraph?",
            "generation": "LangGraph was created by aliens.",
            "web_search": "No",
            "documents": [
                Document(page_content="LangGraph is a library.", metadata={"source": "test1"})
            ],
            "retry_count": 0,
            "relevance_scores": ["yes"],
            "hallucination_check": "",
            "usefulness_check": ""
        }

        result = check_hallucination(state)

        # Verify
        assert result["hallucination_check"] == "not_grounded"


class TestCheckUsefulnessNode:
    """Test the check_usefulness node."""

    @patch('src.agents.graders.AnswerGrader')
    def test_check_usefulness_useful(self, mock_grader_class):
        """Test check_usefulness with useful answer."""
        # Mock grader
        mock_grader = Mock()
        mock_grader.grade.return_value = "yes"
        mock_grader_class.return_value = mock_grader

        state: GraphState = {
            "question": "What is LangGraph?",
            "generation": "LangGraph is a library for building stateful agent applications.",
            "web_search": "No",
            "documents": [],
            "retry_count": 0,
            "relevance_scores": [],
            "hallucination_check": "grounded",
            "usefulness_check": ""
        }

        result = check_usefulness(state)

        # Verify
        assert "usefulness_check" in result
        assert result["usefulness_check"] == "useful"

    @patch('src.agents.graders.AnswerGrader')
    def test_check_usefulness_not_useful(self, mock_grader_class):
        """Test check_usefulness with not useful answer."""
        mock_grader = Mock()
        mock_grader.grade.return_value = "no"
        mock_grader_class.return_value = mock_grader

        state: GraphState = {
            "question": "What is LangGraph?",
            "generation": "I don't know.",
            "web_search": "No",
            "documents": [],
            "retry_count": 0,
            "relevance_scores": [],
            "hallucination_check": "grounded",
            "usefulness_check": ""
        }

        result = check_usefulness(state)

        # Verify
        assert result["usefulness_check"] == "not_useful"


class TestNodeIntegration:
    """Integration tests for node interactions."""

    @patch('src.graph.nodes.similarity_search')
    @patch('src.agents.graders.DocumentGrader')
    def test_retrieve_and_grade_pipeline(self, mock_grader_class, mock_similarity_search):
        """Test retrieve → grade_documents pipeline."""
        # Mock dependencies
        mock_docs = [
            Document(page_content="LangGraph is a library.", metadata={"source": "test1"}),
            Document(page_content="Python is a language.", metadata={"source": "test2"})
        ]
        mock_similarity_search.return_value = mock_docs

        mock_grader = Mock()
        mock_grader.grade_batch.return_value = ["yes", "no"]
        mock_grader_class.return_value = mock_grader

        # Initial state
        state: GraphState = {
            "question": "What is LangGraph?",
            "generation": "",
            "web_search": "No",
            "documents": [],
            "retry_count": 0,
            "relevance_scores": [],
            "hallucination_check": "",
            "usefulness_check": ""
        }

        # Execute retrieve
        result = retrieve(state)
        state.update(result)

        # Execute grade_documents
        result = grade_documents(state)
        state.update(result)

        # Verify pipeline
        assert len(state["documents"]) == 2
        assert len(state["relevance_scores"]) == 2
        assert state["relevance_scores"] == ["yes", "no"]
