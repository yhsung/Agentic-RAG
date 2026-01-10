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
        web_search: "Yes" or "No" flag indicating if web search was performed
        documents: List of retrieved documents (chunks) from vector store
        retry_count: Number of query rewrite attempts (max 3 to prevent infinite loops)
        relevance_scores: List of document relevance grades ("yes" or "no")
        hallucination_check: Result of hallucination check ("grounded" or "not_grounded")
        usefulness_check: Result of usefulness check ("useful" or "not_useful")

    Example:
        >>> state: GraphState = {
        ...     "question": "What is Agentic RAG?",
        ...     "generation": "",
        ...     "web_search": "No",
        ...     "documents": [],
        ...     "retry_count": 0,
        ...     "relevance_scores": [],
        ...     "hallucination_check": "",
        ...     "usefulness_check": ""
        ... }
    """

    question: str
    """The user's original question/query"""

    generation: str
    """The LLM-generated answer (empty until generate node runs)"""

    web_search: str
    """Flag indicating if web search was performed: "Yes" or "No" """

    documents: List[Document]
    """List of retrieved documents (chunks) from vector store or web search"""

    retry_count: int
    """Number of query rewrite attempts (max 3 to prevent infinite loops)"""

    relevance_scores: List[str]
    """List of document relevance grades: "yes" or "no" for each document"""

    hallucination_check: str
    """Result of hallucination check: "grounded" or "not_grounded" """

    usefulness_check: str
    """Result of usefulness check: "useful" or "not_useful" """
