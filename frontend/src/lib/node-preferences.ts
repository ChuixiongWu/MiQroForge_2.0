// ─── Node Parameter Preferences ───────────────────────────────────────────────
//
// Two-level preference system:
//   1. Global:  userdata/node_preferences.yaml (via API, shared across projects)
//   2. Project: localStorage per project (overrides global, resets on restart)
//
// Loading:  loadGlobalPrefs() at startup
// Query:    getNodePrefs() → project localStorage → global → defaults
// Save:     Inspector gear → saveProjectNodePref (localStorage, project-level)
//           Node Repository → saveGlobalPrefs (API, global)
// ──────────────────────────────────────────────────────────────────────────────

export interface NodePreference {
  collapsedParams: string[]
  hiddenParams: string[]
}

const STORAGE_PREFIX = 'mf-node-pref-'
const PROJECT_PREFIX = 'mf-project-node-pref-'

/** 默认折叠的参数名 */
const DEFAULT_COLLAPSED = new Set([
  'max_scf',
  'eps_scf',
  'max_iter',
  'smearing',
  'electronic_temperature',
  'reference',
  'scf_type',
  'rel_cutoff',
  'mem_gb',
  'scf_convergence',
  'diis',
])

// ─── Global preferences (from API) ───────────────────────────────────────────

let _globalPrefs: Record<string, NodePreference> = {}
let _globalPrefsLoaded = false
let _showDeprecated = false
const _listeners: Set<() => void> = new Set()

/**
 * Subscribe to global prefs changes (for reactive UI updates).
 * Returns an unsubscribe function.
 */
export function onGlobalPrefsChange(listener: () => void): () => void {
  _listeners.add(listener)
  return () => { _listeners.delete(listener) }
}

export function isGlobalPrefsLoaded(): boolean {
  return _globalPrefsLoaded
}

/**
 * Load global preferences from the backend API.
 * Call once at app startup.
 */
export async function loadGlobalPrefs(): Promise<void> {
  try {
    const res = await fetch('/api/v1/nodes/preferences')
    if (!res.ok) return
    const data = await res.json()
    const raw = data.node_preferences ?? {}
    _showDeprecated = data.show_deprecated ?? false
    _globalPrefs = {}
    for (const [name, entry] of Object.entries(raw)) {
      const e = entry as { collapsed_params?: string[]; hidden_params?: string[] }
      _globalPrefs[name] = {
        collapsedParams: e.collapsed_params ?? [],
        hiddenParams: e.hidden_params ?? [],
      }
    }
  } catch {
    // API unavailable — use defaults only
  }
  _globalPrefsLoaded = true
  for (const fn of _listeners) fn()
}

/**
 * Save all global preferences to the backend API.
 */
export async function saveGlobalPrefs(
  prefs: Record<string, NodePreference>,
): Promise<void> {
  try {
    const node_preferences: Record<string, { collapsed_params: string[]; hidden_params: string[] }> = {}
    for (const [name, pref] of Object.entries(prefs)) {
      node_preferences[name] = {
        collapsed_params: pref.collapsedParams,
        hidden_params: pref.hiddenParams,
      }
    }
    await fetch('/api/v1/nodes/preferences', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ show_deprecated: _showDeprecated, node_preferences }),
    })
    // Update local cache
    _globalPrefs = prefs
    for (const fn of _listeners) fn()
  } catch {
    // API unavailable
  }
}

// ─── Project-level preferences (localStorage) ────────────────────────────────

let _currentProjectId: string | null = null

export function setPreferenceProjectId(projectId: string | null): void {
  _currentProjectId = projectId
}

function projectStorageKey(nodeName: string): string {
  return `${PROJECT_PREFIX}${_currentProjectId ?? 'default'}-${nodeName}`
}

/**
 * Get project-level preference override from localStorage.
 */
function getProjectPref(nodeName: string): NodePreference | null {
  try {
    const raw = localStorage.getItem(projectStorageKey(nodeName))
    if (raw) {
      const parsed = JSON.parse(raw) as NodePreference
      return {
        collapsedParams: parsed.collapsedParams ?? [],
        hiddenParams: parsed.hiddenParams ?? [],
      }
    }
  } catch {
    // ignore
  }
  return null
}

/**
 * Save project-level preference to localStorage.
 */
export function saveProjectNodePref(nodeName: string, pref: NodePreference): void {
  try {
    localStorage.setItem(projectStorageKey(nodeName), JSON.stringify(pref))
  } catch {
    // localStorage full
  }
}

// ─── Query interface ─────────────────────────────────────────────────────────

/**
 * Get preferences for a node: project override → global → defaults.
 */
export function getNodePrefs(nodeName: string): NodePreference {
  // 1. Project-level override
  const projectPref = getProjectPref(nodeName)
  if (projectPref) return projectPref

  // 2. Global preference
  const global = _globalPrefs[nodeName]
  if (global) return global

  // 3. Defaults
  return {
    collapsedParams: Array.from(DEFAULT_COLLAPSED),
    hiddenParams: [],
  }
}

/**
 * Backward-compatible: save prefs (defaults to project-level localStorage).
 */
export function saveNodePrefs(nodeName: string, prefs: NodePreference): void {
  saveProjectNodePref(nodeName, prefs)
}

// ─── Utility ─────────────────────────────────────────────────────────────────

export type ParamVisibility = 'visible' | 'collapsed' | 'hidden'

export function classifyParams(
  paramNames: string[],
  prefs: NodePreference,
): Record<string, ParamVisibility> {
  const result: Record<string, ParamVisibility> = {}
  for (const name of paramNames) {
    if (prefs.hiddenParams.includes(name)) {
      result[name] = 'hidden'
    } else if (prefs.collapsedParams.includes(name)) {
      result[name] = 'collapsed'
    } else {
      result[name] = 'visible'
    }
  }
  return result
}

/**
 * Get all global prefs (for Node Repository page editing).
 */
export function getAllGlobalPrefs(): Record<string, NodePreference> {
  return { ..._globalPrefs }
}

/**
 * Get the global show_deprecated setting.
 */
export function getShowDeprecated(): boolean {
  return _showDeprecated
}

/**
 * Set and persist the global show_deprecated setting.
 */
export async function setShowDeprecated(value: boolean): Promise<void> {
  _showDeprecated = value
  await saveGlobalPrefs(_globalPrefs) // persists both show_deprecated + prefs
  for (const fn of _listeners) fn()
}
