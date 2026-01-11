"""
LangGraph Workflow for Agentic RAG System

This module builds the state graph that orchestrates the entire
agentic RAG workflow using LangGraph.
"""

import logging
from typing import Dict, Any, List

from langgraph.graph import StateGraph, END

from src.graph.state import GraphState
from src.graph.nodes import (
    retrieve,
    generate,
    grade_documents,
    transform_query,
    web_search,
    check_hallucination,
    check_usefulness
)
from src.graph.routers import (
    decide_to_generate,
    decide_to_web_search,
    check_hallucination_and_usefulness
)
from config.settings import settings


logger = logging.getLogger(__name__)


class AgenticRAGWorkflow:
    """
    Manages the LangGraph StateGraph for the Agentic RAG system.

    This class builds, compiles, and provides methods to run the complete
    agentic RAG workflow with all 4 self-correction mechanisms:
    1. Document relevance grading
    2. Query rewriting
    3. Web search fallback
    4. Hallucination and usefulness checks

    Attributes:
        workflow: The compiled LangGraph StateGraph
        prompt_variant: The prompt variant to use for answer generation

    Example:
        >>> rag = AgenticRAGWorkflow(prompt_variant="baseline")
        >>> result = rag.run("What is Agentic RAG?")
        >>> print(result["generation"])
        "Agentic RAG is a system that..."
    """

    def __init__(self, prompt_variant: str = "baseline"):
        """
        Initialize and build the Agentic RAG workflow.

        Args:
            prompt_variant: Which RAG prompt variant to use for answer generation
                           (baseline, detailed, bullets, reasoning)

        Creates the StateGraph, adds nodes, defines edges, and compiles
        the graph for execution with the specified prompt variant.
        """
        logger.info(f"Initializing Agentic RAG workflow with variant: {prompt_variant}")
        self.prompt_variant = prompt_variant

        # Build the workflow
        self.workflow = self._build_workflow()

        logger.info("Agentic RAG workflow initialized successfully")

    def _build_workflow(self) -> StateGraph:
        """
        Build the complete LangGraph StateGraph with all agentic features.

        Complete workflow flow:
        START → retrieve → grade_documents
                              ↓ (decide_to_web_search)
        ┌─────────────────────┼─────────────────────┐
        ↓                     ↓                     ↓
   transform_query      web_search             generate
        ↓                     ↓                     ↓
     retrieve            generate          check_hallucination
                                                   ↓
                                            check_usefulness
                                                   ↓
                              check_hallucination_and_usefulness
                                                   ↓
                    ┌───────────────┼───────────────┐
                    ↓               ↓               ↓
                regenerate    transform_query      END

        Routing decisions:
        - After grade_documents: decide_to_web_search routes based on relevance
        - After generate: check_hallucination_and_usefulness routes based on quality
        - Multiple loops: query rewriting (max 3), regeneration (unlimited)

        Returns:
            Compiled StateGraph ready for execution
        """
        logger.info("Building complete agentic RAG workflow graph")

        # Create the StateGraph
        workflow = StateGraph(GraphState)

        # Add all 7 nodes with web search now integrated
        workflow.add_node("retrieve", retrieve)
        workflow.add_node("grade_documents", grade_documents)
        workflow.add_node("generate", generate)
        workflow.add_node("transform_query", transform_query)
        workflow.add_node("web_search", web_search)  # Web search fallback for insufficient local docs
        workflow.add_node("check_hallucination", check_hallucination)
        workflow.add_node("check_usefulness", check_usefulness)

        # Set entry point
        workflow.set_entry_point("retrieve")

        # After retrieve, grade documents
        workflow.add_edge("retrieve", "grade_documents")

        # After grading, decide what to do
        # Routes based on document relevance scores and retry count
        workflow.add_conditional_edges(
            "grade_documents",
            decide_to_web_search,
            {
                "web_search": "web_search",
                "transform_query": "transform_query",
                "generate": "generate"
            }
        )

        # After transform_query, loop back to retrieve
        workflow.add_edge("transform_query", "retrieve")

        # After web_search, go to generate
        workflow.add_edge("web_search", "generate")

        # After generate, check hallucination
        workflow.add_edge("generate", "check_hallucination")

        # After hallucination check, check usefulness
        workflow.add_edge("check_hallucination", "check_usefulness")

        # After usefulness check, decide final action
        # Routes based on hallucination_check and usefulness_check
        workflow.add_conditional_edges(
            "check_usefulness",
            check_hallucination_and_usefulness,
            {
                "generate": "generate",  # Regenerate if hallucinated
                "transform_query": "transform_query",  # Improve query if not useful
                "end": END  # Success!
            }
        )

        # Compile the graph
        app = workflow.compile()

        logger.info("Complete agentic RAG workflow graph built and compiled")

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
            "web_search_needed": "No",
            "documents": [],
            "retry_count": 0,
            "relevance_scores": [],
            "hallucination_check": "",
            "usefulness_check": "",
            "prompt_variant": self.prompt_variant
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
            "web_search_needed": "No",
            "documents": [],
            "retry_count": 0,
            "relevance_scores": [],
            "hallucination_check": "",
            "usefulness_check": "",
            "prompt_variant": self.prompt_variant
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
            "nodes": [
                "retrieve",
                "grade_documents",
                "transform_query",
                "web_search",
                "generate",
                "check_hallucination",
                "check_usefulness"
            ],
            "entry_point": "retrieve",
            "end_point": "END",
            "edges": [
                ("retrieve", "grade_documents"),
                ("grade_documents", "web_search"),  # conditional: <50% relevant docs
                ("grade_documents", "transform_query"),  # conditional: no relevant, retries left
                ("grade_documents", "generate"),  # conditional: sufficient relevant docs
                ("transform_query", "retrieve"),  # loop back
                ("web_search", "generate"),  # after web search, generate answer
                ("generate", "check_hallucination"),  # always check
                ("check_hallucination", "check_usefulness"),  # always check
                ("check_usefulness", "generate"),  # conditional: hallucinated
                ("check_usefulness", "transform_query"),  # conditional: not useful
                ("check_usefulness", "END"),  # conditional: good answer
            ],
            "self_correction_mechanisms": [
                "Document relevance grading",
                "Query rewriting (max 3 retries)",
                "Web search fallback",
                "Hallucination detection",
                "Answer usefulness verification"
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
