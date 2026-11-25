# Automated Quality Gatekeeper

A lightweight, SonarQube-like web tool. Paste a public GitHub repository URL and get an
**A–E quality grade** based on ISO/IEC 25010: maintainability, security and reliability.

Software Quality Standards — Group Project · Ayça, Tuğçe, Sidar, Celal, Mert, Kemal

## Run it

**With Docker (recommended):**

```bash
docker compose up --build
# open http://localhost:8000
```

**Without Docker (development):**

```bash
# backend
cd backend
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000

# frontend (second terminal, hot reload on http://localhost:5173)
cd frontend
npm install
npm run dev
```

API documentation (OpenAPI): http://localhost:8000/docs

## Test it

```bash
cd backend
pytest --cov                     # unit, integration and contract tests, coverage gate 70%
ruff check .                     # lint
xenon --max-absolute B app       # McCabe complexity <= 10 per function
bandit -r app -ll                # security scan
python scripts/dogfood.py        # the tool grades its own code; fails below B

cd ../frontend
npx playwright install chromium
npx playwright test              # E2E + accessibility; needs the app running on :8000
```

## What it measures (v0.1)

| Characteristic | Weight | Python | JavaScript / TypeScript |
| --- | --- | --- | --- |
| Maintainability | 40% | Radon (McCabe, maintainability index), Ruff | Lizard (McCabe) |
| Security | 35% | Bandit | not measured yet |
| Reliability (approximate) | 25% | error-handling rules, test ratio | empty `catch`, test ratio |

Grades: A ≥ 90 · B 75–89 · C 60–74 · D 40–59 · E < 40.

## Project structure

```
backend/app/
  api.py            REST endpoints
  repo_url.py       strict GitHub URL validation (SSRF / injection protection)
  cloner.py         secure shallow clone and file limits
  analyzers/        one adapter per tool, common Finding schema
  scoring.py        pure, deterministic scoring engine
  pipeline.py       clone -> analyse -> score -> store -> delete clone
  db.py             SQLite storage
backend/tests/      69 tests, incl. a planted-issues reference repository
frontend/src/       React + TypeScript UI
frontend/e2e/       Playwright end-to-end and accessibility tests
docs/               design decisions and code review log
```

## Quality gates

| Gate | Where | Checks |
| --- | --- | --- |
| G1 | `pre-commit` on each laptop | Ruff, gitleaks, large files |
| G2 | GitHub Actions on every PR | Ruff, McCabe ≤ 10, Bandit, pip-audit, npm audit, tests + 70% coverage, own grade ≥ B, E2E + accessibility, gitleaks |
| G3 / G4 | end of sprint / before release | see Phase 2 test plan |

See [docs/decisions.md](docs/decisions.md) and [docs/code-review-log.md](docs/code-review-log.md).

## AI usage

Parts of this project were drafted with AI assistance (Claude by Anthropic) and reviewed by the team.
Every use is recorded in the DIR declaration in the project report.
