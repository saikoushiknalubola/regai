import { useState } from 'react'
import { ClipboardCheck, AlertTriangle, CheckCircle, XCircle, MinusCircle } from 'lucide-react'
import toast from 'react-hot-toast'
import clsx from 'clsx'
import { checkCompleteness, compareDocuments } from '@/utils/api'

type Mode = 'check' | 'compare'

const DOC_TYPES = [
  { id: 'new_drug_application', label: 'New Drug Application' },
  { id: 'sae_report', label: 'SAE Report' },
]

export default function CompletenessPage() {
  const [mode, setMode] = useState<Mode>('check')
  const [docType, setDocType] = useState('new_drug_application')
  const [textA, setTextA] = useState('')
  const [textB, setTextB] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<any>(null)

  const handleCheck = async () => {
    if (!textA.trim()) return
    setLoading(true); setResult(null)
    try {
      const data = await checkCompleteness(textA, docType)
      setResult(data); toast.success('Completeness check complete')
    } catch {} finally { setLoading(false) }
  }

  const handleCompare = async () => {
    if (!textA.trim() || !textB.trim()) return
    setLoading(true); setResult(null)
    try {
      const data = await compareDocuments(textA, textB)
      setResult(data); toast.success('Comparison complete')
    } catch {} finally { setLoading(false) }
  }

  const statusIcon = (status: string) => {
    if (status === 'present') return <CheckCircle size={13} className="text-signal-green" />
    if (status === 'missing') return <XCircle size={13} className="text-signal-red" />
    return <MinusCircle size={13} className="text-signal-amber" />
  }

  return (
    <div className="p-8 max-w-5xl mx-auto animate-fade-in">
      <div className="mb-7">
        <div className="section-title mb-2">Module 3</div>
        <h1 className="text-2xl font-700 text-ink-800">Completeness & Document Comparison</h1>
        <p className="mt-1.5 text-sm text-ink-500">
          Validate mandatory fields against CDSCO checklist schemas, or run semantic diff
          between two document versions to detect substantive changes.
        </p>
      </div>

      <div className="flex gap-0.5 bg-surface-overlay rounded-md p-1 w-fit mb-6">
        {([['check', 'Completeness Check'], ['compare', 'Version Comparison']] as const).map(([id, label]) => (
          <button key={id} onClick={() => { setMode(id); setResult(null) }}
            className={clsx('px-4 py-1.5 rounded text-sm transition-all duration-150',
              mode === id ? 'bg-white text-ink-800 shadow-card font-medium' : 'text-ink-500 hover:text-ink-700')}>
            {label}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-4">
          {mode === 'check' && (
            <>
              <div>
                <label className="label">Document Type</label>
                <select className="input" value={docType} onChange={e => setDocType(e.target.value)}>
                  {DOC_TYPES.map(d => <option key={d.id} value={d.id}>{d.label}</option>)}
                </select>
              </div>
              <div>
                <label className="label">Document Text</label>
                <textarea className="input min-h-[260px] resize-y font-mono text-xs"
                  placeholder="Paste document text to check completeness..."
                  value={textA} onChange={e => setTextA(e.target.value)} />
              </div>
              <button onClick={handleCheck} disabled={loading || !textA.trim()}
                className="btn-primary w-full justify-center">
                <ClipboardCheck size={15} />
                {loading ? 'Checking...' : 'Check Completeness'}
              </button>
            </>
          )}

          {mode === 'compare' && (
            <>
              <div>
                <label className="label">Version A (Original)</label>
                <textarea className="input min-h-[180px] resize-y font-mono text-xs"
                  placeholder="Paste original document version..."
                  value={textA} onChange={e => setTextA(e.target.value)} />
              </div>
              <div>
                <label className="label">Version B (Revised)</label>
                <textarea className="input min-h-[180px] resize-y font-mono text-xs"
                  placeholder="Paste revised document version..."
                  value={textB} onChange={e => setTextB(e.target.value)} />
              </div>
              <button onClick={handleCompare}
                disabled={loading || !textA.trim() || !textB.trim()}
                className="btn-primary w-full justify-center">
                <ClipboardCheck size={15} />
                {loading ? 'Comparing...' : 'Compare Documents'}
              </button>
            </>
          )}
        </div>

        <div className="space-y-4">
          {result && mode === 'check' && (
            <div className="space-y-4 animate-slide-up">
              <div className="card p-4">
                <div className="flex items-center justify-between mb-3">
                  <div className="section-title">Overall Score</div>
                  <span className={clsx('font-display text-2xl font-700',
                    result.overall_score >= 0.8 ? 'text-signal-green' :
                    result.overall_score >= 0.5 ? 'text-signal-amber' : 'text-signal-red')}>
                    {result.overall_percent}%
                  </span>
                </div>
                <div className="progress-bar mb-3">
                  <div className={clsx('progress-fill',
                    result.overall_score >= 0.8 ? 'bg-signal-green' :
                    result.overall_score >= 0.5 ? 'bg-signal-amber' : 'bg-signal-red')}
                    style={{ width: `${result.overall_percent}%` }} />
                </div>
                <p className="text-xs text-ink-600">{result.verdict}</p>
              </div>

              {result.missing_mandatory?.length > 0 && (
                <div className="card p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <AlertTriangle size={14} className="text-signal-red" />
                    <div className="section-title">Missing Mandatory Fields ({result.missing_mandatory.length})</div>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {result.missing_mandatory.map((f: string) => (
                      <span key={f} className="badge-critical font-mono">{f}</span>
                    ))}
                  </div>
                </div>
              )}

              {result.field_details && (
                <div className="card overflow-hidden">
                  <div className="px-4 py-3 border-b border-surface-border">
                    <div className="section-title">Field Validation</div>
                  </div>
                  <div className="max-h-72 overflow-y-auto scrollbar-thin">
                    <table className="table-base">
                      <thead><tr>
                        <th>Field</th><th>Section</th><th>Status</th><th>Severity</th>
                      </tr></thead>
                      <tbody>
                        {result.field_details.filter((f: any) => f.status !== 'present').map((f: any, i: number) => (
                          <tr key={i}>
                            <td className="font-mono text-xs">{f.field}</td>
                            <td className="text-ink-400">{f.section}</td>
                            <td>
                              <div className="flex items-center gap-1.5">
                                {statusIcon(f.status)}
                                <span className="text-xs capitalize">{f.status}</span>
                              </div>
                            </td>
                            <td>
                              <span className={f.severity === 'mandatory' ? 'badge-critical' : 'badge-neutral'}>
                                {f.severity}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}

          {result && mode === 'compare' && (
            <div className="space-y-4 animate-slide-up">
              <div className="card p-4">
                <div className="section-title mb-3">Change Summary</div>
                <div className="grid grid-cols-2 gap-2 mb-3">
                  {[
                    { label: 'Critical', val: result.critical_changes, cls: 'badge-critical' },
                    { label: 'Major', val: result.major_changes, cls: 'badge-major' },
                    { label: 'Minor', val: result.minor_changes, cls: 'badge-minor' },
                    { label: 'Cosmetic', val: result.cosmetic_changes, cls: 'badge-neutral' },
                  ].map(({ label, val, cls }) => (
                    <div key={label} className="flex justify-between items-center px-3 py-2 bg-surface-raised rounded text-xs">
                      <span className="text-ink-500">{label}</span>
                      <span className={cls}>{val}</span>
                    </div>
                  ))}
                </div>
                <p className="text-xs text-ink-600">{result.summary}</p>
              </div>

              {result.diff_report?.length > 0 && (
                <div className="card overflow-hidden">
                  <div className="px-4 py-3 border-b border-surface-border">
                    <div className="section-title">Changed Sections</div>
                  </div>
                  <div className="max-h-72 overflow-y-auto scrollbar-thin divide-y divide-surface-border">
                    {result.diff_report.filter((c: any) => c.severity !== 'cosmetic').map((chunk: any) => (
                      <div key={chunk.chunk_id} className="p-4">
                        <div className="flex items-center gap-2 mb-2">
                          <span className={clsx('badge',
                            chunk.severity === 'critical' ? 'badge-critical' :
                            chunk.severity === 'major' ? 'badge-major' :
                            chunk.severity === 'minor' ? 'badge-minor' : 'badge-neutral')}>
                            {chunk.severity}
                          </span>
                          <span className="badge-neutral">{chunk.section}</span>
                          <span className="badge-neutral">{chunk.change_type}</span>
                        </div>
                        <p className="text-xs text-ink-500 italic mb-2">{chunk.explanation}</p>
                        {chunk.original && (
                          <div className="text-xs font-mono bg-red-50 text-red-800 rounded p-2 mb-1.5 line-through opacity-70">
                            {chunk.original.slice(0, 200)}{chunk.original.length > 200 ? '...' : ''}
                          </div>
                        )}
                        {chunk.revised && (
                          <div className="text-xs font-mono bg-green-50 text-green-800 rounded p-2">
                            {chunk.revised.slice(0, 200)}{chunk.revised.length > 200 ? '...' : ''}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {!result && !loading && (
            <div className="flex flex-col items-center justify-center h-64 text-ink-300 text-sm gap-2">
              <ClipboardCheck size={32} strokeWidth={1.5} />
              <span>Results will appear here</span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
