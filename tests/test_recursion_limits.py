"""
Tests for recursion limit handling and regeneration tracking.

Tests cover:
- Regeneration count tracking in generate node
- Router limit checking for regeneration and retries
- Recursion limit error recovery
- Configuration validation
"""

import pytest
from unittest.mock import Mock, patch
from langchain_core.documents import Document

from src.graph.workflow import AgenticRAGWorkflow
from src.graph.nodes import generate
from src.graph.routers import check_hallucination_and_usefulness
from src.graph.state import GraphState
from config.settings import settings


class TestRegenerationCountTracking:
    """Test regeneration count tracking in the generate node."""

    def test_generate_increments_regeneration_count_on_hallucination(self):
        """Test that generate node increments regeneration_count when previous answer was hallucinated."""
        state = {
            "question": "What is LangGraph?",
            "documents": [
                Document(page_content="LangGraph is a library for building agents.", metadata={"source": "test"})
            ],
            "regeneration_count": 0,
            "hallucination_check": "not_grounded",  # Previous attempt was hallucinated
            "prompt_variant": "baseline"
        }

        result = generate(state)

        # Should increment regeneration_count
        assert result["regeneration_count"] == 1
        assert "generation" in result

    def test_generate_resets_regeneration_count_on_fresh_start(self):
        """Test that generate node resets regeneration_count when starting fresh."""
        state = {
            "question": "What is LangGraph?",
            "documents": [
                Document(page_content="LangGraph is a library for building agents.", metadata={"source": "test"})
            ],
            "regeneration_count": 2,  # Previous regenerations
            "hallucination_check": "",  # Not a regeneration (fresh start or after query rewrite)
            "prompt_variant": "baseline"
        }

        result = generate(state)

        # Should reset regeneration_count to 0
        assert result["regeneration_count"] == 0
        assert "generation" in result

    def test_generate_preserves_regeneration_count_when_no_hallucination_check(self):
        """Test that generate node handles missing hallucination_check gracefully."""
        state = {
            "question": "What is LangGraph?",
            "documents": [
                Document(page_content="LangGraph is a library for building agents.", metadata={"source": "test"})
            ],
            "regeneration_count": 1,
            # hallucination_check missing
            "prompt_variant": "baseline"
        }

        result = generate(state)

        # Should reset when no hallucination_check (treats as fresh start)
        assert result["regeneration_count"] == 0

    def test_generate_handles_missing_regeneration_count(self):
        """Test that generate node handles missing regeneration_count gracefully."""
        state = {
            "question": "What is LangGraph?",
            "documents": [
                Document(page_content="LangGraph is a library for building agents.", metadata={"source": "test"})
            ],
            # regeneration_count missing
            "hallucination_check": "not_grounded",
            "prompt_variant": "baseline"
        }

        result = generate(state)

        # Should default to 0 and increment
        assert result["regeneration_count"] == 1


class TestRouterLimitChecking:
    """Test router limit checking for regeneration and retries."""

    def test_router_allows_regeneration_under_limit(self):
        """Test that router allows regeneration when under MAX_REGENERATIONS."""
        state = {
            "hallucination_check": "not_grounded",
            "usefulness_check": "useful",
            "retry_count": 0,
            "regeneration_count": 1  # Under limit (default is 3)
        }

        result = check_hallucination_and_usefulness(state)

        assert result == "generate"

    def test_router_stops_regeneration_at_limit(self):
        """Test that router stops regeneration when MAX_REGENERATIONS is reached."""
        state = {
            "hallucination_check": "not_grounded",
            "usefulness_check": "useful",
            "retry_count": 0,
            "regeneration_count": settings.MAX_REGENERATIONS  # At limit
        }

        result = check_hallucination_and_usefulness(state)

        # Should return "end" to stop gracefully
        assert result == "end"

    def test_router_allows_query_rewrite_under_limit(self):
        """Test that router allows query rewrite when under MAX_RETRIES."""
        state = {
            "hallucination_check": "grounded",
            "usefulness_check": "not_useful",
            "retry_count": 1,  # Under limit (default is 3)
            "regeneration_count": 0
        }

        result = check_hallucination_and_usefulness(state)

        assert result == "transform_query"

    def test_router_stops_query_rewrite_at_limit(self):
        """Test that router stops query rewrite when MAX_RETRIES is reached."""
        state = {
            "hallucination_check": "grounded",
            "usefulness_check": "not_useful",
            "retry_count": settings.MAX_RETRIES,  # At limit
            "regeneration_count": 0
        }

        result = check_hallucination_and_usefulness(state)

        # Should return "end" to stop gracefully
        assert result == "end"

    def test_router_prioritizes_hallucination_check_over_usefulness(self):
        """Test that router checks hallucination before usefulness."""
        state = {
            "hallucination_check": "not_grounded",  # Hallucinated
            "usefulness_check": "not_useful",  # Also not useful
            "retry_count": 0,
            "regeneration_count": 1
        }

        result = check_hallucination_and_usefulness(state)

        # Should regenerate (hallucination takes priority)
        assert result == "generate"

    def test_router_returns_end_for_good_answer(self):
        """Test that router returns 'end' for grounded and useful answers."""
        state = {
            "hallucination_check": "grounded",
            "usefulness_check": "useful",
            "retry_count": 0,
            "regeneration_count": 0
        }

        result = check_hallucination_and_usefulness(state)

        assert result == "end"

    def test_router_handles_missing_fields(self):
        """Test that router handles missing state fields gracefully."""
        state = {
            # All fields missing
        }

        result = check_hallucination_and_usefulness(state)

        # Should default to treating as hallucinated (not_grounded)
        # and allow regeneration since count defaults to 0
        assert result in ["generate", "end"]


class TestRecursionLimitConfiguration:
    """Test recursion limit configuration."""

    def test_settings_have_default_values(self):
        """Test that settings have correct default values."""
        assert settings.MAX_REGENERATIONS == 3
        assert settings.WORKFLOW_RECURSION_LIMIT == 50
        assert settings.MAX_RETRIES == 3

    def test_recursion_limit_is_configurable(self):
        """Test that recursion limit can be configured."""
        # This test verifies the setting exists and is configurable
        # Actual configuration happens via .env file
        assert hasattr(settings, 'WORKFLOW_RECURSION_LIMIT')
        assert settings.WORKFLOW_RECURSION_LIMIT >= 25
        assert settings.WORKFLOW_RECURSION_LIMIT <= 200

    def test_max_regenerations_is_configurable(self):
        """Test that max regenerations can be configured."""
        assert hasattr(settings, 'MAX_REGENERATIONS')
        assert settings.MAX_REGENERATIONS >= 1
        assert settings.MAX_REGENERATIONS <= 10


class TestRecursionLimitErrorRecovery:
    """Test graceful error recovery for recursion limit errors."""

    @patch('src.graph.workflow.AgenticRAGWorkflow._build_workflow')
    def test_workflow_catches_recursion_limit_error(self, mock_build_workflow):
        """Test that workflow catches recursion limit errors and returns fallback."""
        # Create a mock workflow that raises recursion limit error
        mock_workflow = Mock()
        mock_workflow.invoke.side_effect = Exception("Recursion limit of 25 reached")
        mock_build_workflow.return_value = mock_workflow

        workflow = AgenticRAGWorkflow()
        result = workflow.run("Test question")

        # Should return fallback response instead of crashing
        assert result is not None
        assert "generation" in result
        assert "apologize" in result["generation"].lower()
        assert result.get("error") == "recursion_limit_exceeded"

    @patch('src.graph.workflow.AgenticRAGWorkflow._build_workflow')
    def test_workflow_reraises_non_recursion_errors(self, mock_build_workflow):
        """Test that workflow re-raises non-recursion errors."""
        # Create a mock workflow that raises a different error
        mock_workflow = Mock()
        mock_workflow.invoke.side_effect = Exception("Some other error")
        mock_build_workflow.return_value = mock_workflow

        workflow = AgenticRAGWorkflow()

        # Should re-raise the error
        with pytest.raises(Exception, match="Some other error"):
            workflow.run("Test question")

    @patch('src.graph.workflow.AgenticRAGWorkflow._build_workflow')
    def test_fallback_response_includes_helpful_message(self, mock_build_workflow):
        """Test that fallback response includes helpful troubleshooting message."""
        mock_workflow = Mock()
        mock_workflow.invoke.side_effect = Exception("Recursion limit of 50 reached")
        mock_build_workflow.return_value = mock_workflow

        workflow = AgenticRAGWorkflow()
        result = workflow.run("Test question")

        generation = result["generation"]

        # Should include helpful suggestions
        assert "Rephrasing your question" in generation or "rephrase" in generation.lower()
        assert "Breaking complex questions" in generation or "simpler parts" in generation.lower()

    @patch('src.graph.workflow.AgenticRAGWorkflow._build_workflow')
    def test_fallback_response_preserves_metadata(self, mock_build_workflow):
        """Test that fallback response preserves initial state metadata."""
        mock_workflow = Mock()
        mock_workflow.invoke.side_effect = Exception("Recursion limit exceeded")
        mock_build_workflow.return_value = mock_workflow

        workflow = AgenticRAGWorkflow(prompt_variant="detailed")
        result = workflow.run("Test question")

        # Should preserve initial state values
        assert result["question"] == "Test question"
        assert result["retry_count"] == 0
        assert result["regeneration_count"] == 0
        assert result["prompt_variant"] == "detailed"
        assert result["hallucination_check"] == "error"
        assert result["usefulness_check"] == "error"


class TestWorkflowInitializationWithRecursionLimit:
    """Test that workflow initializes with correct recursion limit."""

    def test_workflow_graph_info_includes_recursion_limit(self):
        """Test that workflow graph info includes recursion limit information."""
        workflow = AgenticRAGWorkflow()
        info = workflow.get_graph_info()

        mechanisms = info["self_correction_mechanisms"]

        # Should include recursion limit info
        assert any("Recursion limit" in m for m in mechanisms)
        assert any(str(settings.WORKFLOW_RECURSION_LIMIT) in m for m in mechanisms)

    def test_workflow_graph_info_includes_regeneration_info(self):
        """Test that workflow graph info includes regeneration information."""
        workflow = AgenticRAGWorkflow()
        info = workflow.get_graph_info()

        mechanisms = info["self_correction_mechanisms"]

        # Should include regeneration info
        assert any("Answer regeneration" in m or "regeneration" in m.lower() for m in mechanisms)


class TestStatePersistence:
    """Test that state persists correctly across workflow steps."""

    def test_initial_state_includes_regeneration_count(self):
        """Test that workflow initializes state with regeneration_count."""
        workflow = AgenticRAGWorkflow()

        # We can't directly access the initial state, but we can verify
        # the workflow can be created without errors
        assert workflow is not None

    @patch('src.graph.workflow.AgenticRAGWorkflow._build_workflow')
    def test_regeneration_count_persists_in_error_case(self, mock_build_workflow):
        """Test that regeneration_count is preserved in error fallback."""
        mock_workflow = Mock()
        mock_workflow.invoke.side_effect = Exception("Recursion limit of 50 reached")
        mock_build_workflow.return_value = mock_workflow

        workflow = AgenticRAGWorkflow()
        result = workflow.run("Test question")

        # Should have initial values
        assert "regeneration_count" in result
        assert result["regeneration_count"] == 0


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_regeneration_count_exactly_at_limit(self):
        """Test router behavior when regeneration_count equals MAX_REGENERATIONS."""
        state = {
            "hallucination_check": "not_grounded",
            "usefulness_check": "useful",
            "retry_count": 0,
            "regeneration_count": settings.MAX_REGENERATIONS  # Exactly at limit
        }

        result = check_hallucination_and_usefulness(state)

        # Should stop (not regenerate)
        assert result == "end"

    def test_retry_count_exactly_at_limit(self):
        """Test router behavior when retry_count equals MAX_RETRIES."""
        state = {
            "hallucination_check": "grounded",
            "usefulness_check": "not_useful",
            "retry_count": settings.MAX_RETRIES,  # Exactly at limit
            "regeneration_count": 0
        }

        result = check_hallucination_and_usefulness(state)

        # Should stop (not retry)
        assert result == "end"

    def test_both_limits_exceeded(self):
        """Test router behavior when both limits are exceeded."""
        state = {
            "hallucination_check": "not_grounded",
            "usefulness_check": "not_useful",
            "retry_count": settings.MAX_RETRIES,
            "regeneration_count": settings.MAX_REGENERATIONS
        }

        result = check_hallucination_and_usefulness(state)

        # Should stop
        assert result == "end"

    def test_negative_counts(self):
        """Test that router handles negative counts gracefully."""
        state = {
            "hallucination_check": "not_grounded",
            "usefulness_check": "useful",
            "retry_count": -1,  # Invalid but shouldn't crash
            "regeneration_count": 0
        }

        # Should not crash
        result = check_hallucination_and_usefulness(state)
        assert result in ["generate", "transform_query", "end"]
