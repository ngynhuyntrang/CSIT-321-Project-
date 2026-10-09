import type { IngestionRunSummary } from '../types/ingestion'

const API_BASE = '/api'
const TOKEN_KEY = 'scit.token'

export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

export function setToken(token: string | null): void {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token)
    else localStorage.removeItem(TOKEN_KEY)
  } catch {
    // Storage unavailable (private mode): the session lasts for this page load only.
  }
}

/** FastAPI returns `detail` as a string, or as a list of validation errors. */
function errorMessage(body: { detail?: unknown }, status: number): string {
  const { detail } = body
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail.length > 0) {
    return detail
      .map((d: { msg?: string }) => (d.msg ?? '').replace(/^Value error, /, ''))
      .filter(Boolean)
      .join(' ')
  }
  return `Request failed: ${status}`
}

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  const token = getToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (init.body && !(init.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  const response = await fetch(`${API_BASE}${path}`, { ...init, headers })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    if (response.status === 401 && token) {
      setToken(null)
      window.dispatchEvent(new Event('auth:expired'))
    }
    throw new ApiError(errorMessage(body, response.status), response.status)
  }
  if (response.status === 204) return undefined as T
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
