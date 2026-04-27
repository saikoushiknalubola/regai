import { useNavigate } from 'react-router-dom'
import { ShieldCheck, FileText, ClipboardCheck, Tag, ListOrdered, ArrowRight } from 'lucide-react'

const MODULES = [
  {
    to: '/anonymise',
    icon: ShieldCheck,
    label: 'Anonymisation',
    description: 'Detect and remove PII/PHI from clinical documents. Two-step pseudonymisation and irreversible generalisation.',
    badge: 'DPDP • NDHM • ICMR',
    color: 'text-signal-blue',
    bg: 'bg-blue-50',
  },
  {
    to: '/summarise',
    icon: FileText,
    label: 'Summarisation',
    description: 'Generate standardised reviewer summary cards from SUGAM applications, SAE narrations, and meeting transcripts.',
    badge: 'SUGAM • SAE • Audio',
    color: 'text-signal-green',
    bg: 'bg-green-50',
  },
  {
    to: '/completeness',
    icon: ClipboardCheck,
    label: 'Completeness & Diff',
    description: 'Validate mandatory fields against CDSCO checklists. Semantic version comparison to flag substantive changes.',
    badge: 'Checklist • Semantic Diff',
    color: 'text-signal-amber',
    bg: 'bg-amber-50',
  },
  {
    to: '/classify',
    icon: Tag,
    label: 'Classification',
    description: 'Classify SAE severity (death / disability / hospitalisation / others). Detect duplicate case filings.',
    badge: 'ICH E2A • BioBERT',
    color: 'text-signal-red',
    bg: 'bg-red-50',
  },
  {
    to: '/queue',
    icon: ListOrdered,
    label: 'Review Queue',
    description: 'Build a prioritised workload queue using composite scoring: severity, completeness, and submission age.',
    badge: 'Priority Scoring',
    color: 'text-signal-indigo',
    bg: 'bg-indigo-50',
  },
]

export default function Dashboard() {
  const navigate = useNavigate()

  return (
    <div className="p-8 max-w-5xl mx-auto animate-fade-in">
      {/* Header */}
      <div className="mb-10">
        <div className="section-title mb-3">CDSCO-IndiaAI Hackathon — RegAI Platform</div>
        <h1 className="text-3xl font-700 text-ink-800 text-balance">
          AI-Driven Regulatory Workflow Automation
        </h1>
        <p className="mt-3 text-ink-500 max-w-2xl leading-relaxed">
          RegAI reduces the document-processing burden on CDSCO reviewers by automating
          anonymisation, summarisation, completeness checking, and case classification —
          so reviewers can focus on regulatory judgment rather than data extraction.
        </p>
      </div>

      {/* Module cards */}
      <div className="grid grid-cols-1 gap-4">
        {MODULES.map(({ to, icon: Icon, label, description, badge, color, bg }) => (
          <button
            key={to}
            onClick={() => navigate(to)}
            className="card p-5 text-left flex items-start gap-5 hover:shadow-panel transition-all duration-200 group"
          >
            <div className={`w-10 h-10 rounded-md ${bg} flex items-center justify-center shrink-0 mt-0.5`}>
              <Icon size={18} className={color} strokeWidth={2} />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-3 mb-1">
                <span className="font-medium text-ink-800">{label}</span>
                <span className="badge-neutral">{badge}</span>
              </div>
              <p className="text-sm text-ink-500 leading-relaxed">{description}</p>
            </div>
            <ArrowRight
              size={16}
              className="text-ink-300 group-hover:text-ink-600 group-hover:translate-x-0.5 transition-all duration-150 shrink-0 mt-1"
            />
          </button>
        ))}
      </div>

      {/* Compliance footer */}
      <div className="mt-8 p-4 rounded-lg bg-surface-raised border border-surface-border">
        <div className="section-title mb-2">Regulatory Compliance</div>
        <div className="flex flex-wrap gap-2 text-xs text-ink-500">
          {['DPDP Act 2023', 'NDHM Health Data Management Policy', 'ICMR Ethical Guidelines',
            'CDSCO Standards', 'ICH E2A', 'ICH E6 (GCP)', 'IT Act 2000'].map(c => (
            <span key={c} className="px-2 py-1 bg-white border border-surface-border rounded text-ink-600">
              {c}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}
