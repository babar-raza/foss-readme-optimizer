"""Cross-platform subprocess and pipe helpers for repository workers."""

from __future__ import annotations

import hashlib
import os
import signal
import subprocess
import threading
from pathlib import Path
from typing import IO


class _DrainResult:
    __slots__ = ("excerpt", "sha256", "byte_count")

    def __init__(self, excerpt: str, sha256: str, byte_count: int) -> None:
        self.excerpt = excerpt
        self.sha256 = sha256
        self.byte_count = byte_count


def _drain_pipe(pipe: IO[bytes] | None, max_bytes: int) -> _DrainResult:
    """Read a child pipe to EOF, keeping a bounded excerpt but hashing the full stream."""

    hasher = hashlib.sha256()
    buffer = bytearray()
    byte_count = 0
    if pipe is not None:
        while True:
            chunk = pipe.read(65536)
            if not chunk:
                break
            hasher.update(chunk)
            byte_count += len(chunk)
            if len(buffer) < max_bytes:
                buffer.extend(chunk[: max_bytes - len(buffer)])
    excerpt = bytes(buffer).decode("utf-8", errors="replace")
    return _DrainResult(excerpt=excerpt, sha256=hasher.hexdigest(), byte_count=byte_count)


def _start_drain_thread(
    pipe: IO[bytes] | None, max_bytes: int, result_holder: list[_DrainResult]
) -> threading.Thread:
    def _run() -> None:
        result_holder.append(_drain_pipe(pipe, max_bytes))

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    return thread


def _is_windows() -> bool:
    return os.name == "nt"


def _spawn_kwargs(environment: dict[str, str], cwd: Path) -> dict:
    # Deliberately a bare, untyped `dict` (not `dict[str, object]`): mypy resolves
    # platform-specific stubs (POSIX vs. Windows) from the machine it runs on, so exactly one of
    # `creationflags`/`start_new_session` is unknown on any given platform. An `Any`-valued dict
    # unpacked into `Popen(**kwargs)` keeps overload resolution permissive on both; a precisely
    # typed dict makes the overload match fail on whichever platform didn't type-check this file.
    kwargs: dict = {
        "cwd": str(cwd),
        "env": environment,
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
    }
    if _is_windows():
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
    else:
        kwargs["start_new_session"] = True
    return kwargs


def _send_graceful_signal(process: subprocess.Popen[bytes]) -> None:
    if _is_windows():
        try:
            process.send_signal(signal.CTRL_BREAK_EVENT)  # type: ignore[attr-defined]
        except (OSError, ValueError):
            pass
    else:
        try:
            os.killpg(process.pid, signal.SIGTERM)  # type: ignore[attr-defined]
        except ProcessLookupError:
            pass


def _send_forced_kill(process: subprocess.Popen[bytes]) -> None:
    if _is_windows():
        killer = subprocess.Popen(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            killer.wait(timeout=5)
        except subprocess.TimeoutExpired:
            killer.kill()
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)  # type: ignore[attr-defined]
        except ProcessLookupError:
            pass
    if process.poll() is None:
        try:
            process.kill()
        except OSError:
            pass


_EMPTY_DRAIN = _DrainResult("", hashlib.sha256(b"").hexdigest(), 0)
