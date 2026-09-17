import type { IngestionRunSummary } from '../types/ingestion'

const API_BASE = '/api'

class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init)
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new ApiError(body.detail ?? `Request failed: ${response.status}`, response.status)
  }
  return response.json() as Promise<T>
}

export interface HealthStatus {
  status: string
  db: string
}

export function getHealth(): Promise<HealthStatus> {
  return request<HealthStatus>('/health')
}

export function uploadTimetable(file: File): Promise<IngestionRunSummary> {
  const formData = new FormData()
  formData.append('file', file)
  return request<IngestionRunSummary>('/ingestion/upload', {
    method: 'POST',
    body: formData,
  })
}

export function getIngestionSummary(runId: number): Promise<IngestionRunSummary> {
  return request<IngestionRunSummary>(`/ingestion/${runId}/summary`)
}
