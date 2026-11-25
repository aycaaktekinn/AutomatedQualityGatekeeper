"""Static reliability indicators (ISO/IEC 25010 reliability, approximated).

Fault tolerance can only be fully measured by running code, which this tool
never does. We therefore measure error-handling smells that are known to hide
failures, plus whether the project has tests at all. The UI labels this score
as approximate (see Phase 2, Problems and Challenges).
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from .base import AdapterResult, Characteristic, Finding, RepoSnapshot, Severity
from .snippets import read_snippet

_EMPTY_JS_CATCH = re.compile(r"catch\s*(?:\([^)]*\))?\s*\{\s*\}")
_BROAD = {"Exception", "BaseException"}


def _is_silent(body: list[ast.stmt]) -> bool:
    """True when an except block only passes / continues / returns nothing."""
    for stmt in body:
        if isinstance(stmt, (ast.Pass, ast.Continue)):
            continue
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and stmt.value.value is Ellipsis:
            continue
        return False
    return True


def python_error_handling_issues(code: str) -> list[tuple[str, int, Severity, str]]:
    """Return (rule, line, severity, message) for error-handling smells in Python code."""
    issues: list[tuple[str, int, Severity, str]] = []
    tree = ast.parse(code)
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        silent = _is_silent(node.body)
        if node.type is None:
            issues.append(("bare-except", node.lineno, Severity.HIGH if silent else Severity.MEDIUM,
                           "Bare 'except:' also catches KeyboardInterrupt and SystemExit."))
        elif silent and isinstance(node.type, ast.Name) and node.type.id in _BROAD:
            issues.append(("swallowed-exception", node.lineno, Severity.MEDIUM,
                           f"'except {node.type.id}' silently ignores every error."))
        elif silent:
            issues.append(("empty-except", node.lineno, Severity.LOW,
                           "Exception is caught and ignored without handling or logging."))
    return issues


def js_error_handling_issues(code: str) -> list[tuple[str, int, Severity, str]]:
    return [("empty-catch", code.count("\n", 0, m.start()) + 1, Severity.MEDIUM,
             "Empty catch block hides errors.") for m in _EMPTY_JS_CATCH.finditer(code)]


class ReliabilityAnalyzer:
    name = "reliability-rules"
    version = "0.1.0"

    def applies_to(self, repo: RepoSnapshot) -> bool:
        return bool(repo.source_files)

    def run(self, repo: RepoSnapshot) -> AdapterResult:
        result = AdapterResult(tool=self.name, version=self.version, ok=True)
        for path in repo.source_files:
            repo.checkpoint()
            if path in repo.test_files:
                continue
            self._scan_file(repo, path, result)
        production_files = len(repo.source_files) - len(repo.test_files)
        result.metrics = {
            "error_handling_issues": len(result.findings),
            "test_files": len(repo.test_files),
            "production_files": max(production_files, 0),
        }
        return result

    def _scan_file(self, repo: RepoSnapshot, path: Path, result: AdapterResult) -> None:
        code = path.read_text(encoding="utf-8", errors="ignore")
        try:
            issues = python_error_handling_issues(code) if path.suffix == ".py" else js_error_handling_issues(code)
        except (SyntaxError, ValueError, RecursionError):
            return
        for rule, line, severity, message in issues:
            result.findings.append(Finding(
                tool=self.name, rule_id=rule, characteristic=Characteristic.RELIABILITY,
                severity=severity, file=repo.relative(path), line=line, message=message,
                snippet=read_snippet(path, line),
            ))
