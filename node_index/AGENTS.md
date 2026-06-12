# Node Indexing Engine

**Hierarchy:** `node_index/` — Scans `nodespec.yaml` files → searchable index.

## STRUCTURE
```
node_index/
├── models.py    # NodeIndex, NodeIndexEntry, PortSummary (Pydantic)
├── scanner.py   # Directory walk + YAML parse → NodeIndex
├── search.py    # Weighted text search over indexed nodes
├── cli.py       # CLI: reindex, list, search, info
└── __init__.py  # Package marker
```

## WHERE TO LOOK
| Task | Location |
|------|----------|
| Modify index format | `models.py` |
| Add index field | `scanner.py` + `models.py` |
| Tweak search weights | `search.py` |
| Run from script | `python -m node_index.cli reindex` or `mf2.sh nodes reindex` |

## KEY PATTERNS
- **No DB** — file-system based (reads all `nodespec.yaml` files)
- **Output**: `nodes/node_index.yaml` (gitignored, regenerated via `mf2 nodes reindex`)
- **Two search levels**: summary (name + brief) and detail (full schema)
- **Used by**: RAG indexer, planner agent, API nodes router
