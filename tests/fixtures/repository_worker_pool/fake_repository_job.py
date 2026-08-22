"""Parametrized fake child process for `repository_worker_pool` tests.

Not a repository-processing capability -- a controllable stand-in so the worker-pool test suite
never depends on Qwen, Docker, GitHub, or a product repository. Every behavior a test needs
(receipt writing, output volume, failure, long-running for cancellation, invocation counting for
the no-retry proof, environment echoing for the isolation proof) is one flag on this single script.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sleep-seconds", type=float, default=0.0)
    parser.add_argument("--exit-code", type=int, default=0)
    parser.add_argument("--write-receipt", type=Path, default=None)
    parser.add_argument("--stdout-bytes", type=int, default=0)
    parser.add_argument("--stderr-bytes", type=int, default=0)
    parser.add_argument("--counter-file", type=Path, default=None)
    parser.add_argument("--pid-file", type=Path, default=None)
    parser.add_argument("--print-env", action="append", default=[])
    parser.add_argument("--print-cwd", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = _parse_args(argv)

    if args.pid_file is not None:
        args.pid_file.parent.mkdir(parents=True, exist_ok=True)
        args.pid_file.write_text(str(os.getpid()), encoding="utf-8")

    if args.counter_file is not None:
        args.counter_file.parent.mkdir(parents=True, exist_ok=True)
        with args.counter_file.open("a", encoding="utf-8") as handle:
            handle.write("1\n")

    for name in args.print_env:
        value = os.environ.get(name)
        print(f"{name}={'MISSING' if value is None else value}", flush=True)
    if args.print_cwd:
        print(f"CWD={Path.cwd()}", flush=True)

    if args.stdout_bytes > 0:
        sys.stdout.write("A" * args.stdout_bytes)
        sys.stdout.flush()

    if args.stderr_bytes > 0:
        sys.stderr.write("B" * args.stderr_bytes)
        sys.stderr.flush()

    if args.sleep_seconds > 0:
        time.sleep(args.sleep_seconds)

    if args.write_receipt is not None:
        args.write_receipt.parent.mkdir(parents=True, exist_ok=True)
        args.write_receipt.write_text(json.dumps({"ok": True}), encoding="utf-8")

    return args.exit_code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
