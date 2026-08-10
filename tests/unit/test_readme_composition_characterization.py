"""Freeze README composition behavior before responsibility extraction."""

from __future__ import annotations

import hashlib
import inspect
import json
from pathlib import Path

import pytest

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.llm.schema import LLMResponseMeta
from readme_agent.llm.verifier_client import FixtureForcedToolClient, ForcedToolResult
from readme_agent.readme.agentic_composition import (
    plan_readme_composition,
    validate_readme_composition_plan,
)
from readme_agent.readme.assessment import assess_readme_document
from readme_agent.readme.document_renderer import build_readme_document_candidate

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROOF_PATH = (
    PROJECT_ROOT
    / "plans"
    / "investigations"
    / "evidence"
    / "level8-local-immutable-snapshot-and-facts-corrected-acquisition-2026-07-24"
    / "immutable-snapshot-and-product-facts-proof.json"
)

DOCUMENT_CASES = (
    (
        "aspose-cells-foss/Aspose.Cells-FOSS-for-Java",
        "# Aspose.Cells FOSS for Java\n\nSpreadsheet library for Java developers.\n",
        "59718d243945486c8cbce5652214708b92c9866e00289da496cdae73f55d4fba",
        "bc94878879866bdb19bbb94fb43cdbb7401f2dd149b0f18c16ef33fb7b5a9186",
        [
            "readme.journey.key-capabilities",
            "readme.overview-navigation-and-acquisition",
            "readme.installation.add-verified",
            "readme.example.add-verified-minimal",
            "readme.limitations.add-verified",
            "readme.license.add-section",
            "readme.header.badges",
            "readme.presentation.canonical-section-order",
        ],
    ),
    (
        "aspose-3d-foss/Aspose.3D-FOSS-for-Java",
        (
            "# Aspose.3D FOSS for Java\n\n"
            "> [FOSS](https://products.aspose.org/3d/) and "
            "[commercial](https://products.aspose.com/3d/)\n\n"
            '## Usage\n\n```java\nSystem.out.println("legacy");\n```\n'
        ),
        "c5975c089a4ca961887b3656f66c23fce8f41383c464c8eb9c8d5b4e18163053",
        "bbca86443a30df42ad621303cd4b42a58041836722f99168b88ba1205880b0d8",
        [
            "readme.journey.key-capabilities",
            "readme.overview-navigation-and-acquisition",
            "readme.installation.add-verified",
            "readme.limitations.add-verified",
            "readme.opening.remove-promotional-callout",
            "readme.license.add-section",
            "readme.header.badges",
            "readme.unresolved.withhold:1",
            "readme.presentation.canonical-section-order",
        ],
    ),
    (
        "aspose-pdf-foss/Aspose.PDF-FOSS-for-Java",
        (
            "# Aspose.PDF FOSS for Java\n\n"
            "**Version 0.0.1**\n\n"
            "## Installation\n\nExisting instructions.\n"
        ),
        "6f8039efdde20e5b2cc8a004e127a5373783981d7fe588502365093e4f17142f",
        "58c35525e63bfa618502e3332fc81275a0bd83ab0a1dccb5184655b46e9ae257",
        [
            "readme.journey.key-capabilities",
            "readme.overview-navigation-and-acquisition",
            "readme.example.add-verified-minimal",
            "readme.limitations.add-verified",
            "readme.release.correct-manifest-version",
            "readme.license.add-section",
            "readme.header.badges",
            "readme.presentation.canonical-section-order",
        ],
    ),
)


def _facts(org_repo: str) -> tuple[ProductFactsV2, str]:
    proof = json.loads(PROOF_PATH.read_text(encoding="utf-8"))
    pilot = next(item for item in proof["current_pilots"] if item["org_repo"] == org_repo)
    return (
        ProductFactsV2.model_validate(pilot["product_facts_v2"]),
        pilot["snapshot"]["source_revision"],
    )


def _canonical_hash(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def test_public_composition_call_signatures_are_characterized() -> None:
    signatures = {
        "assess": inspect.signature(assess_readme_document),
        "plan": inspect.signature(plan_readme_composition),
        "validate": inspect.signature(validate_readme_composition_plan),
        "render": inspect.signature(build_readme_document_candidate),
    }

    assert tuple(signatures["assess"].parameters) == (
        "org_repo",
        "source_text",
        "facts",
        "base_revision",
    )
    assert tuple(signatures["plan"].parameters) == (
        "org_repo",
        "source_text",
        "facts",
        "assessment",
        "client",
        "max_attempts",
        "review_repair",
    )
    assert tuple(signatures["validate"].parameters) == (
        "payload",
        "org_repo",
        "source_text",
        "facts",
        "assessment",
    )
    assert tuple(signatures["render"].parameters) == (
        "org_repo",
        "source_text",
        "facts",
        "base_revision",
        "agentic_composition_plan",
        "link_catalogs",
        "link_allocation_policy",
    )
    assert signatures["plan"].parameters["client"].kind is inspect.Parameter.KEYWORD_ONLY
    assert signatures["render"].parameters["base_revision"].kind is inspect.Parameter.KEYWORD_ONLY


@pytest.mark.parametrize(
    ("org_repo", "source", "candidate_hash", "plan_hash", "operation_ids"),
    DOCUMENT_CASES,
)
def test_document_composition_bytes_and_plan_are_characterized(
    org_repo: str,
    source: str,
    candidate_hash: str,
    plan_hash: str,
    operation_ids: list[str],
) -> None:
    facts, revision = _facts(org_repo)

    candidate, plan = build_readme_document_candidate(
        org_repo,
        source,
        facts,
        base_revision=revision,
    )

    assert hashlib.sha256(candidate.encode("utf-8")).hexdigest() == candidate_hash
    assert _canonical_hash(plan.model_dump(mode="json")) == plan_hash
    assert [operation.operation_id for operation in plan.operations] == operation_ids


def test_agentic_composition_plan_is_characterized() -> None:
    facts, revision = _facts("aspose-cells-foss/Aspose.Cells-FOSS-for-Java")
    source = "# Aspose.Cells FOSS for Java\n\nMaintainer introduction.\n"
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
    )
    audience = facts.selected_fact("product.audience")
    problem = facts.selected_fact("product.problems_solved")
    planning_sections = [
        section
        for section in assessment.sections
        if section.level <= 2 or section.disposition != "preserve"
    ]
    tool_result = {
        "repository_summary": "Lead with the verified spreadsheet audience and task.",
        "section_decisions": [
            {
                "section_id": section.section_id,
                "disposition": section.disposition,
                "priority": 50,
                "supporting_fact_ids": (
                    [audience.fact_id] if section.section_id == "opening" else []
                ),
                "rationale": "Retain the deterministic source-bound disposition.",
            }
            for section in planning_sections
        ],
        "overview_fact_ids": [audience.fact_id, problem.fact_id],
    }
    client = FixtureForcedToolClient(
        [
            ForcedToolResult(
                arguments=tool_result,
                meta=LLMResponseMeta(model="fixture-author"),
            )
        ]
    )

    plan = plan_readme_composition(
        facts.org_repo,
        source,
        facts,
        assessment,
        client=client,
    )

    assert plan.canonical_hash() == (
        "22db82fa92a47ab79bd29207488152ab9724c6efd43a10f7f8855612cd984828"
    )
    assert plan.input_sha256 == ("004ab18a2a6a0745f585917821013cb3bc2b926fd5905a33cbe607cdaa9d30a9")
