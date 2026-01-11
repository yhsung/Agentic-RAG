# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an **Agentic RAG (Retrieval-Augmented Generation)** system built with LangGraph that implements self-correction through four mechanisms:
1. Document relevance grading
2. Web search fallback
3. Hallucination detection
4. Query rewriting

**Key Technologies**: LangGraph (state machine), ChromaDB (vector store), Ollama (local LLMs), LangChain (document processing)

## Development Commands

### Environment Setup
```bash
# Create virtual environment and install dependencies
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env

# Pull required Ollama models
ollama pull qwen3:30b
ollama pull nomic-embed-text

# Verify Ollama is running
curl http://localhost:11434/api/tags
```

### Running the Application
```bash
# Interactive query mode
python cli/main.py query

# Verbose mode (shows node execution)
python cli/main.py query --verbose

# Load documents into vectorstore
python cli/main.py load path/to/documents

# System health check
python cli/main.py status

# View current configuration
python config/settings.py
```

### Testing
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_graders.py

# Run with coverage
pytest --cov=src tests/

# Verbose test output
pytest -v

# Test individual components
python scripts/test_components.py --component grader
```

### Configuration Debugging
```bash
# Display current settings
python config/settings.py

# List all prompt templates
python config/prompts.py
```

## Architecture

### LangGraph State Machine Flow

The system uses a **directed graph with 7 nodes** and conditional routing:

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

**State Definition** (`src/graph/state.py`):
```python
class GraphState(TypedDict):
    question: str              # User's question
    generation: str            # LLM response
    web_search: str           # "Yes"/"No" flag
    documents: List[Document]  # Retrieved docs
    retry_count: int          # Query rewrite attempts (max 3)
    relevance_scores: List[str] # Document grades
```

### Critical File Responsibilities

**Core Orchestration**:
- `src/graph/workflow.py` - Builds the LangGraph StateGraph, compiles it, and exposes `run()` and `stream()` methods
- `src/graph/nodes.py` - Implements all 7 node functions (each takes GraphState, returns updated GraphState)
- `src/graph/routers.py` - Conditional edge functions that decide routing based on state

**Agentic Components**:
- `src/agents/graders.py` - DocumentGrader, HallucinationGrader, AnswerGrader (all use LLM with JSON output)
- `src/agents/generator.py` - AnswerGenerator (RAG-based response generation)
- `src/agents/rewriter.py` - QueryRewriter (semantic query improvement)
- `src/agents/web_searcher.py` - WebSearcher (Tavily/DuckDuckGo integration)

**Data Layer**:
- `src/vectorstore/chroma_store.py` - ChromaDB integration with Ollama embeddings (`nomic-embed-text`)
- `src/loaders/document_loader.py` - Document loading and chunking (RecursiveCharacterTextSplitter: 1000 chars, 200 overlap)

**Configuration**:
- `config/settings.py` - Pydantic-based settings (models, paths, retrieval params). Import as `from config.settings import settings`
- `config/prompts.py` - All 6 prompt templates (relevance, hallucination, answer, query rewrite, RAG, web search)

### Node Execution Order

1. **retrieve**: Query ChromaDB, return top-k documents
2. **grade_documents**: LLM evaluates each doc (binary yes/no)
3. **Routing**: Based on grades:
   - All relevant → generate
   - Some relevant → web_search then generate
   - None relevant → transform_query (loop back to retrieve)
4. **generate**: Create answer from relevant docs
5. **check_hallucination**: Verify answer is grounded
6. **check_usefulness**: Verify answer addresses question
7. **Final routing**:
   - Hallucinated → regenerate
   - Not useful → transform_query (retry with better query)
   - Good → END

### Configuration System

All configuration is managed through Pydantic Settings (`config/settings.py`):
- Environment variables override defaults
- Load from `.env` file
- Access via `from config.settings import settings`

**Auto-Detection Feature**:
The system automatically detects containerized environments using environment variables:
- **DevContainer**: Uses `http://host.docker.internal:11434` when `DEVCONTAINER=true` or `CODESPACES=true`
- **Local Development**: Uses `http://localhost:11434` by default
- **Override**: Set `OLLAMA_BASE_URL` environment variable to force a specific URL

To enable DevContainer mode, set the environment variable:
```bash
# In your DevContainer configuration or docker-compose.yml
environment:
  - DEVCONTAINER=true
```

This auto-detection eliminates manual configuration when switching between local and containerized development.

**Key Settings**:
- `GENERATION_MODEL`, `EMBEDDING_MODEL`, `GRADING_MODEL` - Ollama model names (swappable)
- `RETRIEVAL_K` - Number of docs to retrieve (default: 4)
- `CHUNK_SIZE` / `CHUNK_OVERLAP` - Document chunking params (1000/200 chars)
- `MAX_RETRIES` - Query rewrite limit (default: 3)
- `TAVILY_API_KEY` - Optional web search API key

### Prompt Engineering

All prompts are in `config/prompts.py`. Each prompt:
- Returns JSON with `{"score": "yes"}` or `{"score": "no"}` for graders
- Returns plain text for generator and rewriter
- Is optimized for binary classification or specific transformation tasks

**Critical Prompts**:
- `RELEVANCE_GRADER_PROMPT` - Document relevance (keyword + semantic)
- `HALLUCINATION_GRADER_PROMPT` - Answer grounding check
- `ANSWER_GRADER_PROMPT` - Question addressing check
- `QUERY_REWRITER_PROMPT` - Query optimization for retrieval
- `RAG_PROMPT` - Concise answer generation (3 sentences max)

### Model Selection Strategy

The system uses **three types of models**:
1. **Embedding**: `nomic-embed-text` (1024 dims, optimized for retrieval)
2. **Generation**: `qwen3:30b` (3B, fast and capable)
3. **Grading**: `qwen3:30b` (same model, but could use smaller for efficiency)

Models are easily swappable via `.env`:
```env
GENERATION_MODEL=qwen3:30b   # Fast (recommended)
GENERATION_MODEL=mistral    # Better reasoning
GENERATION_MODEL=llama3.1   # Most capable (slower, more RAM)
```

### Data Flow

1. **Document Ingestion**: Raw docs → RecursiveCharacterTextSplitter → ChromaDB with Ollama embeddings
2. **Query Processing**: User question → Embedding → Similarity search → Retrieved docs
3. **Agentic Loop**: Grade → Decide (generate/search/rewrite) → Generate → Verify → Return or retry
4. **Max 3 retries** to prevent infinite loops

### ChromaDB Integration

- **Persistence**: `./data/chroma_db/` (configurable)
- **Collection**: `agentic_rag` (configurable)
- **Embeddings**: Ollama `nomic-embed-text` via LangChain integration
- **Retrieval**: Similarity search with configurable k

### Testing Strategy

**Unit Tests**:
- `tests/test_graders.py` - Test graders with known relevant/irrelevant docs
- `tests/test_nodes.py` - Test each node function in isolation

**Integration Tests**:
- `tests/test_workflow.py` - End-to-end scenarios:
  - Happy path: relevant docs → good answer
  - Query rewrite path: vague question → rewrite → better retrieval
  - Web search path: out-of-domain → web search → answer
  - Hallucination correction: bad answer → detection → regeneration

## Implementation Guidelines

### Adding New Nodes

1. Define node function in `src/graph/nodes.py`:
   ```python
   def my_node(state: GraphState) -> GraphState:
       # Process state
       return {"key": "updated_value", ...}
   ```

2. Add routing logic in `src/graph/routers.py` (if needed):
   ```python
   def my_router(state: GraphState) -> str:
       # Return next node name based on state
       return "next_node_name"
   ```

3. Wire into workflow in `src/graph/workflow.py`:
   ```python
   workflow.add_node("my_node", my_node)
   workflow.add_edge("previous_node", "my_node")
   # or add_conditional_edges with router
   ```

### Modifying Prompts

Edit `config/prompts.py` directly. All prompts use string formatting with named variables:
```python
PROMPT = """Your prompt with {variable_name}"""
```

Test prompts by running:
```bash
python config/prompts.py  # Displays all prompts
```

### Changing Models

1. Pull new model: `ollama pull <model_name>`
2. Update `.env`: `GENERATION_MODEL=<model_name>`
3. Restart application

No code changes needed - models are loaded dynamically from settings.

### Working with ChromaDB

The vectorstore is initialized lazily. To force reinitialization:
```bash
rm -rf data/chroma_db/
python scripts/setup_vectorstore.py
```

### Document Processing

Supported formats: PDF, Markdown, Plain Text

Chunking strategy (in `src/loaders/document_loader.py`):
- RecursiveCharacterTextSplitter
- 1000 character chunks with 200 character overlap
- Separators: `\n\n`, `\n`, `.`, `!`, `?`, `,`, ` ` (in order)

## Troubleshooting

### Ollama Connection Issues
```bash
# Verify Ollama is running if environment is in container
curl http://host.docker.internal:11434/api/tags

# Verify Ollama is running if is in host environment
curl http://localhost:11434/api/tags

# If not running, start it
ollama serve
```

### Missing Models
```bash
# Pull required models
ollama pull qwen3:30b
ollama pull nomic-embed-text
```

### ChromaDB Errors
```bash
# Recreate database
rm -rf data/chroma_db/
python scripts/setup_vectorstore.py
```

### Import Errors
Ensure virtual environment is activated and dependencies are installed:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

## Development Workflow

**Current Status**: Phase 1 (Foundation) complete. Phases 2-10 outlined in `docs/plans/DEVELOPMENT_PLAN.md`

**Next Steps**:
1. Implement document processing (`src/loaders/`, `src/vectorstore/`)
2. Build basic RAG (`src/agents/generator.py`, basic nodes)
3. Add agentic features (graders, rewriter, web search)
4. Complete graph integration
5. Build CLI interface
6. Add comprehensive tests

Refer to `docs/plans/DEVELOPMENT_PLAN.md` for detailed implementation phases.

## Key Design Decisions

- **Max 3 retries**: Prevents infinite query rewrite loops
- **Binary grading**: LLM returns JSON `{"score": "yes/no"}` for all grading tasks
- **Temperature 0**: Deterministic outputs for grading and generation
- **Graceful degradation**: Retrieval fails → web search → "I don't know"
- **Centralized prompts**: All in `config/prompts.py` for easy experimentation
- **Model flexibility**: Swap models via config without code changes
