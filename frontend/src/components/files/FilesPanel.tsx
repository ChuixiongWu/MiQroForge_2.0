import React, { useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Upload, Download, Trash2, FolderOpen } from 'lucide-react'
import { filesApi } from '../../api/files-api'
import type { FileEntry } from '../../types/index-types'

// ─── FilesPanel ───────────────────────────────────────────────────────────────

export function FilesPanel() {
  const qc = useQueryClient()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['files'],
    queryFn: () => filesApi.list(),
  })

  const uploadMutation = useMutation({
    mutationFn: (file: File) => filesApi.upload(file),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['files'] }),
  })

  const deleteMutation = useMutation({
    mutationFn: (filename: string) => filesApi.remove(filename),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['files'] }),
  })

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    uploadMutation.mutate(file)
    // reset so the same file can be re-uploaded
    e.target.value = ''
  }

  const handleDownload = async (entry: FileEntry) => {
    try {
      const blob = await filesApi.download(entry.name)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = entry.name
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      console.error('Download failed:', err)
    }
  }

  const formatSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  const files = data?.files ?? []

  return (
    <div className="w-56 mf-panel border-r border-l-0 flex-shrink-0 flex flex-col">
      {/* Header */}
      <div className="flex items-center px-3 py-2 border-b border-mf-border flex-shrink-0">
        <span className="flex items-center gap-1.5 text-xs font-semibold text-mf-text-secondary uppercase tracking-wide">
          <FolderOpen size={13} className="text-blue-400" />
          Files
        </span>
      </div>

      {/* Upload button */}
      <div className="px-3 py-2 border-b border-mf-border flex-shrink-0">
        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          onChange={handleFileChange}
        />
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

      {/* File list */}
      <div className="flex-1 overflow-y-auto mf-scroll">
        {isLoading && (
          <p className="text-xs text-mf-text-muted px-3 py-4 text-center">Loading…</p>
        )}
        {isError && (
          <p className="text-xs text-red-500 px-3 py-4 text-center">Failed to load files</p>
        )}
        {!isLoading && !isError && files.length === 0 && (
          <p className="text-xs text-mf-text-muted px-3 py-4 text-center">No files in workspace</p>
        )}
        {files.map((entry) => (
          <div
            key={entry.name}
            className="px-3 py-2 border-b border-mf-border/50 hover:bg-mf-hover/40 transition-colors"
          >
            <div className="flex items-center gap-1.5">
              <span className="text-mf-text-secondary text-[10px]">📄</span>
              <span
                className="flex-1 text-xs text-mf-text-primary truncate font-mono"
                title={entry.name}
              >
                {entry.name}
              </span>
              <span className="text-[10px] text-mf-text-muted flex-shrink-0">
                {formatSize(entry.size_bytes)}
              </span>
            </div>
            <div className="flex gap-1 mt-1 ml-4">
              <button
                onClick={() => handleDownload(entry)}
                className="flex items-center gap-0.5 px-1.5 py-0.5 text-[10px] text-mf-text-secondary hover:text-blue-300 hover:bg-mf-hover rounded transition-colors"
                title="Download"
              >
                <Download size={10} /> Download
              </button>
              <button
                onClick={() => deleteMutation.mutate(entry.name)}
                disabled={deleteMutation.isPending}
                className="flex items-center gap-0.5 px-1.5 py-0.5 text-[10px] text-mf-text-secondary hover:text-red-400 hover:bg-mf-hover rounded transition-colors disabled:opacity-50"
                title="Delete"
              >
                <Trash2 size={10} /> Delete
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Footer status */}
      <div className="px-3 py-1.5 border-t border-mf-border flex-shrink-0">
        <span className="text-[10px] text-mf-text-muted">
          workspace/ • {files.length} file{files.length !== 1 ? 's' : ''}
        </span>
      </div>
    </div>
  )
}
