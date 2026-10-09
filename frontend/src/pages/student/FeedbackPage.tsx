import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { myFeedback, submitFeedback } from '../../api/feedback'
import { getClassOptions } from '../../api/student'
import { PageHeader } from '../../components/layout/PageHeader'
import { FeedbackItem } from '../../components/student/FeedbackItem'
import { CATEGORY_LABELS } from '../../lib/feedback'
import type { ClassOption, Feedback, FeedbackCategory } from '../../types/student'

interface ClassChoice {
  entry_id: number
  label: string
  lab_code: string | null
}

export function FeedbackPage() {
  const [classes, setClasses] = useState<ClassChoice[]>([])
  const [entryId, setEntryId] = useState('')
  const [category, setCategory] = useState<FeedbackCategory>('timing')
  const [rating, setRating] = useState(0)
  const [comment, setComment] = useState('')
  const [anonymous, setAnonymous] = useState(false)
  const [history, setHistory] = useState<Feedback[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const loadHistory = useCallback(() => {
    myFeedback()
      .then(setHistory)
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load feedback.'))
  }, [])

  useEffect(loadHistory, [loadHistory])

  // Offer the student's chosen classes to attach feedback to.
  useEffect(() => {
    getClassOptions()
      .then((options) => {
        const selected: ClassChoice[] = options.subjects.flatMap((s) =>
          s.groups.flatMap((g) =>
            g.options
              .filter((o: ClassOption) => o.selected)
              .map((o) => ({
                entry_id: o.entry_id,
                label: `${s.subject_code} · ${o.class_type} ${o.activity_name?.split('-').pop() ?? ''}`.trim(),
                lab_code: o.lab_code,
              })),
          ),
        )
        setClasses(selected)
      })
      .catch(() => {})
  }, [])

  const chosen = classes.find((c) => String(c.entry_id) === entryId)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setSubmitting(true)
    setError(null)
    setNotice(null)
    try {
      await submitFeedback({
        entry_id: entryId ? Number(entryId) : null,
        lab_id: null,
        category,
        rating,
        comment,
        anonymous,
      })
      setNotice('Thanks — your feedback was sent to SCIT Operations.')
      setComment('')
      setRating(0)
      setEntryId('')
      setAnonymous(false)
      loadHistory()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not send feedback.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <>
      <PageHeader
        title="Feedback"
        subtitle={
          <>
            Tell SCIT Operations how lab scheduling works for you —{' '}
            <strong>responses inform next semester's timetable</strong>
          </>
        }
      />
      <div className="layout-2col">
        <form className="card" onSubmit={handleSubmit}>
          <div className="card-title">New feedback</div>
          {notice && <div className="alert ok">{notice}</div>}
          {error && <div className="alert error">{error}</div>}
          <div className="field-row">
            <div className="field">
              <label htmlFor="fb-class">Subject / class (optional)</label>
              <select id="fb-class" className="select" value={entryId} onChange={(e) => setEntryId(e.target.value)}>
                <option value="">General feedback</option>
                {classes.map((c) => (
                  <option key={c.entry_id} value={c.entry_id}>
                    {c.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <span className="field-label">Room</span>
              <div className="input" style={{ background: 'transparent' }}>
                {chosen?.lab_code ?? '—'}
              </div>
            </div>
          </div>
          <div className="field">
            <span className="field-label">What is it about?</span>
            <div className="toggle-group">
              {(Object.keys(CATEGORY_LABELS) as FeedbackCategory[]).map((c) => (
                <button key={c} type="button" className={category === c ? 'active' : ''} onClick={() => setCategory(c)}>
                  {CATEGORY_LABELS[c]}
                </button>
              ))}
            </div>
          </div>
          <div className="field">
            <span className="field-label" id="fb-rating">
              How well does this work for you? (1 = poorly, 5 = very well)
            </span>
            <div className="rating" role="radiogroup" aria-labelledby="fb-rating">
              {[1, 2, 3, 4, 5].map((n) => (
                <button
                  key={n}
                  type="button"
                  role="radio"
                  aria-checked={rating === n}
                  className={n <= rating ? 'on' : ''}
                  onClick={() => setRating(n)}
                >
                  {n}
                </button>
              ))}
            </div>
          </div>
          <div className="field">
            <label htmlFor="fb-comment">Comments</label>
            <textarea id="fb-comment" className="textarea" value={comment} maxLength={2000} onChange={(e) => setComment(e.target.value)} />
          </div>
          <label className="checkbox" style={{ marginBottom: 14 }}>
            <input type="checkbox" checked={anonymous} onChange={(e) => setAnonymous(e.target.checked)} />
            Submit anonymously (staff won't see your name)
          </label>
          <div className="form-actions">
            <button type="submit" className="btn" disabled={submitting || rating === 0 || comment.trim().length < 3}>
              {submitting ? 'Sending…' : 'Submit feedback'}
            </button>
          </div>
        </form>

        <div className="card">
          <div className="card-title">Your submissions</div>
          {history === null ? (
            <div className="field-hint">Loading…</div>
          ) : history.length === 0 ? (
            <div className="field-hint">You haven't sent any feedback yet.</div>
          ) : (
            history.map((f) => <FeedbackItem key={f.id} feedback={f} />)
          )}
        </div>
      </div>
    </>
  )
}
