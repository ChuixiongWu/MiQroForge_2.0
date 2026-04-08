# Frontend Runs Panel — Key Code Snippets & Implementation Reference

## parseSteps() — The Core Function

**File:** `frontend/src/components/runs/RunsPanel.tsx` (lines 21-31)

```typescript
interface ArgoStepNode {
  id: string
  name: string
  phase: RunPhase
}

function parseSteps(detail: RunDetailResponse): ArgoStepNode[] {
  const status = (detail.raw.status ?? {}) as Record<string, unknown>
  const nodes = (status.nodes ?? {}) as Record<string, Record<string, unknown>>
  return Object.entries(nodes)
    .filter(([, n]) => n.type === 'Pod' || n.type === 'Skipped')
    .map(([id, n]) => ({
      id,
      name: (n.displayName ?? n.templateName ?? id) as string,
      phase: ((n.phase as RunPhase | undefined) ?? 'Unknown'),
    }))
}
```

**What it does:**
1. Accesses `raw` Argo workflow JSON from `RunDetailResponse`
2. Extracts `status.nodes` object
3. Filters to Pod and Skipped nodes only (ignores DAG, Task, etc.)
4. Maps each node to `{ id, name, phase }` tuple
5. Returns flat array

**Why this matters:**
- This is the ONLY place that parses Argo nodes in the steps list
- All other step functionality depends on this array
- To add grouping, you'd modify this function's return structure

---

## Step Rendering — The Display Loop

**File:** `frontend/src/components/runs/RunsPanel.tsx` (lines 366-382)

```tsx
{(() => {
  const steps = parseSteps(detailQuery.data)
  if (steps.length === 0) return null
  return (
    <div>
      <div className="text-[10px] text-mf-text-muted mb-1 uppercase tracking-wide">
        Steps
      </div>
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

**Breakdown:**
- IIFE to keep scope isolated
- Early return if no steps
- Label: "STEPS" (uppercase, muted, small)
- Container: `space-y-1` (4px gap)
- Each row:
  - Flexbox: space-between
  - Left: name (monospace, truncated, 11px)
  - Right: badge (no truncate, auto-width)

---

## PhaseBadge Component

**File:** `frontend/src/components/runs/RunsPanel.tsx` (lines 38-40)

```tsx
function PhaseBadge({ phase }: { phase: RunPhase }) {
  return <span className={phaseBadgeClass(phase)}>{phase}</span>
}
```

**Implementation is very simple — all logic in `phase-utils.ts`**

**Related:** `lib/phase-utils.ts` (lines 12-50)

```typescript
const PHASE_CONFIG: Record<RunPhase, PhaseConfig> = {
  Running:       { emoji: '🔄', borderClass: 'border-blue-400 animate-pulse',    textClass: 'text-blue-400',              badgeClass: 'badge badge-running'   },
  Succeeded:     { emoji: '✅', borderClass: 'border-green-500',                 textClass: 'text-green-400 font-medium', badgeClass: 'badge badge-succeeded' },
  Failed:        { emoji: '❌', borderClass: 'border-red-500',                   textClass: 'text-red-400 font-medium',   badgeClass: 'badge badge-failed'    },
  Error:         { emoji: '❌', borderClass: 'border-red-500',                   textClass: 'text-red-400 font-medium',   badgeClass: 'badge badge-failed'    },
  Pending:       { emoji: '⏳', borderClass: 'border-gray-500',                  textClass: 'text-mf-text-muted',         badgeClass: 'badge badge-pending'   },
  Unknown:       { emoji: '⊘',  borderClass: 'border-gray-600 opacity-50',      textClass: 'text-mf-text-muted',         badgeClass: 'badge badge-unknown'   },
  Omitted:       { emoji: '⊘',  borderClass: 'border-gray-600 opacity-40',      textClass: 'text-gray-400 opacity-70',   badgeClass: 'badge badge-omitted'   },
  PartialSuccess: { emoji: '⚠️', borderClass: 'border-orange-400',              textClass: 'text-orange-300 font-medium', badgeClass: 'badge badge-partial'  },
}

export function phaseBadgeClass(phase: RunPhase): string {
  return phaseConfig(phase).badgeClass
}
```

**To customize badges:** Modify `PHASE_CONFIG` map

---

## RunList — The Selection Interface

**File:** `frontend/src/components/runs/RunsPanel.tsx` (lines 49-148)

```tsx
function RunList({
  runs,
  onSelect,
}: {
  runs: RunSummaryResponse[]
  onSelect: (name: string) => void
}) {
  const queryClient = useQueryClient()
  const { runSnapshots } = useSavedWorkflowsStore()
  const { loadFromNodes, setMeta } = useWorkflowStore()
  const { showNotification, selectNode, setRightPanel } = useUIStore()
  const { setActiveRun } = useRunOverlayStore()

  const handleRestore = useCallback(
    (runName: string, e: React.MouseEvent) => {
      e.stopPropagation()
      const snap = useSavedWorkflowsStore.getState().runSnapshots[runName]
      if (!snap) return
      const { meta, nodes, edges } = snapshotToRF(snap.snapshot)
      setMeta(meta)
      loadFromNodes(nodes, edges)
      selectNode(null)
      setRightPanel(null)
      setActiveRun(runName)                  // ← Start polling overlay
      showNotification('success', `Restored canvas from run "${runName}"`)
    },
    [loadFromNodes, setMeta, selectNode, setRightPanel, showNotification, setActiveRun],
  )

  const handleDelete = useCallback(
    async (runName: string, e: React.MouseEvent) => {
      e.stopPropagation()
      if (!confirm(`Delete run "${runName}" from Argo? This cannot be undone.`)) return
      try {
        await argoApi.deleteRun(runName, useProjectStore.getState().currentProjectId ?? undefined)
        useSavedWorkflowsStore.getState().deleteRunSnapshot(runName)
        showNotification('success', `Deleted run "${runName}"`)
        queryClient.invalidateQueries({ queryKey: ['runs'] })
      } catch (err) {
        showNotification('error', `Delete failed: ${err instanceof Error ? err.message : String(err)}`)
      }
    },
    [showNotification, queryClient],
  )

  if (runs.length === 0) {
    return <p className="px-3 py-4 text-xs text-mf-text-muted text-center">No runs found</p>
  }

  return (
    <div className="divide-y divide-mf-border/50">
      {runs.map((run) => {
        const hasSnapshot = !!runSnapshots[run.name]
        const isLocalOnly = !!runSnapshots[run.name]?.localOnly
        return (
          <div key={run.name} className="group relative">
            <button
              onClick={() => onSelect(run.name)}
              className="w-full px-3 py-2 text-left hover:bg-mf-hover transition-colors flex items-center justify-between gap-2"
            >
              <div className="min-w-0">
                <div className="text-xs font-mono text-mf-text-secondary truncate">{run.name}</div>
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

            {/* Action buttons — appear on hover */}
            <div className="absolute right-8 top-1/2 -translate-y-1/2 hidden group-hover:flex items-center gap-0.5 bg-mf-card rounded px-0.5 shadow">
              {hasSnapshot && (
                <button
                  onClick={(e) => handleRestore(run.name, e)}
                  className="p-1 text-blue-400 hover:text-blue-200 hover:bg-mf-hover rounded transition-colors"
                  title="Restore canvas to this run's workflow"
                >
                  <RotateCcw size={11} />
                </button>
              )}
              {!isLocalOnly && (
                <button
                  onClick={(e) => handleDelete(run.name, e)}
                  className="p-1 text-mf-text-muted hover:text-red-400 hover:bg-mf-hover rounded transition-colors"
                  title="Delete this run from Argo"
                >
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

**Key interactions:**
- Row click: `onSelect(run.name)` → `setSelectedRun(name)`
- Hover: Show action buttons (Restore/Delete)
- Restore: Load canvas from snapshot + `setActiveRun()` to start polling

---

## Run Overlay Store — Real-Time Status

**File:** `frontend/src/stores/run-overlay-store.ts` (lines 48-97)

```typescript
function parseArgoNodes(raw: Record<string, unknown>): {
  workflowPhase: RunPhase
  nodeStatuses: Record<string, NodeRunStatus>
} {
  const status = (raw.status ?? {}) as Record<string, unknown>
  let workflowPhase = (status.phase as RunPhase | undefined) ?? 'Unknown'
  const rawNodes = (status.nodes ?? {}) as Record<string, ArgoNode>

  const nodeStatuses: Record<string, NodeRunStatus> = {}
  let hasOmitted = false

  for (const argoNode of Object.values(rawNodes)) {
    // Process Pod nodes (actual computation steps) and Skipped nodes (omitted
    // because a `when` condition was false — e.g. quality gate not passed).
    const isCompute = argoNode.type === 'Pod'
    const isSkipped = argoNode.type === 'Skipped'
    if (!isCompute && !isSkipped) continue

    const templateName = argoNode.templateName ?? ''
    // Template name format: "mf-{canvasNodeId}"
    if (!templateName.startsWith('mf-')) continue
    const canvasId = templateName.slice(3)   // strip "mf-"
    if (!canvasId) continue

    const nodePhase = (argoNode.phase as RunPhase | undefined) ?? 'Unknown'
    if (nodePhase === 'Omitted') hasOmitted = true

    // Extract output parameters (only present on Pod nodes that ran)
    const outputs: Record<string, string> = {}
    for (const param of argoNode.outputs?.parameters ?? []) {
      if (param.name && param.value !== undefined) {
        outputs[param.name] = String(param.value)
      }
    }

    nodeStatuses[canvasId] = {
      phase:      nodePhase,
      startedAt:  argoNode.startedAt,
      finishedAt: argoNode.finishedAt,
      outputs,
    }
  }

  // Promote Succeeded → PartialSuccess when quality gates blocked downstream nodes
  if (workflowPhase === 'Succeeded' && hasOmitted) {
    workflowPhase = 'PartialSuccess'
  }

  return { workflowPhase, nodeStatuses }
}
```

**Key insight:**
- Maps Argo nodes (per-array-item pods) to canvas nodes (by templateName)
- Example: "h-pes-sweep-sp-calc-0" through "...sp-calc-11" all map to "sp-calc"
- Only latest status per canvas node is kept (no per-item tracking)

---

## Query Setup — Data Fetching

**File:** `frontend/src/components/runs/RunsPanel.tsx` (lines 269-283)

```tsx
const listQuery = useQuery({
  queryKey: ['runs'],
  queryFn: () => argoApi.listRuns(useProjectStore.getState().currentProjectId ?? undefined),
  refetchInterval: 10000,
})

// ... merge local runs ...

const detailQuery = useQuery({
  queryKey: ['run-detail', selectedRun],
  queryFn: () => (selectedRun ? argoApi.getRun(selectedRun) : null),
  enabled: !!selectedRun && !selectedIsLocalOnly,
  refetchInterval: 5000,
})
```

**Intervals:**
- List: 10 seconds (lower priority, full list refresh)
- Detail: 5 seconds (higher priority, single run updates)

---

## API Layer

**File:** `frontend/src/api/argo-api.ts`

```typescript
export const argoApi = {
  listRuns(projectId?: string): Promise<RunListResponse> {
    const q = projectId ? `?project_id=${encodeURIComponent(projectId)}` : ''
    return fetchJSON(`${BASE}/runs${q}`)
  },

  getRun(name: string): Promise<RunDetailResponse> {
    return fetchJSON(`${BASE}/runs/${encodeURIComponent(name)}`)
  },

  getLogs(name: string, nodeId?: string): Promise<RunLogsResponse> {
    const q = nodeId ? `?node_id=${encodeURIComponent(nodeId)}` : ''
    return fetchJSON(`${BASE}/runs/${encodeURIComponent(name)}/logs${q}`)
  },

  deleteRun(name: string, projectId?: string): Promise<void> {
    const q = projectId ? `?project_id=${encodeURIComponent(projectId)}` : ''
    return fetchJSON(`${BASE}/runs/${encodeURIComponent(name)}${q}`, { method: 'DELETE' })
  },

  saveOutputs(name: string, projectId?: string): Promise<{ saved: boolean; outputs_count: number }> {
    const q = projectId ? `?project_id=${encodeURIComponent(projectId)}` : ''
    return fetchJSON(`${BASE}/runs/${encodeURIComponent(name)}/save-outputs${q}`, { method: 'POST' })
  },
}
```

**Note:** `getLogs()` supports `nodeId` parameter but UI doesn't use it yet

---

## Backend API Response

**File:** `api/routers/runs.py` (lines 53-68)

```python
@router.get("/{name}", response_model=RunDetailResponse, summary="运行详情")
def get_run(name: str, argo: ArgoService = Depends(get_argo_service)) -> RunDetailResponse:
    try:
        wf = argo.get_workflow(name)  # Calls: argo get {name} -o json
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    meta = wf.get("metadata", {})
    status = wf.get("status", {})

    return RunDetailResponse(
        name=meta.get("name", name),
        namespace=meta.get("namespace", ""),
        phase=status.get("phase", "Unknown"),
        raw=wf,                       # ← Complete workflow object
    )
```

**Key:**
- `raw` field contains the entire `argo get` JSON output
- Frontend gets full power to parse it however needed
- Backend doesn't filter or transform node data

---

## Type Definitions

**File:** `frontend/src/types/index-types.ts` (lines 125-160)

```typescript
export type RunPhase =
  | 'Pending'
  | 'Running'
  | 'Succeeded'
  | 'Failed'
  | 'Error'
  | 'Unknown'
  | 'Omitted'
  | 'PartialSuccess'

export interface RunSummaryResponse {
  name: string
  namespace: string
  phase: RunPhase
  started_at?: string
  finished_at?: string
  duration_seconds?: number
  message?: string
}

export interface RunDetailResponse {
  name: string
  namespace: string
  phase: RunPhase
  raw: Record<string, unknown>
}

export interface RunLogsResponse {
  workflow_name: string
  node_id?: string
  logs: string
}
```

---

## Improvement Ideas (Copy-Paste Ready)

### 1. Group Steps by Template Name

```typescript
// Replace parseSteps() with this:
interface GroupedStep {
  templateName: string
  steps: ArgoStepNode[]
  summary: { succeeded: number; failed: number; running: number; pending: number }
}

function parseStepsGrouped(detail: RunDetailResponse): GroupedStep[] {
  const steps = parseSteps(detail)  // Use existing parser
  
  const groups = new Map<string, ArgoStepNode[]>()
  for (const step of steps) {
    const templateName = step.name.split('-').slice(0, -1).join('-')  // Remove index suffix
    if (!groups.has(templateName)) groups.set(templateName, [])
    groups.get(templateName)!.push(step)
  }

  return Array.from(groups.entries()).map(([templateName, stepsInGroup]) => {
    const summary = {
      succeeded: stepsInGroup.filter(s => s.phase === 'Succeeded').length,
      failed: stepsInGroup.filter(s => s.phase === 'Failed').length,
      running: stepsInGroup.filter(s => s.phase === 'Running').length,
      pending: stepsInGroup.filter(s => s.phase === 'Pending').length,
    }
    return { templateName, steps: stepsInGroup, summary }
  })
}
```

### 2. Add Step Duration

```typescript
interface ArgoStepNode {
  id: string
  name: string
  phase: RunPhase
  startedAt?: string        // Add these
  finishedAt?: string
}

function parseSteps(detail: RunDetailResponse): ArgoStepNode[] {
  const status = (detail.raw.status ?? {}) as Record<string, unknown>
  const nodes = (status.nodes ?? {}) as Record<string, Record<string, unknown>>
  return Object.entries(nodes)
    .filter(([, n]) => n.type === 'Pod' || n.type === 'Skipped')
    .map(([id, n]) => ({
      id,
      name: (n.displayName ?? n.templateName ?? id) as string,
      phase: ((n.phase as RunPhase | undefined) ?? 'Unknown'),
      startedAt: (n.startedAt as string | undefined),      // Add
      finishedAt: (n.finishedAt as string | undefined),    // Add
    }))
}

// In render:
function formatStepDuration(startedAt?: string, finishedAt?: string): string {
  if (!startedAt || !finishedAt) return '—'
  const start = new Date(startedAt).getTime()
  const end = new Date(finishedAt).getTime()
  const secs = (end - start) / 1000
  return formatDurationSeconds(secs)
}

// Then in the row:
<span className="text-[10px] text-mf-text-muted">
  {formatStepDuration(n.startedAt, n.finishedAt)}
</span>
```

### 3. Add Step Search/Filter

```tsx
const [stepFilter, setStepFilter] = useState('')
const [phaseFilter, setPhaseFilter] = useState<RunPhase | 'All'>('All')

const filtered = steps.filter(s => {
  const matchName = s.name.toLowerCase().includes(stepFilter.toLowerCase())
  const matchPhase = phaseFilter === 'All' || s.phase === phaseFilter
  return matchName && matchPhase
})

// In render:
<input
  type="text"
  placeholder="Search steps..."
  value={stepFilter}
  onChange={(e) => setStepFilter(e.target.value)}
  className="w-full px-2 py-1 text-xs bg-mf-base border border-mf-border rounded mb-2"
/>

<select
  value={phaseFilter}
  onChange={(e) => setPhaseFilter(e.target.value as RunPhase | 'All')}
  className="w-full px-2 py-1 text-xs bg-mf-base border border-mf-border rounded mb-2"
>
  <option value="All">All phases</option>
  <option value="Running">Running</option>
  <option value="Succeeded">Succeeded</option>
  {/* etc */}
</select>
```

---

**Document created:** 2026-04-08
**Intended for:** Frontend developers implementing runs detail view enhancements
