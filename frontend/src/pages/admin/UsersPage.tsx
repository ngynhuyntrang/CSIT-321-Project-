import { useCallback, useEffect, useState } from 'react'
import { listUsers, updateUser } from '../../api/auth'
import { useAuth } from '../../auth/useAuth'
import { PageHeader } from '../../components/layout/PageHeader'
import type { User, UserStatus } from '../../types/auth'

const STATUS_BADGE: Record<UserStatus, string> = {
  active: 'ok',
  pending: 'warning',
  disabled: 'muted',
}

const ROLE_LABELS: Record<User['role'], string> = {
  admin: 'Admin (Operations)',
  staff: 'Staff',
  student: 'Student',
}

export function UsersPage() {
  const { user: me } = useAuth()
  const [filter, setFilter] = useState<UserStatus | 'all'>('pending')
  const [users, setUsers] = useState<User[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(() => {
    listUsers(filter === 'all' ? undefined : filter)
      .then(setUsers)
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load users.'))
  }, [filter])

  useEffect(load, [load])

  async function change(user: User, changes: Partial<Pick<User, 'role' | 'status'>>) {
    setError(null)
    try {
      await updateUser(user.id, changes)
      load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Update failed.')
    }
  }

  return (
    <>
      <PageHeader
        title="Users"
        subtitle={
          <>
            Approve staff sign-ups and manage access — <strong>staff can see internal timetable data</strong>
          </>
        }
      />
      <div className="filter-bar">
        <div className="toggle-group">
          {(['pending', 'active', 'disabled', 'all'] as const).map((s) => (
            <button key={s} type="button" className={filter === s ? 'active' : ''} onClick={() => setFilter(s)}>
              {s[0]!.toUpperCase() + s.slice(1)}
            </button>
          ))}
        </div>
      </div>
      {error && <div className="alert error">{error}</div>}
      <div className="card">
        {users === null ? (
          <div className="empty">Loading…</div>
        ) : users.length === 0 ? (
          <div className="empty">No {filter === 'all' ? '' : filter} users.</div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Role</th>
                <th>Status</th>
                <th>Joined</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td>{u.full_name}</td>
                  <td>{u.email}</td>
                  <td>
                    {u.id === me?.id ? (
                      ROLE_LABELS[u.role]
                    ) : (
                      <select
                        className="select"
                        style={{ width: 'auto', padding: '4px 8px' }}
                        value={u.role}
                        onChange={(e) => change(u, { role: e.target.value as User['role'] })}
                      >
                        {Object.entries(ROLE_LABELS).map(([value, label]) => (
                          <option key={value} value={value}>
                            {label}
                          </option>
                        ))}
                      </select>
                    )}
                  </td>
                  <td>
                    <span className={`status-badge ${STATUS_BADGE[u.status]}`}>{u.status}</span>
                  </td>
                  <td>{new Date(u.created_at).toLocaleDateString()}</td>
                  <td style={{ textAlign: 'right' }}>
                    {u.id !== me?.id &&
                      (u.status === 'active' ? (
                        <button type="button" className="btn small secondary" onClick={() => change(u, { status: 'disabled' })}>
                          Disable
                        </button>
                      ) : (
                        <button type="button" className="btn small" onClick={() => change(u, { status: 'active' })}>
                          {u.status === 'pending' ? 'Approve' : 'Re-enable'}
                        </button>
                      ))}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  )
}
