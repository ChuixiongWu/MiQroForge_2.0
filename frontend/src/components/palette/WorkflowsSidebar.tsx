import { useCallback } from 'react'
import { Workflow, Trash2, FolderOpen } from 'lucide-react'
import { useSavedWorkflowsStore, snapshotToRF } from '../../stores/saved-workflows-store'
import { useWorkflowStore } from '../../stores/workflow-store'
import { useUIStore } from '../../stores/ui-store'
import { useRunOverlayStore } from '../../stores/run-overlay-store'

// ─── WorkflowsSidebar ─────────────────────────────────────────────────────────

export function WorkflowsSidebar() {
  const { savedWorkflows, deleteWorkflow } = useSavedWorkflowsStore()
  const { loadFromNodes, setMeta } = useWorkflowStore()
  const { showNotification, selectNode } = useUIStore()
  const { clearOverlay } = useRunOverlayStore()

  const handleLoad = useCallback(
    (id: string) => {
      const wf = useSavedWorkflowsStore.getState().savedWorkflows.find((w) => w.id === id)
      if (!wf) return
      const { meta, nodes, edges } = snapshotToRF(wf.snapshot)
      setMeta(meta)
      loadFromNodes(nodes, edges)
      selectNode(null)
      // Clear any active run overlay so the restored canvas shows the clean
      // pre-run design, not stale phase badges / outputs from a previous run
      clearOverlay()
      showNotification('success', `Loaded "${wf.name}"`)
    },
    [loadFromNodes, setMeta, selectNode, showNotification, clearOverlay],
  )

  const handleDelete = useCallback(
    (id: string, name: string, e: React.MouseEvent) => {
      e.stopPropagation()
      if (!confirm(`Delete saved workflow "${name}"?`)) return
      deleteWorkflow(id)
    },
    [deleteWorkflow],
  )

  return (
    <div className="border-t border-mf-border flex-shrink-0 flex flex-col" style={{ maxHeight: 220 }}>
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-1.5 bg-mf-panel">
        <div className="flex items-center gap-1.5">
          <Workflow size={11} className="text-mf-text-muted" />
          <span className="text-[10px] font-semibold text-mf-text-muted uppercase tracking-wider">
            Saved Workflows
          </span>
        </div>
        <span className="text-[10px] text-mf-text-muted">{savedWorkflows.length}</span>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto mf-scroll bg-mf-panel/60">
        {savedWorkflows.length === 0 ? (
          <p className="px-3 py-3 text-[10px] text-mf-text-muted text-center">
            No saved workflows.<br />Click Save in the toolbar.
          </p>
        ) : (
          <div className="divide-y divide-mf-border/50">
            {savedWorkflows.map((wf) => (
              <button
                key={wf.id}
                onClick={() => handleLoad(wf.id)}
                className="w-full text-left px-3 py-1.5 hover:bg-mf-hover transition-colors flex items-center justify-between gap-1 group"
              >
                <div className="min-w-0">
                  <div className="text-xs text-mf-text-secondary truncate flex items-center gap-1">
                    <FolderOpen size={10} className="text-mf-text-muted flex-shrink-0" />
                    {wf.name}
                  </div>
                  <div className="text-[9px] text-mf-text-muted font-mono">
                    {wf.savedAt.slice(0, 16).replace('T', ' ')}
                  </div>
                </div>
                <button
                  onClick={(e) => handleDelete(wf.id, wf.name, e)}
                  className="opacity-0 group-hover:opacity-100 text-mf-text-muted hover:text-red-400 transition-all flex-shrink-0 p-0.5"
                  title="Delete saved workflow"
                >
                  <Trash2 size={11} />
                </button>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
