# Core Pydantic Schema System

**Hierarchy:** `nodes/schemas/` — Single Source of Truth for all node definitions.

## STRUCTURE
```
schemas/
├── node.py                 # NodeSpec (complete node definition)
├── io.py                   # Stream I/O 4-class + On-Board I/O + Quality Gate
├── resources.py            # ComputeResources / LightweightResources
├── connection.py           # Port compatibility rules
├── base.py                 # NodeMetadata / NodeType / NodeCategory
├── units.py                # Physical unit registry
├── semantic_registry.py    # Semantic type registry (Python API)
├── semantic_registry.yaml  # Semantic type data (YAML source)
├── base_image.py           # BaseImageEntry model
├── __init__.py             # Public API re-exports
└── README.md               # Node development guide
```

## WHERE TO LOOK
| Task | Location |
|------|----------|
| Add I/O type | `io.py` + `semantic_registry.yaml` |
| Add resource type | `resources.py` |
| Modify NodeSpec | `node.py` |
| Change port rules | `connection.py` |
| Add unit | `units.py` + `semantic_registry.yaml` |

## KEY PATTERNS
- **NodeSpec** is the SOLE source of truth → serialized to `nodespec.yaml`
- **`node_index.yaml`** auto-generated from all `nodespec.yaml` files
- **Agent layer NEVER imports schemas** — uses RAG vectorstore instead
- **Semantic type yaml** is data-driven — Python wrapper reads it
- **`__init__.py`** carefully curated public API (only exported symbols are public)
