"""
LangGraph Workflow for Agentic RAG System

This module builds the state graph that orchestrates the entire
agentic RAG workflow using LangGraph.
"""

import logging
from typing import Dict, Any, List

from langgraph.graph import StateGraph, END

from src.graph.state import GraphState
from src.graph.nodes import retrieve, generate
from config.settings import settings


logger = logging.getLogger(__name__)


class AgenticRAGWorkflow:
    """
    Manages the LangGraph StateGraph for the Agentic RAG system.

    This class builds, compiles, and provides methods to run the
    agentic RAG workflow. In Phase 3, this is a simple retrieve → generate
    flow. Agentic features will be added in later phases.

    Attributes:
        workflow: The compiled LangGraph StateGraph

    Example:
        >>> rag = AgenticRAGWorkflow()
        >>> result = rag.run("What is Agentic RAG?")
        >>> print(result["generation"])
        "Agentic RAG is a system that..."
    """

    def __init__(self):
        """
        Initialize and build the Agentic RAG workflow.

        Creates the StateGraph, adds nodes, defines edges, and compiles
        the graph for execution.
        """
        logger.info("Initializing Agentic RAG workflow")

        # Build the workflow
        self.workflow = self._build_workflow()

        logger.info("Agentic RAG workflow initialized successfully")

    def _build_workflow(self) -> StateGraph:
        """
        Build the LangGraph StateGraph.

        In Phase 3, this creates a simple linear flow:
        START → retrieve → generate → END

        Later phases will add conditional routing and agentic features.

        Returns:
            Compiled StateGraph ready for execution
        """
        logger.info("Building workflow graph")

        # Create the StateGraph
        workflow = StateGraph(GraphState)

        # Add nodes
        workflow.add_node("retrieve", retrieve)
        workflow.add_node("generate", generate)

        # Define edges
        workflow.set_entry_point("retrieve")
        workflow.add_edge("retrieve", "generate")
        workflow.add_edge("generate", END)

        # Compile the graph
        app = workflow.compile()

        logger.info("Workflow graph built and compiled")

        return app

    def run(self, question: str) -> Dict[str, Any]:
        """
        Run the workflow with a question.

        Executes the complete workflow and returns the final state
        with the generated answer.

        Args:
            question: The user's question

        Returns:
            Dictionary containing the final state with generation

        Raises:
            ValueError: If question is empty
            Exception: If workflow execution fails

        Example:
            >>> rag = AgenticRAGWorkflow()
            >>> result = rag.run("What is Agentic RAG?")
            >>> print(result["generation"])
        """
        if not question:
            raise ValueError("Question cannot be empty")

        logger.info(f"Running workflow for question: {question[:100]}...")

        # Initialize state
        initial_state: GraphState = {
            "question": question,
            "generation": "",
            "web_search": "No",
            "documents": [],
            "retry_count": 0,
            "relevance_scores": []
        }

        try:
            # Run the workflow
            result = self.workflow.invoke(initial_state)

            logger.info("Workflow completed successfully")
            logger.debug(f"Final state keys: {list(result.keys())}")

            return result

        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            raise Exception(f"Workflow failed: {e}")

    def stream(self, question: str):
        """
        Stream the workflow execution step by step.

        Yields the state after each node execution, allowing for
        real-time monitoring and visualization.

        Args:
            question: The user's question

        Yields:
            Dictionary containing node name and updated state

        Example:
            >>> rag = AgenticRAGWorkflow()
            >>> for event in rag.stream("What is Agentic RAG?"):
            ...     print(f"Node: {event['node']}")
            ...     print(f"State: {event['state']}")
        """
        if not question:
            raise ValueError("Question cannot be empty")

        logger.info(f"Streaming workflow for question: {question[:100]}...")

        # Initialize state
        initial_state: GraphState = {
            "question": question,
            "generation": "",
            "web_search": "No",
            "documents": [],
            "retry_count": 0,
            "relevance_scores": []
        }

        try:
            # Stream the workflow
            for event in self.workflow.stream(initial_state):
                yield event

        except Exception as e:
            logger.error(f"Workflow streaming failed: {e}")
            raise Exception(f"Workflow streaming failed: {e}")

    def get_graph_info(self) -> Dict[str, Any]:
        """
        Get information about the workflow graph structure.

        Returns:
            Dictionary with graph information including nodes and edges

        Example:
            >>> rag = AgenticRAGWorkflow()
            >>> info = rag.get_graph_info()
            >>> print(f"Nodes: {info['nodes']}")
        """
        return {
            "nodes": ["retrieve", "generate"],
            "entry_point": "retrieve",
            "end_point": "END",
            "edges": [
                ("retrieve", "generate"),
                ("generate", "END")
            ]
        }


# Convenience function for simple usage
def ask_question(question: str) -> str:
    """
    Convenience function to ask a question and get an answer.

    Args:
        question: The user's question

    Returns:
        Generated answer string

    Example:
        >>> from src.graph.workflow import ask_question
        >>> answer = ask_question("What is Agentic RAG?")
        >>> print(answer)
    """
    rag = AgenticRAGWorkflow()
    result = rag.run(question)
    return result.get("generation", "")


if __name__ == "__main__":
    """Test the Agentic RAG workflow."""
    import sys

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Check if question is provided
    if len(sys.argv) > 1:
        test_question = " ".join(sys.argv[1:])
    else:
        test_question = "What is Agentic RAG?"

    print("=" * 80)
    print("Testing Agentic RAG Workflow")
    print("=" * 80)
    print(f"\nQuestion: {test_question}\n")
    print("-" * 80)

    # Test basic run
    print("\n1. Testing basic run:")
    print("-" * 80)

    try:
        rag = AgenticRAGWorkflow()
        result = rag.run(test_question)

        print("\nGenerated Answer:")
        print(result["generation"])

        print("\n" + "=" * 80)
        print("Workflow test completed successfully")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
