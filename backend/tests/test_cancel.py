"""FR-14 cancellation and the whole-analysis time limit (TC-14)."""

import subprocess
import sys
import time

import pytest
from fastapi.testclient import TestClient

from app import config
from app.control import Cancelled, RunControl, TimedOut, request_cancel, run_process
from app.db import Database
from app.main import create_app
from app.pipeline import run_analysis
from app.repo_url import parse_repo_url

REF = parse_repo_url("https://github.com/example/sample")
SLEEP = [sys.executable, "-c", "import time; time.sleep(30)"]


def test_process_is_killed_when_cancelled():
    control = RunControl(timeout_s=600)
    control.start()
    started = time.monotonic()
    calls = {"n": 0}

    def checkpoint():
        calls["n"] += 1
        if calls["n"] == 2:
            control.cancel()
        control.checkpoint()

    with pytest.raises(Cancelled):
        run_process(SLEEP, timeout=60, checkpoint=checkpoint, poll_s=0.1)
    assert time.monotonic() - started < 5  # TC-14: stops within seconds, not 30 s


def test_process_timeout():
    with pytest.raises(subprocess.TimeoutExpired):
        run_process(SLEEP, timeout=0.3, poll_s=0.1)


def test_run_control_times_out():
    control = RunControl(timeout_s=0)
    control.start()
    time.sleep(0.01)
    with pytest.raises(TimedOut, match="took longer"):
        control.checkpoint()


def test_cancel_during_clone_stops_the_run(tmp_path, sample_repo, copy_fetcher):
    db = Database(tmp_path / "db.sqlite3")
    analysis_id = db.create_analysis(REF.html_url, "test")
    copy = copy_fetcher(sample_repo)

    def fetcher(ref, destination, checkpoint):
        sha = copy(ref, destination)
        db.mark_cancelled(analysis_id)     # the user presses Stop while cloning
        request_cancel(analysis_id)
        checkpoint()
        return sha

    run_analysis(db, analysis_id, REF, fetcher=fetcher)
    analysis = db.get_analysis(analysis_id)
    assert analysis["status"] == "cancelled"
    assert analysis["grade"] is None
    assert db.list_findings(analysis_id) == []


def test_cancelled_before_start_never_runs(tmp_path, sample_repo, copy_fetcher):
    db = Database(tmp_path / "db.sqlite3")
    analysis_id = db.create_analysis(REF.html_url, "test")
    db.mark_cancelled(analysis_id)
    run_analysis(db, analysis_id, REF, fetcher=copy_fetcher(sample_repo))
    assert db.get_analysis(analysis_id)["status"] == "cancelled"


def test_whole_analysis_time_limit(tmp_path, sample_repo, copy_fetcher, monkeypatch):
    monkeypatch.setattr(config, "ANALYSIS_TIMEOUT_S", 0)
    db = Database(tmp_path / "db.sqlite3")
    analysis_id = db.create_analysis(REF.html_url, "test")
    run_analysis(db, analysis_id, REF, fetcher=copy_fetcher(sample_repo))
    analysis = db.get_analysis(analysis_id)
    assert analysis["status"] == "failed"
    assert "took longer" in analysis["error"]


def test_stage_is_reported(tmp_path, sample_repo, copy_fetcher):
    db = Database(tmp_path / "db.sqlite3")
    analysis_id = db.create_analysis(REF.html_url, "test")
    run_analysis(db, analysis_id, REF, fetcher=copy_fetcher(sample_repo))
    assert db.get_analysis(analysis_id)["stage"] == "Done"


@pytest.fixture
def client(tmp_path, sample_repo, copy_fetcher):
    app = create_app(db=Database(tmp_path / "api.sqlite3"), fetcher=copy_fetcher(sample_repo))
    with TestClient(app) as test_client:
        yield test_client


def test_cancel_endpoint(client):
    db = client.app.state.db
    analysis_id = db.create_analysis(REF.html_url, "test")  # still queued
    response = client.post(f"/api/analyses/{analysis_id}/cancel")
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


def test_cancel_finished_analysis_is_conflict(client):
    analysis_id = client.post("/api/analyses", json={"repo_url": REF.html_url}).json()["id"]
    assert client.post(f"/api/analyses/{analysis_id}/cancel").status_code == 409


def test_cancel_unknown_analysis_is_404(client):
    assert client.post("/api/analyses/00000000-0000-0000-0000-000000000000/cancel").status_code == 404


def test_work_dir_is_outside_the_source_tree():
    """A clone inside backend/ would trigger uvicorn --reload in the middle of a run."""
    backend = config.STATIC_DIR.parent.resolve() if config.STATIC_DIR.is_absolute() else None
    assert backend is None or backend not in config.WORK_DIR.resolve().parents
