"""
Router Functions for Agentic RAG Workflow

This module implements conditional edge functions that determine
the routing logic in the LangGraph state machine.
"""

import logging
from typing import Literal

from src.graph.state import GraphState
from config.settings import settings


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

    Routing Logic:
    - All or most documents relevant → generate
    - Few or no documents relevant → web_search
    - Threshold: < 50% relevant documents triggers web search

    Args:
        state: Current graph state containing relevance_scores

    Returns:
        "web_search" if insufficient relevant docs, "generate" otherwise

    Example:
        >>> state = {"relevance_scores": ["yes", "yes", "no"], ...}
        >>> next_node = decide_to_web_search(state)
        >>> print(next_node)
        "generate"

        >>> state = {"relevance_scores": ["no", "no", "no"], ...}
        >>> next_node = decide_to_web_search(state)
        >>> print(next_node)
        "web_search"
    """
    logger.info("Router: decide_to_web_search")

    if not state["relevance_scores"]:
        logger.warning("No relevance scores - defaulting to web search")
        return "web_search"

    # Count relevant documents
    relevant_count = sum(1 for score in state["relevance_scores"] if score == "yes")
    total_count = len(state["relevance_scores"])
    relevance_ratio = relevant_count / total_count if total_count > 0 else 0

    logger.info(f"Relevant documents: {relevant_count}/{total_count} ({relevance_ratio:.1%})")

    # Decision: Web search if less than 50% of documents are relevant
    threshold = 0.5
    if relevance_ratio < threshold:
        logger.info(f"Decision: Relevance ratio {relevance_ratio:.1%} < {threshold:.1%} - trigger web search")
        return "web_search"
    else:
        logger.info(f"Decision: Relevance ratio {relevance_ratio:.1%} >= {threshold:.1%} - generate from local docs")
        return "generate"


def check_hallucination_and_usefulness(state: GraphState) -> Literal["generate", "transform_query", "end"]:
    """
    Check if the generated answer is grounded and useful.

    This router function verifies:
    1. Answer is grounded in documents (not hallucinated)
    2. Answer addresses the question (useful)

    Routing Logic:
    - Hallucinated (not_grounded) AND regenerations remaining → regenerate
    - Grounded but not useful AND retries remaining → transform_query
    - Hallucinated with no regenerations left → end (graceful degradation)
    - Not useful with no retries left → end (graceful degradation)
    - Grounded and useful → end (success)

    Args:
        state: Current graph state containing hallucination_check, usefulness_check,
               retry_count, and regeneration_count

    Returns:
        "generate" if hallucinated and regenerations remaining,
        "transform_query" if not useful and retries remaining,
        "end" if answer is good OR limits exhausted

    Example:
        >>> state = {
        ...     "hallucination_check": "grounded",
        ...     "usefulness_check": "useful",
        ...     "retry_count": 0,
        ...     "regeneration_count": 0,
        ...     ...
        ... }
        >>> next_node = check_hallucination_and_usefulness(state)
        >>> print(next_node)
        "end"

        >>> state = {
        ...     "hallucination_check": "not_grounded",
        ...     "usefulness_check": "useful",
        ...     "retry_count": 0,
        ...     "regeneration_count": 0,
        ...     ...
        ... }
        >>> next_node = check_hallucination_and_usefulness(state)
        >>> print(next_node)
        "generate"

        >>> state = {
        ...     "hallucination_check": "grounded",
        ...     "usefulness_check": "not_useful",
        ...     "retry_count": 0,
        ...     "regeneration_count": 0,
        ...     ...
        ... }
        >>> next_node = check_hallucination_and_usefulness(state)
        >>> print(next_node)
        "transform_query"
    """
    logger.info("Router: check_hallucination_and_usefulness")

    # Get check results from state
    hallucination_check = state.get("hallucination_check", "not_grounded")
    usefulness_check = state.get("usefulness_check", "not_useful")
    retry_count = state.get("retry_count", 0)
    regeneration_count = state.get("regeneration_count", 0)

    logger.info(
        f"Hallucination: {hallucination_check}, "
        f"Usefulness: {usefulness_check}, "
        f"Retries: {retry_count}/{settings.MAX_RETRIES}, "
        f"Regenerations: {regeneration_count}/{settings.MAX_REGENERATIONS}"
    )

    # Decision tree with limit checking:
    # 1. If answer is hallucinated (not grounded) → regenerate, if regenerations remaining
    if hallucination_check == "not_grounded":
        if regeneration_count < settings.MAX_REGENERATIONS:
            logger.warning(
                f"Answer hallucinated, regenerating "
                f"(attempt {regeneration_count + 1}/{settings.MAX_REGENERATIONS})"
            )
            return "generate"
        else:
            logger.error(
                f"Max regenerations ({settings.MAX_REGENERATIONS}) exceeded. "
                f"Returning best attempt despite hallucination."
            )
            return "end"  # Stop even if hallucinated (graceful degradation)

    # 2. If answer is grounded but not useful → transform query, if retries remaining
    if usefulness_check == "not_useful":
        if retry_count < settings.MAX_RETRIES:
            logger.warning(
                f"Answer not useful, rewriting query "
                f"(attempt {retry_count + 1}/{settings.MAX_RETRIES})"
            )
            return "transform_query"
        else:
            logger.error(
                f"Max retries ({settings.MAX_RETRIES}) exceeded. "
                f"Returning best attempt despite low usefulness."
            )
            return "end"  # Stop even if not useful (graceful degradation)

    # 3. Answer is both grounded and useful → end successfully
    logger.info("✓ Answer is grounded and useful - ending workflow")
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
        "web_search_needed": "No",
        "documents": [None] * 3,
        "retry_count": 0,
        "regeneration_count": 0,
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
        "web_search_needed": "No",
        "documents": [None] * 3,
        "retry_count": 0,
        "regeneration_count": 0,
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
            "web_search_needed": "No",
            "documents": [],
            "retry_count": retry_count,
            "regeneration_count": 0,
            "relevance_scores": []
        }
        can_retry = should_retry_query(state)
        print(f"Retry count: {retry_count} - Can retry: {can_retry}")

    print("\n" + "=" * 80)
    print("Router function tests completed")
    print("=" * 80)
