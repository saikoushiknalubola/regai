import { Outlet, NavLink, useLocation } from 'react-router-dom'
import {
  LayoutDashboard, ShieldCheck, FileText, ClipboardCheck,
  Tag, ListOrdered, Activity
} from 'lucide-react'
import clsx from 'clsx'

const NAV = [
  { to: '/dashboard',   icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/anonymise',   icon: ShieldCheck,     label: 'Anonymisation' },
  { to: '/summarise',   icon: FileText,         label: 'Summarisation' },
  { to: '/completeness',icon: ClipboardCheck,  label: 'Completeness' },
  { to: '/classify',    icon: Tag,             label: 'Classification' },
  { to: '/queue',       icon: ListOrdered,     label: 'Review Queue' },
]

export default function Layout() {
  const location = useLocation()

  return (
    <div className="flex h-screen overflow-hidden bg-surface-base">
      {/* Sidebar */}
      <aside className="w-56 shrink-0 flex flex-col border-r border-surface-border bg-white">
        {/* Logo */}
        <div className="px-5 py-5 border-b border-surface-border">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 bg-ink-800 rounded flex items-center justify-center">
              <Activity size={14} color="white" strokeWidth={2.5} />
            </div>
            <div>
              <div className="font-display font-700 text-sm text-ink-800 leading-none">RegAI</div>
              <div className="text-xs text-ink-400 mt-0.5">CDSCO Review Platform</div>
            </div>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-2.5 py-3 space-y-0.5 overflow-y-auto scrollbar-thin">
          {NAV.map(({ to, icon: Icon, label }) => {
            const active = location.pathname === to
            return (
              <NavLink key={to} to={to}>
                <div className={clsx('sidebar-item', active && 'sidebar-item-active')}>
                  <Icon size={15} strokeWidth={active ? 2.5 : 2} />
                  <span>{label}</span>
                  {active && (
                    <div className="ml-auto w-1.5 h-1.5 rounded-full bg-ink-800" />
                  )}
                </div>
              </NavLink>
            )
          })}
        </nav>

        {/* Footer */}
        <div className="px-5 py-4 border-t border-surface-border">
          <div className="text-xs text-ink-400">
            <div className="font-medium text-ink-600">Revithalize Mobility</div>
            <div>v1.0.0 — Stage 1</div>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto scrollbar-thin">
        <Outlet />
      </main>
    </div>
  )
}
