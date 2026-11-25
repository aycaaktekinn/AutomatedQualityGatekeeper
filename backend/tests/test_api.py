"""REST API behaviour, including security requirements SR-04, SR-05 and FR-13."""

import pytest
from fastapi.testclient import TestClient

from app.db import Database
from app.main import create_app

URL = "https://github.com/example/sample"


@pytest.fixture
def client(tmp_path, sample_repo, copy_fetcher):
    app = create_app(db=Database(tmp_path / "api.sqlite3"), fetcher=copy_fetcher(sample_repo))
    with TestClient(app) as test_client:
        yield test_client


def submit(client, url=URL):
    return client.post("/api/analyses", json={"repo_url": url})


def test_health(client):
    assert client.get("/api/health").json()["status"] == "ok"


def test_invalid_url_is_rejected_with_message(client):
    response = submit(client, "https://github.com/a/b;rm -rf /")
    assert response.status_code == 400
    assert "https://github.com/<owner>/<repo>" in response.json()["detail"]


def test_full_analysis_flow(client):
    created = submit(client)
    assert created.status_code == 202
    analysis_id = created.json()["id"]

    analysis = client.get(f"/api/analyses/{analysis_id}").json()
    assert analysis["status"] == "completed"
    assert analysis["grade"] in {"A", "B", "C", "D", "E"}
    assert set(analysis["scores"]) == {"maintainability", "security", "reliability"}
    assert {t["tool"] for t in analysis["tools"]} >= {"radon", "ruff", "bandit", "lizard"}  # FR-15
    assert "client" not in analysis


def test_findings_can_be_filtered(client):
    analysis_id = submit(client).json()["id"]
    security = client.get(f"/api/analyses/{analysis_id}/findings", params={"characteristic": "security"}).json()
    assert security and all(f["characteristic"] == "security" for f in security)
    high = client.get(f"/api/analyses/{analysis_id}/findings", params={"severity": "high"}).json()
    assert all(f["severity"] == "high" for f in high)
    by_file = client.get(f"/api/analyses/{analysis_id}/findings", params={"file": "app.js"}).json()
    assert by_file and all(f["file"].endswith("app.js") for f in by_file)


def test_invalid_filter_value_rejected(client):
    analysis_id = submit(client).json()["id"]
    assert client.get(f"/api/analyses/{analysis_id}/findings", params={"severity": "urgent"}).status_code == 422


def test_unknown_analysis_returns_404(client):
    """TC-11 (until accounts exist): unknown or foreign IDs reveal nothing."""
    response = client.get("/api/analyses/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


def test_delete_removes_analysis_and_findings(client):
    """FR-13."""
    analysis_id = submit(client).json()["id"]
    assert client.delete(f"/api/analyses/{analysis_id}").status_code == 204
    assert client.get(f"/api/analyses/{analysis_id}").status_code == 404
    assert client.get(f"/api/analyses/{analysis_id}/findings").status_code == 404


def test_rate_limit_sixth_request_rejected(client):
    """TC-13 / SR-05: at most 5 analyses per client per hour."""
    for _ in range(5):
        assert submit(client).status_code == 202
    response = submit(client)
    assert response.status_code == 429


def test_history_lists_previous_runs(client):
    first = submit(client).json()["id"]
    submit(client)
    history = client.get(f"/api/analyses/{first}/history").json()
    assert len(history) == 2


def test_security_headers_present(client):
    headers = client.get("/api/health").headers
    assert "default-src 'self'" in headers["content-security-policy"]
    assert headers["x-content-type-options"] == "nosniff"


def test_interrupted_jobs_marked_failed_on_startup(tmp_path, sample_repo, copy_fetcher):
    """NFR-15."""
    db = Database(tmp_path / "restart.sqlite3")
    stuck = db.create_analysis(URL, "test")
    db.update_analysis(stuck, status="running")
    with TestClient(create_app(db=db, fetcher=copy_fetcher(sample_repo))):
        pass
    assert db.get_analysis(stuck)["status"] == "failed"
