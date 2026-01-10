"""
Test script for web search functionality.

This script tests the web searcher with DuckDuckGo (no API key required).
"""

import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_duckduckgo_import():
    """Test DuckDuckGo import."""
    print("=" * 80)
    print("Testing DuckDuckGo Import")
    print("=" * 80)

    try:
        from duckduckgo_search import DDGS
        print("✅ DuckDuckGo imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Failed to import DuckDuckGo: {e}")
        print("To install: pip install duckduckgo-search")
        return False


def test_tavily_import():
    """Test Tavily import."""
    print("\n" + "=" * 80)
    print("Testing Tavily Import")
    print("=" * 80)

    try:
        from tavily import TavilyClient
        print("✅ Tavily imported successfully")

        # Check for API key
        import os
        api_key = os.getenv("TAVILY_API_KEY")
        if api_key:
            print(f"✅ Tavily API key is set")
            return True
        else:
            print("⚠️  Tavily API key not set")
            print("To use Tavily, set TAVILY_API_KEY environment variable")
            return False
    except ImportError as e:
        print(f"❌ Failed to import Tavily: {e}")
        print("To install: pip install tavily-python")
        return False


def test_web_searcher():
    """Test WebSearcher class."""
    print("\n" + "=" * 80)
    print("Testing WebSearcher")
    print("=" * 80)

    try:
        from src.agents.web_searcher import WebSearcher

        # Initialize searcher
        searcher = WebSearcher()

        # Check availability
        if searcher.is_available():
            print("✅ WebSearcher initialized successfully")

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

                return True

            except Exception as e:
                print(f"❌ Search failed: {e}")
                return False

        else:
            print("⚠️  WebSearcher not available - no search engines configured")
            return False

    except Exception as e:
        print(f"❌ Failed to initialize WebSearcher: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("Web Search Test Suite")
    print("=" * 80)

    results = {
        "DuckDuckGo Import": test_duckduckgo_import(),
        "Tavily Import": test_tavily_import(),
        "WebSearcher": test_web_searcher(),
    }

    # Print summary
    print("\n" + "=" * 80)
    print("Test Summary")
    print("=" * 80)

    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")

    # Count results
    passed = sum(1 for v in results.values() if v)
    total = len(results)

    print(f"\nTotal: {passed}/{total} tests passed")

    # Return exit code
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
