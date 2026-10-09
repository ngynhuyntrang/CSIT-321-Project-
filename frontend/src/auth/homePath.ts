import type { User } from '../types/auth'

/** Where a signed-in user lands after login or on `/`. */
export function homePath(user: User): string {
  return user.role === 'student' ? '/student/timetable' : '/admin/upload'
}
