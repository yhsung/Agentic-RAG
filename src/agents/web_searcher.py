"""
Web Search Agent for Agentic RAG System

This module implements web search functionality using Tavily API (primary)
and DuckDuckGo (fallback) to retrieve external information when local
documents are insufficient.
"""

import logging
from typing import List, Optional

from langchain_core.documents import Document
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate

from config.settings import settings
from config.prompts import WEB_SEARCH_QUERY_PROMPT

# Try to import web search libraries
try:
    from tavily import TavilyClient
    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False
    logging.warning("Tavily not available. Install with: pip install tavily-python")

try:
    from duckduckgo_search import DDGS
    DUCKDUCKGO_AVAILABLE = True
except ImportError:
    DUCKDUCKGO_AVAILABLE = False
    logging.warning("DuckDuckGo search not available. Install with: pip install duckduckgo-search")


logger = logging.getLogger(__name__)


class WebSearcher:
    """
    Performs web searches to retrieve external information.

    Uses Tavily API as primary search engine (when API key is available)
    and falls back to DuckDuckGo when Tavily is not configured.

    Attributes:
        tavily_client: Tavily API client (if API key provided)
        llm: Ollama LLM for optimizing search queries
        query_prompt: Template for converting questions to search queries

    Example:
        >>> searcher = WebSearcher()
        >>> documents = searcher.search("What is the latest AI news?")
        >>> print(len(documents))
        3
    """

    def __init__(self):
        """
        Initialize the WebSearcher with available search engines.
        """
        logger.info("Initializing WebSearcher")

        # Initialize Tavily if API key is available
        self.tavily_client = None
        if TAVILY_AVAILABLE and settings.TAVILY_API_KEY:
            try:
                self.tavily_client = TavilyClient(api_key=settings.TAVILY_API_KEY)
                logger.info("Tavily client initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize Tavily client: {e}")

        # Check DuckDuckGo availability
        self.ddg_available = DUCKDUCKGO_AVAILABLE
        if self.ddg_available:
            logger.info("DuckDuckGo search available as fallback")

        # Initialize LLM for query optimization
        self.llm = ChatOllama(
            model=settings.GENERATION_MODEL,
            temperature=0,
            base_url=settings.OLLAMA_BASE_URL,
        )
        self.query_prompt = ChatPromptTemplate.from_template(WEB_SEARCH_QUERY_PROMPT)

        # Log available search methods
        if not self.tavily_client and not self.ddg_available:
            logger.warning("No web search engines available!")
        else:
            methods = []
            if self.tavily_client:
                methods.append("Tavily")
            if self.ddg_available:
                methods.append("DuckDuckGo")
            logger.info(f"Available search methods: {', '.join(methods)}")

    def _optimize_search_query(self, question: str) -> str:
        """
        Optimize a question for web search engines.

        Args:
            question: The user's question

        Returns:
            Optimized search query (3-6 words)

        Example:
            >>> searcher = WebSearcher()
            >>> query = searcher._optimize_search_query("What are the main benefits of using LangGraph for building agents?")
            >>> print(query)
            "LangGraph benefits building agents"
        """
        try:
            # Generate optimized query
            prompt = self.query_prompt.invoke({"question": question})
            response = self.llm.invoke(prompt)
            optimized_query = response.content.strip()

            logger.debug(f"Optimized query: '{question}' -> '{optimized_query}'")
            return optimized_query

        except Exception as e:
            logger.warning(f"Failed to optimize query: {e}")
            # Fallback to original question
            return question

    def _search_tavily(self, query: str, max_results: int) -> List[Document]:
        """
        Perform web search using Tavily API.

        Args:
            query: Search query
            max_results: Maximum number of results to return

        Returns:
            List of Document objects with search results

        Raises:
            Exception: If Tavily search fails
        """
        if not self.tavily_client:
            raise Exception("Tavily client not initialized")

        logger.info(f"Searching Tavily with query: {query}")

        try:
            # Perform search
            response = self.tavily_client.search(
                query=query,
                max_results=max_results,
                search_depth="basic",  # Use "advanced" for deeper search
                include_answer=False,
                include_raw_content=False,
                include_images=False,
            )

            # Convert results to Documents
            documents = []
            for result in response.get("results", []):
                doc = Document(
                    page_content=result.get("content", ""),
                    metadata={
                        "source": result.get("url", ""),
                        "title": result.get("title", ""),
                        "score": result.get("score", 0.0),
                        "search_engine": "tavily"
                    }
                )
                documents.append(doc)

            logger.info(f"Tavily search returned {len(documents)} results")
            return documents

        except Exception as e:
            logger.error(f"Tavily search failed: {e}")
            raise Exception(f"Tavily search error: {e}")

    def _search_duckduckgo(self, query: str, max_results: int) -> List[Document]:
        """
        Perform web search using DuckDuckGo.

        Args:
            query: Search query
            max_results: Maximum number of results to return

        Returns:
            List of Document objects with search results

        Raises:
            Exception: If DuckDuckGo search fails
        """
        if not self.ddg_available:
            raise Exception("DuckDuckGo search not available")

        logger.info(f"Searching DuckDuckGo with query: {query}")

        try:
            # Perform search
            ddgs = DDGS()
            results = ddgs.text(
                query,
                max_results=max_results
            )

            # Convert results to Documents
            documents = []
            if results:
                for result in results:
                    doc = Document(
                        page_content=result.get("body", ""),
                        metadata={
                            "source": result.get("link", ""),
                            "title": result.get("title", ""),
                            "search_engine": "duckduckgo"
                        }
                    )
                    documents.append(doc)

            logger.info(f"DuckDuckGo search returned {len(documents)} results")
            return documents

        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {e}")
            raise Exception(f"DuckDuckGo search error: {e}")

    def search(self, question: str, max_results: Optional[int] = None) -> List[Document]:
        """
        Perform web search for the given question.

        Tries Tavily first (if configured), falls back to DuckDuckGo.

        Args:
            question: The user's question
            max_results: Maximum number of results (defaults to settings.WEB_SEARCH_MAX_RESULTS)

        Returns:
            List of Document objects with search results

        Raises:
            Exception: If all search methods fail

        Example:
            >>> searcher = WebSearcher()
            >>> docs = searcher.search("What is LangGraph?")
            >>> print(f"Found {len(docs)} results")
            Found 3 results
            >>> print(docs[0].metadata["title"])
            "LangGraph Tutorial"
        """
        if not question:
            raise ValueError("Question cannot be empty")

        max_results = max_results or settings.WEB_SEARCH_MAX_RESULTS

        logger.info(f"Web search for question: {question[:100]}...")

        # Optimize query for web search
        search_query = self._optimize_search_query(question)

        # Try Tavily first
        if self.tavily_client:
            try:
                documents = self._search_tavily(search_query, max_results)
                if documents:
                    logger.info("Web search successful using Tavily")
                    return documents
            except Exception as e:
                logger.warning(f"Tavily search failed: {e}")

        # Fall back to DuckDuckGo
        if self.ddg_available:
            try:
                documents = self._search_duckduckgo(search_query, max_results)
                if documents:
                    logger.info("Web search successful using DuckDuckGo")
                    return documents
            except Exception as e:
                logger.warning(f"DuckDuckGo search failed: {e}")

        # All methods failed
        error_msg = "Web search failed: No search engines available or all searches failed"
        logger.error(error_msg)
        raise Exception(error_msg)

    def is_available(self) -> bool:
        """
        Check if any web search method is available.

        Returns:
            True if Tavily or DuckDuckGo is available

        Example:
            >>> searcher = WebSearcher()
            >>> if searcher.is_available():
            ...     docs = searcher.search("AI news")
        """
        return self.tavily_client is not None or self.ddg_available


# Convenience function for simple usage
def web_search(question: str, max_results: Optional[int] = None) -> List[Document]:
    """
    Convenience function to perform web search.

    Args:
        question: The user's question
        max_results: Maximum number of results

    Returns:
        List of Document objects with search results

    Example:
        >>> from src.agents.web_searcher import web_search
        >>> docs = web_search("What is LangGraph?")
        >>> print(len(docs))
        3
    """
    searcher = WebSearcher()
    return searcher.search(question, max_results)


if __name__ == "__main__":
    """Test the web searcher with sample queries."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("=" * 80)
    print("Testing Web Searcher")
    print("=" * 80)

    searcher = WebSearcher()

    if not searcher.is_available():
        print("\n⚠️  No web search engines available!")
        print("To enable web search:")
        print("  1. Tavily: Set TAVILY_API_KEY in .env file")
        print("  2. DuckDuckGo: Install with: pip install duckduckgo-search")
        exit(1)

    # Test search
    question = "What is LangGraph?"

    print(f"\n🔍 Searching for: {question}")
    print("-" * 80)

    try:
        documents = searcher.search(question, max_results=3)

        print(f"\n✅ Found {len(documents)} results:\n")

        for i, doc in enumerate(documents, 1):
            print(f"{i}. {doc.metadata.get('title', 'No title')}")
            print(f"   Source: {doc.metadata.get('source', 'Unknown')}")
            print(f"   Engine: {doc.metadata.get('search_engine', 'Unknown')}")
            print(f"   Content: {doc.page_content[:200]}...")
            print()

    except Exception as e:
        print(f"\n❌ Search failed: {e}")

    print("=" * 80)
