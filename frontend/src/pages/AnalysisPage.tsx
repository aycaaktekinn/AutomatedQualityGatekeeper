import { useEffect, useState } from 'react'
import { api, FINAL_STATUSES, type Analysis, type CharacteristicName } from '../api'
import { GradeBadge, StatusPill } from '../components'
import { formatDate, repoName } from '../format'
import { FindingsTable } from './FindingsTable'

const POLL_MS = 3000 // FR-06: status refreshes at least every 5 seconds

const CHARACTERISTICS: { key: CharacteristicName; label: string; weight: string; note?: string }[] = [
  { key: 'maintainability', label: 'Maintainability', weight: '40%' },
  { key: 'security', label: 'Security', weight: '35%' },
  { key: 'reliability', label: 'Reliability', weight: '25%', note: 'Approximate: measured statically' },
]

const DETAIL_LABELS: Record<string, string> = {
  average_complexity: 'Average McCabe complexity',
  high_complexity_ratio: 'Functions over complexity 10',
  lint_issues_per_kloc: 'Lint issues per 1,000 lines',
  maintainability_index: 'Maintainability index',
  weighted_findings_per_kloc: 'Weighted findings per 1,000 lines',
  high: 'High severity findings',
  medium: 'Medium severity findings',
  low: 'Low severity findings',
  error_handling_issues_per_kloc: 'Error-handling issues per 1,000 lines',
  test_to_source_ratio: 'Test files per source file',
}

function formatDetail(key: string, value: number): string {
  if (key === 'high_complexity_ratio') return `${(value * 100).toFixed(1)}%`
  return Number.isInteger(value) ? String(value) : value.toFixed(2)
}

function useAnalysis(id: string) {
  const [analysis, setAnalysis] = useState<Analysis | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    let timer: number | undefined
    let cancelled = false
    const load = async () => {
      try {
        const data = await api.getAnalysis(id)
        if (cancelled) return
        setAnalysis(data)
        if (!FINAL_STATUSES.includes(data.status)) timer = window.setTimeout(load, POLL_MS)
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Could not load the analysis.')
      }
    }
    load()
    return () => {
      cancelled = true
      window.clearTimeout(timer)
    }
  }, [id])
  return { analysis, error }
}

// Review fix (dogfooding): the page was one component with McCabe 16; it is now split into parts.
export function AnalysisPage({ id }: { id: string }) {
  const { analysis, error } = useAnalysis(id)
  if (error) return <p className="error" role="alert">{error}</p>
  if (!analysis) return <p className="muted">Loading…</p>
  const done = FINAL_STATUSES.includes(analysis.status)
  return (
    <>
      <Summary analysis={analysis} done={done} />
      {analysis.scores && <ScoreCards analysis={analysis} />}
      {done && analysis.status !== 'failed' && <FindingsTable analysisId={analysis.id} />}
      {done && (
        <section className="two-col">
          <ToolsCard analysis={analysis} />
          <HistoryCard analysis={analysis} />
        </section>
      )}
    </>
  )
}

function Summary({ analysis, done }: { analysis: Analysis; done: boolean }) {
  return (
    <section className="card summary" aria-live="polite">
      <div className="summary-main">
        <GradeBadge grade={analysis.grade} size="lg" />
        <div>
          <h1 className="repo-title">
            <a href={analysis.repo_url} target="_blank" rel="noreferrer noopener">{repoName(analysis.repo_url)}</a>
          </h1>
          <p className="muted small">
            <StatusPill status={analysis.status} />
            {analysis.overall !== null && <> · overall score <strong data-testid="overall">{analysis.overall}</strong>/100</>}
            {analysis.commit_sha && <> · commit <code>{analysis.commit_sha.slice(0, 7)}</code></>}
            {' '}· {formatDate(analysis.created_at)}
          </p>
        </div>
      </div>
      {!done && <div className="progress" role="progressbar" aria-label="Analysis in progress" />}
      {analysis.status === 'failed' && <p className="error" role="alert" data-testid="failure">{analysis.error}</p>}
      {analysis.status === 'partial' && (
        <p className="warning">Some analysers failed, so this result is partial. See the tool list below.</p>
      )}
    </section>
  )
}

function ScoreCards({ analysis }: { analysis: Analysis }) {
  return (
    <section className="scores" data-testid="scores">
      {CHARACTERISTICS.map(({ key, label, weight, note }) => {
        const score = analysis.scores![key]
        return (
          <article className="card score-card" key={key} data-testid={`score-${key}`}>
            <header>
              <h2>{label}</h2>
              <span className="muted small">weight {weight}</span>
            </header>
            <p className="score-value">{score.value === null ? 'Not measured' : score.value}</p>
            {score.value !== null && (
              <div className="bar" aria-hidden="true"><span style={{ width: `${score.value}%` }} /></div>
            )}
            {note && <p className="hint">{note}</p>}
            <dl className="details">
              {Object.entries(score.details)
                .filter(([k]) => k in DETAIL_LABELS)
                .map(([k, v]) => (
                  <div key={k}><dt>{DETAIL_LABELS[k]}</dt><dd>{formatDetail(k, v)}</dd></div>
                ))}
            </dl>
          </article>
        )
      })}
    </section>
  )
}

function ToolsCard({ analysis }: { analysis: Analysis }) {
  const stats = analysis.stats
  return (
    <article className="card">
      <h2>Analysers used</h2>
      <table className="compact" data-testid="tools">
        <thead><tr><th>Tool</th><th>Version</th><th>Result</th><th>Findings</th></tr></thead>
        <tbody>
          {(analysis.tools ?? []).map((t) => (
            <tr key={t.tool}>
              <td>{t.tool}</td><td>{t.version}</td>
              <td>{t.ok ? 'OK' : <span className="error-text" title={t.error ?? ''}>Failed</span>}</td>
              <td>{t.findings}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {stats && (
        <p className="muted small">
          {stats.loc} lines · {stats.python_files} Python and {stats.js_files} JS/TS files ·{' '}
          {stats.test_files} test files · {stats.skipped_files} skipped
        </p>
      )}
    </article>
  )
}

function HistoryCard({ analysis }: { analysis: Analysis }) {
  const [history, setHistory] = useState<Analysis[]>([])
  useEffect(() => {
    api.history(analysis.id).then(setHistory).catch(() => setHistory([]))
  }, [analysis.id])

  async function onDelete() {
    await api.deleteAnalysis(analysis.id)
    window.location.hash = '#/'
  }

  return (
    <article className="card">
      <h2>History</h2>
      {history.length < 2 ? (
        <p className="muted">Run the analysis again later to see a trend.</p>
      ) : (
        <ol className="history" data-testid="history">
          {history.map((h) => (
            <li key={h.id}>
              <a href={`#/analyses/${h.id}`}>
                <GradeBadge grade={h.grade} size="sm" /> {h.overall} · {formatDate(h.created_at)}
              </a>
            </li>
          ))}
        </ol>
      )}
      <button className="link-danger" onClick={onDelete} data-testid="delete">Delete this analysis</button>
    </article>
  )
}
