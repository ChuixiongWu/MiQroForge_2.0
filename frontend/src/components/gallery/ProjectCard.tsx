import { useState, useRef, useEffect } from 'react'
import { Copy, Trash2, MoreVertical, Pencil, FileText } from 'lucide-react'
import type { ProjectMeta } from '../../api/projects-api'

// ─── Common emoji sets ──────────────────────────────────────────────────────────

const EMOJI_OPTIONS = [
  // 通用
  '📁', '📂', '📄', '📝', '📌', '📎', '🗂️', '📋',
  '✏️', '🖊️', '🖋️', '📖', '📚', '📰', '🗞️', '🔖',
  // 科学
  '🔬', '🔭', '⚗️', '🧪', '🧬', '🦠', '🧫', '🧮',
  '⚛️', '🧲', '💡', '🌡️', '🔋', '🪫', '⚡', '🔌',
  // 技术
  '💻', '🖥️', '⌨️', '🖱️', '💾', '💿', '📀', '📱',
  '📲', '📡', '🛰️', '🤖', '🔧', '🔨', '🛠️', '⚙️',
  // 数据
  '📊', '📈', '📉', '🗃️', '🗄️', '📇', '📊', '🧾',
  '🔍', '🔎', '💠', '🔷', '🔶', '🌐', '🗺️', '🧭',
  // 自然
  '🌱', '🌿', '🍀', '🌳', '🌲', '🌴', '🌵', '🌾',
  '🌻', '🌸', '🌺', '🌹', '🔥', '💧', '🌊', '❄️',
  // 天文
  '☀️', '🌙', '⭐', '🌟', '💫', '✨', '🪐', '🌍',
  '🌎', '🌏', '🌕', '🌑', '☄️', '🚀', '🛸', '🛰️',
  // 数学/工程
  '➕', '➖', '➗', '✖️', '🟰', '📐', '📏', '🏗️',
  '🏭', '🏗️', '⚙️', '🔧', '🔩', '🪛', '⛏️', '🪚',
  // 符号
  '🎯', '🏁', '🚩', '🏳️', '🏴', '🎖️', '🏆', '🥇',
  '🥈', '🥉', '🏅', '⭐', '🌟', '💎', '👑', '🎵',
  // 动物
  '🐱', '🐶', '🐭', '🐹', '🐰', '🦊', '🐻', '🐼',
  '🐨', '🐯', '🦁', '🐮', '🐷', '🐸', '🐵', '🐔',
  // 食物
  '🍎', '🍊', '🍋', '🍌', '🍉', '🍇', '🍓', '🫐',
  '☕', '🍵', '🧃', '🥤', '🍶', '🍺', '🧋', '🍷',
  // 天气/地标
  '☀️', '🌤️', '⛅', '🌥️', '☁️', '🌧️', '⛈️', '🌩️',
  '🏠', '🏡', '🏢', '🏣', '🏤', '🏥', '🏦', '🏨',
  // 交通
  '🚗', '🚕', '🚌', '🚎', '🏎️', '🚓', '🚑', '🚒',
  '✈️', '🛩️', '🚂', '🚆', '🚇', '🚊', '🚁', '⛵',
  // 其他
  '❤️', '🧡', '💛', '💚', '💙', '💜', '🖤', '🤍',
  '♻️', '☢️', '☣️', '⚠️', '🔒', '🔓', '🔑', '🗝️',
]

interface ProjectCardProps {
  project: ProjectMeta
  onOpen: () => void
  onRename: (newName: string) => void
  onIconChange: (icon: string) => void
  onDescriptionChange: (description: string) => void
  onDuplicate: () => void
  onDelete: () => void
}

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  if (days < 30) return `${days}d ago`
  return new Date(iso).toLocaleDateString()
}

export function ProjectCard({
  project, onOpen, onRename, onIconChange, onDescriptionChange, onDuplicate, onDelete,
}: ProjectCardProps) {
  const [menuOpen, setMenuOpen] = useState(false)
  const [editing, setEditing] = useState(false)
  const [nameVal, setNameVal] = useState(project.name)
  const [emojiPickerOpen, setEmojiPickerOpen] = useState(false)
  const [descEditing, setDescEditing] = useState(false)
  const [descVal, setDescVal] = useState(project.description)
  const menuRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const descRef = useRef<HTMLTextAreaElement>(null)
  const emojiRef = useRef<HTMLDivElement>(null)

  // Sync props to local state
  useEffect(() => { setNameVal(project.name) }, [project.name])
  useEffect(() => { setDescVal(project.description) }, [project.description])

  // Close menu on outside click
  useEffect(() => {
    if (!menuOpen) return
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [menuOpen])

  // Close emoji picker on outside click
  useEffect(() => {
    if (!emojiPickerOpen) return
    const handler = (e: MouseEvent) => {
      if (emojiRef.current && !emojiRef.current.contains(e.target as Node)) {
        setEmojiPickerOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [emojiPickerOpen])

  useEffect(() => {
    if (editing && inputRef.current) {
      inputRef.current.focus()
      inputRef.current.select()
    }
  }, [editing])

  useEffect(() => {
    if (descEditing && descRef.current) {
      descRef.current.focus()
    }
  }, [descEditing])

  const handleRenameSubmit = () => {
    setEditing(false)
    if (nameVal.trim() && nameVal !== project.name) {
      onRename(nameVal.trim())
    } else {
      setNameVal(project.name)
    }
  }

  const handleDescSubmit = () => {
    setDescEditing(false)
    if (descVal !== project.description) {
      onDescriptionChange(descVal)
    }
  }

  const icon = project.icon || '📁'
  const hasIcon = !!project.icon

  return (
    <div
      className="group relative flex flex-col bg-mf-panel border border-mf-border rounded-lg hover:border-blue-500/50 hover:shadow-lg hover:shadow-blue-500/5 transition-all cursor-pointer"
      onClick={() => { if (!editing && !descEditing) onOpen() }}
    >
      {/* Header icon + menu */}
      <div className="flex items-start justify-between p-4 pb-2">
        <div className="flex items-center gap-2.5">
          {/* Emoji icon — click to open picker */}
          <div className="relative" ref={emojiRef}>
            <button
              onClick={(e) => { e.stopPropagation(); setEmojiPickerOpen(!emojiPickerOpen) }}
              className={`w-9 h-9 rounded-md flex items-center justify-center flex-shrink-0 text-lg transition-colors ${
                hasIcon
                  ? 'bg-mf-hover hover:bg-mf-hover'
                  : 'bg-blue-600/15 hover:bg-blue-600/25'
              }`}
              title="Change icon"
            >
              {icon}
            </button>
            {emojiPickerOpen && (
              <div
                className="absolute left-0 top-full mt-1 bg-mf-panel border border-mf-border rounded-lg shadow-xl z-50 p-2 w-56"
                onClick={(e) => e.stopPropagation()}
              >
                <div className="grid grid-cols-6 gap-0.5">
                  {EMOJI_OPTIONS.map((emoji) => (
                    <button
                      key={emoji}
                      onClick={() => {
                        onIconChange(emoji)
                        setEmojiPickerOpen(false)
                      }}
                      className={`w-8 h-8 flex items-center justify-center text-base rounded hover:bg-mf-hover transition-colors ${
                        project.icon === emoji ? 'bg-mf-hover ring-1 ring-blue-500' : ''
                      }`}
                    >
                      {emoji}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {editing ? (
            <input
              ref={inputRef}
              value={nameVal}
              onChange={(e) => setNameVal(e.target.value)}
              onBlur={handleRenameSubmit}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleRenameSubmit()
                if (e.key === 'Escape') { setNameVal(project.name); setEditing(false) }
              }}
              onClick={(e) => e.stopPropagation()}
              className="text-sm font-medium text-mf-text-primary bg-mf-input border border-mf-border rounded px-2 py-0.5 focus:outline-none focus:border-blue-500 w-40"
            />
          ) : (
            <h3 className="text-sm font-medium text-mf-text-primary truncate max-w-40">
              {project.name}
            </h3>
          )}
        </div>

        {/* Context menu */}
        <div ref={menuRef} className="relative">
          <button
            onClick={(e) => { e.stopPropagation(); setMenuOpen(!menuOpen) }}
            className="p-1 text-mf-text-muted hover:text-mf-text-primary hover:bg-mf-hover rounded opacity-0 group-hover:opacity-100 transition-opacity"
          >
            <MoreVertical size={14} />
          </button>
          {menuOpen && (
            <div className="absolute right-0 top-full mt-1 w-36 bg-mf-panel border border-mf-border rounded-md shadow-lg z-50 py-1">
              <button
                onClick={(e) => { e.stopPropagation(); setMenuOpen(false); setEditing(true) }}
                className="flex items-center gap-2 w-full px-3 py-1.5 text-xs text-mf-text-secondary hover:text-mf-text-primary hover:bg-mf-hover"
              >
                <Pencil size={12} /> Rename
              </button>
              <button
                onClick={(e) => { e.stopPropagation(); setMenuOpen(false); setDescEditing(true) }}
                className="flex items-center gap-2 w-full px-3 py-1.5 text-xs text-mf-text-secondary hover:text-mf-text-primary hover:bg-mf-hover"
              >
                <FileText size={12} /> Edit Note
              </button>
              <button
                onClick={(e) => { e.stopPropagation(); setMenuOpen(false); onDuplicate() }}
                className="flex items-center gap-2 w-full px-3 py-1.5 text-xs text-mf-text-secondary hover:text-mf-text-primary hover:bg-mf-hover"
              >
                <Copy size={12} /> Duplicate
              </button>
              <div className="border-t border-mf-border my-1" />
              <button
                onClick={(e) => { e.stopPropagation(); setMenuOpen(false); onDelete() }}
                className="flex items-center gap-2 w-full px-3 py-1.5 text-xs text-red-400 hover:text-red-300 hover:bg-mf-hover"
              >
                <Trash2 size={12} /> Delete
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Stats + description */}
      <div className="px-4 pb-3 flex-1">
        <div className="flex items-center gap-3 text-[11px] text-mf-text-muted">
          <span>{project.canvas_node_count} node{project.canvas_node_count !== 1 ? 's' : ''}</span>
          <span>{project.run_count} run{project.run_count !== 1 ? 's' : ''}</span>
          <span>{project.conversation_count} chat{project.conversation_count !== 1 ? 's' : ''}</span>
        </div>

        {/* Description / Note — inline editable */}
        {descEditing ? (
          <textarea
            ref={descRef}
            value={descVal}
            onChange={(e) => setDescVal(e.target.value)}
            onBlur={handleDescSubmit}
            onKeyDown={(e) => {
              if (e.key === 'Escape') { setDescVal(project.description); setDescEditing(false) }
            }}
            onClick={(e) => e.stopPropagation()}
            placeholder="Add a note..."
            rows={2}
            className="mt-1.5 w-full text-[11px] text-mf-text-secondary bg-mf-input border border-mf-border rounded px-2 py-1.5 focus:outline-none focus:border-blue-500 resize-none"
          />
        ) : project.description ? (
          <p className="text-[11px] text-mf-text-muted mt-1.5 line-clamp-2">
            {project.description}
          </p>
        ) : null}
      </div>

      {/* Footer */}
      <div className="px-4 py-2.5 border-t border-mf-border/60 flex items-center justify-between">
        <span className="text-[10px] text-mf-text-muted">
          Updated {timeAgo(project.updated_at)}
        </span>
        <button
          onClick={(e) => { e.stopPropagation(); onOpen() }}
          className="text-[11px] text-blue-400 hover:text-blue-300 font-medium"
        >
          Open
        </button>
      </div>
    </div>
  )
}
