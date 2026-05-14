import { useState } from 'react'
import { X } from 'lucide-react'
import { useSettingsStore } from '../../stores/settings-store'
import type { Theme, FontSize } from '../../stores/settings-store'
import {
  useShortcutsStore,
  SHORTCUT_DEFS,
  bindingFromEvent,
  displayKey,
} from '../../stores/shortcuts-store'
import type { ShortcutId } from '../../stores/shortcuts-store'

// ─── Shortcut row ──────────────────────────────────────────────────────────────

function ShortcutRow({ id }: { id: ShortcutId }) {
  const def = SHORTCUT_DEFS[id]
  const binding   = useShortcutsStore((s) => s.bindings[id])
  const setBinding  = useShortcutsStore((s) => s.setBinding)
  const resetBinding = useShortcutsStore((s) => s.resetBinding)
  const [recording, setRecording] = useState(false)

  const handleKeyDown = (e: React.KeyboardEvent) => {
    e.preventDefault()
    e.stopPropagation()
    const b = bindingFromEvent(e.nativeEvent)
    if (!b) return          // bare modifier — keep recording
    if (e.key === 'Escape') {
      setRecording(false)
      return
    }
    setBinding(id, b)
    setRecording(false)
  }

  const isDefault = binding === def.defaultKey

  return (
    <div className="flex items-center gap-2 py-1">
      <div className="flex-1 min-w-0">
        <div className="text-xs text-mf-text-secondary truncate">{def.label}</div>
        {def.description && (
          <div className="text-[10px] text-mf-text-muted truncate">{def.description}</div>
        )}
      </div>

      <div className="flex items-center gap-1 flex-shrink-0">
        {/* Key badge / recording button */}
        <button
          onClick={() => setRecording(true)}
          onKeyDown={recording ? handleKeyDown : undefined}
          onBlur={() => setRecording(false)}
          title="Click then press a key to rebind"
          className={`px-2 py-0.5 rounded border text-[11px] font-mono transition-colors ${
            recording
              ? 'bg-blue-600 border-blue-400 text-white animate-pulse'
              : 'bg-mf-card border-mf-border text-mf-text-secondary hover:border-gray-400 hover:text-mf-text-primary'
          }`}
        >
          {recording ? 'press key…' : displayKey(binding)}
        </button>

        {/* Reset to default — only shown when overridden */}
        {!isDefault && (
          <button
            onClick={() => resetBinding(id)}
            title="Reset to default"
            className="text-mf-text-muted hover:text-mf-text-secondary text-[10px] px-1"
          >
            ↺
          </button>
        )}
      </div>
    </div>
  )
}

// ─── SettingsContent (shared between panel and modal) ──────────────────────────

export function SettingsContent() {
  const { theme, fontSize, setTheme, setFontSize } = useSettingsStore()
  const resetAll = useShortcutsStore((s) => s.resetAll)

  const shortcutIds = Object.keys(SHORTCUT_DEFS) as ShortcutId[]

  return (
    <div className="space-y-5">
      {/* Theme */}
      <div>
        <div className="text-xs font-semibold text-mf-text-secondary uppercase tracking-wide mb-2">
          Theme
        </div>
        <div className="flex gap-2">
          {(['light', 'dark'] as Theme[]).map((t) => (
            <button
              key={t}
              onClick={() => setTheme(t)}
              className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 text-xs rounded border transition-colors ${
                theme === t
                  ? 'bg-blue-600 border-blue-500 text-white'
                  : 'bg-mf-card border-mf-border text-mf-text-secondary hover:bg-mf-hover hover:text-mf-text-primary'
              }`}
            >
              {t === 'light' ? '☀' : '🌙'} {t.charAt(0).toUpperCase() + t.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Font size */}
      <div>
        <div className="text-xs font-semibold text-mf-text-secondary uppercase tracking-wide mb-2">
          Font Size
        </div>
        <div className="flex gap-2">
          {([
            { id: 'small', label: 'S' },
            { id: 'medium', label: 'M' },
            { id: 'large', label: 'L' },
          ] as { id: FontSize; label: string }[]).map(({ id, label }) => (
            <button
              key={id}
              onClick={() => setFontSize(id)}
              className={`flex-1 py-1.5 text-xs rounded border transition-colors ${
                fontSize === id
                  ? 'bg-blue-600 border-blue-500 text-white'
                  : 'bg-mf-card border-mf-border text-mf-text-secondary hover:bg-mf-hover hover:text-mf-text-primary'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        <p className="text-[10px] text-mf-text-muted mt-1.5">
          Scales all text and spacing proportionally.
        </p>
      </div>

      {/* Keyboard shortcuts */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <div className="text-xs font-semibold text-mf-text-secondary uppercase tracking-wide">
            Keyboard Shortcuts
          </div>
          <button
            onClick={resetAll}
            className="text-[10px] text-mf-text-muted hover:text-mf-text-secondary transition-colors"
            title="Reset all shortcuts to defaults"
          >
            Reset all
          </button>
        </div>
        <p className="text-[10px] text-mf-text-muted mb-2">
          Click a key badge, then press the new shortcut key.
        </p>
        <div className="bg-mf-card rounded border border-mf-border px-2 py-1 divide-y divide-mf-border/50">
          {shortcutIds.map((id) => (
            <ShortcutRow key={id} id={id} />
          ))}
        </div>
      </div>

      <p className="text-[10px] text-mf-text-muted pt-2 border-t border-mf-border">
        Settings are saved automatically.
      </p>
    </div>
  )
}
