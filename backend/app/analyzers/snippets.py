"""Read a short, masked code snippet around a finding (FR-09, SR-06)."""

from pathlib import Path

from ..masking import mask_secrets

MAX_SNIPPET_LINES = 5


def read_snippet(path: Path, line: int, context: int = 2) -> str:
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return ""
    if not lines or line < 1:
        return ""
    start = max(line - 1 - context, 0)
    end = min(start + MAX_SNIPPET_LINES, len(lines))
    numbered = [f"{n + 1:>5} | {lines[n][:200]}" for n in range(start, end)]
    return mask_secrets("\n".join(numbered))
