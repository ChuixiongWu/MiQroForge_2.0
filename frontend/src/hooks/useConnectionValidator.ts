import { useMemo } from 'react'
import { useWorkflowStore } from '../stores/workflow-store'
import { buildPortLookup, isValidRFConnection } from '../lib/connection-rules'
import type { StreamPort } from '../types/nodespec'

export function useConnectionValidator() {
  const nodes = useWorkflowStore((s) => s.nodes)

  const portLookup = useMemo(
    () =>
      buildPortLookup(
        nodes.map((n) => ({
          id: n.id,
          data: {
            stream_inputs: (n.data.stream_inputs ?? []) as StreamPort[],
            stream_outputs: (n.data.stream_outputs ?? []) as StreamPort[],
            ephemeral: n.data.ephemeral,
            prefab: n.data.prefab,
            ports: n.data.ports as { inputs?: Array<{ name: string; type: string }> | number; outputs?: Array<{ name: string; type: string }> | number } | undefined,
          },
        })),
      ),
    [nodes],
  )

  const isValidConnection = useMemo(
    () =>
      (connection: {
        source: string
        sourceHandle: string | null
        target: string
        targetHandle: string | null
      }) =>
        isValidRFConnection(connection, portLookup),
    [portLookup],
  )

  return { isValidConnection, portLookup }
}
