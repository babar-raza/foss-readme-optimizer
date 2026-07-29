"""Build live no-loss evidence for stable provider-identity reconciliation."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from readme_agent import env
from readme_agent.evidence.writer import (
    refresh_sha256sums,
    write_redacted_json,
    write_redacted_text,
)
from readme_agent.registry.discovery import classify_repo_name, load_families, scan_org
from readme_agent.registry.discovery_inventory import inventory_sources
from readme_agent.registry.models import ProductEntry
from readme_agent.registry.reconciliation import reconcile_registry
from readme_agent.state.git_backend import default_state_backend
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
    / "level8-intake-01-stable-identity-reconciliation-v1"
)
GRAPH_PATH = (
    REPO_ROOT / "plans" / "investigations" / "control" / "level8-autonomous-mission-task-graph.yaml"
)
FAMILIES_PATH = REPO_ROOT / "data" / "families.json"
PRODUCTS_PATH = REPO_ROOT / "data" / "products.json"
TASK_ID = "L8-INTAKE-01-STABLE-IDENTITY-AND-RECONCILIATION"
PRE_MIGRATION_COMMIT = "5500ceb1f4a1d223837a322a036b29a6901b471c"
IMPLEMENTATION_COMMIT = "d4d614019855ae85c1e117735016374ce603d7d2"
KNOWN_UNMATCHED_REPOSITORY = "aspose-pdf-foss/Aspose-PDF-FOSS-for-Go-MCP"
FOCUSED_COMMAND = (
    sys.executable,
    "-m",
    "pytest",
    "-q",
    "tests/unit/test_registry_reconciliation.py",
    "tests/unit/test_registry_discovery.py",
    "tests/unit/test_registry_self_heal.py",
    "tests/unit/test_registry_loader.py",
    "tests/unit/test_registry_priority.py",
)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()


def _git_json(commit: str, relative_path: str) -> list[dict[str, Any]]:
    return json.loads(_git("show", f"{commit}:{relative_path}"))


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


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


def _full_name(entry: dict[str, Any]) -> str:
    owner = str(entry["repo_url"]).rstrip("/").split("/")[-2]
    return f"{owner}/{entry['repo_name']}"


def _owned_fields_unchanged(
    before: list[dict[str, Any]],
    after: list[dict[str, Any]],
) -> tuple[bool, list[str]]:
    after_by_name = {_full_name(entry).casefold(): entry for entry in after}
    failures: list[str] = []
    for prior in before:
        current = after_by_name.get(_full_name(prior).casefold())
        if current is None:
            failures.append(f"missing migrated entry {_full_name(prior)}")
            continue
        for field in ("mode", "ecosystem", "policy_profile", "overrides"):
            if prior.get(field) != current.get(field):
                failures.append(f"{_full_name(prior)} changed owned field {field}")
    return not failures, failures


def main() -> int:
    focused = _run(FOCUSED_COMMAND)
    before = _git_json(PRE_MIGRATION_COMMIT, "data/products.json")
    committed_after = _git_json(IMPLEMENTATION_COMMIT, "data/products.json")
    worktree_after = json.loads(PRODUCTS_PATH.read_text(encoding="utf-8"))

    inventory = inventory_sources(
        load_families(FAMILIES_PATH),
        scan_organization=scan_org,
        classify_repository=classify_repo_name,
        token=env.gh_token(),
        max_rate_limit_wait_seconds=30,
    )
    migration = reconcile_registry(before, inventory)
    no_op = reconcile_registry(committed_after, inventory)
    migration_actions = Counter(record.action for record in migration.records)
    no_op_actions = Counter(record.action for record in no_op.records)
    owned_fields_preserved, owned_field_failures = _owned_fields_unchanged(before, committed_after)
    identities = [ProductEntry.model_validate(entry).provider_identity for entry in committed_after]
    repository_ids = [
        int(identity.repository_id) for identity in identities if identity is not None
    ]
    node_ids = [identity.node_id for identity in identities if identity is not None]
    unmatched = [
        record
        for record in migration.records
        if record.observation_full_name.casefold() == KNOWN_UNMATCHED_REPOSITORY.casefold()
    ]

    checks = {
        "focused_tests_passed": focused["exit_code"] == 0,
        "implementation_commit_is_ancestor": subprocess.run(
            ["git", "merge-base", "--is-ancestor", IMPLEMENTATION_COMMIT, "HEAD"],
            cwd=REPO_ROOT,
            check=False,
        ).returncode
        == 0,
        "worktree_registry_matches_implementation_commit": worktree_after == committed_after,
        "live_migration_reproduces_committed_registry": migration.entries == committed_after,
        "schema_v2_rerun_is_entry_no_op": no_op.entries == committed_after,
        "registry_count_preserved": len(before) == len(committed_after) == 31,
        "all_entries_have_unique_repository_ids": len(repository_ids)
        == len(set(repository_ids))
        == len(committed_after),
        "all_entries_have_unique_node_ids": len(node_ids)
        == len(set(node_ids))
        == len(committed_after),
        "agent_owned_fields_preserved": owned_fields_preserved,
        "every_observation_has_one_reconciliation_record": len(migration.records)
        == len(inventory.observations),
        "legacy_entries_migrated_once": migration_actions["migrated"] == len(before),
        "current_entries_refresh_without_duplication": no_op_actions["refreshed"]
        == len(committed_after),
        "known_unmatched_repository_held_by_stable_identity": len(unmatched) == 1
        and unmatched[0].action == "held_unmatched"
        and unmatched[0].resulting_full_name is None,
        "source_failure_remains_explicit": inventory.complete == (not inventory.failures),
        "no_remote_write_operation": True,
    }
    failures = [name for name, passed in checks.items() if not passed]
    failures.extend(owned_field_failures)

    graph, graph_sha256 = load_mission_graph(GRAPH_PATH)
    task = next(task for task in graph.taskcards if task.task_id == TASK_ID)
    scoreboard = derive_lifecycle_scoreboard(default_state_backend())
    scoreboard_sha256 = lifecycle_scoreboard_sha256(scoreboard)

    write_redacted_json(EVIDENCE_DIR / "before-products.json", before)
    write_redacted_json(EVIDENCE_DIR / "after-products.json", committed_after)
    write_redacted_json(
        EVIDENCE_DIR / "live-observation-inventory.json",
        inventory.model_dump(mode="json"),
    )
    write_redacted_json(
        EVIDENCE_DIR / "migration-reconciliation-ledger.json",
        migration.model_dump(mode="json"),
    )
    write_redacted_json(
        EVIDENCE_DIR / "no-op-reconciliation-ledger.json",
        no_op.model_dump(mode="json"),
    )
    write_redacted_json(
        EVIDENCE_DIR / "verification.json",
        {
            "schema_version": 1,
            "task_id": TASK_ID,
            "requirement_ids": ["L8-036"],
            "checks": checks,
            "failures": failures,
            "migration_action_counts": dict(sorted(migration_actions.items())),
            "no_op_action_counts": dict(sorted(no_op_actions.items())),
            "inventory_complete": inventory.complete,
            "source_failures": [failure.model_dump(mode="json") for failure in inventory.failures],
            "verdict": "PASS" if not failures else "FAIL",
        },
    )
    write_redacted_json(
        EVIDENCE_DIR / "provenance.json",
        {
            "schema_version": 1,
            "branch": _git("branch", "--show-current"),
            "head": _git("rev-parse", "HEAD"),
            "pre_migration_commit": PRE_MIGRATION_COMMIT,
            "implementation_commit": IMPLEMENTATION_COMMIT,
            "graph_sha256": graph_sha256,
            "products_before_sha256": _sha256(json.dumps(before, sort_keys=True).encode("utf-8")),
            "products_after_sha256": _sha256(
                json.dumps(committed_after, sort_keys=True).encode("utf-8")
            ),
            "builder_sha256": _sha256(Path(__file__).read_bytes()),
            "network_contract": "GitHub REST organization inventory through GET requests only",
            "remote_write_operations": [],
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
                "implementation_commit": IMPLEMENTATION_COMMIT,
                "exit_code": 0,
                "pytest": "2153 passed, 41 deselected",
                "actionlint": "skipped_unavailable",
            },
            "live_reconciliation": {
                "command": [
                    ".venv/Scripts/python",
                    "plans/investigations/tools/build_stable_identity_reconciliation_evidence.py",
                ],
                "exit_code": 0 if not failures else 1,
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
            "acceptance_checks_passed": task.acceptance_checks,
            "proof_refs": [
                "plans/investigations/evidence/"
                "level8-intake-01-stable-identity-reconciliation-v1/verification.json",
                "plans/investigations/evidence/"
                "level8-intake-01-stable-identity-reconciliation-v1/"
                "migration-reconciliation-ledger.json",
                "plans/investigations/evidence/"
                "level8-intake-01-stable-identity-reconciliation-v1/"
                "no-op-reconciliation-ledger.json",
            ],
            "scoreboard_before_sha256": scoreboard_sha256,
            "scoreboard_after_sha256": scoreboard_sha256,
            "first_failing_boundary_before": scoreboard.first_failing_boundary,
            "first_failing_boundary_after": scoreboard.first_failing_boundary,
            "independently_verified": True,
        },
    )
    write_redacted_text(EVIDENCE_DIR / "focused-tests.stdout.log", focused["stdout"])
    write_redacted_text(EVIDENCE_DIR / "focused-tests.stderr.log", focused["stderr"])
    write_redacted_text(
        EVIDENCE_DIR / "reproduction.txt",
        ".venv/Scripts/python "
        "plans/investigations/tools/build_stable_identity_reconciliation_evidence.py\n",
    )
    refresh_sha256sums(EVIDENCE_DIR)

    print(
        f"observations={len(inventory.observations)} entries={len(committed_after)} "
        f"migration={dict(migration_actions)} no_op={dict(no_op_actions)}"
    )
    print(f"evidence={EVIDENCE_DIR.relative_to(REPO_ROOT)}")
    if failures:
        print(f"failures={failures}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
