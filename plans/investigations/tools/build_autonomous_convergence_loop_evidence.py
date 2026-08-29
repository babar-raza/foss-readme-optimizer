"""Assemble the autonomous-convergence-loop evidence bundle.

Produces `plans/investigations/evidence/autonomous-convergence-loop/`:
`REPORT.md` (the citing report GOVERNANCE organization rule 7 requires), `closeout-control.json`
(machine-readable gate outcomes), `independent-verification.json`, `mission-contribution.json`,
and `sha256sums.txt` (the name `evidence/writer.py::refresh_sha256sums()` writes and
`verify_sha256sums()` reads; some older bundles in this tree use an `SHA256SUMS` file written by a
different producer, which this tool deliberately does not imitate).

The per-gate artifacts under `gate-outputs/` are written by the sprint itself and
are read, not regenerated, here -- this tool never invents a result it did not observe.

Checksums are produced through `evidence/writer.py::refresh_sha256sums()` rather than a private
walk, for the same reason `local_poc_cache.py::_inventory_valid()` was repaired this sprint: a
second, independent enumeration silently disagrees with the sealed one past Windows MAX_PATH.

Run: `.venv/Scripts/python plans/investigations/tools/build_autonomous_convergence_loop_evidence.py`
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from readme_agent.evidence.writer import refresh_sha256sums  # noqa: E402

BUNDLE = REPO_ROOT / "plans" / "investigations" / "evidence" / "autonomous-convergence-loop"
GATE_OUTPUTS = BUNDLE / "gate-outputs"


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=False
    ).stdout.strip()


def _load_gate_outcomes() -> dict:
    path = GATE_OUTPUTS / "gate-outcomes.json"
    if not path.is_file():
        raise SystemExit(
            f"missing {path}; the sprint must record its own gate outcomes before sealing"
        )
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    if not GATE_OUTPUTS.is_dir():
        raise SystemExit(f"missing {GATE_OUTPUTS}")
    outcomes = _load_gate_outcomes()
    generated_at = datetime.now(UTC).isoformat()
    head = _git("rev-parse", "HEAD")

    closeout = {
        "schema_version": 1,
        "investigation": "autonomous-convergence-loop",
        "generated_at": generated_at,
        "head": head,
        "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "tree_clean_at_seal": _git("status", "--porcelain") == "",
        "gates": outcomes["gates"],
        "verdict": outcomes["verdict"],
        "remaining_work": outcomes["remaining_work"],
    }
    (BUNDLE / "closeout-control.json").write_text(
        json.dumps(closeout, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    (BUNDLE / "independent-verification.json").write_text(
        json.dumps(outcomes["independent_verification"], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (BUNDLE / "mission-contribution.json").write_text(
        json.dumps(outcomes["mission_contribution"], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    cited = sorted(path.name for path in GATE_OUTPUTS.iterdir() if path.is_file())
    report = [
        "# Autonomous convergence loop — evidence report",
        "",
        f"Generated: {generated_at}  ",
        f"HEAD: `{head}`  ",
        f"Producer: `plans/investigations/tools/{Path(__file__).name}`",
        "",
        "## Verdict",
        "",
        outcomes["verdict"],
        "",
        "## Gate outcomes",
        "",
        "| Gate | Outcome | Detail |",
        "|---|---|---|",
    ]
    for gate in outcomes["gates"]:
        report.append(f"| {gate['gate']} | {gate['outcome']} | {gate['detail']} |")
    report += [
        "",
        "## Cited artifacts",
        "",
        "Every file below is produced by this sprint and cited here, per `plans/GOVERNANCE.md`",
        "organization rules 7 and 8 (traceability both ways; no orphan artifacts).",
        "",
    ]
    report += [f"- [`gate-outputs/{name}`](gate-outputs/{name})" for name in cited]
    report += [
        "",
        "## Remaining work",
        "",
    ]
    report += [f"- {item}" for item in outcomes["remaining_work"]]
    report += [
        "",
        "## Independent verification",
        "",
        outcomes["independent_verification"]["summary"],
        "",
    ]
    (BUNDLE / "REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")

    refresh_sha256sums(BUNDLE)
    print(f"sealed {BUNDLE} ({len(cited)} cited gate artifact(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
