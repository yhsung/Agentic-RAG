"""
Grader Agents for Agentic RAG System

This module implements grading agents that evaluate different aspects
of the RAG system, including document relevance, hallucination detection,
and answer usefulness.
"""

import json
import logging
from typing import Dict, Any

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document

from config.settings import settings
from config.prompts import (
    RELEVANCE_GRADER_PROMPT,
    HALLUCINATION_GRADER_PROMPT,
    ANSWER_GRADER_PROMPT
)


logger = logging.getLogger(__name__)


class DocumentGrader:
    """
    Evaluates the relevance of retrieved documents to a user's question.

    Uses an LLM to perform binary classification (yes/no) on whether
    a document is relevant to the question. This enables the system
    to filter out irrelevant context and improve answer quality.

    Attributes:
        llm: The Ollama LLM for grading
        prompt: The relevance grading prompt template
        chain: The complete grading chain

    Example:
        >>> grader = DocumentGrader()
        >>> question = "What is Agentic RAG?"
        >>> document = Document(page_content="Agentic RAG is a system...")
        >>> result = grader.grade(question, document)
        >>> print(result)
        "yes"  # or "no"
    """

    def __init__(self):
        """
        Initialize the DocumentGrader with Ollama LLM.

        Loads the grading model from settings and builds the grading chain.
        """
        logger.info(f"Initializing DocumentGrader with model: {settings.GRADING_MODEL}")

        # Initialize the LLM
        self.llm = ChatOllama(
            model=settings.GRADING_MODEL,
            temperature=0,  # Temperature 0 for deterministic grading
            base_url=settings.OLLAMA_BASE_URL,
        )

        # Create the prompt template
        self.prompt = ChatPromptTemplate.from_template(RELEVANCE_GRADER_PROMPT)

        logger.info("DocumentGrader initialized successfully")

    def grade(self, question: str, document: Document) -> str:
        """
        Grade a document's relevance to a question.

        Args:
            question: The user's question
            document: The document to grade

        Returns:
            "yes" if document is relevant, "no" if not relevant

        Raises:
            ValueError: If question or document is empty
            Exception: If grading fails

        Example:
            >>> grader = DocumentGrader()
            >>> question = "What is Agentic RAG?"
            >>> document = Document(page_content="Agentic RAG uses LangGraph...")
            >>> result = grader.grade(question, document)
            >>> print(result)
            "yes"
        """
        if not question:
            raise ValueError("Question cannot be empty")

        if not document or not document.page_content:
            raise ValueError("Document cannot be empty")

        logger.debug(f"Grading document for question: {question[:100]}...")
        logger.debug(f"Document preview: {document.page_content[:100]}...")

        try:
            # Create the prompt with question and document
            prompt = self.prompt.invoke({
                "question": question,
                "document": document.page_content
            })

            # Generate the grade
            response = self.llm.invoke(prompt)
            response_text = response.content.strip()

            # Parse JSON response
            try:
                # Try to parse as JSON
                result = json.loads(response_text)
                score = result.get("score", "").lower()

                # Validate score
                if score not in ["yes", "no"]:
                    logger.warning(f"Invalid score '{score}', defaulting to 'no'")
                    score = "no"

                logger.debug(f"Document graded as: {score}")
                return score

            except json.JSONDecodeError:
                # Fallback: check if response contains "yes"
                logger.warning(f"Failed to parse JSON, using text matching")
                if "yes" in response_text.lower():
                    return "yes"
                else:
                    return "no"

        except Exception as e:
            logger.error(f"Failed to grade document: {e}")
            raise Exception(f"Document grading failed: {e}")

    def grade_batch(self, question: str, documents: list[Document]) -> list[str]:
        """
        Grade multiple documents for relevance to a question.

        Args:
            question: The user's question
            documents: List of documents to grade

        Returns:
            List of "yes"/"no" scores for each document

        Example:
            >>> grader = DocumentGrader()
            >>> scores = grader.grade_batch(question, documents)
            >>> print(scores)
            ["yes", "yes", "no", "yes"]
        """
        logger.info(f"Grading {len(documents)} documents")

        scores = []
        for i, doc in enumerate(documents):
            logger.debug(f"Grading document {i+1}/{len(documents)}")
            score = self.grade(question, doc)
            scores.append(score)

        # Count relevant documents
        relevant_count = sum(1 for s in scores if s == "yes")
        logger.info(f"Grading complete: {relevant_count}/{len(documents)} relevant")

        return scores


class HallucinationGrader:
    """
    Evaluates whether a generated answer is grounded in source documents.

    Checks if the answer contains information not supported by the retrieved
    documents, which indicates hallucination.

    Attributes:
        llm: The Ollama LLM for grading
        prompt: The hallucination grading prompt template

    Example:
        >>> grader = HallucinationGrader()
        >>> generation = "Agentic RAG uses LangGraph..."
        >>> documents = [doc1, doc2]
        >>> result = grader.grade(generation, documents)
        >>> print(result)
        "yes"  # grounded
    """

    def __init__(self):
        """
        Initialize the HallucinationGrader with Ollama LLM.
        """
        logger.info(f"Initializing HallucinationGrader with model: {settings.GRADING_MODEL}")

        # Initialize the LLM
        self.llm = ChatOllama(
            model=settings.GRADING_MODEL,
            temperature=0,
            base_url=settings.OLLAMA_BASE_URL,
        )

        # Create the prompt template
        self.prompt = ChatPromptTemplate.from_template(HALLUCINATION_GRADER_PROMPT)

        logger.info("HallucinationGrader initialized successfully")

    def grade(self, generation: str, documents: list[Document]) -> str:
        """
        Grade whether a generation is grounded in documents.

        Args:
            generation: The generated answer
            documents: The source documents

        Returns:
            "yes" if grounded, "no" if hallucinated

        Example:
            >>> grader = HallucinationGrader()
            >>> result = grader.grade("Agentic RAG uses...", documents)
            >>> print(result)
            "yes"
        """
        if not generation:
            raise ValueError("Generation cannot be empty")

        if not documents:
            raise ValueError("At least one document must be provided")

        logger.debug(f"Checking if generation is grounded: {generation[:100]}...")

        try:
            # Format documents into context
            context = "\n\n".join(doc.page_content for doc in documents)

            # Create the prompt
            prompt = self.prompt.invoke({
                "documents": context,
                "generation": generation
            })

            # Generate the grade
            response = self.llm.invoke(prompt)
            response_text = response.content.strip()

            # Parse JSON response
            try:
                result = json.loads(response_text)
                score = result.get("score", "").lower()

                if score not in ["yes", "no"]:
                    logger.warning(f"Invalid score '{score}', defaulting to 'no'")
                    score = "no"

                logger.debug(f"Hallucination check: {score}")
                return score

            except json.JSONDecodeError:
                logger.warning(f"Failed to parse JSON, using text matching")
                if "yes" in response_text.lower():
                    return "yes"
                else:
                    return "no"

        except Exception as e:
            logger.error(f"Failed to grade hallucination: {e}")
            raise Exception(f"Hallucination grading failed: {e}")


class AnswerGrader:
    """
    Evaluates whether an answer addresses the user's question.

    Checks if the answer actually resolves the question or if it's
    incomplete/unrelated.

    Attributes:
        llm: The Ollama LLM for grading
        prompt: The answer grading prompt template

    Example:
        >>> grader = AnswerGrader()
        >>> question = "What is Agentic RAG?"
        >>> generation = "Agentic RAG is a system that..."
        >>> result = grader.grade(question, generation)
        >>> print(result)
        "yes"  # addresses question
    """

    def __init__(self):
        """
        Initialize the AnswerGrader with Ollama LLM.
        """
        logger.info(f"Initializing AnswerGrader with model: {settings.GRADING_MODEL}")

        # Initialize the LLM
        self.llm = ChatOllama(
            model=settings.GRADING_MODEL,
            temperature=0,
            base_url=settings.OLLAMA_BASE_URL,
        )

        # Create the prompt template
        self.prompt = ChatPromptTemplate.from_template(ANSWER_GRADER_PROMPT)

        logger.info("AnswerGrader initialized successfully")

    def grade(self, question: str, generation: str) -> str:
        """
        Grade whether an answer addresses the question.

        Args:
            question: The user's question
            generation: The generated answer

        Returns:
            "yes" if addresses question, "no" if not

        Example:
            >>> grader = AnswerGrader()
            >>> result = grader.grade("What is it?", "It's a system...")
            >>> print(result)
            "yes"
        """
        if not question:
            raise ValueError("Question cannot be empty")

        if not generation:
            raise ValueError("Generation cannot be empty")

        logger.debug(f"Checking if answer addresses question: {question[:100]}...")

        try:
            # Create the prompt
            prompt = self.prompt.invoke({
                "question": question,
                "generation": generation
            })

            # Generate the grade
            response = self.llm.invoke(prompt)
            response_text = response.content.strip()

            # Parse JSON response
            try:
                result = json.loads(response_text)
                score = result.get("score", "").lower()

                if score not in ["yes", "no"]:
                    logger.warning(f"Invalid score '{score}', defaulting to 'no'")
                    score = "no"

                logger.debug(f"Answer usefulness check: {score}")
                return score

            except json.JSONDecodeError:
                logger.warning(f"Failed to parse JSON, using text matching")
                if "yes" in response_text.lower():
                    return "yes"
                else:
                    return "no"

        except Exception as e:
            logger.error(f"Failed to grade answer: {e}")
            raise Exception(f"Answer grading failed: {e}")


# Convenience functions for simple usage
def grade_document(question: str, document: Document) -> str:
    """
    Convenience function to grade a single document.

    Args:
        question: The user's question
        document: The document to grade

    Returns:
        "yes" if relevant, "no" if not
    """
    grader = DocumentGrader()
    return grader.grade(question, document)


def grade_documents(question: str, documents: list[Document]) -> list[str]:
    """
    Convenience function to grade multiple documents.

    Args:
        question: The user's question
        documents: List of documents to grade

    Returns:
        List of "yes"/"no" scores
    """
    grader = DocumentGrader()
    return grader.grade_batch(question, documents)


if __name__ == "__main__":
    """Test the graders with sample data."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("=" * 80)
    print("Testing Document Grader")
    print("=" * 80)

    # Test DocumentGrader
    question = "What is Agentic RAG?"

    relevant_doc = Document(
        page_content="Agentic RAG is a retrieval-augmented generation system that uses LangGraph for state management.",
        metadata={"source": "test"}
    )

    irrelevant_doc = Document(
        page_content="The weather in San Francisco is typically mild and foggy.",
        metadata={"source": "test"}
    )

    grader = DocumentGrader()

    print("\n1. Testing relevant document:")
    print("-" * 80)
    print(f"Question: {question}")
    print(f"Document: {relevant_doc.page_content}")
    score1 = grader.grade(question, relevant_doc)
    print(f"Score: {score1}")

    print("\n2. Testing irrelevant document:")
    print("-" * 80)
    print(f"Question: {question}")
    print(f"Document: {irrelevant_doc.page_content}")
    score2 = grader.grade(question, irrelevant_doc)
    print(f"Score: {score2}")

    print("\n" + "=" * 80)
    print("Document Grader tests completed")
    print("=" * 80)
