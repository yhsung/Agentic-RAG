"""
Query Rewriter for Agentic RAG System

This module implements intelligent query transformation to improve
retrieval quality by rewriting vague or unclear queries.
"""

import logging
from typing import List

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from config.settings import settings
from config.prompts import QUERY_REWRITER_PROMPT


logger = logging.getLogger(__name__)


class QueryRewriter:
    """
    Rewrites user queries to improve retrieval quality.

    Uses an LLM to transform vague, unclear, or suboptimal queries
    into more specific, well-formed questions optimized for vector
    store retrieval.

    Attributes:
        llm: The Ollama LLM for query rewriting
        prompt: The query rewriting prompt template
        chain: The complete rewriting chain

    Example:
        >>> rewriter = QueryRewriter()
        >>> original = "How does it work?"
        >>> improved = rewriter.rewrite(original)
        >>> print(improved)
        "How does the Agentic RAG system use LangGraph for workflow management?"
    """

    def __init__(self):
        """
        Initialize the QueryRewriter with Ollama LLM.

        Loads the grading model from settings and builds the rewriting chain.
        """
        logger.info(f"Initializing QueryRewriter with model: {settings.GRADING_MODEL}")

        # Initialize the LLM
        self.llm = ChatOllama(
            model=settings.GRADING_MODEL,
            temperature=0,  # Temperature 0 for deterministic rewriting
            base_url=settings.OLLAMA_BASE_URL,
        )

        # Create the prompt template
        self.prompt = ChatPromptTemplate.from_template(QUERY_REWRITER_PROMPT)

        # Build the chain
        self.chain = self.prompt | self.llm | StrOutputParser()

        logger.info("QueryRewriter initialized successfully")

    def rewrite(self, question: str) -> str:
        """
        Rewrite a question to improve retrieval quality.

        Args:
            question: The original question to rewrite

        Returns:
            Improved question string

        Raises:
            ValueError: If question is empty
            Exception: If rewriting fails

        Example:
            >>> rewriter = QueryRewriter()
            >>> improved = rewriter.rewrite("How does it work?")
            >>> print(improved)
            "How does the Agentic RAG system use LangGraph for workflow management?"
        """
        if not question:
            raise ValueError("Question cannot be empty")

        logger.info(f"Rewriting question: {question[:100]}...")
        logger.debug(f"Original question: {question}")

        try:
            # Invoke the rewriting chain
            improved_question = self.chain.invoke({"question": question})

            # Clean up the response
            improved_question = improved_question.strip()

            # Remove quotes if present
            if improved_question.startswith('"') and improved_question.endswith('"'):
                improved_question = improved_question[1:-1]
            elif improved_question.startswith("'") and improved_question.endswith("'"):
                improved_question = improved_question[1:-1]

            logger.info("Question rewritten successfully")
            logger.debug(f"Improved question: {improved_question}")

            return improved_question

        except Exception as e:
            logger.error(f"Failed to rewrite question: {e}")
            # On failure, return original question
            logger.warning("Falling back to original question")
            return question

    def rewrite_with_history(
        self,
        question: str,
        previous_questions: List[str],
        previous_scores: List[List[str]]
    ) -> str:
        """
        Rewrite question considering retrieval history.

        This advanced version looks at previous query attempts and their
        relevance scores to inform the rewriting strategy.

        Args:
            question: The current question to rewrite
            previous_questions: List of previous query attempts
            previous_scores: List of relevance scores for each previous attempt

        Returns:
            Improved question string

        Example:
            >>> rewriter = QueryRewriter()
            >>> improved = rewriter.rewrite_with_history(
            ...     "How does it work?",
            ...     ["What is this?", "How does it work?"],
            ...     [["no", "no", "no", "no"], ["no", "no", "no", "no"]]
            ... )
        """
        if not question:
            raise ValueError("Question cannot be empty")

        logger.info(f"Rewriting question with history: {question[:100]}...")

        # Build context from history
        context_parts = []
        if previous_questions:
            context_parts.append("Previous query attempts:")
            for i, (prev_q, scores) in enumerate(zip(previous_questions, previous_scores), 1):
                relevant_count = sum(1 for s in scores if s == "yes")
                context_parts.append(f"{i}. '{prev_q}' - {relevant_count}/{len(scores)} relevant")

        # If we have history, use it to inform the rewrite
        if context_parts:
            history_context = "\n".join(context_parts)
            logger.debug(f"Retrieval history:\n{history_context}")

            # For now, use the standard rewrite
            # TODO: Could enhance the prompt to include history context
            return self.rewrite(question)
        else:
            return self.rewrite(question)

    def should_rewrite(self, question: str, relevance_scores: List[str]) -> bool:
        """
        Determine if a question should be rewritten based on retrieval results.

        Args:
            question: The current question
            relevance_scores: List of relevance scores from retrieval

        Returns:
            True if should rewrite, False otherwise

        Example:
            >>> rewriter = QueryRewriter()
            >>> should_rewrite = rewriter.should_rewrite(
            ...     question,
            ...     ["no", "no", "no", "no"]
            ... )
            >>> print(should_rewrite)
            True
        """
        # Calculate relevance
        if not relevance_scores:
            return True  # No scores, should rewrite

        relevant_count = sum(1 for s in relevance_scores if s == "yes")
        total_count = len(relevance_scores)

        # If no relevant documents, should rewrite
        if relevant_count == 0:
            logger.info("No relevant documents found - should rewrite")
            return True

        # If low relevance (less than 50%), consider rewriting
        if relevant_count / total_count < 0.5:
            logger.info(f"Low relevance ({relevant_count}/{total_count}) - should rewrite")
            return True

        logger.info(f"Good relevance ({relevant_count}/{total_count}) - no rewrite needed")
        return False


# Convenience functions for simple usage
def rewrite_query(question: str) -> str:
    """
    Convenience function to rewrite a single query.

    Args:
        question: The question to rewrite

    Returns:
        Improved question string

    Example:
        >>> from src.agents.rewriter import rewrite_query
        >>> improved = rewrite_query("How does it work?")
        >>> print(improved)
    """
    rewriter = QueryRewriter()
    return rewriter.rewrite(question)


if __name__ == "__main__":
    """Test the QueryRewriter with sample data."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("=" * 80)
    print("Testing Query Rewriter")
    print("=" * 80)

    rewriter = QueryRewriter()

    # Test 1: Vague question
    print("\n1. Testing vague question:")
    print("-" * 80)
    question1 = "How does it work?"
    print(f"Original: {question1}")
    improved1 = rewriter.rewrite(question1)
    print(f"Improved: {improved1}")

    # Test 2: Specific question (should remain similar)
    print("\n2. Testing specific question:")
    print("-" * 80)
    question2 = "What is Agentic RAG and how does it use LangGraph?"
    print(f"Original: {question2}")
    improved2 = rewriter.rewrite(question2)
    print(f"Improved: {improved2}")

    # Test 3: Unclear reference
    print("\n3. Testing unclear reference:")
    print("-" * 80)
    question3 = "What components does it use?"
    print(f"Original: {question3}")
    improved3 = rewriter.rewrite(question3)
    print(f"Improved: {improved3}")

    # Test 4: should_rewrite decision
    print("\n4. Testing should_rewrite logic:")
    print("-" * 80)

    test_cases = [
        (["no", "no", "no", "no"], True),
        (["yes", "no", "no", "no"], True),
        (["yes", "yes", "no", "no"], False),
        (["yes", "yes", "yes", "yes"], False),
    ]

    for scores, expected in test_cases:
        should = rewriter.should_rewrite("test question", scores)
        result = "✓" if should == expected else "✗"
        print(f"{result} Scores {scores} → Should rewrite: {should} (expected: {expected})")

    print("\n" + "=" * 80)
    print("Query Rewriter tests completed")
    print("=" * 80)
