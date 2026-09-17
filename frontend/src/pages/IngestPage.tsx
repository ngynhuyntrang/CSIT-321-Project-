import { useState } from 'react'
import { UploadForm } from '../components/upload/UploadForm'
import { ValidationSummary } from '../components/upload/ValidationSummary'
import type { IngestionRunSummary } from '../types/ingestion'

export function IngestPage() {
  const [summary, setSummary] = useState<IngestionRunSummary | null>(null)

  return (
    <div className="ingest-page">
      <h1>Bước 1 — Nạp & kiểm tra dữ liệu thời khóa biểu</h1>
      <UploadForm onUploaded={setSummary} />
      {summary && <ValidationSummary summary={summary} />}
    </div>
  )
}
