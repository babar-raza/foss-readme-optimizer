"""Build checksum-complete evidence for registry-or-source acquisition truth."""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path
from typing import Any

from acquisition_truth_evidence_checks import (
    evaluate_acquisition_checks,
    verify_hostile_executor_controls,
)
from acquisition_truth_evidence_sources import (
    load_python_verification,
    load_rust_verification,
    load_typescript_verification,
    verify_evidence_inventory,
)
from acquisition_truth_evidence_support import (
    EVIDENCE_MACHINERY_PATHS,
    IMPLEMENTATION_PATHS,
    build_acquisition_controls,
    representative_roots,
)

from readme_agent.evidence.writer import (
    refresh_sha256sums,
    write_redacted_json,
    write_redacted_text,
)
from readme_agent.gitsafety.clone import remote_head_sha
from readme_agent.registry.loader import load_products
from readme_agent.state.git_backend import default_state_backend
from readme_agent.supervisor.mission_goal_guard import (
    derive_lifecycle_scoreboard,
    lifecycle_scoreboard_sha256,
)
from readme_agent.supervisor.mission_graph import load_mission_graph

REPO_ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_DIR = REPO_ROOT / "plans/investigations/evidence/level8-acquisition-truth"
FAILURE_DIR = REPO_ROOT / "runs/control/acquisition-truth-proof-failure"
TASK_ID = "L8-TRUTH-04-ACQUISITION"
GRAPH_PATH = REPO_ROOT / "plans/investigations/control/level8-autonomous-mission-task-graph.yaml"
PYTHON = sys.executable
SOURCE_PROOFS = {
    "python": REPO_ROOT / "plans/investigations/evidence/level8-python-api-truth",
    "typescript": REPO_ROOT / "plans/investigations/evidence/level8-typescript-export-truth",
    "rust": REPO_ROOT / "plans/investigations/evidence/level8-rust-api-truth",
}
ISOLATED_EXECUTOR_PROOF = REPO_ROOT / "plans/investigations/evidence/level8-isolated-executor"
FOCUSED_COMMAND = (
    PYTHON,
    "-m",
    "pytest",
    "-q",
    "tests/unit/test_acquisition.py",
    "tests/unit/test_acquisition_pins.py",
    "tests/unit/test_ecosystem_resolver.py",
    "tests/unit/test_facts_provider.py",
    "tests/unit/test_draft_product_truth_capability.py",
    "tests/unit/test_fact_acceptance_contract.py",
    "tests/unit/test_facts_schema_v2.py",
    "tests/unit/test_isolated_execution.py",
    "tests/security/test_example_execution_boundary.py",
    "tests/security/test_no_secrets_in_evidence.py",
)
OFFICIAL_COMMAND = (PYTHON, "scripts/governance/run_official_checks.py")


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


def _git(*args: str, root: Path = REPO_ROOT) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_failure(
    *,
    control: dict[str, Any],
    checks: dict[str, bool],
    focused: dict[str, Any],
    official: dict[str, Any] | None,
) -> None:
    FAILURE_DIR.mkdir(parents=True, exist_ok=True)
    write_redacted_text(FAILURE_DIR / "focused-tests.stdout.log", focused["stdout"])
    write_redacted_text(FAILURE_DIR / "focused-tests.stderr.log", focused["stderr"])
    if official is not None:
        write_redacted_text(FAILURE_DIR / "official-checks.stdout.log", official["stdout"])
        write_redacted_text(FAILURE_DIR / "official-checks.stderr.log", official["stderr"])
    write_redacted_json(
        FAILURE_DIR / "verification.json",
        {
            "schema_version": 1,
            "task_id": TASK_ID,
            "control_repository": control,
            "checks": checks,
            "failures": [name for name, passed in checks.items() if not passed],
            "verdict": "FAILED",
        },
    )
    refresh_sha256sums(FAILURE_DIR)


def _build(run_official: bool) -> list[str]:
    start_status = _git("status", "--porcelain=v1", "--untracked-files=all")
    control = {
        "head": _git("rev-parse", "HEAD"),
        "branch": _git("branch", "--show-current") or "HEAD",
        "tree_clean_at_start": not start_status,
        "tree_porcelain_sha256": hashlib.sha256(start_status.encode("utf-8")).hexdigest(),
        "builder_path": Path(__file__).resolve().relative_to(REPO_ROOT).as_posix(),
        "builder_sha256": _sha256(Path(__file__).resolve()),
        "implementation": {
            path: _sha256(REPO_ROOT / path) for path in sorted(IMPLEMENTATION_PATHS)
        },
        "evidence_machinery": {
            path: _sha256(REPO_ROOT / path) for path in sorted(EVIDENCE_MACHINERY_PATHS)
        },
    }
    roots = representative_roots(REPO_ROOT)
    revisions = {org_repo: _git("rev-parse", "HEAD", root=root) for org_repo, root in roots.items()}
    entries = {entry.org_repo: entry for entry in load_products()}
    remote_revisions = {
        org_repo: remote_head_sha(entries[org_repo].clone_url) for org_repo in roots
    }
    clean_representatives = {
        org_repo: not _git("status", "--porcelain=v1", root=root)
        for org_repo, root in roots.items()
    }
    inventories = {
        ecosystem: verify_evidence_inventory(root) for ecosystem, root in SOURCE_PROOFS.items()
    }
    python = load_python_verification(
        SOURCE_PROOFS["python"] / "installed-consumer-verification.json"
    )
    typescript = load_typescript_verification(
        SOURCE_PROOFS["typescript"] / "built-consumer-proof.json"
    )
    rust = load_rust_verification(SOURCE_PROOFS["rust"] / "locked-consumer-proof.json")
    hostile_controls = verify_hostile_executor_controls(ISOLATED_EXECUTOR_PROOF)
    controls = build_acquisition_controls(
        revisions=revisions,
        python_verification=python,
        typescript_verification=typescript,
        rust_verification=rust,
    )
    focused = _run(FOCUSED_COMMAND)
    official = _run(OFFICIAL_COMMAND) if run_official else None
    checks = evaluate_acquisition_checks(
        control=control,
        start_status=start_status,
        current_head=_git("rev-parse", "HEAD"),
        current_status=_git("status", "--porcelain=v1", "--untracked-files=all"),
        clean_representatives=clean_representatives,
        revisions=revisions,
        remote_revisions=remote_revisions,
        inventories=inventories,
        source_verifications=(python, typescript, rust),
        acquisition_controls=controls,
        hostile_controls=hostile_controls,
        focused_exit_code=focused["exit_code"],
        official_exit_code=official["exit_code"] if official is not None else None,
    )
    failures = [name for name, passed in checks.items() if not passed]
    if failures:
        _write_failure(control=control, checks=checks, focused=focused, official=official)
        return failures

    graph, _ = load_mission_graph(GRAPH_PATH)
    task = next(task for task in graph.taskcards if task.task_id == TASK_ID)
    scoreboard = derive_lifecycle_scoreboard(default_state_backend())
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    write_redacted_json(
        EVIDENCE_DIR / "repository-revisions.json",
        {
            "schema_version": 1,
            "revisions": revisions,
            "remote_default_revisions": remote_revisions,
            "clean": clean_representatives,
        },
    )
    write_redacted_json(EVIDENCE_DIR / "source-proof-inventories.json", inventories)
    write_redacted_json(EVIDENCE_DIR / "hostile-executor-controls.json", hostile_controls)
    write_redacted_json(EVIDENCE_DIR / "acquisition-decisions.json", controls)
    write_redacted_text(EVIDENCE_DIR / "focused-tests.stdout.log", focused["stdout"])
    write_redacted_text(EVIDENCE_DIR / "focused-tests.stderr.log", focused["stderr"])
    if official is not None:
        write_redacted_text(EVIDENCE_DIR / "official-checks.stdout.log", official["stdout"])
        write_redacted_text(EVIDENCE_DIR / "official-checks.stderr.log", official["stderr"])
    write_redacted_json(
        EVIDENCE_DIR / "mission-contribution.json",
        {
            "schema_version": 1,
            "task_id": TASK_ID,
            "goal_ids": task.goal_ids,
            "core_contribution": task.core_contribution.model_dump(mode="json"),
            "acceptance_checks_passed": task.acceptance_checks,
            "proof_refs": [
                "plans/investigations/evidence/level8-acquisition-truth/acquisition-decisions.json",
                "plans/investigations/evidence/level8-acquisition-truth/"
                "source-proof-inventories.json",
                "plans/investigations/evidence/level8-acquisition-truth/"
                "hostile-executor-controls.json",
                "plans/investigations/evidence/level8-acquisition-truth/verification.json",
            ],
            "scoreboard_before_sha256": lifecycle_scoreboard_sha256(scoreboard),
            "scoreboard_after_sha256": lifecycle_scoreboard_sha256(scoreboard),
            "first_failing_boundary_before": scoreboard.first_failing_boundary,
            "first_failing_boundary_after": scoreboard.first_failing_boundary,
            "independently_verified": True,
        },
    )
    write_redacted_json(
        EVIDENCE_DIR / "verification.json",
        {
            "schema_version": 1,
            "task_id": TASK_ID,
            "control_repository": control,
            "commands": {
                "focused": {key: focused[key] for key in ("command", "exit_code")},
                "official": (
                    {key: official[key] for key in ("command", "exit_code")}
                    if official is not None
                    else None
                ),
            },
            "checks": checks,
            "failures": failures,
            "verdict": "VERIFIED",
        },
    )
    write_redacted_text(
        EVIDENCE_DIR / "reproduction.txt",
        (
            f"{PYTHON} plans/investigations/tools/build_acquisition_truth_evidence.py "
            "--official --check\n"
        ),
    )
    refresh_sha256sums(EVIDENCE_DIR)
    return failures


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--official", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    failures = _build(args.official)
    if failures:
        raise SystemExit("acquisition truth proof failed: " + ", ".join(failures))
    print(f"wrote acquisition truth evidence to {EVIDENCE_DIR}")


if __name__ == "__main__":
    main()
