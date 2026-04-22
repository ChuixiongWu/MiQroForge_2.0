# MiQroForge 2.0 Agents Layer — Complete Exploration Guide

## Executive Summary

The **agents/** directory implements Phase 2 of MiQroForge: the intelligent workflow orchestration layer using LangGraph. Three independent LLM-powered agents work together to transform user intent into executable computational chemistry workflows:

1. **Planner Agent** — Intent → Semantic Workflow (abstract, software-agnostic)
2. **YAML Coder Agent** — Semantic Workflow → MF YAML (concrete, executable)
3. **Node Generator Agent** — Generate new computational nodes

All agents follow a **Generator-Evaluator pattern** with iterative refinement (max 3 iterations per agent). They are independently callable via FastAPI endpoints and do NOT require a central Main Agent (Phase 3 feature).

---

## Directory Structure

```
agents/
├── __init__.py
├── schemas.py                    # Shared data models (SemanticWorkflow, etc.)
├── llm_config.py                 # LLM provider abstraction (models.yaml)
├── common/
│   ├── __init__.py
│   ├── prompt_loader.py          # Jinja2 template rendering
│   ├── eval_loop.py              # Generator-Evaluator loop builder
│   └── session_logger.py         # Thread-safe session logging (contextvars)
├── tools/                         # LangChain tools for all agents
│   ├── __init__.py
│   ├── node_search.py            # RAG node retrieval
│   ├── load_nodespec.py          # Load complete NodeSpec by name
│   ├── semantic_registry.py      # Query semantic types
│   ├── validate_workflow.py      # Phase 1 validator integration
│   └── workspace.py              # Workspace file access
├── planner/                       # Planner Agent (Intent → Semantic Workflow)
│   ├── __init__.py
│   ├── state.py                  # PlannerState TypedDict
│   ├── generator.py              # LLM generation node
│   ├── evaluator.py              # Evaluation + DAG validation
│   ├── graph.py                  # LangGraph assembly + run_planner()
│   └── prompts/
│       ├── plan_system.jinja2    # System message (instructions + semantic types)
│       ├── plan_generate.jinja2  # User message (intent + node candidates)
│       └── plan_evaluate.jinja2  # Evaluation prompt
├── yaml_coder/                    # YAML Coder Agent (Semantic → MF YAML)
│   ├── __init__.py
│   ├── state.py                  # YAMLCoderState TypedDict
│   ├── generator.py              # LLM generation node
│   ├── evaluator.py              # Validation + intent checking
│   ├── graph.py                  # LangGraph assembly + run_yaml_coder()
│   └── prompts/
│       ├── yaml_system.jinja2    # System message (MF YAML format + available nodes)
│       ├── yaml_generate.jinja2  # User message (workflow + resolutions)
│       └── yaml_evaluate.jinja2  # Evaluation prompt
└── node_generator/                # Node Generator Agent (Formal + Ephemeral modes)
    ├── __init__.py
    ├── state.py                  # NodeGenState TypedDict (incl. ephemeral fields)
    ├── generator.py              # Dual-mode generator (formal: LLM; ephemeral: ReAct Agent)
    ├── evaluator.py              # Dual-mode evaluator (formal: Schema; ephemeral: exec + vision)
    ├── graph.py                  # LangGraph assembly with mode routing
    ├── knowledge.py              # Load reference nodes + available images
    ├── sandbox.py                # Sandbox execution (Docker container isolation)
    └── prompts/
        ├── nodegen_system.jinja2              # Formal: System message
        ├── nodegen_generate.jinja2            # Formal: Generation prompt
        ├── nodegen_evaluate.jinja2            # Formal: Evaluation prompt
        ├── nodegen_ephemeral_system.jinja2    # Ephemeral: System message
        ├── nodegen_ephemeral_generate.jinja2  # Ephemeral: Generation prompt
        ├── nodegen_ephemeral_evaluate.jinja2  # Ephemeral: Evaluation prompt
        └── nodegen_ephemeral_evaluate_vision.jinja2  # Ephemeral: Vision evaluation
```

---

## Core Infrastructure

### 1. `agents/schemas.py` — Shared Data Models

Defines the interchange formats between agents:

#### Planner Output
```python
class SemanticStep(BaseModel):
    """Abstract computation step (no software specified)."""
    id: str                    # "step-1", "step-2", ...
    semantic_type: str         # From semantic_registry.yaml
    display_name: str
    description: str
    rationale: str            # Why Planner chose this step
    constraints: dict[str, str]  # Hints for YAML Coder (method, basis, etc.)

class SemanticEdge(BaseModel):
    """Data flow between steps (no port names)."""
    from_step: str
    to_step: str
    data_description: str     # "optimized geometry"

class SemanticWorkflow(BaseModel):
    """Planner's output — abstract workflow."""
    name: str
    description: str
    target_molecule: str
    steps: list[SemanticStep]
    edges: list[SemanticEdge]
    planner_notes: str
    available_implementations: dict[str, list[str]]  # step_id → [node_names...]
```

#### YAML Coder Output
```python
class NodeResolution(BaseModel):
    """Maps semantic step → concrete node."""
    step_id: str
    resolved_node: Optional[str]       # Which node to use
    resolved_nodespec_path: Optional[str]
    onboard_params: dict[str, Any]     # Parameter values
    needs_new_node: bool

class ConcretizationResult(BaseModel):
    """YAML Coder's output — concrete executable workflow."""
    resolutions: list[NodeResolution]
    mf_yaml: str                       # Generated MF YAML
    missing_nodes: list[str]           # Steps without implementations
    validation_passed: bool
    validation_errors: list[str]
    evaluation: Optional[EvaluationResult]
```

#### Node Generator Output
```python
class NodeGenRequest(BaseModel):
    """Node Generator input request."""
    semantic_type: str
    description: str
    target_software: Optional[str]
    target_method: Optional[str]
    category: str = "chemistry"
    node_mode: str = "formal"        # "formal" or "ephemeral"
    # Ephemeral-specific fields:
    ports: Optional[dict]             # {'inputs': N, 'outputs': M}
    context: Optional[dict]           # upstream/downstream/sweep context
    reference_nodes: list[str] = []

class NodeGenResult(BaseModel):
    """Node Generator output — saved node."""
    node_name: str
    nodespec_yaml: str
    run_sh: Optional[str]
    input_templates: dict[str, str]
    saved_path: Optional[str]
    evaluation: Optional[EvaluationResult]
    script_content: Optional[str]     # Ephemeral mode: generated Python script
```

#### Evaluation Result (All Agents)
```python
class EvaluationResult(BaseModel):
    """Generator-Evaluator pattern outcome."""
    passed: bool
    issues: list[str]       # Problems found
    suggestions: list[str]  # How to fix
    iteration: int          # Which iteration (0-based)
```

---

### 2. `agents/llm_config.py` — LLM Provider Abstraction

**Purpose**: Centralized model configuration from `userdata/models.yaml`

**Key Components**:
- `_load_registry()` — Load and cache `userdata/models.yaml`
- `_resolve_model_config(purpose)` — Resolve which model to use
  - Priority: `agents.<purpose>` → `default_model` → first defined model
  - Each model can override `base_url` and `api_key` (for local models, API proxies, etc.)
- `get_chat_model(purpose, temperature)` — Returns LangChain `ChatOpenAI` instance
- `LLMConfig` class — Static interface

**Configuration File** (`userdata/models.yaml.example`):
```yaml
proxy:
  base_url: "https://api.openai.com/v1"
  api_key: "sk-..."

agents:
  planner: gpt-4o
  evaluator: gpt-4o
  yaml_coder: gpt-4o
  node_generator: gpt-4o

default_model: gpt-4o

models:
  gpt-4o:
    model_id: gpt-4o
    # Optional: model-specific overrides
    base_url: ""
    api_key: ""
```

---

### 3. `agents/common/prompt_loader.py` — Jinja2 Template Rendering

Loads and renders `.jinja2` templates from agent prompt directories.

```python
load_prompt("planner/prompts/plan_system.jinja2", semantic_types={...})
→ renders template with variables, returns str
```

**Key Features**:
- `StrictUndefined` — Catches missing variables
- `trim_blocks=True, lstrip_blocks=True` — Clean whitespace

---

### 4. `agents/common/eval_loop.py` — Generator-Evaluator Pattern

Factory for building LangGraph sub-graphs with iterative refinement:

```python
graph = build_eval_loop(
    state_type=MyState,
    generate_fn=generate_node,
    evaluate_fn=evaluate_node,
    state_key="output",
    evaluation_key="evaluation",
    max_iterations=3
)
```

**Flow**:
```
generate → evaluate → [passed? → END : max_iter? → refine → evaluate → ...]
```

---

### 5. `agents/tools/` — LangChain Tools Available to All Agents

#### `node_search.py`
- `search_nodes_summary(query, n=8)` — RAG retrieval by natural language
- `search_nodes_by_semantic_type(type)` — Exact type match
- `get_node_details(names)` — Load complete NodeSpec(s)

**Implementation**: Delegates to `vectorstore.retriever.get_retriever()`

#### `load_nodespec.py`
- `load_nodespec_by_name(name)` — Load single node's full spec from YAML

#### `semantic_registry.py`
- `query_semantic_registry(query)` — List all semantic types (with optional filter)

#### `validate_workflow.py`
- `validate_mf_yaml(yaml_content)` — Run Phase 1 validator on workflow YAML

#### `workspace.py`
- `workspace_list_files(project_root)` — List files in user's workspace directory
- `workspace_read_file(filename, project_root, max_chars)` — Read file content (with truncation)

**Use Case**: Planner checks what input files user uploaded and includes filenames in constraints.

---

## Agent Architecture — Individual Components

### Agent 1: Planner Agent

**Purpose**: Analyze user intent → Design abstract semantic workflow

**Input**:
- `intent: str` — User's natural language goal
- `molecule: str` — Target molecule (optional)
- `preferences: str` — User preferences (optional)

**Output**: `SemanticWorkflow` (abstract, no software specified)

#### State Definition (`planner/state.py`)
```python
class PlannerState(TypedDict, total=False):
    # Input
    intent: str
    molecule: str
    preferences: str
    
    # Intermediate
    node_summaries: list[dict]        # RAG retrieval results
    semantic_types: dict[str, Any]    # Loaded from semantic_registry.yaml
    
    # Output
    semantic_workflow: Optional[SemanticWorkflow]
    workflow_json: str                # JSON serialization for evaluation
    
    # Generator-Evaluator
    evaluation: Optional[EvaluationResult]
    iteration: int
    
    # Error
    error: Optional[str]
```

#### Generation Node (`planner/generator.py`)

**Function**: `generate_plan(state: PlannerState) -> dict`

**Flow**:
1. Load semantic types from `semantic_registry.yaml`
2. RAG search for nodes matching intent + molecule
3. Get workspace files (for geometry hints)
4. Construct LLM prompts:
   - **System**: Semantic types catalog + rules
   - **User**: Intent + molecule + RAG results + workspace files
5. Parse LLM response as JSON → `SemanticWorkflow`
6. Map RAG results to steps as `available_implementations`

**Key Helper Functions**:
- `load_semantic_types()` — From YAML
- `search_nodes_for_intent(intent, molecule)` — RAG via vectorstore
- `_extract_json(text)` — Extract JSON from LLM markdown code blocks
- `_build_implementations(steps, nodes)` — Map steps → candidate nodes

#### Evaluation Node (`planner/evaluator.py`)

**Function**: `evaluate_plan(state: PlannerState) -> dict`

**Checks**:
1. **Programmatic** (no LLM):
   - Edge endpoints valid (from_step/to_step exist)
   - DAG no-cycle check (DFS)
   - Semantic types in registry
   
2. **LLM-based**:
   - Completeness (workflow answers user goal)
   - Scientific correctness (geo-opt before freq, etc.)
   - Parameter validity

**Output**: `EvaluationResult`

#### LangGraph Assembly (`planner/graph.py`)

```
START → prepare (load types + RAG)
  ↓
  generate (LLM synthesis)
  ↓
  evaluate (check validity)
  ↓
  [passed? → END : iterate < 3? → increment → generate → ...]
```

**Public Interface**: `run_planner(intent, molecule, preferences) → PlannerState`

#### Prompts

**`plan_system.jinja2`**:
- Lists all semantic types
- MF YAML example structure
- Rules: output JSON only, use semantic types correctly, geo-opt before freq

**`plan_generate.jinja2`**:
- User's intent + molecule + preferences
- Workspace files list
- RAG-retrieved node summaries
- Task: design SemanticWorkflow

**`plan_evaluate.jinja2`**:
- Original intent
- Proposed workflow JSON
- Evaluation criteria

---

### Agent 2: YAML Coder Agent

**Purpose**: Translate semantic workflow → executable MF YAML

**Input**:
- `semantic_workflow: SemanticWorkflow` — From Planner
- `user_params: dict` — Extra parameters (optional)
- `selected_implementations: dict` — Manual step→node selection (optional)

**Output**: `ConcretizationResult` (with `mf_yaml: str`)

#### State Definition (`yaml_coder/state.py`)
```python
class YAMLCoderState(TypedDict, total=False):
    # Input
    semantic_workflow: SemanticWorkflow
    user_params: dict[str, Any]
    selected_implementations: dict[str, str]  # step_id → node_name
    
    # Intermediate
    available_nodes: list[dict]              # Full NodeSpec(s)
    resolutions: list[NodeResolution]        # Step → node mapping
    
    # Generation
    mf_yaml: str
    validation_valid: bool
    validation_errors: list[str]
    validation_warnings: list[str]
    
    # Generator-Evaluator
    evaluation: Optional[EvaluationResult]
    iteration: int
    
    # Output
    result: Optional[ConcretizationResult]
    
    # Error
    error: Optional[str]
```

#### Generation Node (`yaml_coder/generator.py`)

**Function**: `generate_yaml(state: YAMLCoderState) -> dict`

**Flow**:
1. **Load node details** (Level 3 — complete NodeSpec):
   - Prefer user's `selected_implementations`
   - Fallback to RAG candidates from `semantic_workflow.available_implementations`
2. **Build resolutions** — Each step → node mapping with onboard_params from constraints
3. **Construct LLM prompts**:
   - **System**: MF YAML format spec + port definitions for all nodes
   - **User**: Semantic workflow + resolutions + user_params
4. **Generate MF YAML** via LLM
5. Strip markdown code block markers

**Key Helper Functions**:
- `_load_node_details(workflow, implementations)` — Fetch complete NodeSpec(s) via retriever
- `_build_resolutions(...)` — Map steps to nodes
- `_get_nodespec_path(name)` — Look up path in node index

#### Evaluation Node (`yaml_coder/evaluator.py`)

**Function**: `evaluate_yaml(state: YAMLCoderState) -> dict`

**Checks**:
1. **Programmatic** (via Phase 1 validator):
   - Port type compatibility (file category matches)
   - DAG validity
   - Node existence
   - Parameter completeness

2. **LLM-based**:
   - Intent faithfulness (semantic workflow → YAML faithful)
   - Parameter completeness
   - Connection correctness
   - Scientific validity

**Output**: `EvaluationResult` + `validation_valid`, `validation_errors`

#### LangGraph Assembly (`yaml_coder/graph.py`)

```
START → generate (LLM synthesis)
  ↓
  evaluate (validation)
  ↓
  [passed? → finalize : iterate < 3? → increment → generate → ...]
  ↓
  finalize (assemble ConcretizationResult)
  ↓
  END
```

**Public Interface**: `run_yaml_coder(semantic_workflow, user_params, selected_impl) → YAMLCoderState`

#### Prompts

**`yaml_system.jinja2`**:
- MF YAML structure example
- Each available node: name, nodespec_path, description, semantic_type, software, port definitions
- **CRITICAL**: Port type compatibility rules (physical_quantity ↔ physical_quantity, etc.)

**`yaml_generate.jinja2`**:
- Semantic workflow JSON
- Node resolutions (step → node mapping)
- User parameters
- Previous YAML + validation errors (if iteration > 0)
- Task: generate complete MF YAML

**`yaml_evaluate.jinja2`**:
- Original semantic workflow
- Generated YAML
- Programmatic validation result
- Evaluation checklist

---

### Agent 3: Node Generator Agent

**Purpose**: Generate new computational nodes (dual mode: Formal + Ephemeral)

**Formal Mode Input**:
```python
class NodeGenRequest:
    semantic_type: str          # "geometry-optimization"
    description: str            # Detailed requirements
    target_software: Optional[str]  # "ORCA", "GROMACS", etc.
    target_method: Optional[str]    # "B3LYP", etc.
    category: str              # "chemistry", "quantum", etc.
    node_mode: str = "formal"  # "formal" or "ephemeral"
```

**Ephemeral Mode Additional Fields**:
```python
    ports: Optional[dict]       # {'inputs': N, 'outputs': M}
    context: Optional[dict]     # upstream/downstream/sweep context
```

**Output**: `NodeGenResult` (formal: saved to `userdata/nodes/`; ephemeral: script content + execution results)

#### State Definition (`node_generator/state.py`)
```python
class NodeGenState(TypedDict, total=False):
    # Input
    request: NodeGenRequest

    # Intermediate knowledge (formal mode)
    reference_nodes: list[dict]        # Few-shot examples (same software)
    available_images: list[dict]       # From base_images/registry.yaml
    semantic_types: dict[str, Any]

    # Generation (formal mode)
    nodespec_yaml: str
    run_sh: str
    input_templates: dict[str, str]    # filename → content

    # Generation (ephemeral mode)
    _input_data: dict[str, str]        # Real input data {port_name: content}
    script: str                        # Generated Python script
    exec_stdout: str                   # Sandbox execution stdout
    exec_stderr: str                   # Sandbox execution stderr
    exec_return_code: int              # Sandbox execution return code
    generated_files: list[str]         # Files produced by sandbox
    image_files: list[str]             # Image files detected in output
    vision_feedback: list[str]         # Visual evaluation feedback
    _sandbox_dir: str                  # Persistent sandbox directory path

    # Generator-Evaluator
    evaluation: Optional[EvaluationResult]
    iteration: int

    # Output
    result: Optional[NodeGenResult]

    # Error
    error: Optional[str]
```

#### Generation Node (`node_generator/generator.py`) — Dual Mode

**Formal Mode Flow**:
1. **Load knowledge**: available images, semantic types, reference nodes (few-shot)
2. **Construct LLM prompts**: NodeSpec structure + rules + available images + reference nodes
3. **Generate output sections** (marked by separators): `=== NODESPEC_YAML ===`, `=== RUN_SH ===`, `=== INPUT_TEMPLATE ===`
4. Parse sections from LLM response

**Ephemeral Mode Flow** (ReAct Agent inner loop):
1. **Load input data** and config from `userdata/settings.yaml`
2. **Create sandbox tools**: `sandbox_execute` (bound to input data + env overrides) + `pip_install`
3. **LLM with tool calling**: LLM decides when to execute scripts, install packages, or finish
4. **Inner loop**: LLM → tool call → sandbox result → LLM reads result → self-corrects or finishes
5. **Extract final script** from last `sandbox_execute` tool call in conversation history

**Key Helper Functions**:
- `_parse_generated_output(text)` — Extract marked sections (formal mode)
- `_extract_script(text)` — Extract Python script from LLM text response (ephemeral fallback)
- `_load_ephemeral_settings()` — Load runtime config from `userdata/settings.yaml`
- `load_reference_nodes()` — Find similar nodes (few-shot examples)
- `load_available_images()` — From registry

#### Evaluation Node (`node_generator/evaluator.py`) — Dual Mode

**Function**: `evaluate_node(state: NodeGenState) -> dict`

**Formal Mode Checks**:
1. **Programmatic** (no LLM):
   - YAML parseable
   - Pydantic NodeSpec validation
   - Semantic type in registry
   - Port names snake_case
   - Compute nodes have run.sh with `# MF2 init` marker

2. **LLM-based**:
   - Implementation correctness (semantic type behavior)
   - Port design (minimal and correct)
   - run.sh logic
   - Parameter completeness

**Ephemeral Mode Checks** (`_evaluate_ephemeral`):
1. **Programmatic**: Python syntax check, I/O path conventions, sweep type conversion
2. **Execution result**: return_code check
3. **Output detection**: verify files were generated
4. **Visual evaluation** (`evaluate_node_vision`): send images to GPT-4o for multimodal quality check

**Output**: `EvaluationResult`

#### LangGraph Assembly (`node_generator/graph.py`)

**Dual-mode topology**:

```
Formal mode:
  START → generate → evaluate → [pass? save : refine → generate → ...]
  save: write to userdata/nodes/ + trigger reindex

Ephemeral mode:
  START → generate → save → END
  (Inner ReAct Agent loop runs inside generate; outer loop runs in API endpoint)
```

**Save Logic** (`_save_to_userdata`):
- Formal: Create `userdata/nodes/<category>/<node-name>/`, write nodespec.yaml + run.sh + templates, trigger reindex
- Ephemeral: Skip file persistence, return script content directly

**Public Interface**: `run_node_generator(request: NodeGenRequest, **extra_state) -> NodeGenState`

#### Knowledge Loading (`node_generator/knowledge.py`)

- `load_available_images(project_root)` — Parse `base_images/registry.yaml`
- `load_reference_nodes(target_software, semantic_type, max_refs=2)` — Find similar nodes for few-shot examples

#### Prompts

**`nodegen_system.jinja2`**:
- NodeSpec structure (metadata, stream_inputs/outputs, onboard_inputs/outputs, execution, resources)
- run.sh template structure (# MF2 init, env vars, template rendering, software invocation, output extraction)
- Available base images
- Available semantic types
- Key rules: string.Template syntax, /mf/input/ and /mf/output/ paths, MPI environment vars

**`nodegen_generate.jinja2`**:
- Request (semantic_type, description, target_software, target_method, category)
- Reference nodes (few-shot examples with nodespec + run.sh)
- Previous attempt + issues (if iteration > 0)
- Output format markers

**`nodegen_evaluate.jinja2`**:
- Generation request
- Generated nodespec.yaml
- Generated run.sh
- Evaluation checklist (programmatic + intent checks)

---

## Integration Points

### RAG Vector Store (`vectorstore/`)

**Files**:
- `vectorstore/config.py` — ChromaDB config (collection name, embedding model)
- `vectorstore/indexer.py` — Build index from `node_index.yaml`
- `vectorstore/retriever.py` — Query interface (search, by semantic type, load details)

**Key Classes**:
- `ChromaRetriever` — Vector search via chromadb
- `KeywordRetriever` — Fallback keyword search (offline)
- `NodeRetriever` — Unified interface (auto-selects backend)

**Integration Points**:
- Planner calls `retriever.search_summary(intent)` for candidates
- YAML Coder calls `retriever.get_detailed(node_names)` for full specs
- Node Generator calls `retriever.get_by_semantic_type()` and `get_all()` for reference nodes

---

### FastAPI API Layer (`api/routers/agents.py`)

**Endpoints**:

#### `POST /api/v1/agents/plan`
```python
@router.post("/plan", response_model=PlanResponse)
async def plan_workflow(request: PlanRequest) -> PlanResponse:
    # request: intent, molecule, preferences
    # response: semantic_workflow, evaluation, available_nodes, error
```

#### `POST /api/v1/agents/yaml`
```python
@router.post("/yaml", response_model=YAMLResponse)
async def generate_yaml(request: YAMLRequest) -> YAMLResponse:
    # request: semantic_workflow, user_params, selected_implementations
    # response: mf_yaml, validation_report, result, error
```

#### `POST /api/v1/agents/node`
```python
@router.post("/node", response_model=NodeGenAPIResponse)
async def generate_node(request: NodeGenAPIRequest) -> NodeGenAPIResponse:
    # request: semantic_type, description, target_software, target_method, category
    # response: node_name, nodespec_yaml, run_sh, input_templates, saved_path, evaluation, error
```

#### `POST /api/v1/agents/ephemeral`
```python
@router.post("/ephemeral", response_model=EphemeralGenResponse)
async def ephemeral_generate(request: EphemeralGenRequest) -> EphemeralGenResponse:
    # request: description, ports, context, input_data, run_name, project_id
    # response: script, stdout, stderr, return_code, success, generated_files, image_files
```

#### `POST /api/v1/agents/ephemeral/evaluate`
```python
@router.post("/ephemeral/evaluate", response_model=EphemeralEvalResponse)
async def ephemeral_evaluate(request: EphemeralEvalRequest) -> EphemeralEvalResponse:
    # request: description, ports, script, stdout, stderr, image_base64_list
    # response: passed, issues, suggestions
```

#### `POST /api/v1/agents/save-session`
```python
@router.post("/save-session", response_model=SaveSessionResponse)
async def save_session(request: SaveSessionRequest) -> SaveSessionResponse:
    # request: session_id, messages
    # response: saved, session_id, path, message_count
```

**Design**:
- All endpoints use `asyncio.to_thread()` to run CPU-bound agent graphs
- Agents are called sequentially (no concurrent calls)
- Each endpoint returns full state, including evaluation results

---

### LLM Configuration

**File**: `userdata/models.yaml` (gitignored)
**Template**: `models.yaml.example` (in root)

**Resolution Logic**:
1. Purpose (e.g., "planner") → Agent-specific model name
2. Model name → `models.<name>` configuration
3. Each model can specify `base_url` and `api_key` (overrides global proxy)

**Example**:
```yaml
proxy:
  base_url: "https://api.openai.com/v1"
  api_key: "sk-..."

agents:
  planner: gpt-4o          # Use gpt-4o for planner
  evaluator: gpt-4o        # Use gpt-4o for evaluators
  yaml_coder: gpt-4o
  node_generator: gpt-4o

default_model: gpt-4o

models:
  gpt-4o:
    model_id: gpt-4o
```

---

## Data Flow and Interaction Patterns

### Typical User Workflow

```
User Request (intent + molecule)
  ↓
/api/v1/agents/plan
  ├─ Planner loads semantic types + RAG searches
  ├─ LLM synthesizes SemanticWorkflow (abstract)
  ├─ Evaluator checks DAG, semantic types, scientific logic
  └─ Returns: semantic_workflow + evaluation
  
(Frontend shows semantic workflow + ❓ PendingNodes + evaluation feedback)

User confirms / adjusts workflow + optional selections
  ↓
/api/v1/agents/yaml
  ├─ YAML Coder loads selected node specs (Level 3)
  ├─ LLM synthesizes MF YAML (concrete)
  ├─ Evaluator validates via Phase 1 validator + checks intent
  └─ Returns: mf_yaml + validation_report + evaluation
  
(Frontend shows MF YAML + validation errors if any)

User submits workflow
  ↓
/api/v1/workflows/submit
  └─ API compiles MF YAML → Argo YAML + triggers ephemeral node generation
```

### Generator-Evaluator Loop Pattern

**All three agents use the same pattern**:

```
Iteration 0:
  generate() → produces output (YAML, nodespec, workflow)
  evaluate() → checks validity
    ├─ passed=True → END
    └─ passed=False + iteration < 3 → next iteration

Iteration 1+:
  generate() [reads evaluation.issues, attempts to fix]
  evaluate()
    ├─ passed=True → END
    └─ passed=False + iteration < 3 → next iteration

After max_iterations or pass:
  Return result (may still have issues if max iterations reached)
```

---

## Key Design Principles

### 1. Semantic vs. Concrete Separation

- **Planner** operates at **semantic level** (no software names, port names, etc.)
- **YAML Coder** handles **concrete translation** (port matching, onboard params)
- **Node Generator** works at **implementation level** (nodespec structure, run.sh logic)

This layering prevents Planner from needing to know every node's internal details.

### 2. RAG-Based Node Discovery

Agents **never import** `nodes/` internals directly. All node information flows through:
- `vectorstore.retriever` — Decoupled from node implementation
- Agents see nodes as JSON structures, not Python objects

This allows node library evolution without breaking agent code.

### 3. Generative + Evaluative

Every agent has a **dual-phase** workflow:
1. **Generate** — LLM produces candidate output
2. **Evaluate** — Validator checks correctness (programmatic + LLM critique)

Iterative refinement ensures quality while keeping generation temperature low (0.0) for evaluators.

### 4. Independent, Callable Agents

No "Main Agent" orchestration (Phase 3 feature). Phase 2 agents are independently callable:
- Frontend or backend directly invokes one or more agents
- No hidden dependencies between agent invocations
- Planner output is independent; YAML Coder input can use any SemanticWorkflow

### 5. Tool Integration

LangChain tools provide clean interfaces to:
- Node retrieval (no direct node library access)
- Workflow validation (Phase 1 validator)
- Workspace file access (user-uploaded inputs)
- Semantic type queries

---

## File Structure Summary

| File | Purpose |
|------|---------|
| `agents/__init__.py` | Package marker |
| `agents/schemas.py` | SemanticWorkflow, ConcretizationResult, NodeGenRequest/Result, EvaluationResult |
| `agents/llm_config.py` | LLM provider config (models.yaml parsing) |
| `agents/common/prompt_loader.py` | Jinja2 rendering |
| `agents/common/eval_loop.py` | Generator-Evaluator loop factory |
| `agents/tools/*.py` | LangChain tools (node_search, validate, workspace, etc.) |
| `agents/planner/*.py` | Planner state, generator, evaluator, graph, prompts |
| `agents/yaml_coder/*.py` | YAML Coder state, generator, evaluator, graph, prompts |
| `agents/node_generator/*.py` | Node Generator state, generator, evaluator, graph, knowledge, prompts |
| `api/models/agents.py` | Pydantic request/response models for API |
| `api/routers/agents.py` | FastAPI endpoints (/agents/plan, /agents/yaml, /agents/node) |
| `vectorstore/*.py` | RAG indexing + retrieval |

---

## Prompt Template Structure

### System Prompts
Define the **agent role**, **output format**, **available resources** (semantic types, nodes, images).

**Example (Planner)**:
```
You are MiQroForge Planner...
Your role: decompose user goals into semantic steps
Available semantic types: [list]
Output: ONLY JSON SemanticWorkflow
Rules: use semantic_type from registry, edges define data flow, etc.
```

### Generation Prompts
Provide **task context** and **recent state**.

**Example (Planner)**:
```
User Request: [intent]
Target Molecule: [molecule]
Workspace Files: [list]
Available Implementations: [nodes by semantic type]
Task: Design SemanticWorkflow
```

### Evaluation Prompts
Instruct **checker** on what to validate and how to score.

**Example (Planner Evaluator)**:
```
Original Intent: [intent]
Proposed Workflow: [JSON]
Checklist:
  1. Completeness: achieves stated goal?
  2. DAG validity: no cycles?
  3. Scientific correctness: geo-opt before freq?
Output: JSON {passed, issues, suggestions}
```

---

## Ephemeral Node Architecture (M2)

### Overview

Ephemeral nodes use a **two-phase architecture** distinct from the formal Generator-Evaluator pattern:

1. **Compile time**: Compiler generates a thin wrapper script (not the actual Python script)
2. **Run time**: Wrapper calls `POST /api/v1/agents/ephemeral`, server completes the full generation cycle

### ReAct Agent Inner Loop

Unlike formal mode (simple generate → evaluate), ephemeral mode uses a **ReAct-style Agent loop**:

```
SystemMessage + HumanMessage (task + context + input data)
  ↓
LLM (bound with sandbox_execute + pip_install tools)
  ↓ calls sandbox_execute
Tool Result (stdout + stderr + return_code + image_files)
  ↓ LLM reads result, decides to fix or finish
[Repeat until LLM stops calling tools or max rounds reached]
  ↓
Extract final script from conversation history
```

**Key differences from formal mode:**
- LLM has **agency**: it decides when to execute, what to fix, when to stop
- Tools: `sandbox_execute` (execute Python in sandbox) + `pip_install` (install packages)
- Self-correction: LLM reads stderr and rewrites script on failure
- Vision feedback: evaluation results feed back into next generation round

### Sandbox Execution (`sandbox.py`)

Two execution modes, auto-selected:
- **Docker** (preferred): Runs in `ephemeral-py:3.11` container (pre-installed: numpy, matplotlib, scipy, pandas, etc.)
- **Subprocess** (fallback): Runs on host Python when Docker unavailable

**Path handling**:
- Priority: create symlinks `/mf/input → tmpdir/input` (matches Pod environment)
- Fallback: rewrite script paths to use temp directory

**Output scanning**: Automatically detects generated files and image files (PNG, JPG, SVG, PDF, etc.)

### Visual Evaluation (`evaluator.py`)

For ephemeral nodes that produce images:
1. Programmatic checks (Python syntax, I/O path conventions, sweep type conversion)
2. Execution result check (return code)
3. **Multimodal vision evaluation**: images sent to GPT-4o for visual quality check

Vision evaluation uses `nodegen_ephemeral_evaluate_vision.jinja2` prompt and sends up to 4 images per evaluation.

### API Endpoint Flow

`POST /api/v1/agents/ephemeral` runs the complete outer loop:

```
for outer_round in range(max_outer_rounds):
    1. Generate (inner ReAct Agent loop with sandbox)
    2. If execution failed → continue to next round with stderr
    3. If execution succeeded → evaluate (programmatic + vision)
    4. If evaluation passed → break
    5. If evaluation failed → continue with vision_feedback
```

Configuration in `userdata/settings.yaml`:
```yaml
ephemeral:
  max_outer_rounds: 2    # outer generate→evaluate loop
  max_inner_rounds: 3    # inner ReAct sandbox executions
```

---

## Extension Points (Phase 2 → Phase 3)

1. **Main Agent** — Will coordinate multiple agents using same LangGraph patterns
2. **Memory Store** — Persist agent reasoning and project decisions across sessions
3. **Debug Agent** — Automatically fix failed workflows (capture Argo failures via Events)
4. **Review Agent** — Critique workflows before submission (add Argo Suspend/Resume)

All future agents will follow the same structure: state, generator, evaluator, graph, prompts.

---

## Troubleshooting & Testing

### Common Issues

1. **"models.yaml not found"** → Create `userdata/models.yaml` from example
2. **"ChromaDB indexing failed"** → Fallback to keyword search, check network
3. **"Node not found in retriever"** → Reindex: `python -m vectorstore.indexer`
4. **Planner generates invalid steps** → Check semantic_registry.yaml is present
5. **YAML Coder fails on ports** → Verify node port types match (category field)

### Testing Agents Independently

```python
# Planner
from agents.planner.graph import run_planner
result = run_planner("Calculate H2O thermo", molecule="H2O")

# YAML Coder
from agents.yaml_coder.graph import run_yaml_coder
result = run_yaml_coder(result["semantic_workflow"])

# Node Generator
from agents.node_generator.graph import run_node_generator
from agents.schemas import NodeGenRequest
req = NodeGenRequest(
    semantic_type="geometry-optimization",
    description="ORCA DFT geometry optimization",
    target_software="ORCA",
    category="chemistry"
)
result = run_node_generator(req)
```

---

## Conclusion

The MiQroForge 2.0 agents layer provides:

✅ **Three independent, intelligent agents** for workflow design (Planner → YAML Coder → Generator)
✅ **Generator-Evaluator loops** for iterative refinement with maximum 3 iterations
✅ **Modular design** with clear separation of semantic vs. concrete concerns
✅ **RAG integration** for intelligent node discovery without coupling to node implementations
✅ **FastAPI endpoints** for frontend/backend integration
✅ **Tool-based architecture** enabling extensibility for Phase 3+

The design emphasizes **AI-assisted but human-controlled** workflows: agents propose, humans review, agents refine.

