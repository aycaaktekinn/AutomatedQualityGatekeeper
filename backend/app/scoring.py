"""Turn analyser metrics into ISO/IEC 25010 scores and an A-E grade (FR-07).

Pure functions only: the same metrics always give the same score, so the
engine is deterministic (FR-07, TC-08) and easy to unit-test.
Weights and thresholds are the Phase 2 initial values and are documented in
the report; they are calibrated on reference repositories.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .analyzers.base import Characteristic

WEIGHTS: dict[Characteristic, float] = {
    Characteristic.MAINTAINABILITY: 0.40,
    Characteristic.SECURITY: 0.35,
    Characteristic.RELIABILITY: 0.25,
}

GRADE_BANDS: list[tuple[float, str]] = [(90, "A"), (75, "B"), (60, "C"), (40, "D"), (0, "E")]


@dataclass
class Score:
    value: float | None  # None = not measured
    details: dict[str, float] = field(default_factory=dict)


@dataclass
class ScoreCard:
    overall: float | None
    grade: str | None
    characteristics: dict[Characteristic, Score]


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def grade_for(score: float) -> str:
    for threshold, grade in GRADE_BANDS:
        if score >= threshold:
            return grade
    return "E"


def maintainability_score(m: dict[str, float], kloc: float) -> Score:
    functions = m.get("functions", 0)
    if functions == 0 and "lint_issues" not in m:
        return Score(None)
    avg_cc = m.get("complexity_sum", 0) / functions if functions else 1.0
    high_ratio = m.get("high_complexity_functions", 0) / functions if functions else 0.0
    lint_density = m.get("lint_issues", 0) / kloc
    mi = m.get("maintainability_index", 100.0)
    penalties = {
        "avg_complexity_penalty": min(25.0, max(0.0, avg_cc - 4) * 5),
        "high_complexity_penalty": min(30.0, high_ratio * 300),
        "lint_penalty": min(30.0, lint_density * 1.5),
        "maintainability_index_penalty": min(15.0, max(0.0, 65 - mi) * 0.5),
    }
    details = {"average_complexity": round(avg_cc, 2), "high_complexity_ratio": round(high_ratio, 4),
               "lint_issues_per_kloc": round(lint_density, 2), "maintainability_index": round(mi, 1)}
    return Score(round(clamp(100 - sum(penalties.values())), 1), details | penalties)


def security_score(m: dict[str, float], kloc: float) -> Score:
    if "security_high" not in m:
        return Score(None)
    weighted = m["security_high"] * 10 + m.get("security_medium", 0) * 3 + m.get("security_low", 0) * 0.5
    penalty = min(100.0, weighted / kloc * 4)
    value = clamp(100 - penalty)
    if m["security_high"] > 0:
        value = min(value, 74.0)  # any high-severity finding caps security at C (quality gate rule)
    return Score(round(value, 1), {"weighted_findings_per_kloc": round(weighted / kloc, 2),
                                   "high": m["security_high"], "medium": m.get("security_medium", 0),
                                   "low": m.get("security_low", 0)})


def reliability_score(m: dict[str, float], kloc: float) -> Score:
    if "error_handling_issues" not in m:
        return Score(None)
    density = m["error_handling_issues"] / kloc
    production = m.get("production_files", 0)
    ratio = m.get("test_files", 0) / production if production else 1.0
    if ratio == 0:
        test_penalty = 30.0
    elif ratio < 0.1:
        test_penalty = 20.0
    elif ratio < 0.3:
        test_penalty = 10.0
    else:
        test_penalty = 0.0
    error_penalty = min(60.0, density * 10)
    return Score(round(clamp(100 - error_penalty - test_penalty), 1),
                 {"error_handling_issues_per_kloc": round(density, 2), "test_to_source_ratio": round(ratio, 3),
                  "error_handling_penalty": error_penalty, "test_penalty": test_penalty})


def score(metrics: dict[str, float], kloc: float) -> ScoreCard:
    """Compute every characteristic, then a weighted overall score.

    Characteristics that were not measured are left out and the remaining
    weights are re-normalised, so a JavaScript-only project is not punished
    for having no Python security analyser.
    """
    characteristics = {
        Characteristic.MAINTAINABILITY: maintainability_score(metrics, kloc),
        Characteristic.SECURITY: security_score(metrics, kloc),
        Characteristic.RELIABILITY: reliability_score(metrics, kloc),
    }
    measured = {c: s.value for c, s in characteristics.items() if s.value is not None}
    if not measured:
        return ScoreCard(None, None, characteristics)
    total_weight = sum(WEIGHTS[c] for c in measured)
    overall = round(sum(WEIGHTS[c] * v for c, v in measured.items()) / total_weight, 1)
    return ScoreCard(overall, grade_for(overall), characteristics)
