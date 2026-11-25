import { useEffect, useState } from 'react'
import { Icon } from './components'
import { AnalysisPage } from './pages/AnalysisPage'
import { HomePage } from './pages/HomePage'
import { APP_VERSION, REPO_URL } from './constants'
import { useTheme } from './theme'

// Minimal hash routing: #/ and #/analyses/<id>. No router dependency needed (D8).
function useRoute(): string {
  const [hash, setHash] = useState(window.location.hash)
  useEffect(() => {
    const onChange = () => {
      setHash(window.location.hash)
      window.scrollTo(0, 0)
    }
    window.addEventListener('hashchange', onChange)
    return () => window.removeEventListener('hashchange', onChange)
  }, [])
  return hash.replace(/^#/, '') || '/'
}

function Header() {
  const [theme, toggleTheme] = useTheme()
  return (
    <header className="topbar">
      <div className="topbar-inner">
        <a href="#/" className="brand">
          <span className="brand-mark" aria-hidden="true">QG</span>
          <span className="brand-name">Quality Gatekeeper</span>
        </a>
        <span className="chip mono hide-sm">ISO/IEC 25010</span>
        <span className="chip mono hide-sm">{APP_VERSION}</span>
        <nav className="nav" aria-label="Main">
          <a href="#/" className="nav-primary">New analysis</a>
          <a href={`${REPO_URL}#readme`} target="_blank" rel="noreferrer noopener" className="hide-sm">Docs</a>
          <a href={REPO_URL} target="_blank" rel="noreferrer noopener" className="hide-sm">GitHub</a>
          <button className="icon-btn" onClick={toggleTheme} aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}>
            <Icon name={theme === 'dark' ? 'sun' : 'moon'} />
          </button>
        </nav>
      </div>
    </header>
  )
}

function Footer() {
  return (
    <footer className="footer">
      <div className="footer-inner">
        <p className="mono small">Analysed code is never executed. ISO/IEC 25010 based static code analysis.</p>
        <p className="small">
          Analysers: Radon, Lizard, Ruff, Bandit ·{' '}
          <a href={REPO_URL} target="_blank" rel="noreferrer noopener">Source on GitHub</a>
        </p>
      </div>
    </footer>
  )
}

export default function App() {
  const route = useRoute()
  const match = route.match(/^\/analyses\/([0-9a-f-]{36})$/)
  return (
    <>
      <Header />
      <main className="container">{match ? <AnalysisPage id={match[1]} /> : <HomePage />}</main>
      <Footer />
    </>
  )
}
