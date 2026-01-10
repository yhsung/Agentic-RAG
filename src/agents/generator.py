"""
Answer Generator for Agentic RAG System

This module implements the answer generation component that uses
retrieved documents to generate answers to user questions.
"""

import logging
from typing import List

from langchain_core.documents import Document
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

from config.settings import settings
from config.prompts import RAG_PROMPT


logger = logging.getLogger(__name__)


class AnswerGenerator:
    """
    Generates answers to questions using retrieved documents.

    This class uses an LLM (via Ollama) to generate concise answers
    based on retrieved context documents. It implements the RAG pattern
    (Retrieval-Augmented Generation).

    Attributes:
        llm: The Ollama LLM for generation
        rag_prompt: The prompt template for RAG
        chain: The complete RAG chain

    Example:
        >>> generator = AnswerGenerator()
        >>> question = "What is Agentic RAG?"
        >>> documents = [doc1, doc2, doc3]
        >>> answer = generator.generate(question, documents)
        >>> print(answer)
        "Agentic RAG is a system that..."
    """

    def __init__(self):
        """
        Initialize the AnswerGenerator with Ollama LLM.

        Loads the generation model from settings and builds the RAG chain.
        """
        logger.info(f"Initializing AnswerGenerator with model: {settings.GENERATION_MODEL}")

        # Initialize the LLM
        self.llm = ChatOllama(
            model=settings.GENERATION_MODEL,
            temperature=0,  # Use temperature 0 for deterministic output
            base_url=settings.OLLAMA_BASE_URL,
        )

        # Create the prompt template
        self.rag_prompt = ChatPromptTemplate.from_template(RAG_PROMPT)

        # Build the RAG chain
        self.chain = (
            {"context": self._format_documents, "question": RunnablePassthrough()}
            | self.rag_prompt
            | self.llm
            | StrOutputParser()
        )

        logger.info("AnswerGenerator initialized successfully")

    def _format_documents(self, documents: List[Document]) -> str:
        """
        Format documents into a single string for the prompt.

        Joins all document page_contents with double newlines between them.

        Args:
            documents: List of Document objects

        Returns:
            Formatted string with all document contents

        Example:
            >>> docs = [Document(page_content="Doc 1"), Document(page_content="Doc 2")]
            >>> formatted = self._format_documents(docs)
            >>> print(formatted)
            Doc 1

            Doc 2
        """
        return "\n\n".join(doc.page_content for doc in documents)

    def generate(self, question: str, documents: List[Document]) -> str:
        """
        Generate an answer to a question using retrieved documents.

        Args:
            question: The user's question
            documents: List of retrieved documents for context

        Returns:
            Generated answer string

        Raises:
            ValueError: If question is empty or no documents provided
            Exception: If generation fails

        Example:
            >>> generator = AnswerGenerator()
            >>> question = "What is Agentic RAG?"
            >>> documents = [doc1, doc2, doc3]
            >>> answer = generator.generate(question, documents)
        """
        if not question:
            raise ValueError("Question cannot be empty")

        if not documents:
            raise ValueError("At least one document must be provided")

        logger.info(f"Generating answer for question: {question[:100]}...")
        logger.debug(f"Number of context documents: {len(documents)}")

        try:
            # Format the context from documents
            context = self._format_documents(documents)

            # Create the prompt with question and context
            prompt = self.rag_prompt.invoke({"question": question, "context": context})

            # Generate the answer
            answer = self.llm.invoke(prompt)
            answer_text = answer.content

            logger.info("Answer generated successfully")
            logger.debug(f"Generated answer: {answer_text[:200]}...")

            return answer_text

        except Exception as e:
            logger.error(f"Failed to generate answer: {e}")
            raise Exception(f"Answer generation failed: {e}")

    def generate_stream(self, question: str, documents: List[Document]):
        """
        Generate an answer with streaming output.

        Yields chunks of the generated answer as they are produced.
        Useful for real-time display in CLI or UI.

        Args:
            question: The user's question
            documents: List of retrieved documents for context

        Yields:
            Chunks of the generated answer

        Example:
            >>> generator = AnswerGenerator()
            >>> for chunk in generator.generate_stream(question, documents):
            ...     print(chunk, end='', flush=True)
        """
        if not question:
            raise ValueError("Question cannot be empty")

        if not documents:
            raise ValueError("At least one document must be provided")

        logger.info(f"Generating streaming answer for question: {question[:100]}...")

        try:
            # Stream the RAG chain
            for chunk in self.chain.stream(question):
                yield chunk

        except Exception as e:
            logger.error(f"Failed to generate streaming answer: {e}")
            raise Exception(f"Streaming answer generation failed: {e}")

    def count_tokens(self, question: str, documents: List[Document]) -> dict:
        """
        Estimate token counts for the generation request.

        Useful for monitoring usage and costs.

        Args:
            question: The user's question
            documents: List of retrieved documents

        Returns:
            Dictionary with token counts (question, context, total)

        Example:
            >>> counts = generator.count_tokens(question, documents)
            >>> print(f"Total tokens: {counts['total']}")
        """
        # Rough estimation: 1 token ≈ 4 characters for English text
        question_tokens = len(question) // 4
        context_text = self._format_documents(documents)
        context_tokens = len(context_text) // 4

        return {
            "question": question_tokens,
            "context": context_tokens,
            "total": question_tokens + context_tokens
        }


# Convenience function for simple usage
def generate_answer(question: str, documents: List[Document]) -> str:
    """
    Convenience function to generate an answer.

    Args:
        question: The user's question
        documents: List of retrieved documents

    Returns:
        Generated answer string

    Example:
        >>> from src.agents.generator import generate_answer
        >>> answer = generate_answer(question, documents)
    """
    generator = AnswerGenerator()
    return generator.generate(question, documents)


if __name__ == "__main__":
    """Test the AnswerGenerator with sample data."""
    logging.basicConfig(level=logging.INFO)

    # Create sample documents
    sample_docs = [
        Document(
            page_content="Agentic RAG is a retrieval-augmented generation system that uses LangGraph for state management.",
            metadata={"source": "test"}
        ),
        Document(
            page_content="The system includes document grading, web search fallback, and hallucination detection.",
            metadata={"source": "test"}
        ),
        Document(
            page_content="ChromaDB is used as the vector store with Ollama embeddings for document retrieval.",
            metadata={"source": "test"}
        )
    ]

    # Test generation
    generator = AnswerGenerator()
    question = "What is Agentic RAG and what components does it include?"

    print("=" * 80)
    print("Testing AnswerGenerator")
    print("=" * 80)
    print(f"\nQuestion: {question}\n")
    print("Context Documents:")
    for i, doc in enumerate(sample_docs, 1):
        print(f"{i}. {doc.page_content}")
    print("\n" + "=" * 80)

    answer = generator.generate(question, sample_docs)

    print("\nGenerated Answer:")
    print(answer)
    print("\n" + "=" * 80)

    # Show token counts
    tokens = generator.count_tokens(question, sample_docs)
    print("\nToken Counts:")
    print(f"  Question: {tokens['question']} tokens")
    print(f"  Context: {tokens['context']} tokens")
    print(f"  Total: {tokens['total']} tokens")
    print("=" * 80)
