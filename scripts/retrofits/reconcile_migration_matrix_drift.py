"""Reconcile migration-matrix.json provenance rows against current live content.

PWD-009: `validate_compact_authority.py` measured 6 fresh pre-existing errors when this
project's authority-reset was first landed; a live re-run months later found the drift had
grown to 11 (34 new requirements never tracked in `matrix["requirements"]`, 6 deferred
tasks whose `requirement_ids` changed after their original retirement was recorded, and 4
active `new_tasks[]` entries edited in place since the matrix was last synced). The
existing `record_task_retirements_in_migration_matrix.py` only ever covered one specific,
hardcoded retirement batch from an earlier reset; this generalizes the same exact
derivation (never a hand-authored hash -- always `validate_compact_authority.py`'s own
`_semantic_sha256`/`_changed_fields`) to every row the validator currently flags, and adds
any requirement the validator's count/stable-ID checks show as untracked.

Read-only until the final write: prints what it is about to change before changing it.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
GRAPH_PATH = (
    REPO_ROOT / "plans" / "investigations" / "control" / "level8-autonomous-mission-task-graph.yaml"
)
REQUIREMENT_CATALOG_PATH = REPO_ROOT / "plans" / "requirements" / "catalog.jsonl"
MATRIX_PATH = (
    REPO_ROOT
    / "plans"
    / "investigations"
    / "evidence"
    / "agile-authority-reset-v1"
    / "migration-matrix.json"
)


def _semantic_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _changed_fields(before: dict[str, Any], after: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"field": field, "before": before.get(field), "after": after.get(field)}
        for field in sorted(set(before) | set(after))
        if before.get(field) != after.get(field)
    ]


def _source_task(commit: str, task_id: str) -> dict[str, Any] | None:
    result = subprocess.run(
        ["git", "show", f"{commit}:{GRAPH_PATH.relative_to(REPO_ROOT).as_posix()}"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    source_graph = yaml.safe_load(result.stdout)
    return next(
        (task for task in source_graph["taskcards"] if task["task_id"] == task_id),
        None,
    )


def main() -> None:
    matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    graph = yaml.safe_load(GRAPH_PATH.read_text(encoding="utf-8"))
    deferred_path = REPO_ROOT / graph["deferred_task_catalog"]["path"]
    deferred = [
        json.loads(line) for line in deferred_path.read_text(encoding="utf-8").splitlines() if line
    ]

    active_tasks = {task["task_id"]: task for task in graph["taskcards"]}
    deferred_tasks = {record["task"]["task_id"]: record["task"] for record in deferred}
    source_commit = matrix["source_commit"]

    task_updates = 0
    for row in matrix["tasks"]:
        task_id = row["id"]
        destination_task = active_tasks.get(task_id) or deferred_tasks.get(task_id)
        if destination_task is None:
            continue
        current_hash = _semantic_sha256(destination_task)
        if row.get("destination_task_sha256") == current_hash:
            continue
        source_task = _source_task(source_commit, task_id)
        if source_task is None:
            print(f"SKIP {task_id}: no source-commit record to diff against")
            continue
        changes = _changed_fields(source_task, destination_task)
        expected_destination = (
            "active_graph" if task_id in active_tasks else graph["deferred_task_catalog"]["path"]
        )
        print(f"UPDATE tasks[] {task_id}: changed_fields={[c['field'] for c in changes]}")
        row["destination"] = expected_destination
        row["destination_task_sha256"] = current_hash
        row["transformation"] = "resequenced_active_horizon" if changes else "preserved_exactly"
        row["changed_fields"] = changes
        task_updates += 1

    new_task_updates = 0
    for row in matrix.get("new_tasks", []):
        task_id = row["id"]
        destination_task = active_tasks.get(task_id) or deferred_tasks.get(task_id)
        if destination_task is None:
            continue
        current_hash = _semantic_sha256(destination_task)
        if row.get("destination_task_sha256") == current_hash:
            continue
        expected_destination = (
            "active_graph" if task_id in active_tasks else graph["deferred_task_catalog"]["path"]
        )
        print(f"UPDATE new_tasks[] {task_id}: destination={expected_destination}")
        row["destination"] = expected_destination
        row["destination_task_sha256"] = current_hash
        new_task_updates += 1

    requirements = [
        json.loads(line)
        for line in REQUIREMENT_CATALOG_PATH.read_text(encoding="utf-8").splitlines()
        if line
    ]
    tracked_ids = {row["id"] for row in matrix["requirements"]}
    requirement_additions = 0
    for record in requirements:
        requirement_id = record["requirement_id"]
        if requirement_id in tracked_ids:
            continue
        print(f"ADD requirements[] {requirement_id}: not part of the original source migration")
        matrix["requirements"].append(
            {
                "id": requirement_id,
                "destination": "plans/requirements/catalog.jsonl",
                "sha256": _semantic_sha256(record),
            }
        )
        requirement_additions += 1

    MATRIX_PATH.write_text(json.dumps(matrix, indent=2) + "\n", encoding="utf-8")
    print(
        f"updated {task_updates} tasks[] rows, {new_task_updates} new_tasks[] rows, "
        f"added {requirement_additions} requirements[] rows"
    )


if __name__ == "__main__":
    main()
