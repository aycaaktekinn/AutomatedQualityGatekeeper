import { Fragment, useEffect, useState } from 'react'
import { api, type Finding } from '../api'

// FR-08 / FR-09. Snippets are rendered as text (never as HTML), so code from an
// analysed repository cannot run in the browser (R8, TC-12).
export function FindingsTable({ analysisId }: { analysisId: string }) {
  const [characteristic, setCharacteristic] = useState('')
  const [severity, setSeverity] = useState('')
  const [file, setFile] = useState('')
  const [findings, setFindings] = useState<Finding[]>([])
  const [open, setOpen] = useState<number | null>(null)

  useEffect(() => {
    const timer = window.setTimeout(() => {
      api.findings(analysisId, { characteristic, severity, file }).then(setFindings).catch(() => setFindings([]))
    }, 200)
    return () => window.clearTimeout(timer)
  }, [analysisId, characteristic, severity, file])

  return (
    <section className="card">
      <div className="findings-head">
        <h2>Issues <span className="muted" data-testid="finding-count">({findings.length})</span></h2>
        <div className="filters">
          <label>
            Characteristic
            <select value={characteristic} onChange={(e) => setCharacteristic(e.target.value)} data-testid="filter-characteristic">
              <option value="">All</option>
              <option value="maintainability">Maintainability</option>
              <option value="security">Security</option>
              <option value="reliability">Reliability</option>
            </select>
          </label>
          <label>
            Severity
            <select value={severity} onChange={(e) => setSeverity(e.target.value)} data-testid="filter-severity">
              <option value="">All</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </label>
          <label>
            File
            <input value={file} onChange={(e) => setFile(e.target.value)} placeholder="path contains…" maxLength={200} />
          </label>
        </div>
      </div>
      {findings.length === 0 ? (
        <p className="muted">No issues match these filters.</p>
      ) : (
        <table className="findings" data-testid="findings">
          <thead>
            <tr><th>Severity</th><th>Characteristic</th><th>Location</th><th>Issue</th><th>Rule</th></tr>
          </thead>
          <tbody>
            {findings.map((f, i) => (
              <Fragment key={`${f.file}:${f.line}:${f.rule_id}:${i}`}>
                <tr className="finding-row" onClick={() => setOpen(open === i ? null : i)} aria-expanded={open === i}>
                  <td><span className={`sev sev-${f.severity}`}>{f.severity}</span></td>
                  <td>{f.characteristic}</td>
                  <td><code>{f.file}:{f.line}</code></td>
                  <td>{f.message}</td>
                  <td className="muted small">{f.tool} · {f.rule_id}</td>
                </tr>
                {open === i && f.snippet && (
                  <tr className="snippet-row"><td colSpan={5}><pre>{f.snippet}</pre></td></tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}
