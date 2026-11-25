"""REST endpoints. Review fix: moved out of create_app (McCabe 14 > 10)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request

from . import __version__, config
from .db import Database
from .pipeline import run_analysis
from .repo_url import InvalidRepoUrl, parse_repo_url
from .schemas import Analysis, AnalysisCreated, AnalysisRequest, ErrorOut, FindingOut

router = APIRouter(prefix="/api")

CharacteristicName = Literal["maintainability", "security", "reliability"]
SeverityName = Literal["low", "medium", "high"]


def _db(request: Request) -> Database:
    return request.app.state.db


def _get_or_404(database: Database, analysis_id: str) -> dict:
    analysis = database.get_analysis(analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    return analysis


def _enforce_limits(database: Database, client: str) -> None:
    """SR-05: per-client rate limit and a global queue cap."""
    since = (datetime.now(UTC) - timedelta(hours=1)).isoformat(timespec="seconds")
    if database.count_recent_for_client(client, since) >= config.MAX_ANALYSES_PER_HOUR:
        raise HTTPException(status_code=429,
                            detail=f"Limit of {config.MAX_ANALYSES_PER_HOUR} analyses per hour reached.")
    if database.count_active() >= config.MAX_QUEUED_JOBS:
        raise HTTPException(status_code=503, detail="The analysis queue is full. Try again in a few minutes.")


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "version": __version__}


@router.post("/analyses", status_code=202, response_model=AnalysisCreated,
             responses={400: {"model": ErrorOut}, 429: {"model": ErrorOut}, 503: {"model": ErrorOut}})
def create_analysis(body: AnalysisRequest, request: Request, background: BackgroundTasks) -> AnalysisCreated:
    try:
        ref = parse_repo_url(body.repo_url)
    except InvalidRepoUrl as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    database = _db(request)
    client = request.client.host if request.client else "unknown"
    _enforce_limits(database, client)
    analysis_id = database.create_analysis(ref.html_url, client)
    fetcher = request.app.state.fetcher
    kwargs = {"fetcher": fetcher} if fetcher else {}
    background.add_task(run_analysis, database, analysis_id, ref, **kwargs)
    return AnalysisCreated(id=analysis_id, status="queued")


@router.get("/analyses", response_model=list[Analysis])
def list_analyses(request: Request, limit: int = Query(20, ge=1, le=100)) -> list[dict]:
    return _db(request).list_analyses(limit)


@router.get("/analyses/{analysis_id}", response_model=Analysis, responses={404: {"model": ErrorOut}})
def get_analysis(analysis_id: str, request: Request) -> dict:
    return _get_or_404(_db(request), analysis_id)


@router.get("/analyses/{analysis_id}/history", response_model=list[Analysis])
def history(analysis_id: str, request: Request) -> list[dict]:
    database = _db(request)
    return database.history_for_repo(_get_or_404(database, analysis_id)["repo_url"])


@router.get("/analyses/{analysis_id}/findings", response_model=list[FindingOut])
def findings(analysis_id: str, request: Request,
             characteristic: CharacteristicName | None = None,
             severity: SeverityName | None = None,
             file: str | None = Query(None, max_length=200)) -> list[dict]:
    database = _db(request)
    _get_or_404(database, analysis_id)
    return database.list_findings(analysis_id, characteristic, severity, file)


@router.delete("/analyses/{analysis_id}", status_code=204)
def delete_analysis(analysis_id: str, request: Request) -> None:
    if not _db(request).delete_analysis(analysis_id):
        raise HTTPException(status_code=404, detail="Analysis not found.")
