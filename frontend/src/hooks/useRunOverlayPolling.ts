import { useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { argoApi } from '../api/argo-api'
import { useRunOverlayStore } from '../stores/run-overlay-store'

const TERMINAL = new Set(['Succeeded', 'Failed', 'Error', 'PartialSuccess'])

/**
 * Polls the Argo API for the active run and updates the run overlay store.
 * Must be mounted at the App level so polling persists across panel changes.
 *
 * On reaching a terminal state, saves output parameters to runs/{name}/outputs.json
 * via the backend save-outputs endpoint (fire-and-forget).
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

      // Save outputs to runs/ when run first reaches a terminal state
      if (TERMINAL.has(detail.phase) && savedRef.current !== activeRunName) {
        savedRef.current = activeRunName
        argoApi.saveOutputs(activeRunName!).catch(() => {})
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
