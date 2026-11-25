import { useEffect, useState } from 'react'
import { HomePage } from './pages/HomePage'
import { AnalysisPage } from './pages/AnalysisPage'

// Minimal hash routing: #/ and #/analyses/<id>. No router dependency needed in v0.1.
function useRoute(): string {
  const [hash, setHash] = useState(window.location.hash)
  useEffect(() => {
    const onChange = () => setHash(window.location.hash)
    window.addEventListener('hashchange', onChange)
    return () => window.removeEventListener('hashchange', onChange)
  }, [])
  return hash.replace(/^#/, '') || '/'
}

export default function App() {
  const route = useRoute()
  const match = route.match(/^\/analyses\/([0-9a-f-]{36})$/)
  return (
    <div className="layout">
      <header className="topbar">
        <a href="#/" className="brand">
          <span className="brand-mark" aria-hidden="true">QG</span>
          Quality Gatekeeper
        </a>
        <span className="tagline">ISO/IEC 25010 quality scores for GitHub repositories</span>
      </header>
      <main>{match ? <AnalysisPage id={match[1]} /> : <HomePage />}</main>
      <footer className="footer">v0.1 · analysed code is never executed</footer>
    </div>
  )
}
