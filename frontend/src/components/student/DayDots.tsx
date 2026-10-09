import { DAY_KEYS, DAY_LONG } from '../../lib/format'
import type { DayKey } from '../../types/booking'

export function DayDots({ days }: { days: DayKey[] }) {
  return (
    <div className="day-dots">
      {DAY_KEYS.slice(0, 5).map((d) => (
        <span
          key={d}
          className={`day-dot${days.includes(d) ? ' on' : ''}`}
          title={`${DAY_LONG[d]}${days.includes(d) ? ' — on campus' : ''}`}
        >
          {DAY_LONG[d][0]}
        </span>
      ))}
    </div>
  )
}
