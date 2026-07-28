"""Reusable construction helpers for README operation-regression evidence."""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

from readme_agent.errors import LLMError
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.presentation.git_patch import (
    BoundedSourcePatchV1,
    SourceSpanEditV1,
    create_git_patch_proof,
    sha256_text,
)
from readme_agent.readme.agentic_operation_coverage import (
    validate_agentic_operation_coverage,
)
from readme_agent.readme.assessment import assess_readme_document
from readme_agent.readme.document_operations import (
    apply_document_operations,
    build_operation,
    prune_noop_operations,
)
from readme_agent.readme.document_renderer import build_readme_document_candidate

REPO_ROOT = Path(__file__).resolve().parents[3]
TASK_ID = "L8-COMPOSE-02A-OPERATION-REGRESSIONS"
SOURCE_REVISION = "2be25d979d1f3bf2875a1798aed62a16efab6619"
GRAPH_PATH = REPO_ROOT / "plans/investigations/control/level8-autonomous-mission-task-graph.yaml"
INPUT_ROOT = (
    REPO_ROOT / "plans/investigations/evidence/level8-contextual-linking/representatives/java"
)
OUTPUT_ROOT = REPO_ROOT / "plans/investigations/evidence/level8-readme-operation-regressions"
FOCUSED_TEST_COMMAND = (
    sys.executable,
    "-m",
    "pytest",
    "-q",
    "tests/unit/test_readme_operation_regressions.py",
    "tests/unit/test_agentic_readme_composition.py",
    "tests/unit/test_readme_document_operations.py",
    "tests/unit/test_readme_document_plan.py",
    "tests/unit/test_presentation_planner.py",
)


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
        purpose="record the operation-regression candidate without applying a remote effect",
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


def _usage_assessment(source_text: str, facts: ProductFactsV2, disposition: str):
    assessment = assess_readme_document(
        facts.org_repo,
        source_text,
        facts,
        base_revision=SOURCE_REVISION,
    )
    usage = next(section for section in assessment.sections if section.heading == "Usage")
    actionable = usage.model_copy(update={"disposition": disposition})
    rebound = assessment.model_copy(
        update={
            "sections": [
                actionable if section.section_id == usage.section_id else section
                for section in assessment.sections
            ]
        }
    )
    return (
        rebound,
        actionable,
        SimpleNamespace(
            section_id=usage.section_id,
            disposition=disposition,
        ),
    )


def build_operation_controls(facts: ProductFactsV2) -> dict:
    competing_source_text = """# Product

## Usage

```java
Workbook first = Workbook.load("one.xlsx");
```

```java
Workbook second = Workbook.load("two.xlsx");
```
"""
    competing_assessment = assess_readme_document(
        facts.org_repo,
        competing_source_text,
        facts,
        base_revision=SOURCE_REVISION,
    )
    _competing_candidate, competing_plan = build_readme_document_candidate(
        facts.org_repo,
        competing_source_text,
        facts,
        base_revision=SOURCE_REVISION,
    )
    competing_examples_rejected = False
    competing_examples_error = ""
    try:
        validate_agentic_operation_coverage(
            competing_assessment,
            competing_assessment.sections,
            competing_plan.operations,
        )
    except LLMError as exc:
        competing_examples_rejected = True
        competing_examples_error = str(exc)

    source_text = "# Product\n\n## Usage\n\nStale guidance.\n"
    source = source_text.encode("utf-8")
    assessment, usage, rewrite = _usage_assessment(source_text, facts, "rewrite")
    insertion = build_operation(
        operation_id="readme.example.competing-insert",
        operation="insert_after",
        source=source,
        start=usage.source_byte_end,
        end=usage.source_byte_end,
        replacement="\n```java\nnew Example();\n```\n",
        fact_ids=[],
        treatment="additive",
        rationale="Controlled invalid advisory-only rewrite.",
    )
    advisory_rejected = False
    advisory_error = ""
    try:
        validate_agentic_operation_coverage(assessment, [rewrite], [insertion])
    except LLMError as exc:
        advisory_rejected = True
        advisory_error = str(exc)

    exact_source = source[usage.source_byte_start : usage.source_byte_end].decode("utf-8")
    noop_move = build_operation(
        operation_id="readme.usage.noop-move",
        operation="move_exact",
        source=source,
        start=usage.source_byte_start,
        end=usage.source_byte_end,
        replacement=exact_source,
        fact_ids=[],
        treatment="preserve",
        rationale="Controlled decorative move that changes no bytes.",
    )
    pruned_moves = prune_noop_operations(source, [noop_move])
    noop_move_rejected = False
    try:
        validate_agentic_operation_coverage(assessment, [rewrite], pruned_moves)
    except LLMError:
        noop_move_rejected = True

    replacement = "## Usage\n\nVerified example.\n"
    replace = build_operation(
        operation_id="readme.usage.verified-rewrite",
        operation="replace",
        source=source,
        start=usage.source_byte_start,
        end=usage.source_byte_end,
        replacement=replacement,
        fact_ids=[],
        treatment="presentation_policy_correction",
        rationale="Controlled exact-span rewrite.",
    )
    validate_agentic_operation_coverage(assessment, [rewrite], [replace])
    reconstructed = apply_document_operations(source, [replace])
    expected = (
        source[: usage.source_byte_start]
        + replacement.encode("utf-8")
        + source[usage.source_byte_end :]
    )
    stale_hash_rejected = False
    try:
        apply_document_operations(source.replace(b"Stale", b"Other"), [replace])
    except ValueError:
        stale_hash_rejected = True

    remove_assessment, remove_usage, remove_decision = _usage_assessment(
        source_text,
        facts,
        "remove_update",
    )
    remove = build_operation(
        operation_id="readme.usage.remove-stale",
        operation="remove",
        source=source,
        start=remove_usage.source_byte_start,
        end=remove_usage.source_byte_end,
        replacement="",
        fact_ids=[],
        treatment="presentation_policy_correction",
        rationale="Controlled exact-span removal.",
    )
    validate_agentic_operation_coverage(remove_assessment, [remove_decision], [remove])
    removed = apply_document_operations(source, [remove])

    return {
        "source_sha256": hashlib.sha256(source).hexdigest(),
        "competing_examples_rejected": competing_examples_rejected,
        "competing_examples_error": competing_examples_error,
        "advisory_insert_rejected": advisory_rejected,
        "advisory_error": advisory_error,
        "noop_move_pruned": pruned_moves == [],
        "noop_move_rejected": noop_move_rejected,
        "replace_covered": reconstructed == expected and reconstructed != source,
        "replace_candidate_sha256": hashlib.sha256(reconstructed).hexdigest(),
        "remove_covered": removed != source and b"Stale guidance." not in removed,
        "remove_candidate_sha256": hashlib.sha256(removed).hexdigest(),
        "stale_span_hash_rejected": stale_hash_rejected,
        "byte_identical_reconstruction": reconstructed == expected,
    }


def verify_inventory() -> bool:
    for line in (OUTPUT_ROOT / "sha256sums.txt").read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", maxsplit=1)
        if hashlib.sha256((OUTPUT_ROOT / relative).read_bytes()).hexdigest() != expected:
            return False
    return True
