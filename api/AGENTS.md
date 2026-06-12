# FastAPI Backend

**Hierarchy:** `api/` — REST gateway for frontend ↔ pipeline ↔ Argo.

## STRUCTURE
```
api/
├── main.py         # FastAPI app: lifespan, CORS, 8+ router mounts, static serve
├── config.py       # Settings from .env (load_dotenv side effects)
├── routers/        # Endpoints: agents, auth, files, memory, nodes, projects, runs, usage, workflows, argo_proxy
├── models/         # Pydantic response models per domain
├── services/       # Business logic: argo, node_index, project, workflow
└── tracking/       # Usage/activity tracking
```

## WHERE TO LOOK
| Task | Location |
|------|----------|
| Add endpoint | `api/routers/<domain>.py` + `api/models/<domain>.py` |
| Add business logic | `api/services/<domain>_service.py` |
| Modify auth | `api/routers/auth.py` |
| Agent API | `api/routers/agents.py` |

## KEY PATTERNS
- **Route prefix**: `/api/v1/`
- **Pydantic models** for all request/response (no bare dicts)
- **Service layer** separates business logic from routes
- **Workspace PVC** project isolation via `subPath`
- **Argo submit** requires MF → Argo YAML compilation (400 on failure)
- **WebSocket** endpoints for streaming Agent output
- **No Dockerfile** — run raw via `uvicorn api.main:app`
