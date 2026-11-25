import type { Status } from './api'

const GRADE_CLASS: Record<string, string> = { A: 'g-a', B: 'g-b', C: 'g-c', D: 'g-d', E: 'g-e' }

export function GradeBadge({ grade, size = 'md' }: { grade: string | null; size?: 'sm' | 'md' | 'lg' }) {
  return (
    <span className={`grade grade-${size} ${grade ? GRADE_CLASS[grade] : 'g-none'}`} data-testid="grade">
      {grade ?? '–'}
    </span>
  )
}

const STATUS_LABEL: Record<Status, string> = {
  queued: 'Queued',
  running: 'Analysing…',
  completed: 'Completed',
  partial: 'Partial result',
  failed: 'Failed',
}

export function StatusPill({ status }: { status: Status }) {
  return (
    <span className={`pill pill-${status}`} data-testid="status">
      {STATUS_LABEL[status]}
    </span>
  )
}
