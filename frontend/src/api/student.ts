import type { Availability, ClassOptions, Period, Timetable } from '../types/student'
import { request } from './client'

const qs = (params: Record<string, string | undefined>) => {
  const search = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) if (v) search.set(k, v)
  const s = search.toString()
  return s ? `?${s}` : ''
}

export function listPeriods(): Promise<Period[]> {
  return request<Period[]>('/periods')
}

export function listSubjects(periodId?: string): Promise<string[]> {
  return request<string[]>(`/subjects${qs({ period_id: periodId })}`)
}

export function getClassOptions(periodId?: string): Promise<ClassOptions> {
  return request<ClassOptions>(`/student/classes${qs({ period_id: periodId })}`)
}

export function addSubject(subjectCode: string, periodId?: string): Promise<void> {
  return request<void>('/student/subjects', {
    method: 'POST',
    body: JSON.stringify({ subject_code: subjectCode, period_id: periodId ?? null }),
  })
}

export function removeSubject(subjectCode: string): Promise<void> {
  return request<void>(`/student/subjects/${encodeURIComponent(subjectCode)}`, { method: 'DELETE' })
}

export function selectClass(entryId: number): Promise<void> {
  return request<void>('/student/selections', {
    method: 'PUT',
    body: JSON.stringify({ entry_id: entryId }),
  })
}

export function unselectClass(entryId: number): Promise<void> {
  return request<void>(`/student/selections/${entryId}`, { method: 'DELETE' })
}

export function getTimetable(weekStart?: string): Promise<Timetable> {
  return request<Timetable>(`/student/timetable${qs({ week_start: weekStart })}`)
}

export function getAvailability(weekStart?: string): Promise<Availability> {
  return request<Availability>(`/rooms/availability${qs({ week_start: weekStart })}`)
}
