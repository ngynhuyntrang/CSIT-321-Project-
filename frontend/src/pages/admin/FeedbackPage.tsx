import { useCallback, useEffect, useState } from 'react'
import { listFeedback, setFeedbackStatus } from '../../api/feedback'
import { useAuth } from '../../auth/useAuth'
import { PageHeader } from '../../components/layout/PageHeader'
import { FeedbackItem } from '../../components/student/FeedbackItem'
import type { Feedback } from '../../types/student'

export function AdminFeedbackPage() {
  const { user } = useAuth()
  const [filter, setFilter] = useState<Feedback['status'] | 'all'>('received')
  const [items, setItems] = useState<Feedback[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(() => {
    listFeedback(filter === 'all' ? undefined : filter)
      .then(setItems)
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load feedback.'))
  }, [filter])

  useEffect(load, [load])

  async function mark(f: Feedback, status: Feedback['status']) {
    try {
      await setFeedbackStatus(f.id, status)
      load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Update failed.')
    }
  }

  const average =
    items && items.length ? (items.reduce((sum, f) => sum + f.rating, 0) / items.length).toFixed(1) : null

  return (
    <>
      <PageHeader
        title="Student Feedback"
        subtitle={
          <>
            What students say about lab scheduling{average && <> — <strong>average rating {average}/5</strong></>}
          </>
        }
      />
      <div className="filter-bar">
        <div className="toggle-group">
          {(['received', 'reviewed', 'all'] as const).map((s) => (
            <button key={s} type="button" className={filter === s ? 'active' : ''} onClick={() => setFilter(s)}>
              {s === 'received' ? 'To review' : s === 'reviewed' ? 'Reviewed' : 'All'}
            </button>
          ))}
        </div>
      </div>
      {error && <div className="alert error">{error}</div>}
      <div className="card">
        {items === null ? (
          <div className="empty">Loading…</div>
        ) : items.length === 0 ? (
          <div className="empty">Nothing here.</div>
        ) : (
          items.map((f) => (
            <FeedbackItem
              key={f.id}
              feedback={f}
              meta={` · ${f.anonymous ? 'Anonymous' : (f.author ?? 'Unknown')}`}
              action={
                user?.role === 'admin' &&
                (f.status === 'received' ? (
                  <button type="button" className="btn small" onClick={() => mark(f, 'reviewed')}>
                    Mark reviewed
                  </button>
                ) : (
                  <button type="button" className="btn small secondary" onClick={() => mark(f, 'received')}>
                    Reopen
                  </button>
                ))
              }
            />
          ))
        )}
      </div>
    </>
  )
}
