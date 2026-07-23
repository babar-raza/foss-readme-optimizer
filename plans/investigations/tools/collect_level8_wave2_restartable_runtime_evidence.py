# governed_by: plans/master.md + plans/requirements.md + plans/GOVERNANCE.md
# artifact_role: Wave-2 reproducible acceptance-evidence producer
"""Run Wave-2 acceptance gates and write one checksum-complete evidence bundle."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_EVIDENCE_DIR = (
    REPO_ROOT
    / "plans"
    / "investigations"
    / "evidence"
    / "level8-wave2-restartable-actions-2026-07-23"
)
WAVE2_BASELINE_HEAD = "eed220fb3cdb1d2b558c4f3e3d73694e023845b0"
CHECKPOINT_STAGES = (
    "trigger_accepted",
    "run_started",
    "snapshot_captured",
    "profile_completed",
    "task_started",
    "task_completed",
    "verifier_result",
    "repair_plan",
    "effect_pending",
    "effect_applied",
    "final_acceptance",
)
EVIDENCE_FILENAMES = {
    "act-plan-job-output.log",
    "act-queue-compatibility-transform.json",
    "complete-non-live-test-suite.log",
    "official-static-quality-gates.log",
    "repository-snapshot.json",
    "sha256sums.txt",
    "wave2-committed-implementation.diff",
    "wave2-local-acceptance-summary.json",
    "wave2-runtime-fault-and-contract-tests.log",
    *{f"checkpoint-recovery-{stage.replace('_', '-')}.json" for stage in CHECKPOINT_STAGES},
}


def _run(command: list[str], *, timeout_seconds: int) -> dict:
    started = datetime.now(UTC)
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout_seconds,
        check=False,
    )
    return {
        "command": command,
        "return_code": completed.returncode,
        "started_at": started.isoformat(),
        "finished_at": datetime.now(UTC).isoformat(),
        "output": completed.stdout,
    }


def _write_log(path: Path, results: list[dict]) -> None:
    sections = []
    for result in results:
        command = subprocess.list2cmdline(result["command"])
        sections.append(
            f"$ {command}\n"
            f"return_code={result['return_code']}\n"
            f"started_at={result['started_at']}\n"
            f"finished_at={result['finished_at']}\n\n"
            f"{result['output'].rstrip()}\n"
        )
    path.write_text("\n".join(sections), encoding="utf-8", newline="\n")


def _sha256(path: Path) -> str:
    raw = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(raw).hexdigest()


def _gh_resource(path: str, list_field: str) -> dict:
    result = _run(["gh", "api", path], timeout_seconds=30)
    if result["return_code"] != 0:
        return {"accessible": False, "error": result["output"].strip()}
    payload = json.loads(result["output"])
    return {
        "accessible": True,
        "names": sorted(item["name"] for item in payload.get(list_field, [])),
    }


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


def _prepare_evidence_dir(evidence_dir: Path) -> None:
    governed_root = (REPO_ROOT / "plans" / "investigations" / "evidence").resolve()
    if evidence_dir.parent != governed_root or not evidence_dir.name.startswith(
        "level8-wave2-restartable-actions-"
    ):
        raise RuntimeError(f"refusing to replace evidence outside {governed_root}")
    evidence_dir.mkdir(parents=True, exist_ok=True)
    for path in evidence_dir.iterdir():
        if not path.is_file() or path.name not in EVIDENCE_FILENAMES:
            raise RuntimeError(f"refusing to replace unexpected evidence artifact {path}")
        path.unlink()


def main() -> int:
    evidence_dir = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_EVIDENCE_DIR
    _prepare_evidence_dir(evidence_dir)
    python = str(REPO_ROOT / ".venv" / "Scripts" / "python.exe")
    _run(
        [
            python,
            "plans/investigations/tools/reproduce_production_workflow_with_act_compatibility.py",
            "--evidence-dir",
            str(evidence_dir),
        ],
        timeout_seconds=900,
    )

    official_commands = [
        [python, "-m", "ruff", "check", "."],
        [python, "-m", "ruff", "format", "--check", "."],
        [python, "-m", "mypy", "src"],
        ["actionlint"],
        [python, "scripts/governance/validate_plan_structure.py"],
        [python, "plans/investigations/tools/extract_requirements.py", "--check"],
        [python, "plans/investigations/tools/coverage_classify.py", "--check"],
        [
            python,
            "scripts/governance/build_level8_requirement_taskcard_coverage.py",
            "--check",
        ],
    ]
    official_results = [_run(command, timeout_seconds=180) for command in official_commands]
    _write_log(evidence_dir / "official-static-quality-gates.log", official_results)

    fault_test_command = [
        python,
        "-m",
        "pytest",
        "-vv",
        "tests/unit/test_lifecycle_state.py",
        "tests/unit/test_retry.py",
        "tests/unit/test_production_workflow.py",
        "tests/unit/test_commands_lifecycle.py",
        "tests/unit/test_cli.py::TestExecutionProfileFlag",
        "tests/unit/test_effect_ledger.py::TestDuplicateTriggerEffectComposition",
        "tests/unit/test_effect_ledger.py::TestLifecycleEffectCheckpointRecovery",
        "tests/unit/test_supervisor_loop.py::TestEvidenceCompletenessGate",
    ]
    fault_result = _run(fault_test_command, timeout_seconds=240)
    fault_log = evidence_dir / "wave2-runtime-fault-and-contract-tests.log"
    _write_log(fault_log, [fault_result])
    for stage in CHECKPOINT_STAGES:
        test_node_fragment = (
            f"test_crash_after_every_checkpoint_resumes_on_the_same_logical_trigger[{stage}] PASSED"
        )
        if test_node_fragment not in fault_result["output"]:
            raise RuntimeError(f"checkpoint recovery proof did not pass for {stage!r}")
        checkpoint_evidence = {
            "schema_version": 1,
            "checkpoint_stage": stage,
            "injected_failure_boundary": f"immediately_after_persisting_{stage}",
            "recovery_result": "same_logical_trigger_resumed_and_completed",
            "resume_strategy": "canonical_restart_with_idempotent_reconciliation",
            "stage_directed_skip_proven": False,
            "test_node_fragment": test_node_fragment,
            "source_log": fault_log.name,
        }
        (evidence_dir / f"checkpoint-recovery-{stage.replace('_', '-')}.json").write_text(
            json.dumps(checkpoint_evidence, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )

    full_test_result = _run(
        [python, "-m", "pytest", "-q"],
        timeout_seconds=1_200,
    )
    _write_log(evidence_dir / "complete-non-live-test-suite.log", [full_test_result])

    head_result = _run(["git", "rev-parse", "HEAD"], timeout_seconds=30)
    status_result = _run(["git", "status", "--short"], timeout_seconds=30)
    diff_result = _run(
        ["git", "diff", "--binary", f"{WAVE2_BASELINE_HEAD}..HEAD", "--", "."],
        timeout_seconds=120,
    )
    if diff_result["return_code"] != 0:
        raise RuntimeError(f"could not capture committed Wave-2 diff: {diff_result['output']}")
    (evidence_dir / "wave2-committed-implementation.diff").write_text(
        diff_result["output"],
        encoding="utf-8",
        newline="\n",
    )
    changed_paths_result = _run(
        ["git", "diff", "--name-status", f"{WAVE2_BASELINE_HEAD}..HEAD", "--", "."],
        timeout_seconds=30,
    )
    remote_result = _run(
        ["gh", "repo", "view", "--json", "nameWithOwner"],
        timeout_seconds=30,
    )
    remote_repo = (
        json.loads(remote_result["output"])["nameWithOwner"]
        if remote_result["return_code"] == 0
        else None
    )
    repository_snapshot = {
        "captured_at": datetime.now(UTC).isoformat(),
        "baseline_head": WAVE2_BASELINE_HEAD,
        "head": head_result["output"].strip(),
        "status": status_result["output"].splitlines(),
        "committed_changed_paths": changed_paths_result["output"].splitlines(),
        "production_workflow_sha256": _sha256(
            REPO_ROOT / ".github" / "workflows" / "readme-agent-production.yml"
        ),
        "requirements_sha256": _sha256(REPO_ROOT / "plans" / "requirements.md"),
        "mission_graph_sha256": _sha256(
            REPO_ROOT
            / "plans"
            / "investigations"
            / "control"
            / "level8-autonomous-mission-task-graph.yaml"
        ),
        "local_environment_presence_only": {
            name: bool(os.environ.get(name))
            for name in (
                "GH_APP_CLIENT_ID",
                "GH_APP_PRIVATE_KEY",
                "LLM_BASE_URL",
                "LLM_API_KEY",
                "DEAD_MAN_HEARTBEAT_URL",
                "README_AGENT_GITHUB_APP_TOKEN",
            )
        },
        "remote_repository": remote_repo,
        "remote_actions_variables": (
            _gh_resource(f"repos/{remote_repo}/actions/variables", "variables")
            if remote_repo
            else {"accessible": False, "error": "remote repository identity unavailable"}
        ),
        "remote_actions_secrets": (
            _gh_resource(f"repos/{remote_repo}/actions/secrets", "secrets")
            if remote_repo
            else {"accessible": False, "error": "remote repository identity unavailable"}
        ),
    }
    (evidence_dir / "repository-snapshot.json").write_text(
        json.dumps(repository_snapshot, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    act_result_path = evidence_dir / "act-queue-compatibility-transform.json"
    act_result = (
        json.loads(act_result_path.read_text(encoding="utf-8"))
        if act_result_path.exists()
        else {"return_code": None}
    )
    all_results = [*official_results, fault_result, full_test_result]
    summary = {
        "schema_version": 1,
        "producer": str(Path(__file__).relative_to(REPO_ROOT)).replace("\\", "/"),
        "generated_at": datetime.now(UTC).isoformat(),
        "wave": "Wave 2 — Restartable GitHub Actions runtime",
        "production_like_act_plan_job_return_code": act_result.get("return_code"),
        "official_static_quality_gates_passed": all(
            result["return_code"] == 0 for result in official_results
        ),
        "runtime_fault_and_contract_tests_passed": fault_result["return_code"] == 0,
        "complete_non_live_test_suite_passed": full_test_result["return_code"] == 0,
        "all_local_acceptance_gates_passed": (
            act_result.get("return_code") == 0
            and all(result["return_code"] == 0 for result in all_results)
        ),
        "external_proof_still_required": [
            "real GitHub Actions run with installed GitHub App and repository secrets",
            "external dead-man endpoint heartbeat and absence alert",
            "production scheduler recovery observed after an injected interruption",
        ],
    }
    (evidence_dir / "wave2-local-acceptance-summary.json").write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    _refresh_checksums(evidence_dir)
    print(json.dumps(summary, indent=2))
    return 0 if summary["all_local_acceptance_gates_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
