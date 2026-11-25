"""Adapters for analysers that run as separate processes (Ruff, Bandit).

Processes get an argument list (never a shell), a timeout, and ``--isolated``
or equivalent flags so that configuration inside the untrusted repository
cannot change what the tool does.
"""

from __future__ import annotations

import json
import subprocess  # nosec B404 - fixed argument lists only
from importlib.metadata import version
from pathlib import Path

from .. import config
from .base import AdapterResult, Characteristic, Finding, RepoSnapshot, Severity
from .snippets import read_snippet

_BANDIT_SEVERITY = {"LOW": Severity.LOW, "MEDIUM": Severity.MEDIUM, "HIGH": Severity.HIGH}


def _run_json(command: list[str]) -> object:
    completed = subprocess.run(command, capture_output=True, text=True,  # nosec B603
                               timeout=config.ANALYSER_TIMEOUT_S, check=False)
    if not completed.stdout.strip():
        raise RuntimeError(completed.stderr.strip()[:300] or "no output")
    return json.loads(completed.stdout)


class RuffAnalyzer:
    """Lint issues -> maintainability. Pyflakes errors (F) are medium, style is low."""

    name = "ruff"
    RULES = "E,F,W,B"

    def applies_to(self, repo: RepoSnapshot) -> bool:
        return bool(repo.python_files)

    def run(self, repo: RepoSnapshot) -> AdapterResult:
        output = _run_json([
            "ruff", "check", "--isolated", "--no-cache", "--exit-zero",
            "--output-format", "json", "--select", self.RULES, "--ignore", "E501",
            "--", str(repo.root),
        ])
        result = AdapterResult(tool=self.name, version=version("ruff"), ok=True)
        for item in output:  # type: ignore[union-attr]
            abs_path = Path(item["filename"])
            if not abs_path.is_absolute():
                abs_path = repo.root / abs_path
            line = item.get("location", {}).get("row", 1)
            code = item.get("code") or "syntax"
            result.findings.append(Finding(
                tool=self.name, rule_id=code,
                characteristic=Characteristic.MAINTAINABILITY,
                severity=Severity.MEDIUM if code.startswith("F") else Severity.LOW,
                file=repo.relative(abs_path), line=line,
                message=item.get("message", ""), snippet=read_snippet(abs_path, line),
            ))
        result.metrics = {"lint_issues": len(result.findings)}
        return result


class BanditAnalyzer:
    """Insecure Python patterns -> security.

    B101 (use of assert) is skipped: it fires on every pytest test and would
    drown the real findings. Findings inside test files are also ignored:
    calibration on psf/requests showed 127 of 129 security findings were
    test code (e.g. requests without timeout), which gave a misleading 0.
    """

    name = "bandit"

    def applies_to(self, repo: RepoSnapshot) -> bool:
        return bool(repo.python_files)

    def run(self, repo: RepoSnapshot) -> AdapterResult:
        output = _run_json([
            "bandit", "-r", str(repo.root), "-f", "json", "-q", "--exit-zero",
            "-s", "B101", "-x", ",".join(f"*/{d}/*" for d in sorted(config.EXCLUDED_DIRS)),
        ])
        result = AdapterResult(tool=self.name, version=version("bandit"), ok=True)
        counts = {severity: 0 for severity in Severity}
        test_files = {p.resolve() for p in repo.test_files}
        for item in output.get("results", []):  # type: ignore[union-attr]
            abs_path = Path(item["filename"])
            if abs_path.resolve() in test_files:
                continue
            severity = _BANDIT_SEVERITY.get(item.get("issue_severity", "LOW"), Severity.LOW)
            counts[severity] += 1
            result.findings.append(Finding(
                tool=self.name, rule_id=item.get("test_id", "bandit"),
                characteristic=Characteristic.SECURITY, severity=severity,
                file=repo.relative(abs_path), line=item.get("line_number", 1),
                message=item.get("issue_text", ""),
                snippet=read_snippet(abs_path, item.get("line_number", 1)),
            ))
        result.metrics = {f"security_{s.value}": float(n) for s, n in counts.items()}
        result.metrics["ignored_test_findings"] = float(len(output.get("results", [])) - sum(counts.values()))
        return result
