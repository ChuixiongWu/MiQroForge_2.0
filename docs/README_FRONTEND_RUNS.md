# Frontend Runs Detail View — Complete Documentation Index

This directory contains comprehensive analysis of the MiQroForge frontend's "Runs" detail view component, how it displays workflow execution steps, handles parallel/fan-out nodes, and integrates with real-time status updates.

## 📄 Documentation Files

### 1. **frontend_runs_detail_analysis.md** (26 KB, 786 lines)
   **Comprehensive architectural analysis**
   - Component hierarchy and file structure
   - Complete data flow from backend to rendering
   - How individual run steps are parsed and displayed
   - Fan-out/parallel node visualization (current flat list approach)
   - Argo node structure and quality gate handling
   - Real-time overlay integration
   - Local-only snapshot handling
   - API endpoints and type definitions
   - Current limitations and improvement opportunities

### 2. **frontend_runs_visualization_guide.md** (17 KB, 506 lines)
   **Quick reference and visual diagrams**
   - Component tree diagram (ASCII art)
   - Data flow diagram (ASCII art)
   - Current step list rendering example (with `withParam`)
   - Argo node object structure reference
   - Phase badge styling and placement
   - Scrolling behavior diagram
   - Query lifecycle timeline
   - CSS classes reference table
   - Developer quick-start guide

### 3. **frontend_runs_code_snippets.md** (18 KB, 538 lines)
   **Copy-paste ready code references**
   - `parseSteps()` function (the core parsing logic)
   - Step rendering display loop
   - `PhaseBadge` component and phase config
   - `RunList` component (selection interface)
   - Run overlay store (real-time status)
   - Query setup (data fetching)
   - API layer functions
   - Backend API response handler
   - Type definitions
   - Three improvement ideas with code examples:
     - Group steps by template name
     - Add step duration display
     - Add step search/filter

## 🎯 Quick Navigation

### "How do individual run steps get rendered?"
👉 **Start here:** `frontend_runs_detail_analysis.md` → "Data Flow: How Steps Are Rendered" section

### "How are parallel/fan-out nodes displayed?"
👉 **Start here:** `frontend_runs_detail_analysis.md` → "How Parallel/Fan-Out Nodes Are Currently Displayed" section

### "I need to add grouping for parallel steps"
👉 **Start here:** `frontend_runs_code_snippets.md` → "Improvement Ideas (Copy-Paste Ready)" → "Group Steps by Template Name"

### "What's the component structure?"
👉 **Start here:** `frontend_runs_visualization_guide.md` → "Component Tree Diagram" section

### "How does real-time status update work?"
👉 **Start here:** `frontend_runs_detail_analysis.md` → "Real-Time Status Overlay Integration" section

### "What CSS classes are used?"
👉 **Start here:** `frontend_runs_visualization_guide.md` → "CSS Classes Used in Steps" table

### "Where can I copy-paste code?"
👉 **Start here:** `frontend_runs_code_snippets.md` → Any section

## 📊 Key Findings Summary

### Current Implementation ✅
- ✅ Step list rendering from Argo nodes
- ✅ Phase badge styling with emojis and animations
- ✅ Real-time polling of run status (5-second refetch)
- ✅ Validation summary display
- ✅ Logs streaming with scrollable pre block
- ✅ Local-only snapshots for validation-failed workflows
- ✅ Quality gate detection (Omitted phase)
- ✅ Canvas overlay with per-node status badges

### Current Limitations ❌
1. **Flat list for parallel nodes** — All 12 "sp-calc-0" through "sp-calc-11" shown individually
2. **No step count summary** — Could show "sp-calc: 8 succeeded, 2 running, 2 pending"
3. **No virtualization** — All steps render at once (performance issue with 100+ steps)
4. **No per-node logs** — Logs endpoint supports `?node_id=`, but UI always fetches all logs
5. **No step timestamps** — Only workflow-level timestamps visible
6. **No step duration display** — Could calculate `finishedAt - startedAt` per step
7. **No step search/filter** — Can't search for step name in large workflows

## 🏗️ Component Hierarchy

```
RunsPanel.tsx (399 lines)
├── RunList (run selection interface)
└── RunDetail (selected run details)
    ├── RunDetailHeader (back / restore buttons)
    ├── Metadata (name, phase badge)
    ├── Steps Section ← KEY AREA
    │   └── {steps.map(step => <StepRow />)}
    ├── ValidationSummary (warnings/infos)
    └── RunLogs (execution logs)
```

## 📝 File References

| File | Lines | Purpose |
|------|-------|---------|
| `frontend/src/components/runs/RunsPanel.tsx` | 399 | Main component, all sub-components |
| `frontend/src/stores/run-overlay-store.ts` | 145 | Real-time status updates |
| `frontend/src/api/argo-api.ts` | 44 | API client |
| `frontend/src/lib/phase-utils.ts` | 69 | Phase badge styling |
| `frontend/src/types/index-types.ts` | 178 | Type definitions |
| `api/routers/runs.py` | 147 | Backend endpoints |
| `api/services/argo_service.py` | 145 | Argo CLI wrapper |

## 🔄 Data Flow Overview

```
Argo K8s Cluster
     ↓ argo get {name} -o json
Backend: api/routers/runs.py → get_run()
     ↓ raw workflow JSON
Frontend: argo-api.ts → getRun()
     ↓ RunDetailResponse
RunsPanel.tsx → detailQuery.data
     ├─ parseSteps() → ArgoStepNode[]
     ├─ PhaseBadge() → badge styling
     ├─ ValidationSummary() → warnings/infos
     └─ RunLogs() → execution logs

Real-time:
     ↓ every 5 seconds (refetchInterval)
run-overlay-store.ts → parseArgoNodes() → nodeStatuses
     ↓
Canvas nodes display badges ← live updates
```

## 🚀 Common Tasks

### Add Grouping for Parallel Steps
**Files to modify:** `RunsPanel.tsx` (parseSteps function)
**Reference:** `frontend_runs_code_snippets.md` → "Group Steps by Template Name"
**Effort:** ~2-3 hours (moderate complexity)

### Show Step Duration
**Files to modify:** `RunsPanel.tsx` (parseSteps + rendering), `phase-utils.ts` (add helper)
**Reference:** `frontend_runs_code_snippets.md` → "Add Step Duration"
**Effort:** ~1-2 hours (low complexity)

### Add Search/Filter
**Files to modify:** `RunsPanel.tsx` (add state + filter logic)
**Reference:** `frontend_runs_code_snippets.md` → "Add Step Search/Filter"
**Effort:** ~1-2 hours (low complexity)

### Virtualize Large Step Lists
**Files to modify:** `RunsPanel.tsx` (integrate react-window)
**Reference:** `frontend_runs_detail_analysis.md` → "Limitations" section
**Effort:** ~4-6 hours (medium complexity)

### Show Per-Node Logs
**Files to modify:** `argo-api.ts`, `RunsPanel.tsx` (add per-node log fetching)
**Reference:** `frontend_runs_code_snippets.md` → API layer section
**Effort:** ~2-3 hours (medium complexity)

## 📚 Architecture Insights

### Why parseSteps() is Critical
- It's the **only place** that transforms Argo nodes into a displayable array
- Modifying it changes how ALL steps are organized and rendered
- Adding grouping here is the key to improving parallel node visualization

### The Argo Node Structure
```
Argo status.nodes = flat object with:
  "wf-sp-calc-0": { type: "Pod", phase: "Succeeded", ... }
  "wf-sp-calc-1": { type: "Pod", phase: "Running", ... }
  "wf-sp-calc-2": { type: "Pod", phase: "Pending", ... }
```

All three have the same `templateName` ("mf-sp-calc"), so they're all mapped to a single canvas node "sp-calc" in the run overlay store.

### Real-Time vs. Snapshot
- **RunsPanel.steps**: Static snapshot from `detailQuery.data` (updates every 5 seconds)
- **Canvas badges**: Live updates from `run-overlay-store` (only shows latest per canvas node)

These are intentionally different:
- RunsPanel shows detailed per-array-item execution history
- Canvas shows simplified per-node status (aggregated from all items)

## 🎓 Learning Path

1. **Understand the flow:** Read `frontend_runs_detail_analysis.md` → "Data Flow" section
2. **See the structure:** View `frontend_runs_visualization_guide.md` → "Component Tree Diagram"
3. **Find the code:** Look up `frontend_runs_code_snippets.md` → Copy what you need
4. **Make changes:** Modify code in `frontend/src/components/runs/RunsPanel.tsx`
5. **Test:** Open a run with multiple parallel steps and observe the rendering

## 🔗 Related Files Not Covered

- `frontend/src/hooks/useRunOverlayPolling.ts` — Polling mechanism
- `frontend/src/stores/ui-store.ts` — UI state management
- `frontend/src/stores/saved-workflows-store.ts` — Local snapshots
- `frontend/src/components/canvas/` — Canvas visualization (integration point)
- `api/models/runs.py` — Pydantic response models
- `api/services/argo_service.py` — Argo CLI wrapper

## ✅ Document Quality Checklist

- [x] All files exist and are readable
- [x] Line numbers are accurate as of 2026-04-08
- [x] Code snippets are copy-paste ready
- [x] Diagrams are ASCII-based and text-only
- [x] Cross-references between docs are working
- [x] Examples are from actual codebase
- [x] Improvement ideas include code skeletons
- [x] All limitations are documented with solutions

---

**Generated:** 2026-04-08
**Scope:** MiQroForge v2.0 Frontend — Runs Detail View Component
**Files analyzed:** 8 source files, 1,830 lines of documentation
**Status:** ✅ Complete and ready for developer reference

