# governed_by: plans/master.md + plans/requirements.md + plans/GOVERNANCE.md
# artifact_role: canonical official-check evidence appender
"""Run the canonical official suite and append its output to an existing evidence bundle."""

from __future__ import annotations

import hashlib
import subprocess
from argparse import ArgumentParser
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_ROOT = (REPO_ROOT / "plans" / "investigations" / "evidence").resolve()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _refresh_checksums(evidence_dir: Path) -> None:
    lines = [
        f"{_sha256(path)}  {path.name}"
        for path in sorted(evidence_dir.iterdir())
        if path.is_file() and path.name != "sha256sums.txt"
    ]
    (evidence_dir / "sha256sums.txt").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> int:
    parser = ArgumentParser()
    parser.add_argument("evidence_dir", type=Path)
    parser.add_argument("--attempt", type=int, default=1)
    args = parser.parse_args()
    evidence_dir = args.evidence_dir.resolve()
    if evidence_dir.parent != EVIDENCE_ROOT or not evidence_dir.is_dir():
        raise RuntimeError(f"evidence_dir must be an existing child of {EVIDENCE_ROOT}")
    if args.attempt < 1:
        raise RuntimeError("--attempt must be a positive integer")
    output_path = evidence_dir / f"official-checks-attempt-{args.attempt}.log"
    if output_path.exists():
        raise RuntimeError(f"refusing to replace existing official-check evidence: {output_path}")

    command = [
        str(REPO_ROOT / ".venv" / "Scripts" / "python.exe"),
        str(REPO_ROOT / "scripts" / "governance" / "run_official_checks.py"),
    ]
    started = datetime.now(UTC).isoformat()
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=1_500,
        check=False,
    )
    output_path.write_text(
        f"command={subprocess.list2cmdline(command)}\n"
        f"started_at={started}\n"
        f"finished_at={datetime.now(UTC).isoformat()}\n"
        f"return_code={result.returncode}\n\n"
        f"{result.stdout}{result.stderr}",
        encoding="utf-8",
        newline="\n",
    )
    _refresh_checksums(evidence_dir)
    print(f"official checks exit={result.returncode}; evidence={output_path}")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
