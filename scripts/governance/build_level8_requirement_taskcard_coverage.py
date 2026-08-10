"""Map every normative requirement into the one Level-8 mission task graph."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
REQUIREMENTS_PATH = REPO_ROOT / "plans" / "requirements" / "catalog.jsonl"
GRAPH_PATH = (
    REPO_ROOT / "plans" / "investigations" / "control" / "level8-autonomous-mission-task-graph.yaml"
)
MATRIX_PATH = (
    REPO_ROOT
    / "plans"
    / "investigations"
    / "evidence"
    / "implementation-truth-matrix-2026"
    / "matrix.json"
)
REPORT_PATH = (
    REPO_ROOT
    / "plans"
    / "investigations"
    / "evidence"
    / "level8-requirement-taskcard-coverage"
    / "requirement-taskcard-coverage.json"
)
DEFERRED_TASK_CATALOG_PATH = (
    REPO_ROOT / "plans" / "investigations" / "control" / "level8-deferred-task-catalog.jsonl"
)

STAGE_GOAL_ORDER = {
    "GOAL-P0-PLAN-FREEZE": 0,
    "GOAL-V0A-FIRST-VERIFIED-README": 5,
    "GOAL-T0-TRUSTED-QUALIFICATION": 10,
    "GOAL-V0-VERIFIED-PYTHON-POC": 11,
    "GOAL-TP-TRUSTED-COHORT-POC": 12,
    "GOAL-T0R-TRUSTED-ADVERSARIAL-QUALIFICATION": 13,
    "GOAL-V0B-POST-PYTHON-SLICES": 14,
    "GOAL-C0-AUTHORIZED-PORTFOLIO": 15,
    "GOAL-T1-TRUSTED-PORTFOLIO": 20,
    "GOAL-T2-WORKFLOW-STAGING": 30,
    "GOAL-T3-HOSTED-TRUSTED-DELIVERY": 40,
    "GOAL-V1-VERIFIED-TRUTH": 50,
    "GOAL-V2-VERIFIED-GATE-A": 60,
    "GOAL-V3-HUMAN-AND-JAVA-PROOF": 70,
    "GOAL-L5-PRESENTATION-PILOT": 80,
    "GOAL-L6-AUTONOMOUS-PORTFOLIO": 90,
    "GOAL-L7-HETEROGENEOUS-30D": 100,
    "GOAL-L8-SELF-MAINTAINING-90D": 110,
}


def task_stage_goal(task_id: str) -> tuple[str, str]:
    """Return the governed stage and concurrency class for every mission task."""

    if task_id == "L8-PLAN-RECONCILIATION-ACCELERATION":
        return "GOAL-P0-PLAN-FREEZE", "primary_only"
    if task_id == "L8-AGILE-AUTHORITY-RESET":
        return "GOAL-V0A-FIRST-VERIFIED-README", "primary_only"
    if task_id == "L8-HORIZON-01-ACTIVATE-GATE-A":
        return "GOAL-V0B-POST-PYTHON-SLICES", "primary_only"
    if task_id == "L8-VPY-00-GOLDEN-TEMPLATE":
        return "GOAL-V0A-FIRST-VERIFIED-README", "primary_only"
    if task_id == "L8-VPY-00-PRESENTATION-CONTRACT-RESET":
        return "GOAL-V0-VERIFIED-PYTHON-POC", "primary_only"
    if task_id == "L8-VPY-01-NOTE-VERIFIED-CANARY":
        return "GOAL-V0A-FIRST-VERIFIED-README", "primary_only"
    if task_id == "L8-VPY-02-PAGE-PDF-VERIFIED-CANARIES":
        return "GOAL-V0B-POST-PYTHON-SLICES", "primary_only"
    if task_id == "L8-VPY-04-PRODUCTION-TRANSPORT":
        return "GOAL-V0B-POST-PYTHON-SLICES", "primary_only"
    if task_id == "L8-VPY-05-PRODUCTION-ADMISSION":
        return "GOAL-V0B-POST-PYTHON-SLICES", "primary_only"
    if task_id == "L8-VNET-01-ACCELERATED-LOCAL-NO-OP":
        return "GOAL-V0B-POST-PYTHON-SLICES", "repository_local_write_isolated"
    if task_id == "L8-VNET-02-PRODUCTION-TRANSPORT":
        return "GOAL-V0B-POST-PYTHON-SLICES", "primary_only"
    if task_id.startswith("L8-VPY-"):
        return "GOAL-V0-VERIFIED-PYTHON-POC", "primary_only"
    if task_id == "L8-ACCEL-00-PYTHON-READINESS":
        return "GOAL-V0A-FIRST-VERIFIED-README", "primary_only"
    if task_id == "L8-TRUTH-08-FULL-REGISTRY":
        return "GOAL-V2-VERIFIED-GATE-A", "read_only_assurance_isolated"
    if task_id.startswith("TRP-04P-"):
        return "GOAL-TP-TRUSTED-COHORT-POC", "primary_only"
    if task_id == "TRP-04-CANARY-QUALIFICATION":
        return "GOAL-T0R-TRUSTED-ADVERSARIAL-QUALIFICATION", "primary_only"
    if task_id.startswith(("TRP-00", "TRP-01", "TRP-02", "TRP-03")):
        return "GOAL-T0-TRUSTED-QUALIFICATION", "primary_only"
    if task_id.startswith("L8-INTAKE-"):
        return "GOAL-C0-AUTHORIZED-PORTFOLIO", "read_only_assurance_isolated"
    if task_id == "TRP-05-FULL-REGISTRY-TRANSFORM":
        return "GOAL-T1-TRUSTED-PORTFOLIO", "primary_only"
    if task_id.startswith(("TRP-05A-", "TRP-05B-")):
        return "GOAL-T2-WORKFLOW-STAGING", "primary_only"
    if task_id.startswith(("TRP-05C-", "TRP-06-", "TRP-07-")):
        return "GOAL-T3-HOSTED-TRUSTED-DELIVERY", "primary_only"
    if task_id.startswith(("L8-MISSION-", "L8-REQUIREMENT-", "L8-WAVE0-")):
        return "GOAL-P0-PLAN-FREEZE", "primary_only"
    if task_id in {"L8-WAVE1-CANONICAL-SAFETY-SPINE", "L8-PREPRODUCTION-TRUTHFUL-BASELINE"}:
        return "GOAL-V1-VERIFIED-TRUTH", "read_only_assurance_isolated"
    if task_id in {
        "L8-WAVE2-RESTARTABLE-ACTIONS-RUNTIME",
        "L8-PREPRODUCTION-IDEA-FIDELITY-GATE",
    }:
        return "GOAL-V3-HUMAN-AND-JAVA-PROOF", "primary_only"
    if task_id.startswith(
        (
            "L8-WAVE3-",
            "L8-LOCAL-IMMUTABLE-",
            "L8-LOCAL-PORTFOLIO-RUNTIME",
            "L8-TRUTH-",
            "L8-LOCAL-PORTFOLIO-PRODUCT-TRUTH",
        )
    ):
        return "GOAL-V1-VERIFIED-TRUTH", "read_only_assurance_isolated"
    if task_id.startswith(
        (
            "L8-WAVE4-",
            "L8-LOCAL-README-PROPOSAL-",
            "L8-COMPOSE-",
            "L8-REVIEW-",
            "L8-QUAL-",
            "L8-ACCEL-",
            "L8-GATEA-",
            "L8-LOCAL-README-ASSESSMENT-",
            "L8-LOCAL-INDEPENDENT-",
            "L8-LOCAL-HETEROGENEOUS-",
            "L8-LOCAL-FULL-REGISTRY-",
            "L8-LOCAL-CENTRAL-AGENT-",
        )
    ):
        return "GOAL-V2-VERIFIED-GATE-A", "read_only_assurance_isolated"
    if task_id.startswith(
        (
            "L8-LOCAL-HUMAN-",
            "L8-ACT-",
            "L8-STAGING-",
            "L8-WAVE5-",
            "L8-GATE-C-",
            "L8-GATE-D-",
        )
    ):
        return "GOAL-V3-HUMAN-AND-JAVA-PROOF", "primary_only"
    if task_id.startswith("L8-WAVE6-"):
        return "GOAL-L5-PRESENTATION-PILOT", "primary_only"
    if task_id == "L8-WAVE7-LEVEL6-AUTONOMOUS-PORTFOLIO":
        return "GOAL-L6-AUTONOMOUS-PORTFOLIO", "primary_only"
    if task_id == "L8-WAVE7-HETEROGENEOUS-PORTFOLIO":
        return "GOAL-L7-HETEROGENEOUS-30D", "primary_only"
    if task_id == "L8-WAVE8-NINETY-DAY-SELF-MAINTENANCE":
        return "GOAL-L8-SELF-MAINTAINING-90D", "primary_only"
    raise ValueError(f"no stage-goal mapping declared for task {task_id!r}")


def task_campaign(task_id: str, stage_goal_id: str) -> str | None:
    """Map every executable task to exactly one governed campaign."""

    if stage_goal_id.startswith("GOAL-T"):
        return None
    if stage_goal_id == "GOAL-P0-PLAN-FREEZE":
        return "CAMP-PLAN-FREEZE"
    if task_id in {
        "L8-VPY-00-GOLDEN-TEMPLATE",
        "L8-ACCEL-00-PYTHON-READINESS",
        "L8-AGILE-AUTHORITY-RESET",
        "L8-WAVE1-CANONICAL-SAFETY-SPINE",
        "L8-PREPRODUCTION-TRUTHFUL-BASELINE",
        "L8-REVIEW-00-CONTEXT-CORPUS",
        "L8-REVIEW-01-FREEZE-ROLES",
    } or task_id.startswith("L8-INTAKE-"):
        return "CAMP-SHARED-ACCELERATION"
    if task_id in {
        "L8-VPY-02-PAGE-PDF-VERIFIED-CANARIES",
        "L8-VNET-01-ACCELERATED-LOCAL-NO-OP",
    }:
        return "CAMP-THREE-SLICES"
    if task_id in {
        "L8-VPY-04-PRODUCTION-TRANSPORT",
        "L8-VPY-05-PRODUCTION-ADMISSION",
        "L8-VNET-02-PRODUCTION-TRANSPORT",
    }:
        return "CAMP-GATE-B-AND-LATER"
    if task_id == "L8-VPY-01-NOTE-VERIFIED-CANARY":
        return "CAMP-FIRST-PYTHON-SLICE"
    if task_id in {
        "L8-VPY-03B-FIRST-CURRENT-PYTHON-E2E",
        "L8-VPY-00-PRESENTATION-CONTRACT-RESET",
        "L8-VPY-03A-PAGE-PDF-VERIFIED-CANARIES",
        "L8-VPY-03C-PAGE-CURRENT-REFRESH",
        "L8-VPY-03D-NOTE-CURRENT-REFRESH",
        "L8-VPY-03E-3D-CURRENT-REFRESH",
        "L8-VPY-03-ALL-PYTHON-VERIFIED-POC",
        "L8-ACCEL-02-EIGHT-PYTHON",
        "L8-ACCEL-03-ALL-PYTHON",
    }:
        return "CAMP-PYTHON-PORTFOLIO"
    if stage_goal_id in {
        "GOAL-V3-HUMAN-AND-JAVA-PROOF",
        "GOAL-L5-PRESENTATION-PILOT",
        "GOAL-L6-AUTONOMOUS-PORTFOLIO",
        "GOAL-L7-HETEROGENEOUS-30D",
        "GOAL-L8-SELF-MAINTAINING-90D",
    }:
        return "CAMP-GATE-B-AND-LATER"
    return "CAMP-GATE-A-PORTFOLIO"


def bind_stage_goals(graph: dict) -> None:
    """Add deterministic stage ownership and reject backward goal dependencies."""

    tasks = {task["task_id"]: task for task in graph.get("taskcards", [])}
    for task in tasks.values():
        stage_goal_id, concurrency_class = task_stage_goal(task["task_id"])
        task["stage_goal_id"] = stage_goal_id
        task["concurrency_class"] = concurrency_class
        task["campaign_id"] = task_campaign(task["task_id"], stage_goal_id)
    violations = []
    for task in tasks.values():
        task_order = STAGE_GOAL_ORDER[task["stage_goal_id"]]
        for dependency_id in task.get("dependencies", []):
            dependency = tasks[dependency_id]
            dependency_order = STAGE_GOAL_ORDER[dependency["stage_goal_id"]]
            if "GOAL-C0-AUTHORIZED-PORTFOLIO" in {
                task["stage_goal_id"],
                dependency["stage_goal_id"],
            }:
                continue
            # These delivered umbrella tasks predate the stage catalog and retain
            # dependency edges into rerouted descendants. Durable state governs
            # their closure and any later regression.
            if task["task_id"].startswith(("L8-WAVE", "L8-PREPRODUCTION-")):
                continue
            if dependency_order > task_order:
                violations.append(
                    f"{task['task_id']}({task_order}) depends on "
                    f"{dependency_id}({dependency_order})"
                )
    if violations:
        raise ValueError(f"stage-goal dependency order violations: {violations}")


def canonical_text_sha256(path: Path) -> str:
    """Hash UTF-8 text after normalizing checkout-specific line endings."""
    text = path.read_text(encoding="utf-8")
    canonical_text = text.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(canonical_text.encode("utf-8")).hexdigest()


ID_RE = re.compile(r"^[A-Z][A-Z0-9]{1,4}-\d{3}$")
UNESCAPED_PIPE_RE = re.compile(r"(?<!\\)\|")

PREFIX_TO_TASK = {
    "GOV": "L8-WAVE0-PLAN-TRUTH-RECONCILIATION",
    "BIZ": "L8-WAVE0-PLAN-TRUTH-RECONCILIATION",
    "AGT": "L8-WAVE1-CANONICAL-SAFETY-SPINE",
    "CAP": "L8-WAVE1-CANONICAL-SAFETY-SPINE",
    "CORE": "L8-WAVE1-CANONICAL-SAFETY-SPINE",
    "GAP": "L8-WAVE1-CANONICAL-SAFETY-SPINE",
    "ORC": "L8-WAVE1-CANONICAL-SAFETY-SPINE",
    "VER": "L8-WAVE1-CANONICAL-SAFETY-SPINE",
    "EVID": "L8-WAVE2-RESTARTABLE-ACTIONS-RUNTIME",
    "FRESH": "L8-WAVE2-RESTARTABLE-ACTIONS-RUNTIME",
    "MEM": "L8-WAVE2-RESTARTABLE-ACTIONS-RUNTIME",
    "OPS": "L8-WAVE2-RESTARTABLE-ACTIONS-RUNTIME",
    "RUN": "L8-WAVE2-RESTARTABLE-ACTIONS-RUNTIME",
    "SCL": "L8-WAVE2-RESTARTABLE-ACTIONS-RUNTIME",
    "ECO": "L8-WAVE3-PRODUCT-TRUTH-OWNERSHIP",
    "FACT": "L8-WAVE3-PRODUCT-TRUTH-OWNERSHIP",
    "OWN": "L8-WAVE3-PRODUCT-TRUTH-OWNERSHIP",
    "PKG": "L8-WAVE3-PRODUCT-TRUTH-OWNERSHIP",
    "DOC": "L8-WAVE4-PRESENTATION-INTELLIGENCE",
    "LLM": "L8-WAVE4-PRESENTATION-INTELLIGENCE",
    "MET": "L8-WAVE4-PRESENTATION-INTELLIGENCE",
    "NFR": "L8-WAVE4-PRESENTATION-INTELLIGENCE",
    "RDM": "L8-WAVE4-PRESENTATION-INTELLIGENCE",
    "SURF": "L8-WAVE4-PRESENTATION-INTELLIGENCE",
    "VAL": "L8-WAVE4-PRESENTATION-INTELLIGENCE",
    "AUTH": "L8-WAVE5-VERIFIED-PROPOSAL-LIFECYCLE",
    "EFF": "L8-WAVE5-VERIFIED-PROPOSAL-LIFECYCLE",
    "INT": "L8-WAVE5-VERIFIED-PROPOSAL-LIFECYCLE",
    "PRL": "L8-WAVE5-VERIFIED-PROPOSAL-LIFECYCLE",
    "SAFE": "L8-WAVE5-VERIFIED-PROPOSAL-LIFECYCLE",
    "PIL": "L8-WAVE6-CONTROLLED-JAVA-PILOT",
    "ONB": "L8-WAVE7-HETEROGENEOUS-PORTFOLIO",
    "DEP": "L8-WAVE8-NINETY-DAY-SELF-MAINTENANCE",
}

L8_TO_TASK = {
    "AUTH-008": "TRP-05C-GITHUB-APP-HOSTED-QUALIFICATION",
    "NFR-014": "TRP-04P-TEST-LATENCY",
    "RDM-026": "L8-VPY-03-ALL-PYTHON-VERIFIED-POC",
    "L8-001": "L8-GATE-D-GITHUB-APP-INTEGRATION",
    "L8-002": "L8-WAVE1-CANONICAL-SAFETY-SPINE",
    "L8-003": "L8-WAVE2-RESTARTABLE-ACTIONS-RUNTIME",
    "L8-004": "L8-WAVE2-RESTARTABLE-ACTIONS-RUNTIME",
    "L8-005": "L8-WAVE2-RESTARTABLE-ACTIONS-RUNTIME",
    "L8-006": "L8-WAVE3-PRODUCT-TRUTH-OWNERSHIP",
    "L8-007": "L8-WAVE4-PRESENTATION-INTELLIGENCE",
    "L8-008": "L8-WAVE5-VERIFIED-PROPOSAL-LIFECYCLE",
    "L8-009": "L8-WAVE5-VERIFIED-PROPOSAL-LIFECYCLE",
    "L8-010": "L8-WAVE7-HETEROGENEOUS-PORTFOLIO",
    "L8-011": "L8-WAVE8-NINETY-DAY-SELF-MAINTENANCE",
    "L8-012": "L8-WAVE4-PRESENTATION-INTELLIGENCE",
    "L8-013": "L8-WAVE1-CANONICAL-SAFETY-SPINE",
    "L8-014": "L8-PREPRODUCTION-IDEA-FIDELITY-GATE",
    "L8-015": "L8-TRUTH-01-STAGE-LIMIT",
    "L8-016": "L8-QUAL-01-CAMPAIGN-IDENTITY",
    "L8-017": "L8-QUAL-03-RECOVERY",
    "L8-018": "L8-TRUTH-01A-FACT-CONTRACT",
    "L8-019": "L8-TRUTH-03A-ISOLATED-EXECUTOR",
    "L8-020": "L8-COMPOSE-02B-FINAL-CLAIM-CORPUS",
    "L8-021": "L8-COMPOSE-01B-HEADER-VISUAL-CONTRACT",
    "L8-022": "L8-COMPOSE-01C-CONTEXTUAL-LINKING",
    "L8-023": "L8-COMPOSE-01C-CONTEXTUAL-LINKING",
    "L8-024": "L8-COMPOSE-01C-CONTEXTUAL-LINKING",
    "L8-025": "TRP-00-ASSURANCE-CONTRACT",
    "L8-026": "L8-COMPOSE-01C-CONTEXTUAL-LINKING",
    "L8-027": "L8-TRUTH-01B-LLM-CALL-LEDGER",
    "L8-028": "L8-TRUTH-01C-PROMPT-HYGIENE",
    "L8-029": "L8-TRUTH-02A-ASPOSE-ORG-ADAPTATION",
    "L8-030": "L8-TRUTH-02B-PYTHON-API-TRUTH",
    "L8-031": "L8-TRUTH-02C-TYPESCRIPT-EXPORT-TRUTH",
    "L8-032": "L8-TRUTH-02D-RUST-API-TRUTH",
    "L8-033": "L8-TRUTH-02-ROOT-ROLES",
    "L8-034": "L8-TRUTH-07-SEVEN-ECOSYSTEMS",
    "L8-035": "L8-INTAKE-00-DISCOVERY-TRUTH-AND-SAFETY",
    "L8-036": "L8-INTAKE-01-STABLE-IDENTITY-AND-RECONCILIATION",
    "L8-037": "L8-INTAKE-02-READONLY-PREFLIGHT-ENROLLMENT",
    "L8-038": "L8-INTAKE-03-REGISTRY-REVISION-QUEUE-AND-HEALTH",
    "L8-039": "L8-INTAKE-03-REGISTRY-REVISION-QUEUE-AND-HEALTH",
    "L8-040": "L8-WAVE7-LEVEL6-AUTONOMOUS-PORTFOLIO",
    "L8-041": "L8-COMPOSE-01B-HEADER-VISUAL-CONTRACT",
    "L8-042": "L8-VPY-00-GOLDEN-TEMPLATE",
    "L8-043": "L8-VPY-02-PAGE-PDF-VERIFIED-CANARIES",
    "L8-044": "L8-PLAN-RECONCILIATION-ACCELERATION",
    "L8-045": "L8-TRUTH-03A-ISOLATED-EXECUTOR",
    "L8-046": "L8-VPY-03B-FIRST-CURRENT-PYTHON-E2E",
    "L8-047": "L8-AGILE-AUTHORITY-RESET",
    "L8-048": "L8-AGILE-AUTHORITY-RESET",
    "L8-049": "L8-AGILE-AUTHORITY-RESET",
    "L8-050": "L8-AGILE-AUTHORITY-RESET",
    "L8-051": "L8-AGILE-AUTHORITY-RESET",
    "L8-052": "L8-AGILE-AUTHORITY-RESET",
    "L8-053": "L8-AGILE-AUTHORITY-RESET",
    "L8-054": "L8-AGILE-AUTHORITY-RESET",
    "L8-055": "L8-VPY-03B-FIRST-CURRENT-PYTHON-E2E",
    "PIL-016": "L8-GATE-C-VERIFIED-JAVA-PROPOSAL-PROOF",
    "TRP-001": "TRP-00-ASSURANCE-CONTRACT",
    "TRP-002": "TRP-01-README-DERIVED-FACTS",
    "TRP-003": "TRP-01-README-DERIVED-FACTS",
    "TRP-004": "TRP-02-LLM-FIRST-COMPOSITION",
    "TRP-005": "TRP-02-LLM-FIRST-COMPOSITION",
    "TRP-006": "TRP-03-INDEPENDENT-FIDELITY-REVIEW",
    "TRP-007": "TRP-03-INDEPENDENT-FIDELITY-REVIEW",
    "TRP-008": "TRP-04-CANARY-QUALIFICATION",
    "TRP-009": "TRP-05-FULL-REGISTRY-TRANSFORM",
    "TRP-012": "TRP-05A-ACT-WORKFLOW-PARITY",
    "TRP-013": "TRP-05B-STAGING-EFFECT-PROOF",
    "TRP-014": "TRP-05C-GITHUB-APP-HOSTED-QUALIFICATION",
    "TRP-015": "TRP-00-ASSURANCE-CONTRACT",
    "TRP-016": "TRP-04P-COHORT-FREEZE",
    "TRP-017": "TRP-04P-GITHUB-APP-HOSTED-QUALIFICATION",
    "TRP-018": "TRP-04P-DRAFT-PR-COHORT",
    "TRP-019": "TRP-04P-POC-PRESENTATION",
    "TRP-020": "TRP-04P-COHERENT-PRESENTATION-REPAIR",
    "TRP-021": "TRP-04P-COHERENT-PRESENTATION-REPAIR",
    "TRP-022": "TRP-04P-COHERENT-PRESENTATION-REPAIR",
    "TRP-023": "TRP-04P-COHERENT-PRESENTATION-REPAIR",
    "TRP-010": "TRP-06-AUTHORIZATION-ACCESS",
    "TRP-011": "TRP-07-DRAFT-PR-PORTFOLIO",
}


def _split_row(line: str) -> list[str]:
    stripped = line.strip().removeprefix("|").removesuffix("|")
    return [cell.strip() for cell in UNESCAPED_PIPE_RE.split(stripped)]


def _requirement_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in REQUIREMENTS_PATH.read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        record = json.loads(line)
        requirement_id = record["requirement_id"]
        if not ID_RE.fullmatch(requirement_id):
            raise ValueError(f"invalid typed requirement ID {requirement_id!r}")
        rows.append(
            {
                "requirement_id": requirement_id,
                "priority": record["priority"],
                "requirement_status": record["status"],
            }
        )
    return rows


def _semantic_findings() -> dict[str, list[str]]:
    matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    return {
        row["id"]: row["high_confidence_findings"]
        for row in matrix["rows_with_high_confidence_findings"]
    }


def _disposition(row: dict[str, str], findings: list[str]) -> str:
    status = row["requirement_status"]
    if status == "BACKLOG":
        return "excluded_backlog"
    if status == "DEPRECATED":
        return "excluded_deprecated"
    if status == "GOVERNANCE":
        return "active_governance"
    if status == "IMPLEMENTED":
        return "reopened_semantic_evidence_gap" if findings else "preserved_verified"
    return "open_mandatory"


def _load_deferred_records() -> list[dict]:
    return [
        json.loads(line)
        for line in DEFERRED_TASK_CATALOG_PATH.read_text(encoding="utf-8").splitlines()
        if line
    ]


def _jsonl_payload(records: list[dict]) -> bytes:
    return (
        "\n".join(json.dumps(record, sort_keys=True, separators=(",", ":")) for record in records)
        + "\n"
    ).encode("utf-8")


def _reference(path: Path, payload: bytes, record_count: int) -> dict:
    return {
        "path": str(path.relative_to(REPO_ROOT)).replace("\\", "/"),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "record_count": record_count,
    }


def build_coverage() -> tuple[dict, list[dict], dict]:
    graph = yaml.safe_load(GRAPH_PATH.read_text(encoding="utf-8"))
    deferred_records = _load_deferred_records()
    combined = {
        **graph,
        "taskcards": [
            *graph.get("taskcards", []),
            *(record["task"] for record in deferred_records),
        ],
    }
    bind_stage_goals(combined)
    active_ids = {task["task_id"] for task in graph.get("taskcards", [])}
    graph["taskcards"] = [task for task in combined["taskcards"] if task["task_id"] in active_ids]
    updated_by_id = {task["task_id"]: task for task in combined["taskcards"]}
    for record in deferred_records:
        record["task"] = updated_by_id[record["task"]["task_id"]]
    if graph["mission_authority"]["mission_id"] != "LEVEL8-CENTRAL-REPOSITORY-PRESENTATION":
        raise ValueError("refusing to update a different mission graph")
    tasks = {task["task_id"]: task for task in combined["taskcards"]}
    unknown_targets = (set(PREFIX_TO_TASK.values()) | set(L8_TO_TASK.values())) - set(tasks)
    if unknown_targets:
        raise ValueError(f"mapping references unknown taskcards: {sorted(unknown_targets)}")

    rows = _requirement_rows()
    findings_by_id = _semantic_findings()
    mapped_by_task: dict[str, list[str]] = {task_id: [] for task_id in tasks}
    mappings = []
    for row in rows:
        prefix = row["requirement_id"].split("-", 1)[0]
        task_id = L8_TO_TASK.get(row["requirement_id"], PREFIX_TO_TASK.get(prefix))
        if task_id is None:
            raise ValueError(f"no task mapping declared for requirement prefix {prefix!r}")
        findings = findings_by_id.get(row["requirement_id"], [])
        disposition = _disposition(row, findings)
        mappings.append(
            {
                **row,
                "task_id": task_id,
                "disposition": disposition,
                "semantic_findings": findings,
            }
        )
        mapped_by_task[task_id].append(row["requirement_id"])

    for task_id, task in tasks.items():
        task["requirement_ids"] = mapped_by_task[task_id]

    dispositions = [mapping["disposition"] for mapping in mappings]
    coverage = {
        "source_path": "plans/requirements/catalog.jsonl",
        "source_sha256": canonical_text_sha256(REQUIREMENTS_PATH),
        "semantic_matrix_path": (
            "plans/investigations/evidence/implementation-truth-matrix-2026/matrix.json"
        ),
        "total_requirement_rows": len(mappings),
        "mandatory_requirement_rows": sum(
            disposition not in {"excluded_backlog", "excluded_deprecated"}
            for disposition in dispositions
        ),
        "excluded_backlog_rows": dispositions.count("excluded_backlog"),
        "excluded_deprecated_rows": dispositions.count("excluded_deprecated"),
        "reopened_implemented_rows": dispositions.count("reopened_semantic_evidence_gap"),
        "mappings": mappings,
    }
    report = {
        "schema_version": 1,
        "producer": "scripts/governance/build_level8_requirement_taskcard_coverage.py",
        "mission_id": graph["mission_authority"]["mission_id"],
        "graph_path": str(GRAPH_PATH.relative_to(REPO_ROOT)).replace("\\", "/"),
        **{key: value for key, value in coverage.items() if key != "mappings"},
        "disposition_counts": {
            disposition: dispositions.count(disposition)
            for disposition in sorted(set(dispositions))
        },
        "taskcard_counts": {
            task_id: len(requirement_ids)
            for task_id, requirement_ids in mapped_by_task.items()
            if requirement_ids
        },
        "unmapped_requirement_ids": [],
        "duplicate_requirement_ids": [],
        "mappings": mappings,
    }
    deferred_payload = _jsonl_payload(deferred_records)
    deferred_lines = deferred_payload.decode("utf-8").splitlines()
    graph["deferred_task_catalog"] = _reference(
        DEFERRED_TASK_CATALOG_PATH, deferred_payload, len(deferred_records)
    )
    graph["deferred_task_index"] = [
        {
            "task_id": record["task"]["task_id"],
            "status": (
                "DEFERRED_WITH_REASON"
                if record["activation_group"] == "historical-control"
                else record["task"]["status"]
            ),
            "stage_goal_id": record["task"]["stage_goal_id"],
            "activation_group": record["activation_group"],
            "record_sha256": hashlib.sha256(line.encode("utf-8")).hexdigest(),
        }
        for record, line in zip(deferred_records, deferred_lines, strict=True)
    ]
    requirement_payload = REQUIREMENTS_PATH.read_bytes()
    graph["requirement_catalog"] = _reference(REQUIREMENTS_PATH, requirement_payload, len(rows))
    report_payload = (json.dumps(report, indent=2) + "\n").encode("utf-8")
    graph["requirement_coverage"] = {
        **_reference(REPORT_PATH, report_payload, len(mappings)),
        "mandatory_requirement_rows": coverage["mandatory_requirement_rows"],
        "reopened_implemented_rows": coverage["reopened_implemented_rows"],
    }
    return graph, deferred_records, report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    graph, deferred_records, report = build_coverage()

    if args.check:
        current = yaml.safe_load(GRAPH_PATH.read_text(encoding="utf-8"))
        current_task_goals = {
            task["task_id"]: (task.get("stage_goal_id"), task.get("concurrency_class"))
            for task in current.get("taskcards", [])
        }
        expected_task_goals = {
            task["task_id"]: (task["stage_goal_id"], task["concurrency_class"])
            for task in graph["taskcards"]
        }
        if current_task_goals != expected_task_goals:
            print("Level-8 task stage-goal bindings are stale")
            return 1
        if current.get("requirement_coverage") != graph["requirement_coverage"]:
            print("Level-8 requirement coverage is stale")
            return 1
        if current.get("requirement_catalog") != graph["requirement_catalog"]:
            print("Level-8 requirement catalog reference is stale")
            return 1
        if current.get("deferred_task_catalog") != graph["deferred_task_catalog"]:
            print("Level-8 deferred-task catalog reference is stale")
            return 1
        if current.get("deferred_task_index") != graph["deferred_task_index"]:
            print("Level-8 deferred-task index is stale")
            return 1
        expected_deferred = _jsonl_payload(deferred_records)
        if DEFERRED_TASK_CATALOG_PATH.read_bytes() != expected_deferred:
            print("Level-8 deferred-task catalog mappings are stale")
            return 1
        if (
            not REPORT_PATH.exists()
            or json.loads(REPORT_PATH.read_text(encoding="utf-8")) != report
        ):
            print("Level-8 requirement coverage report is stale")
            return 1
        print(f"Level-8 requirement coverage current: {report['total_requirement_rows']} rows")
        return 0

    GRAPH_PATH.write_text(
        yaml.safe_dump(graph, sort_keys=False, allow_unicode=True, width=100),
        encoding="utf-8",
    )
    DEFERRED_TASK_CATALOG_PATH.write_bytes(_jsonl_payload(deferred_records))
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_bytes((json.dumps(report, indent=2) + "\n").encode("utf-8"))
    print(f"Mapped {report['total_requirement_rows']} requirement rows")
    print(f"Mandatory: {report['mandatory_requirement_rows']}")
    print(f"Reopened IMPLEMENTED: {report['reopened_implemented_rows']}")
    print(f"Written: {GRAPH_PATH.relative_to(REPO_ROOT)}")
    print(f"Written: {REPORT_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
