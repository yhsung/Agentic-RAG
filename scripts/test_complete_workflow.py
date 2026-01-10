"""
Test script for complete Agentic RAG workflow.

This script tests the fully integrated Phase 8 workflow with all 7 nodes
and 4 self-correction mechanisms.
"""

import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_workflow_initialization():
    """Test that the workflow can be initialized."""
    print("=" * 80)
    print("Testing Workflow Initialization")
    print("=" * 80)

    try:
        from src.graph.workflow import AgenticRAGWorkflow

        print("\n1. Initializing workflow...")
        print("-" * 80)
        rag = AgenticRAGWorkflow()
        print("✅ Workflow initialized successfully")

        print("\n2. Getting graph info...")
        print("-" * 80)
        info = rag.get_graph_info()
        print(f"Nodes ({len(info['nodes'])}): {', '.join(info['nodes'])}")
        print(f"Entry point: {info['entry_point']}")
        print(f"End point: {info['end_point']}")
        print(f"Edges ({len(info['edges'])}):")
        for edge in info['edges']:
            print(f"  {edge[0]} → {edge[1]}")
        print(f"\nSelf-Correction Mechanisms ({len(info['self_correction_mechanisms'])}):")
        for mechanism in info['self_correction_mechanisms']:
            print(f"  ✅ {mechanism}")

        return True

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_simple_query():
    """Test workflow with a simple query."""
    print("\n" + "=" * 80)
    print("Testing Simple Query")
    print("=" * 80)

    try:
        from src.graph.workflow import AgenticRAGWorkflow

        question = "What is Agentic RAG?"

        print(f"\nQuestion: {question}")
        print("-" * 80)

        rag = AgenticRAGWorkflow()
        print("\nRunning workflow...")
        result = rag.run(question)

        print("\n" + "-" * 80)
        print("Result:")
        print("-" * 80)
        print(f"Generation: {result.get('generation', 'No generation')}")

        # Print additional state info
        print(f"\nWeb Search: {result.get('web_search', 'N/A')}")
        print(f"Retry Count: {result.get('retry_count', 0)}")
        print(f"Relevant Docs: {sum(1 for s in result.get('relevance_scores', []) if s == 'yes')}/{len(result.get('relevance_scores', []))}")
        print(f"Hallucination Check: {result.get('hallucination_check', 'N/A')}")
        print(f"Usefulness Check: {result.get('usefulness_check', 'N/A')}")

        return True

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_workflow_streaming():
    """Test workflow streaming."""
    print("\n" + "=" * 80)
    print("Testing Workflow Streaming")
    print("=" * 80)

    try:
        from src.graph.workflow import AgenticRAGWorkflow

        question = "What are the main components of the system?"

        print(f"\nQuestion: {question}")
        print("-" * 80)

        rag = AgenticRAGWorkflow()
        print("\nStreaming workflow execution...\n")

        for event in rag.stream(question):
            # LangGraph streaming events format
            if isinstance(event, dict):
                for node_name, node_state in event.items():
                    print(f"Node: {node_name}")
                    if isinstance(node_state, dict):
                        if 'generation' in node_state and node_state['generation']:
                            print(f"  Generation preview: {node_state['generation'][:100]}...")
                        if 'documents' in node_state:
                            print(f"  Documents: {len(node_state['documents'])}")
                        if 'relevance_scores' in node_state and node_state['relevance_scores']:
                            print(f"  Relevance: {node_state['relevance_scores']}")
                        if 'hallucination_check' in node_state and node_state['hallucination_check']:
                            print(f"  Hallucination: {node_state['hallucination_check']}")
                        if 'usefulness_check' in node_state and node_state['usefulness_check']:
                            print(f"  Usefulness: {node_state['usefulness_check']}")
                    print()

        return True

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("Phase 8: Complete Graph Integration - Test Suite")
    print("=" * 80)

    results = {
        "Workflow Initialization": test_workflow_initialization(),
        "Simple Query": test_simple_query(),
        "Workflow Streaming": test_workflow_streaming(),
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
