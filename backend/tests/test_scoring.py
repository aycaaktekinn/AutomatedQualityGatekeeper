"""FR-07: scores, grade bands and determinism (TC-07, TC-08)."""

import pytest

from app.analyzers.base import Characteristic
from app.scoring import grade_for, reliability_score, score, security_score


@pytest.mark.parametrize("value, grade", [
    (100, "A"), (90.0, "A"), (89.9, "B"), (75.0, "B"), (74.9, "C"),
    (60.0, "C"), (59.9, "D"), (40.0, "D"), (39.9, "E"), (0, "E"),
])
def test_grade_band_boundaries(value, grade):
    assert grade_for(value) == grade


CLEAN = {"functions": 10, "complexity_sum": 20, "high_complexity_functions": 0, "lint_issues": 0,
         "maintainability_index": 80, "security_high": 0, "security_medium": 0, "security_low": 0,
         "error_handling_issues": 0, "test_files": 5, "production_files": 10}


def test_clean_project_gets_a():
    card = score(CLEAN, kloc=1.0)
    assert card.grade == "A"
    assert card.overall == 100.0


def test_same_metrics_give_same_score():
    assert score(CLEAN, 2.0) == score(dict(CLEAN), 2.0)


def test_high_security_finding_caps_security_at_c():
    result = security_score(CLEAN | {"security_high": 1}, kloc=100.0)
    assert result.value == 74.0


def test_security_not_measured_without_python_analyser():
    metrics = {k: v for k, v in CLEAN.items() if not k.startswith("security")}
    card = score(metrics, 1.0)
    assert card.characteristics[Characteristic.SECURITY].value is None
    # Weights are re-normalised over the measured characteristics.
    assert card.overall == 100.0


def test_nothing_measured_gives_no_grade():
    card = score({}, 1.0)
    assert card.overall is None and card.grade is None


@pytest.mark.parametrize("test_files, production_files, penalty", [
    (0, 10, 30.0), (1, 20, 20.0), (2, 10, 10.0), (3, 10, 0.0),
])
def test_reliability_test_ratio_penalty(test_files, production_files, penalty):
    result = reliability_score({"error_handling_issues": 0, "test_files": test_files,
                                "production_files": production_files}, 1.0)
    assert result.details["test_penalty"] == penalty


def test_complexity_lowers_maintainability():
    complex_code = CLEAN | {"complexity_sum": 150, "high_complexity_functions": 5}
    assert score(complex_code, 1.0).characteristics[Characteristic.MAINTAINABILITY].value < 60


def test_scores_stay_in_range():
    awful = {"functions": 1, "complexity_sum": 500, "high_complexity_functions": 1, "lint_issues": 10_000,
             "maintainability_index": 0, "security_high": 100, "error_handling_issues": 1000,
             "test_files": 0, "production_files": 50}
    card = score(awful, 1.0)
    assert all(0 <= s.value <= 100 for s in card.characteristics.values())
    assert card.grade == "E"
