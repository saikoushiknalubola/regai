import { useState } from 'react'
import { Tag, Copy } from 'lucide-react'
import toast from 'react-hot-toast'
import clsx from 'clsx'
import { classifySeverity, checkDuplicate } from '@/utils/api'

type Mode = 'severity' | 'duplicate'

const SEVERITY_COLOR: Record<string, string> = {
  death: 'badge-critical',
  disability: 'bg-orange-100 text-orange-700',
  hospitalisation: 'badge-major',
  others: 'badge-neutral',
}

export default function ClassificationPage() {
  const [mode, setMode] = useState<Mode>('severity')
  const [text, setText] = useState('')
  const [caseId, setCaseId] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<any>(null)

  const handle = async () => {
    if (!text.trim()) return
    setLoading(true); setResult(null)
    try {
      const data = mode === 'severity'
        ? await classifySeverity(text, caseId || 'case_001')
        : await checkDuplicate(text, caseId || 'case_001')
      setResult(data); toast.success('Classification complete')
    } catch {} finally { setLoading(false) }
  }

  return (
    <div className="p-8 max-w-5xl mx-auto animate-fade-in">
      <div className="mb-7">
        <div className="section-title mb-2">Module 4</div>
        <h1 className="text-2xl font-700 text-ink-800">Classification</h1>
        <p className="mt-1.5 text-sm text-ink-500">
          Classify SAE cases by severity (ICH E2A criteria) and detect potential duplicate
          filings using fuzzy matching and semantic similarity.
        </p>
      </div>

      <div className="flex gap-0.5 bg-surface-overlay rounded-md p-1 w-fit mb-6">
        {([['severity', 'Severity Classification'], ['duplicate', 'Duplicate Detection']] as const).map(([id, label]) => (
          <button key={id} onClick={() => { setMode(id); setResult(null) }}
            className={clsx('px-4 py-1.5 rounded text-sm transition-all duration-150',
              mode === id ? 'bg-white text-ink-800 shadow-card font-medium' : 'text-ink-500 hover:text-ink-700')}>
            {label}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-4">
          <div>
            <label className="label">Case ID</label>
            <input className="input" placeholder="e.g. SAE-2024-00123"
              value={caseId} onChange={e => setCaseId(e.target.value)} />
          </div>
          <div>
            <label className="label">SAE Case Text</label>
            <textarea className="input min-h-[260px] resize-y font-mono text-xs"
              placeholder="Paste SAE case narration or report text..."
              value={text} onChange={e => setText(e.target.value)} />
          </div>
          <button onClick={handle} disabled={loading || !text.trim()}
            className="btn-primary w-full justify-center">
            <Tag size={15} />
            {loading ? 'Classifying...' : mode === 'severity' ? 'Classify Severity' : 'Check for Duplicates'}
          </button>
        </div>

        <div className="space-y-4">
          {result && mode === 'severity' && (
            <div className="space-y-4 animate-slide-up">
              <div className="card p-5">
                <div className="section-title mb-3">Severity Classification</div>
                <div className="flex items-center gap-3 mb-4">
                  <span className={clsx('badge text-sm px-3 py-1', SEVERITY_COLOR[result.severity] || 'badge-neutral')}>
                    {result.severity?.toUpperCase()}
                  </span>
                  <div>
                    <div className="text-xs text-ink-400">Confidence</div>
                    <div className="font-mono font-medium text-ink-800">{(result.confidence * 100).toFixed(1)}%</div>
                  </div>
                  <div>
                    <div className="text-xs text-ink-400">Model</div>
                    <div className="font-mono text-xs text-ink-600">{result.model_used}</div>
                  </div>
                </div>
                <div className="progress-bar mb-1">
                  <div className={clsx('progress-fill',
                    result.severity === 'death' ? 'bg-signal-red' :
                    result.severity === 'disability' ? 'bg-orange-500' :
                    result.severity === 'hospitalisation' ? 'bg-signal-amber' : 'bg-ink-300')}
                    style={{ width: `${result.confidence * 100}%` }} />
                </div>
              </div>

              {result.evidence?.length > 0 && (
                <div className="card p-4">
                  <div className="section-title mb-2">Evidence Keywords</div>
                  <div className="flex flex-wrap gap-1.5">
                    {result.evidence.map((e: string) => (
                      <span key={e} className="badge-neutral font-mono">{e}</span>
                    ))}
                  </div>
                </div>
              )}

              {result.rule_signals && (
                <div className="card p-4">
                  <div className="section-title mb-3">Rule-Based Signal Breakdown</div>
                  <div className="space-y-2">
                    {Object.entries(result.rule_signals).map(([severity, signal]: [string, any]) => (
                      <div key={severity} className="flex items-center justify-between text-xs">
                        <span className={clsx('badge', SEVERITY_COLOR[severity] || 'badge-neutral')}>
                          {severity}
                        </span>
                        <span className="text-ink-500">{signal.count} keyword{signal.count !== 1 ? 's' : ''}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {result && mode === 'duplicate' && (
            <div className="space-y-4 animate-slide-up">
              <div className={clsx('card p-5 border-2', result.is_duplicate ? 'border-signal-red/40 bg-red-50/40' : 'border-signal-green/40 bg-green-50/40')}>
                <div className="section-title mb-2">Duplicate Check Result</div>
                <div className="flex items-center gap-3">
                  <span className={result.is_duplicate ? 'badge-critical text-sm px-3 py-1' : 'badge-ok text-sm px-3 py-1'}>
                    {result.is_duplicate ? 'POTENTIAL DUPLICATE' : 'NOT A DUPLICATE'}
                  </span>
                  <span className="font-mono text-xs text-ink-500">
                    similarity: {(result.similarity_score * 100).toFixed(1)}%
                  </span>
                </div>
                {result.duplicate_of && (
                  <div className="mt-3 text-sm text-ink-700">
                    Matches case: <span className="font-mono font-medium">{result.duplicate_of}</span>
                  </div>
                )}
                <div className="mt-2 text-xs text-ink-500">{result.action}</div>
                <div className="mt-1 text-xs text-ink-400 font-mono">Method: {result.method}</div>
              </div>

              {result.matching_fields?.length > 0 && (
                <div className="card p-4">
                  <div className="section-title mb-2">Matching Fields</div>
                  <div className="flex flex-wrap gap-1.5">
                    {result.matching_fields.map((f: string) => (
                      <span key={f} className="badge-major font-mono">{f}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {!result && !loading && (
            <div className="flex flex-col items-center justify-center h-64 text-ink-300 text-sm gap-2">
              <Tag size={32} strokeWidth={1.5} />
              <span>Classification result will appear here</span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
