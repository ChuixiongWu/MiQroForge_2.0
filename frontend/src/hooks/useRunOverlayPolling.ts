import { useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { argoApi } from '../api/argo-api'
import { useRunOverlayStore } from '../stores/run-overlay-store'
import { useProjectStore } from '../stores/project-store'
import { useWorkflowStore } from '../stores/workflow-store'

const TERMINAL = new Set(['Succeeded', 'Failed', 'Error', 'PartialSuccess'])

/**
 * Polls the Argo API for the active run and updates the run overlay store.
 * Must be mounted at the App level so polling persists across panel changes.
 *
 * On reaching a terminal state, saves output parameters to runs/{name}/outputs.json
 * via the backend save-outputs endpoint (fire-and-forget), along with the current
 * canvas state (afterrun_canvas.json).
 */
export function useRunOverlayPolling() {
  const activeRunName = useRunOverlayStore((s) => s.activeRunName)
  const updateFromArgo = useRunOverlayStore((s) => s.updateFromArgo)
  // Track whether we've already called save-outputs for the current run
  const savedRef = useRef<string | null>(null)

  useQuery({
    queryKey: ['run-overlay', activeRunName],
    queryFn: async () => {
      const detail = await argoApi.getRun(activeRunName!)
      updateFromArgo(detail.raw)

      // Save outputs + canvas to runs/ when run first reaches a terminal state
      if (TERMINAL.has(detail.phase) && savedRef.current !== activeRunName) {
        savedRef.current = activeRunName
        const projectId = useProjectStore.getState().currentProjectId ?? undefined
        const { meta, nodes, edges } = useWorkflowStore.getState()
        const { nodeStatuses, workflowPhase } = useRunOverlayStore.getState()
        const canvas = { meta, nodes, edges, nodeStatuses, workflowPhase }
        argoApi.saveOutputs(activeRunName!, projectId, canvas).then((result) => {
          // Update nodeStatuses with full error text from outputs.json
          if (result.error_texts) {
            const current = useRunOverlayStore.getState().nodeStatuses
            let changed = false
            const merged = { ...current }
            for (const [canvasId, errorText] of Object.entries(result.error_texts)) {
              if (merged[canvasId] && merged[canvasId].error !== errorText) {
                merged[canvasId] = { ...merged[canvasId], error: errorText }
                changed = true
              }
            }
            if (changed) {
              useRunOverlayStore.setState({ nodeStatuses: merged })
              // Re-save afterrun_canvas with updated error text
              const updatedCanvas = {
                ...canvas,
                nodeStatuses: useRunOverlayStore.getState().nodeStatuses,
              }
              argoApi.saveOutputs(activeRunName!, projectId, updatedCanvas).catch(() => {})
            }
          }
        }).catch(() => {})
      }

      return detail
    },
    enabled: !!activeRunName,
    refetchInterval: (query) => {
      const phase = query.state.data?.phase
      if (phase && TERMINAL.has(phase)) return false
      return 3000   // poll every 3 s while running
    },
  })
}
