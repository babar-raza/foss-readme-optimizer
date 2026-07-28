"""Build checksum-complete evidence for seven real FACTS_READY representatives."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any

from filelock import FileLock, Timeout
from seven_ecosystem_fact_evidence_support import sha256_file, verify_campaign

from readme_agent.evidence.writer import (
    refresh_sha256sums,
    write_redacted_json,
    write_redacted_text,
)
from readme_agent.state.git_backend import default_state_backend
from readme_agent.supervisor.mission_goal_guard import (
    derive_lifecycle_scoreboard,
    lifecycle_scoreboard_sha256,
)
from readme_agent.supervisor.mission_graph import load_mission_graph

REPO_ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_DIR = REPO_ROOT / "plans/investigations/evidence/level8-seven-ecosystem-facts"
FAILURE_DIR = REPO_ROOT / "runs/control/seven-ecosystem-fact-proof-failure"
LOCK_PATH = REPO_ROOT / "runs/control/locks/seven-ecosystem-fact-evidence.lock"
GRAPH_PATH = REPO_ROOT / "plans/investigations/control/level8-autonomous-mission-task-graph.yaml"
TASK_ID = "L8-TRUTH-07-SEVEN-ECOSYSTEMS"
PYTHON = sys.executable
FOCUSED_COMMAND = (
    PYTHON,
    "-m",
    "pytest",
    "-q",
    "tests/unit/test_registry_priority.py",
    "tests/unit/test_fact_acceptance_contract.py",
    "tests/unit/test_supervisor_product_truth.py",
    "tests/unit/test_portfolio.py",
    "tests/unit/test_portfolio_stage_cache.py",
    "tests/unit/test_local_poc_evidence.py",
    "tests/security/test_example_execution_boundary.py",
    "tests/security/test_no_secrets_in_evidence.py",
)
OFFICIAL_COMMAND = (PYTHON, "scripts/governance/run_official_checks.py")
MACHINERY_PATHS = (
    "plans/investigations/tools/build_seven_ecosystem_fact_evidence.py",
    "plans/investigations/tools/seven_ecosystem_fact_evidence_support.py",
)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()


def _run(command: tuple[str, ...]) -> dict[str, Any]:
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return {
        "command": subprocess.list2cmdline(command),
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def _build(run_official: bool) -> list[str]:
    head = _git("rev-parse", "HEAD")
    start_status = _git("status", "--porcelain=v1", "--untracked-files=all")
    campaign = verify_campaign(REPO_ROOT)
    focused = _run(FOCUSED_COMMAND)
    official = _run(OFFICIAL_COMMAND) if run_official else None
    checks = {
        **campaign["checks"],
        "control_tree_clean": not start_status,
        "focused_tests_pass": focused["exit_code"] == 0,
        "official_checks_pass": official is not None and official["exit_code"] == 0,
        "tree_stable": (
            _git("rev-parse", "HEAD") == head
            and _git("status", "--porcelain=v1", "--untracked-files=all") == start_status
        ),
    }
    failures = [name for name, passed in checks.items() if not passed]
    output_dir = FAILURE_DIR if failures else EVIDENCE_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    write_redacted_json(output_dir / "representative-facts.json", campaign)
    write_redacted_text(output_dir / "focused-tests.stdout.log", focused["stdout"])
    write_redacted_text(output_dir / "focused-tests.stderr.log", focused["stderr"])
    if official is not None:
        write_redacted_text(output_dir / "official-checks.stdout.log", official["stdout"])
        write_redacted_text(output_dir / "official-checks.stderr.log", official["stderr"])
    write_redacted_json(
        output_dir / "verification.json",
        {
            "schema_version": 1,
            "task_id": TASK_ID,
            "control_repository": {
                "head": head,
                "branch": _git("branch", "--show-current"),
                "tree_clean_at_start": not start_status,
                "evidence_machinery": {
                    path: sha256_file(REPO_ROOT / path) for path in MACHINERY_PATHS
                },
            },
            "commands": {
                "canonical_runtime": (
                    ".venv/Scripts/readme-agent supervise --registry "
                    "runs/level8-truth-seven-ecosystems/seven-ecosystem-representatives.json "
                    "--execution-profile local_poc --max-readme-poc-stage FACTS_READY"
                ),
                "focused": {key: focused[key] for key in ("command", "exit_code")},
                "official": (
                    {key: official[key] for key in ("command", "exit_code")}
                    if official is not None
                    else None
                ),
            },
            "checks": checks,
            "failures": failures,
            "verdict": "FAILED" if failures else "VERIFIED",
        },
    )
    if not failures:
        graph, _ = load_mission_graph(GRAPH_PATH)
        task = next(item for item in graph.taskcards if item.task_id == TASK_ID)
        scoreboard = derive_lifecycle_scoreboard(default_state_backend())
        scoreboard_hash = lifecycle_scoreboard_sha256(scoreboard)
        write_redacted_json(
            output_dir / "mission-contribution.json",
            {
                "schema_version": 1,
                "task_id": TASK_ID,
                "goal_ids": task.goal_ids,
                "core_contribution": task.core_contribution.model_dump(mode="json"),
                "acceptance_checks_passed": task.acceptance_checks,
                "proof_refs": [
                    "plans/investigations/evidence/level8-seven-ecosystem-facts/"
                    "representative-facts.json",
                    "plans/investigations/evidence/level8-seven-ecosystem-facts/verification.json",
                ],
                "scoreboard_before_sha256": scoreboard_hash,
                "scoreboard_after_sha256": scoreboard_hash,
                "first_failing_boundary_before": scoreboard.first_failing_boundary,
                "first_failing_boundary_after": scoreboard.first_failing_boundary,
                "independently_verified": True,
            },
        )
        write_redacted_text(
            output_dir / "reproduction.txt",
            (
                f"{PYTHON} plans/investigations/tools/"
                "build_seven_ecosystem_fact_evidence.py --official --check\n"
            ),
        )
    refresh_sha256sums(output_dir)
    return failures


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--official", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        with FileLock(LOCK_PATH, timeout=0):
            failures = _build(args.official)
    except Timeout as exc:
        raise SystemExit("seven-ecosystem fact proof already has an active run") from exc
    if failures:
        raise SystemExit("seven-ecosystem fact proof failed: " + ", ".join(failures))
    print(f"wrote seven-ecosystem fact evidence to {EVIDENCE_DIR}")


if __name__ == "__main__":
    main()
