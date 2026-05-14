import React, { useRef, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Upload, Download, Trash2, FolderOpen, Copy, ChevronDown, ChevronRight, X } from 'lucide-react'
import { filesApi, projectFilesApi } from '../../api/files-api'
import type { DirectoryEntry } from '../../api/files-api'
import { useProjectStore } from '../../stores/project-store'
import type { FileEntry } from '../../types/index-types'

// ─── Helpers ────────────────────────────────────────────────────────────────

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function handleDownloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

// ─── File list rows ─────────────────────────────────────────────────────────

function FileList({
  files,
  onDownload,
  onDelete,
  deletePending,
  extraAction,
}: {
  files: FileEntry[]
  onDownload: (entry: FileEntry) => void
  onDelete: (name: string) => void
  deletePending: boolean
  extraAction?: { label: string; icon: React.ReactNode; onClick: (entry: FileEntry) => void }
}) {
  if (files.length === 0) {
    return <p className="text-xs text-mf-text-muted px-3 py-4 text-center">No files</p>
  }
  return (
    <>
      {files.map((entry) => (
        <div
          key={entry.name}
          className="px-3 py-2 border-b border-mf-border/50 hover:bg-mf-hover/40 transition-colors"
        >
          <div className="flex items-center gap-1.5">
            <span className="text-mf-text-secondary text-[10px]">📄</span>
            <span className="flex-1 text-xs text-mf-text-primary truncate font-mono" title={entry.name}>
              {entry.name}
            </span>
            <span className="text-[10px] text-mf-text-muted flex-shrink-0">
              {formatSize(entry.size_bytes)}
            </span>
          </div>
          <div className="flex gap-1 mt-1 ml-4">
            <button
              onClick={() => onDownload(entry)}
              className="flex items-center gap-0.5 px-1.5 py-0.5 text-[10px] text-mf-text-secondary hover:text-blue-300 hover:bg-mf-hover rounded transition-colors"
              title="Download"
            >
              <Download size={10} /> Download
            </button>
            {extraAction && (
              <button
                onClick={() => extraAction.onClick(entry)}
                className="flex items-center gap-0.5 px-1.5 py-0.5 text-[10px] text-mf-text-secondary hover:text-green-300 hover:bg-mf-hover rounded transition-colors"
                title={extraAction.label}
              >
                {extraAction.icon} {extraAction.label}
              </button>
            )}
            <button
              onClick={() => onDelete(entry.name)}
              disabled={deletePending}
              className="flex items-center gap-0.5 px-1.5 py-0.5 text-[10px] text-mf-text-secondary hover:text-red-400 hover:bg-mf-hover rounded transition-colors disabled:opacity-50"
              title="Delete"
            >
              <Trash2 size={10} /> Delete
            </button>
          </div>
        </div>
      ))}
    </>
  )
}

// ─── Workspace tab ──────────────────────────────────────────────────────────

function WorkspaceTab() {
  const qc = useQueryClient()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['files', 'workspace'],
    queryFn: () => filesApi.list(),
  })

  const uploadMutation = useMutation({
    mutationFn: (file: File) => filesApi.upload(file),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['files', 'workspace'] }),
  })

  const deleteMutation = useMutation({
    mutationFn: (filename: string) => filesApi.remove(filename),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['files', 'workspace'] }),
  })

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    uploadMutation.mutate(file)
    e.target.value = ''
  }

  const handleDownload = async (entry: FileEntry) => {
    try {
      const blob = await filesApi.download(entry.name)
      handleDownloadBlob(blob, entry.name)
    } catch (err) {
      console.error('Download failed:', err)
    }
  }

  const files = data?.files ?? []

  return (
    <div className="flex flex-col flex-1 min-h-0">
      {/* Upload */}
      <div className="px-3 py-2 border-b border-mf-border flex-shrink-0">
        <input ref={fileInputRef} type="file" className="hidden" onChange={handleFileChange} />
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={uploadMutation.isPending}
          className="flex items-center gap-1.5 px-2 py-1.5 w-full justify-center text-xs bg-blue-600/20 border border-blue-600/40 text-blue-300 hover:bg-blue-600/30 rounded transition-colors disabled:opacity-50"
        >
          <Upload size={12} />
          {uploadMutation.isPending ? 'Uploading…' : 'Upload File'}
        </button>
        {uploadMutation.isError && (
          <p className="text-[10px] text-red-400 mt-1 truncate">
            {uploadMutation.error instanceof Error ? uploadMutation.error.message : 'Upload failed'}
          </p>
        )}
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto mf-scroll">
        {isLoading && <p className="text-xs text-mf-text-muted px-3 py-4 text-center">Loading…</p>}
        {isError && <p className="text-xs text-red-500 px-3 py-4 text-center">Failed to load files</p>}
        <FileList
          files={files}
          onDownload={handleDownload}
          onDelete={(name) => deleteMutation.mutate(name)}
          deletePending={deleteMutation.isPending}
        />
      </div>

      <div className="px-3 py-1.5 border-t border-mf-border flex-shrink-0">
        <span className="text-[10px] text-mf-text-muted">
          workspace/ • {files.length} file{files.length !== 1 ? 's' : ''}
        </span>
      </div>
    </div>
  )
}

// ─── Project tab ────────────────────────────────────────────────────────────

function ProjectTab({ projectId }: { projectId: string }) {
  const qc = useQueryClient()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['files', 'project', projectId],
    queryFn: () => projectFilesApi.list(projectId),
  })

  const { data: wsData } = useQuery({
    queryKey: ['files', 'workspace'],
    queryFn: () => filesApi.list(),
  })

  const uploadMutation = useMutation({
    mutationFn: (file: File) => projectFilesApi.upload(projectId, file),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['files', 'project', projectId] }),
  })

  const deleteMutation = useMutation({
    mutationFn: (filename: string) => projectFilesApi.remove(projectId, filename),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['files', 'project', projectId] }),
  })

  const copyMutation = useMutation({
    mutationFn: (filename: string) => projectFilesApi.copyFromWorkspace(projectId, filename),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['files', 'project', projectId] })
    },
  })

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    uploadMutation.mutate(file)
    e.target.value = ''
  }

  const handleDownload = async (entry: FileEntry) => {
    try {
      const blob = await projectFilesApi.download(projectId, entry.name)
      handleDownloadBlob(blob, entry.name)
    } catch (err) {
      console.error('Download failed:', err)
    }
  }

  const files = data?.files ?? []
  const wsFiles = wsData?.files ?? []

  // Workspace files not already in project
  const existingNames = new Set(files.map((f) => f.name))
  const copyableFiles = wsFiles.filter((f) => !existingNames.has(f.name))

  return (
    <div className="flex flex-col flex-1 min-h-0">
      {/* Upload */}
      <div className="px-3 py-2 border-b border-mf-border flex-shrink-0 space-y-1.5">
        <input ref={fileInputRef} type="file" className="hidden" onChange={handleFileChange} />
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={uploadMutation.isPending}
          className="flex items-center gap-1.5 px-2 py-1.5 w-full justify-center text-xs bg-blue-600/20 border border-blue-600/40 text-blue-300 hover:bg-blue-600/30 rounded transition-colors disabled:opacity-50"
        >
          <Upload size={12} />
          {uploadMutation.isPending ? 'Uploading…' : 'Upload File'}
        </button>
        {uploadMutation.isError && (
          <p className="text-[10px] text-red-400 mt-1 truncate">
            {uploadMutation.error instanceof Error ? uploadMutation.error.message : 'Upload failed'}
          </p>
        )}
      </div>

      {/* Copy from workspace */}
      {copyableFiles.length > 0 && (
        <div className="px-3 py-2 border-b border-mf-border flex-shrink-0">
          <p className="text-[10px] text-mf-text-muted mb-1">Copy from workspace:</p>
          <div className="space-y-0.5 max-h-24 overflow-y-auto mf-scroll">
            {copyableFiles.map((wf) => (
              <button
                key={wf.name}
                onClick={() => copyMutation.mutate(wf.name)}
                disabled={copyMutation.isPending}
                className="flex items-center gap-1.5 w-full px-2 py-1 text-[10px] text-mf-text-secondary hover:text-green-300 hover:bg-mf-hover rounded transition-colors disabled:opacity-50"
              >
                <Copy size={10} />
                <span className="truncate font-mono">{wf.name}</span>
                <span className="ml-auto text-mf-text-muted flex-shrink-0">{formatSize(wf.size_bytes)}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* List */}
      <div className="flex-1 overflow-y-auto mf-scroll">
        {isLoading && <p className="text-xs text-mf-text-muted px-3 py-4 text-center">Loading…</p>}
        {isError && <p className="text-xs text-red-500 px-3 py-4 text-center">Failed to load files</p>}
        <FileList
          files={files}
          onDownload={handleDownload}
          onDelete={(name) => deleteMutation.mutate(name)}
          deletePending={deleteMutation.isPending}
        />
      </div>

      <div className="px-3 py-1.5 border-t border-mf-border flex-shrink-0">
        <span className="text-[10px] text-mf-text-muted">
          project files/ • {files.length} file{files.length !== 1 ? 's' : ''}
        </span>
      </div>
    </div>
  )
}

// ─── Directory tab (project file system browser) ─────────────────────────────

/** Files to hide from the project directory browser. */
const HIDDEN_FILES = new Set(['canvas.json', 'project.json', 'afterrun_canvas.json'])
const HIDDEN_DIRS = new Set(['files'])

interface TreeNode {
  name: string
  path: string
  isDir: boolean
  sizeBytes: number
  children: TreeNode[]
}

function buildTree(entries: DirectoryEntry[]): TreeNode[] {
  // Filter hidden entries
  const visible = entries.filter((e) => {
    const parts = e.path.split('/')
    // Check each path segment for hidden dirs/files
    for (const part of parts) {
      if (HIDDEN_DIRS.has(part)) return false
    }
    if (!e.is_dir && HIDDEN_FILES.has(e.name)) return false
    return true
  })

  const root: TreeNode[] = []
  const dirMap = new Map<string, TreeNode>()

  for (const e of visible) {
    const parts = e.path.split('/')
    const node: TreeNode = {
      name: e.name,
      path: e.path,
      isDir: e.is_dir,
      sizeBytes: e.size_bytes,
      children: [],
    }

    if (parts.length === 1) {
      root.push(node)
    } else {
      const parentPath = parts.slice(0, -1).join('/')
      const parent = dirMap.get(parentPath)
      if (parent) {
        parent.children.push(node)
      } else {
        // Parent not found (shouldn't happen if list is complete) — add to root
        root.push(node)
      }
    }

    if (e.is_dir) {
      dirMap.set(e.path, node)
    }
  }

  // Sort: dirs first, then alphabetically
  const sortNodes = (nodes: TreeNode[]) => {
    nodes.sort((a, b) => {
      if (a.isDir !== b.isDir) return a.isDir ? -1 : 1
      return a.name.localeCompare(b.name)
    })
    for (const n of nodes) sortNodes(n.children)
  }
  sortNodes(root)
  return root
}

function TreeRow({
  node,
  depth,
  onView,
  onDownload,
}: {
  node: TreeNode
  depth: number
  onView: (entry: TreeNode) => void
  onDownload: (entry: TreeNode) => void
}) {
  const [expanded, setExpanded] = useState(depth < 1)
  const hasChildren = node.isDir && node.children.length > 0

  return (
    <>
      <div
        className="px-3 py-1.5 border-b border-mf-border/30 hover:bg-mf-hover/40 transition-colors select-none"
        style={{ paddingLeft: `${12 + depth * 14}px` }}
      >
        <div className="flex items-center gap-1.5">
          {hasChildren ? (
            <button
              onClick={() => setExpanded(!expanded)}
              className="text-mf-text-muted hover:text-mf-text-primary flex-shrink-0"
            >
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
          <span
            className="flex-1 text-[11px] text-mf-text-primary truncate font-mono cursor-pointer"
            title={node.path}
            onClick={() => {
              if (node.isDir && hasChildren) setExpanded(!expanded)
              else if (!node.isDir) onView(node)
            }}
          >
            {node.name}
          </span>
          {!node.isDir && (
            <span className="text-[10px] text-mf-text-muted flex-shrink-0">
              {formatSize(node.sizeBytes)}
            </span>
          )}
        </div>
        {!node.isDir && (
          <div className="flex gap-1 mt-0.5" style={{ marginLeft: `${2 + 10 + 4}px` }}>
            <button
              onClick={() => onView(node)}
              className="flex items-center gap-0.5 px-1.5 py-0.5 text-[10px] text-mf-text-secondary hover:text-blue-300 hover:bg-mf-hover rounded transition-colors"
              title="View"
            >
              View
            </button>
            <button
              onClick={() => onDownload(node)}
              className="flex items-center gap-0.5 px-1.5 py-0.5 text-[10px] text-mf-text-secondary hover:text-green-300 hover:bg-mf-hover rounded transition-colors"
              title="Download"
            >
              <Download size={10} /> Download
            </button>
          </div>
        )}
      </div>
      {hasChildren && expanded && node.children.map((child) => (
        <TreeRow
          key={child.path}
          node={child}
          depth={depth + 1}
          onView={onView}
          onDownload={onDownload}
        />
      ))}
    </>
  )
}

function DirectoryTab({ projectId }: { projectId: string }) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['files', 'directory', projectId],
    queryFn: () => projectFilesApi.listDirectory(projectId),
  })

  const [modalPath, setModalPath] = useState<string | null>(null)
  const [modalContent, setModalContent] = useState<string | null>(null)
  const [modalLoading, setModalLoading] = useState(false)

  const handleView = async (node: TreeNode) => {
    if (node.isDir) return
    setModalPath(node.path)
    setModalContent(null)
    setModalLoading(true)
    try {
      const blob = await projectFilesApi.downloadFromDirectory(projectId, node.path)
      setModalContent(await blob.text())
    } catch {
      setModalContent('[Failed to read file]')
    } finally {
      setModalLoading(false)
    }
  }

  const handleDownload = async (node: TreeNode) => {
    if (node.isDir) return
    try {
      const blob = await projectFilesApi.downloadFromDirectory(projectId, node.path)
      handleDownloadBlob(blob, node.name)
    } catch (err) {
      console.error('Download failed:', err)
    }
  }

  const tree = buildTree(data?.entries ?? [])
  const fileCount = data?.entries?.filter((e) => !e.is_dir).length ?? 0

  return (
    <div className="flex flex-col flex-1 min-h-0">
      <div className="flex-1 overflow-y-auto mf-scroll">
        {isLoading && <p className="text-xs text-mf-text-muted px-3 py-4 text-center">Loading...</p>}
        {isError && <p className="text-xs text-red-500 px-3 py-4 text-center">Failed to load directory</p>}
        {tree.map((node) => (
          <TreeRow
            key={node.path}
            node={node}
            depth={0}
            onView={handleView}
            onDownload={handleDownload}
          />
        ))}
        {tree.length === 0 && !isLoading && (
          <p className="text-xs text-mf-text-muted px-3 py-4 text-center">No files</p>
        )}
      </div>
      <div className="px-3 py-1.5 border-t border-mf-border flex-shrink-0">
        <span className="text-[10px] text-mf-text-muted">
          project dir/ • {fileCount} file{fileCount !== 1 ? 's' : ''}
        </span>
      </div>

      {/* View file modal */}
      {modalPath && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center">
          <div className="absolute inset-0 bg-black/50" onClick={() => { setModalPath(null); setModalContent(null) }} />
          <div className="relative bg-mf-panel border border-mf-border rounded-lg shadow-2xl w-[70vw] max-w-4xl max-h-[80vh] flex flex-col">
            <div className="flex items-center justify-between px-4 py-2 border-b border-mf-border flex-shrink-0">
              <span className="text-xs font-mono text-mf-text-secondary truncate">{modalPath}</span>
              <button onClick={() => { setModalPath(null); setModalContent(null) }}
                className="text-mf-text-muted hover:text-mf-text-primary">
                <X size={14} />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto mf-scroll p-4">
              {modalLoading ? (
                <p className="text-xs text-mf-text-muted">Loading...</p>
              ) : (
                <pre className="text-xs text-mf-text-primary font-mono whitespace-pre-wrap break-all">{modalContent}</pre>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Main FilesPanel ────────────────────────────────────────────────────────

export function FilesPanel() {
  const projectId = useProjectStore((s) => s.currentProjectId)
  const [tab, setTab] = useState<'workspace' | 'project' | 'directory'>(projectId ? 'project' : 'workspace')

  // If projectId changes while panel is open, switch tab
  const effectiveTab = projectId ? tab : 'workspace'

  return (
    <div className="w-64 mf-panel border-r border-l-0 flex-shrink-0 flex flex-col">
      {/* Header with tabs */}
      <div className="flex items-center border-b border-mf-border flex-shrink-0">
        <span className="flex items-center gap-1.5 text-xs font-semibold text-mf-text-secondary uppercase tracking-wide px-3 py-2">
          <FolderOpen size={13} className="text-blue-400" />
          Files
        </span>
        {projectId && (
          <div className="ml-auto flex">
            <button
              onClick={() => setTab('workspace')}
              className={`px-2 py-2 text-[10px] transition-colors ${
                effectiveTab === 'workspace'
                  ? 'text-blue-300 border-b-2 border-blue-400'
                  : 'text-mf-text-muted hover:text-mf-text-secondary'
              }`}
            >
              Global
            </button>
            <button
              onClick={() => setTab('project')}
              className={`px-2 py-2 text-[10px] transition-colors ${
                effectiveTab === 'project'
                  ? 'text-blue-300 border-b-2 border-blue-400'
                  : 'text-mf-text-muted hover:text-mf-text-secondary'
              }`}
            >
              Project
            </button>
            <button
              onClick={() => setTab('directory')}
              className={`px-2 py-2 text-[10px] transition-colors ${
                effectiveTab === 'directory'
                  ? 'text-blue-300 border-b-2 border-blue-400'
                  : 'text-mf-text-muted hover:text-mf-text-secondary'
              }`}
            >
              Dir
            </button>
          </div>
        )}
      </div>

      {/* Tab content */}
      {effectiveTab === 'directory' && projectId ? (
        <DirectoryTab projectId={projectId} />
      ) : effectiveTab === 'project' && projectId ? (
        <ProjectTab projectId={projectId} />
      ) : (
        <WorkspaceTab />
      )}
    </div>
  )
}
