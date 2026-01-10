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
# Pull the generation model (3B parameters)
ollama pull llama3.2

# Pull the embedding model (1024 dimensions)
ollama pull nomic-embed-text
```

Verify Ollama is running:
```bash
curl http://localhost:11434/api/tags
```

### 5. Configure environment

Copy the example environment file and configure:

```bash
cp .env.example .env
```

Edit `.env` to set your preferences:
```env
OLLAMA_BASE_URL=http://localhost:11434
GENERATION_MODEL=llama3.2
EMBEDDING_MODEL=nomic-embed-text
TAVILY_API_KEY=your_key_here  # Optional
```

## Quick Start

### 1. Load Documents

Add your documents to the vector store:

```bash
python cli/main.py load path/to/your/documents
```

Supported formats:
- PDF (`.pdf`)
- Markdown (`.md`)
- Plain text (`.txt`)

Or use the script directly:

```bash
python scripts/load_documents.py path/to/your/documents
```

### 2. Check System Status

Verify everything is working:

```bash
python cli/main.py status
```

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
# Fast, lightweight (recommended for most use cases)
GENERATION_MODEL=llama3.2

# Better reasoning (slower)
GENERATION_MODEL=mistral

# Most capable (requires more RAM)
GENERATION_MODEL=llama3.1
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

Enable web search fallback:

1. Get a free API key from [Tavily](https://tavily.com/) (1,000 requests/month free)
2. Add to `.env`:
   ```env
   TAVILY_API_KEY=your_key_here
   ```

Alternatively, use DuckDuckGo (no API key required, but lower quality results).

## CLI Commands

### Query Mode (Interactive)

```bash
python cli/main.py query [OPTIONS]

Options:
  --verbose, -v  Show detailed execution flow
  --model, -m    Specify Ollama model to use

Example:
  python cli/main.py query --verbose --model mistral
```

### Load Documents

```bash
python cli/main.py load <file_or_directory>

Examples:
  python cli/main.py load docs/
  python cli/main.py load research_paper.pdf
```

### System Status

```bash
python cli/main.py status

Shows:
  ✓ Ollama connection
  ✓ ChromaDB status
  ✓ Document count
  ✓ Available models
```

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
1. Using a smaller model: `llama3.2` (3B) instead of `llama3.1` (8B)
2. Reducing `RETRIEVAL_K` to retrieve fewer documents
3. Ensuring Ollama has sufficient RAM allocated

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

## Roadmap

- [ ] Streamlit web interface
- [ ] Multi-modal support (images, tables)
- [ ] Streaming responses
- [ ] Session memory and conversation context
- [ ] Docker containerization
- [ ] FastAPI endpoints
- [ ] Evaluation framework with metrics
- [ ] Fine-tuned Ollama models

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
