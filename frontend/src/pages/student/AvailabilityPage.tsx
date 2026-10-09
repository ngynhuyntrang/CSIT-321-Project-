import { useEffect, useState } from 'react'
import { getAvailability } from '../../api/student'
import { PageHeader } from '../../components/layout/PageHeader'
import { WeekPicker } from '../../components/student/WeekPicker'
import { DAY_KEYS, DAY_SHORT, dayKeyOf, formatMinutes, formatTime, minutesOfDay, toMinutes } from '../../lib/format'
import type { Availability } from '../../types/student'

// Five shades, from mostly booked (light) to wide open (dark).
function heatClass(freeMinutes: number, windowMinutes: number): string {
  const share = windowMinutes ? freeMinutes / windowMinutes : 0
  if (share < 0.25) return 'h1'
  if (share < 0.45) return 'h2'
  if (share < 0.65) return 'h3'
  if (share < 0.85) return 'h4'
  return 'h5'
}

function hours(minutes: number): string {
  const h = minutes / 60
  return `${Number.isInteger(h) ? h : h.toFixed(1)}h`
}

export function AvailabilityPage() {
  const [week, setWeek] = useState<string | undefined>(undefined)
  const [data, setData] = useState<Availability | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getAvailability(week)
      .then((result) => {
        setData(result)
        setError(null)
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load availability.'))
  }, [week])

  const windowMinutes = data ? toMinutes(data.day_end) - toMinutes(data.day_start) : 0

  return (
    <>
      <PageHeader
        title="Lab Availability"
        subtitle={
          data && (
            <>
              When SCIT rooms are <strong>free of scheduled classes</strong> — {formatTime(data.day_start)} to{' '}
              {formatTime(data.day_end)}, Mon–Fri
            </>
          )
        }
        actions={
          <div className="alert info" style={{ margin: 0, maxWidth: 320 }}>
            Read-only. Rooms are allocated through class selection, not booked directly.
          </div>
        }
      />
      {error && <div className="alert error">{error}</div>}
      {data && (
        <>
          <WeekPicker
            weekStart={data.week_start}
            onChange={setWeek}
            note={data.has_bookings ? undefined : 'No classes scheduled this week (possibly a break).'}
          />
          <div className="layout-2col">
            <div className="card">
              <div className="card-title">Free hours — by room &amp; day</div>
              <div className="heatmap" role="table">
                <div />
                {DAY_KEYS.slice(0, 5).map((d) => (
                  <div key={d} className="col-label">
                    {DAY_SHORT[d]}
                  </div>
                ))}
                {data.rooms.map((room) => (
                  <div key={room.lab_id} style={{ display: 'contents' }}>
                    <div className="row-label">{room.lab_code}</div>
                    {DAY_KEYS.slice(0, 5).map((d) => {
                      const free = room.free_minutes[d] ?? 0
                      return (
                        <div
                          key={d}
                          className={`heat-cell ${heatClass(free, windowMinutes)}`}
                          title={`${room.lab_code} ${DAY_SHORT[d]}: ${hours(free)} free`}
                        >
                          {hours(free)}
                        </div>
                      )
                    })}
                  </div>
                ))}
              </div>
              <div className="legend">
                <span>Free hours/day:</span>
                {['h1', 'h2', 'h3', 'h4', 'h5'].map((h, i) => (
                  <span key={h}>
                    <span className={`swatch ${h}`} />
                    {['Mostly booked', '', '', '', 'Wide open'][i]}
                  </span>
                ))}
              </div>
            </div>

            <div className="card">
              <div className="card-title">
                Free now
                {data.free_now && ` · ${DAY_SHORT[dayKeyOf(data.now)]} ${formatMinutes(minutesOfDay(data.now))}`}
              </div>
              {data.free_now === null ? (
                <div className="field-hint">
                  Outside {formatTime(data.day_start)}–{formatTime(data.day_end)} on a weekday — check back during the
                  day.
                </div>
              ) : (
                data.free_now.map((r) => (
                  <div key={r.lab_code} className="free-row">
                    <span>
                      <span className="pill">{r.lab_code}</span> {r.capacity ? `${r.capacity} seats` : ''}
                    </span>
                    <span className="until">
                      {r.free
                        ? `free until ${formatMinutes(minutesOfDay(r.until))}`
                        : `in use · free ${formatMinutes(minutesOfDay(r.until))}`}
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>
        </>
      )}
    </>
  )
}
