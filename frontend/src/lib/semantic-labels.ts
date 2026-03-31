// ─── Human-readable labels for semantic types ────────────────────────────────

// Fallback hardcoded labels (used before API data loads)
export const SEMANTIC_LABELS: Record<string, string> = {
  'geometry-optimization': 'Geometry Optimization',
  'frequency-analysis': 'Frequency Analysis',
  'thermo-extraction': 'Thermo Extraction',
  'single-point-energy': 'Single-Point Energy',
}

// Runtime registry data loaded from API
let _registryLabels: Record<string, string> = {}
let _registryDescriptions: Record<string, string> = {}

/**
 * Load semantic registry data from API response.
 * Call this once at app startup.
 */
export function setSemanticRegistry(types: Record<string, { display_name: string; description: string }>): void {
  _registryLabels = {}
  _registryDescriptions = {}
  for (const [key, entry] of Object.entries(types)) {
    _registryLabels[key] = entry.display_name
    _registryDescriptions[key] = entry.description
  }
}

export function semanticLabel(st: string): string {
  // Prefer API data over hardcoded fallback
  return (
    _registryLabels[st] ??
    SEMANTIC_LABELS[st] ??
    st.replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
  )
}

export function semanticDescription(st: string): string {
  return _registryDescriptions[st] ?? ''
}

// ─── Icons for semantic types ─────────────────────────────────────────────────

export const SEMANTIC_ICONS: Record<string, string> = {
  'geometry-optimization': '⚙️',
  'frequency-analysis': '〜',
  'thermo-extraction': '🌡',
  'single-point-energy': '⚡',
}

export function semanticIcon(st: string): string {
  return SEMANTIC_ICONS[st] ?? '◈'
}

// ─── Shared picker option type (Palette → Canvas drag protocol) ───────────────

export interface PickerOption {
  nodeName: string
  software: string | null
  label: string   // display_name
}
