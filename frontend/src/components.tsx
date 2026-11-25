import type { ReactNode } from 'react'
import type { Status } from './api'
import { gradeClass } from './grades'

type BadgeSize = 'sm' | 'md' | 'xl'

export function GradeBadge({ grade, size = 'md' }: { grade: string | null; size?: BadgeSize }) {
  return (
    <span className={`grade grade-${size} ${gradeClass(grade)}`}>
      <span className="grade-letter" data-testid="grade">{grade ?? '–'}</span>
      {size === 'xl' && <span className="grade-caption">Grade</span>}
    </span>
  )
}

export function GradeChip({ grade }: { grade: string | null }) {
  if (!grade) return null
  return <span className={`chip chip-grade ${gradeClass(grade)}`}>Grade {grade}</span>
}

const STATUS_LABEL: Record<Status, string> = {
  queued: 'Queued',
  running: 'Analysing…',
  completed: 'Completed',
  partial: 'Partial result',
  failed: 'Failed',
  cancelled: 'Cancelled',
}

export function StatusPill({ status }: { status: Status }) {
  return (
    <span className={`pill pill-${status}`} data-testid="status">
      <span className="pill-dot" aria-hidden="true" />
      {STATUS_LABEL[status]}
    </span>
  )
}

export function Chip({ children, mono = false }: { children: ReactNode; mono?: boolean }) {
  return <span className={`chip ${mono ? 'mono' : ''}`}>{children}</span>
}

const PATHS: Record<string, string> = {
  external: 'M14 3h7v7h-2V6.4l-9.3 9.3-1.4-1.4L17.6 5H14V3zM5 5h6v2H5v12h12v-6h2v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2z',
  refresh: 'M17.7 6.3A8 8 0 1 0 20 12h-2a6 6 0 1 1-1.8-4.2L13 11h7V4l-2.3 2.3z',
  shield: 'M12 2 4 5v6c0 5 3.4 9.7 8 11 4.6-1.3 8-6 8-11V5l-8-3zm-1 14-4-4 1.4-1.4 2.6 2.6 5.6-5.6L18 9l-7 7z',
  info: 'M11 7h2v2h-2V7zm0 4h2v6h-2v-6zm1-9a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm0 18a8 8 0 1 1 0-16 8 8 0 0 1 0 16z',
  check: 'M9 16.2 4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4L9 16.2z',
  stop: 'M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm4 14H8V8h8v8z',
  timer: 'M15 1H9v2h6V1zm-4 13h2V8h-2v6zm8-6.6 1.4-1.4-1.4-1.4-1.5 1.5A9 9 0 1 0 21 13a9 9 0 0 0-2-5.6zM12 20a7 7 0 1 1 0-14 7 7 0 0 1 0 14z',
  more: 'M12 8a2 2 0 1 0 0-4 2 2 0 0 0 0 4zm0 2a2 2 0 1 0 0 4 2 2 0 0 0 0-4zm0 6a2 2 0 1 0 0 4 2 2 0 0 0 0-4z',
  search: 'M15.5 14h-.8l-.3-.3A6.5 6.5 0 1 0 14 15.5l.3.3v.8l5 5 1.5-1.5-5-5zm-6 0a4.5 4.5 0 1 1 0-9 4.5 4.5 0 0 1 0 9z',
  moon: 'M12 3a9 9 0 1 0 9 9c0-.5 0-.9-.1-1.4A5.4 5.4 0 0 1 12.4 3.1 9 9 0 0 0 12 3z',
  sun: 'M12 7a5 5 0 1 0 0 10 5 5 0 0 0 0-10zM11 1h2v3h-2V1zm0 19h2v3h-2v-3zM1 11h3v2H1v-2zm19 0h3v2h-3v-2zM4.2 5.6l1.4-1.4 2.1 2.1-1.4 1.4-2.1-2.1zm12.1 12.1 1.4-1.4 2.1 2.1-1.4 1.4-2.1-2.1zM18.4 4.2l1.4 1.4-2.1 2.1-1.4-1.4 2.1-2.1zM6.3 16.3l1.4 1.4-2.1 2.1-1.4-1.4 2.1-2.1z',
  branch: 'M6 3a3 3 0 0 0-1 5.8v6.4a3 3 0 1 0 2 0v-1.5c0-1 .8-1.7 1.7-1.7H12a4 4 0 0 0 4-4v-.8a3 3 0 1 0-2 0V8a2 2 0 0 1-2 2H8.7c-.6 0-1.2.1-1.7.4V8.8A3 3 0 0 0 6 3z',
  close: 'M19 6.4 17.6 5 12 10.6 6.4 5 5 6.4 10.6 12 5 17.6 6.4 19 12 13.4 17.6 19 19 17.6 13.4 12z',
  arrow: 'M12 4l-1.4 1.4 5.6 5.6H4v2h12.2l-5.6 5.6L12 20l8-8z',
}

export function Icon({ name, size = 18 }: { name: keyof typeof PATHS | string; size?: number }) {
  return (
    <svg className="icon" width={size} height={size} viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path d={PATHS[name] ?? ''} fill="currentColor" />
    </svg>
  )
}
