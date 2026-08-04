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
        "2ba5cabf810eadfe03888a7d29c422221b7dc515bf8c7ff955fd7f78ab8cdb96",
        "c276cded13da9a2acb08a45b563438676fb76d6cdd79cb45f444752988c9e2f1",
        [
            "readme.journey.key-capabilities",
            "readme.overview-navigation-and-acquisition",
            "readme.installation.add-verified",
            "readme.example.add-verified-minimal",
            "readme.limitations.add-verified",
            "readme.license.add-section",
            "readme.header.badges",
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
        "333aa3ca201bb1995e19acf4772f97c1f3aa88c78410e8c7e70a8c22eaf7f51b",
        "3e4db5156129609bc55a9d1b2ad1c35b9b562a7ef8175392748220cf58270708",
        [
            "readme.journey.key-capabilities",
            "readme.overview-navigation-and-acquisition",
            "readme.installation.add-verified",
            "readme.limitations.add-verified",
            "readme.opening.remove-promotional-callout",
            "readme.license.add-section",
            "readme.header.badges",
            "readme.unresolved.withhold:1",
        ],
    ),
    (
        "aspose-pdf-foss/Aspose.PDF-FOSS-for-Java",
        (
            "# Aspose.PDF FOSS for Java\n\n"
            "**Version 0.0.1**\n\n"
            "## Installation\n\nExisting instructions.\n"
        ),
        "48205009dc93fc0cf7caa89fb5abe4b0af2e4ac3ddbbb89403f994f39aa8e19e",
        "ab40c8949b92e7e16890d1d15dd374807e09672acafddec304e3d318f365b4ec",
        [
            "readme.journey.key-capabilities",
            "readme.overview-navigation-and-acquisition",
            "readme.example.add-verified-minimal",
            "readme.limitations.add-verified",
            "readme.release.correct-manifest-version",
            "readme.license.add-section",
            "readme.header.badges",
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
        "930040a354beefaf5471369db9a18358b81553087fce0f270f63c766c8300259"
    )
    assert plan.input_sha256 == ("124a62335aa612dd9d526cc61a20b9d8accf1af83da0567b442c59572853546a")
