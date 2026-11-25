import { useEffect, useState, type FormEvent } from 'react'
import { api, type Analysis } from '../api'
import { GradeBadge, StatusPill } from '../components'
import { formatDate, repoName } from '../format'

// Same rule as the backend (FR-03), checked early for a faster message (NFR-14).
const GITHUB_URL = /^https:\/\/github\.com\/[A-Za-z0-9-]+\/[A-Za-z0-9._-]+\/?$/

export function HomePage() {
  const [url, setUrl] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [recent, setRecent] = useState<Analysis[]>([])

  useEffect(() => {
    api.listAnalyses().then(setRecent).catch(() => setRecent([]))
  }, [])

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    const value = url.trim()
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

  return (
    <>
      <section className="hero">
        <h1>How healthy is your code?</h1>
        <p className="muted">
          Paste a public GitHub repository. We analyse it in a few minutes and grade its maintainability,
          security and reliability from A to E.
        </p>
        <form className="submit-form" onSubmit={onSubmit} noValidate>
          <label htmlFor="repo-url" className="sr-only">GitHub repository URL</label>
          <input
            id="repo-url"
            data-testid="repo-url"
            type="url"
            placeholder="https://github.com/owner/repository"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            aria-invalid={error ? 'true' : 'false'}
            aria-describedby={error ? 'url-error' : undefined}
            autoComplete="off"
          />
          <button type="submit" data-testid="analyse" disabled={submitting}>
            {submitting ? 'Starting…' : 'Analyse'}
          </button>
        </form>
        {error && <p id="url-error" className="error" role="alert" data-testid="error">{error}</p>}
        <p className="hint">Supported in v0.1: Python and JavaScript/TypeScript, public repositories up to 200 MB.</p>
      </section>

      <section className="card">
        <h2>Recent analyses</h2>
        {recent.length === 0 ? (
          <p className="muted">No analyses yet.</p>
        ) : (
          <ul className="recent" data-testid="recent-list">
            {recent.map((a) => (
              <li key={a.id}>
                <a href={`#/analyses/${a.id}`}>
                  <GradeBadge grade={a.grade} size="sm" />
                  <span className="recent-name">{repoName(a.repo_url)}</span>
                  <StatusPill status={a.status} />
                  <span className="muted small">{formatDate(a.created_at)}</span>
                </a>
              </li>
            ))}
          </ul>
        )}
      </section>
    </>
  )
}
