"""One analysis run: fetch -> snapshot -> analysers -> score -> store -> clean up."""

from __future__ import annotations

import logging
import shutil
import tempfile
import threading
from collections.abc import Callable
from pathlib import Path

from . import config
from .analyzers import AdapterResult, Analyzer, RepoSnapshot, default_analyzers
from .cloner import FetchError, build_snapshot, check_repository_metadata, clone_repository
from .control import Cancelled, Checkpoint, RunControl, StopAnalysis, TimedOut, register, unregister
from .db import Database, now_iso
from .repo_url import RepoRef
from .scoring import score

log = logging.getLogger("gatekeeper.pipeline")

Fetcher = Callable[[RepoRef, Path, Checkpoint], str]
StageCallback = Callable[[str], None]
_slots = threading.BoundedSemaphore(config.MAX_PARALLEL_ANALYSES)


def github_fetcher(ref: RepoRef, destination: Path, checkpoint: Checkpoint) -> str:
    check_repository_metadata(ref)
    checkpoint()
    return clone_repository(ref, destination, checkpoint)


def run_adapter(analyzer: Analyzer, repo: RepoSnapshot) -> AdapterResult:
    """Run one adapter; a crash becomes an error record, never an exception (NFR-04).

    Cancellation and time-outs are not crashes: they stop the whole run.
    """
    try:
        return analyzer.run(repo)
    except StopAnalysis:
        raise
    except Exception as exc:  # noqa: BLE001 - contract: adapters must never crash the run
        log.warning("analyser %s failed: %s", analyzer.name, exc)
        return AdapterResult(tool=analyzer.name, version="unknown", ok=False, error=str(exc)[:300])


def merge_metrics(results: list[AdapterResult]) -> dict[str, float]:
    """Sum metrics with the same name (Radon and Lizard both report complexity)."""
    merged: dict[str, float] = {}
    for result in results:
        if not result.ok:
            continue
        for key, value in result.metrics.items():
            if key == "maintainability_index":
                merged[key] = value
            else:
                merged[key] = merged.get(key, 0) + value
    return merged


def analyse_snapshot(repo: RepoSnapshot, analyzers: list[Analyzer],
                     on_stage: StageCallback | None = None) -> tuple[list[AdapterResult], dict]:
    results = []
    for analyzer in analyzers:
        if not analyzer.applies_to(repo):
            continue
        repo.checkpoint()
        if on_stage:
            on_stage(f"Running {analyzer.name}")
        results.append(run_adapter(analyzer, repo))
    metrics = merge_metrics(results)
    card = score(metrics, repo.kloc)
    summary = {
        "overall": card.overall,
        "grade": card.grade,
        "scores": {c.value: {"value": s.value, "details": s.details} for c, s in card.characteristics.items()},
        "metrics": metrics,
    }
    return results, summary


def run_analysis(db: Database, analysis_id: str, ref: RepoRef,
                 fetcher: Fetcher = github_fetcher, analyzers: list[Analyzer] | None = None) -> None:
    analyzers = analyzers if analyzers is not None else default_analyzers()
    control = register(analysis_id, config.ANALYSIS_TIMEOUT_S)
    try:
        current = db.get_analysis(analysis_id)
        if current is None or current["status"] == "cancelled":
            return  # Stop was pressed before the run even started
        with _slots:
            control.start()
            _run_with_workdir(db, analysis_id, ref, fetcher, analyzers, control)
    finally:
        unregister(analysis_id)


def _run_with_workdir(db: Database, analysis_id: str, ref: RepoRef, fetcher: Fetcher,
                      analyzers: list[Analyzer], control: RunControl) -> None:
    config.WORK_DIR.mkdir(parents=True, exist_ok=True)
    workdir = Path(tempfile.mkdtemp(prefix="qg-", dir=config.WORK_DIR))
    try:
        control.checkpoint()
        db.update_analysis(analysis_id, status="running", stage="Checking repository")
        _run(db, analysis_id, ref, fetcher, analyzers, control, workdir / "repo")
    except Cancelled as exc:
        db.update_analysis(analysis_id, status="cancelled", error=str(exc), finished_at=now_iso())
    except (FetchError, TimedOut) as exc:
        db.update_analysis(analysis_id, status="failed", error=str(exc), finished_at=now_iso())
    except Exception:  # noqa: BLE001 - last line of defence, details go to the log only
        log.exception("analysis %s crashed", analysis_id)
        db.update_analysis(analysis_id, status="failed", error="Internal error during analysis.",
                           finished_at=now_iso())
    finally:
        shutil.rmtree(workdir, ignore_errors=True)  # SR-06: never keep the clone


def _run(db: Database, analysis_id: str, ref: RepoRef, fetcher: Fetcher,
         analyzers: list[Analyzer], control: RunControl, destination: Path) -> None:
    def stage(text: str) -> None:
        db.update_analysis(analysis_id, stage=text)

    stage("Cloning repository")
    commit_sha = fetcher(ref, destination, control.checkpoint)
    stage("Reading files")
    repo = build_snapshot(destination, control.checkpoint)
    if not repo.source_files:
        raise FetchError("Unsupported repository: no Python or JavaScript/TypeScript files found.")
    results, summary = analyse_snapshot(repo, analyzers, on_stage=stage)
    control.checkpoint()  # a Stop pressed during scoring still wins
    findings = [f.to_dict() for r in results for f in r.findings]
    db.add_findings(analysis_id, findings)
    partial = any(not r.ok for r in results)
    db.update_analysis(
        analysis_id,
        status="partial" if partial else "completed",
        stage="Done",
        commit_sha=commit_sha or None,
        grade=summary["grade"],
        overall=summary["overall"],
        scores=summary["scores"],
        tools=[{"tool": r.tool, "version": r.version, "ok": r.ok, "error": r.error,
                "findings": len(r.findings)} for r in results],
        stats={"loc": repo.loc, "python_files": len(repo.python_files), "js_files": len(repo.js_files),
               "test_files": len(repo.test_files), "skipped_files": repo.skipped_files,
               "findings": len(findings)},
        finished_at=now_iso(),
    )
