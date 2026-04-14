import React, { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useWorkflowStore } from '../../stores/workflow-store'
import type { MFNodeData } from '../../stores/workflow-store'
import { useUIStore } from '../../stores/ui-store'
import { useSavedWorkflowsStore } from '../../stores/saved-workflows-store'
import { useRunOverlayStore } from '../../stores/run-overlay-store'
import { useAgentStore } from '../../stores/agent-store'
import { useProjectStore } from '../../stores/project-store'
import { useWorkflowValidation } from '../../hooks/useWorkflowValidation'
import { workflowsApi } from '../../api/workflows-api'
import { projectsApi } from '../../api/projects-api'
import {
  rfStateToWorkflowDoc,
  workflowDocToYaml,
  parseWorkflowYaml,
  workflowNodeToRF,
  connectionToRFEdge,
} from '../../lib/workflow-serializer'
import { nodesApi } from '../../api/nodes-api'
import {
  CheckCircle, AlertCircle,
  FileDown, FileUp, Trash2, Save, FolderOpen, ExternalLink, Settings, Activity, PlayCircle,
  BookOpen, Ruler, MessageSquare,
} from 'lucide-react'
import type { RightPanel } from '../../stores/ui-store'
import type { RunPhase } from '../../types/index-types'
import { phaseEmoji } from '../../lib/phase-utils'

// ─── TopBar ───────────────────────────────────────────────────────────────────

export function TopBar() {
  const navigate = useNavigate()
  const { meta, setMeta, nodes, edges, clearCanvas, loadFromNodes, setCompilingNodeIds, clearCompilingNodeIds } = useWorkflowStore()
  const {
    rightPanel, setRightPanel, filesOpen, toggleFiles,
    showNotification, runTrigger,
    setPendingRunName,
  } = useUIStore()
  const { saveWorkflow, saveRunSnapshot } = useSavedWorkflowsStore()
  const { setActiveRun } = useRunOverlayStore()
  const { validate, getYaml } = useWorkflowValidation()
  const { isOpen: chatOpen, toggleChat } = useAgentStore()
  const currentProjectMeta = useProjectStore((s) => s.currentProjectMeta)
  const currentProjectId = useProjectStore((s) => s.currentProjectId)

  const [editingName, setEditingName] = useState(false)
  const [nameVal, setNameVal] = useState(meta.name)
  const [isRunning, setIsRunning] = useState(false)

  // Argo UI URL — fetched once from the backend config endpoint
  const [argoUrl, setArgoUrl] = useState<string | null>(null)
  useEffect(() => {
    fetch('/api/v1/config')
      .then((r) => r.json())
      .then((d: { argo_ui_url?: string }) => {
        if (d.argo_ui_url) setArgoUrl(d.argo_ui_url)
      })
      .catch(() => {})
  }, [])

  const handleNameBlur = () => {
    setMeta({ name: nameVal })
    setEditingName(false)
  }

  // ── Save workflow ────────────────────────────────────────────────────────
  const handleSave = async () => {
    if (nodes.length === 0) {
      showNotification('info', 'Canvas is empty — nothing to save')
      return
    }

    // If inside a project, create a backend snapshot
    if (currentProjectId) {
      try {
        const canvas = {
          meta: JSON.parse(JSON.stringify(meta)),
          nodes: JSON.parse(JSON.stringify(nodes)),
          edges: JSON.parse(JSON.stringify(edges)),
        }
        await projectsApi.createSnapshot(currentProjectId, meta.name, canvas)
        showNotification('success', `Snapshot saved for "${meta.name}"`)
      } catch (err) {
        showNotification('error', `Snapshot failed: ${err instanceof Error ? err.message : String(err)}`)
      }
    }

    // Also save to frontend localStorage for the Saved Workflows sidebar
    saveWorkflow(meta, nodes, edges)
  }

  // ── Export MF YAML ───────────────────────────────────────────────────────
  const handleExport = () => {
    const doc = rfStateToWorkflowDoc(nodes, edges, meta)
    const yaml = workflowDocToYaml(doc)
    const blob = new Blob([yaml], { type: 'text/yaml' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${meta.name.replace(/\s+/g, '-').toLowerCase()}-mf.yaml`
    a.click()
    URL.revokeObjectURL(url)
    showNotification('success', 'Workflow exported')
  }

  // ── Import MF YAML ───────────────────────────────────────────────────────
  const handleImport = () => {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = '.yaml,.yml'
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0]
      if (!file) return
      const text = await file.text()
      try {
        const parsed = parseWorkflowYaml(text)
        setMeta(parsed.meta)

        const rfNodes = await Promise.all(
          parsed.nodes.map(async (wfNode) => {
            // Ephemeral nodes have no nodespec — build directly from YAML data
            if (wfNode.ephemeral) {
              return workflowNodeToRF(wfNode, {
                name: wfNode.id,
                version: '?',
                display_name: wfNode.id,
                description: wfNode.description ?? '',
                node_type: 'lightweight',
                category: '',
                ephemeral: true,
                ephemeral_description: wfNode.description,
                ports: wfNode.ports,
                stream_inputs: wfNode.stream_inputs as never ?? [],
                stream_outputs: wfNode.stream_outputs as never ?? [],
                onboard_inputs: [],
                onboard_params: wfNode.onboard_params ?? {},
              })
            }

            const nodeName = wfNode.node || wfNode.nodespec_name || wfNode.nodespec_path.split('/').slice(-2, -1)[0]
            try {
              const detail = await nodesApi.get(nodeName)
              const defaultParams = Object.fromEntries(
                detail.onboard_inputs
                  .filter((p) => p.default !== undefined && p.default !== null)
                  .map((p) => [p.name, p.default]),
              )
              const mergedParams = { ...defaultParams, ...wfNode.onboard_params }
              return workflowNodeToRF(
                { ...wfNode, onboard_params: mergedParams },
                {
                  name: detail.name,
                  version: detail.version,
                  display_name: detail.display_name,
                  description: detail.description,
                  node_type: detail.node_type,
                  category: detail.category,
                  software: detail.software,
                  stream_inputs: detail.stream_inputs as never,
                  stream_outputs: detail.stream_outputs as never,
                  onboard_inputs: detail.onboard_inputs.map((p) => ({
                    name: p.name,
                    display_name: p.display_name,
                    type: p.kind,
                    default: p.default,
                    description: p.description,
                    enum_values: p.allowed_values,
                    min: p.min_value,
                    max: p.max_value,
                    unit: p.unit,
                    multiple_input: p.multiple_input,
                  })) as never,
                },
              )
            } catch {
              // Fallback: use wfNode data directly (especially important for ephemeral nodes)
              const fallbackData: Record<string, unknown> = {
                name: nodeName,
                version: '?',
                display_name: wfNode.id,
                description: '',
                node_type: wfNode.ephemeral ? 'lightweight' : 'compute',
                category: '',
                stream_inputs: [],
                stream_outputs: [],
                onboard_inputs: [],
              }
              return workflowNodeToRF(wfNode, fallbackData as Partial<MFNodeData>)
            }
          }),
        )
        // Build source node outputs map for edge coloring
        const nodeOutputsMap = new Map<string, Array<{ name: string; category: string }>>()
        for (const rfNode of rfNodes) {
          const data = rfNode.data as MFNodeData
          nodeOutputsMap.set(
            rfNode.id,
            data.stream_outputs?.map((p) => ({ name: p.name, category: p.category })) ?? [],
          )
        }
        const rfEdges = parsed.connections.map((c) => {
          const sourceId = c.from.split('.')[0]
          return connectionToRFEdge(c, nodeOutputsMap.get(sourceId))
        })
        loadFromNodes(rfNodes, rfEdges)
        showNotification('success', `Imported "${parsed.meta.name}"`)
      } catch (err) {
        showNotification('error', `Import failed: ${err instanceof Error ? err.message : String(err)}`)
      }
    }
    input.click()
  }

  // ── Validate → Submit → navigate to run detail ──────────────────────────
  const handleRun = async () => {
    if (nodes.length === 0 || isRunning) return
    setIsRunning(true)

    try {
      // Step 1: Validate
      const result = await validate()
      if (!result) {
        // validate() already showed an error notification
        return
      }
      if (!result.valid) {
        // Errors block submission — user sees the error notification from validate()
        return
      }

      // Step 2: Submit (backend compiles internally — may take ~2 min for ephemeral nodes)
      const mfYaml = getYaml()
      const projectId = useProjectStore.getState().currentProjectId ?? undefined
      showNotification('info', 'Compiling and submitting workflow… (may take up to 2 min)')

      // Set compiling state on ephemeral/sweep nodes for visual feedback
      const compilingIds = nodes
        .filter((n) => n.data.ephemeral)
        .map((n) => n.id)
      setCompilingNodeIds(compilingIds)

      const resp = await workflowsApi.submit(mfYaml, projectId)

      // Persist canvas snapshot + validation warnings for the run detail view
      clearCompilingNodeIds()
      saveRunSnapshot(
        resp.workflow_name,
        meta, nodes, edges,
        result.warnings.map((w) => ({ message: w.message, node_id: w.node_id })),
        result.infos.map((i)   => ({ message: i.message,  node_id: i.node_id })),
      )
      setActiveRun(resp.workflow_name)

      // Navigate to Runs panel and open this run's detail automatically
      setPendingRunName(resp.workflow_name)
      setRightPanel('runs')

      showNotification('success', `Submitted: ${resp.workflow_name}`)
    } catch (err) {
      const errMsg = err instanceof Error ? err.message : String(err)
      showNotification('error', `Submit failed: ${errMsg}`)

      // Persist the failure as a local-only run snapshot
      const syntheticName = `compile-error-${new Date().toLocaleTimeString('en-GB').replace(/:/g, '')}`
      saveRunSnapshot(
        syntheticName,
        meta, nodes, edges,
        undefined, undefined,
        errMsg,
        true,
      )
      setPendingRunName(syntheticName)
      setRightPanel('runs')
    } finally {
      setIsRunning(false)
      clearCompilingNodeIds()
    }
  }

  // ── React to keyboard shortcut (Ctrl+Enter) ──────────────────────────────
  const lastTriggerRef = useRef(0)
  useEffect(() => {
    if (runTrigger === 0 || runTrigger === lastTriggerRef.current) return
    lastTriggerRef.current = runTrigger
    handleRun()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runTrigger])

  // ── Nav panel items ───────────────────────────────────────────────────────
  const navItems: Array<{ id: RightPanel; icon: React.ReactNode; label: string }> = [
    { id: 'runs',      icon: <Activity size={14} />, label: 'Runs' },
    { id: 'settings',  icon: <Settings size={14} />, label: 'Settings' },
  ]

  return (
    <div className="flex items-center h-10 px-3 bg-mf-panel border-b border-mf-border gap-3 flex-shrink-0">
      {/* Logo — click to go back to gallery */}
      <button
        onClick={() => navigate('/')}
        className="flex items-center gap-1.5 flex-shrink-0 hover:opacity-80 transition-opacity"
        title="Back to Project Gallery"
      >
        <img src="/logo.png" alt="MiQroForge" className="h-6 w-auto" />
        <span className="text-sm font-bold text-mf-text-primary tracking-tight">MiQroForge</span>
        <span className="text-[10px] text-mf-text-muted border border-mf-border rounded px-1">2.0</span>
      </button>

      <div className="w-px h-5 bg-mf-border" />

      {/* Project / Workflow breadcrumb */}
      {currentProjectMeta && (
        <span className="text-xs text-mf-text-muted truncate max-w-32 flex-shrink-0">
          {currentProjectMeta.name}
        </span>
      )}
      {currentProjectMeta && (
        <span className="text-xs text-mf-text-muted">/</span>
      )}

      {/* Workflow name (editable) */}
      {editingName ? (
        <input
          autoFocus
          value={nameVal}
          onChange={(e) => setNameVal(e.target.value)}
          onBlur={handleNameBlur}
          onKeyDown={(e) => e.key === 'Enter' && handleNameBlur()}
          className="text-sm text-mf-text-primary bg-mf-input border border-mf-border rounded px-2 py-0.5 focus:outline-none focus:border-blue-500 min-w-0 max-w-48"
        />
      ) : (
        <button
          onClick={() => { setEditingName(true); setNameVal(meta.name) }}
          className="text-sm text-mf-text-secondary hover:text-mf-text-primary truncate max-w-48"
          title="Click to rename"
        >
          {meta.name}
        </button>
      )}

      <div className="flex-1" />

      {/* Files toggle (left panel) */}
      <button
        onClick={toggleFiles}
        className={`flex items-center gap-1 px-2 py-1 text-xs rounded transition-colors ${
          filesOpen
            ? 'bg-blue-600 text-white'
            : 'text-mf-text-muted hover:text-mf-text-primary hover:bg-mf-hover'
        }`}
        title="Toggle Files panel"
      >
        <FolderOpen size={14} /> Files
      </button>

      {/* AI Chat toggle */}
      <button
        onClick={toggleChat}
        className={`flex items-center gap-1 px-2 py-1 text-xs rounded transition-colors ${
          chatOpen
            ? 'bg-purple-700 text-white'
            : 'text-mf-text-muted hover:text-mf-text-primary hover:bg-mf-hover'
        }`}
        title="Toggle AI Assistant (Phase 2)"
      >
        <MessageSquare size={14} /> Chat
      </button>

      <div className="w-px h-5 bg-mf-border" />

      {/* File operations */}
      <div className="flex items-center gap-1">
        <button
          onClick={handleSave}
          disabled={nodes.length === 0}
          className="flex items-center gap-1 px-2 py-1 text-xs text-blue-400 hover:text-blue-200 hover:bg-mf-hover rounded transition-colors disabled:opacity-40 font-medium"
          title="Save workflow"
        >
          <Save size={13} /> Save
        </button>
        <div className="w-px h-4 bg-mf-border" />
        <button
          onClick={handleImport}
          className="flex items-center gap-1 px-2 py-1 text-xs text-mf-text-muted hover:text-mf-text-primary hover:bg-mf-hover rounded transition-colors"
          title="Import MF YAML"
        >
          <FileUp size={13} /> Import
        </button>
        <button
          onClick={handleExport}
          disabled={nodes.length === 0}
          className="flex items-center gap-1 px-2 py-1 text-xs text-mf-text-muted hover:text-mf-text-primary hover:bg-mf-hover rounded transition-colors disabled:opacity-40"
          title="Export MF YAML"
        >
          <FileDown size={13} /> Export
        </button>
        <button
          onClick={() => { if (confirm('Clear canvas?')) clearCanvas() }}
          disabled={nodes.length === 0}
          className="flex items-center gap-1 px-2 py-1 text-xs text-mf-text-muted hover:text-red-400 hover:bg-mf-hover rounded transition-colors disabled:opacity-40"
          title="Clear canvas"
        >
          <Trash2 size={13} />
        </button>
      </div>

      <div className="w-px h-5 bg-mf-border" />

      {/* ── One-click Run button ─────────────────────────────────────────── */}
      <button
        onClick={handleRun}
        disabled={nodes.length === 0 || isRunning}
        className="flex items-center gap-1.5 px-3 py-1 text-xs font-semibold text-white bg-green-700 hover:bg-green-600 disabled:opacity-40 disabled:cursor-not-allowed rounded transition-colors"
        title="Validate and submit workflow (Ctrl+Enter)"
      >
        {isRunning
          ? <span className="inline-block w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
          : <PlayCircle size={13} />
        }
        {isRunning ? 'Running…' : 'Run'}
      </button>

      <div className="w-px h-5 bg-mf-border" />

      {/* Nav panels */}
      <div className="flex items-center gap-0.5">
        {navItems.map((item) => (
          <button
            key={String(item.id)}
            onClick={() => setRightPanel(rightPanel === item.id ? null : item.id)}
            className={`flex items-center gap-1 px-2 py-1 text-xs rounded transition-colors ${
              rightPanel === item.id
                ? 'bg-blue-600 text-white'
                : 'text-mf-text-muted hover:text-mf-text-primary hover:bg-mf-hover'
            }`}
          >
            {item.icon} {item.label}
          </button>
        ))}
        <div className="w-px h-4 bg-mf-border mx-0.5" />
        <RefMenu />
      </div>

      {/* Argo UI link — only shown when backend provides the URL */}
      {argoUrl && (
        <>
          <div className="w-px h-5 bg-mf-border" />
          <a
            href={argoUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 px-2 py-1 text-xs text-mf-text-muted hover:text-blue-300 hover:bg-mf-hover rounded transition-colors"
            title={`Open Argo Workflow UI (${argoUrl})`}
          >
            <ExternalLink size={12} />
            Argo UI
          </a>
        </>
      )}
    </div>
  )
}

// ─── Ref dropdown menu ───────────────────────────────────────────────────────

const REF_PAGES = [
  { path: '/ref/units', icon: <Ruler size={13} />, label: 'Units Reference' },
]

function RefMenu() {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  // Close on outside click
  useEffect(() => {
    if (!open) return
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className={`flex items-center gap-1 px-2 py-1 text-xs rounded transition-colors ${
          open
            ? 'bg-blue-600 text-white'
            : 'text-mf-text-muted hover:text-mf-text-primary hover:bg-mf-hover'
        }`}
        title="Reference pages (open in new tab)"
      >
        <BookOpen size={14} /> Ref
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-1 w-48 bg-mf-panel border border-mf-border rounded-md shadow-lg z-50 py-1">
          {REF_PAGES.map((page) => (
            <a
              key={page.path}
              href={page.path}
              target="_blank"
              rel="noopener noreferrer"
              onClick={() => setOpen(false)}
              className="flex items-center gap-2 px-3 py-1.5 text-xs text-mf-text-secondary hover:text-mf-text-primary hover:bg-mf-hover transition-colors"
            >
              {page.icon}
              {page.label}
              <ExternalLink size={10} className="ml-auto text-mf-text-muted" />
            </a>
          ))}
        </div>
      )}
    </div>
  )
}

// ─── StatusBar ────────────────────────────────────────────────────────────────

export function StatusBar() {
  const { nodes, edges, validationResult } = useWorkflowStore()
  const { notification, clearNotification } = useUIStore()
  const { activeRunName, workflowPhase, clearOverlay } = useRunOverlayStore()

  React.useEffect(() => {
    if (!notification) return
    if (notification.type !== 'success') return
    const t = setTimeout(clearNotification, 4000)
    return () => clearTimeout(t)
  }, [notification, clearNotification])

  const runPhaseEmoji = workflowPhase ? phaseEmoji(workflowPhase as RunPhase) : '⏳'

  return (
    <div className="h-6 flex items-center px-3 bg-mf-panel border-t border-mf-border text-[11px] text-mf-text-muted gap-4 flex-shrink-0">
      <span>{nodes.length} node{nodes.length !== 1 ? 's' : ''}</span>
      <span>{edges.length} connection{edges.length !== 1 ? 's' : ''}</span>

      {validationResult && (
        <span className={validationResult.valid ? 'text-green-500' : 'text-red-500'}>
          {validationResult.valid ? '✓ Valid' : `✗ ${validationResult.errors.length} error(s)`}
        </span>
      )}

      {/* Active run indicator */}
      {activeRunName && (
        <span className="flex items-center gap-1.5 text-[11px]">
          <span className={
            workflowPhase === 'Succeeded' ? 'text-green-400' :
            workflowPhase === 'PartialSuccess' ? 'text-orange-300' :
            workflowPhase === 'Failed' || workflowPhase === 'Error' ? 'text-red-400' :
            'text-blue-400'
          }>
            {runPhaseEmoji} {activeRunName}
            {workflowPhase && ` (${workflowPhase})`}
          </span>
          <button
            onClick={clearOverlay}
            className="text-mf-text-muted hover:text-mf-text-primary ml-0.5"
            title="Clear run overlay"
          >
            ✕
          </button>
        </span>
      )}

      <div className="flex-1" />

      {notification && (
        <span
          className={`flex items-center gap-1 cursor-pointer max-w-xs truncate ${
            notification.type === 'success' ? 'text-green-400' :
            notification.type === 'error' ? 'text-red-400' :
            'text-blue-400'
          }`}
          title={notification.message}
          onClick={clearNotification}
        >
          {notification.type === 'success' && <CheckCircle size={11} className="flex-shrink-0" />}
          {notification.type === 'error' && <AlertCircle size={11} className="flex-shrink-0" />}
          <span className="truncate">{notification.message}</span>
          {notification.type !== 'success' && (
            <span className="flex-shrink-0 ml-0.5 text-mf-text-muted hover:text-mf-text-secondary">✕</span>
          )}
        </span>
      )}
    </div>
  )
}
