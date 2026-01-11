# Agentic RAG with LangGraph

An intelligent Retrieval-Augmented Generation (RAG) system with self-correction capabilities, built using LangGraph, ChromaDB, and Ollama.

## Features

This agentic RAG system implements four key self-correction mechanisms:

1. **Document Relevance Grading** - Automatically evaluates if retrieved documents are relevant to the query
2. **Web Search Fallback** - Searches the web when local documents are insufficient
3. **Hallucination Detection** - Verifies that generated answers are grounded in source documents
4. **Query Rewriting** - Automatically rephrases unclear queries to improve retrieval

## Architecture

The system uses a LangGraph state machine with conditional routing:

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

## Tech Stack

- **LangGraph**: Orchestrates the agentic workflow with conditional routing
- **ChromaDB**: Vector database for document storage and retrieval
- **Ollama**: Local LLMs for generation, grading, and embeddings
- **LangChain**: Document processing and chain abstractions
- **Tavily/DuckDuckGo**: Web search integration

## Prerequisites

- Python 3.10 or higher
- [Ollama](https://ollama.ai/) installed and running
- 8GB+ RAM recommended

## Installation

### 1. Clone the repository

```bash
git clone <repository-url>
cd Agentic-RAG
```

### 2. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Install and configure Ollama

Install Ollama from [ollama.ai](https://ollama.ai/), then pull the required models:

```bash
# Pull the generation model (30B parameters, recommended)
ollama pull qwen3:30b

# Pull the embedding model (1024 dimensions)
ollama pull nomic-embed-text
```

Verify Ollama is running:
```bash
# For local development
curl http://localhost:11434/api/tags

# For DevContainer/Codespaces (auto-detected)
curl http://host.docker.internal:11434/api/tags
```

### 5. Configure environment

Copy the example environment file and configure:

```bash
cp .env.example .env
```

Edit `.env` to set your preferences:
```env
# Ollama Configuration (auto-detects DevContainer/Codespaces)
OLLAMA_BASE_URL=http://localhost:11434  # Auto-switches to host.docker.internal in containers
GENERATION_MODEL=qwen3:30b
GRADING_MODEL=qwen3:30b
EMBEDDING_MODEL=nomic-embed-text

# Web Search (Optional - DuckDuckGo works without key)
TAVILY_API_KEY=your_key_here  # Get free key at tavily.com (1000 requests/month)

# Retrieval Settings
RETRIEVAL_K=4
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
MAX_RETRIES=3
```

## Quick Start

### 1. Load Documents

Add your documents to the vector store (supports both files and directories):

```bash
# Load a single file
python cli/main.py load document.pdf

# Load all documents from a directory
python cli/main.py load path/to/documents/

# With custom chunking
python cli/main.py load docs/ --chunk-size 1500 --chunk-overlap 300
```

Supported formats:
- PDF (`.pdf`)
- Markdown (`.md`, `.markdown`)
- Plain text (`.txt`)

### 2. Check System Status

Verify all components are working:

```bash
python cli/main.py status
```

This displays:
- ✅ Ollama connection and models
- ✅ ChromaDB initialization status
- ✅ Vector store document count
- ✅ Self-correction mechanisms status (including web search)
- ✅ Workflow graph structure (7 nodes, 11 edges)

### 3. Run the CLI

Start the interactive query interface:

```bash
python cli/main.py query
```

### 4. Ask Questions (Interactive Mode)

```bash
Question: What is LangGraph?

Answer: LangGraph is a framework for building stateful,
multi-actor applications with LLMs. It extends LangChain's
capabilities by adding cyclic computational graphs and state
management.

Metadata:
  Documents Retrieved: 4
  Relevant Documents: 4/4
  Query Retries: 0
  Web Search Used: No
  Hallucination Check: grounded
  Usefulness Check: useful

Sources:
  1. docs/langgraph-intro.md
  2. docs/langgraph-concepts.md
```

### 5. Single Question Mode

```bash
python cli/main.py query "What is Agentic RAG?"
```

### 6. Verbose Mode

See detailed workflow execution:

```bash
python cli/main.py query --verbose

Question: How does document grading work?

[Shows each node execution with metadata]
>>> retrieve
  Retrieved: 4 docs

>>> grade_documents
  Relevant: 3/4 docs

>>> generate
  Generated answer

>>> check_hallucination
  ✓ Answer is grounded

>>> check_usefulness
  ✓ Answer addresses question
```

### 7. Stream Mode

Real-time visualization:

```bash
python cli/main.py query --stream
```

Example usage:
```bash
Question: What is LangGraph?

Answer: LangGraph is a framework for building stateful,
multi-actor applications with LLMs. It extends LangChain's
capabilities by adding cyclic computational graphs and state
management.

Sources:
  1. docs/langgraph-intro.md
  2. docs/langgraph-concepts.md
```

### 3. Enable Verbose Mode

See the agentic workflow in action:

```bash
python cli/main.py query --verbose
```

This shows each node execution:
```
>>> retrieve
  Retrieved: 4 docs

>>> grade_documents
  Relevant: 3/4 docs

>>> generate
  Generated answer

>>> check_hallucination
  ✓ Answer is grounded

>>> check_usefulness
  ✓ Answer addresses question
```

## Project Structure

```
Agentic-RAG/
├── config/
│   ├── settings.py      # Pydantic configuration
│   └── prompts.py       # All prompt templates
├── src/
│   ├── graph/
│   │   ├── state.py     # Graph state definition
│   │   ├── nodes.py     # Node implementations
│   │   ├── routers.py   # Conditional routing logic
│   │   └── workflow.py  # LangGraph workflow
│   ├── agents/
│   │   ├── graders.py   # Document & hallucination graders
│   │   ├── generator.py # Answer generation
│   │   ├── rewriter.py  # Query rewriting
│   │   └── web_searcher.py # Web search
│   ├── vectorstore/
│   │   └── chroma_store.py # ChromaDB operations
│   ├── loaders/
│   │   └── document_loader.py # Document processing
│   └── utils/
│       └── logger.py    # Logging configuration
├── cli/
│   └── main.py          # CLI interface
├── scripts/
│   ├── load_documents.py # Document loading script
│   ├── setup_vectorstore.py # ChromaDB initialization
│   └── test_components.py # Component testing
├── tests/
│   ├── test_nodes.py    # Unit tests
│   ├── test_graders.py  # Grading tests
│   └── test_workflow.py # Integration tests
└── data/
    ├── raw/             # Original documents
    ├── processed/       # Chunked documents
    └── chroma_db/      # Vector database
```

## Configuration

### Model Selection

You can swap models by editing `.env`:

```env
# Recommended: Qwen 30B (excellent quality, fast on modern hardware)
GENERATION_MODEL=qwen3:30b

# Lightweight: Llama 3.2 (3B, faster but less capable)
GENERATION_MODEL=llama3.2

# Alternative: Mistral (7B, good balance)
GENERATION_MODEL=mistral

# High-end: Llama 3.1 (70B, best quality, requires 64GB+ RAM)
GENERATION_MODEL=llama3.1:70b
```

### Retrieval Parameters

Adjust retrieval behavior:

```env
RETRIEVAL_K=4            # Number of docs to retrieve
CHUNK_SIZE=1000         # Characters per chunk
CHUNK_OVERLAP=200       # Overlap between chunks
MAX_RETRIES=3           # Max query rewrite attempts
```

### Web Search

The system includes **intelligent web search fallback** that automatically triggers when local documents don't contain relevant information.

**Two search engines supported:**

1. **Tavily API** (Primary - Recommended)
   - Get a free API key from [Tavily](https://tavily.com/) (1,000 requests/month free)
   - Add to `.env`:
     ```env
     TAVILY_API_KEY=your_key_here
     ```
   - Higher quality results, optimized for AI applications

2. **DuckDuckGo** (Fallback)
   - No API key required
   - Works out of the box
   - Automatically used if Tavily is unavailable

**How it works:**
- System retrieves documents from local vector store
- Grades document relevance
- If < 50% documents are relevant → triggers web search
- Web results are added to context for generation

## CLI Commands

### Query Mode (Interactive)

```bash
python cli/main.py query [OPTIONS] [QUESTION]

Options:
  --verbose, -v  Show detailed execution flow with node-by-node progress
  --stream, -s   Stream execution in real-time
  QUESTION       Optional: Ask a single question and exit

Examples:
  python cli/main.py query                           # Interactive mode
  python cli/main.py query --verbose                 # Interactive with details
  python cli/main.py query "What is LangGraph?"      # Single question
  python cli/main.py query --verbose "How does RAG work?"  # Single with details
```

### Load Documents

```bash
python cli/main.py load PATH [OPTIONS]

Options:
  --chunk-size INTEGER     Character size for chunks (default: 1000)
  --chunk-overlap INTEGER  Character overlap between chunks (default: 200)

Examples:
  python cli/main.py load docs/                      # Load directory
  python cli/main.py load research_paper.pdf         # Load single file
  python cli/main.py load docs/ --chunk-size 1500    # Custom chunking
```

### System Status

```bash
python cli/main.py status

Shows:
  ✅ Ollama connection and base URL (auto-detects DevContainer)
  ✅ ChromaDB initialization and path
  ✅ Generation, Embedding, and Grading models
  ✅ Retrieval parameters (k, chunk size, max retries)
  ✅ Self-correction mechanisms status:
     - Document Relevance Grading
     - Query Rewriting
     - Hallucination Detection
     - Answer Usefulness Check
     - Web Search Fallback (dynamically checked)
  ✅ Workflow graph structure (7 nodes, 11 edges)
```

### A/B Testing (Prompt Variants)

Test different prompt strategies to optimize answer quality:

```bash
# Run A/B test with a specific prompt variant
python cli/main.py ab-test run baseline
python cli/main.py ab-test run detailed
python cli/main.py ab-test run bullets
python cli/main.py ab-test run reasoning

# Compare results across variants
python cli/main.py ab-test compare

# View detailed statistics
python cli/main.py ab-test stats
```

Available prompt variants:
- **baseline**: Concise, direct answers (3 sentences max)
- **detailed**: Comprehensive explanations with context
- **bullets**: Structured bullet-point format
- **reasoning**: Step-by-step reasoning before answer

## Testing

Run the test suite:

```bash
# All tests
pytest

# Specific test file
pytest tests/test_graders.py

# With coverage
pytest --cov=src tests/

# Verbose output
pytest -v
```

## How It Works

### 1. Retrieval

User queries are embedded and used to search ChromaDB for similar document chunks.

### 2. Relevance Grading

An LLM evaluates each retrieved document:
- **Relevant**: Keep for generation
- **Not relevant**: Trigger query rewrite or web search

### 3. Generation

Relevant documents are used as context to generate a concise answer.

### 4. Hallucination Check

The system verifies the answer is grounded in source documents:
- **Grounded**: Proceed to usefulness check
- **Hallucinated**: Regenerate without hallucinations

### 5. Usefulness Check

Verifies the answer addresses the question:
- **Useful**: Return to user
- **Not useful**: Rewrite query and retry

## Troubleshooting

### Ollama Connection Error

```
Error: Failed to connect to Ollama
```

**Solution**: Ensure Ollama is running:
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama (if needed)
ollama serve
```

### Model Not Found

```
Error: Model 'llama3.2' not found
```

**Solution**: Pull the model:
```bash
ollama pull llama3.2
```

### ChromaDB Permission Error

```
Error: Permission denied: './data/chroma_db'
```

**Solution**: Create the directory with correct permissions:
```bash
mkdir -p data/chroma_db
chmod 755 data/chroma_db
```

### Slow Generation

If generation is slow, consider:
1. Using a smaller model: `llama3.2` (3B) instead of `qwen3:30b` (30B)
2. Reducing `RETRIEVAL_K` to retrieve fewer documents
3. Ensuring Ollama has sufficient RAM allocated (recommended: 16GB+ for qwen3:30b)
4. Disabling web search if not needed by not setting `TAVILY_API_KEY`

### Deprecation Warnings

If you see warnings about `langchain_community.embeddings` or `langchain_community.vectorstores`:

```bash
# Update to latest packages
pip install -U langchain-chroma langchain-ollama
```

The system now uses:
- `langchain_ollama.OllamaEmbeddings` (instead of langchain_community)
- `langchain_chroma.Chroma` (instead of langchain_community)

## Development

### Adding New Prompts

Edit `config/prompts.py`:

```python
NEW_PROMPT = """Your prompt template here with {variables}"""
```

### Adding New Nodes

1. Define node function in `src/graph/nodes.py`
2. Add routing logic in `src/graph/routers.py`
3. Wire into workflow in `src/graph/workflow.py`

### Testing New Components

```bash
python scripts/test_components.py --component grader
```

## Features Status

### ✅ Completed
- Document relevance grading with LLM
- Query rewriting for improved retrieval
- Hallucination detection and correction
- Answer usefulness verification
- **Web search fallback (Tavily + DuckDuckGo)**
- A/B testing system for prompt variants
- CLI interface with Rich formatting
- Comprehensive test suite
- DevContainer/Codespaces auto-detection
- LangChain package migration (chroma, ollama)

### 🚧 Roadmap
- [ ] Streamlit web interface
- [ ] Multi-modal support (images, tables)
- [ ] Session memory and conversation context
- [ ] Docker containerization
- [ ] FastAPI REST endpoints
- [ ] Evaluation framework with metrics
- [ ] Fine-tuned Ollama models
- [ ] Conversation history persistence

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Submit a pull request

## License

MIT License - see LICENSE file for details

## References

- [LangGraph Documentation](https://python.langchain.com/docs/langgraph)
- [ChromaDB Documentation](https://docs.trychroma.com/)
- [Ollama Models](https://ollama.ai/library)
- [Agentic RAG Tutorial](https://www.kaggle.com/code/ksmooi/langgraph-agentic-rag-with-chroma)

## Citation

If you use this project in your research, please cite:

```bibtex
@software{agentic_rag_langgraph,
  title = {Agentic RAG with LangGraph},
  author = {Your Name},
  year = {2025},
  url = {https://github.com/yourusername/agentic-rag}
}
```

---

Built with ❤️ using LangGraph, ChromaDB, and Ollama
