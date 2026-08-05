"""Run the complete non-live pytest inventory with bounded, evidenced parallelism."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

from readme_agent.evidence.writer import write_redacted_json

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RECEIPT = REPO_ROOT / "runs" / "verification" / "pytest-full-latest.json"


def _selected_nodes(output: str) -> list[str]:
    return sorted(
        line.strip().replace("\\", "/")
        for line in output.splitlines()
        if line.startswith(("tests/", "tests\\"))
    )


def _sha256_text(lines: list[str]) -> str:
    return hashlib.sha256(("\n".join(sorted(lines)) + "\n").encode()).hexdigest()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _git_bytes(*args: str) -> bytes:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        check=True,
    )
    return result.stdout


def _tree_fingerprint() -> str:
    """Bind tracked, staged, and untracked bytes without mutating the index."""

    status = _git_bytes("status", "--porcelain=v1", "-z", "--untracked-files=all")
    unstaged = _git_bytes("diff", "--binary", "--no-ext-diff")
    staged = _git_bytes("diff", "--cached", "--binary", "--no-ext-diff")
    untracked = sorted(
        path
        for path in _git_bytes("ls-files", "--others", "--exclude-standard", "-z").split(b"\0")
        if path
    )
    digest = hashlib.sha256()
    for label, value in ((b"status", status), (b"unstaged", unstaged), (b"staged", staged)):
        digest.update(label + b"\0" + len(value).to_bytes(8, "big") + value)
    for encoded_path in untracked:
        relative = encoded_path.decode("utf-8", errors="surrogateescape")
        path = REPO_ROOT / relative
        value = path.read_bytes() if path.is_file() else b""
        digest.update(b"untracked\0" + encoded_path + b"\0" + hashlib.sha256(value).digest())
    return digest.hexdigest()


_OUTCOME_PATTERN = re.compile(
    r"(?P<count>\d+) (?P<kind>passed|failed|skipped|xfailed|xpassed|errors?|deselected)"
)


def _outcome_counts(output: str) -> dict[str, int]:
    counts = {
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "xfailed": 0,
        "xpassed": 0,
        "errors": 0,
        "deselected": 0,
    }
    for match in _OUTCOME_PATTERN.finditer(output):
        kind = match.group("kind")
        key = "errors" if kind in {"error", "errors"} else kind
        counts[key] = int(match.group("count"))
    return counts


def _repository_process_ids(output: str, repo_root: Path) -> set[int]:
    marker = str(repo_root.resolve()).casefold()
    result: set[int] = set()
    for line in output.splitlines():
        process_id, separator, command_line = line.partition("\t")
        if separator and process_id.isdigit() and marker in command_line.casefold():
            result.add(int(process_id))
    return result


def _matching_process_ids() -> set[int]:
    if os.name != "nt":
        return set()
    command = (
        "Get-CimInstance Win32_Process | Where-Object { "
        "$_.Name -match '^(python|pytest)(\\.exe)?$' "
        '} | ForEach-Object { "$($_.ProcessId)`t$($_.CommandLine)" }'
    )
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        capture_output=True,
        text=True,
        check=False,
    )
    return _repository_process_ids(completed.stdout, REPO_ROOT)


def _pytest_command(python: str, workers: int, basetemp: Path) -> list[str]:
    return [
        python,
        "-m",
        "pytest",
        "-q",
        "-n",
        str(workers),
        "--dist",
        "worksteal",
        "--max-worker-restart",
        "0",
        f"--basetemp={basetemp}",
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=4, choices=range(1, 5))
    parser.add_argument("--receipt", type=Path, default=DEFAULT_RECEIPT)
    args = parser.parse_args(argv)

    python = sys.executable
    collect = subprocess.run(
        [python, "-m", "pytest", "--collect-only", "-q"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    nodes = _selected_nodes(collect.stdout)
    if collect.returncode != 0 or not nodes:
        print(collect.stdout, end="")
        print(collect.stderr, end="", file=sys.stderr)
        return collect.returncode or 2

    # Keep this deliberately short: several repository-bound fixture names are already long,
    # and Windows still fails ordinary file creation once their xdist worker path crosses MAX_PATH.
    basetemp = Path(tempfile.gettempdir()) / "ra-p"
    command = _pytest_command(python, args.workers, basetemp)
    before_processes = _matching_process_ids()
    tree_fingerprint_at_start = _tree_fingerprint()
    index_tree_at_start = _git("write-tree")
    started = datetime.now(UTC)
    started_clock = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    print(completed.stdout, end="")
    print(completed.stderr, end="", file=sys.stderr)
    duration_seconds = round(time.monotonic() - started_clock, 3)
    time.sleep(0.5)
    leaked_processes = sorted(_matching_process_ids() - before_processes)
    tree_fingerprint_at_end = _tree_fingerprint()
    index_tree_at_end = _git("write-tree")
    tree_changed_during_run = (
        tree_fingerprint_at_start != tree_fingerprint_at_end
        or index_tree_at_start != index_tree_at_end
    )
    outcomes = _outcome_counts(f"{completed.stdout}\n{completed.stderr}")

    receipt = {
        "schema_version": 2,
        "command": command,
        "branch": _git("branch", "--show-current"),
        "head": _git("rev-parse", "HEAD"),
        "dirty_tree": bool(_git("status", "--porcelain")),
        "tree_fingerprint_at_start": tree_fingerprint_at_start,
        "tree_fingerprint_at_end": tree_fingerprint_at_end,
        "index_tree_at_start": index_tree_at_start,
        "index_tree_at_end": index_tree_at_end,
        "tree_changed_during_run": tree_changed_during_run,
        "python": sys.version,
        "dependency_lock_sha256": _sha256_file(REPO_ROOT / "requirements-lock.txt"),
        "test_inventory_count": len(nodes),
        "test_inventory_sha256": _sha256_text(nodes),
        "started_at": started.isoformat(),
        "finished_at": datetime.now(UTC).isoformat(),
        "duration_seconds": duration_seconds,
        "exit_code": completed.returncode,
        "worker_count": args.workers,
        "distribution": "worksteal",
        "max_worker_restart": 0,
        "leaked_process_ids": leaked_processes,
        "outcome_counts": outcomes,
    }
    write_redacted_json(args.receipt, receipt)
    print(json.dumps(receipt, sort_keys=True))
    if leaked_processes:
        print(
            f"error: full pytest left descendant process IDs {leaked_processes}",
            file=sys.stderr,
        )
        return 1
    if tree_changed_during_run:
        print("error: repository bytes changed during the full pytest run", file=sys.stderr)
        return 1
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
