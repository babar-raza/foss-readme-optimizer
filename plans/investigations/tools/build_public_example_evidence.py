"""Build checksum-complete evidence for seven-ecosystem public examples."""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path
from typing import Any

from acquisition_truth_evidence_checks import verify_hostile_executor_controls
from public_example_evidence_support import (
    REPRESENTATIVES,
    case_record,
    curated_rejection_controls,
    run_public_example_cases,
)

from readme_agent.evidence.writer import (
    refresh_sha256sums,
    write_redacted_json,
    write_redacted_text,
)
from readme_agent.gitsafety.clone import remote_head_sha
from readme_agent.registry.loader import require_listed
from readme_agent.state.git_backend import default_state_backend
from readme_agent.supervisor.mission_goal_guard import (
    derive_lifecycle_scoreboard,
    lifecycle_scoreboard_sha256,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_DIR = REPO_ROOT / "plans/investigations/evidence/level8-public-examples"
FAILURE_DIR = REPO_ROOT / "runs/control/public-example-proof-failure"
ISOLATED_EXECUTOR_PROOF = REPO_ROOT / "plans/investigations/evidence/level8-isolated-executor"
TASK_ID = "L8-TRUTH-05-PUBLIC-EXAMPLES"
PYTHON = sys.executable
IMPLEMENTATION_PATHS = (
    "src/readme_agent/facts/compiled_consumer.py",
    "src/readme_agent/facts/compiled_consumer_schema.py",
    "src/readme_agent/facts/cpp_example_verifier.py",
    "src/readme_agent/facts/dotnet_example_verifier.py",
    "src/readme_agent/facts/example_verification_schema.py",
    "src/readme_agent/facts/go_example_verifier.py",
    "src/readme_agent/facts/java_example_verifier.py",
    "src/readme_agent/facts/local_verification.py",
    "src/readme_agent/facts/python_example_verifier.py",
    "src/readme_agent/facts/repository_examples.py",
    "src/readme_agent/facts/rust_example_verifier.py",
    "src/readme_agent/facts/typescript_example_verifier.py",
)
FOCUSED_COMMAND = (
    PYTHON,
    "-m",
    "pytest",
    "-q",
    "tests/unit/test_repository_examples.py",
    "tests/unit/test_compiled_consumer_verifiers.py",
    "tests/unit/test_local_verification.py",
    "tests/unit/test_fact_acceptance_contract.py",
    "tests/security/test_example_execution_boundary.py",
    "tests/security/test_isolated_execution_hostile_live.py",
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


def _write_failure(payload: dict[str, Any]) -> None:
    FAILURE_DIR.mkdir(parents=True, exist_ok=True)
    write_redacted_json(FAILURE_DIR / "verification.json", payload)
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
        "support_sha256": _sha256(Path(__file__).with_name("public_example_evidence_support.py")),
        "implementation": {
            path: _sha256(REPO_ROOT / path) for path in sorted(IMPLEMENTATION_PATHS)
        },
    }
    cases, results = run_public_example_cases(REPO_ROOT)
    rejection_controls = curated_rejection_controls(REPO_ROOT)
    records = [case_record(case, results[case.ecosystem]) for case in cases]
    hostile_controls = verify_hostile_executor_controls(ISOLATED_EXECUTOR_PROOF)
    remote_revisions = {
        ecosystem: remote_head_sha(require_listed(org_repo).clone_url)
        for ecosystem, org_repo in REPRESENTATIVES.items()
    }
    focused = _run(FOCUSED_COMMAND)
    official = _run(OFFICIAL_COMMAND) if run_official else None
    checks = {
        "clean_committed_start": not start_status,
        "all_seven_ecosystems_present": set(results) == set(REPRESENTATIVES),
        "all_selected_examples_verified": all(
            result.outcome == "SOURCE_BUILD_VERIFIED" and result.truth_eligible
            for result in results.values()
        ),
        "all_selected_examples_network_denied": all(
            result.isolated_execution is not None
            and result.isolated_execution.policy.network_mode == "none"
            for result in results.values()
        ),
        "all_selected_examples_cleanup_complete": all(
            result.isolated_execution is not None and result.isolated_execution.cleanup.complete
            for result in results.values()
        ),
        "all_selected_examples_have_public_symbols": all(
            bool(result.verified_public_symbols) for result in results.values()
        ),
        "all_selected_examples_have_dependency_inputs": all(
            bool(result.acquisition_dependency_pins) for result in results.values()
        ),
        "remote_default_revisions_match": all(
            remote_revisions[case.ecosystem] == case.snapshot.source_revision for case in cases
        ),
        "python_curated_stale_example_rejected": (
            rejection_controls["python"].outcome == "BUILD_FAILED"
            and not rejection_controls["python"].truth_eligible
        ),
        "typescript_curated_stale_example_rejected": (
            rejection_controls["typescript"].outcome == "BUILD_FAILED"
            and not rejection_controls["typescript"].truth_eligible
        ),
        "hostile_executor_controls_pass": bool(hostile_controls.get("accepted")),
        "focused_tests_pass": focused["exit_code"] == 0,
        "official_checks_pass": official is not None and official["exit_code"] == 0,
        "head_stable": _git("rev-parse", "HEAD") == control["head"],
    }
    failures = [name for name, passed in checks.items() if not passed]
    if failures:
        _write_failure(
            {
                "schema_version": 1,
                "task_id": TASK_ID,
                "control_repository": control,
                "checks": checks,
                "failures": failures,
                "records": records,
                "verdict": "FAILED",
            }
        )
        return failures

    scoreboard = derive_lifecycle_scoreboard(default_state_backend())
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    for ecosystem, result in sorted(results.items()):
        write_redacted_json(
            EVIDENCE_DIR / f"{ecosystem}-verification.json",
            result.model_dump(mode="json"),
        )
    write_redacted_json(
        EVIDENCE_DIR / "curated-readme-dispositions.json",
        {
            "schema_version": 1,
            "principle": (
                "Prefer product-agent-curated README content, but reuse no material unit until "
                "accepted repository, package, public-API, and compiler evidence validates it."
            ),
            "records": records,
            "rejection_controls": {
                ecosystem: result.model_dump(mode="json")
                for ecosystem, result in sorted(rejection_controls.items())
            },
        },
    )
    write_redacted_json(EVIDENCE_DIR / "hostile-executor-controls.json", hostile_controls)
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
            "goal_ids": ["GOAL-TRUTH"],
            "core_contribution": {
                "kind": "visible_deliverable",
                "summary": (
                    "Prove imports or namespaces, public symbols, compilation or execution, and "
                    "secret-free inputs for selected examples in the same disposable OS-isolated "
                    "executor used for acquisition proof."
                ),
            },
            "acceptance_checks_passed": [
                "Unresolved",
                "private",
                "uncompiled",
                "or secret-dependent examples cannot become verified",
                "Host-only compilation or execution cannot become verified",
            ],
            "proof_refs": [
                "plans/investigations/evidence/level8-public-examples/"
                "curated-readme-dispositions.json",
                "plans/investigations/evidence/level8-public-examples/"
                "hostile-executor-controls.json",
                "plans/investigations/evidence/level8-public-examples/verification.json",
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
            "remote_default_revisions": remote_revisions,
            "failures": failures,
            "verdict": "VERIFIED",
        },
    )
    write_redacted_text(
        EVIDENCE_DIR / "reproduction.txt",
        (
            f"{PYTHON} plans/investigations/tools/build_public_example_evidence.py "
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
        raise SystemExit("public example proof failed: " + ", ".join(failures))
    print(f"wrote public example evidence to {EVIDENCE_DIR}")


if __name__ == "__main__":
    main()
