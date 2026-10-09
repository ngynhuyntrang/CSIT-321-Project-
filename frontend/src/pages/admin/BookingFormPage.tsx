import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  checkBooking,
  createBooking,
  getBooking,
  listClassTypes,
  listLabs,
  updateBooking,
} from '../../api/bookings'
import { useAuth } from '../../auth/useAuth'
import { CheckList } from '../../components/bookings/CheckList'
import { PageHeader } from '../../components/layout/PageHeader'
import {
  DAY_KEYS,
  DAY_LONG,
  DAY_SHORT,
  formatDate,
  formatDateTime,
  formatDuration,
  formatRange,
  formatTime,
  toTimeInput,
} from '../../lib/format'
import type {
  BookingCheckRequest,
  BookingCheckResult,
  BookingDetail,
  BookingUpdate,
  DayKey,
  Lab,
} from '../../types/booking'

const DURATIONS = [30, 60, 90, 120, 150, 180, 240]

interface FormState {
  subjects: string
  activity_name: string
  class_type: string
  cohort_size: string
  lab_id: string
  day: DayKey
  start_time: string
  duration_minutes: number
  week_pattern_raw: string
  first_date: string
  occurrences: string
  frequency: 'weekly' | 'fortnightly'
  skip_dates: string[]
}

const EMPTY: FormState = {
  subjects: '',
  activity_name: '',
  class_type: 'Computer Lab',
  cohort_size: '',
  lab_id: '',
  day: 'mon',
  start_time: '09:30',
  duration_minutes: 60,
  week_pattern_raw: '',
  first_date: '',
  occurrences: '10',
  frequency: 'weekly',
  skip_dates: [],
}

function fromBooking(b: BookingDetail): FormState {
  return {
    ...EMPTY,
    subjects: b.subject_codes.join(', '),
    activity_name: b.activity_name ?? '',
    class_type: b.class_type,
    cohort_size: String(b.cohort_size),
    lab_id: b.lab_id ? String(b.lab_id) : '',
    day: b.day_of_week,
    start_time: toTimeInput(b.start_time),
    duration_minutes: b.duration_minutes,
    week_pattern_raw: b.week_pattern_raw ?? '',
  }
}

function subjectCodes(raw: string): string[] {
  return raw
    .split(/[\s,/]+/)
    .map((s) => s.trim().toUpperCase())
    .filter(Boolean)
}

/** Weekday of an ISO date, without timezone drift. */
function dayOfDate(iso: string): DayKey | null {
  if (!iso) return null
  const [y, m, d] = iso.split('-').map(Number)
  const js = new Date(y!, m! - 1, d!).getDay() // 0 = Sunday
  return DAY_KEYS[(js + 6) % 7]!
}

const ACTION_LABELS: Record<string, string> = {
  create: 'Created',
  update: 'Edited',
  cancel: 'Cancelled',
}

export function BookingFormPage() {
  const { id } = useParams()
  const editingId = id ? Number(id) : null
  const { user } = useAuth()
  const readOnly = user?.role !== 'admin'
  const navigate = useNavigate()

  const [labs, setLabs] = useState<Lab[]>([])
  const [classTypes, setClassTypes] = useState<string[]>([])
  const [original, setOriginal] = useState<BookingDetail | null>(null)
  const [form, setForm] = useState<FormState>(EMPTY)
  const [reason, setReason] = useState('')
  const [skipInput, setSkipInput] = useState('')
  const [check, setCheck] = useState<BookingCheckResult | null>(null)
  const [checkError, setCheckError] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    listLabs().then(setLabs).catch(() => {})
    listClassTypes().then(setClassTypes).catch(() => {})
  }, [])

  useEffect(() => {
    if (editingId === null) return
    getBooking(editingId)
      .then((b) => {
        setOriginal(b)
        setForm(fromBooking(b))
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load booking.'))
  }, [editingId])

  function set<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((f) => ({ ...f, [key]: value }))
  }

  const lab = labs.find((l) => String(l.id) === form.lab_id)
  const cancelled = original?.status === 'cancelled'

  // What the live checks and the save send; null while required fields are missing.
  const checkRequest = useMemo<BookingCheckRequest | null>(() => {
    const codes = subjectCodes(form.subjects)
    const cohort = Number(form.cohort_size)
    if (!codes.length || !form.class_type.trim() || !form.lab_id || !form.start_time) return null
    if (form.cohort_size === '' || !Number.isInteger(cohort) || cohort < 0) return null
    const base = {
      subject_codes: codes,
      class_type: form.class_type.trim(),
      lab_id: Number(form.lab_id),
      start_time: form.start_time,
      duration_minutes: form.duration_minutes,
      cohort_size: cohort,
    }
    if (editingId !== null) {
      if (!original || cancelled) return null
      return { ...base, entry_id: editingId, day_of_week: form.day }
    }
    const occurrences = Number(form.occurrences)
    if (!form.first_date || !Number.isInteger(occurrences) || occurrences < 1 || occurrences > 30) return null
    return {
      ...base,
      recurrence: {
        first_date: form.first_date,
        occurrences,
        frequency: form.frequency,
        skip_dates: form.skip_dates,
      },
    }
  }, [form, editingId, original, cancelled])

  // Debounced live checks.
  useEffect(() => {
    if (!checkRequest) return
    const controller = new AbortController()
    const handle = setTimeout(() => {
      checkBooking(checkRequest, controller.signal)
        .then((result) => {
          setCheck(result)
          setCheckError(null)
        })
        .catch((err) => {
          if (controller.signal.aborted) return
          setCheck(null)
          setCheckError(err instanceof Error ? err.message : 'Check failed.')
        })
    }, 350)
    return () => {
      clearTimeout(handle)
      controller.abort()
    }
  }, [checkRequest])

  // Field-level diff for the "Changes" panel and the PATCH body.
  const changes = useMemo(() => {
    if (!original) return []
    const was = fromBooking(original)
    const codes = subjectCodes(form.subjects)
    const rows: { key: string; old: string; new: string }[] = []
    const labCode = (lid: string) => labs.find((l) => String(l.id) === lid)?.code ?? '—'
    if (form.lab_id !== was.lab_id) rows.push({ key: 'Room', old: labCode(was.lab_id), new: labCode(form.lab_id) })
    if (form.day !== was.day) rows.push({ key: 'Day', old: DAY_SHORT[was.day], new: DAY_SHORT[form.day] })
    if (form.start_time !== was.start_time || form.duration_minutes !== was.duration_minutes)
      rows.push({
        key: 'Time',
        old: formatRange(was.start_time, was.duration_minutes),
        new: formatRange(form.start_time, form.duration_minutes),
      })
    if (form.cohort_size !== was.cohort_size) rows.push({ key: 'Cohort size', old: was.cohort_size, new: form.cohort_size })
    if (form.class_type.trim() !== was.class_type) rows.push({ key: 'Activity', old: was.class_type, new: form.class_type })
    if (form.activity_name.trim() !== was.activity_name) rows.push({ key: 'Class name', old: was.activity_name || '—', new: form.activity_name || '—' })
    if (codes.join(', ') !== was.subjects) rows.push({ key: 'Subjects', old: was.subjects, new: codes.join(', ') })
    if (form.week_pattern_raw.trim() !== was.week_pattern_raw) rows.push({ key: 'Week pattern', old: was.week_pattern_raw || '—', new: form.week_pattern_raw || '—' })
    return rows
  }, [form, original, labs])

  function buildUpdate(): BookingUpdate {
    const was = fromBooking(original!)
    const codes = subjectCodes(form.subjects)
    const update: BookingUpdate = { reason: reason.trim() }
    if (form.lab_id !== was.lab_id) update.lab_id = Number(form.lab_id)
    if (form.day !== was.day) update.day_of_week = form.day
    if (form.start_time !== was.start_time) update.start_time = form.start_time
    if (form.duration_minutes !== was.duration_minutes) update.duration_minutes = form.duration_minutes
    if (form.cohort_size !== was.cohort_size) update.cohort_size = Number(form.cohort_size)
    if (form.class_type.trim() !== was.class_type) update.class_type = form.class_type.trim()
    if (form.activity_name.trim() !== was.activity_name) update.activity_name = form.activity_name.trim()
    if (codes.join(', ') !== was.subjects) update.subject_codes = codes
    if (form.week_pattern_raw.trim() !== was.week_pattern_raw) update.week_pattern_raw = form.week_pattern_raw.trim()
    return update
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (!checkRequest) return
    setSaving(true)
    setError(null)
    try {
      if (editingId === null) {
        const { recurrence, entry_id: _entry, day_of_week: _day, ...schedule } = checkRequest
        const created = await createBooking({
          ...schedule,
          recurrence: recurrence!,
          activity_name: form.activity_name.trim() || null,
          week_pattern_raw: form.week_pattern_raw.trim() || null,
        })
        navigate('/admin/bookings', {
          state: { notice: `Added ${created.activity_name ?? created.subject_codes.join('/')} — ${created.occurrence_count} dates in ${created.lab_code}.` },
        })
      } else {
        const updated = await updateBooking(editingId, buildUpdate())
        navigate('/admin/bookings', {
          state: { notice: `Saved changes to ${updated.activity_name ?? 'booking'}.` },
        })
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed.')
      setSaving(false)
    }
  }

  // Results for an older request are hidden once required fields are cleared.
  const shownCheck = checkRequest ? check : null
  const blocked = shownCheck ? !shownCheck.can_save : false
  const canSave =
    !readOnly &&
    !saving &&
    checkRequest !== null &&
    !blocked &&
    (editingId === null || (changes.length > 0 && reason.trim().length >= 3))
  const firstDay = dayOfDate(form.first_date)

  if (editingId !== null && !original && !error) return <div className="empty">Loading…</div>

  const title =
    editingId === null
      ? 'New Booking'
      : `${readOnly || cancelled ? 'Booking' : 'Adjust Booking'} · ${original?.activity_name ?? original?.subject_codes.join('/') ?? ''}`

  return (
    <>
      <PageHeader
        title={title}
        subtitle={
          editingId === null ? (
            <>
              Add a class to the <strong>current baseline</strong> — checked for clashes and room fit before saving
            </>
          ) : (
            <>
              <Link to="/admin/bookings">All Bookings</Link> › <strong>{original?.class_type}</strong>
              {original?.has_clash && ' — currently clashes with another booking'}
              {cancelled && ' — cancelled'}
            </>
          )
        }
      />
      {error && <div className="alert error">{error}</div>}

      <form className="layout-2col" onSubmit={handleSubmit}>
        <fieldset className="card" disabled={readOnly || cancelled} style={{ margin: 0, minWidth: 0 }}>
          <div className="card-title">Class details</div>
          <div className="field-row">
            <div className="field">
              <label htmlFor="bk-subjects">Subject code(s)</label>
              <input id="bk-subjects" className="input" placeholder="CSCI235" value={form.subjects} onChange={(e) => set('subjects', e.target.value)} />
              <div className="field-hint">Separate joint subjects with commas, e.g. CSIT213, CSIT813</div>
            </div>
            <div className="field">
              <label htmlFor="bk-name">Class name</label>
              <input id="bk-name" className="input" placeholder="CSCI235-CL/05" value={form.activity_name} onChange={(e) => set('activity_name', e.target.value)} />
            </div>
          </div>
          <div className="field-row">
            <div className="field">
              <label htmlFor="bk-type">Activity type</label>
              <input id="bk-type" className="input" list="bk-types" value={form.class_type} onChange={(e) => set('class_type', e.target.value)} />
              <datalist id="bk-types">
                {classTypes.map((t) => (
                  <option key={t} value={t} />
                ))}
              </datalist>
            </div>
            <div className="field">
              <label htmlFor="bk-cohort">Cohort size</label>
              <input id="bk-cohort" className="input" type="number" min={0} value={form.cohort_size} onChange={(e) => set('cohort_size', e.target.value)} />
            </div>
          </div>

          <div className="form-section-title">When &amp; where</div>
          <div className="field-row">
            <div className="field">
              <label htmlFor="bk-room">Room</label>
              <select id="bk-room" className="select" value={form.lab_id} onChange={(e) => set('lab_id', e.target.value)}>
                <option value="">Choose a room…</option>
                {labs.map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.code} · {l.capacity ? `capacity ${l.capacity}` : 'capacity unknown'}
                  </option>
                ))}
              </select>
            </div>
            {editingId !== null ? (
              <div className="field">
                <label htmlFor="bk-day">Day</label>
                <select id="bk-day" className="select" value={form.day} onChange={(e) => set('day', e.target.value as DayKey)}>
                  {DAY_KEYS.slice(0, 5).map((d) => (
                    <option key={d} value={d}>
                      {DAY_LONG[d]}
                    </option>
                  ))}
                </select>
                <div className="field-hint">Moves every date by the same number of days.</div>
              </div>
            ) : (
              <div className="field">
                <label htmlFor="bk-first">First date</label>
                <input id="bk-first" className="input" type="date" value={form.first_date} onChange={(e) => set('first_date', e.target.value)} />
                {firstDay && <div className="field-hint">Every {DAY_LONG[firstDay]}</div>}
              </div>
            )}
          </div>
          <div className="field-row">
            <div className="field">
              <label htmlFor="bk-start">Start time</label>
              <input id="bk-start" className="input" type="time" step={900} value={form.start_time} onChange={(e) => set('start_time', e.target.value)} />
            </div>
            <div className="field">
              <label htmlFor="bk-duration">Duration</label>
              <select id="bk-duration" className="select" value={form.duration_minutes} onChange={(e) => set('duration_minutes', Number(e.target.value))}>
                {[...new Set([...DURATIONS, form.duration_minutes])]
                  .sort((a, b) => a - b)
                  .map((m) => (
                    <option key={m} value={m}>
                      {formatDuration(m)}
                    </option>
                  ))}
              </select>
            </div>
            <div className="field">
              <span className="field-label">Ends</span>
              <div className="input" style={{ background: 'transparent' }}>
                {form.start_time ? formatRange(form.start_time, form.duration_minutes).split('–')[1] : '—'}
              </div>
            </div>
          </div>

          {editingId === null && (
            <>
              <div className="field-row">
                <div className="field">
                  <label htmlFor="bk-count">Number of classes</label>
                  <input id="bk-count" className="input" type="number" min={1} max={30} value={form.occurrences} onChange={(e) => set('occurrences', e.target.value)} />
                </div>
                <div className="field">
                  <span className="field-label">Frequency</span>
                  <div className="toggle-group">
                    {(['weekly', 'fortnightly'] as const).map((f) => (
                      <button key={f} type="button" className={form.frequency === f ? 'active' : ''} onClick={() => set('frequency', f)}>
                        {f === 'weekly' ? 'Weekly' : 'Fortnightly'}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
              <div className="field">
                <label htmlFor="bk-skip">Skip dates (e.g. mid-session recess)</label>
                <div style={{ display: 'flex', gap: 8 }}>
                  <input id="bk-skip" className="input" type="date" value={skipInput} onChange={(e) => setSkipInput(e.target.value)} />
                  <button
                    type="button"
                    className="btn secondary"
                    disabled={!skipInput || form.skip_dates.includes(skipInput)}
                    onClick={() => {
                      set('skip_dates', [...form.skip_dates, skipInput].sort())
                      setSkipInput('')
                    }}
                  >
                    Add
                  </button>
                </div>
                {form.skip_dates.length > 0 && (
                  <div className="chips">
                    {form.skip_dates.map((d) => (
                      <span key={d} className="chip">
                        {formatDate(d)}
                        <button type="button" aria-label={`Remove ${formatDate(d)}`} onClick={() => set('skip_dates', form.skip_dates.filter((x) => x !== d))}>
                          ×
                        </button>
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </>
          )}

          <div className="field">
            <label htmlFor="bk-pattern">Teaching week pattern (reference only)</label>
            <input id="bk-pattern" className="input" placeholder="17-21, 23-27" value={form.week_pattern_raw} onChange={(e) => set('week_pattern_raw', e.target.value)} />
            <div className="field-hint">Kept as text; dates above are what's booked.</div>
          </div>

          {editingId !== null && !readOnly && !cancelled && (
            <div className="field">
              <label htmlFor="bk-reason">Reason for change</label>
              <textarea id="bk-reason" className="textarea" value={reason} onChange={(e) => setReason(e.target.value)} placeholder="e.g. Resolve Tue 10:00 clash in 3-124" />
            </div>
          )}

          {!readOnly && !cancelled && (
            <div className="form-actions">
              <button type="submit" className="btn" disabled={!canSave}>
                {saving ? 'Saving…' : editingId === null ? 'Save booking' : 'Save changes'}
              </button>
              <Link to="/admin/bookings" className="btn secondary">
                {editingId === null ? 'Cancel' : 'Discard'}
              </Link>
            </div>
          )}
        </fieldset>

        <div>
          {editingId !== null && !cancelled && (
            <div className="card">
              <div className="card-title">Changes</div>
              {changes.length === 0 ? (
                <div className="field-hint">No changes yet.</div>
              ) : (
                changes.map((c) => (
                  <div key={c.key} className="diff-row">
                    <span className="key">{c.key}</span>
                    <span>
                      <span className="diff-old">{c.old}</span>
                      <span className="diff-new">{c.new}</span>
                    </span>
                  </div>
                ))
              )}
            </div>
          )}

          {!cancelled && (
            <div className="card">
              <div className="card-title">{editingId === null ? 'Live checks' : 'Re-check'}</div>
              {checkError && <div className="alert error">{checkError}</div>}
              {shownCheck ? (
                <>
                  <CheckList checks={shownCheck.checks} />
                  <div className="field-hint">
                    {shownCheck.occurrence_count} date(s): {formatDate(shownCheck.first_date)} – {formatDate(shownCheck.last_date)}
                    {lab && ` · ${lab.code}`}
                    {form.start_time && ` · ${formatTime(form.start_time)}`}
                  </div>
                </>
              ) : (
                !checkError && <div className="field-hint">Fill in the subject, room, time and cohort size to check for clashes.</div>
              )}
            </div>
          )}

          {original && (
            <div className="card">
              <div className="card-title">History</div>
              {original.history.length === 0 && (
                <div className="history-item">
                  Imported from Enterprise export
                  <div className="when">{original.occurrence_count} dates · {formatDate(original.first_date)} – {formatDate(original.last_date)}</div>
                </div>
              )}
              {original.history.map((h) => (
                <div key={h.id} className="history-item">
                  {ACTION_LABELS[h.action] ?? h.action}
                  {Object.entries(h.changes)
                    .filter(([key]) => key !== 'status')
                    .map(([key, [from, to]]) => ` · ${key} ${from} → ${to}`)
                    .join('')}
                  {h.reason && <div>“{h.reason}”</div>}
                  <div className="when">
                    {formatDateTime(h.created_at)}
                    {h.user_name && ` · ${h.user_name}`}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </form>
    </>
  )
}
