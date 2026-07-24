# governed_by: plans/master.md + plans/requirements.md + plans/GOVERNANCE.md
# artifact_role: PRODSYS-P0-T1 controlled reproduction of official-checks non-determinism
"""Run run_official_checks.py N times, single-process, against one unchanged tree.

Records exit code, wall-clock, and (for pytest) the reported pass/fail/deselected counts for
each attempt, so OFFICIAL-CHECKS-NONDETERMINISM can be judged PROVEN/not-reproduced from direct
evidence rather than the four historical, uncontrolled data points already on record.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_ROOT = (REPO_ROOT / "plans" / "investigations" / "evidence").resolve()
_PYTEST_SUMMARY_RE = re.compile(
    r"^(?:(?P<failed>\d+) failed, )?(?P<passed>\d+) passed(?:, (?P<deselected>\d+) deselected)?"
    r"(?:, (?P<skipped>\d+) skipped)?.* in [\d.]+s"
)


def _run_once(attempt: int) -> dict:
    start = time.monotonic()
    result = subprocess.run(
        [
            str(REPO_ROOT / ".venv" / "Scripts" / "python.exe"),
            "scripts/governance/run_official_checks.py",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    elapsed = time.monotonic() - start
    pytest_summary = None
    for line in result.stdout.splitlines():
        match = _PYTEST_SUMMARY_RE.search(line.strip())
        if match:
            pytest_summary = {k: int(v) for k, v in match.groupdict(default=0).items()}
            break
    return {
        "attempt": attempt,
        "started_at": datetime.now(UTC).isoformat(),
        "elapsed_seconds": round(elapsed, 1),
        "exit_code": result.returncode,
        "pytest_summary": pytest_summary,
        "stdout_tail": result.stdout[-2000:],
        "stderr_tail": result.stderr[-2000:] if result.stderr else "",
    }


def main() -> int:
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    output_dir = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else (EVIDENCE_ROOT / "prodsys-official-checks-nondeterminism")
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    dirty = subprocess.run(
        ["git", "status", "--porcelain"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    ).stdout

    attempts = []
    for i in range(1, n + 1):
        print(f"=== attempt {i}/{n} ===", file=sys.stderr, flush=True)
        record = _run_once(i)
        attempts.append(record)
        print(
            f"  exit={record['exit_code']} elapsed={record['elapsed_seconds']}s "
            f"pytest={record['pytest_summary']}",
            file=sys.stderr,
            flush=True,
        )

    exit_codes = {a["exit_code"] for a in attempts}
    pytest_summaries = {json.dumps(a["pytest_summary"], sort_keys=True) for a in attempts}
    elapsed_values = [a["elapsed_seconds"] for a in attempts]

    verdict = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "control_revision": head,
        "tree_dirty_at_start": bool(dirty.strip()),
        "attempts_requested": n,
        "attempts_completed": len(attempts),
        "distinct_exit_codes": sorted(exit_codes),
        "distinct_pytest_summaries": sorted(pytest_summaries),
        "all_attempts_agree": len(exit_codes) == 1 and len(pytest_summaries) == 1,
        "elapsed_seconds_min": min(elapsed_values),
        "elapsed_seconds_max": max(elapsed_values),
        "elapsed_seconds_swing_pct": round(
            (max(elapsed_values) - min(elapsed_values)) / min(elapsed_values) * 100, 1
        )
        if min(elapsed_values) > 0
        else None,
        "verdict": (
            "REPRODUCED_NONDETERMINISM"
            if not (len(exit_codes) == 1 and len(pytest_summaries) == 1)
            else "NOT_REPRODUCED_UNDER_CONTROLLED_SINGLE_PROCESS_CONDITIONS"
        ),
        "attempts": attempts,
    }
    (output_dir / "reproduction-verdict.json").write_text(
        json.dumps(verdict, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    (output_dir / "reproduction-command.txt").write_text(
        ".venv/Scripts/python "
        "plans/investigations/tools/measure_official_checks_reproducibility.py "
        f"plans/investigations/evidence/prodsys-official-checks-nondeterminism {n}\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps({k: v for k, v in verdict.items() if k != "attempts"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
