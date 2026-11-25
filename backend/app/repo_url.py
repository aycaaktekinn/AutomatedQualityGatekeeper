"""Strict validation of GitHub repository URLs (FR-03, SR-03, R4, R5).

Only ``https://github.com/<owner>/<repo>`` is accepted. Everything else is
rejected before any network call or process is started, which closes the
door to SSRF (another host) and command injection (shell characters).
"""

import re
from dataclasses import dataclass

_OWNER = r"(?P<owner>[A-Za-z0-9](?:[A-Za-z0-9]|-(?=[A-Za-z0-9])){0,38})"
_REPO = r"(?P<repo>[A-Za-z0-9._-]{1,100})"
_PATTERN = re.compile(rf"^https://github\.com/{_OWNER}/{_REPO}/?$")


class InvalidRepoUrl(ValueError):
    """Raised with a user-facing message when a URL is not accepted (NFR-14)."""


@dataclass(frozen=True)
class RepoRef:
    owner: str
    name: str

    @property
    def clone_url(self) -> str:
        return f"https://github.com/{self.owner}/{self.name}.git"

    @property
    def html_url(self) -> str:
        return f"https://github.com/{self.owner}/{self.name}"


def parse_repo_url(raw: str) -> RepoRef:
    """Return the owner and repository name, or raise InvalidRepoUrl."""
    if not isinstance(raw, str):
        raise InvalidRepoUrl("Repository URL must be text.")
    url = raw.strip()
    if len(url) > 200:
        raise InvalidRepoUrl("Repository URL is too long.")
    if not url.startswith("https://github.com/"):
        raise InvalidRepoUrl(
            "Only public GitHub repositories are supported. "
            "Use the form https://github.com/<owner>/<repo>."
        )
    match = _PATTERN.match(url)
    if not match:
        raise InvalidRepoUrl(
            "This is not a valid GitHub repository URL. "
            "Use the form https://github.com/<owner>/<repo>."
        )
    name = match.group("repo")
    if name.endswith(".git"):
        name = name[: -len(".git")]
    if name in {"", ".", ".."}:
        raise InvalidRepoUrl("Repository name is not valid.")
    return RepoRef(owner=match.group("owner"), name=name)
