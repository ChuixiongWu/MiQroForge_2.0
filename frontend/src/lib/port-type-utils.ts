import type { PortCategory } from '../types/nodespec'

// ─── Color maps ───────────────────────────────────────────────────────────────

export const PORT_COLORS: Record<PortCategory, string> = {
  physical_quantity:    '#f59e0b',
  software_data_package: '#3b82f6',
  logic_value:          '#22c55e',
  report_object:        '#a855f7',
}

export const PORT_LABELS: Record<PortCategory, string> = {
  physical_quantity:     'Physical',
  software_data_package: 'Software',
  logic_value:           'Logic',
  report_object:         'Report',
}

export const PORT_DOT_CLASS: Record<PortCategory, string> = {
  physical_quantity:     'port-dot port-dot-physical',
  software_data_package: 'port-dot port-dot-software',
  logic_value:           'port-dot port-dot-logic',
  report_object:         'port-dot port-dot-report',
}

export const PORT_HANDLE_CLASS: Record<PortCategory, string> = {
  physical_quantity:     'mf-handle mf-handle-physical',
  software_data_package: 'mf-handle mf-handle-software',
  logic_value:           'mf-handle mf-handle-logic',
  report_object:         'mf-handle mf-handle-report',
}

// ─── Category label helpers ───────────────────────────────────────────────────

export function portCategoryLabel(cat: PortCategory): string {
  return PORT_LABELS[cat] ?? cat
}

export function portColor(cat: PortCategory): string {
  return PORT_COLORS[cat] ?? '#6b7280'
}

// ─── Detail string parser ─────────────────────────────────────────────────────
// e.g. "orca/gbw-file" → { ecosystem: "orca", subtype: "gbw-file" }
// e.g. "energy/Ha/scalar" → { ecosystem: "energy", subtype: "Ha/scalar" }

export function parsePortDetail(detail: string): { ecosystem: string; subtype: string } {
  const parts = detail.split('/')
  return {
    ecosystem: parts[0] ?? '',
    subtype: parts.slice(1).join('/'),
  }
}

// ─── Node type icon ───────────────────────────────────────────────────────────

export function nodeTypeEmoji(category: string): string {
  const lower = category.toLowerCase()
  if (lower.includes('chem') || lower.includes('orca') || lower.includes('gaussian')) return '🧪'
  if (lower.includes('quantum')) return '⚛️'
  if (lower.includes('preprocess') || lower.includes('convert')) return '🔧'
  if (lower.includes('report') || lower.includes('extract') || lower.includes('thermo')) return '📊'
  return '⚙️'
}
