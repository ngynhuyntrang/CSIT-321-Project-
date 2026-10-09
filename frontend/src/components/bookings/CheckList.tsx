import type { CheckItem } from '../../types/booking'

const MARKS: Record<CheckItem['level'], string> = { ok: '✓', warning: '!', error: '✕' }

export function CheckList({ checks }: { checks: CheckItem[] }) {
  return (
    <>
      {checks.map((check, idx) => (
        <div key={`${check.title}-${idx}`} className={`check-item ${check.level}`}>
          <span className="mark" aria-hidden>
            {MARKS[check.level]}
          </span>
          <div>
            <strong>{check.title}</strong>
            {check.detail}
          </div>
        </div>
      ))}
    </>
  )
}
