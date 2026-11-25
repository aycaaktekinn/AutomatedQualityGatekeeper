"""The analyser adapter contract (Phase 2, Interface contracts).

Every analyser is wrapped in an adapter that turns the tool's own output into
the normalised ``Finding`` schema. Adding a new tool means writing one new
adapter; scoring and API code do not change (NFR-17).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Protocol


class Characteristic(StrEnum):
    """ISO/IEC 25010 characteristics that the tool scores."""

    MAINTAINABILITY = "maintainability"
    SECURITY = "security"
    RELIABILITY = "reliability"


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class Finding:
    tool: str
    rule_id: str
    characteristic: Characteristic
    severity: Severity
    file: str
    line: int
    message: str
    snippet: str = ""

    def to_dict(self) -> dict:
        data = asdict(self)
        data["characteristic"] = self.characteristic.value
        data["severity"] = self.severity.value
        return data


@dataclass
class RepoSnapshot:
    """The files of a cloned repository that analysers are allowed to read."""

    root: Path
    python_files: list[Path] = field(default_factory=list)
    js_files: list[Path] = field(default_factory=list)
    test_files: list[Path] = field(default_factory=list)
    loc: int = 0
    skipped_files: int = 0

    @property
    def kloc(self) -> float:
        return max(self.loc / 1000, 1.0)

    @property
    def source_files(self) -> list[Path]:
        return self.python_files + self.js_files

    def relative(self, path: Path) -> str:
        return path.relative_to(self.root).as_posix()


@dataclass
class AdapterResult:
    """What every adapter returns. ``ok=False`` means the tool failed;
    the pipeline then marks the analysis as partial (NFR-04)."""

    tool: str
    version: str
    ok: bool
    findings: list[Finding] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)
    error: str | None = None
    skipped: bool = False


class Analyzer(Protocol):
    name: str

    def applies_to(self, repo: RepoSnapshot) -> bool: ...

    def run(self, repo: RepoSnapshot) -> AdapterResult: ...
