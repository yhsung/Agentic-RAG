#!/usr/bin/env python3
"""
Test script to verify recursion limit handling with intentional failures.

This script tests the graceful error recovery implementation by simulating
scenarios that would previously cause crashes.
"""

import sys
import logging
from unittest.mock import Mock, patch
from langchain_core.documents import Document

# Add project root to path
sys.path.insert(0, "/Volumes/Samsung970EVOPlus/Agentic-RAG")

from src.graph.workflow import AgenticRAGWorkflow
from src.graph.nodes import generate
from src.graph.routers import check_hallucination_and_usefulness
from config.settings import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_scenario_1_regeneration_limit():
    """Test that regeneration stops at MAX_REGENERATIONS."""
    print("\n" + "="*80)
    print("SCENARIO 1: Regeneration Limit Enforcement")
    print("="*80)

    print(f"\nConfiguration:")
    print(f"  MAX_REGENERATIONS = {settings.MAX_REGENERATIONS}")
    print(f"  MAX_RETRIES = {settings.MAX_RETRIES}")

    # Simulate state at regeneration limit
    state = {
        "hallucination_check": "not_grounded",
        "usefulness_check": "useful",
        "retry_count": 0,
        "regeneration_count": settings.MAX_REGENERATIONS  # At limit
    }

    print(f"\nState:")
    print(f"  Hallucination Check: {state['hallucination_check']}")
    print(f"  Usefulness Check: {state['usefulness_check']}")
    print(f"  Regeneration Count: {state['regeneration_count']}/{settings.MAX_REGENERATIONS}")

    result = check_hallucination_and_usefulness(state)

    print(f"\n✓ Router Decision: {result}")
    assert result == "end", "Should return 'end' when regeneration limit reached"
    print("✓ PASS: Router correctly stops regeneration at limit")


def test_scenario_2_retry_limit():
    """Test that query rewriting stops at MAX_RETRIES."""
    print("\n" + "="*80)
    print("SCENARIO 2: Query Rewrite Limit Enforcement")
    print("="*80)

    # Simulate state at retry limit
    state = {
        "hallucination_check": "grounded",
        "usefulness_check": "not_useful",
        "retry_count": settings.MAX_RETRIES,  # At limit
        "regeneration_count": 0
    }

    print(f"\nState:")
    print(f"  Hallucination Check: {state['hallucination_check']}")
    print(f"  Usefulness Check: {state['usefulness_check']}")
    print(f"  Retry Count: {state['retry_count']}/{settings.MAX_RETRIES}")

    result = check_hallucination_and_usefulness(state)

    print(f"\n✓ Router Decision: {result}")
    assert result == "end", "Should return 'end' when retry limit reached"
    print("✓ PASS: Router correctly stops query rewriting at limit")


def test_scenario_3_regeneration_counter_tracking():
    """Test that regeneration counter increments correctly."""
    print("\n" + "="*80)
    print("SCENARIO 3: Regeneration Counter Tracking")
    print("="*80)

    # First generation (hallucinated)
    state1 = {
        "question": "What is LangGraph?",
        "documents": [Document(page_content="Test content", metadata={"source": "test"})],
        "regeneration_count": 0,
        "hallucination_check": "not_grounded",
        "prompt_variant": "baseline"
    }

    result1 = generate(state1)
    print(f"\nFirst generation (after hallucination):")
    print(f"  Input regeneration_count: {state1['regeneration_count']}")
    print(f"  Output regeneration_count: {result1['regeneration_count']}")
    assert result1['regeneration_count'] == 1, "Should increment to 1"

    # Second generation (still hallucinated)
    state2 = {**state1, "regeneration_count": result1['regeneration_count']}
    result2 = generate(state2)
    print(f"\nSecond generation (still hallucinated):")
    print(f"  Input regeneration_count: {state2['regeneration_count']}")
    print(f"  Output regeneration_count: {result2['regeneration_count']}")
    assert result2['regeneration_count'] == 2, "Should increment to 2"

    print("\n✓ PASS: Regeneration counter increments correctly")


def test_scenario_4_reset_after_query_rewrite():
    """Test that regeneration counter resets after query rewrite."""
    print("\n" + "="*80)
    print("SCENARIO 4: Regeneration Counter Reset After Query Rewrite")
    print("="*80)

    # After query rewrite (fresh start)
    state = {
        "question": "What is LangGraph?",
        "documents": [Document(page_content="Test content", metadata={"source": "test"})],
        "regeneration_count": 2,  # Previous regenerations
        "hallucination_check": "",  # Empty indicates fresh start
        "prompt_variant": "baseline"
    }

    result = generate(state)
    print(f"\nAfter query rewrite (fresh start):")
    print(f"  Input regeneration_count: {state['regeneration_count']}")
    print(f"  Output regeneration_count: {result['regeneration_count']}")
    assert result['regeneration_count'] == 0, "Should reset to 0"

    print("\n✓ PASS: Regeneration counter resets after query rewrite")


def test_scenario_5_recursion_limit_error_recovery():
    """Test graceful error recovery for recursion limit errors."""
    print("\n" + "="*80)
    print("SCENARIO 5: Recursion Limit Error Recovery")
    print("="*80)

    with patch('src.graph.workflow.AgenticRAGWorkflow._build_workflow') as mock_build:
        # Create mock workflow that simulates recursion limit error
        mock_workflow = Mock()
        mock_workflow.invoke.side_effect = Exception("Recursion limit of 50 reached")
        mock_build.return_value = mock_workflow

        workflow = AgenticRAGWorkflow()

        print(f"\nSimulating recursion limit error...")
        print(f"  WORKFLOW_RECURSION_LIMIT = {settings.WORKFLOW_RECURSION_LIMIT}")

        result = workflow.run("Test question")

        print(f"\n✓ System caught error gracefully")
        print(f"  Result keys: {list(result.keys())}")
        print(f"  Error flag: {result.get('error', 'None')}")

        assert result is not None, "Should return result, not crash"
        assert "generation" in result, "Should contain generation"
        assert result.get("error") == "recursion_limit_exceeded", "Should flag error type"

        # Check for helpful message
        generation = result["generation"]
        assert "apologize" in generation.lower(), "Should apologize to user"
        assert len(generation) > 100, "Should provide detailed help"

        print(f"\n✓ Fallback message preview:")
        print(f"  {generation[:150]}...")

    print("\n✓ PASS: Recursion limit error handled gracefully")


def test_scenario_6_both_limits_exceeded():
    """Test behavior when both regeneration and retry limits are exceeded."""
    print("\n" + "="*80)
    print("SCENARIO 6: Both Limits Exceeded")
    print("="*80)

    state = {
        "hallucination_check": "not_grounded",
        "usefulness_check": "not_useful",
        "retry_count": settings.MAX_RETRIES,
        "regeneration_count": settings.MAX_REGENERATIONS
    }

    print(f"\nState:")
    print(f"  Hallucination Check: {state['hallucination_check']}")
    print(f"  Usefulness Check: {state['usefulness_check']}")
    print(f"  Retry Count: {state['retry_count']}/{settings.MAX_RETRIES}")
    print(f"  Regeneration Count: {state['regeneration_count']}/{settings.MAX_REGENERATIONS}")

    result = check_hallucination_and_usefulness(state)

    print(f"\n✓ Router Decision: {result}")
    assert result == "end", "Should return 'end' when both limits exceeded"
    print("✓ PASS: System gracefully stops when both limits exceeded")


def run_all_scenarios():
    """Run all test scenarios."""
    print("\n" + "="*80)
    print("RECURSION LIMIT HANDLING - TEST SCENARIOS")
    print("="*80)
    print("\nTesting graceful error recovery implementation from")
    print("DEVELOPMENT_PLAN_v0.2.0.md")
    print(f"\nSettings:")
    print(f"  MAX_REGENERATIONS: {settings.MAX_REGENERATIONS}")
    print(f"  MAX_RETRIES: {settings.MAX_RETRIES}")
    print(f"  WORKFLOW_RECURSION_LIMIT: {settings.WORKFLOW_RECURSION_LIMIT}")

    try:
        test_scenario_1_regeneration_limit()
        test_scenario_2_retry_limit()
        test_scenario_3_regeneration_counter_tracking()
        test_scenario_4_reset_after_query_rewrite()
        test_scenario_5_recursion_limit_error_recovery()
        test_scenario_6_both_limits_exceeded()

        print("\n" + "="*80)
        print("ALL SCENARIOS PASSED ✓")
        print("="*80)
        print("\nSummary:")
        print("  ✓ Regeneration limit enforced correctly")
        print("  ✓ Query rewrite limit enforced correctly")
        print("  ✓ Regeneration counter tracks properly")
        print("  ✓ Counter resets after query rewrite")
        print("  ✓ Recursion limit errors handled gracefully")
        print("  ✓ Both limits exceeded handled correctly")
        print("\nThe implementation successfully prevents infinite loops")
        print("and provides graceful degradation when limits are reached.")

        return 0

    except AssertionError as e:
        print(f"\n✗ FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(run_all_scenarios())
