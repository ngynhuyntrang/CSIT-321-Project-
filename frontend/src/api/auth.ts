import type { LoginResponse, SignupRequest, User, UserStatus } from '../types/auth'
import { request } from './client'

export function login(email: string, password: string, rememberMe: boolean): Promise<LoginResponse> {
  return request<LoginResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password, remember_me: rememberMe }),
  })
}

export function signup(payload: SignupRequest): Promise<User> {
  return request<User>('/auth/signup', { method: 'POST', body: JSON.stringify(payload) })
}

export function logout(): Promise<void> {
  return request<void>('/auth/logout', { method: 'POST' })
}

export function getMe(): Promise<User> {
  return request<User>('/auth/me')
}

export function listUsers(status?: UserStatus): Promise<User[]> {
  return request<User[]>(status ? `/users?status=${status}` : '/users')
}

export function updateUser(
  id: number,
  changes: Partial<Pick<User, 'role' | 'status'>>,
): Promise<User> {
  return request<User>(`/users/${id}`, { method: 'PATCH', body: JSON.stringify(changes) })
}
