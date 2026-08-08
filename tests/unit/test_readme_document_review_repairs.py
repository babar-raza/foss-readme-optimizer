"""Source-bound application of independently grounded README repair findings."""

from __future__ import annotations

import json
from pathlib import Path

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.agentic_composition_models import (
    ReadmeAgenticCompositionPlanV1,
    ReadmeCompositionRepairRequestV1,
)
from readme_agent.readme.document_operations import apply_document_operations
from readme_agent.readme.document_presentation_repairs import (
    build_presentation_policy_operations,
)
from readme_agent.readme.document_render_context import DocumentRenderContext
from readme_agent.readme.document_review_repairs import build_review_repair_operations
from readme_agent.readme.document_structure import parse_headings

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROOF_PATH = (
    PROJECT_ROOT
    / "plans"
    / "investigations"
    / "evidence"
    / "level8-local-immutable-snapshot-and-facts-corrected-acquisition-2026-07-24"
    / "immutable-snapshot-and-product-facts-proof.json"
)


def _facts() -> ProductFactsV2:
    proof = json.loads(PROOF_PATH.read_text(encoding="utf-8"))
    return ProductFactsV2.model_validate(proof["current_pilots"][0]["product_facts_v2"])


def _context(source: str) -> DocumentRenderContext:
    return DocumentRenderContext(
        org_repo="aspose-page-foss/Aspose.Page-FOSS-for-Python",
        source_text=source,
        inner_text=source,
        source=source.encode("utf-8"),
        facts=_facts(),
        base_revision="a" * 40,
        headings=parse_headings(source),
    )


def _request(*, second_span: str) -> ReadmeCompositionRepairRequestV1:
    why_span = "- Convert PS/EPS to PDF\n- Convert XPS to PDF"
    return ReadmeCompositionRepairRequestV1.model_validate(
        {
            "source_candidate_sha256": "b" * 64,
            "failed_criteria": ["visible_duplication"],
            "sections_affected": [
                "Why Aspose.Page FOSS for Python",
                "Key capabilities",
            ],
            "required_repair": "Consolidate the duplicated capability sections.",
            "preserve": [why_span, second_span],
            "findings": [
                {
                    "finding_id": "quality.why-duplication",
                    "section": "Why Aspose.Page FOSS for Python",
                    "criterion": "visible_duplication",
                    "quoted_candidate_span": why_span,
                    "required_repair": "Consolidate this material without dropping it.",
                },
                {
                    "finding_id": "quality.capability-duplication",
                    "section": "Key capabilities",
                    "criterion": "visible_duplication",
                    "quoted_candidate_span": second_span,
                    "required_repair": "Retain one visible capability section.",
                },
            ],
        }
    )


def test_grounded_duplication_repair_consolidates_without_losing_source_content():
    source = """# Aspose.Page FOSS for Python

## Why Aspose.Page FOSS for Python

- Convert PS/EPS to PDF
- Convert XPS to PDF

Maintainer rationale remains valuable.

## Currently Available Features

- PS/EPS to PDF conversion
- XPS to PDF conversion

## Installation

Install from source.
"""
    context = _context(source)
    second_span = "- PS/EPS to PDF conversion\n- XPS to PDF conversion"
    plan = ReadmeAgenticCompositionPlanV1.model_construct(
        review_repair=_request(second_span=second_span)
    )
    policy_operations = build_presentation_policy_operations(context, [])

    repair_operations = build_review_repair_operations(
        context,
        plan,
        policy_operations,
    )
    candidate = apply_document_operations(
        context.source,
        [*policy_operations, *repair_operations],
    ).decode("utf-8")

    assert len(repair_operations) == 2
    assert "## Why Aspose.Page FOSS for Python" not in candidate
    assert candidate.count("## Key Capabilities") == 1
    assert "<summary>Why Aspose.Page FOSS for Python</summary>" in candidate
    assert "- Convert PS/EPS to PDF\n- Convert XPS to PDF" in candidate
    assert "Maintainer rationale remains valuable." in candidate
    assert second_span in candidate


def test_repair_fails_closed_when_a_reviewer_span_is_not_source_bound():
    source = """# Product

## Why Product

Maintainer rationale.

## Features

- Verified feature
"""
    context = _context(source)
    plan = ReadmeAgenticCompositionPlanV1.model_construct(
        review_repair=_request(second_span="not present in the source")
    )

    assert build_review_repair_operations(context, plan, []) == []
