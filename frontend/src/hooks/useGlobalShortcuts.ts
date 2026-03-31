import { useEffect } from 'react'
import { useUIStore } from '../stores/ui-store'
import { useShortcutsStore, keyMatch } from '../stores/shortcuts-store'

/**
 * Registers global keyboard shortcuts for panel toggles and workflow actions.
 * Must be mounted once at the app level (AppLayout).
 */
export function useGlobalShortcuts() {
  const togglePalette = useUIStore((s) => s.togglePalette)
  const toggleFiles   = useUIStore((s) => s.toggleFiles)
  const setRightPanel = useUIStore((s) => s.setRightPanel)
  const rightPanel    = useUIStore((s) => s.rightPanel)
  const triggerRun    = useUIStore((s) => s.triggerRun)

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement
      if (
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.isContentEditable
      ) return

      const bindings = useShortcutsStore.getState().bindings

      if (keyMatch(e, bindings.togglePalette)) {
        e.preventDefault()
        togglePalette()
        return
      }

      if (keyMatch(e, bindings.toggleFiles)) {
        e.preventDefault()
        toggleFiles()
        return
      }

      if (keyMatch(e, bindings.toggleRuns)) {
        e.preventDefault()
        setRightPanel(rightPanel === 'runs' ? null : 'runs')
        return
      }

      if (keyMatch(e, bindings.runWorkflow)) {
        e.preventDefault()
        // TopBar listens to runTrigger and performs the full validate → submit flow
        triggerRun()
        return
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [togglePalette, toggleFiles, setRightPanel, rightPanel, triggerRun])
}
