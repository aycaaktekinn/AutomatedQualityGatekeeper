import { useEffect, useState } from 'react'
import { api, type Analysis } from '../api'
import { GradeBadge, Icon, StatusPill } from '../components'
import { ANALYSIS_LIMIT_S } from '../constants'
import { elapsedSeconds, formatElapsed, repoName } from '../format'

// The real pipeline stages reported by the backend (pipeline.py).
const STEPS = [
  { title: 'Inspect repository', detail: 'Public, size and existence check' },
  { title: 'Shallow clone', detail: 'Depth 1, symlinks disabled' },
  { title: 'Catalogue files', detail: 'Python and JS/TS sources' },
  { title: 'Static analysers', detail: 'radon · lizard · ruff · bandit · rules' },
  { title: 'Synthesise grade', detail: 'ISO/IEC 25010 scoring' },
]

function stepIndex(analysis: Analysis): number {
  if (analysis.status === 'queued') return -1
  const stage = analysis.stage ?? ''
  if (stage.startsWith('Running')) return 3
  if (stage.startsWith('Reading')) return 2
  if (stage.startsWith('Cloning')) return 1
  return 0
}

function useNow(): number {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000)
    return () => window.clearInterval(timer)
  }, [])
  return now
}

function Stepper({ analysis }: { analysis: Analysis }) {
  const current = stepIndex(analysis)
  const tool = analysis.stage?.startsWith('Running') ? analysis.stage.replace('Running ', '') : null
  return (
    <section className="card section">
      <div className="section-head">
        <h2>Analysis pipeline</h2>
        <span className="chip mono">{current < 0 ? 'Waiting for a free slot' : `Stage ${current + 1} / ${STEPS.length}`}</span>
      </div>
      <ol className="stepper">
        {STEPS.map((step, i) => {
          const state = i < current ? 'done' : i === current ? 'active' : 'todo'
          return (
            <li key={step.title} className={`step step-${state}`} aria-current={state === 'active' ? 'step' : undefined}>
              <span className="step-mark" aria-hidden="true">{state === 'done' ? <Icon name="check" size={14} /> : i + 1}</span>
              <span className="step-title">{step.title}</span>
              <span className="step-detail">{state === 'active' && tool ? `Running ${tool}` : step.detail}</span>
            </li>
          )
        })}
      </ol>
      <p className="muted small" data-testid="stage">
        {current < 0 ? 'Waiting for a free slot' : analysis.stage ?? 'Starting'}
      </p>
    </section>
  )
}

function ElapsedCard({ analysis }: { analysis: Analysis }) {
  const now = useNow()
  const share = Math.min(100, (elapsedSeconds(analysis.created_at, now) / ANALYSIS_LIMIT_S) * 100)
  return (
    <article className="card">
      <div className="card-head">
        <p className="label">Elapsed analysis time</p>
        <Icon name="timer" />
      </div>
      <p className="elapsed mono"><span data-testid="elapsed">{formatElapsed(analysis.created_at, now)}</span> <span className="muted small">/ 10:00 max</span></p>
      <div className="bar"><span style={{ width: `${share}%` }} /></div>
      <p className="inset small"><Icon name="info" size={14} /> Analyses stop automatically after <strong>10 minutes</strong>.</p>
    </article>
  )
}

function StopControl({ analysis, onChange }: { analysis: Analysis; onChange: () => void }) {
  const [confirming, setConfirming] = useState(false)
  const [stopping, setStopping] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function stop() {
    setStopping(true)
    setError(null)
    try {
      await api.cancelAnalysis(analysis.id)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not stop the analysis.')
    } finally {
      setStopping(false)
      setConfirming(false)
      onChange()
    }
  }

  return (
    <article className="card">
      <h2 className="card-title">Analysis control</h2>
      {confirming ? (
        <div className="confirm" role="alertdialog" aria-labelledby="stop-q">
          <p id="stop-q"><strong>Stop this analysis?</strong> Results so far will be discarded.</p>
          <div className="row-end">
            <button className="btn btn-ghost" onClick={() => setConfirming(false)}>Keep analysing</button>
            <button className="btn btn-danger-solid" onClick={stop} disabled={stopping} data-testid="confirm-stop">
              <Icon name="stop" size={16} /> {stopping ? 'Stopping…' : 'Confirm stop'}
            </button>
          </div>
        </div>
      ) : (
        <button className="btn btn-danger btn-block" onClick={() => setConfirming(true)} data-testid="stop">
          <Icon name="stop" size={16} /> Stop analysis
        </button>
      )}
      {error && <p className="form-error" role="alert">{error}</p>}
    </article>
  )
}

export function ProgressView({ analysis, onChange }: { analysis: Analysis; onChange: () => void }) {
  return (
    <>
      <section className="card result-head" aria-live="polite">
        <GradeBadge grade={null} size="md" />
        <div className="grow">
          <h1 className="repo-title">{repoName(analysis.repo_url)}</h1>
          <StatusPill status={analysis.status} />
        </div>
        <span className="chip mono">Evaluating quality</span>
      </section>
      <p className="banner banner-info">
        <Icon name="shield" size={16} />
        <span><strong>Deterministic static analysis:</strong> the repository's code is parsed, never executed, and the clone is deleted afterwards.</span>
      </p>
      <Stepper analysis={analysis} />
      <section className="grid-2">
        <ElapsedCard analysis={analysis} />
        <StopControl analysis={analysis} onChange={onChange} />
      </section>
    </>
  )
}
