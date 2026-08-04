"""Fact-bound agentic README composition and deterministic rendering tests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from readme_agent.errors import LLMError
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.llm.generation_prompts import build_readme_composition_tool_schema
from readme_agent.llm.schema import LLMResponseMeta
from readme_agent.llm.verifier_client import FixtureForcedToolClient, ForcedToolResult
from readme_agent.readme.agentic_composition import (
    plan_readme_composition,
    validate_readme_composition_plan,
)
from readme_agent.readme.agentic_composition_assessment import planning_assessment_payload
from readme_agent.readme.agentic_composition_grounding import accepted_composition_fact_ids
from readme_agent.readme.agentic_composition_inputs import (
    compact_prompt_fact_value,
    composition_fact_payloads,
)
from readme_agent.readme.agentic_composition_models import MAX_AUTHORING_ATTEMPTS
from readme_agent.readme.agentic_operation_coverage import (
    validate_agentic_operation_coverage,
)
from readme_agent.readme.assessment import assess_readme_document
from readme_agent.readme.claim_map import build_readme_claim_map
from readme_agent.readme.diagram_role_semantics import normalize_diagram_role_nodes
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
CHARACTERIZATION_SOURCE_SHA256 = "6eedb080ad3204b2feafcdd74aaa8468a19c69a8f55abc6f08b6110609fffe76"
CHARACTERIZATION_FACTS_SHA256 = "8592865d5c3b8e9f161ffc20ec9b3743c09a2e747a9dea8afacb671682800b4f"
CHARACTERIZATION_ASSESSMENT_SHA256 = (
    "9b3eee151d3e49cdbf3259d2646050d6c6af67d94f330a39fcd2453c98a75c4b"
)
CHARACTERIZATION_AGENTIC_PLAN_SHA256 = (
    "58b737d7977bce750260226a244a709ec6f40d3280293a1074b11851408e4abb"
)
CHARACTERIZATION_DOCUMENT_PLAN_SHA256 = (
    "cb250413d70e7fd46138dbe970b33309d03e5cda5504ae22ba369ff0c4fb7ef3"
)
CHARACTERIZATION_CANDIDATE_SHA256 = (
    "5afc4cc1d1f05cceb231dc8edc9523c6190c09dc82ce3979ab9cc3097a8bdc7d"
)


def _facts() -> tuple[ProductFactsV2, str]:
    proof = json.loads(PROOF_PATH.read_text(encoding="utf-8"))
    pilot = next(
        item
        for item in proof["current_pilots"]
        if item["org_repo"] == "aspose-cells-foss/Aspose.Cells-FOSS-for-Java"
    )
    return ProductFactsV2.model_validate(pilot["product_facts_v2"]), pilot["snapshot"][
        "source_revision"
    ]


def _first_text(value: object) -> str:
    if isinstance(value, list):
        return str(value[0])
    return str(value)


def _canonical_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def test_authoring_packet_excludes_native_verifier_receipts_and_caps_equivalent_attempts():
    facts, _revision = _facts()
    example = facts.selected_fact("example.minimal")
    example_value = dict(example.value) if isinstance(example.value, dict) else {}
    example_value["compiled_consumer"] = {"stdout": "native-proof" * 100_000}
    facts = facts.model_copy(
        update={
            "facts": [
                fact.model_copy(update={"value": example_value})
                if fact.fact_id == example.fact_id
                else fact
                for fact in facts.facts
            ]
        }
    )

    payloads = composition_fact_payloads(facts, accepted_composition_fact_ids(facts))
    projected_example = next(row for row in payloads if row["field"] == "example.minimal")

    assert "compiled_consumer" not in projected_example["value"]
    assert len(json.dumps(payloads)) < 50_000
    assert MAX_AUTHORING_ATTEMPTS == 2


def test_authoring_packet_flattens_public_api_and_asset_trees_with_explicit_counts():
    api_value = {
        "modules": [
            {
                "module": "aspose.note",
                "exports": [f"Export{index}" for index in range(100)],
                "source_path": "src/aspose/note/__init__.py",
                "source_sha256": "a" * 64,
            }
        ],
        "classes": [
            {
                "name": f"Class{index}",
                "members": [
                    {
                        "name": "load",
                        "surface": f"Class{index}.load(path)",
                        "native_verifier_transcript": "verifier-tree" * 100,
                    }
                ],
                "source_path": f"src/class_{index}.py",
                "source_sha256": "b" * 64,
            }
            for index in range(100)
        ],
    }
    assets_value = {
        "tests": {
            "count": 100,
            "inventory_sha256": "c" * 64,
            "representative_paths": [
                {"path": f"tests/test_{index}.py", "sha256": "d" * 64} for index in range(20)
            ],
        }
    }

    api = compact_prompt_fact_value("api.public_surface", api_value)
    assets = compact_prompt_fact_value("development.assets", assets_value)
    serialized = json.dumps({"api": api, "assets": assets}, sort_keys=True)

    assert api["inventory_counts"] == {
        "modules": 1,
        "exports": 100,
        "classes": 100,
        "member_surfaces": 100,
    }
    assert len(api["representative_exports"]) == 16
    assert len(api["representative_classes"]) == 16
    assert len(api["representative_member_surfaces"]) == 16
    assert api["projection_bounded"] is True
    assert assets["tests"]["representative_paths"] == [
        f"tests/test_{index}.py" for index in range(5)
    ]
    assert "source_path" not in serialized
    assert "source_sha256" not in serialized
    assert "native_verifier_transcript" not in serialized
    assert len(serialized) < len(json.dumps({"api": api_value, "assets": assets_value})) // 3


def _draft(facts: ProductFactsV2, *, fact_id: str | None = None) -> dict:
    audience = facts.selected_fact("product.audience")
    problem = facts.selected_fact("product.problems_solved")
    identity = facts.selected_fact("product.identity")
    formats = facts.selected_fact("product.formats")
    capabilities = facts.selected_fact("product.capabilities")
    capability_values = (
        capabilities.value if isinstance(capabilities.value, list) else [capabilities.value]
    )
    return {
        "repository_summary": "Lead with the verified spreadsheet audience and task.",
        "section_decisions": [
            {
                "section_id": "opening",
                "disposition": "preserve",
                "priority": 100,
                "supporting_fact_ids": [audience.fact_id],
                "rationale": (
                    "The existing identity is useful and the overview adds verified context."
                ),
            }
        ],
        "overview_sentences": [
            {
                "text": _first_text(audience.value),
                "supporting_fact_ids": [fact_id or audience.fact_id],
            },
            {
                "text": _first_text(problem.value),
                "supporting_fact_ids": [problem.fact_id],
            },
        ],
        "diagram": {
            "nodes": [
                {
                    "role": "input",
                    "label": "XLSX workbooks",
                    "supporting_fact_ids": [formats.fact_id],
                },
                {
                    "role": "input",
                    "label": "XLSX data",
                    "supporting_fact_ids": [formats.fact_id],
                },
                {
                    "role": "input",
                    "label": "Workbook streams",
                    "supporting_fact_ids": [formats.fact_id],
                },
                {
                    "role": "capability",
                    "label": str(capability_values[0]),
                    "supporting_fact_ids": [capabilities.fact_id],
                },
                {
                    "role": "capability",
                    "label": (
                        str(capability_values[1])
                        if len(capability_values) > 1
                        else "Inspect spreadsheet content"
                    ),
                    "supporting_fact_ids": [capabilities.fact_id],
                },
                {
                    "role": "capability",
                    "label": "Process XLSX workbooks without Microsoft Excel",
                    "supporting_fact_ids": [problem.fact_id],
                },
                {
                    "role": "capability",
                    "label": "Read worksheet data",
                    "supporting_fact_ids": [capabilities.fact_id],
                },
                {
                    "role": "capability",
                    "label": "Write workbook data",
                    "supporting_fact_ids": [capabilities.fact_id],
                },
                {
                    "role": "capability",
                    "label": "Inspect workbook formulas",
                    "supporting_fact_ids": [capabilities.fact_id],
                },
                {
                    "role": "output",
                    "label": "Updated XLSX workbooks",
                    "supporting_fact_ids": [formats.fact_id],
                },
                {
                    "role": "output",
                    "label": "Worksheet values",
                    "supporting_fact_ids": [capabilities.fact_id],
                },
                {
                    "role": "output",
                    "label": "Workbook metadata",
                    "supporting_fact_ids": [capabilities.fact_id],
                },
                {
                    "role": "output",
                    "label": "Cell values",
                    "supporting_fact_ids": [capabilities.fact_id],
                },
                {
                    "role": "output",
                    "label": "Spreadsheet styles",
                    "supporting_fact_ids": [capabilities.fact_id],
                },
            ]
        },
        "opening_summary": {
            "text": (
                "Aspose.Cells FOSS for Java is an open-source Java library for processing "
                "spreadsheet workbooks without Microsoft Excel. It is designed for Java "
                "developers creating, loading, modifying, and saving spreadsheet workbooks."
            ),
            "supporting_fact_ids": [identity.fact_id, audience.fact_id, problem.fact_id],
        },
    }


def _tool_arguments(draft: dict) -> dict:
    return {
        "repository_summary": draft["repository_summary"],
        "section_decisions": draft["section_decisions"],
        "overview_fact_ids": [
            sentence["supporting_fact_ids"][0] for sentence in draft["overview_sentences"]
        ],
        "opening_summary": draft["opening_summary"],
        "diagram": draft["diagram"],
    }


def _client(*drafts: dict) -> FixtureForcedToolClient:
    return FixtureForcedToolClient(
        [
            ForcedToolResult(
                arguments=_tool_arguments(draft),
                meta=LLMResponseMeta(model="fixture-author"),
            )
            for draft in drafts
        ]
    )


def test_composition_tool_schema_avoids_gateway_unsupported_unique_items():
    schema = build_readme_composition_tool_schema(
        section_ids=["section:0"],
        accepted_fact_ids=["fact:0"],
        overview_fact_ids=["fact:0"],
    )

    assert "uniqueItems" not in json.dumps(schema)
    assert "diagram" in schema["function"]["parameters"]["required"]
    assert "opening_summary" in schema["function"]["parameters"]["required"]
    assert (
        schema["function"]["parameters"]["properties"]["diagram"]["properties"]["nodes"]["minItems"]
        == 14
    )


def _cover_assessment(draft: dict, assessment) -> dict:
    existing = {decision["section_id"] for decision in draft["section_decisions"]}
    accepted_ids = {
        fact_id
        for decision in draft["section_decisions"]
        for fact_id in decision["supporting_fact_ids"]
    } | {
        fact_id
        for sentence in draft["overview_sentences"]
        for fact_id in sentence["supporting_fact_ids"]
    }
    draft["section_decisions"].extend(
        {
            "section_id": section.section_id,
            "disposition": section.disposition,
            "priority": 50,
            "supporting_fact_ids": [
                fact_id for fact_id in section.fact_ids if fact_id in accepted_ids
            ],
            "rationale": "Retain the deterministic source-bound disposition.",
        }
        for section in assessment.sections
        if section.level <= 2 or section.disposition != "preserve"
        if section.section_id not in existing
    )
    return draft


def test_composition_assessment_projection_binds_full_claims_without_copying_them():
    facts, revision = _facts()
    source = "# Aspose.Cells FOSS for Java\n\nMaintainer introduction.\n"
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
    )
    payload = planning_assessment_payload(assessment)
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)

    assert payload["full_assessment_sha256"] == assessment.canonical_hash()
    assert payload["material_claim_count"] == len(assessment.material_claims)
    assert "material_claims" not in payload
    assert "untrusted_repository_instructions" not in payload
    assert all("protected_fragment_ids" not in section for section in payload["sections"])
    assert all(
        "rationale" not in section
        for section in payload["sections"]
        if section["disposition"] == "preserve"
    )
    assert len(serialized) < len(assessment.model_dump_json())


def test_agentic_plan_is_source_and_fact_bound_and_changes_the_candidate():
    facts, revision = _facts()
    draft = _draft(facts)
    source = f"# Aspose.Cells FOSS for Java\n\n{draft['opening_summary']['text']}\n"
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
    )
    client = _client(_cover_assessment(draft, assessment))

    plan = plan_readme_composition(
        facts.org_repo,
        source,
        facts,
        assessment,
        client=client,
    )
    candidate, document_plan = build_readme_document_candidate(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
        agentic_composition_plan=plan.model_dump(mode="json"),
    )

    assert hashlib.sha256(source.encode("utf-8")).hexdigest() == CHARACTERIZATION_SOURCE_SHA256
    assert facts.canonical_hash() == CHARACTERIZATION_FACTS_SHA256
    assert assessment.canonical_hash() == CHARACTERIZATION_ASSESSMENT_SHA256
    assert plan.canonical_hash() == CHARACTERIZATION_AGENTIC_PLAN_SHA256
    assert (
        _canonical_hash(document_plan.model_dump(mode="json"))
        == CHARACTERIZATION_DOCUMENT_PLAN_SHA256
    )
    assert (
        hashlib.sha256(candidate.encode("utf-8")).hexdigest() == CHARACTERIZATION_CANDIDATE_SHA256
    )
    assert document_plan.candidate_sha256 == CHARACTERIZATION_CANDIDATE_SHA256
    assert [operation.operation_id for operation in document_plan.operations] == [
        "readme.verified-template.compile"
    ]
    assert document_plan.claim_accountability is not None
    blocking_claims = [
        claim
        for claim in document_plan.claim_accountability.claims
        if not claim.currently_accountable
    ]
    assert blocking_claims == []
    assert plan.model == "fixture-author"
    assert plan.attempt_count == 1
    assert plan.input_sha256
    assert plan.prompt_sha256
    assert plan.tool_schema_sha256
    assert plan.opening_summary is not None
    assert {node.role for node in plan.diagram.nodes} == {"input", "capability", "output"}
    assert _first_text(facts.selected_fact("product.audience").value) in candidate
    assert _first_text(facts.selected_fact("product.capabilities").value) in candidate
    assert "Lead with the verified spreadsheet audience" not in candidate
    cited_ids = {
        fact_id
        for binding in document_plan.candidate_content_provenance
        for fact_id in binding.fact_ids
    }
    assert {
        fact_id for sentence in plan.overview_sentences for fact_id in sentence.supporting_fact_ids
    } <= cited_ids
    assert facts.selected_fact("product.formats").fact_id in cited_ids
    claim_map = build_readme_claim_map(
        document_plan,
        facts,
        source_text=source,
        candidate_text=candidate,
    )
    audience_claim = next(
        claim
        for claim in claim_map.claims
        if claim.fact_id == facts.selected_fact("product.audience").fact_id
    )
    assert audience_claim.coordinate_space == "candidate_utf8"
    claim_bytes = candidate.encode("utf-8")[audience_claim.byte_start : audience_claim.byte_end]
    assert _first_text(facts.selected_fact("product.audience").value) in claim_bytes.decode("utf-8")


def test_fact_grounded_diagram_labels_do_not_replace_literal_capability_prose():
    facts, revision = _facts()
    draft = _draft(facts)
    source = f"# Aspose.Cells FOSS for Java\n\n{draft['opening_summary']['text']}\n"
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
    )
    plan = plan_readme_composition(
        facts.org_repo,
        source,
        facts,
        assessment,
        client=_client(_cover_assessment(draft, assessment)),
    )

    candidate, document_plan = build_readme_document_candidate(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
        agentic_composition_plan=plan.model_dump(mode="json"),
    )
    claim_map = build_readme_claim_map(
        document_plan,
        facts,
        source_text=source,
        candidate_text=candidate,
    )

    capability = facts.selected_fact("product.capabilities")
    assert _first_text(capability.value) in candidate
    assert any(node.role == "capability" for node in plan.diagram.nodes)
    assert any(claim.fact_id == capability.fact_id for claim in claim_map.claims)


def test_bidirectional_format_label_may_appear_once_in_input_and_output_roles():
    facts, revision = _facts()
    source = "# Product\n"
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
    )
    draft = _cover_assessment(_draft(facts), assessment)
    draft["diagram"]["nodes"][-1]["label"] = draft["diagram"]["nodes"][0]["label"]
    draft["diagram"]["nodes"][-1]["supporting_fact_ids"] = [
        facts.selected_fact("product.formats").fact_id
    ]

    plan = plan_readme_composition(
        facts.org_repo,
        source,
        facts,
        assessment,
        client=_client(draft),
        max_attempts=1,
    )

    input_label = next(node.label for node in plan.diagram.nodes if node.role == "input")
    assert any(node.role == "output" and node.label == input_label for node in plan.diagram.nodes)


def test_duplicate_diagram_label_within_one_role_is_deduplicated():
    facts, revision = _facts()
    source = "# Product\n"
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
    )
    draft = _cover_assessment(_draft(facts), assessment)
    draft["diagram"]["nodes"][1]["label"] = draft["diagram"]["nodes"][0]["label"]

    plan = plan_readme_composition(
        facts.org_repo,
        source,
        facts,
        assessment,
        client=_client(draft),
        max_attempts=1,
    )

    role_labels = [
        (node.role, " ".join(node.label.casefold().split())) for node in plan.diagram.nodes
    ]
    assert len(role_labels) == len(set(role_labels))


def test_conversion_capabilities_complete_mermaid_input_and_output_roles():
    facts, _revision = _facts()
    replacements = {
        "product.formats": ["Input format: PS/EPS input"],
        "product.capabilities": [
            "PS/EPS to PDF conversion",
            "PS/EPS to image conversion",
            "XPS to PDF conversion",
            "XPS to image conversion",
            "EPS metadata extraction",
        ],
    }
    facts = facts.model_copy(
        update={
            "facts": [
                fact.model_copy(update={"value": replacements[fact.field]})
                if fact.field in replacements
                else fact
                for fact in facts.facts
            ]
        }
    )

    nodes = normalize_diagram_role_nodes(
        [],
        facts,
        {"input": 1, "capability": 1, "output": 1},
        target_counts={"input": 4, "capability": 6, "output": 5},
    )
    inputs = {node.label for node in nodes if node.role == "input"}
    outputs = {node.label for node in nodes if node.role == "output"}

    assert any("PS/EPS" in label for label in inputs)
    assert "XPS files" in inputs
    assert "PDF files" in outputs
    assert "image files" in outputs
    assert "EPS metadata" in outputs
    output_labels = [
        " ".join(node.label.casefold().split()) for node in nodes if node.role == "output"
    ]
    assert len(output_labels) == len(set(output_labels))


def test_generation_capabilities_supply_literal_content_inputs_for_output_only_products():
    facts, _revision = _facts()
    replacements = {
        "product.formats": ["Output format: SVG", "Output format: PNG"],
        "product.capabilities": [
            "Code 128 generation with automatic Code Set switching",
            "Code 39 generation with full ASCII support",
            "QR Code generation with configurable parameters",
        ],
    }
    facts = facts.model_copy(
        update={
            "facts": [
                fact.model_copy(update={"value": replacements[fact.field]})
                if fact.field in replacements
                else fact
                for fact in facts.facts
            ]
        }
    )

    nodes = normalize_diagram_role_nodes(
        [],
        facts,
        {"input": 1, "capability": 1, "output": 1},
        target_counts={"input": 3, "capability": 3, "output": 2},
    )

    assert {node.label for node in nodes if node.role == "input"} == {
        "Code 128 content",
        "Code 39 content",
        "QR Code content",
    }
    assert {node.label for node in nodes if node.role == "output"} == {
        "SVG files",
        "PNG files",
    }


def test_generation_supplies_an_output_when_no_output_format_is_verified():
    facts, _revision = _facts()
    replacements = {
        "product.formats": ["Input format: .TTF"],
        "product.capabilities": [
            "Font format conversion",
            "Web font bundle generation",
            "Delta inspection for variable fonts",
        ],
    }
    facts = facts.model_copy(
        update={
            "facts": [
                fact.model_copy(update={"value": replacements[fact.field]})
                if fact.field in replacements
                else fact
                for fact in facts.facts
            ]
        }
    )

    nodes = normalize_diagram_role_nodes(
        [],
        facts,
        {"input": 1, "capability": 1, "output": 1},
        target_counts={"input": 4, "capability": 6, "output": 5},
    )

    assert ".TTF files" in {node.label for node in nodes if node.role == "input"}
    assert "Web font bundle" in {node.label for node in nodes if node.role == "output"}
    assert "Web font bundle content" not in {node.label for node in nodes if node.role == "input"}


def test_read_write_capability_supplies_fact_grounded_input_when_formats_are_output_only():
    facts, _revision = _facts()
    replacements = {
        "product.formats": ["Output format: XLSX", "Output format: CSV"],
        "product.capabilities": ["Read and write cell values and formulas"],
    }
    facts = facts.model_copy(
        update={
            "facts": [
                fact.model_copy(update={"value": replacements[fact.field]})
                if fact.field in replacements
                else fact
                for fact in facts.facts
            ]
        }
    )

    nodes = normalize_diagram_role_nodes(
        [],
        facts,
        {"input": 1, "capability": 1, "output": 1},
        target_counts={"input": 2, "capability": 3, "output": 2},
    )

    assert {node.label for node in nodes if node.role == "input"} == {"cell values and formulas"}
    assert {node.label for node in nodes if node.role == "output"} == {
        "XLSX files",
        "CSV files",
    }


def test_agentic_plan_rejects_unaccepted_or_invented_fact_ids():
    facts, revision = _facts()
    source = "# Product\n"
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
    )
    client = _client(
        _cover_assessment(
            _draft(facts, fact_id="invented:fact"),
            assessment,
        )
    )

    with pytest.raises(LLMError, match="ineligible overview fact IDs"):
        plan_readme_composition(
            facts.org_repo,
            source,
            facts,
            assessment,
            client=client,
            max_attempts=1,
        )


def test_agentic_plan_rejects_duplicate_supporting_fact_ids_deterministically():
    facts, revision = _facts()
    source = "# Product\n"
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
    )
    draft = _cover_assessment(_draft(facts), assessment)
    duplicate_id = draft["section_decisions"][0]["supporting_fact_ids"][0]
    draft["section_decisions"][0]["supporting_fact_ids"].append(duplicate_id)

    with pytest.raises(LLMError, match="duplicate supporting fact IDs"):
        plan_readme_composition(
            facts.org_repo,
            source,
            facts,
            assessment,
            client=_client(draft),
            max_attempts=1,
        )


def test_agentic_plan_materializes_literal_fact_text_instead_of_authored_prose():
    facts, revision = _facts()
    source = "# Product\n"
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
    )
    draft = _cover_assessment(_draft(facts), assessment)
    draft["overview_sentences"][0]["text"] = (
        "Best-in-class toolkit for " + draft["overview_sentences"][0]["text"]
    )
    client = _client(draft)

    plan = plan_readme_composition(
        facts.org_repo,
        source,
        facts,
        assessment,
        client=client,
        max_attempts=1,
    )

    assert plan.overview_sentences[0].text == _first_text(
        facts.selected_fact("product.audience").value
    )
    assert all("Best-in-class" not in sentence.text for sentence in plan.overview_sentences)


def test_agentic_plan_selects_distinct_literal_phrases_when_fact_lists_overlap():
    facts, revision = _facts()
    problem = facts.selected_fact("product.problems_solved")
    capability = facts.selected_fact("product.capabilities")
    facts = facts.model_copy(
        update={
            "facts": [
                (
                    fact.model_copy(update={"value": ["Shared task", "Second problem"]})
                    if fact.fact_id == problem.fact_id
                    else (
                        fact.model_copy(update={"value": ["Shared task", "Distinct capability"]})
                        if fact.fact_id == capability.fact_id
                        else fact
                    )
                )
                for fact in facts.facts
            ]
        }
    )
    source = "# Product\n"
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
    )
    draft = _draft(facts)
    draft["overview_sentences"].append(
        {
            "text": "Shared task",
            "supporting_fact_ids": [capability.fact_id],
        }
    )
    plan = plan_readme_composition(
        facts.org_repo,
        source,
        facts,
        assessment,
        client=_client(_cover_assessment(draft, assessment)),
        max_attempts=1,
    )

    texts = [sentence.text for sentence in plan.overview_sentences]
    assert len({text.casefold() for text in texts}) == len(texts)
    assert "Distinct capability" in texts


def test_agentic_plan_coalesces_one_literal_phrase_that_subsumes_another():
    facts, revision = _facts()
    problem = facts.selected_fact("product.problems_solved")
    capability = facts.selected_fact("product.capabilities")
    short_phrase = "Create, load, inspect, transform, and save 3D scenes."
    long_phrase = (
        "Create, load, inspect, transform, and save 3D scenes with an open-source Java API."
    )
    facts = facts.model_copy(
        update={
            "facts": [
                (
                    fact.model_copy(update={"value": [long_phrase]})
                    if fact.fact_id == problem.fact_id
                    else (
                        fact.model_copy(update={"value": [short_phrase]})
                        if fact.fact_id == capability.fact_id
                        else fact
                    )
                )
                for fact in facts.facts
            ]
        }
    )
    source = "# Product\n"
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
    )
    draft = _draft(facts)
    draft["overview_sentences"].append(
        {
            "text": short_phrase,
            "supporting_fact_ids": [capability.fact_id],
        }
    )
    plan = plan_readme_composition(
        facts.org_repo,
        source,
        facts,
        assessment,
        client=_client(_cover_assessment(draft, assessment)),
        max_attempts=1,
    )

    overlapping = next(
        sentence
        for sentence in plan.overview_sentences
        if problem.fact_id in sentence.supporting_fact_ids
    )
    assert overlapping.text == long_phrase
    assert overlapping.supporting_fact_ids == [problem.fact_id, capability.fact_id]
    assert (
        sum(short_phrase.rstrip(".") in sentence.text for sentence in plan.overview_sentences) == 1
    )

    stale_payload = plan.model_dump(mode="json")
    stale_payload["overview_sentences"] = [
        {
            "text": _first_text(facts.selected_fact("product.audience").value),
            "supporting_fact_ids": [facts.selected_fact("product.audience").fact_id],
        },
        {
            "text": long_phrase,
            "supporting_fact_ids": [problem.fact_id],
        },
        {
            "text": short_phrase,
            "supporting_fact_ids": [capability.fact_id],
        },
    ]
    with pytest.raises(LLMError, match="semantically duplicate overview"):
        validate_readme_composition_plan(
            stale_payload,
            org_repo=facts.org_repo,
            source_text=source,
            facts=facts,
            assessment=assessment,
        )


def test_agentic_plan_rejects_internal_relationship_codes_as_overview_prose():
    facts, revision = _facts()
    source = "# Product\n"
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
    )
    draft = _cover_assessment(_draft(facts), assessment)
    relationship = facts.selected_fact("relationship.commercial_foss")
    draft["overview_sentences"].append(
        {
            "text": "open_source_scope",
            "supporting_fact_ids": [relationship.fact_id],
        }
    )

    with pytest.raises(LLMError, match="ineligible overview fact IDs"):
        plan_readme_composition(
            facts.org_repo,
            source,
            facts,
            assessment,
            client=_client(draft),
            max_attempts=1,
        )


def test_document_validation_accepts_one_representative_phrase_per_overview_fact():
    facts, revision = _facts()
    problem = facts.selected_fact("product.problems_solved")
    facts = facts.model_copy(
        update={
            "facts": [
                (
                    fact.model_copy(
                        update={"value": ["Primary verified task", "Secondary verified task"]}
                    )
                    if fact.fact_id == problem.fact_id
                    else fact
                )
                for fact in facts.facts
            ]
        }
    )
    source = "# Product\n"
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
    )
    plan = plan_readme_composition(
        facts.org_repo,
        source,
        facts,
        assessment,
        client=_client(_cover_assessment(_draft(facts), assessment)),
        max_attempts=1,
    )
    candidate, document_plan = build_readme_document_candidate(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
        agentic_composition_plan=plan.model_dump(mode="json"),
    )

    result = validate_readme_document_candidate(source, candidate, document_plan, facts)

    assert result.valid, result.errors
    assert document_plan.header_visuals is not None
    assert problem.fact_id in document_plan.header_visuals.diagram_fact_ids
    assert candidate.count("Secondary verified task") == 1
    assert '["Secondary verified task"]' in candidate


def test_presentation_replacement_does_not_blanket_authorize_protected_source_loss():
    facts, revision = _facts()
    source = "# Product\n\n## API reference\n\n```text\nmaintainer_api_contract()\n```\n"
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
    )
    plan = plan_readme_composition(
        facts.org_repo,
        source,
        facts,
        assessment,
        client=_client(_cover_assessment(_draft(facts), assessment)),
        max_attempts=1,
    )
    with pytest.raises(ValueError, match="preserve disposition lost a source claim"):
        build_readme_document_candidate(
            facts.org_repo,
            source,
            facts,
            base_revision=revision,
            agentic_composition_plan=plan.model_dump(mode="json"),
        )


def test_renderer_rejects_a_composition_plan_rebound_to_another_source():
    facts, revision = _facts()
    source = "# Product\n"
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
    )
    plan = plan_readme_composition(
        facts.org_repo,
        source,
        facts,
        assessment,
        client=_client(_cover_assessment(_draft(facts), assessment)),
    )
    tampered = plan.model_dump(mode="json")
    tampered["source_sha256"] = "0" * 64

    with pytest.raises(LLMError, match="binding mismatch"):
        build_readme_document_candidate(
            facts.org_repo,
            source,
            facts,
            base_revision=revision,
            agentic_composition_plan=tampered,
        )


def test_renderer_rejects_a_plan_with_a_stale_tool_schema_binding():
    facts, revision = _facts()
    source = "# Product\n"
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
    )
    plan = plan_readme_composition(
        facts.org_repo,
        source,
        facts,
        assessment,
        client=_client(_cover_assessment(_draft(facts), assessment)),
    )
    tampered = plan.model_dump(mode="json")
    tampered["tool_schema_sha256"] = "0" * 64

    with pytest.raises(LLMError, match="tool_schema_sha256"):
        build_readme_document_candidate(
            facts.org_repo,
            source,
            facts,
            base_revision=revision,
            agentic_composition_plan=tampered,
        )


def test_agentic_plan_requires_one_decision_for_every_assessed_section():
    facts, revision = _facts()
    source = "# Product\n\n## Installation\n\nExisting guidance.\n"
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
    )

    with pytest.raises(LLMError, match="omitted source-bound section decisions"):
        plan_readme_composition(
            facts.org_repo,
            source,
            facts,
            assessment,
            client=_client(_draft(facts)),
            max_attempts=1,
        )


def test_agentic_plan_canonicalizes_copied_dispositions_to_deterministic_assessment():
    facts, revision = _facts()
    source = "# Product\n"
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
    )
    draft = _cover_assessment(_draft(facts), assessment)
    draft["section_decisions"][0]["disposition"] = "rewrite"

    plan = plan_readme_composition(
        facts.org_repo,
        source,
        facts,
        assessment,
        client=_client(draft),
        max_attempts=1,
    )

    dispositions = {section.section_id: section.disposition for section in assessment.sections}
    assert all(
        decision.disposition == dispositions[decision.section_id]
        for decision in plan.section_decisions
    )


def test_actionable_agentic_decision_requires_a_bounded_document_operation():
    facts, revision = _facts()
    source = "# Product\n"
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
    )
    draft = _cover_assessment(_draft(facts), assessment)
    plan = plan_readme_composition(
        facts.org_repo,
        source,
        facts,
        assessment,
        client=_client(draft),
    )

    with pytest.raises(LLMError, match="actionable decisions without bounded operations"):
        validate_agentic_operation_coverage(
            assessment,
            plan.section_decisions,
            [],
        )


def test_agentic_plan_repairs_a_rejected_first_response():
    facts, revision = _facts()
    source = "# Product\n"
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
    )
    invalid = _cover_assessment(_draft(facts), assessment)
    invalid["overview_sentences"][0]["supporting_fact_ids"] = ["invented:fact"]
    valid = _cover_assessment(_draft(facts), assessment)
    client = _client(invalid, valid)

    plan = plan_readme_composition(
        facts.org_repo,
        source,
        facts,
        assessment,
        client=client,
    )

    assert plan.overview_sentences[0].text == _first_text(
        facts.selected_fact("product.audience").value
    )
    assert plan.attempt_count == 2


def test_agentic_plan_repairs_opening_that_omits_audience_citation():
    facts, revision = _facts()
    source = "# Product\n"
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
    )
    invalid = _cover_assessment(_draft(facts), assessment)
    audience_id = facts.selected_fact("product.audience").fact_id
    invalid["opening_summary"]["supporting_fact_ids"].remove(audience_id)
    valid = _cover_assessment(_draft(facts), assessment)
    plan = plan_readme_composition(
        facts.org_repo,
        source,
        facts,
        assessment,
        client=_client(invalid, valid),
    )

    assert audience_id in plan.opening_summary.supporting_fact_ids
    assert plan.attempt_count == 2


def test_agentic_plan_repairs_opening_with_enterprise_comparison():
    facts, revision = _facts()
    source = "# Product\n"
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
    )
    invalid = _cover_assessment(_draft(facts), assessment)
    invalid["opening_summary"]["text"] += " Compare the commercial Aspose.Cells product."
    valid = _cover_assessment(_draft(facts), assessment)

    plan = plan_readme_composition(
        facts.org_repo,
        source,
        facts,
        assessment,
        client=_client(invalid, valid),
    )

    assert "commercial" not in plan.opening_summary.text.casefold()
    assert plan.attempt_count == 2


@pytest.mark.parametrize(
    ("role", "field", "label"),
    [
        ("input", "product.compatibility", "Java 17+ runtime"),
        ("input", "example.minimal", "Java source code"),
        ("input", "product.formats", "Java source code"),
        ("input", "product.formats", "Reads XLSX files"),
        ("input", "product.formats", "Import XLSX files"),
        ("input", "product.formats", "Open XLSX files"),
        ("input", "product.formats", "Parse XLSX files"),
        ("input", "product.formats", "XLSX files and Java runtime"),
        ("output", "product.formats", "XLSX Java API surface"),
        ("output", "product.formats", "XLSX package artifact"),
        ("capability", "product.formats", "Process XLSX through source code"),
        ("capability", "product.capabilities", "source"),
        ("output", "product.formats", "XLSX source"),
        ("output", "product.problems_solved", "XLSX source"),
        ("output", "installation.verified_acquisition", "Maven artifact"),
        ("output", "support.routes", "Java API surface"),
        ("output", "product.problems_solved", "open-source Java API"),
    ],
)
def test_agentic_plan_repairs_infrastructure_facts_used_as_product_diagram_roles(
    role: str,
    field: str,
    label: str,
):
    facts, revision = _facts()
    source = "# Product\n"
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
    )
    invalid = _cover_assessment(_draft(facts), assessment)
    selected = facts.selected_fact(field)
    target = next(node for node in invalid["diagram"]["nodes"] if node["role"] == role)
    target["label"] = label
    target["supporting_fact_ids"] = [selected.fact_id]

    plan = plan_readme_composition(
        facts.org_repo,
        source,
        facts,
        assessment,
        client=_client(invalid),
    )

    assert plan.attempt_count == 1
    assert all(node.label != label for node in plan.diagram.nodes)


def test_agentic_plan_does_not_invent_diagram_detail_to_reach_a_visual_target():
    facts, revision = _facts()
    source = "# Product\n"
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
    )
    draft = _cover_assessment(_draft(facts), assessment)
    removed_one = False
    remaining_nodes = []
    for node in draft["diagram"]["nodes"]:
        if node["role"] == "capability" and not removed_one:
            removed_one = True
            continue
        remaining_nodes.append(node)
    draft["diagram"]["nodes"] = remaining_nodes

    plan = plan_readme_composition(
        facts.org_repo,
        source,
        facts,
        assessment,
        client=_client(draft),
    )

    assert sum(node.role == "capability" for node in plan.diagram.nodes) >= 1
    assert all(node.label != "Inspect workbook formulas" for node in plan.diagram.nodes)
    assert plan.attempt_count == 1


def test_agentic_plan_accepts_literal_format_fact_for_load_capability():
    facts, revision = _facts()
    source = "# Product\n"
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
    )
    draft = _cover_assessment(_draft(facts), assessment)
    formats = facts.selected_fact("product.formats")
    capability = next(node for node in draft["diagram"]["nodes"] if node["role"] == "capability")
    capability["label"] = "Load XLSX workbooks"
    capability["supporting_fact_ids"] = [formats.fact_id]

    plan = plan_readme_composition(
        facts.org_repo,
        source,
        facts,
        assessment,
        client=_client(draft),
    )

    assert any(node.label == "Load XLSX workbooks" for node in plan.diagram.nodes)
    assert plan.attempt_count == 1


def test_structured_load_save_format_facts_render_as_input_and_output_nouns():
    facts, revision = _facts()
    formats = facts.selected_fact("product.formats")
    facts = facts.model_copy(
        update={
            "facts": [
                fact.model_copy(update={"value": ["Save format: XLSX", "Load formats: AUTO, XLSX"]})
                if fact.fact_id == formats.fact_id
                else fact
                for fact in facts.facts
            ]
        }
    )
    source = "# Product\n"
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
    )
    draft = _cover_assessment(_draft(facts), assessment)
    for node in draft["diagram"]["nodes"]:
        if node["role"] == "input":
            node["label"] = "Reads XLSX files"
            node["supporting_fact_ids"] = [formats.fact_id]
        elif node["role"] == "output":
            node["label"] = "Writes XLSX files"
            node["supporting_fact_ids"] = [formats.fact_id]

    plan = plan_readme_composition(
        facts.org_repo,
        source,
        facts,
        assessment,
        client=_client(draft),
        max_attempts=1,
    )

    input_labels = {node.label for node in plan.diagram.nodes if node.role == "input"}
    output_labels = {node.label for node in plan.diagram.nodes if node.role == "output"}
    assert input_labels == {"XLSX files"}
    assert "XLSX files" in output_labels
    assert not any(
        label.startswith(("Reads ", "Writes ")) for label in input_labels | output_labels
    )


def test_diagram_includes_every_safe_selected_verified_capability():
    facts, revision = _facts()
    capabilities = facts.selected_fact("product.capabilities")
    facts = facts.model_copy(
        update={
            "facts": [
                fact.model_copy(
                    update={
                        "value": [
                            "Create workbooks",
                            "Load workbooks",
                            "Modify workbooks",
                            "Save workbooks",
                            "Read cell values",
                            "Write cell values",
                            "Calculate formulas",
                            "Render worksheets",
                            "Export charts",
                            "Import tabular data",
                            "Protect documents",
                            "Inspect styles",
                            "Manage metadata",
                            "Validate formats",
                            "Load diagnostics and repair reporting",
                        ]
                    }
                )
                if fact.fact_id == capabilities.fact_id
                else fact
                for fact in facts.facts
            ]
        }
    )
    source = "# Product\n"
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
    )
    draft = _cover_assessment(_draft(facts), assessment)
    draft["diagram"]["nodes"] = [
        node
        for node in draft["diagram"]["nodes"]
        if node["label"] != "Load diagnostics and repair reporting"
    ]

    plan = plan_readme_composition(
        facts.org_repo,
        source,
        facts,
        assessment,
        client=_client(draft),
        max_attempts=1,
    )

    capability_labels = {node.label for node in plan.diagram.nodes if node.role == "capability"}
    selected_labels = {str(value) for value in facts.selected_fact("product.capabilities").value}
    assert selected_labels <= capability_labels


def test_domain_package_parts_capability_is_not_misclassified_as_package_infrastructure():
    facts, revision = _facts()
    capabilities = facts.selected_fact("product.capabilities")
    domain_capability = (
        "Load diagnostics, repair reporting, and preservation of unsupported package parts"
    )
    facts = facts.model_copy(
        update={
            "facts": [
                fact.model_copy(update={"value": [domain_capability]})
                if fact.fact_id == capabilities.fact_id
                else fact
                for fact in facts.facts
            ]
        }
    )
    source = "# Product\n"
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
    )
    draft = _cover_assessment(_draft(facts), assessment)
    first_capability = next(
        node for node in draft["diagram"]["nodes"] if node["role"] == "capability"
    )
    first_capability["label"] = "Load diagnostics"
    first_capability["supporting_fact_ids"] = [capabilities.fact_id]

    plan = plan_readme_composition(
        facts.org_repo,
        source,
        facts,
        assessment,
        client=_client(draft),
        max_attempts=1,
    )

    assert any(
        node.role == "capability"
        and node.label
        == "Load diagnostics, repair reporting, preservation of unsupported package parts"
        for node in plan.diagram.nodes
    )


def test_semantic_retry_preserves_independent_repair_and_exact_source_dispositions():
    facts, revision = _facts()
    source = "# Product\n"
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
    )
    invalid = _cover_assessment(_draft(facts), assessment)
    invalid["overview_sentences"][0]["supporting_fact_ids"] = ["invented:fact"]
    valid = _cover_assessment(_draft(facts), assessment)
    messages_seen: list[list[dict]] = []
    results = iter(
        [
            ForcedToolResult(
                arguments=_tool_arguments(invalid),
                meta=LLMResponseMeta(model="fixture-author"),
            ),
            ForcedToolResult(
                arguments=_tool_arguments(valid),
                meta=LLMResponseMeta(model="fixture-author"),
            ),
        ]
    )

    class CapturingClient:
        def call(self, messages, tool_schema):
            messages_seen.append(messages)
            return next(results)

    plan = plan_readme_composition(
        facts.org_repo,
        source,
        facts,
        assessment,
        client=CapturingClient(),
        review_repair={
            "source_candidate_sha256": hashlib.sha256(source.encode()).hexdigest(),
            "failed_criteria": ["opening clarity"],
            "sections_affected": ["At a glance"],
            "required_repair": "Replace the malformed candidate overview.",
            "preserve": ["maintainer introduction"],
            "findings": [
                {
                    "finding_id": "quality.opening",
                    "section": "At a glance",
                    "criterion": "opening clarity",
                    "quoted_candidate_span": "malformed candidate overview",
                    "required_repair": "Replace the malformed candidate overview.",
                }
            ],
        },
    )

    retry_prompt = messages_seen[1][1]["content"]
    assert plan.attempt_count == 2
    assert plan.review_repair is not None
    assert plan.review_repair.findings[0].finding_id == "quality.opening"
    assert "Replace the malformed candidate overview." in plan.authoring_hints
    assert "Replace the malformed candidate overview." in retry_prompt
    assert "copy its paired disposition exactly" in retry_prompt
    assert '"section_id": "missing:at-a-glance"' in retry_prompt
    assert '"disposition": "add"' in retry_prompt
    assert "role-compatible vocabulary" in retry_prompt
    assert "Load and save XLSX workbooks." in retry_prompt
    assert (
        validate_readme_composition_plan(
            plan.model_dump(mode="json"),
            org_repo=facts.org_repo,
            source_text=source,
            facts=facts,
            assessment=assessment,
        )
        == plan
    )

    tampered = plan.model_dump(mode="json")
    tampered["authoring_hints"] = ""
    with pytest.raises(LLMError, match="binding mismatch"):
        validate_readme_composition_plan(
            tampered,
            org_repo=facts.org_repo,
            source_text=source,
            facts=facts,
            assessment=assessment,
        )


def test_agentic_plan_fails_closed_after_bounded_semantic_retries():
    facts, revision = _facts()
    source = "# Product\n"
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
    )
    invalid = _cover_assessment(_draft(facts), assessment)
    invalid["overview_sentences"][0]["supporting_fact_ids"] = ["invented:fact"]

    with pytest.raises(LLMError, match="ineligible overview fact IDs"):
        plan_readme_composition(
            facts.org_repo,
            source,
            facts,
            assessment,
            client=_client(invalid, invalid, invalid),
        )
