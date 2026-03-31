import React, { useState, useEffect, useRef } from 'react'
import { CheckCircle, AlertCircle, AlertTriangle, Info } from 'lucide-react'
import { useWorkflowValidation } from '../../hooks/useWorkflowValidation'
import { useWorkflowStore } from '../../stores/workflow-store'
import { useSavedWorkflowsStore } from '../../stores/saved-workflows-store'
import { workflowsApi } from '../../api/workflows-api'
import { useRunOverlayStore } from '../../stores/run-overlay-store'
import { useUIStore } from '../../stores/ui-store'
import type { IssueSeverity, ValidationIssue } from '../../types/workflow'

// ─── Issue row ────────────────────────────────────────────────────────────────

function IssueRow({ issue }: { issue: ValidationIssue }) {
  const icons: Record<IssueSeverity, React.ReactNode> = {
    error:   <AlertCircle   size={12} className="text-red-400 flex-shrink-0 mt-0.5" />,
    warning: <AlertTriangle size={12} className="text-yellow-400 flex-shrink-0 mt-0.5" />,
    info:    <Info          size={12} className="text-blue-400 flex-shrink-0 mt-0.5" />,
  }
  return (
    <div className="flex gap-1.5 text-xs py-0.5">
      {icons[issue.severity]}
      <span className={
        issue.severity === 'error'   ? 'text-red-300' :
        issue.severity === 'warning' ? 'text-yellow-300' :
        'text-mf-text-secondary'
      }>
        {issue.node_id && <span className="font-mono text-mf-text-muted">[{issue.node_id}] </span>}
        {issue.message}
      </span>
    </div>
  )
}

// ─── Stage type ───────────────────────────────────────────────────────────────

type Stage = 'idle' | 'validating' | 'validated' | 'submitting' | 'submitted' | 'error'

// ─── WorkflowPanel ────────────────────────────────────────────────────────────

export function WorkflowPanel() {
  const { validate, getYaml } = useWorkflowValidation()
  const { nodes, edges, meta, validationResult } = useWorkflowStore()
  const { saveRunSnapshot } = useSavedWorkflowsStore()
  const { setActiveRun } = useRunOverlayStore()
  const runTrigger = useUIStore((s) => s.runTrigger)

  const [stage, setStage] = useState<Stage>('idle')
  const [submitResult, setSubmitResult] = useState<{ name: string } | null>(null)
  const [submitError, setSubmitError] = useState<string | null>(null)

  // ── Keyboard shortcut / TopBar button: auto-run when trigger increments ──
  const lastTriggerRef = useRef(0)
  useEffect(() => {
    if (runTrigger === 0 || runTrigger === lastTriggerRef.current) return
    lastTriggerRef.current = runTrigger
    handleRun()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runTrigger])

  // ── Validate → Submit ────────────────────────────────────────────────────

  const handleRun = async () => {
    if (nodes.length === 0) return

    setStage('validating')
    setSubmitResult(null)
    setSubmitError(null)

    const result = await validate()
    if (!result) {
      setStage('error')
      return
    }

    setStage('validated')

    if (!result.valid) {
      return   // Errors found — let user review
    }

    setStage('submitting')
    try {
      const mfYaml = getYaml()
      const resp = await workflowsApi.submit(mfYaml)
      setSubmitResult({ name: resp.workflow_name })
      saveRunSnapshot(resp.workflow_name, meta, nodes, edges)
      setActiveRun(resp.workflow_name)
      setStage('submitted')
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : String(err))
      setStage('error')
    }
  }

  const buttonLabel =
    stage === 'validating' ? 'Validating…' :
    stage === 'submitting' ? 'Submitting…' :
    '▶ Run Workflow'

  const buttonDisabled =
    nodes.length === 0 ||
    stage === 'validating' ||
    stage === 'submitting'

  return (
    <div className="w-72 mf-panel border-l border-r-0 flex-shrink-0">
      <div className="px-3 py-2 border-b border-mf-border">
        <span className="text-xs font-semibold text-mf-text-secondary uppercase tracking-wide">
          Run Workflow
        </span>
      </div>

      <div className="flex-1 overflow-y-auto mf-scroll">
        <div className="space-y-3 p-3">

          {/* ── Main Run button ─────────────────────────────────────────── */}
          <button
            onClick={handleRun}
            disabled={buttonDisabled}
            className="w-full py-2 bg-green-700 hover:bg-green-600 disabled:bg-green-900 disabled:cursor-not-allowed text-white text-xs rounded font-semibold transition-colors flex items-center justify-center gap-1.5"
          >
            {(stage === 'validating' || stage === 'submitting') && (
              <span className="inline-block w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            )}
            {buttonLabel}
          </button>

          {nodes.length === 0 && (
            <p className="text-[11px] text-mf-text-muted text-center">
              Add nodes to the canvas before running.
            </p>
          )}

          {/* ── Validation results ──────────────────────────────────────── */}
          {validationResult && (
            <div className="space-y-1">
              <div className={`flex items-center gap-1.5 text-xs font-medium ${
                validationResult.valid ? 'text-green-400' : 'text-red-400'
              }`}>
                {validationResult.valid
                  ? <><CheckCircle size={13} /> Valid</>
                  : <><AlertCircle size={13} /> {validationResult.errors.length} error{validationResult.errors.length !== 1 ? 's' : ''}</>
                }
                <span className="text-mf-text-muted font-normal ml-auto">
                  {validationResult.errors.length}E · {validationResult.warnings.length}W · {validationResult.infos.length}I
                </span>
              </div>

              {[...validationResult.errors, ...validationResult.warnings, ...validationResult.infos].length > 0 && (
                <div className="bg-mf-card rounded p-2 max-h-40 overflow-y-auto mf-scroll space-y-0.5">
                  {[...validationResult.errors, ...validationResult.warnings, ...validationResult.infos].map((issue, i) => (
                    <IssueRow key={i} issue={issue} />
                  ))}
                </div>
              )}
            </div>
          )}

          {/* ── Submit result ───────────────────────────────────────────── */}
          {submitResult && (
            <div className="flex items-center gap-1.5 text-xs text-green-400 bg-green-500/10 border border-green-500/20 rounded px-2 py-1.5">
              <CheckCircle size={12} />
              <span>Submitted: <span className="font-mono">{submitResult.name}</span></span>
            </div>
          )}

          {/* ── Submit error ────────────────────────────────────────────── */}
          {submitError && (
            <div className="flex items-start gap-1.5 text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded px-2 py-1.5 break-all">
              <AlertCircle size={12} className="flex-shrink-0 mt-0.5" />
              <span>{submitError}</span>
            </div>
          )}

        </div>
      </div>
    </div>
  )
}
