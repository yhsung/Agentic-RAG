"""
Integration tests for the complete Agentic RAG workflow.

Tests cover:
- End-to-end happy path
- Query rewriting path
- Hallucination correction path
- Uselessness correction path
- Error scenarios
"""

import pytest
from unittest.mock import Mock, patch
from langchain_core.documents import Document

from src.graph.workflow import AgenticRAGWorkflow
from src.graph.state import GraphState


class TestWorkflowInitialization:
    """Test workflow initialization."""

    def test_workflow_init(self):
        """Test that workflow initializes without errors."""
        workflow = AgenticRAGWorkflow()
        assert workflow is not None
        assert workflow.workflow is not None

    def test_get_graph_info(self):
        """Test getting graph information."""
        workflow = AgenticRAGWorkflow()
        info = workflow.get_graph_info()

        # Verify structure
        assert "nodes" in info
        assert "edges" in info
        assert "self_correction_mechanisms" in info

        # Verify expected nodes
        expected_nodes = [
            "retrieve",
            "grade_documents",
            "transform_query",
            "generate",
            "check_hallucination",
            "check_usefulness"
        ]
        for node in expected_nodes:
            assert node in info["nodes"]


class TestHappyPath:
    """Test the happy path workflow."""

    @patch('src.graph.nodes.similarity_search')
    @patch('src.agents.graders.DocumentGrader')
    @patch('src.agents.generator.AnswerGenerator')
    @patch('src.agents.graders.HallucinationGrader')
    @patch('src.agents.graders.AnswerGrader')
    def test_happy_path_workflow(
        self,
        mock_answer_grader_class,
        mock_hallucination_grader_class,
        mock_generator_class,
        mock_doc_grader_class,
        mock_similarity_search
    ):
        """Test complete happy path: retrieve → grade → generate → verify → end."""
        # Mock similarity search to return documents
        mock_docs = [
            Document(page_content="LangGraph is a library for building agents.", metadata={"source": "test1"}),
            Document(page_content="LangGraph uses state machines.", metadata={"source": "test2"})
        ]
        mock_similarity_search.return_value = mock_docs

        # Mock document grader - all relevant
        mock_doc_grader = Mock()
        mock_doc_grader.grade_batch.return_value = ["yes", "yes"]
        mock_doc_grader_class.return_value = mock_doc_grader

        # Mock generator
        mock_generator = Mock()
        mock_generator.generate.return_value = "LangGraph is a library for building stateful, multi-actor applications with LLMs."
        mock_generator_class.return_value = mock_generator

        # Mock hallucination grader - grounded
        mock_hallucination_grader = Mock()
        mock_hallucination_grader.grade.return_value = "yes"
        mock_hallucination_grader_class.return_value = mock_hallucination_grader

        # Mock answer grader - useful
        mock_answer_grader = Mock()
        mock_answer_grader.grade.return_value = "yes"
        mock_answer_grader_class.return_value = mock_answer_grader

        # Run workflow
        workflow = AgenticRAGWorkflow()
        result = workflow.run("What is LangGraph?")

        # Verify result
        assert result is not None
        assert "generation" in result
        assert len(result["generation"]) > 0
        assert result["hallucination_check"] == "grounded"
        assert result["usefulness_check"] == "useful"
        assert result["web_search"] == "No"


class TestQueryRewritePath:
    """Test the query rewriting workflow path."""

    @patch('src.graph.nodes.similarity_search')
    @patch('src.agents.graders.DocumentGrader')
    @patch('src.agents.rewriter.QueryRewriter')
    @patch('src.agents.generator.AnswerGenerator')
    @patch('src.agents.graders.HallucinationGrader')
    @patch('src.agents.graders.AnswerGrader')
    def test_query_rewrite_path(
        self,
        mock_answer_grader_class,
        mock_hallucination_grader_class,
        mock_generator_class,
        mock_rewriter_class,
        mock_doc_grader_class,
        mock_get_vector_store
    ):
        """Test path: retrieve → grade (none relevant) → transform_query → retrieve again."""
        # Mock vector store
        mock_store = Mock()
        # First retrieval: irrelevant docs
        mock_store.similarity_search.side_effect = [
            [Mock(page_content="Irrelevant content", metadata={"source": "test1"})],
            [Mock(page_content="LangGraph is a library.", metadata={"source": "test2"})]  # After rewrite
        ]
        mock_get_vector_store.return_value = mock_store

        # Mock document grader - first none relevant, then relevant
        mock_doc_grader = Mock()
        mock_doc_grader.grade.side_effect = ["no", "yes"]
        mock_doc_grader_class.return_value = mock_doc_grader

        # Mock query rewriter
        mock_rewriter = Mock()
        mock_rewriter.rewrite.return_value = "What are the key features of LangGraph?"
        mock_rewriter_class.return_value = mock_rewriter

        # Mock generator
        mock_generator = Mock()
        mock_generator.generate.return_value = "LangGraph provides state machine capabilities for agents."
        mock_generator_class.return_value = mock_generator

        # Mock quality checkers
        mock_hallucination_grader = Mock()
        mock_hallucination_grader.grade.return_value = "yes"
        mock_hallucination_grader_class.return_value = mock_hallucination_grader

        mock_answer_grader = Mock()
        mock_answer_grader.grade.return_value = "yes"
        mock_answer_grader_class.return_value = mock_answer_grader

        # Run workflow
        workflow = AgenticRAGWorkflow()
        result = workflow.run("What is LangGraph?")

        # Verify query was rewritten
        assert result["retry_count"] == 1
        assert result["generation"] is not None


class TestHallucinationCorrectionPath:
    """Test the hallucination correction workflow path."""

    @patch('src.graph.nodes.similarity_search')
    @patch('src.agents.graders.DocumentGrader')
    @patch('src.agents.generator.AnswerGenerator')
    @patch('src.agents.graders.HallucinationGrader')
    @patch('src.agents.graders.AnswerGrader')
    def test_hallucination_correction(
        self,
        mock_answer_grader_class,
        mock_hallucination_grader_class,
        mock_generator_class,
        mock_doc_grader_class,
        mock_get_vector_store
    ):
        """Test path: generate → hallucinated → regenerate → grounded."""
        # Mock vector store
        mock_store = Mock()
        mock_docs = [
            Mock(page_content="LangGraph is a library.", metadata={"source": "test1"})
        ]
        mock_store.similarity_search.return_value = mock_docs
        mock_get_vector_store.return_value = mock_store

        # Mock document grader
        mock_doc_grader = Mock()
        mock_doc_grader.grade.return_value = "yes"
        mock_doc_grader_class.return_value = mock_doc_grader

        # Mock generator - first hallucinated, then grounded
        mock_generator = Mock()
        mock_generator.generate.side_effect = [
            "LangGraph was created by aliens in 2050.",  # Hallucinated
            "LangGraph is a library for building agents."  # Grounded
        ]
        mock_generator_class.return_value = mock_generator

        # Mock hallucination grader
        mock_hallucination_grader = Mock()
        mock_hallucination_grader.grade.side_effect = ["no", "yes"]  # First not grounded, then grounded
        mock_hallucination_grader_class.return_value = mock_hallucination_grader

        # Mock answer grader
        mock_answer_grader = Mock()
        mock_answer_grader.grade.return_value = "yes"
        mock_answer_grader_class.return_value = mock_answer_grader

        # Run workflow
        workflow = AgenticRAGWorkflow()
        result = workflow.run("What is LangGraph?")

        # Verify regeneration happened
        assert result["hallucination_check"] == "grounded"
        assert "aliens" not in result["generation"]


class TestUsefulnessCorrectionPath:
    """Test the usefulness correction workflow path."""

    @patch('src.graph.nodes.similarity_search')
    @patch('src.agents.graders.DocumentGrader')
    @patch('src.agents.rewriter.QueryRewriter')
    @patch('src.agents.generator.AnswerGenerator')
    @patch('src.agents.graders.HallucinationGrader')
    @patch('src.agents.graders.AnswerGrader')
    def test_usefulness_correction(
        self,
        mock_answer_grader_class,
        mock_hallucination_grader_class,
        mock_generator_class,
        mock_rewriter_class,
        mock_doc_grader_class,
        mock_get_vector_store
    ):
        """Test path: generate → grounded but not useful → transform_query → retry."""
        # Mock vector store
        mock_store = Mock()
        mock_store.similarity_search.return_value = [
            Mock(page_content="LangGraph documentation", metadata={"source": "test1"})
        ]
        mock_get_vector_store.return_value = mock_store

        # Mock document grader
        mock_doc_grader = Mock()
        mock_doc_grader.grade.return_value = "yes"
        mock_doc_grader_class.return_value = mock_doc_grader

        # Mock query rewriter
        mock_rewriter = Mock()
        mock_rewriter.rewrite.return_value = "Explain how LangGraph works for agent workflows"
        mock_rewriter_class.return_value = mock_rewriter

        # Mock generator
        mock_generator = Mock()
        mock_generator.generate.side_effect = [
            "I cannot help with that.",  # Not useful
            "LangGraph provides state machines for building agent workflows."  # Useful
        ]
        mock_generator_class.return_value = mock_generator

        # Mock quality checkers
        mock_hallucination_grader = Mock()
        mock_hallucination_grader.grade.return_value = "yes"
        mock_hallucination_grader_class.return_value = mock_hallucination_grader

        mock_answer_grader = Mock()
        mock_answer_grader.grade.side_effect = ["no", "yes"]  # First not useful, then useful
        mock_answer_grader_class.return_value = mock_answer_grader

        # Run workflow
        workflow = AgenticRAGWorkflow()
        result = workflow.run("How does LangGraph work?")

        # Verify query was rewritten for better retrieval
        assert result["usefulness_check"] == "useful"
        assert result["retry_count"] >= 1


class TestErrorScenarios:
    """Test error handling scenarios."""

    def test_empty_question(self):
        """Test workflow with empty question."""
        workflow = AgenticRAGWorkflow()

        with pytest.raises(ValueError, match="Question cannot be empty"):
            workflow.run("")

    @patch('src.graph.nodes.similarity_search')
    def test_no_documents_found(self, mock_get_vector_store):
        """Test workflow when no documents are found."""
        # Mock empty vector store
        mock_store = Mock()
        mock_store.similarity_search.return_value = []
        mock_get_vector_store.return_value = mock_store

        workflow = AgenticRAGWorkflow()

        # Should handle gracefully
        result = workflow.run("What is something not in the database?")

        # Should still return a result
        assert result is not None


class TestWorkflowStreaming:
    """Test workflow streaming functionality."""

    @patch('src.graph.nodes.similarity_search')
    @patch('src.agents.graders.DocumentGrader')
    @patch('src.agents.generator.AnswerGenerator')
    @patch('src.agents.graders.HallucinationGrader')
    @patch('src.agents.graders.AnswerGrader')
    def test_workflow_streaming(
        self,
        mock_answer_grader_class,
        mock_hallucination_grader_class,
        mock_generator_class,
        mock_doc_grader_class,
        mock_get_vector_store
    ):
        """Test that workflow can be streamed."""
        # Mock dependencies
        mock_store = Mock()
        mock_store.similarity_search.return_value = [
            Mock(page_content="LangGraph content", metadata={"source": "test1"})
        ]
        mock_get_vector_store.return_value = mock_store

        mock_doc_grader = Mock()
        mock_doc_grader.grade.return_value = "yes"
        mock_doc_grader_class.return_value = mock_doc_grader

        mock_generator = Mock()
        mock_generator.generate.return_value = "LangGraph is a library."
        mock_generator_class.return_value = mock_generator

        mock_hallucination_grader = Mock()
        mock_hallucination_grader.grade.return_value = "yes"
        mock_hallucination_grader_class.return_value = mock_hallucination_grader

        mock_answer_grader = Mock()
        mock_answer_grader.grade.return_value = "yes"
        mock_answer_grader_class.return_value = mock_answer_grader

        # Stream workflow
        workflow = AgenticRAGWorkflow()
        event_count = 0

        for event in workflow.stream("What is LangGraph?"):
            event_count += 1
            assert isinstance(event, dict)

        # Should have multiple events (one per node)
        assert event_count > 0


class TestSelfCorrectionMechanisms:
    """Test that all self-correction mechanisms work."""

    def test_document_grading_active(self):
        """Verify document grading is in the workflow."""
        workflow = AgenticRAGWorkflow()
        info = workflow.get_graph_info()

        mechanisms = info["self_correction_mechanisms"]
        assert any("Document relevance grading" in m for m in mechanisms)

    def test_query_rewriting_active(self):
        """Verify query rewriting is in the workflow."""
        workflow = AgenticRAGWorkflow()
        info = workflow.get_graph_info()

        mechanisms = info["self_correction_mechanisms"]
        assert any("Query rewriting" in m for m in mechanisms)

    def test_hallucination_detection_active(self):
        """Verify hallucination detection is in the workflow."""
        workflow = AgenticRAGWorkflow()
        info = workflow.get_graph_info()

        mechanisms = info["self_correction_mechanisms"]
        assert any("Hallucination detection" in m for m in mechanisms)

    def test_answer_usefulness_active(self):
        """Verify answer usefulness check is in the workflow."""
        workflow = AgenticRAGWorkflow()
        info = workflow.get_graph_info()

        mechanisms = info["self_correction_mechanisms"]
        assert any("Answer usefulness verification" in m for m in mechanisms)
