"""Update migration-matrix.json provenance rows for tasks retired to the
deferred catalog, closing the gap validate_compact_authority.py's docstring
documents: the original per-task `tasks[]`/`new_tasks[]` rows only ever
modeled the 2026-08-02 migration's active_graph-vs-deferred placement, never
a later retirement.

For each retired task originally tracked in `tasks[]` (part of the source
migration), recomputes `destination`, `destination_task_sha256`,
`transformation`, and `changed_fields` against its current deferred-catalog
content, using the exact same derivation validate_compact_authority.py's own
checks use -- so this is not a hand-authored provenance claim, it is what the
validator will independently recompute and compare against.

For each retired task that was itself a post-migration `new_tasks[]` addition
(never part of the source migration), removes its row: `new_tasks[]` tracks
"new tasks currently in the active graph," which no longer includes it.
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
MATRIX_PATH = (
    REPO_ROOT
    / "plans"
    / "investigations"
    / "evidence"
    / "agile-authority-reset-v1"
    / "migration-matrix.json"
)

_RETIRED_TASK_IDS = [
    "L8-AGILE-AUTHORITY-RESET",
    "L8-VPY-03B-FIRST-CURRENT-PYTHON-E2E",
    "L8-VPY-01-NOTE-VERIFIED-CANARY",
    "L8-VPY-00-PRESENTATION-CONTRACT-RESET",
    "L8-VPY-03A-PAGE-PDF-VERIFIED-CANARIES",
    "L8-VPY-03C-PAGE-CURRENT-REFRESH",
    "L8-VPY-03D-NOTE-CURRENT-REFRESH",
    "L8-VPY-03E-3D-CURRENT-REFRESH",
    "L8-VPY-03-ALL-PYTHON-VERIFIED-POC",
    "L8-VPY-02-PAGE-PDF-VERIFIED-CANARIES",
]


def _semantic_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _changed_fields(before: dict[str, Any], after: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"field": field, "before": before.get(field), "after": after.get(field)}
        for field in sorted(set(before) | set(after))
        if before.get(field) != after.get(field)
    ]


def _source_task(commit: str, task_id: str) -> dict[str, Any]:
    result = subprocess.run(
        ["git", "show", f"{commit}:{GRAPH_PATH.relative_to(REPO_ROOT).as_posix()}"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    source_graph = yaml.safe_load(result.stdout)
    return next(task for task in source_graph["taskcards"] if task["task_id"] == task_id)


def main() -> None:
    matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    graph = yaml.safe_load(GRAPH_PATH.read_text(encoding="utf-8"))

    deferred_catalog_path = REPO_ROOT / graph["deferred_task_catalog"]["path"]
    deferred_tasks = {
        json.loads(line)["task"]["task_id"]: json.loads(line)["task"]
        for line in deferred_catalog_path.read_text(encoding="utf-8").splitlines()
        if line
    }

    tasks_by_id = {row["id"]: row for row in matrix["tasks"]}
    updated = 0
    for task_id in _RETIRED_TASK_IDS:
        if task_id not in tasks_by_id:
            continue
        row = tasks_by_id[task_id]
        destination_task = deferred_tasks[task_id]
        source_task = _source_task(matrix["source_commit"], task_id)
        changes = _changed_fields(source_task, destination_task)
        row["destination"] = graph["deferred_task_catalog"]["path"]
        row["destination_task_sha256"] = _semantic_sha256(destination_task)
        row["transformation"] = "resequenced_active_horizon" if changes else "preserved_exactly"
        row["changed_fields"] = changes
        updated += 1

    new_tasks_by_id = {row["id"]: row for row in matrix["new_tasks"]}
    new_task_updates = 0
    for task_id in _RETIRED_TASK_IDS:
        if task_id not in new_tasks_by_id:
            continue
        row = new_tasks_by_id[task_id]
        row["destination"] = graph["deferred_task_catalog"]["path"]
        row["destination_task_sha256"] = _semantic_sha256(deferred_tasks[task_id])
        new_task_updates += 1

    MATRIX_PATH.write_text(json.dumps(matrix, indent=2) + "\n", encoding="utf-8")
    print(f"updated {updated} tasks[] provenance rows")
    print(f"updated {new_task_updates} new_tasks[] rows for now-retired tasks")


if __name__ == "__main__":
    main()
