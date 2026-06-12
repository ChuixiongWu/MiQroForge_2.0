# MF YAML Compiler

**Hierarchy:** `workflows/pipeline/` — Validates, compiles, and submits MF workflows.

## STRUCTURE
```
pipeline/
├── models.py     # Pydantic models for MF YAML structure
├── validator.py  # Schema compliance + type compatibility checks
├── compiler.py   # MF YAML → Argo Workflow YAML
├── loader.py     # File I/O: load MF YAML, resolve references
├── cli.py        # CLI: validate, compile, run
└── __init__.py   # Package marker
```

## WHERE TO LOOK
| Task | Location |
|------|----------|
| Fix compilation error | `compiler.py` |
| Add validation rule | `validator.py` |
| Modify YAML model | `models.py` |
| Add CLI command | `cli.py` |

## KEY PATTERNS
- **MF YAML** is human-editable intermediate format (not raw Argo YAML)
- **Two-phase**: validate (structure) → compile (generate Argo YAML)
- **Ephemeral nodes**: compiler generates thin wrapper scripts at compile time
- **Connected outputs**: skips unconsumed ports; SDP ports are never exported as Argo parameters (PVC `.stream/` transport only, etcd request size limit)
- **Sweep/fan-in**: compiler handles `parallel_sweep` + `auto_fan_out` + fan-in nodes
- **Run via**: `bash scripts/mf2.sh validate/compile/run`
