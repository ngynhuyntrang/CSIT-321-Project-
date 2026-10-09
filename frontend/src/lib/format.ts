import type { DayKey } from '../types/booking'

export const DAY_KEYS: DayKey[] = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']

export const DAY_SHORT: Record<DayKey, string> = {
  mon: 'Mon',
  tue: 'Tue',
  wed: 'Wed',
  thu: 'Thu',
  fri: 'Fri',
  sat: 'Sat',
  sun: 'Sun',
}

export const DAY_LONG: Record<DayKey, string> = {
  mon: 'Monday',
  tue: 'Tuesday',
  wed: 'Wednesday',
  thu: 'Thursday',
  fri: 'Friday',
  sat: 'Saturday',
  sun: 'Sunday',
}

/** "13:30" or "13:30:00" -> minutes since midnight. */
export function toMinutes(time: string): number {
  const [h = '0', m = '0'] = time.split(':')
  return Number(h) * 60 + Number(m)
}

/** "13:30:00" -> "1:30 PM" */
export function formatTime(time: string): string {
  return formatMinutes(toMinutes(time))
}

export function formatMinutes(total: number): string {
  const h = Math.floor(total / 60) % 24
  const m = total % 60
  return `${h % 12 || 12}:${String(m).padStart(2, '0')} ${h < 12 ? 'AM' : 'PM'}`
}

/** "12:30:00", 60 -> "12:30–1:30 PM" style range. */
export function formatRange(start: string, durationMinutes: number): string {
  const begin = toMinutes(start)
  return `${formatMinutes(begin)}–${formatMinutes(begin + durationMinutes)}`
}

export function formatDuration(minutes: number): string {
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  if (!h) return `${m} min`
  return m ? `${h} hr ${m} min` : `${h} hr`
}

/** ISO "2026-03-17" -> "17/03/2026" (UOW's day-first format). */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  const [y, m, d] = iso.slice(0, 10).split('-')
  return `${d}/${m}/${y}`
}

export function formatDateTime(iso: string): string {
  return new Date(iso.endsWith('Z') ? iso : `${iso}Z`).toLocaleString(undefined, {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

/** "17:30" (input type=time) -> "17:30" ; "17:30:00" -> "17:30" */
export function toTimeInput(time: string): string {
  return time.slice(0, 5)
}

/** Adds days to an ISO date string, returning an ISO date string. */
export function addDays(iso: string, days: number): string {
  const [y, m, d] = iso.slice(0, 10).split('-').map(Number)
  const date = new Date(Date.UTC(y!, m! - 1, d! + days))
  return date.toISOString().slice(0, 10)
}

/** "2026-03-09" -> "9 Mar" */
export function formatShortDate(iso: string): string {
  const [y, m, d] = iso.slice(0, 10).split('-').map(Number)
  return new Date(Date.UTC(y!, m! - 1, d!)).toLocaleDateString('en-AU', {
    day: 'numeric',
    month: 'short',
    timeZone: 'UTC',
  })
}

/** Minutes since midnight of an ISO datetime's wall-clock time. */
export function minutesOfDay(isoDateTime: string): number {
  const [h = '0', m = '0'] = isoDateTime.slice(11, 16).split(':')
  return Number(h) * 60 + Number(m)
}

/** Weekday key of an ISO date or datetime (by its calendar date). */
export function dayKeyOf(iso: string): DayKey {
  const [y, m, d] = iso.slice(0, 10).split('-').map(Number)
  return DAY_KEYS[(new Date(Date.UTC(y!, m! - 1, d!)).getUTCDay() + 6) % 7]!
}
