"""
Router Functions for Agentic RAG Workflow

This module implements conditional edge functions that determine
the routing logic in the LangGraph state machine.
"""

import logging
from typing import Literal

from src.graph.state import GraphState


logger = logging.getLogger(__name__)


def decide_to_generate(state: GraphState) -> Literal["generate", "transform_query", "end"]:
    """
    Determine whether to generate an answer, transform the query, or end.

    This router function evaluates the relevance scores of retrieved documents
    and retry count to decide the next step:
    - If any documents are relevant → generate answer
    - If no documents are relevant AND retries left → transform query
    - If no documents are relevant AND no retries left → end

    Args:
        state: Current graph state containing relevance_scores and retry_count

    Returns:
        "generate" if any relevant docs, "transform_query" if none and retries left,
        "end" if no retries left

    Routing Logic:
        - At least one relevant document → generate
        - No relevant documents AND retry_count < MAX_RETRIES → transform_query
        - No relevant documents AND retry_count >= MAX_RETRIES → end

    Example:
        >>> state = {
        ...     "relevance_scores": ["yes", "no", "yes"],
        ...     "retry_count": 0,
        ...     ...
        ... }
        >>> next_node = decide_to_generate(state)
        >>> print(next_node)
        "generate"

        >>> state = {
        ...     "relevance_scores": ["no", "no", "no"],
        ...     "retry_count": 0,
        ...     ...
        ... }
        >>> next_node = decide_to_generate(state)
        >>> print(next_node)
        "transform_query"

        >>> state = {
        ...     "relevance_scores": ["no", "no", "no"],
        ...     "retry_count": 3,
        ...     ...
        ... }
        >>> next_node = decide_to_generate(state)
        >>> print(next_node)
        "end"
    """
    logger.info("Router: decide_to_generate")

    if not state["relevance_scores"]:
        logger.warning("No relevance scores available")
        # If no scores, check retry count
        if state["retry_count"] < 3:  # MAX_RETRIES
            logger.info("No scores but retries left - transform query")
            return "transform_query"
        else:
            logger.info("No scores and max retries reached - end")
            return "end"

    # Count relevant documents
    relevant_count = sum(1 for score in state["relevance_scores"] if score == "yes")
    total_count = len(state["relevance_scores"])

    logger.info(f"Relevant documents: {relevant_count}/{total_count}")
    logger.info(f"Retry count: {state['retry_count']}/3")

    # Decision tree:
    # 1. If we have relevant documents → generate answer
    if relevant_count > 0:
        logger.info("Decision: Generate answer from relevant documents")
        return "generate"

    # 2. No relevant documents - check if we should retry
    if state["retry_count"] < 3:  # MAX_RETRIES
        logger.info("Decision: No relevant documents, transform query (retries left)")
        return "transform_query"
    else:
        logger.info("Decision: Max retries reached, ending workflow")
        return "end"


def decide_to_web_search(state: GraphState) -> Literal["web_search", "generate"]:
    """
    Determine whether to perform web search or generate answer.

    This router function evaluates whether we have enough relevant
    documents or should fall back to web search.

    NOTE: This is a placeholder for Phase 6. Currently always routes
    to generate since web search is not yet implemented.

    Args:
        state: Current graph state containing relevance_scores

    Returns:
        "web_search" or "generate"

    Example:
        >>> state = {"relevance_scores": ["yes"], ...}
        >>> next_node = decide_to_web_search(state)
        >>> print(next_node)
        "generate"
    """
    logger.info("Router: decide_to_web_search")
    logger.info("Web search not yet implemented - Phase 6")
    logger.warning("Routing to generate")

    # Placeholder: Always route to generate
    # Will implement proper logic in Phase 6
    return "generate"


def check_hallucination_and_usefulness(state: GraphState) -> Literal["generate", "transform_query", "end"]:
    """
    Check if the generated answer is grounded and useful.

    This router function verifies:
    1. Answer is grounded in documents (not hallucinated)
    2. Answer addresses the question (useful)

    Routing Logic:
    - Hallucinated → regenerate
    - Not useful → transform_query
    - Both good → end

    NOTE: This is a placeholder for Phase 7. Currently always routes
    to end since hallucination/usefulness checks are not yet implemented.

    Args:
        state: Current graph state

    Returns:
        "generate", "transform_query", or "end"

    Example:
        >>> state = {"generation": "...", ...}
        >>> next_node = check_hallucination_and_usefulness(state)
        >>> print(next_node)
        "end"
    """
    logger.info("Router: check_hallucination_and_usefulness")
    logger.info("Hallucination/usefulness check not yet implemented - Phase 7")
    logger.warning("Routing to end")

    # Placeholder: Always route to end
    # Will implement proper logic in Phase 7
    return "end"


def should_retry_query(state: GraphState) -> bool:
    """
    Check if query should be rewritten (based on retry count).

    Args:
        state: Current graph state containing retry_count

    Returns:
        True if should retry, False if max retries reached

    Example:
        >>> state = {"retry_count": 2, ...}
        >>> should_retry_query(state)
        True
    """
    max_retries = 3  # Could also load from settings
    should_retry = state["retry_count"] < max_retries

    if should_retry:
        logger.info(f"Retry count: {state['retry_count']}/{max_retries} - Can retry")
    else:
        logger.warning(f"Retry count: {state['retry_count']}/{max_retries} - Max retries reached")

    return should_retry


# Router registry for easy access
ROUTER_FUNCTIONS = {
    "decide_to_generate": decide_to_generate,
    "decide_to_web_search": decide_to_web_search,
    "check_hallucination_and_usefulness": check_hallucination_and_usefulness,
    "should_retry_query": should_retry_query,
}


def get_router(router_name: str):
    """
    Get a router function by name.

    Args:
        router_name: Name of the router function

    Returns:
        The corresponding router function

    Raises:
        ValueError: If router_name is not found

    Example:
        >>> router = get_router("decide_to_generate")
        >>> next_node = router(state)
    """
    if router_name not in ROUTER_FUNCTIONS:
        raise ValueError(f"Unknown router: {router_name}. Available routers: {list(ROUTER_FUNCTIONS.keys())}")

    return ROUTER_FUNCTIONS[router_name]


if __name__ == "__main__":
    """Test router functions with sample states."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("=" * 80)
    print("Testing Router Functions")
    print("=" * 80)

    # Test decide_to_generate with relevant documents
    print("\n1. Testing decide_to_generate with relevant documents:")
    print("-" * 80)
    state_with_relevant = {
        "question": "What is Agentic RAG?",
        "generation": "",
        "web_search": "No",
        "documents": [None] * 3,
        "retry_count": 0,
        "relevance_scores": ["yes", "no", "yes"]
    }
    result = decide_to_generate(state_with_relevant)
    print(f"Relevance scores: {state_with_relevant['relevance_scores']}")
    print(f"Next node: {result}")

    # Test decide_to_generate with no relevant documents
    print("\n2. Testing decide_to_generate with no relevant documents:")
    print("-" * 80)
    state_without_relevant = {
        "question": "What is Agentic RAG?",
        "generation": "",
        "web_search": "No",
        "documents": [None] * 3,
        "retry_count": 0,
        "relevance_scores": ["no", "no", "no"]
    }
    result = decide_to_generate(state_without_relevant)
    print(f"Relevance scores: {state_without_relevant['relevance_scores']}")
    print(f"Next node: {result}")

    # Test should_retry_query
    print("\n3. Testing should_retry_query:")
    print("-" * 80)
    for retry_count in [0, 1, 2, 3]:
        state = {
            "question": "",
            "generation": "",
            "web_search": "No",
            "documents": [],
            "retry_count": retry_count,
            "relevance_scores": []
        }
        can_retry = should_retry_query(state)
        print(f"Retry count: {retry_count} - Can retry: {can_retry}")

    print("\n" + "=" * 80)
    print("Router function tests completed")
    print("=" * 80)
