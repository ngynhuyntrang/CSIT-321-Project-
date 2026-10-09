export type DayKey = 'mon' | 'tue' | 'wed' | 'thu' | 'fri' | 'sat' | 'sun'
export type BookingFlag = 'manual' | 'clash' | 'over_capacity'

export interface Lab {
  id: number
  code: string
  building: string | null
  capacity: number | null
  room_type: string | null
  weekly_available_hours: number | null
  active: boolean
}

export interface Booking {
  id: number
  activity_name: string | null
  subject_codes: string[]
  class_type: string
  lab_id: number | null
  lab_code: string | null
  lab_capacity: number | null
  day_of_week: DayKey
  start_time: string
  duration_minutes: number
  cohort_size: number
  week_pattern_raw: string | null
  source: 'enterprise' | 'manual'
  status: 'active' | 'cancelled'
  occurrence_count: number
  first_date: string | null
  last_date: string | null
  has_clash: boolean
  over_capacity: boolean
}

export interface BookingChange {
  id: number
  action: 'create' | 'update' | 'cancel'
  changes: Record<string, [string, string]>
  reason: string | null
  user_name: string | null
  created_at: string
}

export interface BookingDetail extends Booking {
  dates: string[]
  history: BookingChange[]
}

export interface BookingStats {
  total: number
  manual: number
  clashes: number
  over_capacity: number
}

export interface BookingList {
  items: Booking[]
  total: number
  page: number
  page_size: number
  stats: BookingStats
}

export interface BookingFilters {
  q?: string
  lab_id?: number
  class_type?: string
  day?: DayKey
  flag?: BookingFlag
  page?: number
  page_size?: number
}

export interface Recurrence {
  first_date: string
  occurrences: number
  frequency: 'weekly' | 'fortnightly'
  skip_dates: string[]
}

export interface BookingSchedule {
  subject_codes: string[]
  class_type: string
  lab_id: number
  start_time: string
  duration_minutes: number
  cohort_size: number
}

export interface BookingCreate extends BookingSchedule {
  activity_name: string | null
  week_pattern_raw: string | null
  recurrence: Recurrence
}

export interface BookingUpdate extends Partial<BookingSchedule> {
  activity_name?: string | null
  day_of_week?: DayKey
  week_pattern_raw?: string | null
  reason: string
}

export interface BookingCheckRequest extends BookingSchedule {
  entry_id?: number
  day_of_week?: DayKey
  recurrence?: Recurrence
}

export interface CheckItem {
  level: 'ok' | 'warning' | 'error'
  title: string
  detail: string
}

export interface BookingCheckResult {
  can_save: boolean
  occurrence_count: number
  first_date: string | null
  last_date: string | null
  checks: CheckItem[]
}
