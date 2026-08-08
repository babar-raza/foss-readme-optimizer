"""Perform the one-time lossless migration to compact, query-scoped authority."""

# ruff: noqa: E501

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
MASTER_PATH = REPO_ROOT / "plans" / "master.md"
IDEA_PATH = REPO_ROOT / "plans" / "idea.md"
REQUIREMENTS_PATH = REPO_ROOT / "plans" / "requirements.md"
GRAPH_PATH = (
    REPO_ROOT / "plans" / "investigations" / "control" / "level8-autonomous-mission-task-graph.yaml"
)
REQUIREMENT_CATALOG_PATH = REPO_ROOT / "plans" / "requirements" / "catalog.jsonl"
DECISION_CATALOG_PATH = REPO_ROOT / "plans" / "decisions" / "catalog.jsonl"
DEFERRED_TASK_CATALOG_PATH = (
    REPO_ROOT / "plans" / "investigations" / "control" / "level8-deferred-task-catalog.jsonl"
)
EVIDENCE_DIR = REPO_ROOT / "plans" / "investigations" / "evidence" / "agile-authority-reset-v1"
INVENTORY_PATH = EVIDENCE_DIR / "authority-inventory.json"
MIGRATION_MATRIX_PATH = EVIDENCE_DIR / "migration-matrix.json"
COVERAGE_PATH = (
    REPO_ROOT
    / "plans"
    / "investigations"
    / "evidence"
    / "level8-requirement-taskcard-coverage"
    / "requirement-taskcard-coverage.json"
)

ACTIVE_TASK_IDS = (
    "L8-AGILE-AUTHORITY-RESET",
    "L8-VPY-03B-FIRST-CURRENT-PYTHON-E2E",
    "L8-VPY-01-NOTE-VERIFIED-CANARY",
    "L8-VPY-03A-PAGE-PDF-VERIFIED-CANARIES",
    "L8-VPY-03C-PAGE-CURRENT-REFRESH",
    "L8-VPY-03D-NOTE-CURRENT-REFRESH",
    "L8-VPY-03E-3D-CURRENT-REFRESH",
    "L8-VPY-03-ALL-PYTHON-VERIFIED-POC",
    "L8-VPY-02-PAGE-PDF-VERIFIED-CANARIES",
)
ACTIVATION_TASK_ID = "L8-HORIZON-01-ACTIVATE-GATE-A"
ID_RE = re.compile(r"^[A-Z][A-Z0-9]{1,4}-\d{3}$")
UNESCAPED_PIPE_RE = re.compile(r"(?<!\\)\|")


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _path_sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _semantic_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return _sha256_bytes(payload)


def _changed_fields(before: dict[str, Any], after: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"field": field, "before": before.get(field), "after": after.get(field)}
        for field in sorted(set(before) | set(after))
        if before.get(field) != after.get(field)
    ]


def _relative(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def _head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _split_row(line: str) -> list[str]:
    stripped = line.strip().removeprefix("|").removesuffix("|")
    return [cell.strip() for cell in UNESCAPED_PIPE_RE.split(stripped)]


def _requirement_records(text: str) -> list[dict[str, Any]]:
    section = "Unsectioned"
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if line.startswith("## "):
            section = line.removeprefix("## ").strip()
        if not line.startswith("| "):
            continue
        cells = _split_row(line)
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
                "legacy_acceptance_evidence": cells[4],
                "traceability": cells[5],
                "section": section,
                "legacy_line": line_number,
                "legacy_row_sha256": _sha256_bytes(line.encode("utf-8")),
            }
        )
    return records


def _decision_records(text: str) -> list[dict[str, Any]]:
    ledger = text.split("## Decision Ledger", 1)[1].split("## Architecture", 1)[0].strip()
    matches = list(re.finditer(r"(?ms)^(\d+)\. \*\*(.+?)\*\*", ledger))
    records: list[dict[str, Any]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(ledger)
        raw = ledger[match.start() : end].strip()
        records.append(
            {
                "schema_version": 1,
                "decision_id": int(match.group(1)),
                "title": match.group(2).strip(),
                "markdown": raw,
                "legacy_record_sha256": _sha256_bytes(raw.encode("utf-8")),
            }
        )
    return records


def _jsonl(records: list[dict[str, Any]]) -> bytes:
    return (
        "\n".join(json.dumps(record, sort_keys=True, separators=(",", ":")) for record in records)
        + "\n"
    ).encode("utf-8")


def _activation_group(task: dict[str, Any]) -> str:
    stage = task["stage_goal_id"]
    if stage.startswith("GOAL-T") or stage == "GOAL-P0-PLAN-FREEZE":
        return "historical-control"
    if stage == "GOAL-C0-AUTHORIZED-PORTFOLIO":
        return "portfolio-intake"
    if stage in {"GOAL-V1-VERIFIED-TRUTH", "GOAL-V2-VERIFIED-GATE-A"}:
        return "verified-gate-a"
    if stage == "GOAL-V3-HUMAN-AND-JAVA-PROOF":
        return "gate-b-c"
    if stage in {"GOAL-L5-PRESENTATION-PILOT", "GOAL-L6-AUTONOMOUS-PORTFOLIO"}:
        return "deployment"
    if stage in {"GOAL-L7-HETEROGENEOUS-30D", "GOAL-L8-SELF-MAINTAINING-90D"}:
        return "background-certification"
    return "verified-next-horizon"


def _activation_task(mission_id: str) -> dict[str, Any]:
    return {
        "task_id": ACTIVATION_TASK_ID,
        "mission_id": mission_id,
        "parent_task_id": None,
        "title": "Activate the next bounded verified-delivery horizon",
        "source_audit_finding": (
            "Future work must remain losslessly deferred without loading the complete mission into "
            "every active execution context."
        ),
        "audit_classification": "future_hardening_work",
        "priority": "P0",
        "lane": "mission-horizon-activation",
        "owner": "readme-agent-supervisor",
        "status": "TODO",
        "objective": (
            "After the Python and representative post-Python slices close, promote only the next "
            "dependency-ready verified task horizon from the hashed deferred catalog into this same graph."
        ),
        "why_it_matters": (
            "Bounded context prevents authority overload while a lossless activation boundary preserves "
            "the full portfolio mission and its stable task identities."
        ),
        "allowed_paths": [
            "plans/investigations/control/level8-autonomous-mission-task-graph.yaml",
            "plans/investigations/control/level8-deferred-task-catalog.jsonl",
            "plans/investigations/evidence/",
            "plans/requirements/",
            "scripts/governance/",
            "src/readme_agent/supervisor/",
            "tests/unit/test_mission_control.py",
            "logs/",
        ],
        "forbidden_paths": ["runs/readme-poc/", "product repositories", "target remotes"],
        "dependencies": ["L8-VPY-02-PAGE-PDF-VERIFIED-CANARIES"],
        "expected_outputs": [
            "One next-horizon active graph with at most fifteen tasks and five ready tasks",
            "Updated catalog hashes, requirement slice, migration matrix, and durable-state reconciliation",
        ],
        "acceptance_checks": [
            "Every promoted task retains its stable ID and exact deferred record hash",
            "No task is lost, duplicated, made ready early, or silently treated as complete",
        ],
        "verification": [
            "catalog integrity, dependency, ready-budget, graph/state migration, and focused mission tests"
        ],
        "negative_controls": [
            "A missing, duplicate, unmapped, or dependency-ineligible deferred task fails activation"
        ],
        "regression_checks": [
            "durable claim recovery, stage-goal derivation, and requirement coverage"
        ],
        "evidence_requirements": [
            "before/after horizon manifest, graph hash, catalog hash, and focused-test receipt"
        ],
        "rollback_or_recovery": (
            "Restore the prior graph/catalog commit and reconcile durable state without deleting history."
        ),
        "failure_reroute": (
            "Repair the first catalog, dependency, or state-migration boundary; never create another controller."
        ),
        "closeout_rules": [
            "The next horizon is dependency-ready, bounded, state-reconciled, and independently verified"
        ],
        "goal_ids": ["GOAL-AUTONOMY"],
        "core_contribution": {
            "kind": "first_boundary_removal",
            "summary": "Advance the sole mission graph without reloading its complete future backlog.",
        },
        "execution_kind": "infrastructure",
        "infrastructure_admission": {
            "trigger": "next_cohort_exercised",
            "evidence_refs": [
                "The Python and representative post-Python slice dependencies must be CLOSED before this task is eligible."
            ],
        },
        "requirement_ids": [],
        "stage_goal_id": "GOAL-V0B-POST-PYTHON-SLICES",
        "concurrency_class": "primary_only",
        "campaign_id": "CAMP-THREE-SLICES",
    }


def _compact_graph(graph: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    graph = copy.deepcopy(graph)
    graph["mission_authority"]["in_scope_outcomes"] = [
        outcome.replace(
            "before trusted portfolio fan-out", "before verified Gate-A portfolio fan-out"
        )
        for outcome in graph["mission_authority"]["in_scope_outcomes"]
    ]
    graph["mission_authority"]["mandatory_acceptance_criteria"].extend(
        criterion
        for criterion in (
            "delivery_complete means every executable stage through deployable Level 6 is CLOSED; it never claims Level 7, Level 8, or full mission closure.",
            "certification_complete means the Level-7 and Level-8 background observations and independent audits are CLOSED; mission_complete requires both delivery_complete and certification_complete.",
        )
        if criterion not in graph["mission_authority"]["mandatory_acceptance_criteria"]
    )
    by_id = {task["task_id"]: task for task in graph["taskcards"]}
    missing = set(ACTIVE_TASK_IDS) - set(by_id)
    if missing:
        raise RuntimeError(f"active task IDs missing from source graph: {sorted(missing)}")
    active = [by_id[task_id] for task_id in ACTIVE_TASK_IDS]
    dependencies = {
        "L8-AGILE-AUTHORITY-RESET": [],
        "L8-VPY-01-NOTE-VERIFIED-CANARY": ["L8-AGILE-AUTHORITY-RESET"],
        "L8-VPY-03B-FIRST-CURRENT-PYTHON-E2E": ["L8-VPY-01-NOTE-VERIFIED-CANARY"],
        "L8-VPY-03A-PAGE-PDF-VERIFIED-CANARIES": ["L8-VPY-03B-FIRST-CURRENT-PYTHON-E2E"],
        "L8-VPY-03C-PAGE-CURRENT-REFRESH": ["L8-VPY-03A-PAGE-PDF-VERIFIED-CANARIES"],
        "L8-VPY-03D-NOTE-CURRENT-REFRESH": ["L8-VPY-03C-PAGE-CURRENT-REFRESH"],
        "L8-VPY-03E-3D-CURRENT-REFRESH": ["L8-VPY-03D-NOTE-CURRENT-REFRESH"],
        "L8-VPY-03-ALL-PYTHON-VERIFIED-POC": ["L8-VPY-03E-3D-CURRENT-REFRESH"],
        "L8-VPY-02-PAGE-PDF-VERIFIED-CANARIES": ["L8-VPY-03-ALL-PYTHON-VERIFIED-POC"],
    }
    for task in active:
        task["dependencies"] = dependencies[task["task_id"]]
        if task.get("parent_task_id") not in {*ACTIVE_TASK_IDS, None}:
            task["parent_task_id"] = None
    reset_paths = active[0]["allowed_paths"]
    for path in (
        "src/readme_agent/cli.py",
        "src/readme_agent/capabilities/effect_ledger.py",
        "src/readme_agent/capabilities/open_presentation_pr.py",
        "src/readme_agent/state/schema.py",
        "tests/unit/test_effect_ledger.py",
        "tests/unit/test_open_presentation_pr.py",
        "tests/unit/test_stage_dependency_manifest.py",
        "tests/unit/test_local_poc_cache.py",
        "tests/unit/test_readme_poc_lifecycle.py",
        "tests/unit/test_readme_poc_acceptance_axes.py",
        "tests/unit/test_agile_execution_controls.py",
        "tests/unit/test_run_full_pytest.py",
        "tests/unit/test_portfolio.py",
    ):
        if path not in reset_paths:
            reset_paths.append(path)
    active[0].update(
        {
            "execution_kind": "infrastructure",
            "infrastructure_admission": {
                "trigger": "current_repository_blocker",
                "evidence_refs": [
                    "The oversized control surface repeatedly invalidated visible README work "
                    "and obscured the next executable boundary."
                ],
            },
            "verification_change_classes": [
                "governance",
                "mission_state",
                "shared_code",
                "factuality",
                "safety",
            ],
            "evidence_promotion_boundary": "shared_code",
        }
    )
    active.append(_activation_task(graph["mission_authority"]["mission_id"]))

    deferred_records = [
        {
            "schema_version": 1,
            "activation_group": _activation_group(task),
            "task": task,
        }
        for task in graph["taskcards"]
        if task["task_id"] not in ACTIVE_TASK_IDS
    ]
    deferred_payload = _jsonl(deferred_records)
    deferred_lines = deferred_payload.decode("utf-8").splitlines()
    deferred_index = []
    for record, line in zip(deferred_records, deferred_lines, strict=True):
        task = record["task"]
        deferred_index.append(
            {
                "task_id": task["task_id"],
                "status": (
                    "DEFERRED_WITH_REASON"
                    if record["activation_group"] == "historical-control"
                    else task["status"]
                ),
                "stage_goal_id": task["stage_goal_id"],
                "activation_group": record["activation_group"],
                "record_sha256": _sha256_bytes(line.encode("utf-8")),
            }
        )

    coverage = json.loads(COVERAGE_PATH.read_text(encoding="utf-8"))
    compact = {
        **graph,
        "schema_version": 3,
        "taskcards": active,
        "requirement_catalog": {},
        "requirement_coverage": {
            "path": _relative(COVERAGE_PATH),
            "sha256": _path_sha256(COVERAGE_PATH),
            "record_count": coverage["total_requirement_rows"],
            "mandatory_requirement_rows": coverage["mandatory_requirement_rows"],
            "reopened_implemented_rows": coverage["reopened_implemented_rows"],
        },
        "deferred_task_catalog": {
            "path": _relative(DEFERRED_TASK_CATALOG_PATH),
            "sha256": _sha256_bytes(deferred_payload),
            "record_count": len(deferred_records),
        },
        "deferred_task_index": deferred_index,
        "bootstrap_state": {
            "initialization": "task status fields are bootstrap defaults only",
            "selection": "derive the earliest dependency-ready task through mission evaluate",
            "mission_complete": False,
            "stop_reason": "durable supervisor state owns live execution",
        },
    }
    return compact, deferred_records


def _task_migration_records(
    source_graph: dict[str, Any],
    destination_graph: dict[str, Any],
    deferred_records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    source_tasks = {task["task_id"]: task for task in source_graph["taskcards"]}
    active_tasks = {task["task_id"]: task for task in destination_graph["taskcards"]}
    deferred_tasks = {record["task"]["task_id"]: record["task"] for record in deferred_records}
    task_migrations = []
    for task_id, source_task in source_tasks.items():
        destination_task = active_tasks.get(task_id) or deferred_tasks[task_id]
        transformations = _changed_fields(source_task, destination_task)
        task_migrations.append(
            {
                "id": task_id,
                "destination": (
                    "active_graph"
                    if task_id in active_tasks
                    else _relative(DEFERRED_TASK_CATALOG_PATH)
                ),
                "source_task_sha256": _semantic_sha256(source_task),
                "destination_task_sha256": _semantic_sha256(destination_task),
                "transformation": (
                    "resequenced_active_horizon" if transformations else "preserved_exactly"
                ),
                "changed_fields": transformations,
            }
        )
    new_tasks = [
        {
            "id": task_id,
            "destination": "active_graph",
            "destination_task_sha256": _semantic_sha256(task),
            "reason": "bounded activation boundary for the next deferred execution horizon",
        }
        for task_id, task in active_tasks.items()
        if task_id not in source_tasks
    ]
    return task_migrations, new_tasks


def _master_text(decision_count: int) -> str:
    return f"""# Master Plan

## Mission

Deliver `verified_repository_presentation` for every dynamically discovered and admitted Aspose
FOSS repository. The system derives repository facts from authoritative evidence, produces
repository-specific professional presentation, validates every material claim and protected region,
obtains independent and staged human acceptance, and performs only separately authorized effects.

Python is the first complete platform, followed by .NET, Java, C++, TypeScript, Rust, and Go.
Level 5 and deployable Level 6 are delivery milestones. Level 7 and Level 8 are background
certifications accumulated after deployment, never prerequisites for visible output.

`delivery_complete` means every executable stage through deployable Level 6 is closed.
`certification_complete` means both post-deployment Level-7 and Level-8 observation/audit tracks
are closed. Full `mission_complete` requires both; delivery completion is never called Level 7,
Level 8, or full umbrella-mission closure.

## Status

The project remains pre-POC: current verified acceptance is `0/31` registry-wide. Durable mission
  state owns live status. After plan/state reconciliation, `L8-VPY-01-NOTE-VERIFIED-CANARY`
  requalifies the same-revision Note comparison as the development-time comparative regression
  pilot. Aspose.3D, Page, PDF, and the remaining Python cohort follow through the same reusable
  native contract.

Current generated views: `plans/status.md`, `plans/roadmap.md`, and `logs/`. They are derived and
never override the mission graph or durable state.

## Decision Ledger

The complete typed ledger contains {decision_count} stable decisions in
`plans/decisions/catalog.jsonl`. This section is the human-readable current decision index; the
catalog preserves the complete text and hashes of every prior decision.

Binding current decisions:

- **#24/#40 — Registry scope and intent gates.** Every admitted repository is relevant to read-only
  research; write permission remains separately allow-listed and authorized.
- **#26 — Canonical runtime.** `readme-agent supervise` is the only production execution path.
- **#33 — Product effects.** No product-repository write occurs without fresh exact what/why/where
  authorization; default branches are never written directly.
- **#78/#85/#88 — Verified POC.** Trusted execution is historical. Verified Python is first, then
  the dynamic portfolio. Independent approval and no-op proof precede human acceptance.
- **#89 — Dependencies.** Required toolchains are provisioned autonomously in disposable isolated
  environments from pinned, verified inputs.
- **#90 — Agile presentation.** Repository transactions pin component versions; later changes
  invalidate only semantic dependants. Non-critical improvements become `VALID_UPDATE_AVAILABLE`.
- **#91 — Staged acceptance.** Facts, presentation, independent review, human acceptance, and
  publication eligibility are separate states. All admitted repositories require final Gate-B
  human acceptance before any product PR.
- **#92 — Just-in-time infrastructure.** Infrastructure enters the critical path only when the next
  visible vertical slice exercises or demonstrably needs it.
- **#93 — Compact authority.** Active authority is query-scoped: no more than 15 active tasks, five
  ready tasks, or 25 requirements in one task context. Stable deferred work remains hashed.
- **#94 — Risk-tiered proof.** Focused proof follows each repair; complete suites and canonical
  evidence occur at declared shared/repository/cohort boundaries.
- **#95 — Adaptive parallelism.** Calibration and shared repair are serial. Repository workers
  scale from two to at most three only after isolation and measured throughput proof.
- **#96 — Background certification.** The 30/90-day windows are `OBSERVATION_RUNNING`, not blocked
  delivery tasks.
- **#97 — Technical judgment.** Agents classify and challenge tactics. Two equivalent failures or
  15 minutes without narrowing require a different causal boundary or mechanism.
- **#98 — First calibration.** Aspose.3D FOSS for Python is first; Note is second; Page/PDF form the
  representative Python cohort.

Current execution amendment: the latest product-outcome direction changes only the calibration
order recorded by #98. The same-revision Note comparison is now the first development regression;
Aspose.3D and Page/PDF follow after the resulting native contract passes. Aspose.org is a
development-only comparative corpus, never a deployed dependency or factual authority.

## Architecture

```text
authorized discovery -> immutable snapshot -> verified ProductFactsV2
  -> native fact selection + conflict reconciliation
  -> repository assessment -> semantic graph + component-versioned document plan
  -> candidate + native patch -> deterministic validation
  -> independent review/repair -> unchanged no-op proof
  -> staged human acceptance -> separately authorized proposal effect
  -> hosted observation and background maturity certification
```

### Authority and state

- `plans/idea.md`: human product outcome and intent.
- `plans/master.md` plus `plans/decisions/catalog.jsonl`: architecture, decisions, and sequence.
- `plans/requirements.md` plus `plans/requirements/catalog.jsonl`: normative obligations.
- Level-8 graph: sole active task/dependency graph.
- Hashed deferred-task catalog: future task records, never executable until promoted into the graph.
- Git-ref supervisor state: sole live claims, transitions, leases, and runtime status.

### Runtime invariants

- One immutable repository snapshot supplies every stage of a logical run.
- Repository README prose is evidence to verify, never truth by itself.
- Every final material claim maps to accepted facts or an explicit disposition.
- Existing content is protected and changed only through authorized, source-spanned operations.
- Product repositories are not touched during local proof; analysis never receives a write token.
- Draft proposals never merge, mark ready, force-push, or write default branches.
- State uncertainty, fact conflict, authorization failure, or evidence corruption fails closed.
- Identical reruns produce no patch, duplicate effect, or unnecessary model call.

### Presentation contract

All READMEs use a consistent professional header, product-specific title and opening, one useful
badge row, list-form navigation, verified installation and examples, a detailed fact-backed semantic
Mermaid graph, task-oriented capabilities, curated hub APIs, complete applicable documentation,
user-relevant limitations, maintainer guidance, MIT-license prose when applicable, and a separate
third-party-notices section. No comments, emoji, process narration, raw export dumps, duplicate
sections, or dangling fragments are emitted. Aspose.com and Aspose.org links are natural,
contextual, policy-capped, and selected from governed catalogs; `products.*` destinations have
priority. Commercial products are called **Enterprise Edition**.

Template structure is reusable but prose and facts remain repository-specific. Dense examples and
reference material may use accessible collapsible sections. Later style changes create component
deltas rather than global invalidation.

### Execution and concurrency

The coordinator owns shared state, plans, integration, commits, and closure. Calibration and shared
repairs are serial. After transaction/cache/cancellation/aggregation isolation passes, two disjoint
repository workers may run; a third is admitted only while speedup is at least 1.5x and coordination
overhead at most 25 percent. Independent verification never authors accepted work.

### Verification tiers

1. Touched static and focused checks during implementation.
2. Impacted integration, safety, recovery, and idempotency proof at coherent slices.
3. Per-repository facts, candidate, diff, deterministic validation, independent review, repair,
   no-op, LLM ledger, and checksum-valid manifest.
4. Complete non-live suite at shared-code, Python-platform, Gate-A, and declared delivery boundaries.
5. One independently reconstructed canonical evidence package per repository and cohort.

## Registry & Policy Config

`data/products.json` is the hard allow-list, not proof of discovery completeness. Organization-wide,
paginated, all-visibility discovery produces a revisioned observation set; exclusions and inaccessible
sources remain visible. New matching repositories enter disabled/read-only preflight. Platform priority
comes from `data/platform_priorities.json`.

Aspose link destinations come only from `data/aspose_com_links.json` and
`plans/aspose_org_links.json`. Configured link slots override automatic size-based allocation.

## Validator Registry

Validators are registered, typed, deterministic where judgment is unnecessary, and bound into the
candidate dependency manifest. They cover factual claims, package coordinates, examples, protected
content, Markdown structure, links, badges, Mermaid facts, license/notices, branding consistency,
promotion balance, ownership, safety, no-op behavior, and evidence integrity.

## LLM Contract

Models organize and write repository-specific prose and independently review quality where rules
cannot express judgment. Deterministic code remains authoritative for facts, permissions, source spans,
component versions, link ceilings, schemas, examples, validation, and effects. Author and reviewer
contexts, prompts, identities, caches, and evidence are separate. Every call records job, route, model,
input/output hashes, latency, retry, and repository without secrets.

## CI & Safety

All Python commands use `.venv`. Official control checks are Ruff, Ruff formatting, mypy, the bounded
complete non-live pytest runner, plan/coverage/authority validation, actionlint, and `git diff --check`.
Push-blocking, the allow-list, evidence redaction, isolated repository execution, short-lived effect
credentials, authorization, and default-branch protection are non-negotiable.

## Reference Data

Repository/package/test evidence outranks README prose. Approved policy owns subjective positioning.
Release data and approved documentation follow. During development, matching Aspose.org knowledge
and reports may expose gaps in Repo Presenter's extraction, selection, composition, graph, and
review behavior. Those lessons must be generalized into this repository's native versioned
contracts. Deployed and acceptance runs never read or depend on the sibling repository, its reports,
skills, scripts, or caches.

## Build Checklist

- [ ] **Agile authority reset:** compact catalogs and active graph, reconcile durable state, prove
  lossless stable-ID/dependency/coverage migration, and commit one control-only slice.
- [ ] **Comparative Note regression:** use the revision-matched Aspose.org report during development
  to expose native contract gaps, then regenerate Note without an Aspose.org runtime dependency and
  pass factual, editorial, semantic-graph, review, repair,
  promotion, and unchanged no-op proof without manual README editing.
- [ ] **Python representative cohort:** apply the accepted native contract to Aspose.3D, then
  Page/PDF, with targeted component-only feedback updates.
- [ ] **Python platform POC:** finalize every dynamically admitted Python repository.
- [ ] **Post-Python slices:** prove one current .NET and one current Java vertical slice.
- [ ] **Discovery and verified Gate A:** reconcile the complete source denominator, then finalize all
  repositories in .NET, Java, C++, TypeScript, Rust, and Go order.
- [ ] **Gate B:** independently approved portfolio package and explicit human acceptance per repository.
- [ ] **Workflow/staging/Gate C:** prove `act`, disposable GitHub staging, and authorized draft proposals.
- [ ] **Hosted system:** GitHub App token isolation, recovery, health, backlog, alerts, and dead-man monitor.
- [ ] **Level 5 and deployable Level 6:** complete presentation surfaces and autonomous portfolio operation.
- [ ] **Background certification:** observe and independently award Level 7 and Level 8 after deployment.

## Verification Checklist

- [ ] Active graph has at most 15 tasks, at most five ready, and no competing controller.
- [ ] Every original requirement, decision, task, dependency, status, and evidence pointer is preserved
  in a typed active or deferred record with verified hashes.
- [ ] Current task loads at most 25 requirements plus always-on invariants.
- [ ] Cosmetic changes do not invalidate facts or unrelated accepted components.
- [ ] Factual/safety/acceptance changes reopen the earliest affected stage.
- [ ] No README proceeds without deterministic and independent acceptance and no-op proof.
- [ ] Acceptance and deployed runs succeed with the Aspose.org checkout unavailable; no sibling
  report, raw knowledge record, skill, script, or cache is a runtime input or factual proof.
- [ ] Mermaid validation proves semantic topology, not syntax alone, and independent review rejects
  a correct-but-unhelpful document.
- [ ] Every admitted repository is human-accepted before Gate-C product effects.
- [ ] No local/`act` run writes a product remote and no effect writes a default branch.
- [ ] Recovery, deduplication, drift, lost-response, authorization, and corruption controls pass.
- [ ] Full-registry evidence is checksum-complete and independently reproducible.
- [ ] Level 7/8 observations run after deployment without blocking deliverables.

## Changelog

History lives in `logs/`; decisions retain stable IDs in `plans/decisions/catalog.jsonl`.
"""


def _requirements_text(records: list[dict[str, Any]]) -> str:
    counts = Counter(record["status"] for record in records)
    families = Counter(record["requirement_id"].split("-", 1)[0] for record in records)
    status_lines = "\n".join(f"- `{status}`: {count}" for status, count in sorted(counts.items()))
    family_lines = ", ".join(f"`{name}` {count}" for name, count in sorted(families.items()))
    return f"""# Requirements

## Authority

The normative typed catalog is `plans/requirements/catalog.jsonl`. This file is its compact
human-readable entry point. Every catalog line is one complete `RequirementRecordV1`; stable IDs are
never reused. Requirement status is not completion proof: current evidence and the mapped active task
still govern acceptance.

The catalog contains **{len(records)}** requirements:

{status_lines}

Families: {family_lines}.

## Loading requirements

The active mission graph lists only IDs directly owned by an active task. A task context may load
those records plus declared always-on invariants and must remain at or below 25 records. Full catalog
scans are governance/audit operations, not routine execution context.

Use:

```powershell
.venv/Scripts/python scripts/governance/query_requirement_catalog.py --task-id <TASK-ID>
```

The query fails closed on a missing/duplicate ID, stale graph/catalog hash, more than 25 records, or
an ID not mapped to the requested active task.

## Always-on invariants

Safety, factuality, authorization, recovery, idempotency, evidence integrity, and independent review
remain acceptance invariants even when their detailed rows are not loaded into the task prose context.
Their enforcement lives in registered validators and official checks, not repeated narrative text.

## Current active slice

The next executable slice is `L8-VPY-01-NOTE-VERIFIED-CANARY`: a development-only comparison and
native comparative regression. Aspose.org artifacts may diagnose contract gaps, but the accepted
run must succeed without that checkout and may not write any product repository. Durable supervisor
state remains the sole authority for the live claim.

## Status and history

Generated coverage lives at
`plans/investigations/evidence/level8-requirement-taskcard-coverage/requirement-taskcard-coverage.json`.
Detailed execution history remains in Git, `logs/`, durable state, and checksum-addressed evidence.
No derived report or handover overrides this catalog or durable state.
"""


def _commit_text(commit: str, path: Path) -> str:
    return subprocess.run(
        ["git", "show", f"{commit}:{_relative(path)}"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout


def _head_text(path: Path) -> str:
    return _commit_text("HEAD", path)


def migrate(*, source_head: bool) -> None:
    if (REQUIREMENT_CATALOG_PATH.exists() or DECISION_CATALOG_PATH.exists()) and not source_head:
        raise RuntimeError("compact authority catalogs already exist; refusing a second migration")
    reader = _head_text if source_head else lambda path: path.read_text(encoding="utf-8")
    master_text = reader(MASTER_PATH)
    requirements_text = reader(REQUIREMENTS_PATH)
    graph_text = reader(GRAPH_PATH)
    graph = yaml.safe_load(graph_text)
    if graph.get("schema_version") != 2:
        raise RuntimeError("source mission graph is not the expected schema_version 2")

    requirement_records = _requirement_records(requirements_text)
    decision_records = _decision_records(master_text)
    compact_graph, deferred_records = _compact_graph(graph)

    requirement_payload = _jsonl(requirement_records)
    decision_payload = _jsonl(decision_records)
    deferred_payload = _jsonl(deferred_records)
    compact_graph["requirement_catalog"] = {
        "path": _relative(REQUIREMENT_CATALOG_PATH),
        "sha256": _sha256_bytes(requirement_payload),
        "record_count": len(requirement_records),
    }

    before = {
        "head": _head(),
        "idea": {
            "sha256": _sha256_bytes(_head_text(IDEA_PATH).encode("utf-8")),
            "lines": len(_head_text(IDEA_PATH).splitlines()),
        },
        "master": {
            "sha256": _sha256_bytes(master_text.encode("utf-8")),
            "lines": len(master_text.splitlines()),
        },
        "requirements": {
            "sha256": _sha256_bytes(requirements_text.encode("utf-8")),
            "lines": len(requirements_text.splitlines()),
        },
        "graph": {
            "sha256": _sha256_bytes(graph_text.encode("utf-8")),
            "lines": len(graph_text.splitlines()),
        },
        "decision_ids": [record["decision_id"] for record in decision_records],
        "requirement_ids": [record["requirement_id"] for record in requirement_records],
        "task_ids": [task["task_id"] for task in graph["taskcards"]],
    }

    REQUIREMENT_CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    DECISION_CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    DEFERRED_TASK_CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    REQUIREMENT_CATALOG_PATH.write_bytes(requirement_payload)
    DECISION_CATALOG_PATH.write_bytes(decision_payload)
    DEFERRED_TASK_CATALOG_PATH.write_bytes(deferred_payload)
    MASTER_PATH.write_text(_master_text(len(decision_records)), encoding="utf-8")
    REQUIREMENTS_PATH.write_text(_requirements_text(requirement_records), encoding="utf-8")
    GRAPH_PATH.write_text(
        yaml.safe_dump(compact_graph, sort_keys=False, allow_unicode=True, width=100),
        encoding="utf-8",
    )

    after = {
        "idea": {
            "sha256": _path_sha256(IDEA_PATH),
            "lines": len(IDEA_PATH.read_text(encoding="utf-8").splitlines()),
        },
        "master": {
            "sha256": _path_sha256(MASTER_PATH),
            "lines": len(MASTER_PATH.read_text(encoding="utf-8").splitlines()),
        },
        "requirements": {
            "sha256": _path_sha256(REQUIREMENTS_PATH),
            "lines": len(REQUIREMENTS_PATH.read_text(encoding="utf-8").splitlines()),
        },
        "graph": {
            "sha256": _path_sha256(GRAPH_PATH),
            "lines": len(GRAPH_PATH.read_text(encoding="utf-8").splitlines()),
        },
        "requirement_catalog": {
            "sha256": _path_sha256(REQUIREMENT_CATALOG_PATH),
            "records": len(requirement_records),
        },
        "decision_catalog": {
            "sha256": _path_sha256(DECISION_CATALOG_PATH),
            "records": len(decision_records),
        },
        "deferred_task_catalog": {
            "sha256": _path_sha256(DEFERRED_TASK_CATALOG_PATH),
            "records": len(deferred_records),
        },
        "active_task_ids": [task["task_id"] for task in compact_graph["taskcards"]],
        "deferred_task_ids": [record["task"]["task_id"] for record in deferred_records],
    }
    inventory = {
        "schema": "AuthorityInventoryV1",
        "source_commit": before["head"],
        "before": before,
        "after": after,
        "lossless_counts": {
            "decisions_before": len(decision_records),
            "decisions_after": len(decision_records),
            "requirements_before": len(requirement_records),
            "requirements_after": len(requirement_records),
            "original_tasks_before": len(graph["taskcards"]),
            "original_tasks_after": len(ACTIVE_TASK_IDS) + len(deferred_records),
            "new_horizon_activation_tasks": 1,
        },
    }
    task_migrations, new_tasks = _task_migration_records(graph, compact_graph, deferred_records)
    matrix = {
        "schema": "AuthorityMigrationMatrixV1",
        "source_commit": before["head"],
        "decisions": [
            {
                "id": record["decision_id"],
                "destination": _relative(DECISION_CATALOG_PATH),
                "sha256": record["legacy_record_sha256"],
            }
            for record in decision_records
        ],
        "requirements": [
            {
                "id": record["requirement_id"],
                "destination": _relative(REQUIREMENT_CATALOG_PATH),
                "sha256": record["legacy_row_sha256"],
            }
            for record in requirement_records
        ],
        "tasks": task_migrations,
        "new_tasks": new_tasks,
    }
    INVENTORY_PATH.write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
    MIGRATION_MATRIX_PATH.write_text(json.dumps(matrix, indent=2) + "\n", encoding="utf-8")
    print(f"Migrated {len(decision_records)} decisions, {len(requirement_records)} requirements")
    print(
        f"Active tasks: {len(compact_graph['taskcards'])}; deferred tasks: {len(deferred_records)}"
    )


def refresh_inventory() -> None:
    inventory = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    graph = yaml.safe_load(GRAPH_PATH.read_text(encoding="utf-8"))
    inventory["after"].update(
        {
            "idea": {
                "sha256": _path_sha256(IDEA_PATH),
                "lines": len(IDEA_PATH.read_text(encoding="utf-8").splitlines()),
            },
            "master": {
                "sha256": _path_sha256(MASTER_PATH),
                "lines": len(MASTER_PATH.read_text(encoding="utf-8").splitlines()),
            },
            "requirements": {
                "sha256": _path_sha256(REQUIREMENTS_PATH),
                "lines": len(REQUIREMENTS_PATH.read_text(encoding="utf-8").splitlines()),
            },
            "graph": {
                "sha256": _path_sha256(GRAPH_PATH),
                "lines": len(GRAPH_PATH.read_text(encoding="utf-8").splitlines()),
            },
            "requirement_catalog": {
                "sha256": _path_sha256(REQUIREMENT_CATALOG_PATH),
                "records": graph["requirement_catalog"]["record_count"],
            },
            "decision_catalog": {
                "sha256": _path_sha256(DECISION_CATALOG_PATH),
                "records": len(_jsonl_records(DECISION_CATALOG_PATH)),
            },
            "deferred_task_catalog": {
                "sha256": _path_sha256(DEFERRED_TASK_CATALOG_PATH),
                "records": graph["deferred_task_catalog"]["record_count"],
            },
            "active_task_ids": [task["task_id"] for task in graph["taskcards"]],
            "deferred_task_ids": [task["task_id"] for task in graph["deferred_task_index"]],
        }
    )
    INVENTORY_PATH.write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
    matrix = json.loads(MIGRATION_MATRIX_PATH.read_text(encoding="utf-8"))
    source_graph = yaml.safe_load(_commit_text(inventory["source_commit"], GRAPH_PATH))
    deferred_records = _jsonl_records(DEFERRED_TASK_CATALOG_PATH)
    task_migrations, new_tasks = _task_migration_records(source_graph, graph, deferred_records)
    matrix["tasks"] = task_migrations
    matrix["new_tasks"] = new_tasks
    MIGRATION_MATRIX_PATH.write_text(json.dumps(matrix, indent=2) + "\n", encoding="utf-8")
    print("Refreshed AuthorityInventoryV1 after-state hashes")


def _jsonl_records(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def add_legacy_requirement_status() -> None:
    """Add the immutable migrated status without overwriting current status."""

    records = _jsonl_records(REQUIREMENT_CATALOG_PATH)
    changed = False
    for record in records:
        if record.get("legacy_status") is None:
            record["legacy_status"] = record["status"]
            changed = True
    if changed:
        REQUIREMENT_CATALOG_PATH.write_bytes(_jsonl(records))
    print(f"Requirement legacy status present on {len(records)} record(s)")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--migrate", action="store_true")
    parser.add_argument("--source-head", action="store_true")
    parser.add_argument("--refresh-inventory", action="store_true")
    parser.add_argument("--add-legacy-requirement-status", action="store_true")
    args = parser.parse_args()
    selected = sum((args.migrate, args.refresh_inventory, args.add_legacy_requirement_status))
    if selected != 1:
        parser.error(
            "choose exactly one of --migrate, --refresh-inventory, or "
            "--add-legacy-requirement-status"
        )
    if args.migrate:
        migrate(source_head=args.source_head)
    elif args.add_legacy_requirement_status:
        add_legacy_requirement_status()
    else:
        refresh_inventory()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
