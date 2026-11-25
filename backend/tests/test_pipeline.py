"""Snapshot limits (R1, R2), adapters on the planted-issues repo (NFR-10) and fault tolerance (NFR-04)."""

import os
from pathlib import Path

import pytest

from app import config
from app.analyzers import AdapterResult, default_analyzers
from app.cloner import FetchError, build_snapshot
from app.db import Database
from app.pipeline import analyse_snapshot, run_analysis
from app.repo_url import parse_repo_url

REF = parse_repo_url("https://github.com/example/sample")


def test_symlink_to_host_file_is_removed_and_not_read(sample_repo: Path):
    """TC-10: a symlink to /etc/passwd must never be followed."""
    os.symlink("/etc/passwd", sample_repo / "src" / "passwd.py")
    snapshot = build_snapshot(sample_repo)
    assert not (sample_repo / "src" / "passwd.py").exists()
    assert all("passwd" not in p.name for p in snapshot.python_files)
    assert snapshot.skipped_files == 1


def test_large_files_and_excluded_dirs_are_skipped(sample_repo: Path):
    (sample_repo / "src" / "huge.py").write_text("x = 1\n" * 200_000)
    snapshot = build_snapshot(sample_repo)
    names = {p.name for p in snapshot.source_files}
    assert "huge.py" not in names
    assert "index.js" not in names  # node_modules is excluded
    assert {"service.py", "clean.py", "app.js", "test_clean.py"} <= names


def test_file_count_limit(sample_repo: Path, monkeypatch):
    monkeypatch.setattr(config, "MAX_FILES", 3)
    with pytest.raises(FetchError, match="more than 3 files"):
        build_snapshot(sample_repo)


def test_planted_issues_are_found(sample_repo: Path):
    """NFR-10: every planted issue in the reference repository is reported."""
    results, summary = analyse_snapshot(build_snapshot(sample_repo), default_analyzers())
    found = {(f.tool, f.rule_id, f.file) for r in results for f in r.findings}
    expected = {
        ("radon", "high-complexity", "src/service.py"),
        ("bandit", "B602", "src/service.py"),           # subprocess with shell=True
        ("ruff", "F401", "src/service.py"),             # unused import os
        ("reliability-rules", "bare-except", "src/service.py"),
        ("reliability-rules", "swallowed-exception", "src/service.py"),
        ("reliability-rules", "empty-catch", "web/app.js"),
    }
    assert expected <= found
    assert summary["grade"] in {"A", "B", "C", "D", "E"}


def test_security_findings_in_test_files_are_ignored(sample_repo: Path):
    """Calibration fix: insecure code in tests must not lower the security score."""
    results, _ = analyse_snapshot(build_snapshot(sample_repo), default_analyzers())
    bandit = next(r for r in results if r.tool == "bandit")
    assert all(not f.file.startswith("tests/") for f in bandit.findings)
    assert bandit.metrics["ignored_test_findings"] >= 1


def test_secret_in_snippet_is_masked(sample_repo: Path):
    results, _ = analyse_snapshot(build_snapshot(sample_repo), default_analyzers())
    snippets = "\n".join(f.snippet for r in results for f in r.findings)
    assert "ghp_abcdefghijklmnopqrstuvwxyz" not in snippets


class CrashingAnalyzer:
    name = "crasher"

    def applies_to(self, repo):
        return True

    def run(self, repo):
        raise RuntimeError("tool exploded")


def test_crashing_analyser_gives_partial_result(sample_repo, copy_fetcher, tmp_path):
    """NFR-04: one failing tool does not crash the run."""
    db = Database(tmp_path / "db.sqlite3")
    analysis_id = db.create_analysis(REF.html_url, "test")
    run_analysis(db, analysis_id, REF, fetcher=copy_fetcher(sample_repo),
                 analyzers=[*default_analyzers(), CrashingAnalyzer()])
    analysis = db.get_analysis(analysis_id)
    assert analysis["status"] == "partial"
    crashed = [t for t in analysis["tools"] if t["tool"] == "crasher"]
    assert crashed[0]["ok"] is False and "exploded" in crashed[0]["error"]
    assert analysis["grade"] is not None


def test_repository_without_supported_code_fails_clearly(tmp_path, copy_fetcher):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "README.md").write_text("# only docs")
    db = Database(tmp_path / "db.sqlite3")
    analysis_id = db.create_analysis(REF.html_url, "test")
    run_analysis(db, analysis_id, REF, fetcher=copy_fetcher(docs))
    analysis = db.get_analysis(analysis_id)
    assert analysis["status"] == "failed"
    assert "Unsupported repository" in analysis["error"]


def test_clone_is_deleted_after_analysis(sample_repo, copy_fetcher, tmp_path):
    """SR-06: the analysed code is not kept on disk."""
    db = Database(tmp_path / "db.sqlite3")
    analysis_id = db.create_analysis(REF.html_url, "test")
    run_analysis(db, analysis_id, REF, fetcher=copy_fetcher(sample_repo))
    leftovers = list(config.WORK_DIR.glob("qg-*")) if config.WORK_DIR.exists() else []
    assert leftovers == []


def test_adapter_result_defaults():
    result = AdapterResult(tool="x", version="1", ok=True)
    assert result.findings == [] and result.metrics == {}
