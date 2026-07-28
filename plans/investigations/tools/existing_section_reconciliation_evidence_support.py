"""Reusable construction helpers for existing-section reconciliation evidence."""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.presentation.git_patch import (
    BoundedSourcePatchV1,
    SourceSpanEditV1,
    create_git_patch_proof,
    sha256_text,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
TASK_ID = "L8-COMPOSE-02-EXISTING-SECTIONS"
SOURCE_REVISION = "6a209e8fc3dfc305df39a417037e32a4d4c7b2be"
GRAPH_PATH = REPO_ROOT / "plans/investigations/control/level8-autonomous-mission-task-graph.yaml"
INPUT_ROOT = (
    REPO_ROOT / "plans/investigations/evidence/level8-contextual-linking/representatives/net"
)
OUTPUT_ROOT = REPO_ROOT / "plans/investigations/evidence/level8-existing-section-reconciliation"
FOCUSED_TEST_COMMAND = (
    sys.executable,
    "-m",
    "pytest",
    "-q",
    "tests/unit/test_readme_existing_section_regressions.py",
    "tests/unit/test_readme_fact_grounding.py",
    "tests/unit/test_readme_assessment.py",
    "tests/unit/test_protected_content.py",
    "tests/unit/test_readme_factuality.py",
    "tests/unit/test_readme_document_plan.py",
    "tests/unit/test_readme_document_operations.py",
    "tests/unit/test_readme_document_structure.py",
    "tests/unit/test_agentic_readme_composition.py",
    "tests/unit/test_readme_header_visual.py",
    "tests/unit/test_readme_contextual_links.py",
    "tests/unit/test_local_poc_evidence.py",
    "tests/unit/test_readme_proposal_bundle_verifier.py",
    "tests/unit/test_supervise_readme_proposal_review_integration.py",
)
UNRESOLVED_SOURCE = """# Aspose.3D FOSS for .NET

Maintainer-authored product explanation.

## Installation

```bash
dotnet add package Unverified.Package
```

## Quick Start

```csharp
var unverified = Product.Create();
```

## Support

Open an issue with a reproducible case.
"""


def git_output(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()


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


def native_patch(source: str, candidate: str):
    edit = SourceSpanEditV1(
        path="README.md",
        byte_start=0,
        byte_end=len(source.encode("utf-8")),
        expected_sha256=sha256_text(source),
        replacement=candidate,
        purpose="apply the independently reconstructable section reconciliation",
    )
    return create_git_patch_proof(
        source,
        candidate,
        BoundedSourcePatchV1(
            path="README.md",
            source_sha256=sha256_text(source),
            edits=[edit],
        ),
    )


def block_fields(facts: ProductFactsV2, fields: set[str]) -> ProductFactsV2:
    replacements = {
        facts.selected_fact(field).fact_id: facts.selected_fact(field).model_copy(
            update={"verification_state": "blocked", "confidence": 0.0}
        )
        for field in fields
    }
    return facts.model_copy(
        update={"facts": [replacements.get(fact.fact_id, fact) for fact in facts.facts]}
    )


def section_operation_map(source: str, facts: ProductFactsV2, assessment, plan) -> list[dict]:
    records = []
    for section in assessment.sections:
        overlapping = [
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
        if not overlapping and section.disposition == "preserve":
            continue
        fact_ids = sorted({fact_id for operation in overlapping for fact_id in operation.fact_ids})
        records.append(
            {
                "section_id": section.section_id,
                "heading": section.heading,
                "source_byte_start": section.source_byte_start,
                "source_byte_end": section.source_byte_end,
                "source_sha256": hashlib.sha256(
                    source.encode("utf-8")[section.source_byte_start : section.source_byte_end]
                ).hexdigest(),
                "assessment_disposition": section.disposition,
                "assessment_fact_ids": section.fact_ids,
                "operation_ids": [operation.operation_id for operation in overlapping],
                "operation_fact_ids": fact_ids,
                "authoritative_owners": sorted(
                    {facts.fact_by_id(fact_id).authoritative_owner for fact_id in fact_ids}
                ),
                "uncertainty": (
                    section.rationale if section.disposition == "investigate" else None
                ),
                "protected_fragment_ids": section.protected_fragment_ids,
                "rationale": section.rationale,
            }
        )
    return records


def verify_inventory() -> bool:
    for line in (OUTPUT_ROOT / "sha256sums.txt").read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", maxsplit=1)
        if hashlib.sha256((OUTPUT_ROOT / relative).read_bytes()).hexdigest() != expected:
            return False
    return True
