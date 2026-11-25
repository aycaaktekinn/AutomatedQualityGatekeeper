import type { Analysis, CharacteristicName } from '../api'
import { GradeChip } from '../components'
import { gradeClass, gradeFor } from '../grades'

const CHARACTERISTICS: { key: CharacteristicName; label: string; weight: string; tools: string[]; note?: string }[] = [
  { key: 'maintainability', label: 'Maintainability', weight: '40%', tools: ['radon', 'lizard', 'ruff'] },
  { key: 'security', label: 'Security', weight: '35%', tools: ['bandit'] },
  { key: 'reliability', label: 'Reliability', weight: '25%', tools: ['reliability-rules'], note: 'Approximate: measured statically' },
]

const DETAIL_LABELS: Record<string, string> = {
  average_complexity: 'Average McCabe complexity',
  high_complexity_ratio: 'Functions over complexity 10',
  lint_issues_per_kloc: 'Lint issues per 1,000 lines',
  maintainability_index: 'Maintainability index',
  high: 'High severity findings',
  medium: 'Medium severity findings',
  low: 'Low severity findings',
  weighted_findings_per_kloc: 'Weighted findings per 1,000 lines',
  error_handling_issues_per_kloc: 'Error-handling issues per 1,000 lines',
  test_to_source_ratio: 'Test files per source file',
}

function formatDetail(key: string, value: number): string {
  if (key === 'high_complexity_ratio') return `${(value * 100).toFixed(1)}%`
  return Number.isInteger(value) ? String(value) : value.toFixed(2)
}

function toolLine(analysis: Analysis, names: string[]): string {
  const used = (analysis.tools ?? []).filter((t) => names.includes(t.tool))
  return used.map((t) => `${t.tool} ${t.version}`).join(' · ')
}

function ScoreCard({ analysis, spec }: { analysis: Analysis; spec: (typeof CHARACTERISTICS)[number] }) {
  const score = analysis.scores![spec.key]
  const grade = gradeFor(score.value)
  return (
    <article className="card score-card" data-testid={`score-${spec.key}`}>
      <div className="card-head">
        <div>
          <p className="label">ISO/IEC 25010</p>
          <h2 className="card-title">{spec.label}</h2>
        </div>
        <span className="chip mono">Weight {spec.weight}</span>
      </div>
      <div className="score-line">
        <p className="score-value">
          {score.value === null ? 'Not measured' : <>{score.value}<span className="muted small"> / 100</span></>}
        </p>
        <GradeChip grade={grade} />
      </div>
      {score.value !== null && (
        <div className={`bar ${gradeClass(grade)}`} aria-hidden="true"><span style={{ width: `${score.value}%` }} /></div>
      )}
      <dl className="details">
        {Object.entries(score.details).filter(([k]) => k in DETAIL_LABELS).map(([k, v]) => (
          <div key={k}><dt>{DETAIL_LABELS[k]}</dt><dd className="mono">{formatDetail(k, v)}</dd></div>
        ))}
      </dl>
      <p className="card-foot mono">{spec.note ?? toolLine(analysis, spec.tools) ?? ''}</p>
    </article>
  )
}

export function ScoreCards({ analysis }: { analysis: Analysis }) {
  if (!analysis.scores) return null
  return (
    <section className="grid-3" data-testid="scores">
      {CHARACTERISTICS.map((spec) => <ScoreCard key={spec.key} analysis={analysis} spec={spec} />)}
    </section>
  )
}
