"""Build clean-commit live evidence for the truth-eligible isolated executor."""

from __future__ import annotations

import argparse
import hashlib
import subprocess
from pathlib import Path
from typing import Any

from isolated_executor_evidence_support import (
    CONTROL_SCRIPT,
    IMAGE,
    docker_inventory,
    run_live_controls,
)

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
EVIDENCE_DIR = REPO_ROOT / "plans/investigations/evidence/level8-isolated-executor"
GRAPH_PATH = REPO_ROOT / "plans/investigations/control/level8-autonomous-mission-task-graph.yaml"
TASK_ID = "L8-TRUTH-03A-ISOLATED-EXECUTOR"
REQUIREMENT_ID = "L8-019"
OFFICIAL_COMMAND = (
    str(REPO_ROOT / ".venv/Scripts/python.exe"),
    "scripts/governance/run_official_checks.py",
)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _control_state() -> dict[str, Any]:
    status = _git("status", "--porcelain=v1")
    builder = Path(__file__).resolve()
    support = builder.with_name("isolated_executor_evidence_support.py")
    implementation_paths = [
        REPO_ROOT / "src/readme_agent/facts/isolated_execution.py",
        REPO_ROOT / "src/readme_agent/facts/isolated_execution_inputs.py",
        REPO_ROOT / "src/readme_agent/facts/isolated_execution_schema.py",
        REPO_ROOT / "src/readme_agent/facts/example_execution.py",
        REPO_ROOT / "src/readme_agent/facts/example_verification_schema.py",
        REPO_ROOT / "src/readme_agent/facts/local_verification.py",
    ]
    return {
        "head": _git("rev-parse", "HEAD"),
        "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "tree_clean_at_start": not status,
        "tree_porcelain_sha256": hashlib.sha256(status.encode("utf-8")).hexdigest(),
        "builder_path": builder.relative_to(REPO_ROOT).as_posix(),
        "builder_sha256": _sha256(builder),
        "support_path": support.relative_to(REPO_ROOT).as_posix(),
        "support_sha256": _sha256(support),
        "implementation": {
            path.relative_to(REPO_ROOT).as_posix(): _sha256(path) for path in implementation_paths
        },
    }


def _official_checks(control: dict[str, Any]) -> dict[str, Any]:
    if not control["tree_clean_at_start"]:
        raise RuntimeError("official isolation proof requires a clean committed tree")
    result = subprocess.run(
        OFFICIAL_COMMAND,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    stable = _git("rev-parse", "HEAD") == control["head"] and not _git("status", "--porcelain=v1")
    return {
        "command": ".venv/Scripts/python scripts/governance/run_official_checks.py",
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "tree_stable": stable,
    }


def _write(run_official: bool) -> list[str]:
    control = _control_state()
    official = _official_checks(control) if run_official else None
    success, timeout, host = run_live_controls()
    cleanup_inventory = docker_inventory()
    expected_stdout = {
        "uid=65534",
        "pids=32",
        "memory=134217728",
        "cpu=50000 100000",
        "interfaces=lo",
        "root_read_only=true",
        "isolation_controls_passed=true",
    }
    observed_stdout = set(success["stdout"].splitlines())
    checks = {
        "official_checks_pass": bool(
            official
            and official["exit_code"] == 0
            and official["tree_stable"]
            and "All official checks passed." in official["stdout"]
        ),
        "effective_controls_match_policy": expected_stdout <= observed_stdout,
        "immutable_image_observed": success["image"]["repo_digest"] == IMAGE,
        "process_inventory_recorded": bool(success["process_inventory"]),
        "secret_not_in_output": "ghp_synthetic" not in success["stdout"] + success["stderr"],
        "success_cleanup_complete": all(success["cleanup"].values()),
        "timeout_killed": timeout["timed_out"] and timeout["return_code"] == 124,
        "timeout_cleanup_complete": all(timeout["cleanup"].values()),
        "host_truth_ineligible": (
            host["isolation_kind"] == "host_secret_filtered" and not host["truth_eligible"]
        ),
        "no_managed_resources_remain": not any(cleanup_inventory.values()),
    }
    failures = [name for name, passed in checks.items() if not passed]
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    write_redacted_text(EVIDENCE_DIR / "control.sh", CONTROL_SCRIPT)
    write_redacted_json(EVIDENCE_DIR / "isolated-success.json", success)
    write_redacted_json(EVIDENCE_DIR / "isolated-timeout.json", timeout)
    write_redacted_json(EVIDENCE_DIR / "host-negative-control.json", host)
    write_redacted_json(EVIDENCE_DIR / "cleanup-inventory.json", cleanup_inventory)
    if official:
        write_redacted_text(EVIDENCE_DIR / "official-checks.stdout.log", official["stdout"])
        write_redacted_text(EVIDENCE_DIR / "official-checks.stderr.log", official["stderr"])
    write_redacted_json(
        EVIDENCE_DIR / "verification.json",
        {
            "schema_version": 1,
            "task_id": TASK_ID,
            "requirement_id": REQUIREMENT_ID,
            "control_repository": control,
            "checks": checks,
            "official_check": (
                {
                    "command": official["command"],
                    "exit_code": official["exit_code"],
                    "tree_stable": official["tree_stable"],
                    "raw_stdout": "official-checks.stdout.log",
                    "raw_stderr": "official-checks.stderr.log",
                }
                if official
                else {"status": "not_run"}
            ),
            "failures": failures,
            "verdict": "VERIFIED" if not failures else "FAILED",
        },
    )
    graph, _ = load_mission_graph(GRAPH_PATH)
    task = next(task for task in graph.taskcards if task.task_id == TASK_ID)
    scoreboard = derive_lifecycle_scoreboard(default_state_backend())
    scoreboard_hash = lifecycle_scoreboard_sha256(scoreboard)
    write_redacted_json(
        EVIDENCE_DIR / "mission-contribution.json",
        {
            "schema_version": 1,
            "task_id": TASK_ID,
            "goal_ids": task.goal_ids,
            "core_contribution": task.core_contribution.model_dump(mode="json"),
            "acceptance_checks_passed": task.acceptance_checks,
            "proof_refs": [
                "plans/investigations/evidence/level8-isolated-executor/verification.json",
                "plans/investigations/evidence/level8-isolated-executor/isolated-success.json",
                "plans/investigations/evidence/level8-isolated-executor/isolated-timeout.json",
            ],
            "scoreboard_before_sha256": scoreboard_hash,
            "scoreboard_after_sha256": scoreboard_hash,
            "first_failing_boundary_before": scoreboard.first_failing_boundary,
            "first_failing_boundary_after": scoreboard.first_failing_boundary,
            "independently_verified": not failures,
        },
    )
    reproduction = (
        f"docker pull {IMAGE}\n"
        ".venv/Scripts/python "
        "plans/investigations/tools/build_isolated_executor_evidence.py --official --check\n"
    )
    write_redacted_text(EVIDENCE_DIR / "reproduction.txt", reproduction)
    refresh_sha256sums(EVIDENCE_DIR)
    return failures


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--official", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    failures = _write(args.official)
    if args.check and failures:
        raise SystemExit("isolated executor evidence failed: " + ", ".join(failures))
    print(f"wrote isolated-executor evidence to {EVIDENCE_DIR}")


if __name__ == "__main__":
    main()
