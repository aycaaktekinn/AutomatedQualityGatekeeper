"""Stopping a running analysis: user cancellation (FR-14) and a hard time limit (SR-01).

Each run gets a ``RunControl``. Long steps call ``checkpoint()`` regularly; it
raises ``Cancelled`` or ``TimedOut`` so the pipeline can stop cleanly. External
processes are polled and killed when the checkpoint fires, so a stuck ``git``
or analyser cannot keep running after the user pressed Stop.
"""

from __future__ import annotations

import subprocess  # nosec B404
import tempfile
import threading
import time
from collections.abc import Callable

Checkpoint = Callable[[], None]


class StopAnalysis(Exception):  # noqa: N818 - control-flow signal, not an error type
    """Base class for reasons to stop a run early."""


class Cancelled(StopAnalysis):
    pass


class TimedOut(StopAnalysis):
    pass


def no_checkpoint() -> None:
    """Default checkpoint used when a step runs outside a pipeline (e.g. in tests)."""


class RunControl:
    def __init__(self, timeout_s: float) -> None:
        self._event = threading.Event()
        self._timeout_s = timeout_s
        self._deadline: float | None = None

    def start(self) -> None:
        """Start the clock once the run has a slot (time in the queue does not count)."""
        self._deadline = time.monotonic() + self._timeout_s

    def cancel(self) -> None:
        self._event.set()

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()

    def checkpoint(self) -> None:
        if self._event.is_set():
            raise Cancelled("Cancelled by the user.")
        if self._deadline is not None and time.monotonic() > self._deadline:
            raise TimedOut(f"Analysis stopped: it took longer than {int(self._timeout_s // 60)} minutes.")


_active: dict[str, RunControl] = {}
_lock = threading.Lock()


def register(analysis_id: str, timeout_s: float) -> RunControl:
    with _lock:
        control = _active.setdefault(analysis_id, RunControl(timeout_s))
    return control


def unregister(analysis_id: str) -> None:
    with _lock:
        _active.pop(analysis_id, None)


def request_cancel(analysis_id: str) -> None:
    """Signal a queued or running analysis to stop. Unknown IDs are ignored."""
    with _lock:
        control = _active.get(analysis_id)
    if control:
        control.cancel()


def run_process(command: list[str], *, timeout: float, checkpoint: Checkpoint = no_checkpoint,
                env: dict[str, str] | None = None, poll_s: float = 0.25) -> subprocess.CompletedProcess:
    """Run a command (argument list, no shell) that can be stopped by ``checkpoint``.

    Output goes to temporary files instead of pipes, so a large report cannot
    fill a pipe buffer and block the process.
    """
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        process = subprocess.Popen(command, stdout=out, stderr=err, env=env)  # nosec B603
        started = time.monotonic()
        while True:
            try:
                process.wait(timeout=poll_s)
                break
            except subprocess.TimeoutExpired:
                _stop_if_needed(process, command, started, timeout, checkpoint)
        out.seek(0)
        err.seek(0)
        return subprocess.CompletedProcess(command, process.returncode,
                                           out.read().decode("utf-8", errors="replace"),
                                           err.read().decode("utf-8", errors="replace"))


def _stop_if_needed(process: subprocess.Popen, command: list[str], started: float, timeout: float,
                    checkpoint: Checkpoint) -> None:
    try:
        checkpoint()
    except StopAnalysis:
        _kill(process)
        raise
    if time.monotonic() - started > timeout:
        _kill(process)
        raise subprocess.TimeoutExpired(command, timeout)


def _kill(process: subprocess.Popen) -> None:
    process.kill()
    process.wait(timeout=10)
