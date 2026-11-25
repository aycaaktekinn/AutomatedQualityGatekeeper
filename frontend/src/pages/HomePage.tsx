import { useEffect, useState, type FormEvent } from 'react'
import { api, type Analysis } from '../api'
import { GradeBadge, Icon, StatusPill } from '../components'
import { languageOf, relativeTime, repoName } from '../format'

// Same rule as the backend (FR-03), checked early for a faster message (NFR-14).
const GITHUB_URL = /^https:\/\/github\.com\/[A-Za-z0-9-]+\/[A-Za-z0-9._-]+\/?$/

const SAMPLES = ['pallets/flask', 'psf/requests', 'pallets/itsdangerous', 'sindresorhus/is-plain-obj']

const PILLARS = [
  {
    key: 'maintainability', title: 'Maintainability', weight: '40% weight',
    text: 'Cyclomatic complexity, maintainability index and lint rule violations per 1,000 lines.',
    tools: ['Radon: McCabe complexity and maintainability index (Python)', 'Lizard: McCabe complexity (JavaScript/TypeScript)', 'Ruff: pyflakes, pycodestyle and bugbear rules'],
  },
  {
    key: 'security', title: 'Security', weight: '35% weight',
    text: 'Insecure code patterns such as shell injection, weak hashing and hard-coded secrets.',
    tools: ['Bandit: Python security rules', 'Findings in test files are reported but not scored', 'Any high-severity finding caps the score at C'],
  },
  {
    key: 'reliability', title: 'Reliability', weight: '25% approx.',
    text: 'Error-handling smells that hide failures, and whether the project has tests.',
    tools: ['Bare and silently swallowed exceptions (Python)', 'Empty catch blocks (JavaScript/TypeScript)', 'Test files per source file'],
  },
]

function useSubmit() {
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  async function submit(value: string) {
    if (!GITHUB_URL.test(value)) {
      setError('Enter a public GitHub repository URL in the form https://github.com/<owner>/<repo>.')
      return
    }
    setSubmitting(true)
    setError(null)
    try {
      const created = await api.createAnalysis(value)
      window.location.hash = `#/analyses/${created.id}`
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong.')
    } finally {
      setSubmitting(false)
    }
  }
  return { error, submitting, submit }
}

function AnalyseForm() {
  const [url, setUrl] = useState('')
  const { error, submitting, submit } = useSubmit()

  function onSubmit(event: FormEvent) {
    event.preventDefault()
    submit(url.trim())
  }

  return (
    <>
      <form className="analyse-form" onSubmit={onSubmit} noValidate>
        <Icon name="branch" />
        <label htmlFor="repo-url" className="sr-only">GitHub repository URL</label>
        <input
          id="repo-url" data-testid="repo-url" type="url" className="mono"
          placeholder="https://github.com/owner/repository"
          value={url} onChange={(e) => setUrl(e.target.value)}
          aria-invalid={error ? 'true' : 'false'} aria-describedby={error ? 'url-error' : 'url-hint'}
          autoComplete="off"
        />
        {url && (
          <button type="button" className="icon-btn" onClick={() => setUrl('')} aria-label="Clear URL">
            <Icon name="close" />
          </button>
        )}
        <button type="submit" className="btn btn-primary" data-testid="analyse" disabled={submitting}>
          {submitting ? 'Starting…' : 'Analyse'} <Icon name="arrow" size={16} />
        </button>
      </form>
      {error && <p id="url-error" className="form-error" role="alert" data-testid="error">{error}</p>}
      <div className="form-meta">
        <span id="url-hint"><Icon name="info" size={14} /> Supported: Python and JavaScript/TypeScript, public repositories up to 200 MB.</span>
        <span className="mono">Engines: radon · lizard · ruff · bandit</span>
      </div>
      <div className="samples">
        <span className="label">Try a sample:</span>
        {SAMPLES.map((name) => (
          <button key={name} type="button" className="chip chip-button mono" onClick={() => setUrl(`https://github.com/${name}`)}>
            <span className="pill-dot" aria-hidden="true" />{name}
          </button>
        ))}
      </div>
    </>
  )
}

function Pillars() {
  return (
    <section className="section">
      <div className="section-head">
        <div>
          <h2>ISO/IEC 25010 quality model</h2>
          <p className="muted">Three characteristics, each scored 0–100 and combined into an A–E grade.</p>
        </div>
      </div>
      <div className="grid-3">
        {PILLARS.map((p) => (
          <article className="card pillar" key={p.key}>
            <header className="card-head">
              <h3>{p.title}</h3>
              <span className="chip mono">{p.weight}</span>
            </header>
            <p>{p.text}</p>
            <div className="inset">
              <p className="label">How it is measured</p>
              <ul>{p.tools.map((t) => <li key={t}>{t}</li>)}</ul>
            </div>
          </article>
        ))}
      </div>
    </section>
  )
}

function RecentRow({ analysis }: { analysis: Analysis }) {
  const done = ['completed', 'partial'].includes(analysis.status)
  return (
    <tr>
      <td><GradeBadge grade={analysis.grade} size="sm" /></td>
      <td><a className="mono" href={`#/analyses/${analysis.id}`}>{repoName(analysis.repo_url)}</a></td>
      <td>{languageOf(analysis.stats) ? <span className="chip mono">{languageOf(analysis.stats)}</span> : <span className="muted">–</span>}</td>
      <td><StatusPill status={analysis.status} /></td>
      <td className="mono muted num">{relativeTime(analysis.created_at)}</td>
      <td className="right">
        <a href={`#/analyses/${analysis.id}`} className="link-strong">{done ? 'View report' : 'Open'} ›</a>
      </td>
    </tr>
  )
}

function RecentAnalyses() {
  const [recent, setRecent] = useState<Analysis[] | null>(null)
  useEffect(() => {
    api.listAnalyses().then(setRecent).catch(() => setRecent([]))
  }, [])
  return (
    <section className="card section" id="recent">
      <div className="section-head">
        <h2>Recent analyses {recent && <span className="chip mono">{recent.length}</span>}</h2>
      </div>
      {recent && recent.length === 0 && <p className="muted">No analyses yet. Paste a repository above to start.</p>}
      {recent && recent.length > 0 && (
        <div className="table-wrap">
          <table className="table" data-testid="recent-list">
            <thead><tr><th>Grade</th><th>Repository</th><th>Language</th><th>Status</th><th>Analysed</th><th className="right">Report</th></tr></thead>
            <tbody>{recent.map((a) => <RecentRow key={a.id} analysis={a} />)}</tbody>
          </table>
        </div>
      )}
    </section>
  )
}

export function HomePage() {
  return (
    <>
      <section className="hero">
        <span className="chip mono"><Icon name="shield" size={14} /> Deterministic ISO/IEC 25010 quality audit</span>
        <h1>How healthy is your code?</h1>
        <p className="lead">
          Evaluate the maintainability, security and reliability of a public GitHub repository and get a grade from A to E.
        </p>
        <AnalyseForm />
      </section>
      <Pillars />
      <RecentAnalyses />
    </>
  )
}
