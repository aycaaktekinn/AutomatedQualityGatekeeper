"""Quality gate G2 (dogfooding): the Gatekeeper grades its own source code.

Usage: python scripts/dogfood.py [--min-grade B]
Exits with 1 when our own grade is below the minimum.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.analyzers import default_analyzers  # noqa: E402
from app.cloner import build_snapshot  # noqa: E402
from app.pipeline import analyse_snapshot  # noqa: E402
from app.scoring import GRADE_BANDS  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
# Planted-issue fixtures exist to be bad; they are test data, not our code.
IGNORE = shutil.ignore_patterns("fixtures", "node_modules", "static", "data", ".git", "dist",
                                "test-results", "playwright-report")
ORDER = [grade for _, grade in GRADE_BANDS]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-grade", default="B", choices=ORDER)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / "self"
        shutil.copytree(REPO_ROOT, copy, ignore=IGNORE, symlinks=True)
        results, summary = analyse_snapshot(build_snapshot(copy), default_analyzers())
    scores = {name: s["value"] for name, s in summary["scores"].items()}
    print(json.dumps({"grade": summary["grade"], "overall": summary["overall"], "scores": scores}, indent=2))
    for result in results:
        for finding in result.findings:
            print(f"  [{finding.severity}] {finding.file}:{finding.line} {finding.rule_id} {finding.message}")
    if ORDER.index(summary["grade"]) > ORDER.index(args.min_grade):
        print(f"FAIL: own grade {summary['grade']} is below {args.min_grade}")
        return 1
    print(f"PASS: own grade {summary['grade']} (minimum {args.min_grade})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
