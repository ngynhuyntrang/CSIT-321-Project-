import type {
  BookingCheckRequest,
  BookingCheckResult,
  BookingCreate,
  BookingDetail,
  BookingFilters,
  BookingList,
  BookingUpdate,
  Lab,
} from '../types/booking'
import { ApiError, getToken, request } from './client'

function query(filters: BookingFilters): string {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== '' && value !== null) params.set(key, String(value))
  }
  const qs = params.toString()
  return qs ? `?${qs}` : ''
}

export function listLabs(): Promise<Lab[]> {
  return request<Lab[]>('/labs')
}

export function listBookings(filters: BookingFilters): Promise<BookingList> {
  return request<BookingList>(`/bookings${query(filters)}`)
}

export function listClassTypes(): Promise<string[]> {
  return request<string[]>('/bookings/class-types')
}

export function getBooking(id: number): Promise<BookingDetail> {
  return request<BookingDetail>(`/bookings/${id}`)
}

export function checkBooking(
  payload: BookingCheckRequest,
  signal?: AbortSignal,
): Promise<BookingCheckResult> {
  return request<BookingCheckResult>('/bookings/check', {
    method: 'POST',
    body: JSON.stringify(payload),
    signal,
  })
}

export function createBooking(payload: BookingCreate): Promise<BookingDetail> {
  return request<BookingDetail>('/bookings', { method: 'POST', body: JSON.stringify(payload) })
}

export function updateBooking(id: number, payload: BookingUpdate): Promise<BookingDetail> {
  return request<BookingDetail>(`/bookings/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function cancelBooking(id: number, reason: string): Promise<BookingDetail> {
  return request<BookingDetail>(`/bookings/${id}/cancel`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  })
}

/** Downloads the filtered bookings as .xlsx. A plain link can't send the
 * bearer token, so fetch the file and hand the browser a blob URL. */
export async function downloadBookingsExport(filters: BookingFilters): Promise<void> {
  const { page: _page, page_size: _size, ...rest } = filters
  const token = getToken()
  const response = await fetch(`/api/bookings/export.xlsx${query(rest)}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!response.ok) throw new ApiError(`Export failed: ${response.status}`, response.status)
  const url = URL.createObjectURL(await response.blob())
  const link = document.createElement('a')
  link.href = url
  link.download = 'scit-bookings.xlsx'
  link.click()
  URL.revokeObjectURL(url)
}
