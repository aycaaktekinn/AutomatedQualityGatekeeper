"""Registry of analyser adapters. Add a new tool here and nowhere else (NFR-17)."""

from .base import AdapterResult, Analyzer, Characteristic, Finding, RepoSnapshot, Severity
from .complexity import LizardAnalyzer, RadonAnalyzer
from .external import BanditAnalyzer, RuffAnalyzer
from .reliability import ReliabilityAnalyzer


def default_analyzers() -> list[Analyzer]:
    return [RadonAnalyzer(), LizardAnalyzer(), RuffAnalyzer(), BanditAnalyzer(), ReliabilityAnalyzer()]


__all__ = [
    "AdapterResult", "Analyzer", "Characteristic", "Finding", "RepoSnapshot", "Severity",
    "default_analyzers",
]
