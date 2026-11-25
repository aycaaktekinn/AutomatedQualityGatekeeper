import { useEffect, useState } from 'react'
import { api, FINAL_STATUSES, type Analysis } from '../api'
import { repoParts } from '../format'
import { FindingsTable } from './FindingsTable'
import { ProgressView } from './ProgressView'
import { ResultHeader } from './ResultHeader'
import { ScoreCards } from './ScoreCards'
import { HistoryCard, ToolsCard } from './SidePanels'

const POLL_MS = 3000 // FR-06: status refreshes at least every 5 seconds

function useAnalysis(id: string) {
  const [analysis, setAnalysis] = useState<Analysis | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [reload, setReload] = useState(0)
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
  }, [id, reload])
  return { analysis, error, refresh: () => setReload((n) => n + 1) }
}

function Breadcrumb({ analysis }: { analysis: Analysis }) {
  const { owner, name } = repoParts(analysis.repo_url)
  return (
    <nav className="breadcrumb mono" aria-label="Breadcrumb">
      <a href="#/">Analyses</a> / <span>{owner}</span> / <strong>{name}</strong>
    </nav>
  )
}

function Results({ analysis }: { analysis: Analysis }) {
  const hasResults = analysis.status === 'completed' || analysis.status === 'partial'
  return (
    <>
      <ResultHeader analysis={analysis} />
      {hasResults && <ScoreCards analysis={analysis} />}
      {hasResults && <FindingsTable analysisId={analysis.id} />}
      <section className="grid-2">
        {hasResults && <ToolsCard analysis={analysis} />}
        <HistoryCard analysis={analysis} />
      </section>
    </>
  )
}

export function AnalysisPage({ id }: { id: string }) {
  const { analysis, error, refresh } = useAnalysis(id)
  if (error) return <p className="banner banner-error" role="alert">{error}</p>
  if (!analysis) return <p className="muted loading">Loading…</p>
  const done = FINAL_STATUSES.includes(analysis.status)
  return (
    <>
      <Breadcrumb analysis={analysis} />
      {done ? <Results analysis={analysis} /> : <ProgressView analysis={analysis} onChange={refresh} />}
    </>
  )
}
