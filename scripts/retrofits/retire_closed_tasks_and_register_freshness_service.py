"""Retire the 10 durably-CLOSED active taskcards into the deferred catalog and
register one umbrella taskcard for the autonomous README freshness-service
objective, following the L8-VNET-01 next-platform precedent (Python-gated by
a plain dependency edge, not a special-cased eligibility rule).

Context: the active mission graph sits at its 15-task cap
(mission_graph.py:166-167) with 10 durably-CLOSED cards occupying slots that
could not previously be retired because mission_graph.py::_validate_graph and
mission_control.py::_dependency_ready_tasks resolved dependencies only against
active taskcards, never the deferred catalog -- a gap fixed and regression
tested this session (see l8-horizon-01-deferral-2026-08-13/findings.md,
Finding 3). This script performs the one-time data migration that fix makes
safe, and registers the freshness-service umbrella card the plan at
plans/claude/moonlit-juggling-flurry.md was written to eventually enter the
graph through -- as a normal blocked/todo task, not a live authority of its
own.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml

GRAPH_PATH = Path("plans/investigations/control/level8-autonomous-mission-task-graph.yaml")
DEFERRED_CATALOG_PATH = Path("plans/investigations/control/level8-deferred-task-catalog.jsonl")

_RETIRED_CLOSED_TASK_IDS = [
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
_ACTIVATION_GROUP = "capacity-retired-closed"

_FRESHNESS_SERVICE_TASK = {
    "task_id": "L8-FRESH-00-FRESHNESS-SERVICE",
    "mission_id": "LEVEL8-CENTRAL-REPOSITORY-PRESENTATION",
    "parent_task_id": None,
    "title": "Register the autonomous README freshness-service objective",
    "source_audit_finding": (
        "plans/claude/moonlit-juggling-flurry.md and its 2026-08-16 reconciliation "
        "(plans/investigations/evidence/freshness-service-final-2026-08-15/) designed and "
        "partially built an autonomous README freshness service on an isolated, unregistered "
        "worktree/branch (freshness-service/integration) instead of through this graph -- real, "
        "diagnosed, mostly-tested engineering exists there (T3 vendored checks, T4 factpack "
        "views, T14 section registry, a T5 cells/python pilot with a proven disposition-ledger "
        "fix) but it was never admitted through TS-01/TS-02/TS-03 registration before executing, "
        "so none of it is currently visible to durable mission state."
    ),
    "audit_classification": "partially_done",
    "priority": "P2",
    "lane": "freshness-service",
    "owner": "readme-agent-supervisor",
    "status": "TODO",
    "objective": (
        "Reuse the proven Aspose.org README contract, source-reconciliation, fact-extraction, "
        "and validation practices to build an autonomous freshness service on top of the current "
        "supervisor, mission graph, taskcards, validators, state, evidence, and recovery "
        "machinery: detect unchanged inputs and perform a zero-LLM no-op, compose bounded LLM "
        "steps through llm.professionalize.com only where needed, and process the complete "
        "portfolio to a local, human-reviewable candidate bundle -- without bypassing any "
        "existing remote-write or human-approval boundary."
    ),
    "why_it_matters": (
        "Freshness must become one governed capability of the existing autonomous system, not a "
        "second execution path -- reusing this mission's proven state machine, evidence "
        "contract, and authorization gates is what keeps portfolio-wide freshness work "
        "repeatable, auditable, and safe to resume across reruns."
    ),
    "allowed_paths": [
        "src/readme_agent/",
        "tests/",
        "plans/investigations/evidence/freshness-service-*/",
        "plans/investigations/control/freshness-service-*",
        "docs/",
        "logs/",
        "runs/readme-poc/",
        "runs/multi-agent/L8-FRESH-00-FRESHNESS-SERVICE/",
    ],
    "forbidden_paths": [
        "plans/claude/moonlit-juggling-flurry.md (historical design reference only; never "
        "executed from, never a live status source)",
        "production target repository remotes",
        "target default branches",
    ],
    "dependencies": ["L8-VPY-05-PRODUCTION-ADMISSION"],
    "expected_outputs": [
        "A reconciliation ledger disposing every commit on freshness-service/integration "
        "(reusable-unchanged, reusable-after-adaptation, must-be-discarded, or "
        "requires-external-authority) against current main",
        "The proven, licensing-cleared aspose.org-derived README contract, checks, and factpack "
        "reused behind existing interfaces rather than a second composer/validator stack",
        "A freshness/no-op detection path wired into the existing supervisor and scheduler",
    ],
    "acceptance_checks": [
        "No live status, gate, or transition model operates outside this graph and durable state",
        "Every reused component from freshness-service/integration is revalidated against current "
        "main's baseline before being trusted, not merely carried over on old evidence",
        "Zero-LLM no-op is proven for at least one repository with unchanged inputs",
        "No remote-write or human-approval boundary already enforced by the current system is "
        "bypassed or weakened",
    ],
    "verification": [
        "Focused tests for each reused/adapted module",
        "Full governed suite green with zero new failures",
        "run_official_checks.py and validate_compact_authority.py both clean",
    ],
    "negative_controls": [
        "A candidate produced outside the tracked supervise lane cannot count as portfolio "
        "progress",
        "An evidence directory alone, without a governed commit and mission transition, cannot "
        "close this task",
    ],
    "regression_checks": [
        "mission graph load and dependency resolution (active and deferred)",
        "existing README contract and validator suite",
        "no-op / freshness idempotency",
    ],
    "evidence_requirements": [
        "The reconciliation ledger, per-component revalidation results, and governed commit "
        "history for every piece of freshness-service/integration reused",
    ],
    "rollback_or_recovery": (
        "Nothing in this task's own registration touches product repositories or shared runtime "
        "state beyond this graph; a bad reuse decision reverts by discarding the specific "
        "governed commit that applied it, per its own task's rollback rule."
    ),
    "failure_reroute": (
        "A defect in shared supervisor/validator machinery discovered while reconciling reused "
        "code is fixed surgically at its own layer with regression tests, not patched inline "
        "inside this task."
    ),
    "closeout_rules": [
        "This task closes only once the reconciliation ledger is fully disposed and every kept "
        "component is reapplied through a governed commit with passing tests -- not merely once "
        "old evidence exists",
    ],
    "goal_ids": ["GOAL-README", "GOAL-AUTONOMY"],
    "core_contribution": {
        "kind": "visible_deliverable",
        "summary": (
            "Bring the autonomous README freshness-service objective, and the real work already "
            "done for it, under this mission's one governed state machine."
        ),
    },
    "execution_focus": {
        "goal_id": "DELIVERY-FRESHNESS-SERVICE",
        "immediate_outcome": (
            "Reconcile the isolated freshness-service branch into governed state and resume its "
            "proven work through the current supervisor."
        ),
        "repository_scope": ["platform:cross-platform"],
        "allowed_change_classes": [
            "shared_code",
            "repository_runtime",
            "factuality",
            "presentation",
        ],
        "next_goal_on_success": (
            "Extend the freshness service across the complete portfolio once it is production-"
            "proven on its first repository."
        ),
    },
    "requirement_ids": [],
    "stage_goal_id": "GOAL-V0B-POST-PYTHON-SLICES",
    "concurrency_class": "repository_local_write_isolated",
    "campaign_id": "CAMP-GATE-B-AND-LATER",
}


def _compact_json_line(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def main() -> None:
    raw = yaml.safe_load(GRAPH_PATH.read_text(encoding="utf-8"))

    active_by_id = {task["task_id"]: task for task in raw["taskcards"]}
    missing = [task_id for task_id in _RETIRED_CLOSED_TASK_IDS if task_id not in active_by_id]
    if missing:
        raise SystemExit(f"expected active tasks not found: {missing}")

    new_deferred_index_entries = []
    new_catalog_lines = []
    for task_id in _RETIRED_CLOSED_TASK_IDS:
        task = dict(active_by_id[task_id])
        task["status"] = "CLOSED"
        record = {"schema_version": 1, "activation_group": _ACTIVATION_GROUP, "task": task}
        line = _compact_json_line(record)
        new_catalog_lines.append(line)
        new_deferred_index_entries.append(
            {
                "task_id": task_id,
                "status": "CLOSED",
                "stage_goal_id": task["stage_goal_id"],
                "activation_group": _ACTIVATION_GROUP,
                "record_sha256": hashlib.sha256(line.encode()).hexdigest(),
            }
        )

    existing_catalog_text = DEFERRED_CATALOG_PATH.read_text(encoding="utf-8")
    if not existing_catalog_text.endswith("\n"):
        existing_catalog_text += "\n"
    updated_catalog_text = existing_catalog_text + "\n".join(new_catalog_lines) + "\n"
    DEFERRED_CATALOG_PATH.write_text(updated_catalog_text, encoding="utf-8")

    raw["taskcards"] = [
        task for task in raw["taskcards"] if task["task_id"] not in _RETIRED_CLOSED_TASK_IDS
    ]
    raw["taskcards"].append(_FRESHNESS_SERVICE_TASK)
    raw["deferred_task_index"].extend(new_deferred_index_entries)

    catalog_lines = [line for line in updated_catalog_text.splitlines() if line]
    raw["deferred_task_catalog"]["record_count"] = len(catalog_lines)
    raw["deferred_task_catalog"]["sha256"] = hashlib.sha256(
        DEFERRED_CATALOG_PATH.read_bytes()
    ).hexdigest()

    # Match compact_active_authority.py's exact dump parameters (the script
    # that originally generated this file) so re-serialization only touches
    # the real data change, not the whole file's line-wrapping.
    GRAPH_PATH.write_text(
        yaml.safe_dump(raw, sort_keys=False, allow_unicode=True, width=100),
        encoding="utf-8",
    )

    print(f"retired {len(_RETIRED_CLOSED_TASK_IDS)} closed tasks into the deferred catalog")
    print("registered L8-FRESH-00-FRESHNESS-SERVICE")
    print(f"deferred catalog now has {len(catalog_lines)} records")
    print(f"active taskcards now: {len(raw['taskcards'])}")


if __name__ == "__main__":
    main()
