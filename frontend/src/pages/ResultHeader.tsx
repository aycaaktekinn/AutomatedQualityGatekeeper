import { useState } from 'react'
import { api, type Analysis } from '../api'
import { GradeBadge, Icon, StatusPill } from '../components'
import { formatDate, languageOf, repoName } from '../format'

function ActionsMenu({ analysis }: { analysis: Analysis }) {
  const [open, setOpen] = useState(false)
  const [copied, setCopied] = useState(false)

  async function copyLink() {
    try {
      await navigator.clipboard.writeText(window.location.href)
      setCopied(true)
    } catch {
      setCopied(false)
    }
  }

  async function remove() {
    await api.deleteAnalysis(analysis.id)
    window.location.hash = '#/'
  }

  return (
    <div className="menu-wrap">
      <button className="icon-btn bordered" aria-haspopup="menu" aria-expanded={open} aria-label="More actions"
        onClick={() => setOpen(!open)} data-testid="more-actions">
        <Icon name="more" />
      </button>
      {open && (
        <div className="menu" role="menu">
          <button role="menuitem" onClick={copyLink}>{copied ? 'Link copied' : 'Copy link'}</button>
          <button role="menuitem" className="danger" onClick={remove} data-testid="delete">Delete analysis</button>
        </div>
      )}
    </div>
  )
}

function AnalyseAgain({ analysis }: { analysis: Analysis }) {
  const [error, setError] = useState<string | null>(null)
  async function again() {
    try {
      const created = await api.createAnalysis(analysis.repo_url)
      window.location.hash = `#/analyses/${created.id}`
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not start a new analysis.')
    }
  }
  return (
    <>
      <button className="btn btn-primary" onClick={again} data-testid="analyse-again">
        <Icon name="refresh" size={16} /> Analyse again
      </button>
      {error && <p className="form-error" role="alert">{error}</p>}
    </>
  )
}

function Meta({ analysis }: { analysis: Analysis }) {
  const language = languageOf(analysis.stats)
  return (
    <p className="muted small meta">
      {analysis.commit_sha && <span className="chip mono">commit {analysis.commit_sha.slice(0, 7)}</span>}
      {language && <span className="chip mono">{language}</span>}
      <span>Analysed {formatDate(analysis.created_at)}</span>
      {analysis.stats && <span>· {analysis.stats.loc.toLocaleString()} lines in {analysis.stats.python_files + analysis.stats.js_files} files</span>}
    </p>
  )
}

function StatusBanner({ analysis }: { analysis: Analysis }) {
  if (analysis.status === 'failed') {
    return <p className="banner banner-error" role="alert" data-testid="failure">{analysis.error}</p>
  }
  if (analysis.status === 'cancelled') {
    return <p className="banner" data-testid="cancelled">This analysis was stopped. Start it again whenever you are ready.</p>
  }
  if (analysis.status === 'partial') {
    return <p className="banner banner-warn">Some analysers failed, so this result is partial. See “Analysers used” below.</p>
  }
  return null
}

export function ResultHeader({ analysis }: { analysis: Analysis }) {
  return (
    <>
      <section className="card result-head">
        <GradeBadge grade={analysis.grade} size="xl" />
        <div className="grow">
          <h1 className="repo-title">
            <a href={analysis.repo_url} target="_blank" rel="noreferrer noopener">
              {repoName(analysis.repo_url)} <Icon name="external" size={16} />
            </a>
          </h1>
          <div className="title-row"><StatusPill status={analysis.status} /></div>
          <Meta analysis={analysis} />
          {analysis.overall !== null && (
            <p className="overall"><strong data-testid="overall">{analysis.overall}</strong><span className="muted"> / 100</span></p>
          )}
        </div>
        <div className="actions">
          <AnalyseAgain analysis={analysis} />
          <ActionsMenu analysis={analysis} />
        </div>
      </section>
      <StatusBanner analysis={analysis} />
    </>
  )
}
