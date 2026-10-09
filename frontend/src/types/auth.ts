export type Role = 'student' | 'staff' | 'admin'
export type UserStatus = 'active' | 'pending' | 'disabled'

export interface User {
  id: number
  email: string
  full_name: string
  student_number: string | null
  role: Role
  status: UserStatus
  created_at: string
}

export interface LoginResponse {
  token: string
  expires_at: string
  user: User
}

export interface SignupRequest {
  email: string
  full_name: string
  student_number: string | null
  role: 'student' | 'staff'
  password: string
}
