"""Run the complete non-live pytest inventory with bounded, evidenced parallelism."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
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
    started = datetime.now(UTC)
    started_clock = time.monotonic()
    completed = subprocess.run(command, cwd=REPO_ROOT, check=False)
    duration_seconds = round(time.monotonic() - started_clock, 3)
    time.sleep(0.5)
    leaked_processes = sorted(_matching_process_ids() - before_processes)

    receipt = {
        "schema_version": 1,
        "command": command,
        "branch": _git("branch", "--show-current"),
        "head": _git("rev-parse", "HEAD"),
        "dirty_tree": bool(_git("status", "--porcelain")),
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
    }
    write_redacted_json(args.receipt, receipt)
    print(json.dumps(receipt, sort_keys=True))
    if leaked_processes:
        print(
            f"error: full pytest left descendant process IDs {leaked_processes}",
            file=sys.stderr,
        )
        return 1
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
