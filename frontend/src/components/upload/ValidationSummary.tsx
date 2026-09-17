import type { IngestionErrorOut, IngestionRunSummary } from '../../types/ingestion'

const ERROR_TYPE_LABELS: Record<string, string> = {
  missing_value: 'Missing value',
  invalid_room_code: 'Unrecognized room code',
  malformed_day: 'Unrecognized day of week',
  malformed_time: 'Unrecognized time',
  malformed_duration: 'Malformed duration',
  malformed_date: 'Malformed activity date(s)',
  unparseable_subject_code: 'Could not extract subject code',
  invalid_cohort_size: 'Invalid cohort size',
  zero_cohort_size: 'Cohort size is 0',
  duration_end_time_mismatch: 'Start + duration ≠ recorded end time',
  date_count_mismatch: 'Date count ≠ Number Of Teaching Weeks',
}

interface ValidationSummaryProps {
  summary: IngestionRunSummary
}

function ErrorTable({
  rows,
  caption,
  variant,
}: {
  rows: IngestionErrorOut[]
  caption: string
  variant: 'error' | 'warning'
}) {
  if (rows.length === 0) return null
  return (
    <table className={`error-table error-table--${variant}`}>
      <caption>{caption}</caption>
      <thead>
        <tr>
          <th>Row</th>
          <th>Field</th>
          <th>Type</th>
          <th>Value</th>
          <th>Details</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((err, idx) => (
          <tr key={idx}>
            <td>{err.row_number || '—'}</td>
            <td>{err.field}</td>
            <td>{ERROR_TYPE_LABELS[err.error_type] ?? err.error_type}</td>
            <td>{err.raw_value ?? '—'}</td>
            <td>{err.message}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

export function ValidationSummary({ summary }: ValidationSummaryProps) {
  const statusLabel =
    summary.status === 'completed' ? 'Completed' : summary.status === 'failed' ? 'Failed' : 'Processing'

  const blockingErrors = summary.errors.filter((e) => e.severity === 'error')
  const warnings = summary.errors.filter((e) => e.severity === 'warning')

  return (
    <section className="validation-summary">
      <h2>Ingestion result: {summary.filename}</h2>
      <p>
        Status: <strong>{statusLabel}</strong>
      </p>
      <ul className="summary-stats">
        <li>Total rows: {summary.total_rows}</li>
        <li>Valid: {summary.valid_rows}</li>
        <li>Invalid: {summary.invalid_rows}</li>
        <li>With warnings: {summary.rows_with_warnings}</li>
      </ul>

      <ErrorTable
        rows={blockingErrors}
        caption="Errors (row excluded from baseline)"
        variant="error"
      />
      <ErrorTable
        rows={warnings}
        caption="Warnings (row included, flagged for review)"
        variant="warning"
      />
    </section>
  )
}
