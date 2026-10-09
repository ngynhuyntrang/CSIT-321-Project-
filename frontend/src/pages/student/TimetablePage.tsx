import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getTimetable } from '../../api/student'
import { PageHeader } from '../../components/layout/PageHeader'
import { DayDots } from '../../components/student/DayDots'
import { TimetableGrid } from '../../components/student/TimetableGrid'
import { WeekPicker } from '../../components/student/WeekPicker'
import { DAY_SHORT, formatDate, formatMinutes, minutesOfDay } from '../../lib/format'
import type { Timetable } from '../../types/student'

const todayIso = () => new Date().toLocaleDateString('en-CA')

export function TimetablePage() {
  const [week, setWeek] = useState<string | undefined>(undefined)
  const [data, setData] = useState<Timetable | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getTimetable(week)
      .then((result) => {
        setData(result)
        setError(null)
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load timetable.'))
  }, [week])

  const subjects = data ? new Set(data.events.flatMap((e) => e.subject_codes)).size : 0
  const next = data?.next_class

  return (
    <>
      <PageHeader
        title="My Timetable"
        subtitle={
          data && data.selected_count > 0 ? (
            <>
              <strong>{data.selected_count} classes</strong> chosen
              {data.weeks.length > 0 &&
                ` · ${formatDate(data.weeks[0])} – ${formatDate(data.weeks[data.weeks.length - 1])}`}
            </>
          ) : (
            'Your classes for the week'
          )
        }
        actions={
          <Link to="/student/classes" className="btn secondary">
            Change classes
          </Link>
        }
      />
      {error && <div className="alert error">{error}</div>}
      {data && data.selected_count === 0 ? (
        <div className="card">
          <div className="empty">
            You haven't chosen any classes yet. <Link to="/student/classes">Choose your classes</Link> to build your
            timetable.
          </div>
        </div>
      ) : (
        data && (
          <>
            <WeekPicker
              weekStart={data.week_start}
              onChange={setWeek}
              note={data.events.length === 0 ? 'No classes this week.' : `${subjects} subject${subjects === 1 ? '' : 's'} this week`}
            />
            <div className="layout-2col">
              <div className="card">
                <TimetableGrid events={data.events} weekStart={data.week_start} today={todayIso()} />
                <div className="legend">
                  <span>
                    <span className="swatch" style={{ background: 'var(--accent)' }} />
                    Computer Lab
                  </span>
                  <span>
                    <span className="swatch" style={{ background: '#7c3aed' }} />
                    Lecture
                  </span>
                  <span>
                    <span className="swatch" style={{ background: '#0d9488' }} />
                    Tutorial / other
                  </span>
                </div>
              </div>
              <div>
                <div className="card">
                  <div className="card-title">On-campus days this week</div>
                  <div className="big-number">
                    {data.on_campus_days.length} day{data.on_campus_days.length === 1 ? '' : 's'}
                  </div>
                  <DayDots days={data.on_campus_days} />
                </div>
                <div className="card">
                  <div className="card-title">Next class</div>
                  {next ? (
                    <>
                      <div className="metric-row">
                        <span>{next.subject_codes.join('/')} {next.class_type}</span>
                        <span className="value">
                          {DAY_SHORT[next.day_of_week]} {formatMinutes(minutesOfDay(next.start))}
                        </span>
                      </div>
                      <div className="metric-row">
                        <span>Date</span>
                        <span className="value">{formatDate(next.start)}</span>
                      </div>
                      <div className="metric-row">
                        <span>Room</span>
                        <span className="value">{next.lab_code}</span>
                      </div>
                    </>
                  ) : (
                    <div className="field-hint">No upcoming classes.</div>
                  )}
                </div>
              </div>
            </div>
          </>
        )
      )}
    </>
  )
}
