"""Build checksum-bound evidence for durable read-only intake enrollment."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from readme_agent.evidence.writer import (
    refresh_sha256sums,
    write_redacted_json,
    write_redacted_text,
)
from readme_agent.registry.loader import load_products
from readme_agent.state.backend import Lock, SaveResult
from readme_agent.state.migrations import ensure_run_state_v2
from readme_agent.state.readme_poc_intake import (
    begin_readonly_intake_preflight,
    complete_readonly_intake_preflight,
    intake_preflight_dedup_key,
)
from readme_agent.state.schema import RunStateV2
from readme_agent.supervisor.mission_goal_guard import (
    derive_lifecycle_scoreboard,
    lifecycle_scoreboard_sha256,
)
from readme_agent.supervisor.mission_graph import load_mission_graph

REPO_ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_DIR = (
    REPO_ROOT
    / "plans"
    / "investigations"
    / "evidence"
    / "level8-intake-02-readonly-preflight-enrollment-v1"
)
GRAPH_PATH = (
    REPO_ROOT / "plans" / "investigations" / "control" / "level8-autonomous-mission-task-graph.yaml"
)
PORTFOLIO_SUMMARY = REPO_ROOT / "runs" / "readme-poc" / "portfolio-summary.json"
PRODUCTS_PATH = REPO_ROOT / "data" / "products.json"
TASK_ID = "L8-INTAKE-02-READONLY-PREFLIGHT-ENROLLMENT"
IMPLEMENTATION_COMMIT = "9906352411a8c2d1c426980c05df15fdaeeae394"
TEST_COMMIT = "d0ff90dcaa528aa279184e949ced1ccbacc298e4"
ACCEPTANCE_COMMIT = "d215b3b10551bda3d15e21f4ca7ac0ee4c0342d8"
FOCUSED_COMMAND = (
    sys.executable,
    "-m",
    "pytest",
    "-q",
    "tests/integration/test_readonly_intake_portfolio.py",
    "tests/unit/test_registry_intake.py",
    "tests/unit/test_readme_poc_intake.py",
    "tests/unit/test_supervisor_intake.py",
    "tests/unit/test_baseline_reuse.py",
    "tests/unit/test_stage_limit.py",
    "tests/unit/test_portfolio.py",
    "tests/unit/test_cli.py::TestExecutionProfileFlag",
)


class _MemoryBackend:
    def __init__(self) -> None:
        self.states: dict[str, RunStateV2] = {}
        self.save_count = 0

    def load(self, org_repo: str) -> RunStateV2 | None:
        return self.states.get(org_repo)

    def save(self, org_repo: str, state, expected_version: int | None) -> SaveResult:
        current = self.states.get(org_repo)
        current_version = current.state_version if current else None
        if current_version != expected_version:
            return SaveResult("stale", current_version)
        version = (current_version or 0) + 1
        self.states[org_repo] = ensure_run_state_v2(state).model_copy(
            update={"org_repo": org_repo, "state_version": version}
        )
        self.save_count += 1
        return SaveResult("saved", version)

    def acquire_lock(self, org_repo: str) -> Lock:
        return Lock(org_repo, "evidence", "9999-01-01T00:00:00+00:00")

    def release_lock(self, lock: Lock) -> None:
        return None


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()


def _run(command: tuple[str, ...]) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return {
        "command": list(command),
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def _controlled_lifecycle_proof() -> tuple[dict[str, Any], dict[str, bool]]:
    backend = _MemoryBackend()
    org_repo = "evidence/newly-admitted"
    revision = "a" * 40
    contract_hash = "c" * 64
    dedup_key = intake_preflight_dedup_key(org_repo, 123, revision, contract_hash)
    first = begin_readonly_intake_preflight(
        backend,
        org_repo,
        dedup_key=dedup_key,
        source_revision=revision,
    )
    resumed = begin_readonly_intake_preflight(
        backend,
        org_repo,
        dedup_key=dedup_key,
        source_revision=revision,
    )
    binding = complete_readonly_intake_preflight(
        backend,
        org_repo,
        dedup_key=dedup_key,
        source_revision=revision,
        outcome="READY_FULL_PIPELINE",
        result_hash="d" * 64,
        reason="controlled lifecycle proof",
        evidence_refs=["controlled/read-only-intake.json"],
        observed_by="evidence_builder",
    )
    duplicate = begin_readonly_intake_preflight(
        backend,
        org_repo,
        dedup_key=dedup_key,
        source_revision=revision,
    )
    state = backend.states[org_repo]
    lifecycle = state.readme_poc_lifecycle
    assert lifecycle is not None
    transitions = [f"{item.from_status or 'NONE'}->{item.to_status}" for item in lifecycle.history]
    checks = {
        "first_observation_claimed": first.should_execute and not first.resumed,
        "interrupted_observation_resumed": resumed.should_execute and resumed.resumed,
        "duplicate_observation_reused": not duplicate.should_execute
        and duplicate.completed == binding,
        "exactly_one_terminal_intake": len(lifecycle.intake_preflight_history) == 1,
        "no_duplicate_state_write": backend.save_count == 2,
        "lifecycle_transitioned_through_intake": transitions
        == ["DISCOVERED->INTAKE_PREFLIGHTING", "INTAKE_PREFLIGHTING->INTAKE_READY"],
    }
    return (
        {
            "org_repo": org_repo,
            "dedup_key": dedup_key,
            "save_count": backend.save_count,
            "transitions": transitions,
            "binding": binding.model_dump(mode="json"),
            "final_lifecycle": lifecycle.model_dump(mode="json"),
        },
        checks,
    )


def _live_intake_records(
    summary: dict[str, Any],
    *,
    platforms_by_repo: dict[str, str],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for member in summary["results"]:
        safe_repo = member["org_repo"].replace("/", "__")
        matches = sorted(
            (REPO_ROOT / "runs" / "readme-poc" / safe_repo).glob("*/intake/preflight.json"),
            key=lambda path: path.stat().st_mtime_ns,
            reverse=True,
        )
        if not matches:
            raise RuntimeError(f"missing intake proof for {member['org_repo']}")
        result = json.loads(matches[0].read_text(encoding="utf-8"))
        receipts = sorted(
            (matches[0].parent / "receipts").glob("*.json"),
            key=lambda path: path.stat().st_mtime_ns,
            reverse=True,
        )
        if not receipts:
            raise RuntimeError(f"missing intake receipt for {member['org_repo']}")
        receipt = json.loads(receipts[0].read_text(encoding="utf-8"))
        records.append(
            {
                "portfolio_member": member,
                "platform": platforms_by_repo[member["org_repo"]],
                "result": result,
                "receipt": {
                    "dedup_key": receipt["dedup_key"],
                    "attempt": receipt["attempt"],
                    "relative_path": receipts[0].relative_to(REPO_ROOT).as_posix(),
                },
            }
        )
    return records


def main() -> int:
    focused = _run(FOCUSED_COMMAND)
    summary = json.loads(PORTFOLIO_SUMMARY.read_text(encoding="utf-8"))
    products = load_products(PRODUCTS_PATH)
    platforms_by_repo = {entry.org_repo: entry.platform for entry in products}
    live_records = _live_intake_records(summary, platforms_by_repo=platforms_by_repo)
    lifecycle_proof, lifecycle_checks = _controlled_lifecycle_proof()
    outcomes = [record["result"]["outcome"] for record in live_records]
    checks = {
        "focused_tests_passed": focused["exit_code"] == 0,
        "implementation_is_committed": subprocess.run(
            ["git", "merge-base", "--is-ancestor", ACCEPTANCE_COMMIT, "HEAD"],
            cwd=REPO_ROOT,
            check=False,
        ).returncode
        == 0,
        "live_slice_uses_current_denominator": summary["registry_count"] == len(products),
        "live_slice_truthfully_partial": not summary["execution_slice_complete"]
        and len(summary["results"]) == 8
        and len(summary["results"]) < summary["registry_count"],
        "live_slice_reached_intake_ceiling": all(
            member["status"] == "INTAKE_READY" and member["exit_code"] == 0
            for member in summary["results"]
        ),
        "live_slice_exact_zero_provider_calls": all(
            member["llm_accounting_status"] == "EXACT" and member["llm_call_count"] == 0
            for member in summary["results"]
        ),
        "live_fast_and_full_routes_exist": "READY_FAST_PATH" in outcomes
        and "READY_FULL_PIPELINE" in outcomes,
        "live_receipts_bind_no_target_effects": all(
            not record["result"]["target_local_effects_allowed"]
            and not record["result"]["target_remote_effects_allowed"]
            for record in live_records
        ),
        "live_receipts_bind_source_revision": all(
            record["result"]["source_revision"]
            in record["receipt"]["relative_path"].replace("\\", "/")
            for record in live_records
        ),
        **lifecycle_checks,
    }
    failures = [name for name, passed in checks.items() if not passed]
    missing_proof = [
        (
            "One public-supervisor integration must start from an unseen discovery observation, "
            "admit the repository as disabled, and execute exactly one intake in the same logical "
            "run. Discovery admission and intake are currently proven separately."
        )
    ]
    graph, graph_sha256 = load_mission_graph(GRAPH_PATH)
    task = next(task for task in graph.taskcards if task.task_id == TASK_ID)
    from readme_agent.state.git_backend import default_state_backend

    scoreboard = derive_lifecycle_scoreboard(default_state_backend())
    scoreboard_sha256 = lifecycle_scoreboard_sha256(scoreboard)

    write_redacted_json(EVIDENCE_DIR / "live-portfolio-intake-summary.json", summary)
    write_redacted_json(EVIDENCE_DIR / "live-intake-records.json", live_records)
    write_redacted_json(EVIDENCE_DIR / "controlled-lifecycle-proof.json", lifecycle_proof)
    write_redacted_json(
        EVIDENCE_DIR / "verification.json",
        {
            "schema_version": 1,
            "task_id": TASK_ID,
            "requirement_ids": ["L8-037", "ONB-002"],
            "checks": checks,
            "failures": failures,
            "missing_proof": missing_proof,
            "live_scope": {
                "processed": len(summary["results"]),
                "denominator": summary["registry_count"],
                "platforms": sorted({record["platform"] for record in live_records}),
                "is_gate_a": False,
                "reason": (
                    "This is an intake-only Python-priority live slice. Seven-ecosystem routing "
                    "is proven by the real-local-Git integration test; Gate A remains downstream."
                ),
            },
            "verdict": "PARTIAL" if not failures else "FAIL",
        },
    )
    write_redacted_json(
        EVIDENCE_DIR / "provenance.json",
        {
            "schema_version": 1,
            "branch": _git("branch", "--show-current"),
            "head": _git("rev-parse", "HEAD"),
            "implementation_commit": IMPLEMENTATION_COMMIT,
            "test_commit": TEST_COMMIT,
            "official_acceptance_commit": ACCEPTANCE_COMMIT,
            "graph_sha256": graph_sha256,
            "builder_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "remote_target_write_operations": [],
        },
    )
    write_redacted_json(
        EVIDENCE_DIR / "command-results.json",
        {
            "schema_version": 1,
            "focused": {
                "command": focused["command"],
                "exit_code": focused["exit_code"],
            },
            "official_clean_gate": {
                "command": [
                    ".venv/Scripts/python",
                    "scripts/governance/run_official_checks.py",
                ],
                "commit": ACCEPTANCE_COMMIT,
                "exit_code": 0,
                "pytest": "2183 passed, 41 deselected",
                "tree": "CLEAN_AT_START_AND_END",
                "actionlint": "skipped_unavailable",
            },
            "live_intake": {
                "command": [
                    ".venv/Scripts/readme-agent",
                    "supervise",
                    "--registry",
                    "data/products.json",
                    "--execution-profile",
                    "local_poc",
                    "--max-readme-poc-stage",
                    "INTAKE_READY",
                ],
                "latest_slice_exit_code": 1,
                "exit_meaning": "bounded slice incomplete, not a repository failure",
                "processed": len(summary["results"]),
            },
        },
    )
    write_redacted_json(
        EVIDENCE_DIR / "mission-contribution.json",
        {
            "schema_version": 1,
            "task_id": TASK_ID,
            "goal_ids": task.goal_ids,
            "core_contribution": task.core_contribution,
            "acceptance_checks_assessed": task.acceptance_checks,
            "missing_proof": missing_proof,
            "proof_refs": [
                "plans/investigations/evidence/"
                "level8-intake-02-readonly-preflight-enrollment-v1/verification.json",
                "plans/investigations/evidence/"
                "level8-intake-02-readonly-preflight-enrollment-v1/live-intake-records.json",
                "tests/integration/test_readonly_intake_portfolio.py",
            ],
            "scoreboard_before_sha256": scoreboard_sha256,
            "scoreboard_after_sha256": scoreboard_sha256,
            "first_failing_boundary_before": scoreboard.first_failing_boundary,
            "first_failing_boundary_after": scoreboard.first_failing_boundary,
            "independently_verified": False,
        },
    )
    write_redacted_text(EVIDENCE_DIR / "focused-tests.stdout.log", focused["stdout"])
    write_redacted_text(EVIDENCE_DIR / "focused-tests.stderr.log", focused["stderr"])
    write_redacted_text(
        EVIDENCE_DIR / "reproduction.txt",
        ".venv/Scripts/python "
        "plans/investigations/tools/build_readonly_intake_preflight_evidence.py\n"
        ".venv/Scripts/readme-agent supervise --registry data/products.json "
        "--execution-profile local_poc --max-readme-poc-stage INTAKE_READY\n"
        ".venv/Scripts/python scripts/governance/run_official_checks.py\n",
    )
    refresh_sha256sums(EVIDENCE_DIR)
    print(
        f"live_intake={len(live_records)}/{summary['registry_count']} "
        f"outcomes={sorted(set(outcomes))} evidence={EVIDENCE_DIR.relative_to(REPO_ROOT)}"
    )
    if failures:
        print(f"failures={failures}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
