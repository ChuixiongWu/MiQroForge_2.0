import { create } from 'zustand'
import type { NodeSummaryResponse } from '../types/index-types'
import { semanticLabel } from '../lib/semantic-labels'

// ─── Semantic group (pure, exported for Palette) ──────────────────────────────

export interface SemanticGroup {
  semanticType: string          // kebab-case key or '__other__'
  label: string                 // human-readable name
  nodes: NodeSummaryResponse[]
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
    .map((key) => ({
      semanticType: key,
      label: key === '__other__' ? 'Other' : semanticLabel(key),
      nodes: map[key],
    }))
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
  if (!query.trim()) return nodes
  const lower = query.toLowerCase()
  return nodes.filter(
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
