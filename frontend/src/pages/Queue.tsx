import { useState } from 'react'
import { ListOrdered, Plus, Trash2, AlertTriangle } from 'lucide-react'
import toast from 'react-hot-toast'
import clsx from 'clsx'
import { buildPriorityQueue } from '@/utils/api'

const BLANK_CASE = () => ({
  case_id: '', severity: 'hospitalisation', completeness_score: 0.9,
  submission_age_days: 5, document_type: 'sae_report', assigned_reviewer: ''
})

const SEVERITY_COLOR: Record<string, string> = {
  death: 'severity-death',
  disability: 'bg-orange-100 text-orange-700 badge',
  hospitalisation: 'severity-hospitalisation',
  others: 'severity-others',
}

export default function QueuePage() {
  const [cases, setCases] = useState([
    { case_id: 'SAE-2024-001', severity: 'death', completeness_score: 0.95, submission_age_days: 3, document_type: 'sae_report', assigned_reviewer: '' },
    { case_id: 'SAE-2024-002', severity: 'hospitalisation', completeness_score: 0.6, submission_age_days: 18, document_type: 'sae_report', assigned_reviewer: '' },
    { case_id: 'NDA-2024-045', severity: 'others', completeness_score: 1.0, submission_age_days: 7, document_type: 'new_drug_application', assigned_reviewer: '' },
  ])
  const [loading, setLoading] = useState(false)
  const [queue, setQueue] = useState<any>(null)

  const addCase = () => setCases(c => [...c, BLANK_CASE()])
  const removeCase = (i: number) => setCases(c => c.filter((_, j) => j !== i))
  const updateCase = (i: number, key: string, val: any) =>
    setCases(c => c.map((item, j) => j === i ? { ...item, [key]: val } : item))

  const handleBuild = async () => {
    const valid = cases.filter(c => c.case_id.trim())
    if (!valid.length) { toast.error('Add at least one case with a Case ID'); return }
    setLoading(true); setQueue(null)
    try {
      const data = await buildPriorityQueue(valid)
      setQueue(data); toast.success(`Queue built — ${data.total_cases} cases ranked`)
    } catch {} finally { setLoading(false) }
  }

  return (
    <div className="p-8 max-w-5xl mx-auto animate-fade-in">
      <div className="mb-7">
        <div className="section-title mb-2">Module 4 — Priority Engine</div>
        <h1 className="text-2xl font-700 text-ink-800">Review Queue</h1>
        <p className="mt-1.5 text-sm text-ink-500">
          Build a prioritised workload queue from SAE reports and applications.
          Composite score: severity weight (50%) + completeness deficit (30%) + submission age (20%).
        </p>
      </div>

      {/* Case input table */}
      <div className="card overflow-hidden mb-5">
        <div className="flex items-center justify-between px-4 py-3 border-b border-surface-border">
          <div className="section-title">Input Cases</div>
          <button onClick={addCase} className="btn-ghost text-xs py-1 px-2">
            <Plus size={13} /> Add Case
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="table-base">
            <thead><tr>
              <th>Case ID</th><th>Severity</th><th>Completeness</th>
              <th>Age (days)</th><th>Doc Type</th><th></th>
            </tr></thead>
            <tbody>
              {cases.map((c, i) => (
                <tr key={i}>
                  <td>
                    <input className="input py-1 text-xs font-mono"
                      value={c.case_id} onChange={e => updateCase(i, 'case_id', e.target.value)}
                      placeholder="SAE-2024-XXX" />
                  </td>
                  <td>
                    <select className="input py-1 text-xs" value={c.severity}
                      onChange={e => updateCase(i, 'severity', e.target.value)}>
                      <option value="death">Death</option>
                      <option value="disability">Disability</option>
                      <option value="hospitalisation">Hospitalisation</option>
                      <option value="others">Others</option>
                    </select>
                  </td>
                  <td>
                    <input className="input py-1 text-xs w-20" type="number" min="0" max="1" step="0.05"
                      value={c.completeness_score}
                      onChange={e => updateCase(i, 'completeness_score', parseFloat(e.target.value))} />
                  </td>
                  <td>
                    <input className="input py-1 text-xs w-16" type="number" min="0"
                      value={c.submission_age_days}
                      onChange={e => updateCase(i, 'submission_age_days', parseInt(e.target.value))} />
                  </td>
                  <td>
                    <select className="input py-1 text-xs" value={c.document_type}
                      onChange={e => updateCase(i, 'document_type', e.target.value)}>
                      <option value="sae_report">SAE Report</option>
                      <option value="new_drug_application">NDA</option>
                      <option value="clinical_trial">Clinical Trial</option>
                    </select>
                  </td>
                  <td>
                    <button onClick={() => removeCase(i)}
                      className="text-ink-300 hover:text-signal-red transition-colors p-1">
                      <Trash2 size={13} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <button onClick={handleBuild} disabled={loading}
        className="btn-primary mb-8">
        <ListOrdered size={15} />
        {loading ? 'Building queue...' : 'Build Priority Queue'}
      </button>

      {/* Queue result */}
      {queue && (
        <div className="space-y-4 animate-slide-up">
          {/* Summary stats */}
          <div className="grid grid-cols-4 gap-3">
            {[
              { label: 'Death', val: queue.death_cases, cls: 'text-signal-red' },
              { label: 'Disability', val: queue.disability_cases, cls: 'text-orange-600' },
              { label: 'Hospitalisation', val: queue.hospitalisation_cases, cls: 'text-signal-amber' },
              { label: 'Others', val: queue.other_cases, cls: 'text-ink-400' },
            ].map(({ label, val, cls }) => (
              <div key={label} className="card p-4">
                <div className="section-title mb-1">{label}</div>
                <div className={clsx('stat-number text-2xl', cls)}>{val}</div>
              </div>
            ))}
          </div>

          {/* Prioritised table */}
          <div className="card overflow-hidden">
            <div className="px-4 py-3 border-b border-surface-border">
              <div className="section-title">Prioritised Review Queue</div>
            </div>
            <table className="table-base">
              <thead><tr>
                <th>Rank</th><th>Case ID</th><th>Severity</th>
                <th>Priority Score</th><th>Completeness</th><th>Age</th><th>Flags</th>
              </tr></thead>
              <tbody>
                {queue.queue.map((item: any) => (
                  <tr key={item.case_id}
                    className={clsx(item.severity === 'death' && 'bg-red-50/60')}>
                    <td className="font-mono text-ink-400">#{item.rank}</td>
                    <td className="font-mono font-medium text-ink-800">{item.case_id}</td>
                    <td>
                      <span className={clsx(SEVERITY_COLOR[item.severity] || 'badge-neutral')}>
                        {item.severity}
                      </span>
                    </td>
                    <td>
                      <div className="flex items-center gap-2">
                        <div className="w-16 progress-bar">
                          <div className="progress-fill bg-ink-400"
                            style={{ width: `${item.priority_score * 100}%` }} />
                        </div>
                        <span className="font-mono text-xs text-ink-600">
                          {item.priority_score.toFixed(3)}
                        </span>
                      </div>
                    </td>
                    <td>
                      <span className={item.completeness_score < 0.6 ? 'badge-critical' :
                        item.completeness_score < 0.9 ? 'badge-major' : 'badge-ok'}>
                        {Math.round(item.completeness_score * 100)}%
                      </span>
                    </td>
                    <td className="text-ink-500 font-mono">{item.submission_age_days}d</td>
                    <td>
                      <div className="flex flex-col gap-0.5">
                        {item.flags.map((f: string, fi: number) => (
                          <div key={fi} className="flex items-start gap-1">
                            <AlertTriangle size={10} className="text-signal-amber shrink-0 mt-0.5" />
                            <span className="text-xs text-ink-500 leading-tight">{f}</span>
                          </div>
                        ))}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
