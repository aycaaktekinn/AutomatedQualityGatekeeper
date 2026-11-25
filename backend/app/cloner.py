"""Secure fetching of an untrusted repository (FR-04, SR-01 - SR-03, R1 - R5).

Design rules:
* the analysed code is never executed, imported or installed;
* git is started with an argument list, never through a shell;
* symlinks are not created, so a link to a host file cannot be read;
* clone depth, size, file count, file size and time are all limited.
"""

from __future__ import annotations

import json
import os
import shutil

# subprocess is used only with fixed argument lists, never with a shell.
import subprocess  # nosec B404
import urllib.error
import urllib.request
from pathlib import Path

from . import config
from .analyzers.base import RepoSnapshot
from .repo_url import RepoRef

# Review fix (S607): call git by absolute path so PATH cannot be hijacked.
GIT = shutil.which("git") or "/usr/bin/git"


class FetchError(RuntimeError):
    """A user-facing reason why a repository could not be analysed."""


def check_repository_metadata(ref: RepoRef, timeout: float = 10.0) -> dict:
    """Ask the GitHub API whether the repository exists, is public and small enough.

    If the API cannot be reached (for example rate limits), the check is
    skipped and the size is enforced again after cloning.
    """
    url = f"https://api.github.com/repos/{ref.owner}/{ref.name}"
    request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json",
                                                   "User-Agent": "quality-gatekeeper"})
    try:
        # Scheme and host are fixed above; owner and name were validated by parse_repo_url.
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310  # nosec B310
            data = json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise FetchError("Repository not found or not public.") from exc
        return {}
    except (urllib.error.URLError, TimeoutError, ValueError):
        return {}
    if data.get("private"):
        raise FetchError("Private repositories are not supported.")
    size_mb = data.get("size", 0) / 1024
    if size_mb > config.MAX_REPO_SIZE_MB:
        raise FetchError(f"Repository is larger than {config.MAX_REPO_SIZE_MB} MB.")
    return data


def clone_repository(ref: RepoRef, destination: Path) -> str:
    """Shallow-clone the default branch into ``destination`` and return the commit SHA."""
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(destination.parent),
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_LFS_SKIP_SMUDGE": "1",
        "GIT_CONFIG_NOSYSTEM": "1",
    }
    # Proxy and certificate settings, plus the variables Windows needs to start processes.
    for proxy_var in ("HTTPS_PROXY", "https_proxy", "SSL_CERT_FILE", "GIT_SSL_CAINFO",
                      "SYSTEMROOT", "SystemRoot", "WINDIR", "TEMP", "TMP", "USERPROFILE", "APPDATA"):
        if proxy_var in os.environ:
            env[proxy_var] = os.environ[proxy_var]
    command = [
        GIT,
        "-c", "core.symlinks=false",
        "-c", "protocol.allow=never",
        "-c", "protocol.https.allow=always",
        "clone", "--depth", "1", "--single-branch", "--no-tags", "--quiet",
        "--", ref.clone_url, str(destination),
    ]
    try:
        subprocess.run(command, env=env, check=True, capture_output=True,  # nosec B603
                       timeout=config.CLONE_TIMEOUT_S)
    except subprocess.TimeoutExpired as exc:
        raise FetchError("Cloning took too long.") from exc
    except subprocess.CalledProcessError as exc:
        raise FetchError("Repository could not be cloned. Check that it exists and is public.") from exc

    sha = subprocess.run([GIT, "-C", str(destination), "rev-parse", "HEAD"],  # nosec B603
                         env=env, capture_output=True, text=True, timeout=30)
    shutil.rmtree(destination / ".git", ignore_errors=True)
    return sha.stdout.strip()


def _is_test_file(relative: Path) -> bool:
    name = relative.name.lower()
    parts = {p.lower() for p in relative.parts[:-1]}
    stem = relative.stem.lower()
    return (
        stem in {"test", "tests", "conftest"}
        or name.startswith("test_") or name.endswith("_test.py")
        or ".test." in name or ".spec." in name
        or bool(parts & {"tests", "test", "__tests__", "spec"})
    )


class _Budget:
    """Running totals for the repository-wide limits (R2, R3)."""

    def __init__(self) -> None:
        self.files = 0
        self.bytes = 0

    def charge(self, size: int) -> None:
        self.files += 1
        self.bytes += size
        if self.files > config.MAX_FILES:
            raise FetchError(f"Repository has more than {config.MAX_FILES} files.")
        if self.bytes > config.MAX_REPO_SIZE_MB * 1024 * 1024:
            raise FetchError(f"Repository is larger than {config.MAX_REPO_SIZE_MB} MB.")


def build_snapshot(root: Path) -> RepoSnapshot:
    """Walk the clone and collect the files analysers may read, enforcing limits."""
    snapshot = RepoSnapshot(root=root)
    budget = _Budget()
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = [d for d in dirnames if d not in config.EXCLUDED_DIRS]
        for filename in filenames:
            _visit_file(snapshot, budget, Path(dirpath) / filename)
    return snapshot


def _visit_file(snapshot: RepoSnapshot, budget: _Budget, path: Path) -> None:
    if path.is_symlink():  # TC-10: never follow links out of the repository
        path.unlink(missing_ok=True)
        snapshot.skipped_files += 1
        return
    size = path.stat().st_size
    budget.charge(size)
    suffix = path.suffix.lower()
    if suffix not in config.PYTHON_EXTENSIONS | config.JS_EXTENSIONS:
        return
    if size > config.MAX_FILE_SIZE_BYTES or path.name.endswith(".min.js"):
        snapshot.skipped_files += 1
        return
    _add_source_file(snapshot, path, suffix)


def _add_source_file(snapshot: RepoSnapshot, path: Path, suffix: str) -> None:
    if suffix in config.PYTHON_EXTENSIONS:
        snapshot.python_files.append(path)
    else:
        snapshot.js_files.append(path)
    if _is_test_file(path.relative_to(snapshot.root)):
        snapshot.test_files.append(path)
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return
    snapshot.loc += sum(1 for line in text.splitlines() if line.strip())
