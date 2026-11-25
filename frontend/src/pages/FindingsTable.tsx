import { Fragment, useEffect, useMemo, useState } from 'react'
import { api, type Finding, type SeverityName } from '../api'
import { Icon } from '../components'

// FR-08 / FR-09. All findings are loaded once (max 500) and filtered in the browser,
// so the counts on the tabs are always exact. Snippets are rendered as text, never
// as HTML, so code from an analysed repository cannot run in the browser (R8, TC-12).

const PAGE_SIZE = 10
const TABS = [
  { key: '', label: 'All' },
  { key: 'maintainability', label: 'Maintainability' },
  { key: 'security', label: 'Security' },
  { key: 'reliability', label: 'Reliability' },
]
const SEVERITIES: SeverityName[] = ['high', 'medium', 'low']
const SEVERITY_RANK: Record<SeverityName, number> = { high: 0, medium: 1, low: 2 }

type Sort = 'severity' | 'file'

interface Filters {
  characteristic: string
  severity: SeverityName | ''
  query: string
  sort: Sort
}

function matches(f: Finding, filters: Filters, ignore?: 'characteristic' | 'severity'): boolean {
  const q = filters.query.trim().toLowerCase()
  if (ignore !== 'characteristic' && filters.characteristic && f.characteristic !== filters.characteristic) return false
  if (ignore !== 'severity' && filters.severity && f.severity !== filters.severity) return false
  return !q || `${f.file} ${f.rule_id} ${f.tool} ${f.message}`.toLowerCase().includes(q)
}

function sortFindings(list: Finding[], sort: Sort): Finding[] {
  const byFile = (a: Finding, b: Finding) => a.file.localeCompare(b.file) || a.line - b.line
  const bySeverity = (a: Finding, b: Finding) => SEVERITY_RANK[a.severity] - SEVERITY_RANK[b.severity] || byFile(a, b)
  return [...list].sort(sort === 'file' ? byFile : bySeverity)
}

function Snippet({ finding }: { finding: Finding }) {
  return (
    <div className="snippet">
      <p className="snippet-head mono">{finding.file} · line {finding.line}</p>
      <pre className="code">
        {finding.snippet.split('\n').map((line) => {
          const number = Number(line.split('|')[0])
          return <span key={line} className={number === finding.line ? 'code-hit' : undefined}>{line}{'\n'}</span>
        })}
      </pre>
    </div>
  )
}

function FindingRow({ finding, open, onToggle }: { finding: Finding; open: boolean; onToggle: () => void }) {
  return (
    <Fragment>
      <tr className={`finding-row ${open ? 'open' : ''}`} onClick={onToggle}>
        <td><span className={`sev sev-${finding.severity}`}>{finding.severity}</span></td>
        <td>{finding.characteristic}</td>
        <td>
          {/* the real control for keyboard and screen-reader users; the row click is a shortcut */}
          <button className="link-btn" aria-expanded={open} onClick={(e) => { e.stopPropagation(); onToggle() }}>
            <code>{finding.file}:{finding.line}</code>
          </button>
        </td>
        <td>{finding.message}</td>
        <td className="mono muted small right">{finding.tool} · {finding.rule_id}</td>
      </tr>
      {open && finding.snippet && (
        <tr className="snippet-row"><td colSpan={5}><Snippet finding={finding} /></td></tr>
      )}
    </Fragment>
  )
}

function Toolbar({ all, filters, set }: { all: Finding[]; filters: Filters; set: (f: Partial<Filters>) => void }) {
  const tabCount = (key: string) => all.filter((f) => matches(f, { ...filters, characteristic: key }, undefined)).length
  const sevCount = (s: SeverityName) => all.filter((f) => matches(f, { ...filters, severity: s })).length
  return (
    <div className="toolbar">
      <div className="tabs" role="tablist" aria-label="Filter by characteristic">
        {TABS.map((t) => (
          <button key={t.label} role="tab" aria-selected={filters.characteristic === t.key}
            className={`tab ${filters.characteristic === t.key ? 'active' : ''}`}
            onClick={() => set({ characteristic: t.key })} data-testid={`tab-${t.key || 'all'}`}>
            {t.label} ({tabCount(t.key)})
          </button>
        ))}
      </div>
      <div className="toolbar-right">
        {SEVERITIES.map((s) => (
          <button key={s} className={`chip chip-button sev-chip sev-${s} ${filters.severity === s ? 'active' : ''}`}
            aria-pressed={filters.severity === s} onClick={() => set({ severity: filters.severity === s ? '' : s })}
            data-testid={`sev-${s}`}>
            {s[0].toUpperCase() + s.slice(1)} ({sevCount(s)})
          </button>
        ))}
        <label className="select-label">
          <span className="sr-only">Sort issues</span>
          <select value={filters.sort} onChange={(e) => set({ sort: e.target.value as Sort })}>
            <option value="severity">Severity: high to low</option>
            <option value="file">File path: A to Z</option>
          </select>
        </label>
      </div>
    </div>
  )
}

function Pager({ page, pages, total, shown, setPage }: { page: number; pages: number; total: number; shown: number; setPage: (p: number) => void }) {
  return (
    <div className="pager">
      <span className="muted small">Showing {shown} of {total} issues · page {page + 1} of {Math.max(pages, 1)}</span>
      <div>
        <button className="btn btn-ghost btn-sm" disabled={page === 0} onClick={() => setPage(page - 1)}>Previous</button>
        <button className="btn btn-ghost btn-sm" disabled={page + 1 >= pages} onClick={() => setPage(page + 1)}>Next</button>
      </div>
    </div>
  )
}

export function FindingsTable({ analysisId }: { analysisId: string }) {
  const [all, setAll] = useState<Finding[]>([])
  const [filters, setFilters] = useState<Filters>({ characteristic: '', severity: '', query: '', sort: 'severity' })
  const [page, setPage] = useState(0)
  const [open, setOpen] = useState<string | null>(null)

  useEffect(() => {
    api.findings(analysisId, {}).then(setAll).catch(() => setAll([]))
  }, [analysisId])

  const visible = useMemo(() => sortFindings(all.filter((f) => matches(f, filters)), filters.sort), [all, filters])
  const pages = Math.ceil(visible.length / PAGE_SIZE)
  const shown = visible.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)
  const set = (change: Partial<Filters>) => {
    setFilters((f) => ({ ...f, ...change }))
    setPage(0)
    setOpen(null)
  }

  return (
    <section className="card section">
      <div className="section-head">
        <div>
          <h2>Issues <span className="chip mono" data-testid="finding-count">{visible.length}</span></h2>
          <p className="muted small">Findings from every analyser, mapped to ISO/IEC 25010 characteristics.</p>
        </div>
        <label className="search">
          <Icon name="search" size={16} />
          <span className="sr-only">Filter by file, rule or message</span>
          <input className="mono" placeholder="Filter by file or rule…" value={filters.query}
            maxLength={200} onChange={(e) => set({ query: e.target.value })} data-testid="search" />
        </label>
      </div>
      <Toolbar all={all} filters={filters} set={set} />
      {visible.length === 0 ? (
        <p className="empty muted">No issues match these filters.</p>
      ) : (
        <div className="table-wrap">
          <table className="table findings" data-testid="findings">
            <thead><tr><th>Severity</th><th>Characteristic</th><th>Location</th><th>Message</th><th className="right">Rule (tool · id)</th></tr></thead>
            <tbody>
              {shown.map((f, i) => {
                const key = `${f.file}:${f.line}:${f.rule_id}:${page}:${i}`
                return <FindingRow key={key} finding={f} open={open === key} onToggle={() => setOpen(open === key ? null : key)} />
              })}
            </tbody>
          </table>
        </div>
      )}
      <Pager page={page} pages={pages} total={visible.length} shown={shown.length} setPage={setPage} />
    </section>
  )
}
