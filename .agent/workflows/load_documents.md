---
description: Load documents into the ChromaDB vector store
---

This workflow helps you ingest valid documents (PDF, Markdown, Text) into the system.

1. Load a specific file or directory
```bash
source venv/bin/activate
# Replace 'docs/' with your target file or directory
python cli/main.py load docs/
```
