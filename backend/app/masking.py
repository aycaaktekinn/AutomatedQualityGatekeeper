"""Mask secret-like values before code snippets are stored or shown (SR-06, R9)."""

import re

_SECRET_ASSIGNMENT = re.compile(
    r"""(?ix)
    (?P<key>\b[\w.-]*(?:password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|private[_-]?key)[\w.-]*\b
        \s*[:=]\s*)
    (?P<quote>["']?)(?P<value>[^"'\s,;]{4,})(?P=quote)
    """
)
_KNOWN_TOKENS = re.compile(
    r"\b(?:ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|sk-[A-Za-z0-9]{20,}|xox[bap]-[A-Za-z0-9-]{10,})\b"
)

MASK = "****"


def mask_secrets(text: str) -> str:
    masked = _SECRET_ASSIGNMENT.sub(
        lambda m: f"{m.group('key')}{m.group('quote')}{MASK}{m.group('quote')}", text
    )
    return _KNOWN_TOKENS.sub(MASK, masked)
