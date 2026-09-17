import { useRef, useState } from 'react'
import { uploadTimetable } from '../../api/client'
import type { IngestionRunSummary } from '../../types/ingestion'

interface UploadFormProps {
  onUploaded: (summary: IngestionRunSummary) => void
}

export function UploadForm({ onUploaded }: UploadFormProps) {
  const [isUploading, setIsUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    const file = fileInputRef.current?.files?.[0]
    if (!file) {
      setError('Chọn một file .xlsx hoặc .csv trước.')
      return
    }

    setIsUploading(true)
    setError(null)
    try {
      const summary = await uploadTimetable(file)
      onUploaded(summary)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload thất bại.')
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="upload-form">
      <label htmlFor="timetable-file">Semester timetable export (.xlsx / .csv)</label>
      <input id="timetable-file" ref={fileInputRef} type="file" accept=".xlsx,.xls,.csv" />
      <button type="submit" disabled={isUploading}>
        {isUploading ? 'Đang tải lên…' : 'Upload & Validate'}
      </button>
      {error && <p className="error-text">{error}</p>}
    </form>
  )
}
