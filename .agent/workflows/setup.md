---
description: Set up the development environment, install dependencies, and configure Ollama
---

This workflow will help you set up the Agentic RAG system environment.

1. Create a virtual environment (if not already created)
```bash
python3 -m venv venv
```

2. Activate the virtual environment and install dependencies
```bash
source venv/bin/activate
pip install -r requirements.txt
```

3. Copy the example environment file
```bash
cp .env.example .env
```

4. Pull required Ollama models
// turbo
```bash
ollama pull llama3.2
ollama pull nomic-embed-text
```

5. Verify Ollama is running
// turbo
```bash
curl http://localhost:11434/api/tags
```
