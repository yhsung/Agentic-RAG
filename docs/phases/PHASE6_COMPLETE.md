# Phase 6: Web Search Fallback - COMPLETED ✅

**Status**: ✅ Complete
**Date**: 2026-01-10
**Commit**: `abd25f4`

## Overview

Phase 6 implements web search fallback capability, enabling the Agentic RAG system to retrieve external information from the internet when local documents are insufficient to answer the user's question. This is the third of four self-correction mechanisms in the system.

## Implementation Summary

### 1. WebSearcher Agent

**File**: [src/agents/web_searcher.py](../../src/agents/web_searcher.py)

A comprehensive web search agent with dual search engine support:

#### Primary Search Engine: Tavily
- LLM-optimized search results specifically designed for RAG applications
- Requires API key (`TAVILY_API_KEY` in `.env`)
- Returns structured, high-quality results with content snippets

#### Fallback Search Engine: DuckDuckGo
- No API key required
- Always available as backup
- Uses standard web search results

#### Key Features:
- **Query Optimization**: Uses LLM to convert natural language questions into effective search queries (3-6 words)
- **Automatic Fallback**: Seamlessly switches from Tavily to DuckDuckGo if primary fails
- **Structured Output**: Returns results as LangChain `Document` objects with rich metadata
- **Error Handling**: Comprehensive error handling with graceful degradation

```python
from src.agents.web_searcher import WebSearcher

searcher = WebSearcher()

# Check availability
if searcher.is_available():
    # Perform search
    documents = searcher.search("What is LangGraph?", max_results=3)

    # Access results
    for doc in documents:
        print(f"Title: {doc.metadata['title']}")
        print(f"Source: {doc.metadata['source']}")
        print(f"Engine: {doc.metadata['search_engine']}")
        print(f"Content: {doc.page_content[:200]}...")
```

### 2. Web Search Node

**File**: [src/graph/nodes.py](../../src/graph/nodes.py#L237)

Updated `web_search` node implementation:

```python
def web_search(state: GraphState) -> dict:
    """Perform web search to find additional information."""
    # Initialize WebSearcher
    searcher = WebSearcher()

    # Check availability
    if not searcher.is_available():
        logger.warning("Web search not available")
        return {"documents": [], "web_search": "No"}

    # Perform search
    documents = searcher.search(
        question=state["question"],
        max_results=settings.WEB_SEARCH_MAX_RESULTS
    )

    return {"documents": documents, "web_search": "Yes"}
```

**Features**:
- Validates search engine availability before attempting search
- Returns empty documents gracefully if search unavailable
- Comprehensive logging of search results for debugging
- Error handling with fallback behavior

### 3. Smart Routing Logic

**File**: [src/graph/routers.py](../../src/graph/routers.py#L101)

Implemented `decide_to_web_search` router function with intelligent decision-making:

```python
def decide_to_web_search(state: GraphState) -> Literal["web_search", "generate"]:
    """Determine whether to perform web search or generate answer."""

    # Count relevant documents
    relevant_count = sum(1 for score in state["relevance_scores"] if score == "yes")
    relevance_ratio = relevant_count / len(state["relevance_scores"])

    # Decision: Web search if < 50% of documents are relevant
    threshold = 0.5
    if relevance_ratio < threshold:
        return "web_search"
    else:
        return "generate"
```

**Routing Logic**:
- **Relevance ≥ 50%**: Generate answer from local documents (high confidence)
- **Relevance < 50%**: Trigger web search for additional information (low confidence)
- **No scores**: Default to web search (safe fallback)

### 4. Configuration Updates

**File**: [requirements.txt](../../requirements.txt)

Added new dependency:
```
langchain-ollama>=0.1.0
```

**File**: [.env](../../.env.example)

New configuration options:
```env
# Web Search Configuration
TAVILY_API_KEY=your_key_here  # Optional: Tavily API key for primary search
WEB_SEARCH_MAX_RESULTS=3      # Number of web search results to retrieve
```

## Workflow Integration

The web search fallback integrates into the RAG workflow as follows:

```
START → retrieve → grade_documents
                        ↓
        ┌───────────────┴───────────────┐
   Relevant docs ≥ 50%        Relevant docs < 50%
        ↓                           ↓
   generate                  web_search → generate
```

**Decision Flow**:
1. **retrieve**: Fetch documents from vector store
2. **grade_documents**: LLM evaluates each document's relevance
3. **decide_to_web_search**: Check if enough relevant docs
   - If relevance < 50%: Search web for additional information
   - If relevance ≥ 50%: Proceed with local docs
4. **generate**: Create answer from available context (local + web)

## Key Technical Details

### Query Optimization Process

The WebSearcher uses the LLM to optimize search queries:

```
User Question: "What are the main benefits of using LangGraph for building agents?"
              ↓
LLM Query Rewriter
              ↓
Search Query: "LangGraph benefits building agents"
```

This improves search relevance by:
- Extracting key terms and concepts
- Removing stop words and filler phrases
- Optimizing for search engine algorithms

### Document Metadata Structure

Web search results include rich metadata:

```python
{
    "page_content": "Snippet of the web page content...",
    "metadata": {
        "source": "https://example.com/article",
        "title": "Article Title",
        "score": 0.95,  # Tavily relevance score (if available)
        "search_engine": "tavily" or "duckduckgo"
    }
}
```

### Graceful Degradation Strategy

The system degrades gracefully when web search fails:

1. **Tavily unavailable**: Automatically use DuckDuckGo
2. **DuckDuckGo unavailable**: Return empty documents
3. **Both unavailable**: Log warning, continue with local docs only
4. **Search errors**: Catch exceptions, log details, return empty docs

This ensures the system always provides some response rather than crashing.

## Testing

### Test Suite

**File**: [scripts/test_web_search.py](../../scripts/test_web_search.py)

Comprehensive test suite covering:
- ✅ DuckDuckGo import and availability
- ✅ Tavily import (with API key validation)
- ✅ WebSearcher initialization
- ✅ Search execution with real queries
- ✅ Error handling and fallback behavior

### Running Tests

```bash
# Activate virtual environment
source venv/bin/activate

# Run web search tests
python scripts/test_web_search.py
```

### Expected Behavior

**Success Case**:
```
✅ DuckDuckGo imported successfully
✅ Tavily imported successfully
⚠️  Tavily API key not set (optional)
✅ WebSearcher initialized successfully
🔍 Searching for: What is LangGraph?
✅ Found 3 results:
   1. LangGraph Tutorial (https://langchain-ai.github.io/langgraph/)
   2. What is LangGraph? (https://example.com)
   3. Building Agents with LangGraph (https://example.com)
```

**Error Handling**:
- DuckDuckGo rate limiting: Handles gracefully with error logging
- Missing API keys: Falls back to DuckDuckGo automatically
- Network errors: Returns empty documents, continues workflow

## Configuration Examples

### Using Tavily (Primary)

```env
# .env file
TAVILY_API_KEY=tvly-your-api-key-here
WEB_SEARCH_MAX_RESULTS=3
```

```bash
# Install Tavily
pip install tavily-python

# Test
python scripts/test_web_search.py
```

### Using DuckDuckGo (Fallback)

```env
# .env file
# No API key needed - DuckDuckGo is free
WEB_SEARCH_MAX_RESULTS=3
```

```bash
# Install DuckDuckGo
pip install duckduckgo-search

# Test
python scripts/test_web_search.py
```

## Performance Characteristics

### Latency

- **Tavily**: ~2-5 seconds per search (optimized for RAG)
- **DuckDuckGo**: ~1-3 seconds per search (standard web search)
- **Query optimization**: +1-2 seconds (LLM processing)

### Rate Limits

- **Tavily**: Depends on API tier (see [Tavily pricing](https://tavily.com/pricing))
- **DuckDuckGo**: No official rate limit, but may throttle aggressive use

### Best Practices

1. **Use Tavily for production**: Better results, designed for RAG
2. **Keep DuckDuckGo as fallback**: Ensures system always works
3. **Limit max results**: 3-5 results is optimal for most queries
4. **Monitor rate limits**: Implement caching if hitting limits frequently

## Dependencies

### Required Packages

```txt
# From requirements.txt
langchain-ollama>=0.1.0     # LLM integration for query optimization
tavily-python==0.5.0         # Tavily API client (optional)
duckduckgo-search==6.3.7     # DuckDuckGo client (fallback)
```

### Optional Setup

```bash
# Pull Ollama model for query optimization
ollama pull qwen3:30b

# Get Tavily API key (optional but recommended)
# Visit: https://tavily.com/home
# Set in .env: TAVILY_API_KEY=your_key_here
```

## Usage Examples

### Example 1: Out-of-Domain Question

```python
# Question about topic not in local documents
question = "What are the latest developments in quantum computing?"

# System behavior:
# 1. Retrieve from vector store → 0/4 relevant docs
# 2. Grade documents → all "no"
# 3. decide_to_web_search → relevance ratio 0% < 50% → trigger web search
# 4. web_search → returns 3 relevant web pages
# 5. generate → creates answer from web search results
```

### Example 2: Partial Relevance

```python
# Question with some relevant local docs
question = "How does LangGraph compare to other workflow tools?"

# System behavior:
# 1. Retrieve from vector store → 4 documents
# 2. Grade documents → 1/4 relevant ("yes", "no", "no", "no")
# 3. decide_to_web_search → relevance ratio 25% < 50% → trigger web search
# 4. web_search → returns 3 comparison articles from web
# 5. generate → creates answer from 1 local doc + 3 web docs
```

### Example 3: Sufficient Local Docs

```python
# Question well-covered by local documents
question = "What is the role of the DocumentGrader agent?"

# System behavior:
# 1. Retrieve from vector store → 4 documents
# 2. Grade documents → 4/4 relevant
# 3. decide_to_web_search → relevance ratio 100% ≥ 50% → skip web search
# 4. generate → creates answer from local docs only (faster)
```

## Troubleshooting

### Common Issues

**Issue**: "Web search not available - no search engines configured"
- **Cause**: Neither Tavily nor DuckDuckGo is installed
- **Fix**: `pip install tavily-python duckduckgo-search`

**Issue**: "DuckDuckGo search failed: Ratelimit"
- **Cause**: DuckDuckGo rate limiting (temporary)
- **Fix**: Wait a few minutes, or use Tavily API instead

**Issue**: "Tavily search failed: Invalid API key"
- **Cause**: Missing or incorrect `TAVILY_API_KEY`
- **Fix**: Set valid API key in `.env` file

**Issue**: "ModuleNotFoundError: No module named 'langchain_ollama'"
- **Cause**: langchain-ollama not installed
- **Fix**: `pip install langchain-ollama>=0.1.0`

### Debug Mode

Enable verbose logging to troubleshoot:

```bash
# Run with debug logging
LOG_LEVEL=DEBUG python cli/main.py query "Your question here"
```

## Integration with Other Phases

### Dependencies
- **Phase 3 (Basic RAG)**: Required - provides generate node
- **Phase 4 (Document Grading)**: Required - provides relevance scores for routing
- **Phase 5 (Query Rewriting)**: Complementary - improves local retrieval before web search

### Enables
- **Phase 7 (Hallucination Check)**: Will verify web-sourced answers
- **Phase 8 (Complete Graph)**: Full agentic workflow integration

## Next Steps

### Phase 7: Hallucination Check (Next)

The final self-correction mechanism will:
1. Verify generated answers are grounded in source documents
2. Check if answers address the user's question
3. Route to regeneration or query transformation if checks fail
4. Use `HallucinationGrader` and `AnswerGrader` agents

### Future Enhancements

Post-MVP improvements to web search:
1. **Result Caching**: Cache web search results to avoid redundant searches
2. **Source Ranking**: Rank web sources by credibility
3. **Deduplication**: Remove duplicate results from multiple searches
4. **Async Search**: Parallel Tavily + DuckDuckGo searches for faster results
5. **Custom Sources**: Add support for Wikipedia, ArXiv, news APIs, etc.

## Success Criteria

✅ **All criteria met**:

1. ✅ WebSearcher agent implemented with Tavily and DuckDuckGo
2. ✅ Query optimization using LLM for better search results
3. ✅ Smart routing: triggers web search when < 50% of docs are relevant
4. ✅ Graceful fallback between search engines
5. ✅ Comprehensive error handling and logging
6. ✅ Integration with existing RAG workflow
7. ✅ Test suite with real search execution
8. ✅ Documentation and usage examples

## Conclusion

Phase 6 successfully implements web search fallback, completing the third of four self-correction mechanisms. The system can now:

1. ✅ Grade document relevance (Phase 4)
2. ✅ Rewrite queries for better retrieval (Phase 5)
3. ✅ **Search web when local docs insufficient** (Phase 6 - NEW)
4. ⏳ Verify answers are grounded and useful (Phase 7 - Next)

This significantly improves the system's ability to answer questions outside its local knowledge base, making it a truly agentic RAG system with external knowledge access.
