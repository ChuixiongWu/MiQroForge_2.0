# RAG Vector Retrieval

**Hierarchy:** `vectorstore/` — ChromaDB-based semantic search over node schemas.

## STRUCTURE
```
vectorstore/
├── config.py      # ChromaDB connection, collection name, persistence dir
├── indexer.py     # Reads node_index.yaml → creates/updates ChromaDB collection
├── retriever.py   # Query interface: ChromaDB semantic search + keyword fallback
└── __init__.py    # Package marker
```

## WHERE TO LOOK
| Task | Location |
|------|----------|
| Change vector DB | `config.py` |
| Rebuild index | `python -m vectorstore.indexer` |
| Modify retrieval strategy | `retriever.py` |

## KEY PATTERNS
- **ChromaDB (dev)** / FAISS (prod) — swappable via config
- **Two-level retrieval**: summary (relevance) → detail (full schema JSON)
- **Used by**: Planner Agent's RAG node lookup
- **Index source**: `nodes/node_index.yaml`
- **Keyword fallback**: BM25 / TF-IDF when vector search fails
