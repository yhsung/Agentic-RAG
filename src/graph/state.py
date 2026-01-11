"""
Graph State Definition for Agentic RAG System

This module defines the state structure that flows through the LangGraph
state machine. Each node in the graph receives this state, processes it,
and returns an updated version.
"""

from typing import List, TypedDict
from langchain_core.documents import Document


class GraphState(TypedDict):
    """
    State structure for the Agentic RAG workflow.

    This TypedDict defines all the fields that flow through the LangGraph
    state machine. Each node receives this state and can update any subset
    of fields before passing it to the next node.

    Attributes:
        question: The user's original question/query
        generation: The LLM-generated answer
        web_search_needed: "Yes" or "No" flag indicating if web search is needed
        documents: List of retrieved documents (chunks) from vector store
        retry_count: Number of query rewrite attempts (max 3 to prevent infinite loops)
        regeneration_count: Number of answer regeneration attempts for hallucination correction
        relevance_scores: List of document relevance grades ("yes" or "no")
        hallucination_check: Result of hallucination check ("grounded" or "not_grounded")
        usefulness_check: Result of usefulness check ("useful" or "not_useful")
        prompt_variant: The RAG prompt variant to use for answer generation (optional)

    Example:
        >>> state: GraphState = {
        ...     "question": "What is Agentic RAG?",
        ...     "generation": "",
        ...     "web_search_needed": "No",
        ...     "documents": [],
        ...     "retry_count": 0,
        ...     "regeneration_count": 0,
        ...     "relevance_scores": [],
        ...     "hallucination_check": "",
        ...     "usefulness_check": "",
        ...     "prompt_variant": "baseline"
        ... }
    """

    question: str
    """The user's original question/query"""

    generation: str
    """The LLM-generated answer (empty until generate node runs)"""

    web_search_needed: str
    """Flag indicating if web search is needed: "Yes" or "No" """

    documents: List[Document]
    """List of retrieved documents (chunks) from vector store or web search"""

    retry_count: int
    """Number of query rewrite attempts (max 3 to prevent infinite loops)"""

    regeneration_count: int
    """Number of answer regeneration attempts for hallucination correction (max 3)"""

    relevance_scores: List[str]
    """List of document relevance grades: "yes" or "no" for each document"""

    hallucination_check: str
    """Result of hallucination check: "grounded" or "not_grounded" """

    usefulness_check: str
    """Result of usefulness check: "useful" or "not_useful" """

    prompt_variant: str
    """The RAG prompt variant to use: "baseline", "detailed", "bullets", or "reasoning" """
