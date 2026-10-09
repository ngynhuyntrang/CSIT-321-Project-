import { useState } from 'react'
import { useAuth } from '../../auth/useAuth'
import { PageHeader } from '../../components/layout/PageHeader'
import { UploadForm } from '../../components/upload/UploadForm'
import { ValidationSummary } from '../../components/upload/ValidationSummary'
import type { IngestionRunSummary } from '../../types/ingestion'

export function IngestPage() {
  const { user } = useAuth()
  const [summary, setSummary] = useState<IngestionRunSummary | null>(null)

  return (
    <>
      <PageHeader
        title="Upload & Validate"
        subtitle={
          <>
            FR1 — <strong>Timetable Data Ingestion &amp; Integrity Check</strong>
          </>
        }
      />
      {user?.role === 'admin' ? (
        <div className="card">
          <div className="card-title">Upload Enterprise export</div>
          <UploadForm onUploaded={setSummary} />
        </div>
      ) : (
        <div className="alert info">Only SCIT Operations admins can upload a new baseline.</div>
      )}
      {summary && <ValidationSummary summary={summary} />}
    </>
  )
}
