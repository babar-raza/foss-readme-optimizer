# governed_by: plans/master.md + plans/requirements.md + plans/GOVERNANCE.md
# artifact_role: pre-production truthful-baseline acceptance-evidence producer
"""Run the truthful-baseline gates and preserve the pilot false-success correction."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_DIR = (
    REPO_ROOT
    / "plans"
    / "investigations"
    / "evidence"
    / "level8-preproduction-truthful-baseline-2026-07-24"
)
PILOT_RUNS = {
    "false-success-before-repair": "20260723-230757-082f",
    "3d-java-after-repair": "20260723-231310-624b",
    "cells-java-after-repair": "20260723-231434-0dba",
    "pdf-java-after-repair": "20260723-231612-3132",
}
EXPECTED_STATUSES = {
    "false-success-before-repair": "CONVERGED_NO_CHANGE",
    "3d-java-after-repair": "PARTIAL_WITH_FINDINGS",
    "cells-java-after-repair": "PARTIAL_WITH_FINDINGS",
    "pdf-java-after-repair": "PARTIAL_WITH_FINDINGS",
}
SECRET_PATTERN = re.compile(
    rb"(?:gh[oprsu]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|"
    rb"sk-[A-Za-z0-9]{20,}|Bearer\s+[A-Za-z0-9._-]{12,})"
)
IMPLEMENTATION_INPUTS = (
    "docs/architecture.md",
    "plans/investigations/control/level8-autonomous-mission-task-graph.yaml",
    "plans/requirements.md",
    "scripts/governance/build_level8_requirement_taskcard_coverage.py",
    "src/readme_agent/llm/prompt_registry.py",
    "src/readme_agent/supervisor/convergence.py",
    "src/readme_agent/supervisor/finding_status.py",
    "src/readme_agent/supervisor/mission_control.py",
    "src/readme_agent/supervisor/planner_loop.py",
    "src/readme_agent/supervisor/status.py",
    "src/readme_agent/supervisor/work_ledger.py",
    "tests/unit/test_cli.py",
    "tests/unit/test_convergence.py",
    "tests/unit/test_mission_control.py",
    "tests/unit/test_prompt_registry.py",
    "tests/unit/test_supervisor_loop.py",
    "tests/unit/test_work_ledger.py",
)


def _sha256(path: Path) -> str:
    normalized = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(normalized).hexdigest()


def _verify_bundle(source: Path) -> None:
    expected: dict[str, str] = {}
    for line in (source / "sha256sums.txt").read_text(encoding="utf-8").splitlines():
        checksum, filename = line.split("  ", 1)
        expected[filename] = checksum
    observed = {
        path.name: _sha256(path)
        for path in source.iterdir()
        if path.is_file() and path.name != "sha256sums.txt"
    }
    if observed != expected:
        raise RuntimeError(f"checksum mismatch in {source}")


def _prepare_directory() -> None:
    governed_root = (REPO_ROOT / "plans" / "investigations" / "evidence").resolve()
    if EVIDENCE_DIR.parent.resolve() != governed_root:
        raise RuntimeError(f"refusing to write outside {governed_root}")
    if EVIDENCE_DIR.exists():
        shutil.rmtree(EVIDENCE_DIR)
    EVIDENCE_DIR.mkdir(parents=True)


def _run(command: list[str], timeout: int) -> dict[str, object]:
    started_at = datetime.now(UTC).isoformat()
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        check=False,
    )
    return {
        "command": command,
        "return_code": completed.returncode,
        "started_at": started_at,
        "finished_at": datetime.now(UTC).isoformat(),
        "output": completed.stdout,
    }


def _write_result(path: Path, result: dict[str, object]) -> None:
    command = subprocess.list2cmdline(result["command"])  # type: ignore[arg-type]
    path.write_text(
        f"$ {command}\n"
        f"return_code={result['return_code']}\n"
        f"started_at={result['started_at']}\n"
        f"finished_at={result['finished_at']}\n\n"
        f"{str(result['output']).rstrip()}\n",
        encoding="utf-8",
        newline="\n",
    )


def _preserve_pilot_evidence() -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    target_root = EVIDENCE_DIR / "pilot-terminal-evidence"
    target_root.mkdir()
    for label, run_id in PILOT_RUNS.items():
        source = REPO_ROOT / "runs" / "evidence" / run_id
        _verify_bundle(source)
        target = target_root / label
        shutil.copytree(source, target)
        manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
        status = manifest["status"]
        results.append(
            {
                "label": label,
                "run_id": run_id,
                "repository": manifest["org_repo"],
                "upstream_revision": manifest["upstream_revision"],
                "status": status,
                "expected_status": EXPECTED_STATUSES[label],
                "status_matches": status == EXPECTED_STATUSES[label],
                "bundle_checksums_valid": True,
            }
        )
    return results


def _write_checksums() -> None:
    files = sorted(
        path for path in EVIDENCE_DIR.rglob("*") if path.is_file() and path.name != "sha256sums.txt"
    )
    secret_hits = [
        path.relative_to(EVIDENCE_DIR).as_posix()
        for path in files
        if SECRET_PATTERN.search(path.read_bytes())
    ]
    if secret_hits:
        raise RuntimeError(f"secret-like values found in evidence: {secret_hits}")
    lines = [f"{_sha256(path)}  {path.relative_to(EVIDENCE_DIR).as_posix()}" for path in files]
    (EVIDENCE_DIR / "sha256sums.txt").write_text(
        "\n".join(lines) + "\n", encoding="utf-8", newline="\n"
    )


def main() -> int:
    _prepare_directory()
    python = str(REPO_ROOT / ".venv" / "Scripts" / "python.exe")
    focused = _run(
        [
            python,
            "-m",
            "pytest",
            "-q",
            "tests/unit/test_supervisor_loop.py",
            "tests/unit/test_work_ledger.py",
            "tests/unit/test_convergence.py",
            "tests/unit/test_prompt_registry.py",
            "tests/unit/test_mission_control.py",
            "tests/unit/test_cli.py",
        ],
        1_200,
    )
    official = _run(
        [python, "scripts/governance/run_official_checks.py"],
        1_800,
    )
    _write_result(EVIDENCE_DIR / "focused-truthful-runtime-tests.log", focused)
    _write_result(EVIDENCE_DIR / "complete-official-checks.log", official)
    pilots = _preserve_pilot_evidence()
    all_pilots_match = all(item["status_matches"] for item in pilots)
    acceptance = {
        "schema_version": 1,
        "task_id": "L8-PREPRODUCTION-TRUTHFUL-BASELINE",
        "generated_at": datetime.now(UTC).isoformat(),
        "source_head": subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip(),
        "implementation_input_sha256": {
            path: _sha256(REPO_ROOT / path) for path in IMPLEMENTATION_INPUTS
        },
        "working_tree_status": subprocess.run(
            ["git", "status", "--short"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.splitlines(),
        "focused_tests_passed": focused["return_code"] == 0,
        "official_checks_passed": official["return_code"] == 0,
        "pilot_terminal_observations": pilots,
        "false_success_correction_preserved": all_pilots_match,
        "independent_acceptance_checks": {
            "unresolved_findings_are_nonzero": all_pilots_match,
            "proposal_ready_is_distinct_from_no_change": focused["return_code"] == 0,
            "planner_stop_is_not_authoritative": focused["return_code"] == 0,
            "prompt_loading_is_order_and_cwd_independent": focused["return_code"] == 0,
            "mission_resumption_is_durable": focused["return_code"] == 0,
        },
    }
    acceptance["accepted"] = bool(
        acceptance["focused_tests_passed"]
        and acceptance["official_checks_passed"]
        and acceptance["false_success_correction_preserved"]
        and all(acceptance["independent_acceptance_checks"].values())
    )
    (EVIDENCE_DIR / "truthful-baseline-acceptance.json").write_text(
        json.dumps(acceptance, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (EVIDENCE_DIR / "reproduce.md").write_text(
        "# Reproduce the truthful baseline\n\n"
        "From the repository root:\n\n"
        "```powershell\n"
        ".venv/Scripts/python "
        "plans/investigations/tools/collect_preproduction_truthful_baseline_evidence.py\n"
        "```\n",
        encoding="utf-8",
        newline="\n",
    )
    _write_checksums()
    print(json.dumps(acceptance, indent=2))
    return 0 if acceptance["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
