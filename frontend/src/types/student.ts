import type { DayKey } from './booking'

export interface Period {
  id: string
  start: string
  end: string
}

export interface ClassOption {
  entry_id: number
  activity_name: string | null
  class_type: string
  day_of_week: DayKey
  start_time: string
  duration_minutes: number
  lab_code: string | null
  capacity: number | null
  cohort_size: number
  picks: number
  seats_left: number | null
  full: boolean
  selected: boolean
  clashes_with: string[]
  adds_day: boolean
  /** On-campus days if this class were chosen (replacing any pick in the same slot). */
  days_after: number
  first_date: string
  last_date: string
  occurrence_count: number
}

export interface SubjectClasses {
  subject_code: string
  groups: { class_type: string; options: ClassOption[] }[]
}

export interface ClassOptions {
  period: Period | null
  periods: Period[]
  subjects: SubjectClasses[]
  on_campus_days: DayKey[]
}

export interface TimetableEvent {
  entry_id: number
  subject_codes: string[]
  activity_name: string | null
  class_type: string
  lab_code: string | null
  start: string
  end: string
  day_of_week: DayKey
}

export interface Timetable {
  week_start: string
  weeks: string[]
  events: TimetableEvent[]
  on_campus_days: DayKey[]
  next_class: TimetableEvent | null
  selected_count: number
}

export interface RoomAvailability {
  lab_id: number
  lab_code: string
  capacity: number | null
  free_minutes: Partial<Record<DayKey, number>>
}

export interface Availability {
  week_start: string
  day_start: string
  day_end: string
  has_bookings: boolean
  rooms: RoomAvailability[]
  now: string
  free_now: { lab_code: string; capacity: number | null; free: boolean; until: string }[] | null
}

export type FeedbackCategory = 'timing' | 'room' | 'days' | 'other'

export interface Feedback {
  id: number
  entry_id: number | null
  class_label: string | null
  lab_code: string | null
  category: FeedbackCategory
  rating: number
  comment: string
  anonymous: boolean
  status: 'received' | 'reviewed'
  author: string | null
  created_at: string
}

export interface FeedbackCreate {
  entry_id: number | null
  lab_id: number | null
  category: FeedbackCategory
  rating: number
  comment: string
  anonymous: boolean
}
