"""Run subprocesses with bounded descendant-tree cleanup on cancellation."""

import os
import signal
import subprocess
from pathlib import Path


def _terminate_process_tree(process: subprocess.Popen[bytes]) -> None:
    """Terminate the exact process tree created by ``run_bounded``."""

    if os.name == "nt":
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
        process.kill()


def run_bounded(
    args: list[str],
    *,
    cwd: Path | None = None,
    timeout: float,
    input_bytes: bytes | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run without an interactive stdin and kill descendants on timeout."""

    popen_kwargs: dict = {
        "cwd": str(cwd) if cwd else None,
        "stdin": subprocess.PIPE if input_bytes is not None else subprocess.DEVNULL,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "env": env,
    }
    if os.name == "nt":
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        popen_kwargs["start_new_session"] = True

    process: subprocess.Popen[bytes] = subprocess.Popen(args, **popen_kwargs)
    try:
        stdout, stderr = process.communicate(input=input_bytes, timeout=timeout)
        return subprocess.CompletedProcess(
            args=args,
            returncode=process.returncode,
            stdout=stdout.decode("utf-8", errors="replace"),
            stderr=stderr.decode("utf-8", errors="replace"),
        )
    except subprocess.TimeoutExpired:
        _terminate_process_tree(process)
        try:
            stdout, stderr = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            if process.stdout is not None:
                process.stdout.close()
            if process.stderr is not None:
                process.stderr.close()
            stdout, stderr = b"", b""
        return subprocess.CompletedProcess(
            args=args,
            returncode=124,
            stdout=stdout.decode("utf-8", errors="replace"),
            stderr=stderr.decode("utf-8", errors="replace"),
        )
