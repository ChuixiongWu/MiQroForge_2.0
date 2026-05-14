import { create } from 'zustand'

// 'files' and 'inspector' are no longer right-panel slots:
//  - Files has its own toggle on the left side
//  - Inspector is always shown when a node is selected
export type RightPanel = 'runs' | null

interface UIState {
  selectedNodeId: string | null
  rightPanel: RightPanel
  paletteCollapsed: boolean
  filesOpen: boolean
  yamlEditorOpen: boolean
  notification: { type: 'success' | 'error' | 'info'; message: string } | null
  runTrigger: number
  // Set after a successful submission so RunsPanel can auto-open the detail view
  pendingRunName: string | null

  selectNode: (id: string | null) => void
  setRightPanel: (panel: RightPanel) => void
  togglePalette: () => void
  toggleFiles: () => void
  triggerRun: () => void
  setPendingRunName: (name: string | null) => void
  openYamlEditor: () => void
  closeYamlEditor: () => void
  showNotification: (type: 'success' | 'error' | 'info', message: string) => void
  clearNotification: () => void
}

export const useUIStore = create<UIState>((set) => ({
  selectedNodeId: null,
  rightPanel: null,
  paletteCollapsed: false,
  filesOpen: false,
  yamlEditorOpen: false,
  notification: null,
  runTrigger: 0,
  pendingRunName: null,

  selectNode: (id) => set({ selectedNodeId: id }),
  setRightPanel: (panel) => set({ rightPanel: panel }),
  togglePalette: () => set((s) => ({ paletteCollapsed: !s.paletteCollapsed })),
  toggleFiles: () => set((s) => ({ filesOpen: !s.filesOpen })),
  triggerRun: () => set((s) => ({ runTrigger: s.runTrigger + 1 })),
  setPendingRunName: (name) => set({ pendingRunName: name }),
  openYamlEditor:  () => set({ yamlEditorOpen: true }),
  closeYamlEditor: () => set({ yamlEditorOpen: false }),
  showNotification: (type, message) => set({ notification: { type, message } }),
  clearNotification: () => set({ notification: null }),
}))
