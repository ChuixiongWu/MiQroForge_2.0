# MiQroForge Agents Layer — Detailed Technical Reference

## Prompt System Architecture

### Template Rendering Pipeline

All agent prompts use Jinja2 templates stored in `agents/<agent>/prompts/`.

**Rendering Flow**:
```
Template file (.jinja2)
    ↓
load_prompt("planner/prompts/plan_system.jinja2", **variables)
    ↓
Jinja2 environment (StrictUndefined, trim_blocks=True, lstrip_blocks=True)
    ↓
Rendered string → LangChain Message → LLM
```

**Key Settings**:
- `StrictUndefined` — Raises error if template references undefined variables
- `trim_blocks=True` — Removes block tags (e.g., `{% if %}`) from output
- `lstrip_blocks=True` — Removes leading whitespace from indented block lines

**Example Template** (simplified):
```jinja2
You are {{ agent_role }}.

Available semantic types:
{% for type_key, type_info in semantic_types.items() %}
- {{ type_key }}: {{ type_info.display_name }}
{% endfor %}

Rules:
1. Output ONLY JSON
2. Use semantic_type values from above
```

---

### Three-Message Pattern

Each agent uses a consistent **three-message** conversation structure:

```python
messages = [
    SystemMessage(content=system_content),      # Role + format + resources
    HumanMessage(content=user_content),         # Task context + recent state
    # Optional refine message on iteration > 0
]

response = llm.invoke(messages)
```

#### System Message

**Contains**:
- Agent role and expertise
- Output format specification (JSON? YAML? plain text?)
- Available resources (semantic types, nodes, images)
- Rules and constraints
- Example outputs

**Example (Planner)**:
```
You are MiQroForge Planner...
Available semantic types:
- geometry-optimization: Compute optimized molecular geometry
- frequency-analysis: Calculate vibrational frequencies
...

Key Rules:
1. Output ONLY a JSON SemanticWorkflow
2. Use ONLY semantic_type values from the list above
...

Output Format (JSON only):
{
  "name": "workflow-name",
  "steps": [...],
  "edges": [...]
}
```

#### User Message (Generation)

**Contains**:
- Task specification ("design workflow for user intent X")
- Immediate context (intent, molecule, preferences, workspace files)
- Candidate options (RAG-retrieved nodes, available implementations)
- Previous iteration data (if refining)

**Example (Planner)**:
```
User Request:
Intent: Calculate thermodynamic properties of H₂O
Target Molecule: H₂O
Workspace Files:
- h2o.xyz (45 bytes)

Semantic Types with Available Implementations:
- geometry-optimization — implementation(s) available
- frequency-analysis — implementation(s) available

Task: Design a semantic workflow...
```

#### Optional Refine Message (Iteration > 0)

**Appended to user message** if evaluation failed:
```
## Previous Attempt (failed evaluation):
```json
{...previous output...}
```

## Issues to Fix:
- Issue 1: ...
- Issue 2: ...

## Suggestions:
- Suggestion 1: ...

Please output a corrected ...
```

---

## Agent State Management

### State TypedDict Pattern

Each agent defines a `State` class (TypedDict) that tracks:

```python
class PlannerState(TypedDict, total=False):
    # Inputs
    intent: str
    molecule: str
    
    # Intermediate (computed once, reused in iterations)
    node_summaries: list[dict]
    semantic_types: dict[str, Any]
    
    # Main output
    semantic_workflow: Optional[SemanticWorkflow]
    workflow_json: str
    
    # Generator-Evaluator tracking
    evaluation: Optional[EvaluationResult]
    iteration: int
    
    # Error tracking
    error: Optional[str]
```

**Key Pattern**:
- `total=False` — All fields optional (TypedDict convention for state)
- **Immutable inputs** — `intent`, `molecule` never change
- **Computed once** — `node_summaries`, `semantic_types` cached to avoid re-computation
- **Mutable outputs** — `semantic_workflow`, `evaluation` updated per iteration
- **Iteration tracking** — `iteration` increments after each evaluate node

### LangGraph Node Functions

Each LangGraph node is a pure function: `(state: Dict) -> Dict`

```python
def generate_plan(state: PlannerState) -> dict[str, Any]:
    """LangGraph node — returns updates to state."""
    intent = state.get("intent", "")
    
    # ... compute ...
    
    return {
        "semantic_workflow": workflow,
        "workflow_json": json.dumps(...),
        "error": None,
    }
```

**Merge Behavior**:
- Return dict keys **merge** into state (not replace)
- Unmentioned keys remain unchanged
- Allows nodes to focus on their responsibilities

### Generator-Evaluator Iteration Loop

All agents share identical iteration logic via `agents/common/eval_loop.py`:

```python
def _route(state: dict) -> str:
    evaluation = state.get("evaluation")
    iteration = state.get("iteration", 0)
    
    if evaluation and evaluation.passed:
        return "end"
    if iteration >= max_iterations:  # Usually 3
        return "end"  # Stop even if not passed
    return "refine"

graph = StateGraph(state_type)
graph.add_edge("generate", "evaluate")
graph.add_conditional_edges("evaluate", _route, {"end": END, "refine": "increment"})
graph.add_edge("increment", "generate")  # Loop back
```

**Key Decisions**:
- Max iterations = 3 (hardcoded per agent)
- **Always returns result** — Even if max iterations exceeded (no "failed" end state)
- **Agent responsible for using feedback** — generate_fn reads `evaluation.issues` and adapts

---

## Tool Chain Architecture

### Tool Availability

All agents have access to the same **LangChain tools**:

```python
from agents.tools import (
    search_nodes_summary,              # RAG text search
    search_nodes_by_semantic_type,     # Exact type match
    get_node_details,                  # Load complete NodeSpec
    load_nodespec_by_name,             # Single node by name
    query_semantic_registry,           # List semantic types
    validate_mf_yaml,                  # Phase 1 validator
    workspace_list_files,              # List workspace files
    workspace_read_file,               # Read file content
)
```

### Tool Not Used in Current Phase 2

**Why**?
- Agents have **direct implementation control** (no tool calling overhead)
- Planner generator directly calls `search_nodes_for_intent()` in Python
- YAML Coder directly calls `_load_node_details()` in Python
- Tools are available **but not invoked** via LangChain agent pattern

**Future use** (Phase 3):
- Main Agent may use tools via `ReAct` pattern or `ToolExecutor`
- Debug Agent may use tools to diagnose failures
- Review Agent may use validation tools

---

## LLM Configuration & Model Selection

### Runtime Model Resolution

When agent calls `LLMConfig.get_chat_model(purpose="planner")`:

```python
def _resolve_model_config(purpose: str) -> dict:
    registry = _load_registry()  # Load userdata/models.yaml
    
    # 1. Try purpose-specific assignment
    model_name = registry.get("agents", {}).get("planner")
    
    # 2. Fallback to default
    if not model_name:
        model_name = registry.get("default_model")
    
    # 3. Fallback to first available
    if not model_name:
        model_name = next(iter(registry.get("models", {})))
    
    # 4. Get full config
    model_cfg = registry["models"][model_name]
    
    # 5. Get base_url and api_key (model overrides proxy)
    base_url = model_cfg.get("base_url") or registry.get("proxy", {}).get("base_url")
    api_key = model_cfg.get("api_key") or registry.get("proxy", {}).get("api_key")
    
    return {
        "model_name": model_name,
        "model_id": model_cfg.get("model_id", model_name),
        "base_url": base_url,
        "api_key": api_key,
    }
```

### Support for Local/Proxy Models

Example configuration for local LLM server:

```yaml
proxy:
  base_url: "http://localhost:8000/v1"  # Local Ollama server
  api_key: "not-needed"

agents:
  planner: local-llama2
  evaluator: local-llama2

default_model: local-llama2

models:
  local-llama2:
    model_id: llama2
    base_url: "http://localhost:8000/v1"
    api_key: ""
```

### Caching & Reload

```python
@lru_cache(maxsize=1)
def _load_registry() -> dict:
    # Cached to avoid re-parsing YAML on every call
    ...

class LLMConfig:
    @staticmethod
    def reload():
        _load_registry.cache_clear()
```

**Use case**: Hot-reload config without restarting API server

---

## Node Index Integration

### Three-Level Information Hierarchy

Agent tools use a **three-level** information disclosure pattern:

**Level 1 — Summary** (Planner search):
```python
search_nodes_summary("geometry optimization", n=8)
→ [
    {
        "name": "orca-geo-opt",
        "display_name": "ORCA Geometry Optimization",
        "description": "Optimize molecular geometry...",
        "semantic_type": "geometry-optimization",
        "software": "ORCA",
        "stream_inputs": [...],
        "stream_outputs": [...]
    },
    ...
]
```

**Level 2 — Semantic Type Match** (Node Generator reference lookup):
```python
search_nodes_by_semantic_type("geometry-optimization")
→ [same as Level 1]
```

**Level 3 — Full Spec** (YAML Coder node selection):
```python
get_node_details(["orca-geo-opt", "orca-freq"])
→ [
    {
        "metadata": {...},
        "stream_inputs": [...],
        "stream_outputs": [...],
        "onboard_inputs": [...],
        "onboard_outputs": [...],
        "execution": {...},
        "resources": {...}
    },
    ...
]
```

### Retriever Backend Selection

`NodeRetriever` auto-selects backend based on `.index_type` file:

```python
def _ensure_connected(self):
    index_type_file = persist_dir / ".index_type"
    
    if not index_type_file.exists():
        # Auto-build if missing
        from vectorstore.indexer import build_index
        build_index()
    
    index_type = index_type_file.read_text().strip()
    
    if index_type == "chromadb":
        try:
            self._backend = ChromaRetriever(...)
            return
        except Exception:
            pass
    
    # Fallback to keyword search
    self._backend = KeywordRetriever(...)
```

---

## Error Handling & Failure Modes

### Generator Failures

If LLM generation fails (e.g., API error, timeout):

```python
def generate_plan(state: PlannerState) -> dict:
    try:
        response = llm.invoke(messages)
        # ... parse and return
    except Exception as e:
        return {
            "semantic_workflow": None,
            "workflow_json": "",
            "error": f"Planner generation failed: {e}",
        }
```

**Result**: Error is captured in state; next iteration still runs but has no input.

### Evaluator Failures

If evaluator crashes (unlikely but possible):

```python
def evaluate_plan(state: PlannerState) -> dict:
    try:
        response = llm.invoke([HumanMessage(...)])
        # ... parse result
    except Exception as e:
        # Fail-open: treat as passed to avoid infinite loops
        result = EvaluationResult(
            passed=True,
            issues=[],
            suggestions=[f"Evaluator failed (auto-pass): {e}"],
            iteration=iteration,
        )
```

**Philosophy**: Auto-pass on evaluator crash prevents agent deadlock.

### Validation Failures (YAML Coder)

Phase 1 validator may reject YAML (incomplete params, port mismatch):

```python
def _run_programmatic_validation(yaml_content: str):
    try:
        workflow = load_workflow(tmp_path)
        result = validate_workflow(workflow)  # May have errors
        return {
            "valid": result.valid,
            "errors": [e.message for e in result.errors],
        }
    except Exception as e:
        return {"valid": False, "errors": [str(e)]}
```

**Result**: Validator errors are **always** included in `EvaluationResult.issues`.

---

## Planner Agent — Detailed Implementation

### Node Candidate Mapping

After LLM generates SemanticWorkflow, Planner maps steps → candidate nodes:

```python
def _build_implementations(
    steps: list[SemanticStep],
    node_summaries: list[dict[str, Any]],
) -> dict[str, list[str]]:
    """For each step, find all candidate nodes by semantic_type."""
    implementations: dict[str, list[str]] = {}
    for step in steps:
        candidates = [
            n["name"]
            for n in node_summaries
            if n.get("semantic_type") == step.semantic_type
        ]
        implementations[step.id] = candidates  # May be empty!
    return implementations
```

**Result**: `SemanticWorkflow.available_implementations` = `{"step-1": ["orca-geo-opt", ...], ...}`

If no candidates exist for a step, the list is empty (YAML Coder will flag as `needs_new_node`).

### Workspace Integration

Planner loads user-uploaded workspace files (project-scoped) and includes filenames in prompt:

```python
settings = get_settings()
# 项目级文件目录：userdata/workspace/.files/{project_id}/
if project_id:
    workspace_dir = settings.userdata_root / "workspace" / ".files" / project_id
else:
    workspace_dir = settings.userdata_root / "workspace"
workspace_files = []
if workspace_dir.exists():
    for f in sorted(workspace_dir.iterdir()):
        if f.is_file() and f.name != ".gitkeep":
            workspace_files.append({
                "name": f.name,
                "size_bytes": f.stat().st_size
            })

user_content = load_prompt(
    "planner/prompts/plan_generate.jinja2",
    workspace_files=workspace_files,
    ...
)
```

**Use Case**: If user uploaded `h2o.xyz`, Planner can include hint in constraints:
```
constraints: {"geometry_file": "h2o.xyz"}
```

YAML Coder later includes this filename in `onboard_params`.

> **Note**: Since workspace is now project-scoped via `subPath`, the Planner reads from
> `workspace/.files/{project_id}/` when a project context is active. This ensures each project
> only sees its own files.

---

## YAML Coder Agent — Detailed Implementation

### Resolution Building

YAML Coder maps each semantic step → concrete node:

```python
def _build_resolutions(
    semantic_workflow,
    selected_implementations: dict[str, str],  # User manual selection
    available_nodes: list[dict[str, Any]],
) -> list[NodeResolution]:
    """Build step → node mappings."""
    node_by_name = {n["metadata"]["name"]: n for n in available_nodes}
    
    resolutions = []
    for step in semantic_workflow.steps:
        # User selection > RAG candidates > None
        selected_name = selected_implementations.get(step.id)
        if not selected_name:
            candidates = semantic_workflow.available_implementations.get(step.id, [])
            selected_name = candidates[0] if candidates else None  # Pick first
        
        resolution = NodeResolution(
            step_id=step.id,
            resolved_node=selected_name,
            onboard_params=dict(step.constraints),  # From Planner constraints
            needs_new_node=(selected_name is None),
        )
        resolutions.append(resolution)
    return resolutions
```

**Key Decisions**:
- User selection overrides RAG (supports manual curation)
- Takes first RAG candidate (no scoring logic)
- `constraints` from Planner become `onboard_params`

### Port Compatibility Rules

Critical for YAML generation — system prompt includes:

```jinja2
## CRITICAL — Port Type Compatibility:
You may ONLY connect two ports if their `category` matches.
- `physical_quantity` ↔ `physical_quantity` only
- `software_data_package` ↔ `software_data_package` only
- `logic_value` ↔ `logic_value` only
- `report_object` ↔ `report_object` only

Example WRONG:
  geometry_port (physical_quantity) → gbw_port (software_data_package)  ✗

Example CORRECT:
  optimized_geometry (physical_quantity) → xyz_geometry (physical_quantity)  ✓
```

LLM must respect this when generating `connections` in MF YAML.

---

## Node Generator Agent — Detailed Implementation

### Output Section Parsing

LLM output is marked with separators; parser extracts each section:

```python
def _parse_generated_output(text: str) -> dict[str, str]:
    sections = {}
    markers = {
        "nodespec_yaml": "=== NODESPEC_YAML ===",
        "run_sh": "=== RUN_SH ===",
        "input_template": "=== INPUT_TEMPLATE ===",
    }
    
    current_section = None
    current_lines = []
    
    for line in text.splitlines():
        found_marker = False
        for key, marker in markers.items():
            if marker in line:
                # Save previous section
                if current_section:
                    sections[current_section] = "\n".join(current_lines).strip()
                current_section = key
                current_lines = []
                found_marker = True
                break
        
        if not found_marker and current_section:
            current_lines.append(line)
    
    # Save last section
    if current_section:
        sections[current_section] = "\n".join(current_lines).strip()
    
    # Strip markdown code block markers
    for key in list(sections.keys()):
        val = sections[key]
        if val.startswith("```"):
            lines = val.splitlines()[1:]  # Remove first ```
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]  # Remove last ```
            sections[key] = "\n".join(lines).strip()
    
    return sections
```

**Robustness**: Handles markdown code blocks, missing sections, extra whitespace.

### Knowledge Loading for Few-Shot

Node Generator loads similar nodes as examples:

```python
def load_reference_nodes(
    target_software: str | None,
    semantic_type: str | None,
    max_refs: int = 2,
) -> list[dict[str, Any]]:
    """Load same-software/same-semantic-type nodes for few-shot."""
    try:
        index = load_index(project_root)
    except Exception:
        return []
    
    candidates = []
    for entry in index.entries:
        # Filter by software if specified
        if target_software and entry.software.lower() != target_software.lower():
            continue
        candidates.append(entry)
    
    # Prioritize same semantic type
    if semantic_type:
        same_semantic = [c for c in candidates if c.semantic_type == semantic_type]
        others = [c for c in candidates if c.semantic_type != semantic_type]
        candidates = same_semantic + others
    
    # Load nodespec.yaml + run.sh for each reference
    references = []
    for entry in candidates[:max_refs]:
        node_data = {"name": entry.name}
        
        spec_path = project_root / entry.nodespec_path
        if spec_path.exists():
            node_data["nodespec_yaml"] = spec_path.read_text()
        
        run_sh_path = spec_path.parent / "profile" / "run.sh"
        if run_sh_path.exists():
            node_data["run_sh"] = run_sh_path.read_text()
        
        references.append(node_data)
    
    return references
```

**Result**: Prompt includes 1-2 real working nodes as examples → LLM has concrete patterns to follow.

### Node Persistence

After evaluation passes, save to `userdata/nodes/`:

```python
def _save_to_userdata(state: NodeGenState) -> dict:
    nodespec_yaml = state.get("nodespec_yaml")
    run_sh = state.get("run_sh")
    input_templates = state.get("input_templates")
    request = state.get("request")
    
    # Extract node name from YAML
    spec_data = yaml.safe_load(nodespec_yaml)
    node_name = spec_data["metadata"]["name"]  # e.g., "my-orca-node"
    
    # Create directory: userdata/nodes/<category>/<node-name>/
    node_dir = userdata_root / "nodes" / request.category / node_name
    node_dir.mkdir(parents=True, exist_ok=True)
    
    # Write nodespec.yaml
    (node_dir / "nodespec.yaml").write_text(nodespec_yaml)
    
    # Write run.sh to profile/
    if run_sh:
        profile_dir = node_dir / "profile"
        profile_dir.mkdir(exist_ok=True)
        (profile_dir / "run.sh").write_text(run_sh)
        (profile_dir / "run.sh").chmod(0o755)  # Make executable
        
        # Write input templates
        for tpl_name, tpl_content in input_templates.items():
            (profile_dir / tpl_name).write_text(tpl_content)
    
    # Trigger reindex
    from vectorstore.indexer import build_index
    build_index()
    
    # Return result
    return {
        "result": NodeGenResult(
            node_name=node_name,
            nodespec_yaml=nodespec_yaml,
            run_sh=run_sh,
            input_templates=input_templates,
            saved_path=str(node_dir.relative_to(project_root)),
            evaluation=state.get("evaluation"),
        )
    }
```

---

## API Integration

### Request/Response Flow

```
POST /api/v1/agents/plan
  Request: PlanRequest(intent, molecule, preferences)
  ↓
  [asyncio.to_thread → run_planner(...)]
  ↓
  PlanResponse(semantic_workflow, evaluation, available_nodes)
  
JSON serialization:
  - SemanticWorkflow → Pydantic .model_dump(mode="json")
  - EvaluationResult → same
```

### Async Execution

Agents run CPU-bound synchronous code in thread pool:

```python
@router.post("/plan")
async def plan_workflow(request: PlanRequest):
    state = await asyncio.to_thread(
        run_planner,
        intent=request.intent,
        molecule=request.molecule,
        preferences=request.preferences,
    )
    
    return PlanResponse(
        semantic_workflow=state.get("semantic_workflow"),
        evaluation=state.get("evaluation"),
        available_nodes=state["semantic_workflow"].available_implementations,
    )
```

---

## Ephemeral Agent Technical Details (M2)

### ReAct Agent Inner Loop (`node_generator/generator.py::_generate_ephemeral_agent`)

The ephemeral mode uses a fundamentally different architecture from the formal Generator-Evaluator pattern. Instead of generate → evaluate → refine, it runs a **ReAct (Reasoning + Acting) loop**:

```python
llm_with_tools = llm.bind_tools([sandbox_execute, pip_install])
messages = [SystemMessage(...), HumanMessage(...)]

for _ in range(max_tool_calls):
    response = llm_with_tools.invoke(messages)

    if not response.tool_calls:
        # LLM decided it's done — extract final script
        break

    messages.append(response)

    for tool_call in response.tool_calls:
        if tool_call.name == "sandbox_execute":
            result = sandbox_tool.invoke(tool_call.args)
            # Capture stdout, stderr, return_code, image_files
        elif tool_call.name == "pip_install":
            result = pip_tool.invoke(tool_call.args)

        messages.append(ToolMessage(content=result, tool_call_id=...))
```

**Key parameters** (from `userdata/settings.yaml`):
- `max_inner_rounds` (default 3): max sandbox_execute calls per generation
- `max_tool_calls` = `max_inner_rounds * 2` (includes pip_install calls)

### Sandbox Execution (`node_generator/sandbox.py`)

#### Mode Selection
```python
def _resolve_sandbox_mode() -> str:
    # auto → docker if available, else subprocess
    # Can override via MF_SANDBOX_MODE env var
```

#### Docker Mode (preferred)
- Image: `ephemeral-py:3.11` (pre-installed: numpy, matplotlib, scipy, pandas, pyyaml, jinja2, requests)
- Mounts: `-v {sandbox_dir}:/sandbox`
- Environment: `MF_INPUT_DIR`, `MF_OUTPUT_DIR`, `MF_WORKSPACE_DIR` + custom overrides
- Timeout: 60 seconds per execution

#### Subprocess Mode (fallback)
- Runs on host Python (`sys.executable`)
- Path handling: symlink `/mf/input → tmpdir/input` (if permissions allow)
- Fallback: rewrite `/mf/` paths in script to temp directory paths

#### Tool Factories
```python
# sandbox_execute: bound to specific input_data and sandbox_dir
sandbox_tool = make_sandbox_tool(input_data, env_overrides, sandbox_dir)

# pip_install: tracks installation history
pip_tool, pip_history = make_pip_install_tool()
```

### Visual Evaluation (`node_generator/evaluator.py::evaluate_node_vision`)

For ephemeral nodes that generate images:

1. Load images as base64 from file paths
2. Build multimodal message: text prompt + up to 4 images
3. Send to GPT-4o (or configured vision model) via `purpose="evaluator_vision"`
4. Parse structured JSON response: `{passed, issues, suggestions}`

**Fail-open design**: If visual evaluation fails (API error, parsing error), the node passes automatically with a warning. This prevents deadlocks in the generation loop.

### API-Level Outer Loop (`api/routers/agents.py::ephemeral_generate`)

The API endpoint manages the outer generate → evaluate → retry loop:

```python
for outer_round in range(max_outer_rounds):
    # Generate (inner ReAct loop + sandbox execution)
    state = run_node_generator(gen_request, ...)

    if exec_return_code != 0:
        continue  # Retry with stderr feedback

    # Evaluate (programmatic + visual)
    eval_result = evaluate_node(eval_state)

    if evaluation.passed:
        break  # Success

    # Feed vision_feedback into next round
    vision_feedback = evaluation.issues + evaluation.suggestions
```

**Log persistence**: Each round generates separate log files in the project's runs directory:
- `{agent_type}_gen_r{round}_{time}.json` — Generation log
- `ephemeral_eval_r{round}_{time}.json` — Evaluation log

---

## Conclusion

The agents layer is built on:

1. **Clean separation** — Semantic (Planner) → Concrete (YAML Coder) → Implementation (Node Generator)
2. **Iterative refinement** — Generator-Evaluator loops with max 3 iterations (formal mode)
3. **ReAct Agent loop** — Ephemeral mode uses tool-calling Agent with sandbox + pip tools
4. **Decoupled retrieval** — RAG vectorstore hides node internals
5. **Flexible configuration** — LLM provider resolution from YAML
6. **Visual evaluation** — Multimodal quality check for ephemeral node outputs
7. **Tool-ready** — Tools available for Phase 3 agent patterns

This foundation supports Phase 3's Main Agent, Debug Agent, Review Agent without restructuring.

