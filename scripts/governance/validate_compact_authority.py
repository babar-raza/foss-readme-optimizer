"""Validate compact authority budgets and lossless stable-ID migration."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from readme_agent.supervisor.mission_schema import (
    DecisionCatalogRecordV1,
    DeferredTaskRecordV1,
    RequirementCatalogRecordV1,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
IDEA_PATH = REPO_ROOT / "plans" / "idea.md"
MASTER_PATH = REPO_ROOT / "plans" / "master.md"
REQUIREMENTS_PATH = REPO_ROOT / "plans" / "requirements.md"
REQUIREMENT_CATALOG_PATH = REPO_ROOT / "plans" / "requirements" / "catalog.jsonl"
DECISION_CATALOG_PATH = REPO_ROOT / "plans" / "decisions" / "catalog.jsonl"
GRAPH_PATH = (
    REPO_ROOT / "plans" / "investigations" / "control" / "level8-autonomous-mission-task-graph.yaml"
)
INVENTORY_PATH = (
    REPO_ROOT
    / "plans"
    / "investigations"
    / "evidence"
    / "agile-authority-reset-v1"
    / "authority-inventory.json"
)
MATRIX_PATH = INVENTORY_PATH.with_name("migration-matrix.json")
ID_RE = re.compile(r"^[A-Z][A-Z0-9]{1,4}-\d{3}$")
UNESCAPED_PIPE_RE = re.compile(r"(?<!\\)\|")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _semantic_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _changed_fields(before: dict[str, Any], after: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"field": field, "before": before.get(field), "after": after.get(field)}
        for field in sorted(set(before) | set(after))
        if before.get(field) != after.get(field)
    ]


def _source_text(commit: str, path: Path) -> str:
    result = subprocess.run(
        ["git", "show", f"{commit}:{path.relative_to(REPO_ROOT).as_posix()}"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout


def _source_requirement_records(text: str) -> list[dict[str, Any]]:
    section = "Unsectioned"
    records = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if line.startswith("## "):
            section = line.removeprefix("## ").strip()
        if not line.startswith("| "):
            continue
        stripped = line.strip().removeprefix("|").removesuffix("|")
        cells = [cell.strip() for cell in UNESCAPED_PIPE_RE.split(stripped)]
        if len(cells) != 6:
            continue
        requirement_id = cells[0].strip("`")
        if not ID_RE.fullmatch(requirement_id):
            continue
        records.append(
            {
                "schema_version": 1,
                "requirement_id": requirement_id,
                "priority": cells[1].strip("`"),
                "status": cells[2].strip("`"),
                "legacy_status": cells[2].strip("`"),
                "requirement": cells[3],
                "acceptance_evidence": cells[4],
                "traceability": cells[5],
                "section": section,
                "legacy_line": lineno,
                "legacy_row_sha256": hashlib.sha256(line.encode("utf-8")).hexdigest(),
            }
        )
    return records


def _source_decision_records(text: str) -> list[dict[str, Any]]:
    ledger = text.split("## Decision Ledger", 1)[1].split("## Architecture", 1)[0].strip()
    matches = list(re.finditer(r"(?ms)^(\d+)\. \*\*(.+?)\*\*", ledger))
    records = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(ledger)
        markdown = ledger[match.start() : end].strip()
        records.append(
            {
                "schema_version": 1,
                "decision_id": int(match.group(1)),
                "title": match.group(2).strip(),
                "markdown": markdown,
                "legacy_record_sha256": hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
            }
        )
    return records


def _jsonl(path: Path, record_type: type[BaseModel]) -> list[dict[str, Any]]:
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        payload = json.loads(line)
        record_type.model_validate(payload)
        records.append(payload)
    return records


def _source_catalog_errors(
    requirements: list[dict[str, Any]],
    decisions: list[dict[str, Any]],
    source_commit: str,
) -> list[str]:
    errors = []
    source_requirements = _source_requirement_records(
        _source_text(source_commit, REQUIREMENTS_PATH)
    )
    migrated_requirements = [
        {
            **{
                key: value
                for key, value in record.items()
                if key
                not in {
                    "legacy_section",
                    "legacy_requirement",
                    "legacy_priority",
                    "legacy_acceptance_evidence",
                    "legacy_traceability",
                }
            },
            "section": record.get("legacy_section") or record["section"],
            "requirement": record.get("legacy_requirement") or record["requirement"],
            "priority": record.get("legacy_priority") or record["priority"],
            "status": record.get("legacy_status") or record["status"],
            "acceptance_evidence": (
                record.get("legacy_acceptance_evidence") or record["acceptance_evidence"]
            ),
            "traceability": record.get("legacy_traceability") or record["traceability"],
        }
        for record in requirements
    ]
    if migrated_requirements != source_requirements:
        errors.append("typed requirement catalog is not an exact source-record migration")
    source_decisions = _source_decision_records(_source_text(source_commit, MASTER_PATH))
    source_decision_ids = {record["decision_id"] for record in source_decisions}
    migrated_decisions = [
        {
            **{
                key: value
                for key, value in record.items()
                if key not in {"legacy_title", "legacy_markdown"}
            },
            "title": record.get("legacy_title") or record["title"],
            "markdown": record.get("legacy_markdown") or record["markdown"],
        }
        for record in decisions
        if record["decision_id"] in source_decision_ids
    ]
    if migrated_decisions != source_decisions:
        errors.append("typed decision catalog is not an exact source-record migration")
    return errors


def main() -> int:
    errors: list[str] = []
    graph = yaml.safe_load(GRAPH_PATH.read_text(encoding="utf-8"))
    inventory = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    requirement_path = REPO_ROOT / graph["requirement_catalog"]["path"]
    deferred_path = REPO_ROOT / graph["deferred_task_catalog"]["path"]
    decision_path = DECISION_CATALOG_PATH
    requirements = _jsonl(requirement_path, RequirementCatalogRecordV1)
    deferred = _jsonl(deferred_path, DeferredTaskRecordV1)
    decisions = _jsonl(decision_path, DecisionCatalogRecordV1)

    budgets = {
        "idea lines": (len(IDEA_PATH.read_text(encoding="utf-8").splitlines()), 500),
        "master lines": (len(MASTER_PATH.read_text(encoding="utf-8").splitlines()), 600),
        "requirements index lines": (
            len(REQUIREMENTS_PATH.read_text(encoding="utf-8").splitlines()),
            200,
        ),
        "active tasks": (len(graph["taskcards"]), 15),
    }
    for label, (actual, maximum) in budgets.items():
        if actual > maximum:
            errors.append(f"{label} exceeds budget: {actual} > {maximum}")

    active_ids = {task["task_id"] for task in graph["taskcards"]}
    deferred_ids = {record["task"]["task_id"] for record in deferred}
    if active_ids & deferred_ids:
        errors.append("active and deferred task IDs overlap")
    original_task_ids = set(inventory["before"]["task_ids"])
    declared_new_task_ids = {record["id"] for record in matrix.get("new_tasks", [])}
    if original_task_ids != (active_ids | deferred_ids) - declared_new_task_ids:
        errors.append("original task ID set was not preserved losslessly")
    if len({record["requirement_id"] for record in requirements}) != len(requirements):
        errors.append("requirement catalog contains duplicate IDs")
    if len({record["decision_id"] for record in decisions}) != len(decisions):
        errors.append("decision catalog contains duplicate IDs")
    if {record["requirement_id"] for record in requirements} != set(
        inventory["before"]["requirement_ids"]
    ):
        errors.append("requirement stable-ID set changed during migration")
    current_decision_ids = {record["decision_id"] for record in decisions}
    source_decision_ids = set(inventory["before"]["decision_ids"])
    if not source_decision_ids.issubset(current_decision_ids):
        errors.append("a source decision stable ID was removed after migration")
    appended_decision_ids = current_decision_ids - source_decision_ids
    if appended_decision_ids:
        expected_appended_ids = set(
            range(max(source_decision_ids) + 1, max(current_decision_ids) + 1)
        )
        if appended_decision_ids != expected_appended_ids:
            errors.append("post-migration decision IDs are not append-only and contiguous")
    if any(len(task.get("requirement_ids", [])) > 25 for task in graph["taskcards"]):
        errors.append("an active task exceeds the 25-requirement context budget")

    ready = []
    task_by_id = {task["task_id"]: task for task in graph["taskcards"]}
    for task in graph["taskcards"]:
        if task["status"] not in {"TODO", "READY", "REOPENED", "REGRESSED"}:
            continue
        if all(task_by_id[dep]["status"] == "CLOSED" for dep in task["dependencies"]):
            ready.append(task["task_id"])
    if len(ready) > 5:
        errors.append(f"static active horizon exposes {len(ready)} ready tasks, over budget 5")

    references = {
        "requirement catalog": (requirement_path, graph["requirement_catalog"]["sha256"]),
        "deferred task catalog": (deferred_path, graph["deferred_task_catalog"]["sha256"]),
        "requirement coverage": (
            REPO_ROOT / graph["requirement_coverage"]["path"],
            graph["requirement_coverage"]["sha256"],
        ),
    }
    for label, (path, expected) in references.items():
        actual = _sha256(path)
        if actual != expected:
            errors.append(f"{label} hash mismatch: {actual} != {expected}")

    if len(matrix["decisions"]) != len(inventory["before"]["decision_ids"]):
        errors.append("decision migration matrix count mismatch")
    if len(matrix["requirements"]) != len(requirements):
        errors.append("requirement migration matrix count mismatch")
    if len(matrix["tasks"]) != len(original_task_ids):
        errors.append("task migration matrix count mismatch")
    source_commit = matrix["source_commit"]
    source_graph = yaml.safe_load(_source_text(source_commit, GRAPH_PATH))
    source_tasks = {task["task_id"]: task for task in source_graph["taskcards"]}
    active_tasks = {task["task_id"]: task for task in graph["taskcards"]}
    deferred_tasks = {record["task"]["task_id"]: record["task"] for record in deferred}
    matrix_tasks = {record["id"]: record for record in matrix["tasks"]}
    if set(matrix_tasks) != set(source_tasks):
        errors.append("task migration matrix stable-ID set mismatch")
    for task_id, source_task in source_tasks.items():
        destination_task = active_tasks.get(task_id) or deferred_tasks.get(task_id)
        if destination_task is None:
            errors.append(f"task {task_id} has no migration destination")
            continue
        row = matrix_tasks.get(task_id)
        if row is None:
            continue
        changes = _changed_fields(source_task, destination_task)
        expected_destination = (
            "active_graph" if task_id in active_tasks else graph["deferred_task_catalog"]["path"]
        )
        expected_transformation = "resequenced_active_horizon" if changes else "preserved_exactly"
        if row.get("destination") != expected_destination:
            errors.append(f"task {task_id} migration destination mismatch")
        if row.get("source_task_sha256") != _semantic_sha256(source_task):
            errors.append(f"task {task_id} source semantic hash mismatch")
        destination_changed_after_migration = row.get(
            "destination_task_sha256"
        ) != _semantic_sha256(destination_task)
        focus_amendment = task_id in active_tasks and destination_task.get("execution_focus")
        if destination_changed_after_migration and not focus_amendment:
            errors.append(f"task {task_id} destination semantic hash mismatch")
        if not destination_changed_after_migration:
            if row.get("transformation") != expected_transformation:
                errors.append(f"task {task_id} transformation classification mismatch")
            if row.get("changed_fields") != changes:
                errors.append(f"task {task_id} changed-field record mismatch")
    new_tasks = {record["id"]: record for record in matrix.get("new_tasks", [])}
    expected_new_ids = set(active_tasks) - set(source_tasks)
    if set(new_tasks) != expected_new_ids:
        errors.append("new task migration set mismatch")
    for task_id in expected_new_ids:
        if new_tasks[task_id].get("destination_task_sha256") != _semantic_sha256(
            active_tasks[task_id]
        ):
            errors.append(f"new task {task_id} semantic hash mismatch")
    errors.extend(_source_catalog_errors(requirements, decisions, source_commit))

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(
        "Compact authority valid: "
        f"{len(decisions)} decisions, {len(requirements)} requirements, "
        f"{len(active_ids)} active tasks, {len(deferred_ids)} deferred tasks, {len(ready)} ready"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
