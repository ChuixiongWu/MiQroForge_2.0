import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus } from 'lucide-react'
import { ProjectCard } from '../components/gallery/ProjectCard'
import { projectsApi } from '../api/projects-api'
import type { ProjectMeta } from '../api/projects-api'

// ─── Migration from old localStorage keys ─────────────────────────────────────

const OLD_KEYS = ['mf-canvas-v1', 'mf-agent-v1', 'mf2:saved-workflows', 'mf2:run-snapshots']

async function tryMigrateOldData(): Promise<boolean> {
  const hasOldKeys = OLD_KEYS.some((k) => localStorage.getItem(k) !== null)
  if (!hasOldKeys) return false

  // Check that there are no existing projects
  const { projects } = await projectsApi.list()
  if (projects.length > 0) {
    // Projects already exist — just clean up old keys
    for (const key of OLD_KEYS) localStorage.removeItem(key)
    return false
  }

  // Capture old data then immediately clean keys (prevents duplicate migration)
  const canvasRaw = localStorage.getItem('mf-canvas-v1')
  const agentRaw = localStorage.getItem('mf-agent-v1')
  for (const key of OLD_KEYS) localStorage.removeItem(key)

  // Create a migrated project
  const meta = await projectsApi.create({
    name: 'Migrated Workflow',
    description: 'Auto-migrated from local storage',
  })

  // Upload canvas data
  if (canvasRaw) {
    try {
      const parsed = JSON.parse(canvasRaw)
      await projectsApi.saveCanvas(meta.id, {
        meta: parsed.meta || {},
        nodes: parsed.nodes || [],
        edges: parsed.edges || [],
      })
    } catch { /* ignore parse errors */ }
  }

  // Migrate agent messages as a conversation
  if (agentRaw) {
    try {
      const agentData = JSON.parse(agentRaw)
      if (agentData.messages?.length > 0) {
        const conv = await projectsApi.createConversation(meta.id, 'Migrated Chat')
        await fetch(`/api/v1/projects/${meta.id}/conversations/${conv.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ messages: agentData.messages }),
        })
      }
    } catch { /* ignore */ }
  }

  return true
}

// ─── Gallery page ─────────────────────────────────────────────────────────────

export function ProjectGallery() {
  const navigate = useNavigate()
  const [projects, setProjects] = useState<ProjectMeta[]>([])
  const [loading, setLoading] = useState(true)
  const [migrated, setMigrated] = useState(false)

  const fetchProjects = useCallback(async () => {
    try {
      const resp = await projectsApi.list()
      setProjects(resp.projects)
    } catch {
      /* ignore */
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    ;(async () => {
      const didMigrate = await tryMigrateOldData()
      if (didMigrate) setMigrated(true)
      await fetchProjects()
    })()
  }, [fetchProjects])

  const handleCreate = async () => {
    try {
      const meta = await projectsApi.create({ name: 'Untitled Project' })
      navigate(`/project/${meta.id}`)
    } catch { /* ignore */ }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this project? This cannot be undone.')) return
    try {
      await projectsApi.delete(id)
      setProjects((prev) => prev.filter((p) => p.id !== id))
    } catch { /* ignore */ }
  }

  const handleDuplicate = async (id: string) => {
    try {
      const meta = await projectsApi.duplicate(id)
      setProjects((prev) => [meta, ...prev])
    } catch { /* ignore */ }
  }

  const handleRename = async (id: string, name: string) => {
    try {
      const meta = await projectsApi.update(id, { name })
      setProjects((prev) => prev.map((p) => (p.id === id ? meta : p)))
    } catch { /* ignore */ }
  }

  const handleIconChange = async (id: string, icon: string) => {
    // Optimistic update
    setProjects((prev) => prev.map((p) => (p.id === id ? { ...p, icon } : p)))
    try {
      await projectsApi.update(id, { icon })
    } catch { /* ignore */ }
  }

  const handleDescriptionChange = async (id: string, description: string) => {
    // Optimistic update
    setProjects((prev) => prev.map((p) => (p.id === id ? { ...p, description } : p)))
    try {
      await projectsApi.update(id, { description })
    } catch { /* ignore */ }
  }

  return (
    <div className="min-h-screen bg-mf-base flex flex-col">
      {/* Header */}
      <div className="flex items-center h-14 px-6 border-b border-mf-border bg-mf-panel">
        <div className="flex items-center gap-2">
          <img src="/logo.png" alt="MiQroForge" className="h-7 w-auto" />
          <span className="text-base font-bold text-mf-text-primary tracking-tight">MiQroForge</span>
          <span className="text-[10px] text-mf-text-muted border border-mf-border rounded px-1">2.0</span>
        </div>
        <div className="flex-1" />
        <button
          onClick={handleCreate}
          className="flex items-center gap-1.5 px-4 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-500 rounded-md transition-colors"
        >
          <Plus size={14} /> New Project
        </button>
      </div>

      {/* Migration banner */}
      {migrated && (
        <div className="mx-6 mt-4 px-4 py-2.5 bg-blue-900/30 border border-blue-500/30 rounded-md text-xs text-blue-300">
          Your previous workflow has been migrated to a project called "Migrated Workflow".
        </div>
      )}

      {/* Content */}
      <div className="flex-1 p-6">
        {loading ? (
          <div className="flex items-center justify-center h-64 text-mf-text-muted text-sm">
            Loading projects...
          </div>
        ) : projects.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 gap-3">
            <div className="w-16 h-16 rounded-full bg-mf-panel border border-mf-border flex items-center justify-center">
              <Plus size={24} className="text-mf-text-muted" />
            </div>
            <p className="text-sm text-mf-text-muted">No projects yet</p>
            <button
              onClick={handleCreate}
              className="text-sm text-blue-400 hover:text-blue-300 font-medium"
            >
              Create your first project
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {projects.map((p) => (
              <ProjectCard
                key={p.id}
                project={p}
                onOpen={() => navigate(`/project/${p.id}`)}
                onRename={(name) => handleRename(p.id, name)}
                onIconChange={(icon) => handleIconChange(p.id, icon)}
                onDescriptionChange={(desc) => handleDescriptionChange(p.id, desc)}
                onDuplicate={() => handleDuplicate(p.id)}
                onDelete={() => handleDelete(p.id)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
