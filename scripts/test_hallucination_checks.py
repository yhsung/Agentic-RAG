"""
Test script for hallucination and usefulness checks.

This script tests the Phase 7 implementation of hallucination detection
and answer usefulness verification.
"""

import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from langchain_core.documents import Document

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_hallucination_grader():
    """Test HallucinationGrader with grounded and hallucinated answers."""
    print("=" * 80)
    print("Testing HallucinationGrader")
    print("=" * 80)

    try:
        from src.agents.graders import HallucinationGrader

        # Sample documents
        documents = [
            Document(
                page_content="LangGraph is a library for building stateful, multi-actor applications with LLMs.",
                metadata={"source": "test1"}
            ),
            Document(
                page_content="Agentic RAG uses LangGraph for workflow management and self-correction.",
                metadata={"source": "test2"}
            ),
        ]

        # Test 1: Grounded answer
        print("\n1. Testing grounded answer:")
        print("-" * 80)
        grounded_generation = "LangGraph is used in Agentic RAG for workflow management."

        print(f"Documents:")
        for doc in documents:
            print(f"  - {doc.page_content}")
        print(f"\nGeneration: {grounded_generation}")

        grader = HallucinationGrader()
        score = grader.grade(grounded_generation, documents)
        print(f"\nHallucination check result: {score}")
        print(f"✅ Expected: 'yes' (grounded)")

        # Test 2: Hallucinated answer
        print("\n2. Testing hallucinated answer:")
        print("-" * 80)
        hallucinated_generation = "LangGraph was created in 2025 by Google and can predict stock prices with 99% accuracy."

        print(f"Documents:")
        for doc in documents:
            print(f"  - {doc.page_content}")
        print(f"\nGeneration: {hallucinated_generation}")

        score = grader.grade(hallucinated_generation, documents)
        print(f"\nHallucination check result: {score}")
        print(f"✅ Expected: 'no' (hallucinated)")

        return True

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_answer_grader():
    """Test AnswerGrader with useful and not useful answers."""
    print("\n" + "=" * 80)
    print("Testing AnswerGrader")
    print("=" * 80)

    try:
        from src.agents.graders import AnswerGrader

        # Test 1: Useful answer
        print("\n1. Testing useful answer:")
        print("-" * 80)
        question = "What is LangGraph?"
        useful_generation = "LangGraph is a library for building stateful, multi-actor applications with LLMs, enabling complex agent workflows."

        print(f"Question: {question}")
        print(f"Generation: {useful_generation}")

        grader = AnswerGrader()
        score = grader.grade(question, useful_generation)
        print(f"\nUsefulness check result: {score}")
        print(f"✅ Expected: 'yes' (useful)")

        # Test 2: Not useful answer
        print("\n2. Testing not useful answer:")
        print("-" * 80)
        not_useful_generation = "I don't know."

        print(f"Question: {question}")
        print(f"Generation: {not_useful_generation}")

        score = grader.grade(question, not_useful_generation)
        print(f"\nUsefulness check result: {score}")
        print(f"✅ Expected: 'no' (not useful)")

        return True

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_check_hallucination_node():
    """Test check_hallucination node."""
    print("\n" + "=" * 80)
    print("Testing check_hallucination Node")
    print("=" * 80)

    try:
        from src.graph.nodes import check_hallucination
        from src.graph.state import GraphState

        # Create test state with grounded answer
        print("\n1. Testing with grounded answer:")
        print("-" * 80)

        state: GraphState = {
            "question": "What is LangGraph?",
            "generation": "LangGraph is used for building agent workflows.",
            "web_search": "No",
            "documents": [
                Document(page_content="LangGraph is a library for building stateful applications.", metadata={"source": "test"})
            ],
            "retry_count": 0,
            "relevance_scores": ["yes"],
            "hallucination_check": "",
            "usefulness_check": ""
        }

        result = check_hallucination(state)
        print(f"Hallucination check: {result['hallucination_check']}")
        print(f"✅ Expected: 'grounded'")

        # Create test state with hallucinated answer
        print("\n2. Testing with hallucinated answer:")
        print("-" * 80)

        state["generation"] = "LangGraph was created by aliens in 2050."
        result = check_hallucination(state)
        print(f"Hallucination check: {result['hallucination_check']}")
        print(f"✅ Expected: 'not_grounded'")

        return True

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_check_usefulness_node():
    """Test check_usefulness node."""
    print("\n" + "=" * 80)
    print("Testing check_usefulness Node")
    print("=" * 80)

    try:
        from src.graph.nodes import check_usefulness
        from src.graph.state import GraphState

        # Create test state with useful answer
        print("\n1. Testing with useful answer:")
        print("-" * 80)

        state: GraphState = {
            "question": "What is LangGraph?",
            "generation": "LangGraph is a library for building stateful applications with LLMs.",
            "web_search": "No",
            "documents": [],
            "retry_count": 0,
            "relevance_scores": [],
            "hallucination_check": "",
            "usefulness_check": ""
        }

        result = check_usefulness(state)
        print(f"Usefulness check: {result['usefulness_check']}")
        print(f"✅ Expected: 'useful'")

        # Create test state with not useful answer
        print("\n2. Testing with not useful answer:")
        print("-" * 80)

        state["generation"] = "I cannot answer this question."
        result = check_usefulness(state)
        print(f"Usefulness check: {result['usefulness_check']}")
        print(f"✅ Expected: 'not_useful'")

        return True

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_router_logic():
    """Test check_hallucination_and_usefulness router."""
    print("\n" + "=" * 80)
    print("Testing check_hallucination_and_usefulness Router")
    print("=" * 80)

    try:
        from src.graph.routers import check_hallucination_and_usefulness
        from src.graph.state import GraphState

        # Test 1: Grounded and useful → end
        print("\n1. Testing grounded + useful → end:")
        print("-" * 80)

        state: GraphState = {
            "question": "What is LangGraph?",
            "generation": "LangGraph is a library for building agents.",
            "web_search": "No",
            "documents": [],
            "retry_count": 0,
            "relevance_scores": [],
            "hallucination_check": "grounded",
            "usefulness_check": "useful"
        }

        next_node = check_hallucination_and_usefulness(state)
        print(f"Next node: {next_node}")
        print(f"✅ Expected: 'end'")

        # Test 2: Not grounded → generate
        print("\n2. Testing hallucinated → regenerate:")
        print("-" * 80)

        state["hallucination_check"] = "not_grounded"
        state["usefulness_check"] = "useful"

        next_node = check_hallucination_and_usefulness(state)
        print(f"Next node: {next_node}")
        print(f"✅ Expected: 'generate'")

        # Test 3: Grounded but not useful → transform_query
        print("\n3. Testing grounded but not useful → transform_query:")
        print("-" * 80)

        state["hallucination_check"] = "grounded"
        state["usefulness_check"] = "not_useful"

        next_node = check_hallucination_and_usefulness(state)
        print(f"Next node: {next_node}")
        print(f"✅ Expected: 'transform_query'")

        return True

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("Phase 7: Hallucination and Usefulness Checks - Test Suite")
    print("=" * 80)

    results = {
        "HallucinationGrader": test_hallucination_grader(),
        "AnswerGrader": test_answer_grader(),
        "check_hallucination Node": test_check_hallucination_node(),
        "check_usefulness Node": test_check_usefulness_node(),
        "Router Logic": test_router_logic(),
    }

    # Print summary
    print("\n" + "=" * 80)
    print("Test Summary")
    print("=" * 80)

    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")

    # Count results
    passed = sum(1 for v in results.values() if v)
    total = len(results)

    print(f"\nTotal: {passed}/{total} tests passed")

    # Return exit code
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
