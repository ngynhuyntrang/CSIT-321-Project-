import type { IngestionRunSummary } from '../../types/ingestion'

const ERROR_TYPE_LABELS: Record<string, string> = {
  missing_value: 'Thiếu dữ liệu',
  invalid_room_code: 'Mã phòng không hợp lệ',
  malformed_time_block: 'Khung giờ không hợp lệ',
}

interface ValidationSummaryProps {
  summary: IngestionRunSummary
}

export function ValidationSummary({ summary }: ValidationSummaryProps) {
  const statusLabel =
    summary.status === 'completed'
      ? 'Hoàn tất'
      : summary.status === 'failed'
        ? 'Thất bại'
        : 'Đang xử lý'

  return (
    <section className="validation-summary">
      <h2>Kết quả nạp dữ liệu: {summary.filename}</h2>
      <p>
        Trạng thái: <strong>{statusLabel}</strong>
      </p>
      <ul className="summary-stats">
        <li>Tổng số dòng: {summary.total_rows}</li>
        <li>Hợp lệ: {summary.valid_rows}</li>
        <li>Lỗi: {summary.invalid_rows}</li>
      </ul>

      {summary.errors.length > 0 && (
        <table className="error-table">
          <thead>
            <tr>
              <th>Dòng</th>
              <th>Trường</th>
              <th>Loại lỗi</th>
              <th>Giá trị</th>
              <th>Chi tiết</th>
            </tr>
          </thead>
          <tbody>
            {summary.errors.map((err, idx) => (
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
      )}
    </section>
  )
}
