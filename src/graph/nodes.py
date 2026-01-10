"""
Node Functions for Agentic RAG Workflow

This module implements all node functions that process the state
as it flows through the LangGraph state machine.
"""

import logging
from typing import List

from langchain_core.documents import Document

from src.graph.state import GraphState
from src.vectorstore.chroma_store import similarity_search, get_retriever
from src.agents.generator import AnswerGenerator
from config.settings import settings


logger = logging.getLogger(__name__)


def retrieve(state: GraphState) -> dict:
    """
    Retrieve documents from the vector store based on the question.

    This node performs a similarity search in the ChromaDB vector store
    to find the most relevant documents for the user's question.

    Args:
        state: Current graph state containing the question

    Returns:
        Dictionary with updated documents field

    Example:
        >>> state = {"question": "What is Agentic RAG?", ...}
        >>> result = retrieve(state)
        >>> print(result["documents"])
        [Document1, Document2, Document3, Document4]
    """
    logger.info("Node: retrieve")
    logger.debug(f"Retrieving documents for question: {state['question']}")

    try:
        # Perform similarity search
        documents = similarity_search(
            query=state["question"],
            k=settings.RETRIEVAL_K
        )

        logger.info(f"Retrieved {len(documents)} documents")

        # Log document sources for debugging
        for i, doc in enumerate(documents):
            logger.debug(f"  Document {i+1}: source={doc.metadata.get('source', 'unknown')}")

        return {"documents": documents}

    except Exception as e:
        logger.error(f"Retrieval failed: {e}")
        # Return empty documents on failure - system can degrade gracefully
        return {"documents": []}


def generate(state: GraphState) -> dict:
    """
    Generate an answer using retrieved documents.

    This node uses the RAG (Retrieval-Augmented Generation) pattern to
    generate a concise answer based on the retrieved context documents.

    Args:
        state: Current graph state containing question and documents

    Returns:
        Dictionary with updated generation field

    Raises:
        ValueError: If no documents are available

    Example:
        >>> state = {
        ...     "question": "What is Agentic RAG?",
        ...     "documents": [doc1, doc2, doc3],
        ...     ...
        ... }
        >>> result = generate(state)
        >>> print(result["generation"])
        "Agentic RAG is a system that uses..."
    """
    logger.info("Node: generate")
    logger.debug(f"Generating answer for question: {state['question']}")

    if not state["documents"]:
        logger.warning("No documents available for generation")
        return {
            "generation": "I apologize, but I don't have enough relevant information to answer this question."
        }

    try:
        # Initialize generator
        generator = AnswerGenerator()

        # Generate answer
        answer = generator.generate(
            question=state["question"],
            documents=state["documents"]
        )

        logger.info("Answer generated successfully")
        logger.debug(f"Generated answer: {answer[:200]}...")

        return {"generation": answer}

    except Exception as e:
        logger.error(f"Generation failed: {e}")
        return {
            "generation": f"I encountered an error while generating the answer: {str(e)}"
        }


def grade_documents(state: GraphState) -> dict:
    """
    Grade retrieved documents for relevance to the question.

    This node evaluates each retrieved document to determine if it's
    relevant to the user's question. Uses an LLM to perform binary
    classification (yes/no) for each document.

    Args:
        state: Current graph state containing question and documents

    Returns:
        Dictionary with updated relevance_scores field

    Example:
        >>> state = {
        ...     "question": "What is Agentic RAG?",
        ...     "documents": [doc1, doc2, doc3],
        ...     ...
        ... }
        >>> result = grade_documents(state)
        >>> print(result["relevance_scores"])
        ["yes", "yes", "no"]
    """
    logger.info("Node: grade_documents")

    if not state["documents"]:
        logger.warning("No documents to grade")
        return {"relevance_scores": []}

    try:
        # Import DocumentGrader
        from src.agents.graders import DocumentGrader

        # Initialize grader
        grader = DocumentGrader()

        # Grade all documents
        logger.info(f"Grading {len(state['documents'])} documents")
        scores = grader.grade_batch(state["question"], state["documents"])

        # Count relevant documents
        relevant_count = sum(1 for s in scores if s == "yes")
        logger.info(f"Grading complete: {relevant_count}/{len(scores)} documents relevant")

        # Log individual scores
        for i, (doc, score) in enumerate(zip(state["documents"], scores)):
            source = doc.metadata.get("source", "unknown")
            logger.debug(f"  Document {i+1}: {score} (source: {source})")

        return {"relevance_scores": scores}

    except Exception as e:
        logger.error(f"Document grading failed: {e}")
        # On failure, grade all as relevant to allow system to continue
        logger.warning("Falling back: grading all documents as relevant")
        return {"relevance_scores": ["yes"] * len(state["documents"])}


def transform_query(state: GraphState) -> dict:
    """
    Transform the query to improve retrieval.

    This node rewrites the user's question to be more specific and
    better optimized for vector store retrieval.

    Args:
        state: Current graph state containing question and retry_count

    Returns:
        Dictionary with updated question and retry_count fields

    Example:
        >>> state = {
        ...     "question": "How does it work?",
        ...     "retry_count": 0,
        ...     ...
        ... }
        >>> result = transform_query(state)
        >>> print(result["question"])
        "How does the Agentic RAG system use LangGraph for workflow management?"
    """
    logger.info("Node: transform_query")

    try:
        # Import QueryRewriter
        from src.agents.rewriter import QueryRewriter

        # Initialize rewriter
        rewriter = QueryRewriter()

        # Rewrite the question
        logger.info(f"Original question: {state['question']}")
        improved_question = rewriter.rewrite(state["question"])
        logger.info(f"Improved question: {improved_question}")

        # Increment retry count
        new_retry_count = state["retry_count"] + 1
        logger.info(f"Retry count: {new_retry_count}")

        return {
            "question": improved_question,
            "retry_count": new_retry_count
        }

    except Exception as e:
        logger.error(f"Query transformation failed: {e}")
        # On failure, return original question and increment retry count
        logger.warning("Falling back to original question")
        return {
            "question": state["question"],
            "retry_count": state["retry_count"] + 1
        }


def web_search(state: GraphState) -> dict:
    """
    Perform web search to find additional information.

    This node performs a web search when local documents are insufficient
    to answer the question.

    Args:
        state: Current graph state containing question

    Returns:
        Dictionary with updated documents and web_search fields

    Note:
        This is a placeholder for Phase 6. Currently returns empty documents.
        Will be implemented with WebSearcher in Phase 6.

    Example:
        >>> state = {
        ...     "question": "Latest news about AI",
        ...     ...
        ... }
        >>> result = web_search(state)
        >>> print(len(result["documents"]))
        5
    """
    logger.info("Node: web_search")
    logger.info("Web search not yet implemented - Phase 6")
    logger.warning("Returning empty documents")

    # Placeholder: Return empty documents
    # Will implement with WebSearcher in Phase 6
    return {
        "documents": [],
        "web_search": "Yes"
    }


def check_hallucination(state: GraphState) -> dict:
    """
    Check if the generated answer is grounded in the documents.

    This node verifies that the answer doesn't contain information
    not supported by the retrieved documents.

    Args:
        state: Current graph state containing generation and documents

    Returns:
        Dictionary with hallucination check result

    Note:
        This is a placeholder for Phase 7. Currently returns "grounded".
        Will be implemented with HallucinationGrader in Phase 7.

    Example:
        >>> state = {
        ...     "generation": "Agentic RAG uses LangGraph...",
        ...     "documents": [doc1, doc2],
        ...     ...
        ... }
        >>> result = check_hallucination(state)
        >>> print(result["hallucination_check"])
        "grounded"
    """
    logger.info("Node: check_hallucination")
    logger.info("Hallucination check not yet implemented - Phase 7")
    logger.warning("Returning default 'grounded' result")

    # Placeholder: Return grounded
    # Will implement with HallucinationGrader in Phase 7
    return {"hallucination_check": "grounded"}


# Node registry for easy access
NODE_FUNCTIONS = {
    "retrieve": retrieve,
    "generate": generate,
    "grade_documents": grade_documents,
    "transform_query": transform_query,
    "web_search": web_search,
    "check_hallucination": check_hallucination,
}


def get_node(node_name: str):
    """
    Get a node function by name.

    Args:
        node_name: Name of the node function

    Returns:
        The corresponding node function

    Raises:
        ValueError: If node_name is not found

    Example:
        >>> node_func = get_node("retrieve")
        >>> result = node_func(state)
    """
    if node_name not in NODE_FUNCTIONS:
        raise ValueError(f"Unknown node: {node_name}. Available nodes: {list(NODE_FUNCTIONS.keys())}")

    return NODE_FUNCTIONS[node_name]


if __name__ == "__main__":
    """Test node functions with sample state."""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create sample state
    sample_state: GraphState = {
        "question": "What is Agentic RAG?",
        "generation": "",
        "web_search": "No",
        "documents": [],
        "retry_count": 0,
        "relevance_scores": []
    }

    print("=" * 80)
    print("Testing Node Functions")
    print("=" * 80)

    # Test retrieve node
    print("\n1. Testing retrieve node:")
    print("-" * 80)
    result = retrieve(sample_state)
    print(f"Retrieved {len(result['documents'])} documents")

    # Update state with retrieved documents
    sample_state["documents"] = result["documents"]

    # Test generate node
    print("\n2. Testing generate node:")
    print("-" * 80)
    result = generate(sample_state)
    print(f"Generated answer:\n{result['generation']}")

    print("\n" + "=" * 80)
    print("Node function tests completed")
    print("=" * 80)
