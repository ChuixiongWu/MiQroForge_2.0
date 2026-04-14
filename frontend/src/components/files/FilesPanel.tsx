import React, { useRef, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Upload, Download, Trash2, FolderOpen, Copy } from 'lucide-react'
import { filesApi, projectFilesApi } from '../../api/files-api'
import { useProjectStore } from '../../stores/project-store'
import type { FileEntry } from '../../types/index-types'

// ─── Helpers ────────────────────────────────────────────────────────────────

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function handleDownload(blob: Blob, filename: string) {
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
      handleDownload(blob, entry.name)
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
      handleDownload(blob, entry.name)
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

// ─── Main FilesPanel ────────────────────────────────────────────────────────

export function FilesPanel() {
  const projectId = useProjectStore((s) => s.currentProjectId)
  const [tab, setTab] = useState<'workspace' | 'project'>(projectId ? 'project' : 'workspace')

  // If projectId changes while panel is open, switch tab
  const effectiveTab = projectId ? tab : 'workspace'

  return (
    <div className="w-56 mf-panel border-r border-l-0 flex-shrink-0 flex flex-col">
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
          </div>
        )}
      </div>

      {/* Tab content */}
      {effectiveTab === 'project' && projectId ? (
        <ProjectTab projectId={projectId} />
      ) : (
        <WorkspaceTab />
      )}
    </div>
  )
}
