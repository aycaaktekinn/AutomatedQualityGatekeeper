# Code review log

Findings from automated gates and reviews, and what we changed. Raw tool output for round 1 is in
`review-round1-ruff.txt`.

## Round 1 — first backend version (quality gate G2)

| # | Found by | Finding | Change | Requirement |
| --- | --- | --- | --- | --- |
| 1 | Ruff S607 | `git` was started by a partial path, so a manipulated `PATH` could run another program | Resolve `git` once with `shutil.which` and call it by absolute path | SR-03, R5 |
| 2 | Ruff S608 / Bandit B608 | `update_analysis` built its SQL from strings (keys were allow-listed, but the pattern is risky) | One static `UPDATE … COALESCE(?, column)` statement, no string building | NFR-03 |
| 3 | Ruff C901 | `create_app` had McCabe complexity 14 (limit 10) because every endpoint was nested in it | Endpoints moved to `app/api.py` as an `APIRouter`; factory is now 4 lines of logic | NFR-05 |
| 4 | xenon / Radon | `build_snapshot` had McCabe complexity 11 | Limits extracted into a `_Budget` class and per-file logic into `_visit_file` | NFR-05 |
| 5 | Ruff S310 | `urlopen` on a URL built from input | Reviewed: scheme and host are fixed and owner/name are validated first; suppression documented in code | R4 |
| 6 | Bandit warnings | `# nosec` comments with free text after them were parsed as test IDs | Explanations moved to the line above, `# nosec` keeps only the rule ID | — |

## Round 2 — frontend (E2E and dogfooding)

| # | Found by | Finding | Change | Requirement |
| --- | --- | --- | --- | --- |
| 7 | axe-core in Playwright | Status pill text `#1f8a4c` on white had contrast 4.37:1, below WCAG AA 4.5:1 | Darker green `#1a7a43` | NFR-13 |
| 8 | Playwright | Filter test read the table once, before the debounced filter applied (flaky test) | Test now waits until no non-matching row is left | Test quality |
| 9 | Dogfooding (our own tool) | `AnalysisPage` component had McCabe complexity 16 | Split into `Summary`, `ScoreCards`, `ToolsCard`, `HistoryCard` | NFR-05 |
| 10 | ESLint react-refresh | Helper functions exported from a component file break fast refresh | Helpers moved to `format.ts` | Maintainability |

## Round 3 — calibration on real repositories

| # | Found by | Finding | Change | Requirement |
| --- | --- | --- | --- | --- |
| 11 | Manual review of results (psf/requests) | Security score was 0: 127 of 129 Bandit findings were in test files (e.g. HTTP calls without timeout in tests) | Security findings in test files are ignored and counted separately; new test with a planted insecure test file | NFR-10, NFR-11 |

After the fix: psf/requests B (89.2), pallets/flask B (85.9), pallets/itsdangerous B (86.3).

## Gate status after all rounds

- Ruff: 0 issues · xenon: every function McCabe ≤ 10, average 2.6 · Bandit: 0 medium/high
- 70 backend tests, branch coverage 89% · 4 Playwright E2E tests incl. accessibility
- Dogfooding: our own repository scores **A (97.5)**
