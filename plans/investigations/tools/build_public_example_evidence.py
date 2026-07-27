"""Build checksum-complete evidence for seven ecosystem public examples."""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path
from typing import Any

from acquisition_truth_evidence_checks import verify_hostile_executor_controls
from filelock import FileLock, Timeout
from public_example_evidence_checks import evaluate_public_example_checks
from public_example_evidence_support import (
    REPRESENTATIVES,
    example_summary,
    remove_obsolete_combined_evidence,
    representative_roots,
    verify_representatives,
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
    "src/readme_agent/facts/acceptance_contract.py",
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
EVIDENCE_MACHINERY_PATHS = (
    "plans/investigations/tools/build_public_example_evidence.py",
    "plans/investigations/tools/public_example_evidence_checks.py",
    "plans/investigations/tools/public_example_evidence_support.py",
)
FOCUSED_COMMAND = (
    PYTHON,
    "-m",
    "pytest",
    "-q",
    "tests/unit/test_compiled_consumer_verifiers.py",
    "tests/unit/test_repository_examples.py",
    "tests/unit/test_local_verification.py",
    "tests/unit/test_fact_acceptance_contract.py",
    "tests/unit/test_acquisition.py",
    "tests/unit/test_acquisition_pins.py",
    "tests/unit/test_rust_consumer.py",
    "tests/security/test_example_execution_boundary.py",
    "tests/security/test_no_secrets_in_evidence.py",
)
OFFICIAL_COMMAND = (PYTHON, "scripts/governance/run_official_checks.py")
LOCK_PATH = REPO_ROOT / "runs/control/locks/public-example-evidence.lock"


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


def _write_failure(
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
        "tree_porcelain_sha256": hashlib.sha256(start_status.encode()).hexdigest(),
        "builder_path": Path(__file__).resolve().relative_to(REPO_ROOT).as_posix(),
        "builder_sha256": _sha256(Path(__file__).resolve()),
        "implementation": {
            path: _sha256(REPO_ROOT / path) for path in sorted(IMPLEMENTATION_PATHS)
        },
        "evidence_machinery": {
            path: _sha256(REPO_ROOT / path) for path in sorted(EVIDENCE_MACHINERY_PATHS)
        },
    }
    results, curated_controls = verify_representatives(REPO_ROOT)
    roots = representative_roots(REPO_ROOT)
    remote_revisions = {
        ecosystem: remote_head_sha(require_listed(org_repo).clone_url)
        for ecosystem, org_repo in REPRESENTATIVES.items()
    }
    hostile_controls = verify_hostile_executor_controls(ISOLATED_EXECUTOR_PROOF)
    focused = _run(FOCUSED_COMMAND)
    official = _run(OFFICIAL_COMMAND) if run_official else None
    checks = evaluate_public_example_checks(
        control=control,
        start_status=start_status,
        current_head=_git("rev-parse", "HEAD"),
        current_status=_git("status", "--porcelain=v1", "--untracked-files=all"),
        results=results,
        curated_controls=curated_controls,
        remote_revisions=remote_revisions,
        hostile_controls=hostile_controls,
        focused_exit_code=focused["exit_code"],
        official_exit_code=official["exit_code"] if official is not None else None,
    )
    checks["representative_revisions_stable"] = all(
        _git("rev-parse", "HEAD", root=roots[ecosystem])
        == results[ecosystem]["verification"]["source_revision"]
        for ecosystem in roots
    )
    failures = [name for name, passed in checks.items() if not passed]
    if failures:
        _write_failure(control, checks, focused, official)
        return failures

    scoreboard = derive_lifecycle_scoreboard(default_state_backend())
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    remove_obsolete_combined_evidence(EVIDENCE_DIR)
    for ecosystem, item in sorted(results.items()):
        write_redacted_json(EVIDENCE_DIR / f"{ecosystem}-verification.json", item)
    write_redacted_json(
        EVIDENCE_DIR / "example-verifications-summary.json",
        {
            "schema_version": 1,
            "representative_count": len(results),
            "records": example_summary(results),
        },
    )
    write_redacted_json(
        EVIDENCE_DIR / "curated-readme-controls.json",
        {
            "schema_version": 1,
            "principle": (
                "Treat product-agent-curated README content as high-value preferred input, but "
                "reuse no material unit until accepted evidence validates it."
            ),
            "controls": curated_controls,
        },
    )
    write_redacted_json(EVIDENCE_DIR / "remote-revisions.json", remote_revisions)
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
                    "Prove imports or namespaces, public symbols, compilation or execution, "
                    "and secret-free inputs for selected examples in the same disposable "
                    "OS-isolated executor used for acquisition proof."
                ),
            },
            "acceptance_checks_passed": [
                "Unresolved, private, uncompiled, or secret-dependent examples cannot verify",
                "Host-only compilation or execution cannot become verified",
                "Stale curated README examples are rejected instead of silently reused",
                "Filesystem, process, resource, and undeclared-network escapes fail closed",
            ],
            "proof_refs": [
                "plans/investigations/evidence/level8-public-examples/"
                "example-verifications-summary.json",
                "plans/investigations/evidence/level8-public-examples/curated-readme-controls.json",
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
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        with FileLock(LOCK_PATH, timeout=0):
            failures = _build(args.official)
    except Timeout as exc:
        raise SystemExit("public example proof already has an active sole-operator run") from exc
    if failures:
        raise SystemExit("public example proof failed: " + ", ".join(failures))
    print(f"wrote public example evidence to {EVIDENCE_DIR}")


if __name__ == "__main__":
    main()
