export function StatCard({
  value,
  label,
  tone,
  selected,
  onClick,
}: {
  value: number | string
  label: string
  tone?: 'ok' | 'error' | 'warning'
  selected?: boolean
  onClick?: () => void
}) {
  const className = `stat-card${tone ? ` ${tone}` : ''}${onClick ? ' clickable' : ''}${selected ? ' selected' : ''}`
  const body = (
    <>
      <div className="value">{value}</div>
      <div className="label">{label}</div>
    </>
  )
  return onClick ? (
    <button type="button" className={className} onClick={onClick} aria-pressed={selected}>
      {body}
    </button>
  ) : (
    <div className={className}>{body}</div>
  )
}
