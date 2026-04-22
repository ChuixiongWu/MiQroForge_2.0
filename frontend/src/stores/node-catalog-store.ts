import { create } from 'zustand'
import type { NodeSummaryResponse } from '../types/index-types'
import { semanticLabel } from '../lib/semantic-labels'
import { getShowDeprecated, onGlobalPrefsChange } from '../lib/node-preferences'

// ─── Semantic group (pure, exported for Palette) ──────────────────────────────

export interface SubGroup {
  algorithm: string             // "DFT", "HF", "MP2", etc.
  label: string                 // display label
  nodes: NodeSummaryResponse[]
}

export interface SemanticGroup {
  semanticType: string          // kebab-case key or '__other__'
  label: string                 // human-readable name
  nodes: NodeSummaryResponse[]
  subGroups?: SubGroup[]        // optional algorithm sub-grouping
}

/**
 * Extract algorithm key from a node name or its methods tags.
 * Priority: methods[0] → name suffix after software prefix.
 * e.g. "orca-dft" → "DFT", "gaussian-hf" → "HF"
 */
function extractAlgorithm(node: NodeSummaryResponse): string {
  if (node.methods && node.methods.length > 0) {
    return node.methods[0].toUpperCase()
  }
  // Fallback: split name by '-', take last segment
  const parts = node.name.split('-')
  return (parts[parts.length - 1] ?? 'other').toUpperCase()
}

function buildSubGroups(nodes: NodeSummaryResponse[]): SubGroup[] {
  const algoMap: Record<string, NodeSummaryResponse[]> = {}
  for (const n of nodes) {
    const algo = extractAlgorithm(n)
    if (!algoMap[algo]) algoMap[algo] = []
    algoMap[algo].push(n)
  }
  return Object.keys(algoMap)
    .sort()
    .map((algo) => ({
      algorithm: algo,
      label: algo,
      nodes: algoMap[algo],
    }))
}

export function buildSemanticGroups(nodes: NodeSummaryResponse[]): SemanticGroup[] {
  const map: Record<string, NodeSummaryResponse[]> = {}
  for (const n of nodes) {
    const key = n.semantic_type ?? '__other__'
    if (!map[key]) map[key] = []
    map[key].push(n)
  }
  return Object.keys(map)
    .sort((a, b) => {
      if (a === '__other__') return 1
      if (b === '__other__') return -1
      return a.localeCompare(b)
    })
    .map((key) => {
      const groupNodes = map[key]
      // Sub-group if >5 nodes and all have methods tags
      const shouldSubGroup =
        groupNodes.length > 5 &&
        groupNodes.every((n) => n.methods && n.methods.length > 0)
      return {
        semanticType: key,
        label: key === '__other__' ? 'Other' : semanticLabel(key),
        nodes: groupNodes,
        subGroups: shouldSubGroup ? buildSubGroups(groupNodes) : undefined,
      }
    })
}

// ─── Store ────────────────────────────────────────────────────────────────────

interface NodeCatalogState {
  nodes: NodeSummaryResponse[]
  isLoading: boolean
  error: string | null
  searchQuery: string
  filteredNodes: NodeSummaryResponse[]
  expandedTypes: Set<string>

  // Actions
  setNodes: (nodes: NodeSummaryResponse[]) => void
  setLoading: (v: boolean) => void
  setError: (msg: string | null) => void
  setSearchQuery: (q: string) => void
  toggleExpanded: (semanticType: string) => void
  collapseAll: () => void
}

function filterNodes(nodes: NodeSummaryResponse[], query: string): NodeSummaryResponse[] {
  // Filter deprecated first
  let result = getShowDeprecated() ? nodes : nodes.filter((n) => !n.deprecated)
  if (!query.trim()) return result
  const lower = query.toLowerCase()
  return result.filter(
    (n) =>
      n.name.toLowerCase().includes(lower) ||
      n.display_name.toLowerCase().includes(lower) ||
      n.description.toLowerCase().includes(lower) ||
      n.software?.toLowerCase().includes(lower) ||
      n.semantic_type?.toLowerCase().includes(lower) ||
      n.keywords.some((k) => k.toLowerCase().includes(lower)) ||
      n.category.toLowerCase().includes(lower),
  )
}

export const useNodeCatalogStore = create<NodeCatalogState>((set, get) => ({
  nodes: [],
  isLoading: false,
  error: null,
  searchQuery: '',
  filteredNodes: [],
  expandedTypes: new Set<string>(),

  setNodes: (nodes) =>
    set({ nodes, filteredNodes: filterNodes(nodes, get().searchQuery) }),

  setLoading: (v) => set({ isLoading: v }),
  setError: (msg) => set({ error: msg }),

  setSearchQuery: (q) => {
    const filtered = filterNodes(get().nodes, q)
    // Auto-expand groups that contain matching nodes when query is non-empty
    const expanded = new Set<string>()
    if (q.trim()) {
      for (const n of filtered) {
        expanded.add(n.semantic_type ?? '__other__')
      }
    }
    set({ searchQuery: q, filteredNodes: filtered, expandedTypes: expanded })
  },

  toggleExpanded: (semanticType) =>
    set((s) => {
      const next = new Set(s.expandedTypes)
      if (next.has(semanticType)) {
        next.delete(semanticType)
      } else {
        next.add(semanticType)
      }
      return { expandedTypes: next }
    }),

  collapseAll: () => set({ expandedTypes: new Set<string>() }),
}))

// Re-filter when global prefs change (e.g. showDeprecated toggle)
onGlobalPrefsChange(() => {
  const { nodes, searchQuery } = useNodeCatalogStore.getState()
  useNodeCatalogStore.setState({ filteredNodes: filterNodes(nodes, searchQuery) })
})
