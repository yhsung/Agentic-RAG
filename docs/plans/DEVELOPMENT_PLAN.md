# Agentic RAG with LangGraph Implementation Plan

## Project Overview

Build an agentic RAG (Retrieval-Augmented Generation) system using LangGraph, ChromaDB, and Ollama that implements 4 key agentic features:
1. **Document relevance grading** - Evaluate if retrieved docs are relevant
2. **Web search fallback** - Search web if local docs insufficient
3. **Answer hallucination check** - Verify answers are grounded in sources
4. **Query rewriting** - Rephrase queries to improve retrieval

**Tech Stack**: LangGraph, ChromaDB, Ollama (local LLMs), Tavily/DuckDuckGo (web search)
**Interface**: CLI first, Streamlit UI as future enhancement

## Architecture

### LangGraph State Machine

The system uses a directed graph with 7 nodes and conditional routing:

```
START → retrieve → grade_documents
                        ↓ (conditional routing)
        ┌───────────────┼───────────────┐
        │               │               │
   transform_query  web_search      generate
        │               │               │
        └───────────────┴───────────────┘
                        ↓
            check_hallucination & usefulness
                        ↓ (conditional routing)
        ┌───────────────┼───────────────┐
   regenerate      transform_query      END
```

**State Definition**:
```python
class GraphState(TypedDict):
    question: str              # User's question
    generation: str            # LLM response
    web_search: str           # "Yes"/"No" flag
    documents: List[Document]  # Retrieved docs
    retry_count: int          # Query rewrite attempts
    relevance_scores: List[str] # Document grades
```

**Routing Logic**:
- After `grade_documents`: Route to `generate` if docs relevant, `web_search` if not enough relevant docs, `transform_query` if no relevant docs
- After `generate`: Route to END if answer is grounded & useful, `generate` if hallucinated, `transform_query` if not useful
- Max 3 retry attempts to prevent infinite loops

### Node Functions

1. **retrieve** - Query ChromaDB vector store, return top-k similar documents
2. **grade_documents** - LLM evaluates each doc's relevance (binary yes/no)
3. **generate** - LLM generates answer from relevant documents using RAG prompt
4. **transform_query** - LLM rewrites query for better retrieval
5. **web_search_node** - Fetch results from Tavily/DuckDuckGo, convert to documents
6. (Built into generate node) **check_hallucination** - Verify answer is grounded in docs
7. (Built into generate node) **check_answer_usefulness** - Verify answer addresses question

## Project Structure

```
/Volumes/Samsung970EVOPlus/Agentic-RAG/
├── requirements.txt           # Dependencies
├── .env.example              # Configuration template
├── README.md                 # Documentation
│
├── config/
│   ├── settings.py           # Pydantic settings (models, paths, params)
│   └── prompts.py            # All prompt templates
│
├── data/
│   ├── raw/                  # Original documents
│   ├── processed/            # Chunked documents
│   └── chroma_db/           # ChromaDB persistence
│
├── src/
│   ├── embeddings/
│   │   └── ollama_embeddings.py    # Ollama embedding wrapper
│   │
│   ├── vectorstore/
│   │   └── chroma_store.py         # ChromaDB operations
│   │
│   ├── loaders/
│   │   └── document_loader.py      # Document loading & chunking
│   │
│   ├── graph/
│   │   ├── state.py                # GraphState definition
│   │   ├── nodes.py                # All 7 node implementations
│   │   ├── routers.py              # Conditional edge functions
│   │   └── workflow.py             # StateGraph construction
│   │
│   ├── agents/
│   │   ├── graders.py              # Document & hallucination graders
│   │   ├── generator.py            # Answer generation
│   │   ├── rewriter.py             # Query rewriting
│   │   └── web_searcher.py         # Web search integration
│   │
│   └── utils/
│       └── logger.py               # Logging configuration
│
├── cli/
│   └── main.py                     # CLI interface (Click + Rich)
│
├── scripts/
│   ├── setup_vectorstore.py        # Initialize ChromaDB
│   ├── load_documents.py           # Load sample data
│   └── test_components.py          # Component validation
│
└── tests/
    ├── test_nodes.py               # Unit tests for nodes
    ├── test_graders.py             # Unit tests for graders
    └── test_workflow.py            # Integration tests
```

## Critical Files & Responsibilities

### 1. `/src/graph/workflow.py` - Core Orchestration
**Purpose**: Constructs the LangGraph StateGraph with all nodes and edges

Key components:
- Initialize all node functions
- Define conditional edge logic
- Compile graph
- Expose `run()` and `stream()` methods for CLI/UI

### 2. `/src/graph/nodes.py` - Node Implementations
**Purpose**: Implements all 7 node functions

Each node:
- Takes `GraphState` as input
- Performs its specific operation
- Returns updated `GraphState`
- Includes error handling and logging

### 3. `/config/prompts.py` - Prompt Templates
**Purpose**: Centralized prompt engineering

5 key prompts:
- `RELEVANCE_GRADER_PROMPT` - Binary yes/no document relevance
- `HALLUCINATION_GRADER_PROMPT` - Check if answer is grounded
- `ANSWER_GRADER_PROMPT` - Check if answer addresses question
- `QUERY_REWRITER_PROMPT` - Improve query for retrieval
- `RAG_PROMPT` - Generate concise answer from context

### 4. `/src/vectorstore/chroma_store.py` - Vector Store
**Purpose**: ChromaDB integration with Ollama embeddings

Key features:
- Initialize persistent ChromaDB client
- Create/update collections
- Return retriever for similarity search
- Handle embeddings with `nomic-embed-text` model

### 5. `/config/settings.py` - Configuration Management
**Purpose**: Centralized configuration using Pydantic

Key settings:
- Model names (generation, embedding, grading)
- ChromaDB paths and collection names
- Retrieval parameters (k, chunk_size, overlap)
- Web search API keys
- Logging levels

## Implementation Phases

### Phase 1: Foundation Setup (Days 1-2)
**Goal**: Project structure and basic infrastructure

Tasks:
1. Create directory structure
2. Install Ollama and pull models:
   ```bash
   ollama pull llama3.2
   ollama pull nomic-embed-text
   ```
3. Create `requirements.txt` with core dependencies
4. Set up `config/settings.py` with Pydantic
5. Create `.env.example` template

**Validation**: Can import all packages, Ollama responds to API calls

### Phase 2: Document Processing (Days 3-4)
**Goal**: Load, chunk, and store documents in ChromaDB

Tasks:
1. Implement `src/loaders/document_loader.py`:
   - `RecursiveCharacterTextSplitter` (chunk_size=1000, overlap=200)
   - Support for text, PDF, markdown
2. Implement `src/vectorstore/chroma_store.py`:
   - Initialize ChromaDB with Ollama embeddings
   - Create persistent collection
   - Return retriever
3. Create `scripts/load_documents.py`:
   - Load sample dataset (LangChain docs or similar)
   - Chunk documents
   - Store in ChromaDB
4. Test retrieval with sample queries

**Validation**: Can load docs, embed, store, and retrieve similar chunks

### Phase 3: Basic RAG (Days 5-6)
**Goal**: Non-agentic baseline RAG system

Tasks:
1. Implement `src/agents/generator.py`:
   - Ollama LLM initialization
   - RAG prompt template
   - Simple retrieval → generation chain
2. Create basic `retrieve` and `generate` nodes
3. Test with sample questions
4. Measure baseline quality

**Validation**: Can answer questions using retrieved context

### Phase 4: Document Grading (Days 7-8)
**Goal**: Add document relevance evaluation

Tasks:
1. Implement `src/agents/graders.py`:
   - `DocumentGrader` class with relevance prompt
   - JSON output parsing (binary yes/no)
2. Create `grade_documents` node
3. Implement `decide_to_generate` router function
4. Add conditional routing in graph
5. Test grading accuracy with known relevant/irrelevant docs

**Validation**: System correctly identifies relevant vs irrelevant documents

### Phase 5: Query Rewriting (Days 9-10)
**Goal**: Add query transformation for better retrieval

Tasks:
1. Implement `src/agents/rewriter.py`:
   - Query rewriting prompt
   - Semantic improvement logic
2. Create `transform_query` node
3. Add retry counter to state
4. Implement loop: transform_query → retrieve → grade_documents
5. Test with vague/unclear queries

**Validation**: Vague queries get rewritten and retrieval improves

### Phase 6: Web Search Fallback (Days 11-12)
**Goal**: Add external knowledge via web search

Tasks:
1. Implement `src/agents/web_searcher.py`:
   - Tavily API integration (or DuckDuckGo fallback)
   - Convert results to Document format
2. Create `web_search_node`
3. Update router to trigger web search when no relevant docs
4. Test with queries outside knowledge base

**Validation**: System falls back to web search when local docs insufficient

### Phase 7: Hallucination Check (Days 13-14)
**Goal**: Verify generated answers are grounded

Tasks:
1. Add `HallucinationGrader` to `src/agents/graders.py`:
   - Compare answer to source documents
   - Binary grounded/not grounded
2. Add `AnswerGrader` for usefulness check
3. Implement `check_hallucination_and_answer` router
4. Add conditional routing after generation
5. Test with intentionally misleading prompts

**Validation**: System catches and corrects hallucinated answers

### Phase 8: Complete Graph Integration (Days 15-16)
**Goal**: Wire all nodes into complete StateGraph

Tasks:
1. Define complete `GraphState` in `src/graph/state.py`
2. Wire all nodes in `src/graph/workflow.py`:
   - All 7 nodes
   - All conditional edges
   - Router functions
3. Test end-to-end flow with diverse queries
4. Add comprehensive logging

**Validation**: Full agentic flow works from question to verified answer

### Phase 9: CLI Interface (Days 17-18)
**Goal**: User-friendly command-line interface

Tasks:
1. Implement `cli/main.py` using Click + Rich:
   - `query` command - Interactive Q&A
   - `load` command - Add documents to vectorstore
   - `status` command - System health check
2. Add verbose mode to show node execution
3. Format output with Rich (panels, markdown, syntax highlighting)
4. Add query history

**Validation**: Can use system through clean CLI

### Phase 10: Testing & Documentation (Days 19-20)
**Goal**: Comprehensive testing and docs

Tasks:
1. Write unit tests:
   - `tests/test_graders.py` - All grading functions
   - `tests/test_nodes.py` - Each node in isolation
2. Write integration tests:
   - `tests/test_workflow.py` - End-to-end scenarios
3. Create validation test sets for each agentic feature
4. Write comprehensive README.md:
   - Architecture diagram
   - Setup instructions
   - Usage examples
   - Configuration guide
5. Document prompt templates and their rationale

**Validation**: All tests pass, documentation complete

## Key Technical Decisions

### Model Selection
- **Generation**: `llama3.2` (3B) - Fast, good quality for most queries
- **Grading**: `llama3.2` (3B) - Sufficient for binary classification
- **Embeddings**: `nomic-embed-text` - Best for general text retrieval
- **Rationale**: Balance speed, quality, and local resource usage

### Chunking Strategy
- **Size**: 1000 characters - Balance context vs precision
- **Overlap**: 200 characters - Prevent context loss at boundaries
- **Method**: `RecursiveCharacterTextSplitter` - Preserves semantic structure

### Web Search
- **Primary**: Tavily API - LLM-optimized results, free tier available
- **Fallback**: DuckDuckGo - No API key required
- **Rationale**: Tavily provides better results for RAG, DuckDuckGo for testing

### Error Handling
- **Max retries**: 3 query rewrites - Prevent infinite loops
- **Graceful degradation**: If retrieval fails, try web search; if that fails, return "I don't know"
- **Logging**: Comprehensive DEBUG logs for troubleshooting

### Sample Dataset
- **Recommendation**: LangChain documentation (~100-200 docs)
- **Rationale**: Relevant to tech stack, well-structured, manageable size, good for testing
- **Alternative**: ArXiv papers, Wikipedia articles, or custom docs

## Dependencies

Core dependencies (see `requirements.txt` for versions):

```
# Framework
langgraph==0.2.45
langchain==0.3.9
langchain-core==0.3.21
langchain-community==0.3.8

# LLM & Embeddings
ollama==0.4.5

# Vector Store
chromadb==0.5.23

# Document Processing
pypdf==5.1.0
unstructured==0.16.9

# Web Search
tavily-python==0.5.0
duckduckgo-search==7.0.3

# CLI
click==8.1.8
rich==13.9.4

# Configuration
pydantic==2.10.4
pydantic-settings==2.7.0
python-dotenv==1.0.1

# Testing
pytest==8.3.4
pytest-asyncio==0.25.2

# Future: streamlit (for UI phase)
```

## Configuration Example

**`.env` file**:
```env
# Ollama
OLLAMA_BASE_URL=http://localhost:11434
EMBEDDING_MODEL=nomic-embed-text
GENERATION_MODEL=llama3.2
GRADING_MODEL=llama3.2

# ChromaDB
CHROMA_PERSIST_DIR=./data/chroma_db
CHROMA_COLLECTION=agentic_rag

# Retrieval
RETRIEVAL_K=4
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
MAX_RETRIES=3

# Web Search
TAVILY_API_KEY=your_key_here

# Logging
LOG_LEVEL=INFO
```

## Testing Strategy

### Component Tests
- **Graders**: Test with known relevant/irrelevant docs, grounded/hallucinated answers
- **Query Rewriter**: Verify improved specificity
- **Web Search**: Confirm API integration and Document conversion
- **Retriever**: Check similarity search returns relevant chunks

### Integration Tests
- **Happy path**: Question → relevant docs → good answer
- **Query rewrite path**: Vague question → rewrite → better retrieval
- **Web search path**: Out-of-domain question → web search → answer
- **Hallucination correction**: Bad answer → detection → regeneration

### Validation Metrics
- Retrieval accuracy: % relevant docs in top-k
- Grading accuracy: Correct yes/no classifications
- Hallucination detection rate: % hallucinations caught
- End-to-end latency: Time per query
- Token usage: Cost per query

## Future Enhancements (Post-MVP)

These are noted as TODOs but not in initial scope:

1. **Streamlit UI** - Visual interface with:
   - Real-time node execution visualization
   - Source document display
   - Query history and analytics
   - Graph visualization with LangGraph Studio

2. **Advanced Features**:
   - Multi-modal support (images, tables in PDFs)
   - Streaming responses (real-time generation)
   - Session memory (conversation context)
   - Custom data sources (APIs, databases)
   - Fine-tuned Ollama models for domain

3. **Production Readiness**:
   - Docker containerization
   - API endpoints (FastAPI)
   - Caching layer (Redis)
   - Evaluation framework (automated benchmarks)
   - Monitoring and observability

## Reference Sources

Implementation based on:
- [LangGraph Agentic RAG Tutorial](https://docs.langchain.com/oss/python/langgraph/agentic-rag)
- [Kaggle: LangGraph Agentic RAG with Chroma](https://www.kaggle.com/code/ksmooi/langgraph-agentic-rag-with-chroma)
- [Building Agentic RAG Systems Guide](https://www.analyticsvidhya.com/blog/2024/07/building-agentic-rag-systems-with-langgraph/)
- [Ollama Embeddings with ChromaDB](https://cookbook.chromadb.dev/integrations/ollama/embeddings/)

---

## Implementation Notes

**Development approach**: Build incrementally, test each component before integrating. Each phase should have clear validation criteria. Use verbose logging during development to understand agent decision-making.

**Extensibility**: The `AgenticRAGWorkflow` class encapsulates the graph, making it easy to use from CLI, Streamlit, or API. All configuration is centralized in `config/settings.py` for easy model swapping and parameter tuning.

**Model flexibility**: The system is designed to work with any Ollama model. Can easily swap `llama3.2` for `mistral`, `phi3`, or other models by changing configuration.
