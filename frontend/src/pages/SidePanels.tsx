import { useEffect, useState } from 'react'
import { api, type Analysis } from '../api'
import { GradeChip } from '../components'
import { formatDate } from '../format'

export function ToolsCard({ analysis }: { analysis: Analysis }) {
  const tools = analysis.tools ?? []
  const allOk = tools.every((t) => t.ok)
  return (
    <article className="card">
      <div className="card-head">
        <div>
          <h2 className="card-title">Analysers used</h2>
          <p className="muted small">Static tools only; nothing from the repository is executed.</p>
        </div>
        <span className={`chip ${allOk ? 'chip-ok' : 'chip-warn'}`}>{allOk ? 'All engines passed' : 'Some engines failed'}</span>
      </div>
      <ul className="tool-list" data-testid="tools">
        {tools.map((t) => (
          <li key={t.tool}>
            <span className={`pill-dot ${t.ok ? 'ok' : 'bad'}`} aria-hidden="true" />
            <span className="mono"><strong>{t.tool}</strong> <span className="muted">{t.version}</span></span>
            <span className="muted small grow right">{t.findings} findings</span>
            <span className={`mono small ${t.ok ? 'ok-text' : 'error-text'}`} title={t.error ?? ''}>{t.ok ? 'PASS' : 'FAILED'}</span>
          </li>
        ))}
      </ul>
    </article>
  )
}

// Small SVG line chart of the overall score over earlier runs (oldest left).
function Trend({ runs }: { runs: Analysis[] }) {
  const points = [...runs].reverse().filter((r) => r.overall !== null)
  if (points.length < 2) return null
  const values = points.map((r) => r.overall as number)
  const low = Math.max(0, Math.min(...values) - 5)
  const high = Math.min(100, Math.max(...values) + 5)
  const x = (i: number) => 16 + (i * 368) / (points.length - 1)
  const y = (v: number) => 88 - ((v - low) / Math.max(high - low, 1)) * 72
  const path = points.map((r, i) => `${i ? 'L' : 'M'}${x(i)},${y(r.overall as number)}`).join(' ')
  return (
    <svg className="trend" viewBox="0 0 400 100" role="img"
      aria-label={`Overall score over ${points.length} runs: ${values.join(', ')}`}>
      <path d={`${path} L${x(points.length - 1)},96 L16,96 Z`} className="trend-area" />
      <path d={path} className="trend-line" />
      {points.map((r, i) => <circle key={r.id} cx={x(i)} cy={y(r.overall as number)} r="4" className="trend-dot" />)}
    </svg>
  )
}

export function HistoryCard({ analysis }: { analysis: Analysis }) {
  const [runs, setRuns] = useState<Analysis[]>([])
  useEffect(() => {
    api.history(analysis.id).then(setRuns).catch(() => setRuns([]))
  }, [analysis.id])
  const first = runs[runs.length - 1]?.overall
  const last = runs[0]?.overall
  const change = runs.length > 1 && first != null && last != null ? Math.round((last - first) * 10) / 10 : null
  return (
    <article className="card">
      <div className="card-head">
        <div>
          <h2 className="card-title">History &amp; trend</h2>
          <p className="muted small">Overall score of earlier analyses of this repository.</p>
        </div>
        {change !== null && <span className={`chip mono ${change >= 0 ? 'chip-ok' : 'chip-warn'}`}>{change >= 0 ? '+' : ''}{change} since first run</span>}
      </div>
      {runs.length < 2 ? (
        <p className="muted">Run the analysis again later to see a trend.</p>
      ) : (
        <>
          <Trend runs={runs} />
          <ol className="history" data-testid="history">
            {runs.map((h) => (
              <li key={h.id} className={h.id === analysis.id ? 'current' : ''}>
                <a href={`#/analyses/${h.id}`} className="mono">{h.commit_sha?.slice(0, 7) ?? '–'}</a>
                {h.id === analysis.id && <span className="chip mono">current</span>}
                <span className="grow" />
                <GradeChip grade={h.grade} />
                <span className="mono small">{h.overall}</span>
                <span className="muted small">{formatDate(h.created_at)}</span>
              </li>
            ))}
          </ol>
        </>
      )}
    </article>
  )
}
