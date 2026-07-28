"""Negative controls for assessment-to-operation execution."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from readme_agent.errors import LLMError
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.agentic_composition_models import AgenticSectionDecisionV1
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
from readme_agent.readme.document_validation import validate_readme_document_candidate

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROOF_PATH = (
    PROJECT_ROOT
    / "plans"
    / "investigations"
    / "evidence"
    / "level8-local-immutable-snapshot-and-facts-corrected-acquisition-2026-07-24"
    / "immutable-snapshot-and-product-facts-proof.json"
)


def _facts() -> tuple[ProductFactsV2, str]:
    proof = json.loads(PROOF_PATH.read_text(encoding="utf-8"))
    pilot = next(
        item
        for item in proof["current_pilots"]
        if item["org_repo"] == "aspose-cells-foss/Aspose.Cells-FOSS-for-Java"
    )
    return (
        ProductFactsV2.model_validate(pilot["product_facts_v2"]),
        pilot["snapshot"]["source_revision"],
    )


def test_multiple_unverified_usage_examples_fail_closed_instead_of_competing():
    facts, revision = _facts()
    source = """# Aspose.Cells FOSS for Java

## Usage

```java
Workbook first = Workbook.load("one.xlsx");
```

```java
Workbook second = Workbook.load("two.xlsx");
```
"""

    candidate, plan = build_readme_document_candidate(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
    )
    decision = validate_readme_document_candidate(source, candidate, plan, facts)

    assert decision.valid is False
    assert decision.checks["verified_example_present"] is True
    assert decision.checks["no_competing_examples"] is False
    assert any("competing code examples" in error for error in decision.errors)


def _actionable_usage(source: str, disposition: str):
    facts, revision = _facts()
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
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
    decision = AgenticSectionDecisionV1(
        section_id=usage.section_id,
        disposition=disposition,
        priority=100,
        rationale="controlled operation-coverage regression",
    )
    return rebound, actionable, decision


def test_advisory_usage_rewrite_cannot_be_satisfied_by_inserting_a_competing_example():
    source_text = "# Product\n\n## Usage\n\nExisting example.\n"
    source = source_text.encode("utf-8")
    assessment, usage, decision = _actionable_usage(source_text, "rewrite")
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

    with pytest.raises(LLMError, match="actionable decisions without bounded operations"):
        validate_agentic_operation_coverage(assessment, [decision], [insertion])


@pytest.mark.parametrize(
    ("disposition", "operation", "replacement"),
    [
        ("rewrite", "replace", "## Usage\n\nVerified example.\n"),
        ("remove_update", "remove", ""),
    ],
)
def test_update_and_remove_decisions_require_and_accept_exact_span_edits(
    disposition: str,
    operation: str,
    replacement: str,
):
    source_text = "# Product\n\n## Usage\n\nStale guidance.\n"
    source = source_text.encode("utf-8")
    assessment, usage, decision = _actionable_usage(source_text, disposition)
    bounded = build_operation(
        operation_id=f"readme.usage.{operation}",
        operation=operation,
        source=source,
        start=usage.source_byte_start,
        end=usage.source_byte_end,
        replacement=replacement,
        fact_ids=[],
        treatment="presentation_policy_correction",
        rationale="Controlled exact-span operation.",
    )

    validate_agentic_operation_coverage(assessment, [decision], [bounded])
    rendered = apply_document_operations(source, [bounded])

    assert rendered != source
    assert rendered == (
        source[: usage.source_byte_start]
        + replacement.encode("utf-8")
        + source[usage.source_byte_end :]
    )


def test_noop_move_cannot_cover_an_actionable_section():
    source_text = "# Product\n\n## Usage\n\nStale guidance.\n"
    source = source_text.encode("utf-8")
    assessment, usage, decision = _actionable_usage(source_text, "rewrite")
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

    operations = prune_noop_operations(source, [noop_move])

    assert operations == []
    with pytest.raises(LLMError, match="actionable decisions without bounded operations"):
        validate_agentic_operation_coverage(assessment, [decision], operations)


def test_operation_hash_and_reconstruction_bind_to_the_immutable_source():
    source_text = "# Product\n\n## Usage\n\nStale guidance.\n"
    source = source_text.encode("utf-8")
    _, usage, _ = _actionable_usage(source_text, "rewrite")
    replacement = "## Usage\n\nVerified example.\n"
    operation = build_operation(
        operation_id="readme.usage.verified-rewrite",
        operation="replace",
        source=source,
        start=usage.source_byte_start,
        end=usage.source_byte_end,
        replacement=replacement,
        fact_ids=[],
        treatment="presentation_policy_correction",
        rationale="Controlled reconstruction proof.",
    )
    expected = (
        source[: usage.source_byte_start]
        + replacement.encode("utf-8")
        + source[usage.source_byte_end :]
    )

    assert apply_document_operations(source, [operation]) == expected
    with pytest.raises(ValueError, match="source span changed"):
        apply_document_operations(source.replace(b"Stale", b"Other"), [operation])
