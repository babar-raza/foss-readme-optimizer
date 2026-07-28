"""Reusable helpers for operation and claim-accountability enforcement evidence."""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
TASK_ID = "L8-COMPOSE-03-OPERATION-COVERAGE"
GRAPH_PATH = REPO_ROOT / "plans/investigations/control/level8-autonomous-mission-task-graph.yaml"
OUTPUT_ROOT = REPO_ROOT / "plans/investigations/evidence/level8-operation-accountability"
FOCUSED_TEST_COMMAND = (
    sys.executable,
    "-m",
    "pytest",
    "-q",
    "tests/unit/test_readme_final_claim_corpus.py",
    "tests/unit/test_readme_operation_regressions.py",
    "tests/unit/test_readme_document_operations.py",
    "tests/unit/test_readme_document_plan.py",
    "tests/unit/test_agentic_readme_composition.py",
    "tests/unit/test_presentation_planner.py",
    "tests/unit/test_readme_proposal_bundle_verifier.py",
    "tests/unit/test_local_poc_evidence.py",
)


def run_focused_tests() -> dict:
    result = subprocess.run(
        FOCUSED_TEST_COMMAND,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return {
        "command": subprocess.list2cmdline(FOCUSED_TEST_COMMAND),
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def git_output(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()


def decision_operation_map(assessment, plan) -> list[dict]:
    records = []
    for section in assessment.sections:
        operations = [
            operation
            for operation in plan.operations
            if (
                operation.source_byte_start == operation.source_byte_end
                and section.source_byte_start
                <= operation.source_byte_start
                <= section.source_byte_end
            )
            or (
                operation.source_byte_start < section.source_byte_end
                and section.source_byte_start < operation.source_byte_end
            )
        ]
        records.append(
            {
                "section_id": section.section_id,
                "heading": section.heading,
                "disposition": section.disposition,
                "source_byte_start": section.source_byte_start,
                "source_byte_end": section.source_byte_end,
                "operation_ids": [operation.operation_id for operation in operations],
                "operation_kinds": [operation.operation for operation in operations],
                "source_span_hashes": [operation.expected_sha256 for operation in operations],
            }
        )
    return records


def verify_inventory() -> bool:
    for line in (OUTPUT_ROOT / "sha256sums.txt").read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", maxsplit=1)
        if hashlib.sha256((OUTPUT_ROOT / relative).read_bytes()).hexdigest() != expected:
            return False
    return True
