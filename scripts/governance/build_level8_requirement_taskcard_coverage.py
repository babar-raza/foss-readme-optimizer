"""Map every normative requirement into the one Level-8 mission task graph."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
REQUIREMENTS_PATH = REPO_ROOT / "plans" / "requirements.md"
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

ID_RE = re.compile(r"^[A-Z]{2,5}-\d{3}$")
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


def _split_row(line: str) -> list[str]:
    stripped = line.strip().removeprefix("|").removesuffix("|")
    return [cell.strip() for cell in UNESCAPED_PIPE_RE.split(stripped)]


def _requirement_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in REQUIREMENTS_PATH.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| "):
            continue
        cells = _split_row(line)
        if len(cells) != 6:
            continue
        requirement_id = cells[0].strip("`")
        if not ID_RE.fullmatch(requirement_id):
            continue
        rows.append(
            {
                "requirement_id": requirement_id,
                "priority": cells[1],
                "requirement_status": cells[2],
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


def build_coverage() -> tuple[dict, dict]:
    graph = yaml.safe_load(GRAPH_PATH.read_text(encoding="utf-8"))
    if graph["mission_authority"]["mission_id"] != "LEVEL8-CENTRAL-REPOSITORY-PRESENTATION":
        raise ValueError("refusing to update a different mission graph")
    tasks = {task["task_id"]: task for task in graph["taskcards"]}
    unknown_targets = set(PREFIX_TO_TASK.values()) - set(tasks)
    if unknown_targets:
        raise ValueError(f"mapping references unknown taskcards: {sorted(unknown_targets)}")

    rows = _requirement_rows()
    findings_by_id = _semantic_findings()
    mapped_by_task: dict[str, list[str]] = {task_id: [] for task_id in tasks}
    mappings = []
    for row in rows:
        prefix = row["requirement_id"].split("-", 1)[0]
        task_id = PREFIX_TO_TASK.get(prefix)
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
        "source_path": "plans/requirements.md",
        "source_sha256": hashlib.sha256(REQUIREMENTS_PATH.read_bytes()).hexdigest(),
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
    graph["requirement_coverage"] = coverage

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
    return graph, report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    graph, report = build_coverage()

    if args.check:
        current = yaml.safe_load(GRAPH_PATH.read_text(encoding="utf-8"))
        if current.get("requirement_coverage") != graph["requirement_coverage"]:
            print("Level-8 requirement coverage is stale")
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
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Mapped {report['total_requirement_rows']} requirement rows")
    print(f"Mandatory: {report['mandatory_requirement_rows']}")
    print(f"Reopened IMPLEMENTED: {report['reopened_implemented_rows']}")
    print(f"Written: {GRAPH_PATH.relative_to(REPO_ROOT)}")
    print(f"Written: {REPORT_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
