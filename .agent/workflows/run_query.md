---
description: Run the Agentic RAG CLI in interactive query mode
---

This workflow runs the main CLI application in query mode.

1. Run the query interface
```bash
source venv/bin/activate
python cli/main.py query
```

2. Run with verbose mode (optional, shows internal steps)
```bash
source venv/bin/activate
python cli/main.py query --verbose
```
