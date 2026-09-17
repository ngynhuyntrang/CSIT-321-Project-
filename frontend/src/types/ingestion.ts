export interface IngestionErrorOut {
  row_number: number
  field: string
  error_type: 'missing_value' | 'invalid_room_code' | 'malformed_time_block' | string
  raw_value: string | null
  message: string
}

export interface IngestionRunSummary {
  id: number
  filename: string
  uploaded_at: string
  status: 'processing' | 'completed' | 'failed'
  total_rows: number
  valid_rows: number
  invalid_rows: number
  errors: IngestionErrorOut[]
}
