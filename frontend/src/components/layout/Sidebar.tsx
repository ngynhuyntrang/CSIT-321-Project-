import { useEffect, useState } from 'react'
import { NavLink, useLocation, useNavigate } from 'react-router-dom'
import { getHealth } from '../../api/client'
import { useAuth } from '../../auth/useAuth'
import type { User } from '../../types/auth'

export interface NavEntry {
  label: string
  to?: string
  /** Also active on these sub-paths (e.g. a booking's edit page). */
  activeUnder?: string
  /** Shown as a badge; `planned` entries render disabled. */
  badge?: string
  planned?: boolean
}

export interface NavSection {
  title: string
  items: NavEntry[]
}

function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]!.toUpperCase())
    .join('')
}

const ROLE_LABELS: Record<User['role'], string> = {
  admin: 'SCIT Operations',
  staff: 'SCIT Staff',
  student: 'Student',
}

export function Sidebar({ sections }: { sections: NavSection[] }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const exactMatch = (to?: string) => sections.some((s) => s.items.some((i) => i.to === pathname && i.to !== to))
  const [health, setHealth] = useState<'ok' | 'error' | 'pending'>('pending')

  useEffect(() => {
    getHealth()
      .then((h) => setHealth(h.status === 'ok' && h.db === 'ok' ? 'ok' : 'error'))
      .catch(() => setHealth('error'))
  }, [])

  async function handleSignOut() {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <nav className="sidebar">
      <div className="brand">
        <div className="brand-title">SCIT Lab Scheduling</div>
        <div className="brand-sub">School of Computing &amp; IT, UOW</div>
      </div>

      {sections.map((section, idx) => (
        <div key={section.title}>
          <div className={`nav-section-label${idx > 0 ? ' nav-section-gap' : ''}`}>
            {section.title}
          </div>
          {section.items.map((item) =>
            item.planned || !item.to ? (
              <div key={item.label} className="nav-item disabled" title="Not built yet">
                <span>{item.label}</span>
                {item.badge && <span className="nav-badge">{item.badge}</span>}
              </div>
            ) : (
              <NavLink
                key={item.label}
                to={item.to}
                end
                className={({ isActive }) => {
                  const under =
                    item.activeUnder !== undefined &&
                    pathname.startsWith(item.activeUnder) &&
                    !exactMatch(item.to)
                  return `nav-item${isActive || under ? ' active' : ''}`
                }}
              >
                <span>{item.label}</span>
                {item.badge && <span className="nav-badge count">{item.badge}</span>}
              </NavLink>
            ),
          )}
        </div>
      ))}

      {user && (
        <div className="sidebar-foot">
          <div className="user-chip">
            <span className={`avatar${user.role === 'student' ? ' student' : ''}`}>
              {initials(user.full_name)}
            </span>
            <div>
              <div className="user-name">{user.full_name}</div>
              <span className={`role-pill${user.role === 'student' ? ' student' : ''}`}>
                {ROLE_LABELS[user.role]}
              </span>
            </div>
          </div>
          <div className="sidebar-foot-row">
            <button type="button" className="link-button" onClick={handleSignOut}>
              Sign out
            </button>
            <span className={`health-dot ${health}`}>
              {health === 'pending' ? 'Checking…' : health === 'ok' ? 'Online' : 'Backend down'}
            </span>
          </div>
        </div>
      )}
    </nav>
  )
}
