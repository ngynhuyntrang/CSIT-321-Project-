import type { ReactNode } from 'react'
import { CATEGORY_LABELS } from '../../lib/feedback'
import { formatDate } from '../../lib/format'
import type { Feedback } from '../../types/student'

export function FeedbackItem({ feedback: f, meta, action }: { feedback: Feedback; meta?: ReactNode; action?: ReactNode }) {
  return (
    <div className="feedback-item">
      <div className="top">
        <strong>
          {f.class_label ?? 'General'} · {CATEGORY_LABELS[f.category]}
        </strong>
        <span className={`status-badge ${f.status === 'reviewed' ? 'ok' : 'info'}`}>
          {f.status === 'reviewed' ? 'Reviewed' : 'Received'}
        </span>
      </div>
      {f.comment}
      <div className="field-hint">
        {formatDate(f.created_at)} · rating {f.rating}/5
        {f.lab_code && ` · ${f.lab_code}`}
        {meta}
      </div>
      {action && <div style={{ marginTop: 8 }}>{action}</div>}
    </div>
  )
}
