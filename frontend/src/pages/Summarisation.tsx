import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { FileText, Upload, AlertCircle, CheckCircle } from 'lucide-react'
import toast from 'react-hot-toast'
import clsx from 'clsx'
import { summariseText, summariseDocument, summariseAudio } from '@/utils/api'

type DocType = 'sugam' | 'sae' | 'meeting'

const DOC_TYPES: { id: DocType; label: string; hint: string }[] = [
  { id: 'sugam', label: 'SUGAM Application', hint: 'New drug / clinical trial / medical device application checklists' },
  { id: 'sae', label: 'SAE Case Narration', hint: 'Serious Adverse Event reports and case narrations' },
  { id: 'meeting', label: 'Meeting Transcript', hint: 'DTAB / advisory committee / review meeting transcripts or audio' },
]

export default function SummarisationPage() {
  const [docType, setDocType] = useState<DocType>('sugam')
  const [inputMode, setInputMode] = useState<'text' | 'file'>('text')
  const [inputText, setInputText] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<any>(null)

  const handleTextSubmit = async () => {
    if (!inputText.trim()) return
    setLoading(true); setResult(null)
    try {
      const data = await summariseText(inputText, docType)
      setResult(data)
      toast.success('Summary generated')
    } catch {
      //
    } finally { setLoading(false) }
  }

  const onDrop = useCallback(async (files: File[]) => {
    if (!files[0]) return
    setLoading(true); setResult(null)
    try {
      const isAudio = ['mp3','mp4','wav','m4a'].some(e => files[0].name.endsWith(e))
      const data = isAudio
        ? await summariseAudio(files[0])
        : await summariseDocument(files[0], docType)
      setResult(data)
      toast.success('Summary generated')
    } catch {
      //
    } finally { setLoading(false) }
  }, [docType])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({ onDrop, maxFiles: 1 })

  return (
    <div className="p-8 max-w-5xl mx-auto animate-fade-in">
      <div className="mb-7">
        <div className="section-title mb-2">Module 2</div>
        <h1 className="text-2xl font-700 text-ink-800">Document Summarisation</h1>
        <p className="mt-1.5 text-sm text-ink-500">
          Generates standardised reviewer summary cards from three document types.
          SUGAM checklists, SAE narrations, and meeting transcripts each have dedicated pipelines.
        </p>
      </div>

      {/* Doc type selector */}
      <div className="grid grid-cols-3 gap-3 mb-6">
        {DOC_TYPES.map(dt => (
          <button
            key={dt.id}
            onClick={() => { setDocType(dt.id); setResult(null) }}
            className={clsx(
              'card p-4 text-left transition-all duration-150',
              docType === dt.id ? 'border-signal-blue ring-2 ring-signal-blue/20' : 'hover:shadow-panel'
            )}
          >
            <div className="flex items-start justify-between">
              <span className="font-medium text-sm text-ink-800">{dt.label}</span>
              {docType === dt.id && (
                <CheckCircle size={14} className="text-signal-blue shrink-0 mt-0.5" />
              )}
            </div>
            <p className="text-xs text-ink-400 mt-1 leading-relaxed">{dt.hint}</p>
          </button>
        ))}
      </div>

      {/* Input mode toggle */}
      <div className="flex gap-0.5 bg-surface-overlay rounded-md p-1 w-fit mb-5">
        {(['text', 'file'] as const).map(m => (
          <button
            key={m}
            onClick={() => { setInputMode(m); setResult(null) }}
            className={clsx(
              'px-4 py-1.5 rounded text-sm transition-all duration-150',
              inputMode === m ? 'bg-white text-ink-800 shadow-card font-medium' : 'text-ink-500 hover:text-ink-700'
            )}
          >
            {m === 'text' ? 'Paste Text' : 'Upload File'}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Input */}
        <div className="space-y-4">
          {inputMode === 'text' ? (
            <>
              <textarea
                className="input min-h-[280px] resize-y font-mono text-xs"
                placeholder={`Paste ${docType === 'sugam' ? 'SUGAM application text' : docType === 'sae' ? 'SAE case narration text' : 'meeting transcript text'} here...`}
                value={inputText}
                onChange={e => setInputText(e.target.value)}
              />
              <button
                onClick={handleTextSubmit}
                disabled={loading || !inputText.trim()}
                className="btn-primary w-full justify-center"
              >
                <FileText size={15} />
                {loading ? 'Summarising...' : 'Generate Summary'}
              </button>
            </>
          ) : (
            <div {...getRootProps()} className={clsx('drop-zone', isDragActive && 'drop-zone-active')}>
              <input {...getInputProps()} />
              <Upload size={28} className="text-ink-300" />
              <div>
                <div className="text-sm font-medium text-ink-700">
                  {isDragActive ? 'Drop file here' : 'Drop file or click to browse'}
                </div>
                <div className="text-xs text-ink-400 mt-1">
                  PDF, DOCX, TXT{docType === 'meeting' ? ', MP3, WAV, MP4' : ''} — max 50 MB
                </div>
              </div>
              {loading && <div className="text-xs text-signal-blue animate-pulse font-medium">Summarising...</div>}
            </div>
          )}
        </div>

        {/* Result */}
        <div className="space-y-4">
          {result ? (
            <SummaryResult result={result} docType={docType} />
          ) : !loading ? (
            <div className="flex flex-col items-center justify-center h-64 text-ink-300 text-sm gap-2">
              <FileText size={32} strokeWidth={1.5} />
              <span>Summary card will appear here</span>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  )
}

function SummaryResult({ result, docType }: { result: any; docType: DocType }) {
  if (docType === 'sugam') return (
    <div className="space-y-4 animate-slide-up">
      <div className="card p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="section-title">Completeness</div>
          <span className={clsx('badge', result.completeness_score >= 0.8 ? 'badge-ok' : result.completeness_score >= 0.5 ? 'badge-major' : 'badge-critical')}>
            {Math.round(result.completeness_score * 100)}%
          </span>
        </div>
        <div className="progress-bar mb-2">
          <div
            className={clsx('progress-fill', result.completeness_score >= 0.8 ? 'bg-signal-green' : result.completeness_score >= 0.5 ? 'bg-signal-amber' : 'bg-signal-red')}
            style={{ width: `${result.completeness_score * 100}%` }}
          />
        </div>
        <p className="text-xs text-ink-500 mt-2">{result.reviewer_notes}</p>
      </div>
      {result.missing_mandatory_fields?.length > 0 && (
        <div className="card p-4">
          <div className="section-title mb-2">Missing Mandatory Fields</div>
          <div className="flex flex-wrap gap-1.5">
            {result.missing_mandatory_fields.map((f: string) => (
              <span key={f} className="badge-critical">{f}</span>
            ))}
          </div>
        </div>
      )}
      <div className="card p-4">
        <div className="section-title mb-2">Reviewer Summary</div>
        <p className="text-sm text-ink-700 leading-relaxed">{result.summary}</p>
      </div>
    </div>
  )

  if (docType === 'sae') return (
    <div className="space-y-4 animate-slide-up">
      {result.key_flags?.length > 0 && (
        <div className="card p-4 border-signal-amber/40 bg-amber-50/40">
          <div className="flex items-center gap-2 mb-2">
            <AlertCircle size={14} className="text-signal-amber" />
            <div className="section-title">Review Flags</div>
          </div>
          <div className="space-y-1">
            {result.key_flags.map((f: string, i: number) => (
              <div key={i} className="text-xs text-amber-800 font-mono">{f}</div>
            ))}
          </div>
        </div>
      )}
      <div className="card p-4">
        <div className="section-title mb-3">Case Details</div>
        <div className="space-y-2">
          {[
            ['Case ID', result.case_id],
            ['Suspect Drug', result.suspect_drug],
            ['Adverse Event', result.adverse_event],
            ['Causality', result.causality_assessment],
            ['Outcome', result.outcome],
            ['Reporter', result.reporter_type],
          ].filter(([, v]) => v).map(([k, v]) => (
            <div key={String(k)} className="flex justify-between text-xs py-1.5 border-b border-surface-border last:border-0">
              <span className="text-ink-400 font-medium">{k}</span>
              <span className="text-ink-700 font-mono text-right max-w-[60%]">{String(v)}</span>
            </div>
          ))}
        </div>
      </div>
      {result.seriousness_criteria?.length > 0 && (
        <div className="card p-4">
          <div className="section-title mb-2">Seriousness Criteria</div>
          <div className="flex flex-wrap gap-1.5">
            {result.seriousness_criteria.map((c: string) => (
              <span key={c} className="badge-critical">{c.replace('_', ' ')}</span>
            ))}
          </div>
        </div>
      )}
      <div className="card p-4">
        <div className="section-title mb-2">Structured Narrative</div>
        <p className="text-sm text-ink-700 leading-relaxed">{result.structured_narrative}</p>
      </div>
    </div>
  )

  // meeting
  return (
    <div className="space-y-4 animate-slide-up">
      <div className="card p-4">
        <div className="section-title mb-2">Summary</div>
        <p className="text-sm text-ink-700 leading-relaxed">{result.summary}</p>
      </div>
      {result.key_decisions?.length > 0 && (
        <div className="card p-4">
          <div className="section-title mb-2">Key Decisions</div>
          <ul className="space-y-1.5">
            {result.key_decisions.map((d: string, i: number) => (
              <li key={i} className="text-sm text-ink-700 flex gap-2">
                <span className="text-ink-300 shrink-0">{i + 1}.</span>
                <span>{d}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      {result.action_items?.length > 0 && (
        <div className="card p-4">
          <div className="section-title mb-2">Action Items</div>
          <div className="space-y-2">
            {result.action_items.map((a: any, i: number) => (
              <div key={i} className="text-xs bg-surface-raised rounded p-2.5">
                <div className="flex justify-between mb-0.5">
                  <span className="font-medium text-ink-700">{a.owner || 'TBD'}</span>
                  {a.deadline && <span className="text-ink-400 font-mono">{a.deadline}</span>}
                </div>
                <div className="text-ink-600">{a.action}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
