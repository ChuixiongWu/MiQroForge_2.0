import { useEffect, useState } from 'react'
import { ArrowLeft } from 'lucide-react'

import '../../stores/settings-store'

interface SharedParamEntry {
  display_name: string
  gaussian: string | null
  psi4: string | null
  orca: string | null
  cp2k: string | null
}

interface SharedParamsData {
  functionals: Record<string, SharedParamEntry>
  basis_sets: Record<string, SharedParamEntry>
  dispersions: Record<string, SharedParamEntry>
}

const CATEGORY_INFO: Record<string, { title: string; description: string }> = {
  functionals: {
    title: 'DFT Functionals',
    description: 'Exchange-correlation functionals used in DFT calculations. Canonical names are translated to software-native keywords at compile time.',
  },
  basis_sets: {
    title: 'Basis Sets',
    description: 'Atomic orbital basis sets define the accuracy of molecular calculations. Larger basis sets give more accurate results but cost more compute. null = not supported by that software.',
  },
  dispersions: {
    title: 'Dispersion Corrections',
    description: 'Empirical corrections for van der Waals interactions. Essential for non-covalent interactions, layered materials, and molecular crystals.',
  },
}

export function SharedParamsPage() {
  const [data, setData] = useState<SharedParamsData | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    document.title = 'Shared Parameters — MiQroForge'
    fetch('/api/v1/nodes/shared-params')
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then(setData)
      .catch((e) => setError(e.message))
  }, [])

  return (
    <div className="h-screen flex flex-col bg-mf-base text-mf-text-primary">
      {/* Header */}
      <header className="sticky top-0 z-10 bg-mf-panel border-b border-mf-border flex-shrink-0">
        <div className="max-w-5xl mx-auto px-6 py-3 flex items-center gap-4">
          <a
            href="/"
            className="flex items-center gap-1.5 text-xs text-mf-text-muted hover:text-mf-text-primary transition-colors"
          >
            <ArrowLeft size={14} />
            Gallery
          </a>
          <div className="w-px h-5 bg-mf-border" />
          <div className="flex items-center gap-2">
            <img src="/logo.png" alt="MiQroForge" className="h-5 w-auto" />
            <h1 className="text-sm font-semibold tracking-tight">Shared Parameters</h1>
          </div>
        </div>
      </header>

      <main className="flex-1 overflow-y-auto max-w-5xl mx-auto px-6 py-6 w-full">
        {/* Intro */}
        <div className="mb-6 p-4 rounded-lg border border-mf-border bg-mf-panel">
          <h2 className="text-xs font-semibold text-mf-text-secondary uppercase tracking-wide mb-2">
            Cross-Software Parameter Translation
          </h2>
          <p className="text-[12px] text-mf-text-muted">
            Shared parameters are canonical names (e.g. <code className="text-blue-400">PBE0</code>,{' '}
            <code className="text-blue-400">def2-SVP</code>, <code className="text-blue-400">D3BJ</code>) that
            the compiler automatically translates to each software's native keywords.
            A value of <code className="text-red-400">null</code> means the parameter is not available for that software.
          </p>
        </div>

        {/* Error */}
        {error && (
          <div className="text-sm text-red-400 bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3 mb-6">
            Failed to load shared parameters: {error}
          </div>
        )}

        {/* Loading */}
        {!data && !error && (
          <div className="text-sm text-mf-text-muted animate-pulse py-8 text-center">Loading shared parameters...</div>
        )}

        {/* Tables */}
        {data && (
          <div className="grid gap-6">
            {(Object.entries(CATEGORY_INFO) as [string, { title: string; description: string }][]).map(
              ([key, info]) => {
                const entries = data[key as keyof SharedParamsData]
                if (!entries || Object.keys(entries).length === 0) return null
                return (
                  <ParamTable
                    key={key}
                    title={info.title}
                    description={info.description}
                    entries={entries}
                  />
                )
              },
            )}
          </div>
        )}
      </main>
    </div>
  )
}

function ParamTable({
  title,
  description,
  entries,
}: {
  title: string
  description: string
  entries: Record<string, SharedParamEntry>
}) {
  const sorted = Object.entries(entries).sort(([a], [b]) => a.localeCompare(b))

  return (
    <div className="rounded-lg border border-mf-border bg-mf-panel overflow-hidden">
      <div className="px-4 py-3 bg-mf-hover/40 border-b border-mf-border">
        <h3 className="text-[13px] font-semibold text-mf-text-primary">{title}</h3>
        <p className="text-[11px] text-mf-text-muted mt-0.5">{description}</p>
      </div>
      <table className="w-full text-[12px]">
        <thead>
          <tr className="text-mf-text-muted border-b border-mf-border">
            <th className="text-left px-4 py-1.5 font-medium">Canonical</th>
            <th className="text-left px-4 py-1.5 font-medium">Display Name</th>
            <th className="text-center px-4 py-1.5 font-mono font-medium">Gaussian</th>
            <th className="text-center px-4 py-1.5 font-mono font-medium">ORCA</th>
            <th className="text-center px-4 py-1.5 font-mono font-medium">Psi4</th>
            <th className="text-center px-4 py-1.5 font-mono font-medium">CP2K</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map(([canonical, entry], i) => (
            <tr
              key={canonical}
              className={`hover:bg-mf-hover/30 ${i < sorted.length - 1 ? 'border-b border-mf-border/40' : ''}`}
            >
              <td className="px-4 py-1.5 font-mono text-mf-text-primary font-medium">{canonical}</td>
              <td className="px-4 py-1.5 text-mf-text-muted">{entry.display_name}</td>
              <td className="text-center px-4 py-1.5 font-mono">
                <CellValue value={entry.gaussian} />
              </td>
              <td className="text-center px-4 py-1.5 font-mono">
                <CellValue value={entry.orca} />
              </td>
              <td className="text-center px-4 py-1.5 font-mono">
                <CellValue value={entry.psi4} />
              </td>
              <td className="text-center px-4 py-1.5 font-mono">
                <CellValue value={entry.cp2k} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function CellValue({ value }: { value: string | null }) {
  if (value === null) {
    return <span className="text-red-400/60 text-[10px]">null</span>
  }
  return <span className="text-mf-text-primary">{value}</span>
}
