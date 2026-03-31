import { useEffect, useState } from 'react'
import { ArrowLeft } from 'lucide-react'

// Import settings store so theme is applied on this page too
import '../../stores/settings-store'

interface UnitEntry {
  symbol: string
  dimension: string
  to_si_factor: number
}

interface UnitsData {
  total_units: number
  total_dimensions: number
  dimensions: Record<string, UnitEntry[]>
}

const SI_LABELS: Record<string, string> = {
  energy: 'J (Joule)',
  length: 'm (metre)',
  pressure: 'Pa (Pascal)',
  temperature: 'K (Kelvin)',
  angle: 'rad (radian)',
  force: 'N (Newton)',
  time: 's (second)',
}

export function UnitsPage() {
  const [data, setData] = useState<UnitsData | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    document.title = 'Units Reference — MiQroForge'
    fetch('/api/v1/nodes/units')
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then(setData)
      .catch((e) => setError(e.message))
  }, [])

  const sorted = data
    ? Object.entries(data.dimensions).sort(([a], [b]) => a.localeCompare(b))
    : []

  return (
    <div className="min-h-screen bg-mf-base text-mf-text-primary">
      {/* Page header */}
      <header className="sticky top-0 z-10 bg-mf-panel border-b border-mf-border">
        <div className="max-w-5xl mx-auto px-6 py-3 flex items-center gap-4">
          <a
            href="/"
            className="flex items-center gap-1.5 text-xs text-mf-text-muted hover:text-mf-text-primary transition-colors"
          >
            <ArrowLeft size={14} />
            Canvas
          </a>
          <div className="w-px h-5 bg-mf-border" />
          <div className="flex items-center gap-2">
            <img src="/logo.png" alt="MiQroForge" className="h-5 w-auto" />
            <h1 className="text-sm font-semibold tracking-tight">Units Reference</h1>
          </div>
          {data && (
            <span className="ml-auto text-[11px] text-mf-text-muted">
              {data.total_units} units / {data.total_dimensions} dimensions
            </span>
          )}
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-6">
        {/* Intro */}
        <div className="mb-6 p-4 rounded-lg border border-mf-border bg-mf-panel">
          <h2 className="text-xs font-semibold text-mf-text-secondary uppercase tracking-wide mb-2">
            Connection Rules for Physical Quantity Ports
          </h2>
          <ul className="text-[12px] text-mf-text-muted space-y-1 list-disc list-inside">
            <li>Two PQ ports can connect when they share the same <strong className="text-mf-text-primary">dimension</strong> (e.g. both are <code className="text-blue-400">energy</code>) and the same <strong className="text-mf-text-primary">shape</strong> (e.g. both are <code className="text-blue-400">scalar</code>).</li>
            <li>Different units within the same dimension are <strong className="text-mf-text-primary">automatically converted</strong> at runtime via their SI factors.</li>
            <li>Ports with different dimensions (e.g. <code className="text-blue-400">energy</code> vs <code className="text-blue-400">length</code>) cannot connect.</li>
          </ul>
        </div>

        {/* Error */}
        {error && (
          <div className="text-sm text-red-400 bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3 mb-6">
            Failed to load units: {error}
          </div>
        )}

        {/* Loading */}
        {!data && !error && (
          <div className="text-sm text-mf-text-muted animate-pulse py-8 text-center">Loading units...</div>
        )}

        {/* Dimension cards grid */}
        {data && (
          <div className="grid gap-4" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))' }}>
            {sorted.map(([dimension, units]) => (
              <DimensionCard key={dimension} dimension={dimension} units={units} />
            ))}
          </div>
        )}
      </main>
    </div>
  )
}


function DimensionCard({ dimension, units }: { dimension: string; units: UnitEntry[] }) {
  const siLabel = SI_LABELS[dimension] ?? '?'

  return (
    <div className="rounded-lg border border-mf-border bg-mf-panel overflow-hidden">
      {/* Card header */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-mf-hover/40 border-b border-mf-border">
        <span className="text-[13px] font-semibold text-mf-text-primary capitalize">{dimension}</span>
        <span className="text-[11px] text-mf-text-muted">SI: {siLabel}</span>
      </div>
      {/* Unit rows */}
      <table className="w-full text-[12px]">
        <thead>
          <tr className="text-mf-text-muted border-b border-mf-border">
            <th className="text-left px-4 py-1.5 font-medium">Symbol</th>
            <th className="text-right px-4 py-1.5 font-medium">to SI factor</th>
          </tr>
        </thead>
        <tbody>
          {units.map((u, i) => (
            <tr
              key={u.symbol}
              className={`hover:bg-mf-hover/30 ${i < units.length - 1 ? 'border-b border-mf-border/40' : ''}`}
            >
              <td className="px-4 py-1.5 font-mono text-mf-text-primary">{u.symbol}</td>
              <td className="px-4 py-1.5 text-right font-mono text-mf-text-muted">{formatFactor(u.to_si_factor)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}


function formatFactor(f: number): string {
  if (f === 1) return '1'
  if (f < 0.01 || f > 1e6) return f.toExponential(3)
  return f.toPrecision(4)
}
