# Frontend Runs Panel — Quick Reference & Visualization

## Component Tree Diagram

```
RunsPanel (399 lines)
│
├─ Header
│  └─ "Runs (X)" + refresh button
│
└─ Main Content Area (flex-1 overflow-y-auto)
   │
   ├─ State: !selectedRun
   │  └─ RunList
   │     └─ Divider-separated rows
   │        ├─ Run name (font-mono, truncated)
   │        ├─ Timestamp (ISO 16 chars)
   │        ├─ Duration (if completed)
   │        ├─ Phase badge (right-aligned)
   │        └─ Hover: Restore/Delete buttons
   │
   └─ State: selectedRun
      │
      ├─ RunDetailHeader
      │  ├─ "← Back" button
      │  └─ "Restore Canvas" button (if snapshot exists)
      │
      ├─ (If local-only)
      │  ├─ Name + Failed badge
      │  ├─ Timestamp
      │  ├─ Error block (max-h-60 overflow)
      │  └─ ValidationSummary
      │
      └─ (If Argo-submitted)
         ├─ Metadata
         │  ├─ Name (break-all)
         │  └─ Phase badge
         │
         ├─ Status message (if present)
         │
         ├─ Steps Section ← KEY AREA
         │  ├─ "STEPS" label
         │  └─ Step list (space-y-1)
         │     └─ {steps.map((n) => (
         │        <div key={n.id}>
         │          <span>{n.name}</span>
         │          <PhaseBadge phase={n.phase} />
         │        </div>
         │      ))}
         │
         ├─ ValidationSummary
         │  └─ max-h-32 overflow-y-auto
         │
         └─ RunLogs
            └─ max-h-60 overflow-auto
               <pre>logs content</pre>
```

---

## Data Flow Diagram

```
┌─────────────────────────────────┐
│  Backend: Argo K8s Cluster      │
│  argo get {name} -o json        │
└──────────────┬──────────────────┘
               │
               │ RUN_DETAIL_RESPONSE
               │ {
               │   name, namespace, phase,
               │   raw: { metadata, status }
               │ }
               │
               ▼
┌─────────────────────────────────┐
│  Frontend: getRun() via argo-api│
│  GET /api/v1/runs/{name}        │
│  refetchInterval: 5000ms        │
└──────────────┬──────────────────┘
               │
               │ RunDetailResponse
               │
               ▼
┌─────────────────────────────────┐
│  RunsPanel                      │
│  detailQuery.data               │
└──────────────┬──────────────────┘
               │
               ├──────────┬────────────┬─────────────┐
               │          │            │             │
               ▼          ▼            ▼             ▼
            parseSteps  getRun   ValidationSummary  RunLogs
               │          │            │             │
               │          │            │             │
               ▼          ▼            ▼             ▼
            Steps[]    Metadata   Warnings[]     LogString
               │          │            │             │
               │          │            │             │
               └──────────┴────────────┴─────────────┘
                          │
                          ▼
                  RENDERED OUTPUT
```

---

## Step List Current Rendering

### For a workflow with `withParam: [12 items]` on "sp-calc" task:

**What the UI shows:**
```
Steps
  h-pes-sweep-abc123-sp-calc-0               ✅ Succeeded
  h-pes-sweep-abc123-sp-calc-1               ✅ Succeeded
  h-pes-sweep-abc123-sp-calc-2               ✅ Succeeded
  h-pes-sweep-abc123-sp-calc-3               ✅ Succeeded
  h-pes-sweep-abc123-sp-calc-4               🔄 Running
  h-pes-sweep-abc123-sp-calc-5               ⏳ Pending
  h-pes-sweep-abc123-sp-calc-6               ⏳ Pending
  h-pes-sweep-abc123-sp-calc-7               ⏳ Pending
  h-pes-sweep-abc123-sp-calc-8               ⏳ Pending
  h-pes-sweep-abc123-sp-calc-9               ⏳ Pending
  h-pes-sweep-abc123-sp-calc-10              ⏳ Pending
  h-pes-sweep-abc123-sp-calc-11              ⏳ Pending
```

**The code:**
```tsx
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
```

**Layout breakdown:**
- Container: `space-y-1` (1 gap between rows)
- Each row: flex, items-center, justify-between
- Left: name, truncated, monospace, text-[11px]
- Right: phase badge, no truncate
- Height: ~18-20px per row
- Total for 12 steps: ~240px (before scrolling)

---

## Argo Node Object Structure

```typescript
// What status.nodes contains:
{
  "workflow-name-task-index": {
    id: string              // Argo assigns this
    type: "Pod"             // or "Skipped"
    displayName: string     // "workflow-name-task-index"
    templateName: string    // "mf-sp-calc" (MiQroForge convention)
    phase: string           // "Running" | "Succeeded" | "Failed" | "Omitted"
    startedAt: string       // ISO timestamp
    finishedAt: string      // ISO timestamp
    outputs?: {
      parameters: [
        { name: string, value: string },
        ...
      ]
    }
  }
}
```

**Key for parseSteps():**
- Filter: `type === 'Pod' || type === 'Skipped'`
- Extract: `displayName` (or fallback to `templateName` or `id`)
- Extract: `phase` (or fallback to 'Unknown')
- Map to `ArgoStepNode { id, name, phase }`

---

## Phase Badge Styling Reference

```tsx
const PHASE_CONFIG = {
  Running:       { emoji: '🔄', text: 'blue-400 animate-pulse' },
  Succeeded:     { emoji: '✅', text: 'green-400 font-medium' },
  Failed:        { emoji: '❌', text: 'red-400 font-medium' },
  Error:         { emoji: '❌', text: 'red-400 font-medium' },
  Pending:       { emoji: '⏳', text: 'text-mf-text-muted' },
  Unknown:       { emoji: '⊘',  text: 'text-mf-text-muted' },
  Omitted:       { emoji: '⊘',  text: 'gray-400 opacity-70' },
  PartialSuccess: { emoji: '⚠️', text: 'orange-300 font-medium' },
}
```

**Badge rendered as:**
```tsx
<span className={phaseBadgeClass(phase)}>
  {phaseEmoji(phase)} {phase}
</span>
```

---

## Scrolling Behavior

### RunsPanel Container (w-80)
```
┌─────────────────────────┐
│ Header (fixed height)   │ ← "Runs (5)"
├─────────────────────────┤
│                         │
│  Scrollable Content     │ ← flex-1 overflow-y-auto
│  (RunList or Detail)    │    max height = container - header
│                         │    scrollbar: .mf-scroll
│                         │
└─────────────────────────┘
```

### Detail View Sections
```
┌─────────────────────────┐
│ RunDetailHeader (sticky)│ ← "← Back | Restore Canvas"
├─────────────────────────┤
│ Metadata                │ (no max-height, flows naturally)
├─────────────────────────┤
│ Steps                   │ (no max-height, flows naturally)
│ (can be very long)      │
├─────────────────────────┤
│ ValidationSummary       │ ← max-h-32 overflow-y-auto
│ (scrolls internally)    │
├─────────────────────────┤
│ RunLogs                 │ ← max-h-60 overflow-auto
│ (scrolls internally)    │
└─────────────────────────┘
```

**Scrolling strategy:**
- Only the outer `.mf-scroll` div scrolls (entire detail panel)
- ValidationSummary and RunLogs have internal scrollbars
- Steps section scrolls with everything else (no separate scroll)

---

## useRunOverlayPolling Integration

```typescript
// In App.tsx -> CanvasLayout
useRunOverlayPolling()

// What it does:
// 1. Reads activeRunName from useRunOverlayStore
// 2. If activeRunName exists, polls getRun() every 5 seconds
// 3. Parses Argo JSON via parseArgoNodes()
// 4. Updates useRunOverlayStore.nodeStatuses
// 5. Canvas components read nodeStatuses and display badges
```

**Timeline:**
```
t=0:   User clicks run in RunsPanel
       → setActiveRun(runName)
       → polling hook activates
       
t=1s:  Canvas shows initial status from overlay store
       
t=5s:  Polling triggers getRun(runName)
       → updateFromArgo(raw)
       → nodeStatuses updated
       → Canvas re-renders badges
       
t=10s: Another poll
       (and so on until user selects different run or clears overlay)
```

---

## Keyboard & Interactions

### RunList (Run Selection)
- Click row → `onSelect(run.name)` → `setSelectedRun(name)`
- Hover → show Restore/Delete buttons (group-hover)
- Restore (RotateCcw icon) → `handleRestore()` → load canvas from snapshot + setActiveRun()
- Delete (Trash2 icon) → confirm → deleteRun() + invalidateQueries(['runs'])

### RunDetail
- Click "← Back" → `setSelectedRun(null)` → back to list
- Click "Restore Canvas" → same as Restore button in list

### Auto-Selection
```typescript
// In RunsPanel effect:
useEffect(() => {
  if (!pendingRunName) return
  setSelectedRun(pendingRunName)  // Auto-open detail view
  setPendingRunName(null)          // Clear flag
}, [pendingRunName, setPendingRunName])
```
When TopBar submits a workflow, it sets `pendingRunName`, which auto-opens the detail view.

---

## Data Sources

### List Query
```typescript
const listQuery = useQuery({
  queryKey: ['runs'],
  queryFn: () => argoApi.listRuns(currentProjectId),
  refetchInterval: 10000,  // 10 seconds
})

// Result: RunListResponse
// { total: number, runs: RunSummaryResponse[] }
```

### Detail Query
```typescript
const detailQuery = useQuery({
  queryKey: ['run-detail', selectedRun],
  queryFn: () => (selectedRun ? argoApi.getRun(selectedRun) : null),
  enabled: !!selectedRun && !selectedIsLocalOnly,  // Don't fetch for local-only
  refetchInterval: 5000,  // 5 seconds
})

// Result: RunDetailResponse
// { name, namespace, phase, raw: full_argo_workflow_json }
```

### Logs Query
```typescript
const query = useQuery({
  queryKey: ['run-logs', runName],
  queryFn: () => argoApi.getLogs(runName),
  refetchInterval: 5000,
})

// Result: RunLogsResponse
// { name, logs: string }
```

---

## Local-Only Snapshots

Stored in `useSavedWorkflowsStore` (Zustand):

```typescript
interface RunSnapshot {
  runName: string
  snapshot: { nodes, edges, meta }
  validationWarnings: ValidationIssue[]
  validationInfos: ValidationIssue[]
  error?: string                    // Compilation or submission error
  localOnly: boolean                // true = not in Argo, only local
  savedAt: string                   // ISO timestamp
}
```

**When created:**
1. User submits workflow → validation fails
2. Compilation error or API error
3. Frontend saves snapshot with `localOnly: true` + error message
4. Later, user can view this in detail view

**What's displayed:**
```
Name: workflow-name
Phase: Failed ❌
Timestamp: 2026-04-08 12:34
Error: [error message from backend]
Validation: [warnings and infos captured at submission time]
(No Steps section because workflow never reached Argo)
```

---

## Phase Badge Placement

### In RunList
```
┌─────────────────────────────────────────┐
│ ┌───────────────┐  ┌─────────────────┐  │
│ │ h-pes-sweep-  │  │ ✅   Running    │  │
│ │ abc123        │  │         →       │  │
│ │ 2026-04-08 12:34 ├─────────────────┤  │
│ │               │  │ (hover shows:)  │  │
│ │               │  │ ↻ Restore       │  │
│ │               │  │ 🗑 Delete       │  │
│ └───────────────┘  └─────────────────┘  │
└─────────────────────────────────────────┘
```

### In RunDetail (top)
```
┌─────────────────────────────────────────┐
│ h-pes-sweep-abc123    ✅ Running        │
│ Status: Running 3 steps...              │
└─────────────────────────────────────────┘
```

### In Steps Section
```
Steps
  sp-calc-0               ✅ Succeeded
  sp-calc-1               ✅ Succeeded
  sp-calc-2               🔄 Running
  collect-energy          ⏳ Pending
```

### In Canvas (Real-time overlay)
```
┌──────────────────┐
│  [sp-calc]       │
│     🔄           │  ← Badge on node
│  Running: 12     │     Shows latest status from runOverlayStore
│                  │
└──────────────────┘
```

---

## Query Lifecycle

```
Initial:
  listQuery = { status: 'pending' }
  detailQuery = disabled (selectedRun = null)

User clicks run "abc123":
  setSelectedRun("abc123")
  detailQuery enabled = true
  → queryFn fires: getRun("abc123")
  → data received: RunDetailResponse with raw Argo JSON
  → render detail view
  → refetchInterval: 5000ms starts polling

5 seconds later:
  → queryFn fires again: getRun("abc123")
  → compare data with cache
  → if changed, re-render with new status
  → steps list updated

User clicks back:
  setSelectedRun(null)
  detailQuery enabled = false
  → polling stops
  → queryClient keeps cache for 5 min default staleTime

User clicks same run again:
  setSelectedRun("abc123")
  detailQuery enabled = true
  → data already in cache (not stale)
  → renders immediately
  → refetchInterval resumes after 5s
```

---

## CSS Classes Used in Steps

| Class | Purpose |
|-------|---------|
| `space-y-1` | Gap between step rows (0.25rem = 4px) |
| `text-xs` | Font size for row (12px) |
| `font-mono` | Monospace for step names |
| `text-[11px]` | Step name font size (11px, smaller than row) |
| `truncate` | Ellipsis overflow on step names |
| `text-mf-text-secondary` | Dimmed text color for names |
| `flex` | Flexbox layout for row |
| `items-center` | Vertical center alignment |
| `justify-between` | Space name left, badge right |
| `gap-1` | Horizontal gap (same in phase-utils) |
| `animate-pulse` | Running phase animation (pulsing blue) |
| `font-medium` | Bold text for Success/Failed phases |
| `opacity-70` | Dimmed for Omitted nodes |
| `break-words` | Wrap long validation messages |

---

## Summary for Developers

**To understand how steps are rendered:**
1. Read `RunsPanel.tsx` lines 21-31 (`parseSteps()`)
2. Read `RunsPanel.tsx` lines 366-382 (rendering)
3. Check `phase-utils.ts` for badge styling
4. Check `run-overlay-store.ts` for real-time updates

**To add grouping for parallel steps:**
1. Modify `parseSteps()` to group by `templateName` prefix
2. Add collapsible group component with summary badge (e.g., "5 succeeded, 2 running")
3. Optional: Add expand/collapse state to localStorage

**To improve performance with 100+ steps:**
1. Integrate `react-window` for virtualization
2. Replace `.map()` with `<FixedSizeList>` 
3. Keep row height constant (18-20px)

**To show per-node logs:**
1. Add `?node_id={n.id}` param to `getLogs()` call
2. Add expandable "View logs" button per step
3. Cache logs per node_id

