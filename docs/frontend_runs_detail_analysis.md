# Frontend Runs Detail View — Comprehensive Code Analysis

## Executive Summary

The MiQroForge frontend provides a **RunsPanel** component that displays:
1. A **list view** of all submitted workflow runs
2. A **detail view** for selected runs showing:
   - Workflow metadata (name, phase/status badge, status message)
   - **Steps section** listing all executed Pod nodes and Skipped nodes
   - Validation warnings/infos
   - Workflow logs

**Current limitations:**
- Steps are displayed as a **flat list** with no grouping or summarization
- **Fan-out/parallel nodes** (created via `withParam` in Argo) are shown individually, one per array item
- No collapsible groups, hierarchical structure, or step count aggregation
- Scrolling is handled via standard `overflow-y-auto` on the detail panel
- No special rendering for parallel patterns

---

## Component Hierarchy

```
App.tsx
└── CanvasLayout
    └── RunsPanel (components/runs/RunsPanel.tsx)
        ├── RunList (sub-component)
        │   └── Renders list of RunSummaryResponse[]
        │
        └── [Selected Run Detail]
            ├── RunDetailHeader (restore canvas button)
            ├── RunDetailContent (conditional)
            │   ├── LocalOnlyRunDetail (if local-only snapshot)
            │   │   └── Error display + ValidationSummary
            │   │
            │   └── ArgoRunDetail (if Argo-submitted)
            │       ├── Metadata (name, phase badge)
            │       ├── StatusMessage (optional)
            │       ├── StepsSection (THIS IS THE KEY AREA)
            │       │   └── Flat list of steps from parseSteps()
            │       ├── ValidationSummary
            │       └── RunLogs
            │
            └── [Integration: Run Overlay Store]
                └── Updates canvas node badges with status in real-time
```

### File Structure

```
frontend/src/
├── components/runs/
│   └── RunsPanel.tsx                    ← MAIN COMPONENT (399 lines)
│
├── stores/
│   ├── run-overlay-store.ts             ← Zustand store for run status overlay
│   │   ├── parseArgoNodes()             ← Parses Argo JSON to canvas node statuses
│   │   └── NodeRunStatus interface      ← { phase, startedAt, finishedAt, outputs }
│   │
│   ├── ui-store.ts                      ← UI state (rightPanel, selectedNodeId, etc.)
│   └── saved-workflows-store.ts         ← Local run snapshots + validation issues
│
├── types/index-types.ts                 ← Type definitions
│   ├── RunPhase type                    ← "Pending" | "Running" | "Succeeded" | "Failed" | etc.
│   ├── RunSummaryResponse               ← List items
│   ├── RunDetailResponse                ← { name, namespace, phase, raw: argo_json }
│   └── RunLogsResponse                  ← Logs
│
├── api/argo-api.ts                      ← API client
│   ├── listRuns()                       ← GET /api/v1/runs → RunListResponse
│   ├── getRun(name)                     ← GET /api/v1/runs/{name} → RunDetailResponse
│   └── getLogs(name)                    ← GET /api/v1/runs/{name}/logs → RunLogsResponse
│
├── lib/phase-utils.ts                   ← Phase badge styling + duration formatting
│   ├── phaseBadgeClass(phase)
│   ├── formatDurationSeconds(secs)
│   └── PHASE_CONFIG map                 ← Emoji, colors, animation for each phase
│
└── hooks/
    └── useRunOverlayPolling()            ← Polls run details every 5 sec while run active
```

---

## Data Flow: How Steps Are Rendered

### Step 1: Fetch Run Detail (Backend)
**File:** `api/routers/runs.py` → `get_run(name)`

```python
@router.get("/{name}", response_model=RunDetailResponse)
def get_run(name: str, argo: ArgoService) -> RunDetailResponse:
    wf = argo.get_workflow(name)          # Call: argo get {name} -o json
    meta = wf.get("metadata", {})
    status = wf.get("status", {})
    
    return RunDetailResponse(
        name=meta.get("name", name),
        namespace=meta.get("namespace", ""),
        phase=status.get("phase", "Unknown"),
        raw=wf,                            # ← Complete Argo workflow object
    )
```

### Step 2: Parse Steps in Frontend
**File:** `components/runs/RunsPanel.tsx` → `parseSteps(detail: RunDetailResponse)`

```typescript
interface ArgoStepNode {
  id: string                 // Argo node ID (from status.nodes key)
  name: string              // displayName ?? templateName ?? id
  phase: RunPhase            // Pod phase: Running | Succeeded | Failed | etc.
}

function parseSteps(detail: RunDetailResponse): ArgoStepNode[] {
  const status = (detail.raw.status ?? {}) as Record<string, unknown>
  const nodes = (status.nodes ?? {}) as Record<string, Record<string, unknown>>
  
  // Filter to Pod and Skipped nodes only
  return Object.entries(nodes)
    .filter(([, n]) => n.type === 'Pod' || n.type === 'Skipped')
    .map(([id, n]) => ({
      id,
      name: (n.displayName ?? n.templateName ?? id) as string,
      phase: ((n.phase as RunPhase | undefined) ?? 'Unknown'),
    }))
}
```

### Step 3: Render Steps Section
**File:** `components/runs/RunsPanel.tsx` → Lines 366-382

```tsx
{(() => {
  const steps = parseSteps(detailQuery.data)
  if (steps.length === 0) return null
  return (
    <div>
      <div className="text-[10px] text-mf-text-muted mb-1 uppercase tracking-wide">Steps</div>
      <div className="space-y-1">
        {steps.map((n) => (
          <div key={n.id} className="flex items-center justify-between text-xs">
            <span className="text-mf-text-secondary font-mono text-[11px] truncate">
              {n.name}
            </span>
            <PhaseBadge phase={n.phase} />
          </div>
        ))}
      </div>
    </div>
  )
})()}
```

**Rendering:**
- Each step is a **single-line row**
- Left: Step name (truncated if too long)
- Right: Phase badge (color-coded)
- No grouping, no aggregation

---

## How Parallel/Fan-Out Nodes Are Currently Displayed

### Argo Parallel Pattern Example
When a task uses `withParam`, Argo creates **separate Pod nodes for each array item**:

**Argo Workflow YAML (simplified):**
```yaml
templates:
  - dag:
      tasks:
      - name: sp-calc
        template: mf-sp-calc
        withParam: '[...h2_0.5.xyz..., ...h2_0.6.xyz..., ...]'  # 12 items
```

**Resulting Argo status.nodes:**
```json
{
  "status": {
    "nodes": {
      "h-pes-sweep-abc123-sp-calc-0": { "type": "Pod", "templateName": "mf-sp-calc", "phase": "Succeeded", ... },
      "h-pes-sweep-abc123-sp-calc-1": { "type": "Pod", "templateName": "mf-sp-calc", "phase": "Succeeded", ... },
      "h-pes-sweep-abc123-sp-calc-2": { "type": "Pod", "templateName": "mf-sp-calc", "phase": "Running", ... },
      ...
      "h-pes-sweep-abc123-sp-calc-11": { "type": "Pod", "templateName": "mf-sp-calc", "phase": "Pending", ... }
    }
  }
}
```

### Frontend Rendering
**Current behavior: Each pod is a separate row**

```
Steps
  h-pes-sweep-abc123-sp-calc-0    ✅ Succeeded
  h-pes-sweep-abc123-sp-calc-1    ✅ Succeeded
  h-pes-sweep-abc123-sp-calc-2    🔄 Running
  h-pes-sweep-abc123-sp-calc-3    ⏳ Pending
  h-pes-sweep-abc123-sp-calc-4    ⏳ Pending
  h-pes-sweep-abc123-sp-calc-5    ⏳ Pending
  h-pes-sweep-abc123-sp-calc-6    ⏳ Pending
  h-pes-sweep-abc123-sp-calc-7    ⏳ Pending
  h-pes-sweep-abc123-sp-calc-8    ⏳ Pending
  h-pes-sweep-abc123-sp-calc-9    ⏳ Pending
  h-pes-sweep-abc123-sp-calc-10   ⏳ Pending
  h-pes-sweep-abc123-sp-calc-11   ⏳ Pending
```

**Problem:** Long, unreadable list with 12 nearly-identical items. No visual grouping.

---

## Argo Node Structure (What parseSteps() Sees)

### Pod Node (Compute Step)
```typescript
interface ArgoNode {
  type: 'Pod'
  templateName: string                    // e.g., "mf-sp-calc", "mf-geom-input"
  displayName: string                     // e.g., "h-pes-sweep-abc123-sp-calc-0"
  phase: RunPhase                         // e.g., "Running", "Succeeded"
  startedAt?: string                      // ISO timestamp
  finishedAt?: string                     // ISO timestamp
  outputs?: {
    parameters?: Array<{
      name: string                        // e.g., "total_energy"
      value: string                       // e.g., "-76.123"
    }>
  }
}
```

### Skipped Node (Quality Gate Blocked)
```typescript
interface SkippedNode {
  type: 'Skipped'
  phase: 'Omitted'
  templateName: string
  displayName: string
  // No outputs
}
```

**Note:** `parseSteps()` treats Skipped nodes identically to Pod nodes—both contribute to the flat list.

---

## Scrolling & Layout Behavior

### RunsPanel Container
**File:** `components/runs/RunsPanel.tsx` → Line 305

```tsx
<div className="w-80 mf-panel border-l border-r-0 flex-shrink-0">
  {/* Header */}
  <div className="flex items-center justify-between px-3 py-2 border-b border-mf-border">
    ...
  </div>

  {/* Scrollable content area */}
  <div className="flex-1 overflow-y-auto mf-scroll">
    {selectedRun ? (
      <RunDetailHeader ... />
      {/* Run detail content */}
    ) : (
      <RunList ... />
    )}
  </div>
</div>
```

### Scroll Styling
```css
.mf-scroll {
  /* Defined in tailwind config */
  /* Custom scrollbar styling, likely from global CSS */
}
```

### Steps Section Scrolling
- The **entire detail panel** scrolls (not individual sections)
- Steps section has **no special max-height**—it consumes as much space as available
- If many steps exist, the entire detail panel scrolls vertically
- **No virtualization** or lazy loading of step rows

### Other Scrollable Sections (for reference)
```tsx
// Logs section has explicit max-height
<pre className="... max-h-60 overflow-auto mf-scroll ...">

// Validation summary has explicit max-height
<div className="... max-h-32 overflow-y-auto mf-scroll ...">
```

---

## Real-Time Status Overlay Integration

While the RunsPanel displays a **static snapshot** at fetch time, the Run Overlay Store provides **real-time updates** to the canvas visualization:

### File: `stores/run-overlay-store.ts`

```typescript
interface NodeRunStatus {
  phase: RunPhase                         // Current phase
  startedAt?: string
  finishedAt?: string
  outputs: Record<string, string>         // e.g., { total_energy: "-76.123 Ha" }
}

function parseArgoNodes(raw: Record<string, unknown>) {
  const status = raw.status ?? {}
  const rawNodes = status.nodes ?? {}
  
  // Extract per-canvas-node statuses
  const nodeStatuses: Record<string, NodeRunStatus> = {}
  for (const argoNode of Object.values(rawNodes)) {
    if (!isCompute && !isSkipped) continue
    
    const templateName = argoNode.templateName ?? ''
    if (!templateName.startsWith('mf-')) continue
    
    const canvasId = templateName.slice(3)  // "mf-sp-calc" → "sp-calc"
    nodeStatuses[canvasId] = {
      phase: argoNode.phase,
      outputs: extractParameters(argoNode)
    }
  }
  
  return { workflowPhase, nodeStatuses }
}
```

**Key insight:** The run overlay store maps **Argo nodes** → **canvas nodes**:
- Argo creates multiple Pod nodes per `withParam` task (one per array item)
- But all of them have the same `templateName` (e.g., all "mf-sp-calc")
- So they map to a **single canvas node ID** (e.g., "sp-calc")
- The store **only tracks the latest status** per canvas node—not per-array-item status

This is why the Steps panel in RunsPanel is **different** from the canvas overlay:
- **RunsPanel.steps**: Shows **all Argo nodes** individually (12 rows for `withParam` with 12 items)
- **Canvas overlay**: Shows **one badge per canvas node** (1 badge for "sp-calc")

---

## Quality Gate & Omitted Nodes

### When a Quality Gate Blocks a Node
```typescript
// In Argo YAML:
- name: collect-energy
  when: '{{tasks.sp-calc.outputs.parameters._qg_scf_converged}} == true'
```

If the condition is false, Argo creates a **Skipped node** with `phase: "Omitted"`:

```json
{
  "h-pes-sweep-abc123-collect-energy": {
    "type": "Skipped",
    "phase": "Omitted",
    "templateName": "mf-collect-energy",
    "displayName": "h-pes-sweep-abc123-collect-energy"
  }
}
```

### Frontend Handling
1. **parseSteps()** includes Skipped nodes: `n.type === 'Pod' || n.type === 'Skipped'`
2. **PhaseBadge** renders the "Omitted" phase with its own styling:
   - Emoji: ⊘
   - Color: gray-400, opacity-70
   - Badge class: `badge badge-omitted`

### Workflow Phase Promotion
```typescript
// In run-overlay-store.ts:
if (workflowPhase === 'Succeeded' && hasOmitted) {
  workflowPhase = 'PartialSuccess'  // Synthetic phase
}
```

This ensures the **workflow-level badge** (not individual step badges) is promoted from "Succeeded" to "PartialSuccess" if any downstream nodes were omitted.

---

## Validation Summary Section

**File:** `components/runs/RunsPanel.tsx` → Lines 173-210

Displays **warnings and infos** stored with the run snapshot:

```tsx
function ValidationSummary({ runName }: { runName: string }) {
  const snap = useSavedWorkflowsStore.getState().runSnapshots[runName]
  if (!snap) return null

  const warnings = snap.validationWarnings ?? []
  const infos = snap.validationInfos ?? []
  
  return (
    <div className="mt-2">
      <div className="text-[10px] ... uppercase tracking-wide px-1">Validation</div>
      <div className="... max-h-32 overflow-y-auto mf-scroll">
        {warnings.map((w, i) => (
          <div key={i} className="flex gap-1.5 text-[11px]">
            <AlertTriangle size={11} className="text-yellow-400 ..." />
            <span className="text-yellow-300 break-words">
              {w.node_id && <span className="font-mono text-mf-text-muted">[{w.node_id}] </span>}
              {w.message}
            </span>
          </div>
        ))}
        {infos.map((info, i) => (
          <div key={i} className="flex gap-1.5 text-[11px]">
            <Info size={11} className="text-blue-400 ..." />
            <span className="text-mf-text-secondary break-words">
              {info.node_id && <span className="font-mono text-mf-text-muted">[{info.node_id}] </span>}
              {info.message}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
```

**Data source:** `saved-workflows-store.ts` → `runSnapshots[runName].validationWarnings/Infos`
- Captured when the workflow is **submitted** (not fetched from Argo)
- Stored in `userdata/projects/{projectId}/workflows/` JSON files

---

## Phase Badge Styling

**File:** `lib/phase-utils.ts`

```typescript
const PHASE_CONFIG: Record<RunPhase, PhaseConfig> = {
  Running:       { emoji: '🔄', textClass: 'text-blue-400 animate-pulse', ... },
  Succeeded:     { emoji: '✅', textClass: 'text-green-400 font-medium', ... },
  Failed:        { emoji: '❌', textClass: 'text-red-400 font-medium', ... },
  Error:         { emoji: '❌', textClass: 'text-red-400 font-medium', ... },
  Pending:       { emoji: '⏳', textClass: 'text-mf-text-muted', ... },
  Unknown:       { emoji: '⊘', textClass: 'text-mf-text-muted', ... },
  Omitted:       { emoji: '⊘', textClass: 'text-gray-400 opacity-70', ... },
  PartialSuccess: { emoji: '⚠️', textClass: 'text-orange-300 font-medium', ... },
}

export function phaseBadgeClass(phase: RunPhase): string {
  return phaseConfig(phase).badgeClass
}
```

**Badge rendering:**
```tsx
function PhaseBadge({ phase }: { phase: RunPhase }) {
  return <span className={phaseBadgeClass(phase)}>{phase}</span>
}
```

---

## Local-Only Runs (Validation-Failed Snapshots)

When a workflow **fails validation before submission**:

```tsx
// Lines 328-352: Local-only run detail
{selectedIsLocalOnly && runSnapshots[selectedRun] && (
  <div className="px-3 pb-3 space-y-2 pt-2">
    <div>
      <div className="text-xs font-mono text-mf-text-secondary break-all">
        {selectedRun}
      </div>
      <PhaseBadge phase={'Failed' as RunPhase} />
    </div>

    <div className="text-[10px] text-mf-text-muted">
      {runSnapshots[selectedRun].savedAt.slice(0, 16).replace('T', ' ')}
    </div>

    {runSnapshots[selectedRun].error && (
      <div className="mt-2">
        <div className="text-[10px] text-red-400 mb-1 uppercase tracking-wide px-1">
          Error
        </div>
        <pre className="bg-mf-base border border-red-500/30 rounded p-2 ... max-h-60 overflow-auto mf-scroll ...">
          {runSnapshots[selectedRun].error}
        </pre>
      </div>
    )}

    <ValidationSummary runName={selectedRun} />
  </div>
)}
```

These are snapshots with `localOnly: true`, showing:
1. Workflow name
2. Failed phase badge
3. Timestamp (from `savedAt`)
4. Error message (from `error` field)
5. Validation warnings/infos

**Note:** No "Steps" section for local-only runs (they never reached Argo).

---

## Run List View (Before Selection)

**File:** `components/runs/RunsPanel.tsx` → Lines 49-148

```tsx
function RunList({ runs, onSelect }: { runs: RunSummaryResponse[]; onSelect: (name: string) => void }) {
  const handleRestore = ...
  const handleDelete = ...

  return (
    <div className="divide-y divide-mf-border/50">
      {runs.map((run) => {
        const hasSnapshot = !!runSnapshots[run.name]
        const isLocalOnly = !!runSnapshots[run.name]?.localOnly
        
        return (
          <div key={run.name} className="group relative">
            <button onClick={() => onSelect(run.name)} className="...">
              <div className="min-w-0">
                <div className="text-xs font-mono text-mf-text-secondary truncate">
                  {run.name}
                </div>
                <div className="text-[10px] text-mf-text-muted mt-0.5">
                  {run.started_at?.slice(0, 16).replace('T', ' ')}
                  {!isLocalOnly && ` · ${formatDuration(run.duration_seconds)}`}
                </div>
              </div>
              <div className="flex items-center gap-1 flex-shrink-0">
                <PhaseBadge phase={run.phase} />
                <ChevronRight size={12} className="text-mf-text-muted" />
              </div>
            </button>

            {/* Action buttons appear on hover */}
            <div className="... hidden group-hover:flex ...">
              {hasSnapshot && (
                <button ... onClick={(e) => handleRestore(run.name, e)} ...>
                  <RotateCcw size={11} />
                </button>
              )}
              {!isLocalOnly && (
                <button ... onClick={(e) => handleDelete(run.name, e)} ...>
                  <Trash2 size={11} />
                </button>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}
```

**Features:**
- Click to view detail
- Hover to reveal action buttons (Restore / Delete)
- Shows run name, start timestamp, duration (if completed), and phase badge
- Sorting: Most recent first (`sort((a, b) => (b.started_at ?? '').localeCompare(a.started_at ?? ''))`)

---

## API Endpoints

**Backend:** `api/routers/runs.py`

| Method | Endpoint | Response Type | Purpose |
|--------|----------|---|---------|
| GET | `/api/v1/runs` | `RunListResponse` | List all runs in namespace |
| GET | `/api/v1/runs/{name}` | `RunDetailResponse` | Get full workflow object + metadata |
| GET | `/api/v1/runs/{name}/logs` | `RunLogsResponse` | Get aggregated logs |
| DELETE | `/api/v1/runs/{name}` | `204 No Content` | Delete workflow from Argo |
| POST | `/api/v1/runs/{name}/save-outputs` | `{ saved: bool, ... }` | Extract outputs to JSON file |

---

## Type Definitions

**File:** `frontend/src/types/index-types.ts`

```typescript
export type RunPhase =
  | 'Pending'           // Workflow queued, not yet started
  | 'Running'           // At least one pod running
  | 'Succeeded'         // All pods succeeded
  | 'Failed'            // At least one pod failed
  | 'Error'             // Workflow error (e.g., bad template)
  | 'Unknown'           // Unknown phase
  | 'Omitted'           // Individual node omitted by when clause
  | 'PartialSuccess'    // Synthetic: Succeeded but ≥1 node Omitted

export interface RunSummaryResponse {
  name: string
  namespace: string
  phase: RunPhase
  started_at?: string
  finished_at?: string
  duration_seconds?: number
  message?: string
}

export interface RunListResponse {
  total: number
  runs: RunSummaryResponse[]
}

export interface RunDetailResponse {
  name: string
  namespace: string
  phase: RunPhase
  raw: Record<string, unknown>  // ← Full Argo workflow JSON
}

export interface RunLogsResponse {
  workflow_name: string
  node_id?: string              // Optional: logs for single node
  logs: string
}
```

---

## Key Findings & Limitations

### ✅ What's Implemented
1. **Step list rendering** from Argo nodes
2. **Phase badge styling** with emojis and animations
3. **Real-time polling** of run status (5-second refetch)
4. **Validation summary** display
5. **Logs streaming** with scrollable pre block
6. **Local-only snapshots** for validation-failed workflows
7. **Quality gate detection** (Omitted phase)
8. **Canvas overlay** with per-node status badges

### ❌ Current Limitations (For Improvement)

1. **Flat list for parallel nodes**
   - No grouping for `withParam` spawned nodes
   - All 12 "sp-calc-0" through "sp-calc-11" shown individually
   - **Suggestion:** Detect common `templateName` prefix and group/collapse

2. **No step count summary**
   - Could show: "sp-calc: 8 succeeded, 2 running, 2 pending"
   - **Suggestion:** Add a summary row or collapsed group header

3. **No virtualization**
   - If workflow has 100+ parallel steps, all render at once
   - **Suggestion:** Use react-window or similar for large step lists

4. **No per-node logs**
   - Logs endpoint supports `?node_id=`, but UI always fetches all logs
   - **Suggestion:** Add "View logs" button per step

5. **Timestamps not shown for individual steps**
   - Only workflow-level timestamps visible
   - **Suggestion:** Show startedAt/finishedAt per step, or on hover

6. **No step duration display**
   - Could calculate `finishedAt - startedAt` for each step
   - **Suggestion:** Add duration column or tooltip

7. **No step search/filter**
   - Can't search for step name in a 100-step workflow
   - **Suggestion:** Add search box + filter by phase

---

## Integration Points

### Polling Hook
**File:** `hooks/useRunOverlayPolling.ts`

Polls run detail every 5 seconds while run is active, updates overlay store.

### UI Store Integration
```typescript
// TopBar.tsx triggers new run detail fetch
const { showNotification, setPendingRunName } = useUIStore()

// RunsPanel monitors pendingRunName and auto-opens detail view
useEffect(() => {
  if (!pendingRunName) return
  setSelectedRun(pendingRunName)
  setPendingRunName(null)
}, [pendingRunName, setPendingRunName])
```

### Canvas Integration
- Run overlay store provides real-time node statuses
- Canvas nodes display phase badges overlaid
- Clicking run list item opens detail panel (toggles `rightPanel: 'runs'`)

---

## Example: Parsing a Typical Argo Workflow

Given this Argo workflow snippet:

```yaml
spec:
  templates:
  - dag:
      tasks:
      - name: geom-input
        withParam: '[file1, file2, file3]'
      - name: sp-calc
        depends: geom-input
        withParam: '[file1, file2, file3]'
      - name: collect-results
        depends: sp-calc.Succeeded
        when: '{{tasks.sp-calc.outputs.parameters._qg_converged}} == true'
```

After execution, `status.nodes` contains:

```json
{
  "wf-abc-geom-input-0": { "type": "Pod", "templateName": "mf-geom-input", "phase": "Succeeded", ... },
  "wf-abc-geom-input-1": { "type": "Pod", "templateName": "mf-geom-input", "phase": "Succeeded", ... },
  "wf-abc-geom-input-2": { "type": "Pod", "templateName": "mf-geom-input", "phase": "Succeeded", ... },
  
  "wf-abc-sp-calc-0": { "type": "Pod", "templateName": "mf-sp-calc", "phase": "Succeeded", ... },
  "wf-abc-sp-calc-1": { "type": "Pod", "templateName": "mf-sp-calc", "phase": "Succeeded", ... },
  "wf-abc-sp-calc-2": { "type": "Pod", "templateName": "mf-sp-calc", "phase": "Running", ... },
  
  "wf-abc-collect-results": { "type": "Skipped", "phase": "Omitted", ... }
}
```

**parseSteps() output:**
```javascript
[
  { id: 'wf-abc-geom-input-0', name: 'wf-abc-geom-input-0', phase: 'Succeeded' },
  { id: 'wf-abc-geom-input-1', name: 'wf-abc-geom-input-1', phase: 'Succeeded' },
  { id: 'wf-abc-geom-input-2', name: 'wf-abc-geom-input-2', phase: 'Succeeded' },
  { id: 'wf-abc-sp-calc-0', name: 'wf-abc-sp-calc-0', phase: 'Succeeded' },
  { id: 'wf-abc-sp-calc-1', name: 'wf-abc-sp-calc-1', phase: 'Succeeded' },
  { id: 'wf-abc-sp-calc-2', name: 'wf-abc-sp-calc-2', phase: 'Running' },
  { id: 'wf-abc-collect-results', name: 'wf-abc-collect-results', phase: 'Omitted' },
]
```

**Rendered output:**
```
Steps
  wf-abc-geom-input-0               ✅ Succeeded
  wf-abc-geom-input-1               ✅ Succeeded
  wf-abc-geom-input-2               ✅ Succeeded
  wf-abc-sp-calc-0                  ✅ Succeeded
  wf-abc-sp-calc-1                  ✅ Succeeded
  wf-abc-sp-calc-2                  🔄 Running
  wf-abc-collect-results            ⊘ Omitted
```

---

## Summary: Opportunities for Enhancement

| Area | Current | Opportunity |
|------|---------|-------------|
| **Step Grouping** | Flat list | Group by templateName + collapse |
| **Parallel Visualization** | Individual rows | Progress bar + summary badge |
| **Step Details** | Name + phase only | Add duration, timestamps, per-node logs |
| **Performance** | All steps rendered | Virtualization for 100+ steps |
| **Search/Filter** | None | Filter by phase, search name |
| **User Experience** | Scrolls entire panel | Sticky header, fixed steps area with scroll |

---

**Document generated:** 2026-04-08
**Analysis scope:** Frontend React component hierarchy, Argo JSON parsing, real-time status updates
**Files analyzed:** 8 core files, 400+ lines of step-related code
