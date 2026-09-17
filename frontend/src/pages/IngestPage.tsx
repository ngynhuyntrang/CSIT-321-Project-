import { useState } from 'react'
import { UploadForm } from '../components/upload/UploadForm'
import { ValidationSummary } from '../components/upload/ValidationSummary'
import type { IngestionRunSummary } from '../types/ingestion'

export function IngestPage() {
  const [summary, setSummary] = useState<IngestionRunSummary | null>(null)

  return (
    <div className="ingest-page">
      <h1>Step 1 — Upload &amp; validate timetable data</h1>
      <UploadForm onUploaded={setSummary} />
      {summary && <ValidationSummary summary={summary} />}
    </div>
  )
}
