import { useCallback, useEffect, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import {
  cancelBooking,
  downloadBookingsExport,
  listBookings,
  listClassTypes,
  listLabs,
} from '../../api/bookings'
import { useAuth } from '../../auth/useAuth'
import { Modal } from '../../components/common/Modal'
import { StatCard } from '../../components/common/StatCard'
import { PageHeader } from '../../components/layout/PageHeader'
import { DAY_KEYS, DAY_SHORT, formatDate, formatRange } from '../../lib/format'
import type { Booking, BookingFilters, BookingFlag, BookingList, DayKey, Lab } from '../../types/booking'

const PAGE_SIZE = 50

export function BookingsPage() {
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'
  const location = useLocation()
  const navigate = useNavigate()
  const [notice, setNotice] = useState<string | null>(
    (location.state as { notice?: string } | null)?.notice ?? null,
  )
  const [filters, setFilters] = useState<BookingFilters>({ page: 1, page_size: PAGE_SIZE })
  const [search, setSearch] = useState('')
  const [data, setData] = useState<BookingList | null>(null)
  const [labs, setLabs] = useState<Lab[]>([])
  const [classTypes, setClassTypes] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)
  const [cancelling, setCancelling] = useState<Booking | null>(null)

  // Clear router state so the notice doesn't reappear on refresh.
  useEffect(() => {
    if (location.state) navigate(location.pathname, { replace: true, state: null })
  }, [location.pathname, location.state, navigate])

  useEffect(() => {
    listLabs().then(setLabs).catch(() => {})
    listClassTypes().then(setClassTypes).catch(() => {})
  }, [])

  const load = useCallback(() => {
    listBookings(filters)
      .then((result) => {
        setData(result)
        setError(null)
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load bookings.'))
  }, [filters])

  useEffect(load, [load])

  // Debounce the search box into the filters.
  useEffect(() => {
    const handle = setTimeout(() => {
      setFilters((f) => (f.q === (search || undefined) ? f : { ...f, q: search || undefined, page: 1 }))
    }, 300)
    return () => clearTimeout(handle)
  }, [search])

  function setFilter<K extends keyof BookingFilters>(key: K, value: BookingFilters[K]) {
    setFilters((f) => ({ ...f, [key]: value, page: 1 }))
  }

  function toggleFlag(flag: BookingFlag) {
    setFilter('flag', filters.flag === flag ? undefined : flag)
  }

  async function handleExport() {
    try {
      await downloadBookingsExport(filters)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Export failed.')
    }
  }

  const stats = data?.stats
  const page = filters.page ?? 1
  const pageCount = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1

  return (
    <>
      <PageHeader
        title="All Bookings"
        subtitle={
          <>
            Current baseline — <strong>Enterprise import plus manual edits</strong>
          </>
        }
        actions={
          isAdmin && (
            <Link to="/admin/bookings/new" className="btn">
              + New booking
            </Link>
          )
        }
      />
      {notice && (
        <div className="alert ok" role="status">
          {notice}{' '}
          <button type="button" className="link-button" style={{ color: 'inherit' }} onClick={() => setNotice(null)}>
            Dismiss
          </button>
        </div>
      )}
      {error && <div className="alert error">{error}</div>}

      <div className="stats-row">
        <StatCard value={stats?.total ?? '—'} label="Bookings" selected={!filters.flag} onClick={() => setFilter('flag', undefined)} />
        <StatCard value={stats?.manual ?? '—'} label="Manual" selected={filters.flag === 'manual'} onClick={() => toggleFlag('manual')} />
        <StatCard value={stats?.clashes ?? '—'} label="Room clashes" tone="error" selected={filters.flag === 'clash'} onClick={() => toggleFlag('clash')} />
        <StatCard value={stats?.over_capacity ?? '—'} label="Over capacity" tone="warning" selected={filters.flag === 'over_capacity'} onClick={() => toggleFlag('over_capacity')} />
      </div>

      <div className="filter-bar">
        <input
          className="input"
          style={{ width: 240 }}
          type="search"
          placeholder="Search subject or class…"
          aria-label="Search subject or class"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select
          className="select"
          aria-label="Room"
          value={filters.lab_id ?? ''}
          onChange={(e) => setFilter('lab_id', e.target.value ? Number(e.target.value) : undefined)}
        >
          <option value="">All rooms</option>
          {labs.map((lab) => (
            <option key={lab.id} value={lab.id}>
              {lab.code}
            </option>
          ))}
        </select>
        <select
          className="select"
          aria-label="Activity type"
          value={filters.class_type ?? ''}
          onChange={(e) => setFilter('class_type', e.target.value || undefined)}
        >
          <option value="">All activity types</option>
          {classTypes.map((t) => (
            <option key={t}>{t}</option>
          ))}
        </select>
        <select
          className="select"
          aria-label="Day"
          value={filters.day ?? ''}
          onChange={(e) => setFilter('day', (e.target.value || undefined) as DayKey | undefined)}
        >
          <option value="">All days</option>
          {DAY_KEYS.slice(0, 5).map((d) => (
            <option key={d} value={d}>
              {DAY_SHORT[d]}
            </option>
          ))}
        </select>
        <span className="spacer" />
        <button type="button" className="btn secondary" onClick={handleExport}>
          Export to Excel
        </button>
      </div>

      <div className="card">
        {data === null ? (
          <div className="empty">Loading…</div>
        ) : data.items.length === 0 ? (
          <div className="empty">
            {stats?.total === 0 ? 'No baseline yet — upload an Enterprise export first.' : 'No bookings match these filters.'}
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Class</th>
                  <th>Activity</th>
                  <th>Room</th>
                  <th>Day &amp; time</th>
                  <th>Size / Cap.</th>
                  <th>Dates</th>
                  <th>Source</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((b) => (
                  <tr key={b.id} className={b.has_clash ? 'flag-error' : b.over_capacity ? 'flag-warning' : ''}>
                    <td>
                      {b.activity_name ?? b.subject_codes.join('/')}
                      <div className="muted">{b.subject_codes.join(', ')}</div>
                    </td>
                    <td className="nowrap">{b.class_type}</td>
                    <td className="nowrap">
                      <span className="pill">{b.lab_code ?? '—'}</span>
                    </td>
                    <td className="nowrap">
                      {DAY_SHORT[b.day_of_week]} {formatRange(b.start_time, b.duration_minutes)}
                    </td>
                    <td className="nowrap">
                      {b.cohort_size} / {b.lab_capacity ?? '?'}
                    </td>
                    <td className="nowrap">
                      {b.occurrence_count}×
                      <div className="muted">
                        {formatDate(b.first_date)} – {formatDate(b.last_date)}
                      </div>
                    </td>
                    <td>
                      <span className={b.source === 'manual' ? 'source-manual' : 'source-enterprise'}>
                        {b.source === 'manual' ? 'Manual' : 'Enterprise'}
                      </span>
                    </td>
                    <td>
                      <div className="row-actions">
                        <Link to={`/admin/bookings/${b.id}`}>{isAdmin ? 'Edit' : 'View'}</Link>
                        {isAdmin && (
                          <button type="button" className="danger" onClick={() => setCancelling(b)}>
                            Cancel
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <div className="table-foot">
          <span>
            <span className="swatch" style={{ background: 'var(--error-bg)', border: '1px solid var(--error-border)' }} />
            Room clash (overlapping booking)
          </span>
          <span>
            <span className="swatch" style={{ background: 'var(--warning-bg)', border: '1px solid var(--warning-border)' }} />
            Cohort size exceeds room capacity
          </span>
          <span className="spacer" />
          {data && data.total > 0 && (
            <div className="pager">
              <span>
                {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, data.total)} of {data.total}
              </span>
              <button type="button" className="btn small secondary" disabled={page <= 1} onClick={() => setFilters((f) => ({ ...f, page: page - 1 }))}>
                Prev
              </button>
              <button type="button" className="btn small secondary" disabled={page >= pageCount} onClick={() => setFilters((f) => ({ ...f, page: page + 1 }))}>
                Next
              </button>
            </div>
          )}
        </div>
      </div>

      {cancelling && (
        <CancelDialog
          booking={cancelling}
          onClose={() => setCancelling(null)}
          onDone={() => {
            setNotice(`Cancelled ${cancelling.activity_name ?? 'booking'}.`)
            setCancelling(null)
            load()
          }}
        />
      )}
    </>
  )
}

function CancelDialog({
  booking,
  onClose,
  onDone,
}: {
  booking: Booking
  onClose: () => void
  onDone: () => void
}) {
  const [reason, setReason] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function submit() {
    setBusy(true)
    setError(null)
    try {
      await cancelBooking(booking.id, reason)
      onDone()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Cancel failed.')
      setBusy(false)
    }
  }

  return (
    <Modal title={`Cancel ${booking.activity_name ?? 'booking'}?`} onClose={onClose}>
      <p>
        Frees {booking.lab_code} {DAY_SHORT[booking.day_of_week]}{' '}
        {formatRange(booking.start_time, booking.duration_minutes)} on all {booking.occurrence_count} dates. The
        booking stays in the history.
      </p>
      {error && <div className="alert error">{error}</div>}
      <div className="field">
        <label htmlFor="cancel-reason">Reason</label>
        <textarea
          id="cancel-reason"
          className="textarea"
          value={reason}
          autoFocus
          onChange={(e) => setReason(e.target.value)}
        />
      </div>
      <div className="form-actions">
        <button type="button" className="btn danger" disabled={busy || reason.trim().length < 3} onClick={submit}>
          {busy ? 'Cancelling…' : 'Cancel booking'}
        </button>
        <button type="button" className="btn secondary" onClick={onClose}>
          Keep
        </button>
      </div>
    </Modal>
  )
}
