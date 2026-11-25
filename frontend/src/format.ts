export function repoName(url: string): string {
  return url.replace('https://github.com/', '')
}

export function repoParts(url: string): { owner: string; name: string } {
  const [owner = '', name = ''] = repoName(url).split('/')
  return { owner, name }
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

export function formatElapsed(fromIso: string, now: number): string {
  const seconds = Math.max(0, Math.floor((now - new Date(fromIso).getTime()) / 1000))
  const minutes = Math.floor(seconds / 60)
  return `${String(minutes).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`
}

export function elapsedSeconds(fromIso: string, now: number): number {
  return Math.max(0, (now - new Date(fromIso).getTime()) / 1000)
}

const UNITS: [Intl.RelativeTimeFormatUnit, number][] = [
  ['day', 86400], ['hour', 3600], ['minute', 60],
]

export function relativeTime(iso: string, now: number = Date.now()): string {
  const seconds = Math.round((new Date(iso).getTime() - now) / 1000)
  const format = new Intl.RelativeTimeFormat(undefined, { numeric: 'auto' })
  const unit = UNITS.find(([, size]) => Math.abs(seconds) >= size)
  return unit ? format.format(Math.round(seconds / unit[1]), unit[0]) : format.format(0, 'minute')
}

// Language label from the real file counts of the analysis (no guessing).
export function languageOf(stats: Record<string, number> | null): string | null {
  if (!stats) return null
  const python = stats.python_files > 0
  const js = stats.js_files > 0
  if (python && js) return 'Python + JS/TS'
  if (python) return 'Python'
  if (js) return 'JavaScript/TS'
  return null
}
