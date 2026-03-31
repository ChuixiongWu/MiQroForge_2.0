import { create } from 'zustand'

export type Theme = 'light' | 'dark'
export type FontSize = 'small' | 'medium' | 'large'

interface SettingsState {
  theme: Theme
  fontSize: FontSize
  setTheme: (t: Theme) => void
  setFontSize: (f: FontSize) => void
}

const FONT_SIZE_MAP: Record<FontSize, string> = {
  small:  '13px',
  medium: '15px',
  large:  '17px',
}

// Read from localStorage; default to dark + medium
function loadInitial(): { theme: Theme; fontSize: FontSize } {
  try {
    const raw = localStorage.getItem('mf-settings')
    if (raw) return JSON.parse(raw) as { theme: Theme; fontSize: FontSize }
  } catch {
    // ignore parse errors
  }
  return { theme: 'dark', fontSize: 'medium' }
}

function applyTheme(theme: Theme) {
  document.documentElement.classList.toggle('dark', theme === 'dark')
}

function applyFontSize(fontSize: FontSize) {
  document.documentElement.style.fontSize = FONT_SIZE_MAP[fontSize]
}

function persist(state: { theme: Theme; fontSize: FontSize }) {
  localStorage.setItem('mf-settings', JSON.stringify(state))
}

// Apply immediately (before React renders) to prevent FOUC
const initial = loadInitial()
applyTheme(initial.theme)
applyFontSize(initial.fontSize)

export const useSettingsStore = create<SettingsState>((set) => ({
  theme:    initial.theme,
  fontSize: initial.fontSize,

  setTheme: (theme) => {
    applyTheme(theme)
    set({ theme })
    persist({ theme, fontSize: useSettingsStore.getState().fontSize })
  },

  setFontSize: (fontSize) => {
    applyFontSize(fontSize)
    set({ fontSize })
    persist({ theme: useSettingsStore.getState().theme, fontSize })
  },
}))
