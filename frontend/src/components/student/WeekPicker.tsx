import { addDays, formatShortDate } from '../../lib/format'

export function WeekPicker({
  weekStart,
  onChange,
  note,
}: {
  weekStart: string
  onChange: (weekStart: string) => void
  note?: string
}) {
  const end = addDays(weekStart, 4)
  return (
    <div className="week-picker">
      <button type="button" className="btn small secondary" aria-label="Previous week" onClick={() => onChange(addDays(weekStart, -7))}>
        ◂
      </button>
      <span className="label">
        Week of {formatShortDate(weekStart)} – {formatShortDate(end)} {weekStart.slice(0, 4)}
      </span>
      <button type="button" className="btn small secondary" aria-label="Next week" onClick={() => onChange(addDays(weekStart, 7))}>
        ▸
      </button>
      {note && <span className="field-hint" style={{ marginTop: 0 }}>{note}</span>}
    </div>
  )
}
