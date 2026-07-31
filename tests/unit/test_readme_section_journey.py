"""Verified README core-section ordering and loss-bounded consolidation."""

from __future__ import annotations

import json
from pathlib import Path

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.document_renderer import build_readme_document_candidate
from readme_agent.readme.document_structure import parse_headings
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
    pilot = proof["current_pilots"][0]
    return (
        ProductFactsV2.model_validate(pilot["product_facts_v2"]),
        pilot["snapshot"]["source_revision"],
    )


def test_why_and_feature_sections_become_one_canonical_lossless_section():
    facts, revision = _facts()
    source = """# Product

## Why Product

- Create workbooks
- Read workbooks

Maintainer explanation remains useful.

## Installation

Existing installation guidance.

## Currently Available Features

- Create spreadsheets
- Update cell values

## Quick start

Existing quick start.
"""

    candidate, plan = build_readme_document_candidate(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
    )
    validation = validate_readme_document_candidate(source, candidate, plan, facts)
    h2s = [heading.title for heading in parse_headings(candidate) if heading.level == 2]

    assert validation.valid, validation.errors
    assert h2s[:5] == [
        "Navigation",
        "At a glance",
        "Key capabilities",
        "Installation",
        "Quick start",
    ]
    assert "## Why Product" not in candidate
    assert "## Currently Available Features" not in candidate
    assert "- Create spreadsheets\n- Update cell values" in candidate
    assert "<summary>Why Product</summary>" in candidate
    assert "- Create workbooks\n- Read workbooks" in candidate
    assert "Maintainer explanation remains useful." in candidate
    assert any(
        operation.operation_id == "readme.journey.key-capabilities" for operation in plan.operations
    )


def test_missing_source_capabilities_are_generated_from_accepted_facts():
    facts, revision = _facts()
    source = """# Product

## Installation

Existing installation guidance.

## Quick start

Existing quick start.
"""

    candidate, plan = build_readme_document_candidate(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
    )
    h2s = [heading.title for heading in parse_headings(candidate) if heading.level == 2]

    assert h2s[:5] == [
        "Navigation",
        "At a glance",
        "Key capabilities",
        "Installation",
        "Quick start",
    ]
    operation = next(
        operation
        for operation in plan.operations
        if operation.operation_id == "readme.journey.key-capabilities"
    )
    assert operation.fact_ids
    assert "## Key capabilities" in candidate
