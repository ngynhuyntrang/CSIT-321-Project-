import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { addSubject, getClassOptions, listSubjects, removeSubject, selectClass } from '../../api/student'
import { PageHeader } from '../../components/layout/PageHeader'
import { DayDots } from '../../components/student/DayDots'
import { DAY_LONG, DAY_SHORT, formatDate, formatDuration, formatRange } from '../../lib/format'
import type { ClassOption, ClassOptions } from '../../types/student'

function seatsLabel(o: ClassOption): { text: string; tone: 'ok' | 'low' | 'none' } {
  if (o.seats_left === null) return { text: 'Capacity unknown', tone: 'low' }
  if (o.full) return { text: `Full · ${o.capacity} / ${o.capacity}`, tone: 'none' }
  return {
    text: `${o.seats_left} of ${o.capacity} seats left`,
    tone: o.seats_left <= 3 ? 'low' : 'ok',
  }
}

export function ChooseClassesPage() {
  const [periodId, setPeriodId] = useState<string | undefined>(undefined)
  const [data, setData] = useState<ClassOptions | null>(null)
  const [available, setAvailable] = useState<string[]>([])
  const [newSubject, setNewSubject] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState<number | string | null>(null)

  const load = useCallback(() => {
    getClassOptions(periodId)
      .then((result) => {
        setData(result)
        setError(null)
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load classes.'))
  }, [periodId])

  useEffect(load, [load])

  const activePeriod = data?.period?.id
  useEffect(() => {
    if (!activePeriod) return
    listSubjects(activePeriod).then(setAvailable).catch(() => {})
  }, [activePeriod])

  async function run(key: number | string, action: () => Promise<void>) {
    setBusy(key)
    setError(null)
    try {
      await action()
      load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong.')
    } finally {
      setBusy(null)
    }
  }

  function handleAdd(event: FormEvent) {
    event.preventDefault()
    const code = newSubject.trim().toUpperCase()
    if (!code) return
    void run(code, async () => {
      await addSubject(code, activePeriod)
      setNewSubject('')
    })
  }

  const days = data?.on_campus_days ?? []
  const chosenSubjects = new Set(data?.subjects.map((s) => s.subject_code))

  return (
    <>
      <PageHeader
        title="Choose Classes"
        subtitle={
          <>
            Pick one class of each type per subject — <strong>seats are limited by room capacity</strong>
          </>
        }
        actions={
          <Link to="/student/timetable" className="btn">
            View timetable
          </Link>
        }
      />
      {error && <div className="alert error">{error}</div>}

      <div className="filter-bar">
        {data && data.periods.length > 1 && (
          <select
            className="select"
            aria-label="Teaching period"
            value={activePeriod ?? ''}
            onChange={(e) => setPeriodId(e.target.value)}
          >
            {data.periods.map((p) => (
              <option key={p.id} value={p.id}>
                {formatDate(p.start)} – {formatDate(p.end)}
              </option>
            ))}
          </select>
        )}
        <form className="add-subject" onSubmit={handleAdd}>
          <input
            className="input"
            list="subject-codes"
            placeholder="Add subject, e.g. CSCI235"
            aria-label="Subject code"
            value={newSubject}
            onChange={(e) => setNewSubject(e.target.value)}
          />
          <datalist id="subject-codes">
            {available
              .filter((c) => !chosenSubjects.has(c))
              .map((c) => (
                <option key={c} value={c} />
              ))}
          </datalist>
          <button type="submit" className="btn secondary" disabled={!newSubject.trim() || busy !== null}>
            Add
          </button>
        </form>
      </div>

      {data === null ? (
        <div className="empty">Loading…</div>
      ) : data.period === null ? (
        <div className="card">
          <div className="empty">No timetable has been published yet.</div>
        </div>
      ) : (
        <div className="layout-2col">
          <div>
            {data.subjects.length === 0 && (
              <div className="card">
                <div className="empty">Add the subjects you're enrolled in to see their classes.</div>
              </div>
            )}
            {data.subjects.map((subject) => (
              <div key={subject.subject_code} className="card">
                <div className="subject-head">
                  <span className="title">{subject.subject_code}</span>
                  <button
                    type="button"
                    className="btn small secondary"
                    disabled={busy !== null}
                    onClick={() => run(subject.subject_code, () => removeSubject(subject.subject_code))}
                  >
                    Remove
                  </button>
                </div>
                {subject.groups.length === 0 && (
                  <div className="field-hint">No classes for this subject in this period.</div>
                )}
                {subject.groups.map((group) => (
                  <div key={group.class_type}>
                    <div className="group-title">
                      {group.class_type} · {formatDuration(group.options[0]!.duration_minutes)}
                    </div>
                    <div className="slot-grid">
                      {group.options.map((o) => {
                        const seats = seatsLabel(o)
                        const clash = o.clashes_with.length > 0 && !o.selected
                        const disabled = o.full || clash || busy !== null
                        return (
                          <div
                            key={o.entry_id}
                            className={`slot-card${o.selected ? ' selected' : ''}${o.full ? ' full' : ''}${clash ? ' clash' : ''}`}
                          >
                            <span className="name">
                              {o.activity_name?.split('-').pop() ?? o.class_type}
                              {o.selected && ' · Selected'}
                            </span>
                            <span className="when">
                              {DAY_SHORT[o.day_of_week]} {formatRange(o.start_time, o.duration_minutes)} · {o.lab_code}
                            </span>
                            {clash && <span className="slot-note error">Clashes with your {o.clashes_with.join(', ')}</span>}
                            {!clash && !o.selected && o.adds_day && days.length > 0 && (
                              <span className="slot-note warning">
                                Adds {DAY_LONG[o.day_of_week]} — {o.days_after} on-campus days
                              </span>
                            )}
                            <div className="foot">
                              <span className={`seats ${seats.tone}`}>{seats.text}</span>
                              {o.selected ? (
                                <span className="btn small secondary" aria-disabled>
                                  Selected ✓
                                </span>
                              ) : (
                                <button
                                  type="button"
                                  className="btn small"
                                  disabled={disabled}
                                  onClick={() => run(o.entry_id, () => selectClass(o.entry_id))}
                                >
                                  {o.full ? 'Full' : busy === o.entry_id ? 'Saving…' : 'Select'}
                                </button>
                              )}
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                ))}
              </div>
            ))}
          </div>

          <div>
            <div className="card">
              <div className="card-title">Your week</div>
              <div className="big-number">
                {days.length} day{days.length === 1 ? '' : 's'}
              </div>
              <div className="field-hint" style={{ marginTop: 0 }}>
                On campus
              </div>
              <DayDots days={days} />
              {days.length > 0 && (
                <div className="alert info" style={{ marginTop: 14, marginBottom: 0 }}>
                  Classes marked “Adds …” would put you on campus an extra day.
                </div>
              )}
            </div>
            <div className="card">
              <div className="card-title">Selected</div>
              {data.subjects.flatMap((s) => s.groups.flatMap((g) => g.options.filter((o) => o.selected))).length === 0 ? (
                <div className="field-hint">Nothing selected yet.</div>
              ) : (
                data.subjects.flatMap((s) =>
                  s.groups.flatMap((g) =>
                    g.options
                      .filter((o) => o.selected)
                      .map((o) => (
                        <div key={o.entry_id} className="metric-row">
                          <span>
                            {s.subject_code} {o.activity_name?.split('-').pop() ?? o.class_type}
                          </span>
                          <span className="value">
                            {DAY_SHORT[o.day_of_week]} {formatRange(o.start_time, o.duration_minutes).split('–')[0]}
                          </span>
                        </div>
                      )),
                  ),
                )
              )}
            </div>
          </div>
        </div>
      )}
    </>
  )
}
