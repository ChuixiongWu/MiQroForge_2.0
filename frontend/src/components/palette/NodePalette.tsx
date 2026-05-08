import React, { useCallback } from 'react'
import { Search, RefreshCw, ChevronLeft, ChevronRight, ChevronDown, Zap, Sparkles } from 'lucide-react'
import { useNodeCatalog } from '../../hooks/useNodeCatalog'
import { useNodeCatalogStore, buildSemanticGroups, type SubGroup } from '../../stores/node-catalog-store'
import { useUIStore } from '../../stores/ui-store'
import { semanticIcon } from '../../lib/semantic-labels'
import type { PickerOption } from '../../lib/semantic-labels'
import type { NodeSummaryResponse } from '../../types/index-types'

// ─── Ephemeral type card (fixed, draggable) ──────────────────────────────────

function EphemeralTypeCard() {
  const onDragStart = useCallback((e: React.DragEvent) => {
    e.dataTransfer.setData('application/mf-ephemeral', 'true')
    e.dataTransfer.effectAllowed = 'copy'
  }, [])

  return (
    <div className="mx-2 mb-2">
      <div
        draggable
        onDragStart={onDragStart}
        className="bg-mf-card border border-orange-700/40 rounded-lg shadow cursor-grab active:cursor-grabbing hover:border-orange-500/60 transition-colors select-none"
      >
        <div className="px-2.5 py-2 bg-orange-900/20 rounded-lg flex items-start gap-1.5">
          <Zap size={14} className="text-orange-400 mt-0.5 flex-shrink-0" />
          <div className="min-w-0">
            <div className="text-xs font-semibold text-orange-200 truncate leading-tight">
              Ephemeral Node
            </div>
            <div className="text-[10px] text-orange-500/80">
              temporary · drag to create
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// ─── Node Generator type card (fixed, draggable) ─────────────────────────────

function NodeGeneratorTypeCard() {
  const onDragStart = useCallback((e: React.DragEvent) => {
    e.dataTransfer.setData('application/mf-node-gen', 'true')
    e.dataTransfer.effectAllowed = 'copy'
  }, [])

  return (
    <div className="mx-2 mb-2">
      <div
        draggable
        onDragStart={onDragStart}
        className="bg-mf-card border border-purple-700/40 rounded-lg shadow cursor-grab active:cursor-grabbing hover:border-purple-500/60 transition-colors select-none"
      >
        <div className="px-2.5 py-2 bg-purple-900/20 rounded-lg flex items-start gap-1.5">
          <Sparkles size={14} className="text-purple-400 mt-0.5 flex-shrink-0" />
          <div className="min-w-0">
            <div className="text-xs font-semibold text-purple-200 truncate leading-tight">
              Generate Node
            </div>
            <div className="text-[10px] text-purple-500/80">
              AI-assisted · drag to create
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// ─── Software row (secondary-menu item, draggable with node-name protocol) ────

function SoftwareRow({ node }: { node: NodeSummaryResponse }) {
  const onDragStart = useCallback(
    (e: React.DragEvent) => {
      e.stopPropagation()
      e.dataTransfer.setData('application/mf-node-name', node.name)
      e.dataTransfer.effectAllowed = 'copy'
    },
    [node.name],
  )

  return (
    <div
      draggable
      onDragStart={onDragStart}
      className="flex items-center justify-between px-2.5 py-1.5 hover:bg-mf-hover cursor-grab active:cursor-grabbing transition-colors select-none group"
      title={`Drag to place ${node.name}`}
    >
      <span className="text-xs font-medium text-blue-400 group-hover:text-blue-300 truncate">
        {node.software ?? node.display_name}
      </span>
      <span className="text-[10px] text-mf-text-muted font-mono ml-2 shrink-0">
        {node.name}
      </span>
    </div>
  )
}

// ─── Sub-group row (algorithm level) ─────────────────────────────────────────

interface SubGroupRowProps {
  subGroup: SubGroup
  expanded: boolean
  onToggle: () => void
}

function SubGroupRow({ subGroup, expanded, onToggle }: SubGroupRowProps) {
  return (
    <div>
      <div
        onClick={onToggle}
        className="flex items-center justify-between px-2.5 py-1.5 hover:bg-mf-hover cursor-pointer transition-colors select-none"
      >
        <div className="flex items-center gap-1.5 min-w-0">
          <span className="text-mf-text-muted">
            {expanded ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
          </span>
          <span className="text-xs font-medium text-mf-text-secondary truncate">
            {subGroup.label}
          </span>
        </div>
        <span className="text-[10px] text-mf-text-muted">
          {subGroup.nodes.length} impl{subGroup.nodes.length !== 1 ? 's' : ''}
        </span>
      </div>
      {expanded && (
        <div className="ml-3">
          {subGroup.nodes.map((n) => (
            <SoftwareRow key={n.name} node={n} />
          ))}
        </div>
      )}
    </div>
  )
}

// ─── Semantic type "node card" in palette ─────────────────────────────────────

interface SemanticTypeCardProps {
  semanticType: string
  label: string
  nodes: NodeSummaryResponse[]
  subGroups?: SubGroup[]
  expanded: boolean
  onToggle: () => void
}

function SemanticTypeCard({ semanticType, label, nodes, subGroups, expanded, onToggle }: SemanticTypeCardProps) {
  const icon = semanticIcon(semanticType)
  const [expandedSubs, setExpandedSubs] = React.useState<Set<string>>(new Set())

  const toggleSub = React.useCallback((algo: string) => {
    setExpandedSubs((prev) => {
      const next = new Set(prev)
      if (next.has(algo)) next.delete(algo)
      else next.add(algo)
      return next
    })
  }, [])

  const onDragStart = useCallback(
    (e: React.DragEvent) => {
      const options: PickerOption[] = nodes.map((n) => ({
        nodeName: n.name,
        software: n.software ?? null,
        label: n.display_name,
        methods: n.methods,
      }))
      e.dataTransfer.setData('application/mf-semantic-type', semanticType)
      e.dataTransfer.setData('application/mf-node-implementations', JSON.stringify(options))
      e.dataTransfer.effectAllowed = 'copy'
    },
    [semanticType, nodes],
  )

  return (
    <div className="mx-2 mb-2">
      <div
        draggable
        onDragStart={onDragStart}
        className="bg-mf-card border border-mf-border rounded-lg shadow cursor-grab active:cursor-grabbing hover:border-mf-hover transition-colors select-none"
      >
        {/* Card header — mimics MFNode header */}
        <div
          onClick={onToggle}
          className="px-2.5 py-2 bg-mf-hover/50 rounded-t-lg flex items-center justify-between gap-1 cursor-pointer hover:bg-mf-hover/70 transition-colors"
          style={{ borderRadius: expanded ? '0.5rem 0.5rem 0 0' : '0.5rem' }}
        >
          <div className="flex items-start gap-1.5 min-w-0">
            <span className="text-sm leading-none mt-0.5">{icon}</span>
            <div className="min-w-0">
              <div className="text-xs font-semibold text-mf-text-primary truncate leading-tight">
                {label}
              </div>
              <div className="text-[10px] text-mf-text-muted font-mono">
                {nodes.length} impl{nodes.length !== 1 ? 's' : ''}
              </div>
            </div>
          </div>
          <span className="text-mf-text-muted flex-shrink-0">
            {expanded
              ? <ChevronDown size={11} />
              : <ChevronRight size={11} />
            }
          </span>
        </div>

        {/* Expanded: sub-groups or flat list */}
        {expanded && (
          <div className="border-t border-mf-border/50 rounded-b-lg overflow-hidden">
            {subGroups ? (
              subGroups.map((sg) => (
                <SubGroupRow
                  key={sg.algorithm}
                  subGroup={sg}
                  expanded={expandedSubs.has(sg.algorithm)}
                  onToggle={() => toggleSub(sg.algorithm)}
                />
              ))
            ) : (
              nodes.map((n) => (
                <SoftwareRow key={n.name} node={n} />
              ))
            )}
          </div>
        )}
      </div>
    </div>
  )
}

// ─── NodePalette ──────────────────────────────────────────────────────────────

export function NodePalette() {
  const { isLoading, refetch } = useNodeCatalog()
  const { filteredNodes, searchQuery, setSearchQuery, expandedTypes, toggleExpanded } = useNodeCatalogStore()
  const { paletteCollapsed, togglePalette } = useUIStore()

  const groups = buildSemanticGroups(filteredNodes)

  if (paletteCollapsed) {
    return (
      <div className="flex flex-col items-center py-2 bg-mf-panel h-full">
        <button
          onClick={togglePalette}
          className="text-mf-text-muted hover:text-mf-text-primary p-1"
          title="Expand palette"
        >
          <ChevronRight size={16} />
        </button>
      </div>
    )
  }

  return (
    <div className="flex flex-col bg-mf-panel h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-mf-border">
        <span className="text-xs font-semibold text-mf-text-secondary uppercase tracking-wide">Nodes</span>
        <div className="flex gap-1 items-center">
          <button
            onClick={() => refetch()}
            className="text-mf-text-muted hover:text-mf-text-primary p-0.5"
            title="Refresh node catalog"
            disabled={isLoading}
          >
            <RefreshCw size={13} className={isLoading ? 'animate-spin' : ''} />
          </button>
          <button
            onClick={togglePalette}
            className="text-mf-text-muted hover:text-mf-text-primary p-0.5"
            title="Collapse palette"
          >
            <ChevronLeft size={13} />
          </button>
        </div>
      </div>

      {/* Search */}
      <div className="px-2 py-1.5 border-b border-mf-border">
        <div className="relative">
          <Search size={11} className="absolute left-2 top-1/2 -translate-y-1/2 text-mf-text-muted" />
          <input
            type="text"
            placeholder="Search nodes..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-6 pr-2 py-1 bg-mf-input border border-mf-border rounded text-xs text-mf-text-primary placeholder-mf-text-muted focus:outline-none focus:border-gray-400"
          />
        </div>
      </div>

      {/* Semantic node cards */}
      <div className="flex-1 overflow-y-auto mf-scroll py-2">
        {/* Ephemeral node card — always shown */}
        <EphemeralTypeCard />

        {/* Node Generator card — always shown */}
        <NodeGeneratorTypeCard />

        {isLoading && (
          <div className="px-3 py-4 text-xs text-mf-text-muted text-center">Loading nodes…</div>
        )}

        {!isLoading && filteredNodes.length === 0 && (
          <div className="px-3 py-4 text-xs text-mf-text-muted text-center">
            {searchQuery ? 'No nodes match your search.' : 'No nodes found. Run mf2 nodes reindex.'}
          </div>
        )}

        {!isLoading && groups.map((g) => (
          <SemanticTypeCard
            key={g.semanticType}
            semanticType={g.semanticType}
            label={g.label}
            nodes={g.nodes}
            subGroups={g.subGroups}
            expanded={expandedTypes.has(g.semanticType)}
            onToggle={() => toggleExpanded(g.semanticType)}
          />
        ))}
      </div>

      {/* Footer hint */}
      <div className="px-3 py-1.5 border-t border-mf-border text-[10px] text-mf-text-muted">
        Drag to canvas · Click to select software
      </div>
    </div>
  )
}
