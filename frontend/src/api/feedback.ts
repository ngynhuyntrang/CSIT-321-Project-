import type { Feedback, FeedbackCreate } from '../types/student'
import { request } from './client'

export function submitFeedback(payload: FeedbackCreate): Promise<Feedback> {
  return request<Feedback>('/feedback', { method: 'POST', body: JSON.stringify(payload) })
}

export function myFeedback(): Promise<Feedback[]> {
  return request<Feedback[]>('/feedback/mine')
}

export function listFeedback(status?: Feedback['status']): Promise<Feedback[]> {
  return request<Feedback[]>(status ? `/feedback?status=${status}` : '/feedback')
}

export function setFeedbackStatus(id: number, status: Feedback['status']): Promise<Feedback> {
  return request<Feedback>(`/feedback/${id}`, { method: 'PATCH', body: JSON.stringify({ status }) })
}
