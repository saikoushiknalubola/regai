import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, ShieldCheck, Copy, CheckCheck, AlertTriangle } from 'lucide-react'
import toast from 'react-hot-toast'
import clsx from 'clsx'
import { anonymiseText, anonymiseDocument, anonymiseStructured } from '@/utils/api'

type Tab = 'text' | 'document' | 'structured'

export default function AnonymisationPage() {
  const [tab, setTab] = useState<Tab>('text')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [inputText, setInputText] = useState('')
  const [sensitiveColumns, setSensitiveColumns] = useState('')
  const [copied, setCopied] = useState(false)

  const onDrop = useCallback(async (files: File[]) => {
    if (!files[0]) return
    setLoading(true)
    setResult(null)
    try {
      const data = tab === 'structured'
        ? await anonymiseStructured(files[0], sensitiveColumns)
        : await anonymiseDocument(files[0], true)
      setResult(data)
      toast.success('Anonymisation complete')
    } catch {
      // handled by api interceptor
    } finally {
      setLoading(false)
    }
  }, [tab, sensitiveColumns])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    maxFiles: 1,
    accept: tab === 'structured'
      ? { 'text/csv': ['.csv'] }
      : { 'application/pdf': ['.pdf'], 'text/plain': ['.txt'], 'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'] }
  })

  const handleTextSubmit = async () => {
    if (!inputText.trim()) return
    setLoading(true)
    setResult(null)
    try {
      const data = await anonymiseText(inputText)
      setResult(data)
      toast.success('Anonymisation complete')
    } catch {
      //
    } finally {
      setLoading(false)
    }
  }

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const TABS: { id: Tab; label: string }[] = [
    { id: 'text', label: 'Text Input' },
    { id: 'document', label: 'Document Upload' },
    { id: 'structured', label: 'Structured Data (CSV)' },
  ]

  return (
    <div className="p-8 max-w-5xl mx-auto animate-fade-in">
      <div className="mb-7">
        <div className="section-title mb-2">Module 1</div>
        <h1 className="text-2xl font-700 text-ink-800">Anonymisation</h1>
        <p className="mt-1.5 text-sm text-ink-500">
          Two-step pipeline: pseudonymisation (reversible tokens) then irreversible generalisation.
          Reports k-anonymity, l-diversity, t-closeness for structured data.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-0.5 bg-surface-overlay rounded-md p-1 w-fit mb-6">
        {TABS.map(t => (
          <button
            key={t.id}
            onClick={() => { setTab(t.id); setResult(null) }}
            className={clsx(
              'px-4 py-1.5 rounded text-sm transition-all duration-150',
              tab === t.id ? 'bg-white text-ink-800 shadow-card font-medium' : 'text-ink-500 hover:text-ink-700'
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Input panel */}
        <div className="space-y-4">
          {tab === 'text' && (
            <>
              <div>
                <label className="label">Paste document text</label>
                <textarea
                  className="input min-h-[260px] resize-y font-mono text-xs"
                  placeholder="Paste clinical document text, SAE narration, or application text here..."
                  value={inputText}
                  onChange={e => setInputText(e.target.value)}
                />
              </div>
              <button
                onClick={handleTextSubmit}
                disabled={loading || !inputText.trim()}
                className="btn-primary w-full justify-center"
              >
                <ShieldCheck size={15} />
                {loading ? 'Processing...' : 'Anonymise Text'}
              </button>
            </>
          )}

          {(tab === 'document' || tab === 'structured') && (
            <>
              {tab === 'structured' && (
                <div>
                  <label className="label">Sensitive column names (comma-separated)</label>
                  <input
                    className="input"
                    placeholder="e.g. patient_name, aadhaar, phone, address"
                    value={sensitiveColumns}
                    onChange={e => setSensitiveColumns(e.target.value)}
                  />
                </div>
              )}
              <div
                {...getRootProps()}
                className={clsx('drop-zone', isDragActive && 'drop-zone-active')}
              >
                <input {...getInputProps()} />
                <Upload size={28} className="text-ink-300" />
                <div>
                  <div className="text-sm font-medium text-ink-700">
                    {isDragActive ? 'Drop file here' : 'Drop file or click to browse'}
                  </div>
                  <div className="text-xs text-ink-400 mt-1">
                    {tab === 'structured' ? 'CSV files only' : 'PDF, DOCX, TXT — max 50 MB'}
                  </div>
                </div>
                {loading && (
                  <div className="text-xs text-signal-blue font-medium animate-pulse">
                    Anonymising...
                  </div>
                )}
              </div>
            </>
          )}

          {/* Compliance badges */}
          <div className="flex flex-wrap gap-1.5">
            {['DPDP Act 2023', 'NDHM', 'ICMR', 'CDSCO'].map(b => (
              <span key={b} className="badge-neutral">{b}</span>
            ))}
          </div>
        </div>

        {/* Result panel */}
        <div className="space-y-4">
          {result && (
            <>
              {/* Entity summary */}
              {result.entities_detected && (
                <div className="card p-4">
                  <div className="section-title mb-3">Entities Detected</div>
                  <div className="grid grid-cols-2 gap-2">
                    {Object.entries(result.entities_detected).map(([k, v]) => (
                      <div key={k} className="flex justify-between items-center py-1.5 px-3 bg-surface-raised rounded text-xs">
                        <span className="text-ink-500 font-mono">{k}</span>
                        <span className="font-medium text-ink-800">{String(v)}</span>
                      </div>
                    ))}
                  </div>
                  <div className="mt-3 pt-3 border-t border-surface-border text-xs text-ink-400">
                    {result.processing_time_ms}ms processing time
                  </div>
                </div>
              )}

              {/* Privacy metrics for structured */}
              {result.privacy_metrics && (
                <div className="card p-4">
                  <div className="section-title mb-3">Privacy Metrics</div>
                  <div className="space-y-2">
                    {[
                      { label: 'k-Anonymity', value: result.privacy_metrics.k_anonymity, pass: result.privacy_metrics.compliant_k5, threshold: 'k ≥ 5' },
                      { label: 'l-Diversity', value: result.privacy_metrics.l_diversity, pass: result.privacy_metrics.compliant_l2, threshold: 'l ≥ 2' },
                      { label: 't-Closeness', value: result.privacy_metrics.t_closeness, pass: result.privacy_metrics.compliant_t025, threshold: 't ≤ 0.25' },
                    ].map(({ label, value, pass, threshold }) => (
                      <div key={label} className="flex items-center justify-between text-sm">
                        <span className="text-ink-600 font-mono">{label}</span>
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-ink-800">{value ?? 'N/A'}</span>
                          <span className={pass === true ? 'badge-ok' : pass === false ? 'badge-critical' : 'badge-neutral'}>
                            {pass === true ? 'COMPLIANT' : pass === false ? 'NON-COMPLIANT' : threshold}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Anonymised text output */}
              {result.anonymised_text && (
                <div className="card p-4">
                  <div className="flex items-center justify-between mb-3">
                    <div className="section-title">Anonymised Output</div>
                    <button
                      onClick={() => handleCopy(result.anonymised_text)}
                      className="btn-ghost text-xs py-1 px-2"
                    >
                      {copied ? <CheckCheck size={13} /> : <Copy size={13} />}
                      {copied ? 'Copied' : 'Copy'}
                    </button>
                  </div>
                  <pre className="text-xs font-mono text-ink-600 bg-surface-raised rounded p-3 max-h-64 overflow-y-auto scrollbar-thin whitespace-pre-wrap leading-relaxed">
                    {result.anonymised_text}
                  </pre>
                </div>
              )}
            </>
          )}

          {!result && !loading && (
            <div className="flex flex-col items-center justify-center h-64 text-ink-300 text-sm gap-2">
              <ShieldCheck size={32} strokeWidth={1.5} />
              <span>Anonymised output will appear here</span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
