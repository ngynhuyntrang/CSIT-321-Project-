import { addDays, DAY_KEYS, DAY_SHORT, formatMinutes, minutesOfDay } from '../../lib/format'
import type { TimetableEvent } from '../../types/student'

const PX_PER_MIN = 52 / 60
const DEFAULT_START = 8 * 60 + 30
const DEFAULT_END = 18 * 60 + 30

function blockClass(classType: string): string {
  const t = classType.toLowerCase()
  if (t.includes('lab')) return 'lab'
  if (t.includes('lecture')) return 'lecture'
  return 'other'
}

export function TimetableGrid({
  events,
  weekStart,
  today,
}: {
  events: TimetableEvent[]
  weekStart: string
  today?: string
}) {
  // Stretch the visible hours to fit early or evening classes.
  const starts = events.map((e) => minutesOfDay(e.start))
  const ends = events.map((e) => minutesOfDay(e.end))
  const first = Math.min(DEFAULT_START, ...starts.map((m) => Math.floor((m - 30) / 60) * 60 + 30))
  const last = Math.max(DEFAULT_END, ...ends.map((m) => Math.ceil((m - 30) / 60) * 60 + 30))
  const height = (last - first) * PX_PER_MIN
  const hours: number[] = []
  for (let m = first; m < last; m += 60) hours.push(m)

  return (
    <div className="timetable" role="table" aria-label="Weekly timetable">
      <div />
      {DAY_KEYS.slice(0, 5).map((d, i) => (
        <div key={d} className={`day-head${addDays(weekStart, i) === today ? ' today' : ''}`}>
          {DAY_SHORT[d]}
        </div>
      ))}
      <div className="hours" style={{ height }}>
        {hours.map((m) => (
          <span key={m} className="hour-label" style={{ top: (m - first) * PX_PER_MIN }}>
            {formatMinutes(m).replace(' AM', '').replace(' PM', '')}
          </span>
        ))}
      </div>
      {DAY_KEYS.slice(0, 5).map((d) => (
        <div key={d} className="day-col" style={{ height }}>
          {hours.map((m) => (
            <div key={m} className="hour-line" style={{ top: (m - first) * PX_PER_MIN }} />
          ))}
          {events
            .filter((e) => e.day_of_week === d)
            .map((e) => {
              const top = (minutesOfDay(e.start) - first) * PX_PER_MIN
              const h = (minutesOfDay(e.end) - minutesOfDay(e.start)) * PX_PER_MIN
              return (
                <div
                  key={`${e.entry_id}-${e.start}`}
                  className={`tt-block ${blockClass(e.class_type)}`}
                  style={{ top: top + 2, height: h - 4 }}
                  title={`${e.activity_name ?? ''} ${formatMinutes(minutesOfDay(e.start))}–${formatMinutes(minutesOfDay(e.end))}`}
                >
                  <strong>{e.subject_codes.join('/')}</strong>
                  {e.class_type} · {e.lab_code}
                </div>
              )
            })}
        </div>
      ))}
    </div>
  )
}
