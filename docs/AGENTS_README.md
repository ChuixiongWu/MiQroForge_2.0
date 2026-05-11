# MiQroForge 2.0 Agents Layer Documentation

## Quick Navigation

This folder contains **comprehensive documentation** of the MiQroForge Phase 2 agents layer (intelligent workflow orchestration via LangGraph).

### 📚 Three Documents

1. **AGENTS_EXPLORATION_GUIDE.md** (30 KB) — **START HERE**
   - Executive summary
   - Architecture overview
   - All three agents explained
   - Integration points
   - Data flows
   - Troubleshooting
   
   **Best for**: Architects, system designers, anyone wanting the big picture

2. **AGENTS_TECHNICAL_REFERENCE.md** (22 KB) — **Deep dive**
   - Prompt system architecture
   - State management details
   - Generator-Evaluator loop mechanics
   - LLM configuration
   - Error handling
   - Agent-specific implementation details
   
   **Best for**: LLM engineers, backend developers, debuggers

3. **AGENTS_README.md** (this file) — **Navigation**
   - Quick overview
   - Document guide
   - Key findings summary
   - File reference

---

## At a Glance

### What Are the Agents?

Three LLM-powered agents that work together to transform user intent into executable computational chemistry workflows:

```
User Intent (natural language)
  ↓
[Planner Agent] → SemanticWorkflow (abstract, software-agnostic)
  ↓
[YAML Coder Agent] → MF YAML (concrete, executable)
  ↓
[Argo Workflow Engine] → Results
```

### Key Characteristics

✅ **Independent, callable agents** — No central orchestrator (Phase 3 feature)
✅ **Generator-Evaluator loops** — Iterative refinement with LLM + validator feedback
✅ **Max 3 iterations per agent** — Prevents infinite loops, always returns result
✅ **LLM-agnostic** — Configuration from `userdata/models.yaml`
✅ **RAG-powered** — Node discovery via vector store, no direct coupling to node internals
✅ **Tool-ready** — Tools available for Phase 3 agent patterns
✅ **Well-tested** — Shared patterns across all three agents

---

## The Three Agents

### 1. Planner Agent

**What it does**: Analyzes user intent → produces abstract workflow blueprint

**Input**: 
- `intent: str` — User goal ("Calculate H₂O thermochemistry")
- `molecule: str` — Target molecule (optional)
- `preferences: str` — User preferences (optional)

**Output**: `SemanticWorkflow`
- Abstract steps (no software specified)
- Data flow edges
- Candidate implementations (from RAG)
- Evaluation feedback

**Location**: `agents/planner/`

**Unique features**:
- Loads semantic types from registry
- RAG searches available nodes
- Checks workspace for user-uploaded files
- Validates DAG (no cycles)
- Evaluates scientific correctness

---

### 2. YAML Coder Agent

**What it does**: Translates semantic workflow → executable MF YAML

**Input**:
- `semantic_workflow` — From Planner
- `user_params` — Optional extra parameters
- `selected_implementations` — Optional manual node selections

**Output**: `ConcretizationResult`
- Executable MF YAML
- Validation report
- Node resolutions (step → node mapping)
- Evaluation feedback

**Location**: `agents/yaml_coder/`

**Unique features**:
- Loads complete node specifications
- Port type compatibility checking (critical!)
- Phase 1 validator integration
- Combines programmatic + LLM evaluation
- Handles user manual selections

---

### 3. Node Generator Agent

**What it does**: Generates new computational nodes (dual mode: Prefab + Ephemeral)

**Prefab Mode（正式节点生成）** — `POST /api/v1/agents/node`
- ReAct Agent 循环，使用工具链研究、生成、沙箱测试预制菜节点
- 工具系统 (17 个 LangChain @tool)：软件手册 BM25 检索、参考节点查询、Schema 查询、文件读写、沙箱执行
- 共享基础设施：经验记忆 (ChromaDB embedding)、上下文压缩、节点知识库
- 产出：nodespec.yaml + run.sh + input templates（不入库，前端确认后持久化）

**Ephemeral Mode（临时节点生成）** — `POST /api/v1/agents/ephemeral`
- `node_mode: "ephemeral"`
- `description` — 功能描述
- `ports` — 端口声明 `{'inputs': N, 'outputs': M}`
- ReAct Agent 内循环 (sandbox_execute + pip_install)
- Docker 沙箱执行 (`ephemeral-py:3.11` 镜像)
- 视觉评估 (GPT-4o multimodal)
- 外循环: generate → evaluate → retry (max 2 rounds)

**Location**: `agents/node_generator/`（ephemeral/ + prefab/ + shared/ 子模块）

**P2M4 新增能力**:
- 软件手册层级索引 (BM25 段落级搜索)
- 经验记忆系统 (ChromaDB embedding + JSONL 备份)
- 上下文压缩 (消息历史 token 管理)
- 正式节点沙箱测试（Docker 容器执行 + 结果捕获）

---

## Architecture Highlights

### Shared Patterns (All Three Agents)

```
TypedDict State
  ├─ Inputs (immutable)
  ├─ Intermediate (computed once)
  ├─ Outputs (mutable per iteration)
  ├─ Generator-Evaluator tracking
  └─ Error handling

Generate Node (LLM synthesis)
  └─ Reads issues from previous evaluation, adapts

Evaluate Node (dual validation)
  ├─ Programmatic (schema, DAG, validator)
  └─ LLM (intent, correctness, compatibility)

LangGraph Flow
  → generate → evaluate → [passed? END : refine?]
```

### Core Infrastructure

**schemas.py** — Pydantic models for inter-agent communication:
- `SemanticWorkflow` (Planner → YAML Coder)
- `ConcretizationResult` (YAML Coder → Argo)
- `NodeGenRequest/Result` (Node Generator)
- `EvaluationResult` (all agents)

**llm_config.py** — Flexible LLM configuration:
- Multi-model support
- Local server support (Ollama, etc.)
- Per-agent model assignment
- Hot-reload capability

**Prompts** — Jinja2 templates:
- System messages (role + rules + resources)
- Generation messages (task + context)
- Evaluation messages (criteria + checklist)

**Tools** — LangChain tools (not yet used in agent loops):
- Node search (RAG)
- Node details (Level 3)
- Semantic type queries
- Workflow validation
- Workspace access

---

## Integration Points

### Vector Store (`vectorstore/`)

Provides **three-level node retrieval**:

1. **Summary** — For Planner RAG search
2. **Semantic Type** — For Node Generator references
3. **Full Spec** — For YAML Coder port details

Auto-selects backend:
- ChromaDB (vector similarity, online)
- Keyword search (text matching, offline fallback)

### API Endpoints (`api/routers/agents.py`)

```
POST /api/v1/agents/plan              — Planner Agent
POST /api/v1/agents/yaml              — YAML Coder Agent
POST /api/v1/agents/node              — Node Generator Agent (Prefab)
POST /api/v1/agents/ephemeral         — Ephemeral Agent（运行时生成 + 沙箱执行 + 评估）
POST /api/v1/agents/ephemeral/evaluate — Ephemeral Visual Evaluator（多模态图片评估）
POST /api/v1/agents/save-session      — 保存对话会话到磁盘
```

All endpoints:
- Use `asyncio.to_thread()` for CPU-bound agents
- Return full state + evaluation
- Support optional query parameters for debugging

### LLM Configuration

File: `userdata/models.yaml`

```yaml
agents:
  planner: gpt-4o
  evaluator: gpt-4o
  yaml_coder: gpt-4o
  node_generator: gpt-4o

models:
  gpt-4o:
    model_id: gpt-4o
    base_url: "https://api.openai.com/v1"
    api_key: "sk-..."
```

---

## Key Design Principles

### 1. Semantic vs. Concrete Separation

**Planner** (semantic): No software names, no port names
**YAML Coder** (concrete): Maps semantic → specific nodes + ports
**Node Generator** (implementation): Generates nodespec.yaml + run.sh

→ Planner doesn't need to know node internals

### 2. RAG Decoupling

Agents see nodes as **JSON structures**, not Python objects:
- Via `vectorstore.retriever`
- Node library can evolve independently
- No tight coupling to node implementations

### 3. Generator-Evaluator Pattern

**All agents use identical loop**:
```
generate → evaluate → [passed? END : refine → ...]
```

Max 3 iterations per agent. Always returns result.

### 4. Fail-Open Philosophy

- Evaluator crash → treat as passed (prevent deadlock)
- Generator crash → capture error
- Validator error → include in issues (not fatal)

### 5. Tool Readiness (Phase 3 Foundation)

Tools are defined but **not used** in Phase 2:
- Direct Python calls (no overhead)
- Infrastructure for Phase 3 agent patterns
- Phase 3 Main Agent can enable tool-calling

---

## Configuration Requirements

### 1. `userdata/models.yaml` (required)

LLM provider configuration. Create from `models.yaml.example`.

### 2. `nodes/schemas/semantic_registry.yaml` (required)

Lists all semantic computation types:
```yaml
types:
  geometry-optimization:
    display_name: "Geometry Optimization"
    description: "Compute optimized molecular geometry"
```

### 3. `nodes/base_images/registry.yaml` (optional, for Node Generator)

Docker image registry:
```yaml
images:
  - name: orca:6.1
    description: "ORCA 6.1"
    source_type: user-built
```

---

## Testing & Debugging

### Run Individual Agents

```python
# Planner
from agents.planner.graph import run_planner
result = run_planner("Calculate H2O thermo", molecule="H2O")

# YAML Coder
from agents.yaml_coder.graph import run_yaml_coder
result = run_yaml_coder(result["semantic_workflow"])

# Node Generator
from agents.node_generator import run_node_generator
from agents.schemas import NodeGenRequest
result = run_node_generator(NodeGenRequest(node_mode="prefab", ...))
```

### Check Status

```bash
# Is vectorstore indexed?
ls -la userdata/vectorstore/chroma/.index_type

# Reindex if needed
python -m vectorstore.indexer

# Check config
cat userdata/models.yaml
```

### Common Issues

| Problem | Cause | Fix |
|---------|-------|-----|
| "models.yaml not found" | Config missing | Create from example |
| ChromaDB fails | No network/GPU | Falls back to keyword search |
| Node not found | Index stale | Run `python -m vectorstore.indexer` |
| Invalid steps | Missing semantic_registry.yaml | Check file exists, has types |
| Port mismatch | Incompatible categories | Check YAML system prompt rules |

---

## Next Steps

### For Architects

1. Read **AGENTS_EXPLORATION_GUIDE.md** → big picture
2. Review data flow diagrams
3. Understand semantic vs. concrete layering
4. Plan Phase 3 extensions

### For Developers

1. Read **AGENTS_TECHNICAL_REFERENCE.md** → implementation details
2. Study prompt templates in `agents/<agent>/prompts/`
3. Trace through `agents/<agent>/graph.py` (LangGraph assembly)
4. Test agents independently (code examples in AGENTS_TECHNICAL_REFERENCE.md)

### For LLM Engineers

1. Review prompt templates (Jinja2, three-message pattern)
2. Check `agents/llm_config.py` for model selection logic
3. Understand Generator-Evaluator iteration loop
4. Plan Phase 3 tool-calling patterns

### For Phase 3 Planning

1. All agents are templates for future agents
2. Main Agent, Debug Agent, Review Agent will use same LangGraph patterns
3. Tools are ready for Phase 3 ReAct/ToolExecutor patterns
4. Memory store will plug into state management

---

## File Structure

```
agents/
├── schemas.py              # Shared Pydantic models
├── llm_config.py           # LLM provider config
├── common/
│   ├── prompt_loader.py    # Jinja2 template rendering
│   ├── eval_loop.py        # Generator-Evaluator factory
│   └── session_logger.py   # Thread-safe session logging
├── tools/                  # Phase 2 早期工具 (node_search, validate, workspace — 待迁移)
├── planner/                # Planner Agent
│   ├── state.py, generator.py, evaluator.py, graph.py
│   └── prompts/
├── yaml_coder/             # YAML Coder Agent
│   ├── state.py, generator.py, evaluator.py, graph.py
│   └── prompts/
└── node_generator/         # Node Generator Agent (Prefab + Ephemeral)
    ├── __init__.py         #   统一入口 run_node_generator()
    ├── prefab/             #   Prefab 模式：正式节点生成
    │   ├── state.py, generator.py, evaluator.py, graph.py
    │   ├── tools.py        #     17 个 LangChain @tool（手册/节点/Schema/文件/沙箱）
    │   └── prompts/
    ├── ephemeral/          #   Ephemeral 模式：临时节点生成
    │   ├── state.py, generator.py, evaluator.py, graph.py
    │   ├── sandbox.py      #     Docker 沙箱执行
    │   └── prompts/
    └── shared/             #   共享基础设施
        ├── knowledge.py    #     节点库 + 镜像注册表感知
        ├── sandbox_base.py #     沙箱环境管理
        ├── manual_index.py #     BM25 软件手册层级索引
        ├── memory.py       #     ChromaDB 经验记忆系统
        └── compression.py  #     消息历史 token 压缩

api/
├── models/agents.py        # Pydantic request/response models
├── routers/agents.py       # FastAPI agent 端点
└── routers/memory.py       # 经验记忆管理端点

vectorstore/
├── indexer.py              # Build index
├── retriever.py            # Query interface
└── config.py               # ChromaDB config

docs/
├── AGENTS_README.md        # This file
├── AGENTS_EXPLORATION_GUIDE.md    # Big picture
├── AGENTS_TECHNICAL_REFERENCE.md  # Deep dive
└── software_manuals/       # 软件手册 (BM25 索引供 Prefab Agent 检索)
```

---

## References

- **CLAUDE.md** — Full project architecture (Phase 2 section)
- **Phase 1 Validator** — `workflows/pipeline/validator.py`
- **Node Index** — `node_index/scanner.py`
- **FastAPI Main** — `api/main.py`

---

## Summary

The MiQroForge agents layer is a **production-ready Phase 2 implementation** providing:

✅ Three independently callable LLM agents
✅ Iterative refinement with Generator-Evaluator loops
✅ Semantic ↔ concrete translation pipeline
✅ RAG-powered node discovery
✅ Flexible LLM configuration
✅ Comprehensive error handling
✅ Foundation for Phase 3 extensions

**Design philosophy**: AI-assisted but human-controlled. Agents propose, humans review, agents refine.

---

Generated: 2026-04-13
Documentation Version: 2.0 (post-M2 update)
