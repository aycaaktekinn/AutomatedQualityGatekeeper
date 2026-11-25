# Architecture and design decisions (v0.1)

Each decision lists the options we compared, what we chose and why. Decisions marked
**temporary** are simplifications for the first working version and have a planned follow-up.

## D1. One deployable service: FastAPI serves the API and the built React app

- **Options:** (a) separate frontend and backend containers behind a reverse proxy; (b) FastAPI serves the static React build.
- **Chosen:** (b).
- **Why:** one container, one port, no CORS configuration, and `docker compose up` is enough for the instructor (NFR-07). The frontend still builds and is linted on its own in CI, so it can be split later without code changes.

## D2. Background tasks instead of Redis + RQ — temporary

- **Options:** (a) Redis + RQ worker as planned in Phase 1; (b) FastAPI `BackgroundTasks` with a semaphore of 2 parallel analyses.
- **Chosen:** (b) for v0.1.
- **Why:** an analysis takes 1–30 seconds on typical repositories, so a separate queue service adds operational cost without benefit yet. A crash still cannot leave jobs stuck: on start-up, unfinished jobs are marked failed (NFR-15). **Follow-up:** move to Redis + RQ when analyses run in per-job containers.

## D3. SQLite instead of PostgreSQL — temporary

- **Options:** (a) PostgreSQL; (b) SQLite file on a Docker volume.
- **Chosen:** (b).
- **Why:** zero setup. All SQL lives in `app/db.py`, so switching to PostgreSQL touches one module (NFR-21).

## D4. Adapter pattern for analysers

- **Options:** (a) call each tool directly in the pipeline; (b) one adapter per tool behind a common `Analyzer` interface returning normalised `Finding` objects.
- **Chosen:** (b).
- **Why:** adding a tool means adding one adapter and one line in the registry; scoring and API do not change (NFR-17). Each adapter is tested on the planted-issues fixture. A crashing adapter becomes an error record and the result is marked *partial* (NFR-04).

## D5. Pure, deterministic scoring engine

- **Options:** (a) compute scores inside adapters; (b) a separate module of pure functions from metrics to scores.
- **Chosen:** (b).
- **Why:** the same metrics always give the same grade (FR-07, TC-08), boundaries are unit-tested (TC-07), and weights are in one place for calibration. Characteristics that were not measured are reported as *not measured* and the remaining weights are re-normalised, so a JavaScript-only project is not punished for having no Python security scanner.

## D6. Security by design for untrusted code (R1–R5)

- The analysed code is **never executed**: Radon and Lizard parse it, Python's `ast` reads it, Ruff and Bandit are static.
- URLs must match `https://github.com/<owner>/<repo>` exactly (SR-03); git is called by absolute path with an argument list, never through a shell.
- Clone is shallow, `core.symlinks=false`, only the `https` protocol is allowed, and remaining symlinks are deleted before analysis (TC-10).
- Limits: 200 MB, 50 000 files, 1 MB per source file, 120 s clone and 300 s per analyser.
- Ruff runs with `--isolated`, so configuration files inside the repository cannot change its behaviour.
- Clones are deleted after every run and secret-like values are masked in snippets (SR-06).
- The container runs as a non-root user with a read-only filesystem, no capabilities and clones in `tmpfs` (SR-01).
- **Temporary gap:** analyses run inside the application container, not in a fresh container per analysis. Because nothing is executed, the remaining risk is a parser bug in an analyser. **Follow-up:** one short-lived container per analysis (Phase 2, SR-01/SR-02).

## D7. Reliability measured statically and labelled approximate

Fault tolerance needs running code, which D6 forbids. We measure error-handling smells (bare `except`, silently swallowed exceptions, empty `catch`) and the test-to-source ratio, and the UI labels this score *approximate*.

## D8. Hash-based routing without a router library

Two pages do not justify a dependency; fewer dependencies means a smaller attack surface for `npm audit`.

## D9. Stitch design adopted, rebuilt in our own CSS (v0.2)

- **Options:** (a) paste the Stitch HTML with its Tailwind and Google Fonts CDN links; (b) rebuild the design with our own CSS and bundled fonts.
- **Chosen:** (b).
- **Why:** (a) would require loosening the Content-Security-Policy (R8) and would make the UI depend on third-party servers. Elements of the design with no real data behind them were left out on purpose.
