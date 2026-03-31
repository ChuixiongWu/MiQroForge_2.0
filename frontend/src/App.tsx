import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactFlowProvider } from '@xyflow/react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { useEffect } from 'react'

import { TopBar, StatusBar } from './components/layout/TopBar'
import { NodePalette } from './components/palette/NodePalette'
import { WorkflowsSidebar } from './components/palette/WorkflowsSidebar'
import { WorkflowCanvas } from './components/canvas/WorkflowCanvas'
import { NodeInspector } from './components/inspector/NodeInspector'
import { RunsPanel } from './components/runs/RunsPanel'
import { FilesPanel } from './components/files/FilesPanel'
import { SettingsPanel } from './components/settings/SettingsPanel'
import { UnitsPage } from './components/docs/UnitsPage'
import { ChatPanel } from './components/chat/ChatPanel'
import { useUIStore } from './stores/ui-store'
import { useAgentStore } from './stores/agent-store'
import { nodesApi } from './api/nodes-api'
import { setSemanticRegistry } from './lib/semantic-labels'
import { useRunOverlayPolling } from './hooks/useRunOverlayPolling'
import { useGlobalShortcuts } from './hooks/useGlobalShortcuts'

// Import settings store to trigger initial theme/font-size application
import './stores/settings-store'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

// ─── Main canvas layout ─────────────────────────────────────────────────────

function CanvasLayout() {
  const rightPanel      = useUIStore((s) => s.rightPanel)
  const paletteCollapsed = useUIStore((s) => s.paletteCollapsed)
  const filesOpen       = useUIStore((s) => s.filesOpen)
  const selectedNodeId  = useUIStore((s) => s.selectedNodeId)
  const chatOpen        = useAgentStore((s) => s.isOpen)

  // Mount run overlay polling at app level (persists across panel changes)
  useRunOverlayPolling()
  // Mount global keyboard shortcuts
  useGlobalShortcuts()

  // Load semantic registry from API on startup
  useEffect(() => {
    nodesApi.semanticRegistry()
      .then((data) => setSemanticRegistry(data.types))
      .catch(() => { /* silently fall back to hardcoded labels */ })
  }, [])

  return (
    <div className="flex flex-col h-screen bg-mf-base overflow-hidden">
      <TopBar />

      <div className="flex flex-1 min-h-0 overflow-hidden">

        {/* Far left: Files panel (toggled, narrow) */}
        {filesOpen && <FilesPanel />}

        {/* Left column: Node palette + Saved workflows */}
        <div
          className="flex-shrink-0 flex flex-col border-r border-mf-border bg-mf-panel overflow-hidden"
          style={{ width: paletteCollapsed ? 32 : 256 }}
        >
          <div className="flex-1 min-h-0">
            <NodePalette />
          </div>
          {!paletteCollapsed && <WorkflowsSidebar />}
        </div>

        {/* Center: Canvas */}
        <WorkflowCanvas />

        {/* Right: Inspector (always when node selected) */}
        {selectedNodeId && <NodeInspector />}

        {/* Right: Context panel (runs / settings) */}
        {rightPanel === 'runs'      && <RunsPanel />}
        {rightPanel === 'settings'  && <SettingsPanel />}

        {/* Far right: Chat panel (AI Assistant) */}
        {chatOpen && <ChatPanel />}
      </div>

      <StatusBar />
    </div>
  )
}

// ─── App root ─────────────────────────────────────────────────────────────────

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={
            <ReactFlowProvider>
              <CanvasLayout />
            </ReactFlowProvider>
          } />
          <Route path="/ref/units" element={<UnitsPage />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
