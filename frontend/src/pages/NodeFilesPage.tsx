import { useState, useEffect, useCallback } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Save, X, RefreshCw, ChevronDown, ChevronRight } from 'lucide-react'
import { nodeFilesApi } from '../api/nodes-api'
import type { DirectoryEntry } from '../api/files-api'

import '../stores/settings-store'

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

// ─── Tree helpers ──────────────────────────────────────────────────────────────

interface TreeNode {
  name: string
  path: string
  isDir: boolean
  sizeBytes: number
  children: TreeNode[]
}

function buildTree(entries: DirectoryEntry[]): TreeNode[] {
  const root: TreeNode[] = []
  const dirMap = new Map<string, TreeNode>()

  for (const e of entries) {
    const parts = e.path.split('/')
    const node: TreeNode = { name: e.name, path: e.path, isDir: e.is_dir, sizeBytes: e.size_bytes, children: [] }

    if (parts.length === 1) {
      root.push(node)
    } else {
      const parentPath = parts.slice(0, -1).join('/')
      dirMap.get(parentPath)?.children.push(node) || root.push(node)
    }
    if (e.is_dir) dirMap.set(e.path, node)
  }

  const sortNodes = (nodes: TreeNode[]) => {
    nodes.sort((a, b) => a.isDir !== b.isDir ? (a.isDir ? -1 : 1) : a.name.localeCompare(b.name))
    for (const n of nodes) sortNodes(n.children)
  }
  sortNodes(root)
  return root
}

// ─── Tree row ─────────────────────────────────────────────────────────────────

function TreeRow({
  node, depth, editingPath, onEdit,
}: {
  node: TreeNode; depth: number; editingPath: string | null
  onEdit: (node: TreeNode) => void
}) {
  const [expanded, setExpanded] = useState(depth < 1)
  const hasChildren = node.isDir && node.children.length > 0
  const isSelected = editingPath === node.path

  return (
    <>
      <div
        onClick={() => {
          if (node.isDir && hasChildren) setExpanded(!expanded)
          else if (!node.isDir) onEdit(node)
        }}
        className={`border-b border-mf-border/30 hover:bg-mf-hover/40 cursor-pointer transition-colors ${
          isSelected ? 'bg-blue-600/15 border-l-2 border-l-blue-500' : ''
        }`}
        style={{ paddingLeft: `${12 + depth * 14}px` }}
      >
        <div className="flex items-center gap-1.5 py-1.5 pr-4">
          {hasChildren ? (
            <button onClick={(e) => { e.stopPropagation(); setExpanded(!expanded) }}
              className="text-mf-text-muted hover:text-mf-text-primary flex-shrink-0">
              {expanded ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
            </button>
          ) : node.isDir ? (
            <span className="w-2.5 flex-shrink-0" />
          ) : (
            <span className="w-2.5 flex-shrink-0" />
          )}
          <span className="text-mf-text-secondary text-[10px] flex-shrink-0">
            {node.isDir ? (expanded ? '📂' : '📁') : '📄'}
          </span>
          <span className="flex-1 text-[11px] text-mf-text-primary truncate font-mono" title={node.path}>
            {node.name}
          </span>
          {!node.isDir && (
            <span className="text-[10px] text-mf-text-muted flex-shrink-0">{formatSize(node.sizeBytes)}</span>
          )}
        </div>
      </div>
      {hasChildren && expanded && node.children.map((child) => (
        <TreeRow key={child.path} node={child} depth={depth + 1} editingPath={editingPath} onEdit={onEdit} />
      ))}
    </>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export function NodeFilesPage() {
  const qc = useQueryClient()

  const { data, isLoading, isError } = useQuery({
    queryKey: ['node-files'],
    queryFn: () => nodeFilesApi.list(),
  })

  const [editingPath, setEditingPath] = useState<string | null>(null)
  const [editContent, setEditContent] = useState('')
  const [saving, setSaving] = useState(false)
  const [saveMsg, setSaveMsg] = useState<string | null>(null)

  useEffect(() => {
    document.title = 'Node Files — MiQroForge'
  }, [])

  const handleEdit = useCallback(async (node: TreeNode) => {
    if (node.isDir) return
    try {
      const text = await nodeFilesApi.read(node.path)
      setEditingPath(node.path)
      setEditContent(text)
      setSaveMsg(null)
    } catch {
      setEditingPath(node.path)
      setEditContent('[Failed to read file]')
    }
  }, [])

  const handleSave = useCallback(async () => {
    if (!editingPath) return
    setSaving(true)
    try {
      await nodeFilesApi.write(editingPath, editContent)
      setSaveMsg('Saved')
      qc.invalidateQueries({ queryKey: ['node-files'] })
    } catch (err) {
      setSaveMsg(`Save failed: ${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setSaving(false)
    }
  }, [editingPath, editContent, qc])

  const tree = buildTree(data?.entries ?? [])

  return (
    <div className="h-screen flex flex-col bg-mf-base text-mf-text-primary">
      {/* Header */}
      <header className="sticky top-0 z-10 bg-mf-panel border-b border-mf-border flex-shrink-0">
        <div className="max-w-5xl mx-auto px-6 py-3 flex items-center gap-4">
          <a href="/" className="flex items-center gap-1.5 text-xs text-mf-text-muted hover:text-mf-text-primary transition-colors">
            <ArrowLeft size={14} /> Gallery
          </a>
          <div className="w-px h-5 bg-mf-border" />
          <a href="/node-repository/preference" className="flex items-center gap-1.5 text-xs text-mf-text-muted hover:text-mf-text-primary transition-colors">
            Preferences
          </a>
          <div className="w-px h-5 bg-mf-border" />
          <div className="flex items-center gap-2">
            <img src="/logo.png" alt="MiQroForge" className="h-5 w-auto" />
            <h1 className="text-sm font-semibold tracking-tight">Node Files</h1>
          </div>
          <span className="text-[10px] text-mf-text-muted">userdata/nodes/</span>
          <div className="flex-1" />
          <button onClick={() => qc.invalidateQueries({ queryKey: ['node-files'] })}
            className="flex items-center gap-1 px-2 py-1 text-xs text-mf-text-muted hover:text-mf-text-primary hover:bg-mf-hover rounded transition-colors" title="Refresh">
            <RefreshCw size={12} />
          </button>
        </div>
      </header>

      <main className="flex-1 overflow-hidden flex">
        {/* File tree */}
        <div className="w-80 flex-shrink-0 border-r border-mf-border overflow-y-auto mf-scroll">
          {isLoading && <p className="text-xs text-mf-text-muted px-4 py-4 text-center">Loading...</p>}
          {isError && <p className="text-xs text-red-500 px-4 py-4 text-center">Failed to load files</p>}
          {tree.map((node) => (
            <TreeRow key={node.path} node={node} depth={0} editingPath={editingPath} onEdit={handleEdit} />
          ))}
          {tree.length === 0 && !isLoading && (
            <p className="text-xs text-mf-text-muted px-4 py-4 text-center">No files. Add nodes to userdata/nodes/ first.</p>
          )}
        </div>

        {/* Editor */}
        <div className="flex-1 flex flex-col min-w-0">
          {editingPath ? (
            <>
              <div className="flex items-center justify-between px-4 py-2 border-b border-mf-border bg-mf-panel flex-shrink-0">
                <span className="text-xs font-mono text-mf-text-secondary truncate">{editingPath}</span>
                <div className="flex items-center gap-2">
                  {saveMsg && (
                    <span className={`text-[10px] ${saveMsg === 'Saved' ? 'text-green-400' : 'text-red-400'}`}>{saveMsg}</span>
                  )}
                  <button onClick={handleSave} disabled={saving}
                    className="flex items-center gap-1 px-3 py-1 text-xs text-white bg-blue-600 hover:bg-blue-500 rounded transition-colors disabled:opacity-50">
                    <Save size={12} /> {saving ? 'Saving...' : 'Save'}
                  </button>
                  <button onClick={() => { setEditingPath(null); setEditContent(''); setSaveMsg(null) }}
                    className="text-mf-text-muted hover:text-mf-text-primary">
                    <X size={14} />
                  </button>
                </div>
              </div>
              <textarea value={editContent} onChange={(e) => { setEditContent(e.target.value); setSaveMsg(null) }}
                className="flex-1 bg-mf-base text-mf-text-primary font-mono text-xs p-4 resize-none focus:outline-none" spellCheck={false} />
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-xs text-mf-text-muted">Select a file to edit</div>
          )}
        </div>
      </main>
    </div>
  )
}
