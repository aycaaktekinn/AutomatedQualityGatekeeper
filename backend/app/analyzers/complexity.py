"""McCabe complexity and maintainability index.

Python: Radon (library, parses with ``ast``; nothing is executed).
JavaScript / TypeScript: Lizard.
"""

from __future__ import annotations

from importlib.metadata import version

from .base import AdapterResult, Characteristic, Finding, RepoSnapshot, Severity
from .snippets import read_snippet

COMPLEXITY_LIMIT = 10  # NFR-05: McCabe <= 10 per function


def _complexity_finding(tool: str, repo: RepoSnapshot, path, name: str, line: int, cc: int) -> Finding:
    return Finding(
        tool=tool,
        rule_id="high-complexity",
        characteristic=Characteristic.MAINTAINABILITY,
        severity=Severity.HIGH if cc > 2 * COMPLEXITY_LIMIT else Severity.MEDIUM,
        file=repo.relative(path),
        line=line,
        message=f"Function '{name}' has McCabe complexity {cc} (limit {COMPLEXITY_LIMIT}).",
        snippet=read_snippet(path, line),
    )


class RadonAnalyzer:
    name = "radon"

    def applies_to(self, repo: RepoSnapshot) -> bool:
        return bool(repo.python_files)

    def run(self, repo: RepoSnapshot) -> AdapterResult:
        from radon.complexity import cc_visit
        from radon.metrics import mi_visit

        result = AdapterResult(tool=self.name, version=version("radon"), ok=True)
        functions = cc_sum = high = 0
        mi_values: list[float] = []
        failed_files = 0
        for path in repo.python_files:
            code = path.read_text(encoding="utf-8", errors="ignore")
            try:
                blocks = cc_visit(code)
                mi_values.append(mi_visit(code, multi=True))
            except (SyntaxError, ValueError, RecursionError):
                failed_files += 1
                continue
            for block in blocks:
                if block.letter == "C":  # class totals would double count methods
                    continue
                functions += 1
                cc_sum += block.complexity
                if block.complexity > COMPLEXITY_LIMIT:
                    high += 1
                    result.findings.append(
                        _complexity_finding(self.name, repo, path, block.name, block.lineno, block.complexity))
        result.metrics = {
            "functions": functions,
            "complexity_sum": cc_sum,
            "high_complexity_functions": high,
            "maintainability_index": sum(mi_values) / len(mi_values) if mi_values else 100.0,
            "unparsed_files": failed_files,
        }
        return result


class LizardAnalyzer:
    name = "lizard"

    def applies_to(self, repo: RepoSnapshot) -> bool:
        return bool(repo.js_files)

    def run(self, repo: RepoSnapshot) -> AdapterResult:
        import lizard

        result = AdapterResult(tool=self.name, version=version("lizard"), ok=True)
        functions = cc_sum = high = 0
        for path in repo.js_files:
            info = lizard.analyze_file(str(path))
            for func in info.function_list:
                functions += 1
                cc_sum += func.cyclomatic_complexity
                if func.cyclomatic_complexity > COMPLEXITY_LIMIT:
                    high += 1
                    result.findings.append(_complexity_finding(
                        self.name, repo, path, func.name, func.start_line, func.cyclomatic_complexity))
        result.metrics = {"functions": functions, "complexity_sum": cc_sum,
                          "high_complexity_functions": high}
        return result
