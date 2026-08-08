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
from readme_agent.presentation.verified_template_provenance import build_source_claim_resolutions
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
from readme_agent.readme.agentic_composition_models import (
    MAX_AUTHORING_ATTEMPTS,
    AgenticDiagramNodeV1,
)
from readme_agent.readme.agentic_operation_coverage import (
    validate_agentic_operation_coverage,
)
from readme_agent.readme.assessment import assess_readme_document
from readme_agent.readme.claim_accountability_validation import validate_claim_accountability_map
from readme_agent.readme.claim_map import build_readme_claim_map
from readme_agent.readme.composition_lineage_models import ExactSourcePlacementV1
from readme_agent.readme.diagram_role_semantics import (
    normalize_diagram_role_nodes,
    validate_diagram_role_fact_semantics,
)
from readme_agent.readme.document_renderer import build_readme_document_candidate
from readme_agent.readme.document_validation import validate_readme_document_candidate
from readme_agent.readme.fact_grounding import literal_fact_ids
from readme_agent.readme.verified_preservation_composition import (
    build_verified_preservation_composition_plan,
)

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
    "0b04df12d3ffcbde3e72fe68168ba51c5dbdd511b7a408ff16ac0a534c2ceb15"
)
CHARACTERIZATION_DOCUMENT_PLAN_SHA256 = (
    "a73ff306744157df88970db141cf61df13c23b61ab58c142abd9d44998a8ef1c"
)
CHARACTERIZATION_CANDIDATE_SHA256 = (
    "826b15a4e9bffe6dfc25d6fd35c1c5dba2ee236e33748b89ef570abfc09d5b05"
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
        == 1
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
    assert "**Create and manage XLSX workbooks**" in candidate
    assert "**Edit spreadsheet cell values and styles**" in candidate
    assert "Lead with the verified spreadsheet audience" not in candidate
    cited_ids = {
        fact_id
        for binding in document_plan.candidate_content_provenance
        for fact_id in binding.fact_ids
    }
    planned_fact_ids = {
        fact_id for sentence in plan.overview_sentences for fact_id in sentence.supporting_fact_ids
    }
    assert planned_fact_ids <= cited_ids
    summary_equivalence = next(
        resolution
        for resolution in document_plan.source_claim_resolutions
        if resolution.resolution == "verified_equivalence"
    )
    assert any(
        segment.origin != "source_preserved"
        and draft["opening_summary"]["text"] in segment.content_text
        for segment in document_plan.composition_ledger.segments
    )
    assert summary_equivalence.candidate_byte_start is not None
    assert summary_equivalence.candidate_byte_end is not None
    assert not any(
        placement.final_byte_start < summary_equivalence.candidate_byte_end
        and summary_equivalence.candidate_byte_start < placement.final_byte_end
        for placement in document_plan.composition_ledger.source_placements
    )
    injected_source_owner = ExactSourcePlacementV1(
        placement_id="source.tamper.summary",
        placement_basis="structural_exact_equivalence",
        source_owner_id=summary_equivalence.claim_id,
        structural_role="opening_material_claim",
        source_byte_start=summary_equivalence.source_byte_start,
        source_byte_end=summary_equivalence.source_byte_end,
        source_content_sha256=summary_equivalence.content_sha256,
        final_byte_start=summary_equivalence.candidate_byte_start,
        final_byte_end=summary_equivalence.candidate_byte_end,
        final_content_sha256=summary_equivalence.candidate_content_sha256,
    )
    tampered_ledger = document_plan.composition_ledger.model_copy(
        update={
            "source_placements": [
                *document_plan.composition_ledger.source_placements,
                injected_source_owner,
            ]
        }
    )
    tampered_validation = validate_claim_accountability_map(
        document_plan.claim_accountability,
        source_text=source,
        candidate_text=candidate,
        facts=facts,
        operations=document_plan.operations,
        candidate_content_provenance=document_plan.candidate_content_provenance,
        source_claim_resolutions=document_plan.source_claim_resolutions,
        composition_ledger=tampered_ledger,
    )
    assert tampered_validation.checks["verified_equivalences_have_exact_candidate_claims"] is False
    no_ledger_validation = validate_claim_accountability_map(
        document_plan.claim_accountability,
        source_text=source,
        candidate_text=candidate,
        facts=facts,
        operations=document_plan.operations,
        candidate_content_provenance=document_plan.candidate_content_provenance,
        source_claim_resolutions=document_plan.source_claim_resolutions,
        composition_ledger=None,
    )
    assert no_ledger_validation.checks["verified_equivalences_have_exact_candidate_claims"] is False
    assert facts.selected_fact("product.formats").fact_id in cited_ids
    claim_map = build_readme_claim_map(
        document_plan,
        facts,
        source_text=source,
        candidate_text=candidate,
    )
    assert any(
        claim.fact_id == facts.selected_fact("product.audience").fact_id
        for claim in claim_map.claims
    )


def test_fact_grounded_diagram_labels_do_not_drop_capability_semantics():
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
    assert "**Create and manage XLSX workbooks**" in candidate
    assert "**Edit spreadsheet cell values and styles**" in candidate
    assert any(node.role == "capability" for node in plan.diagram.nodes)
    capability_bindings = [
        binding
        for binding in document_plan.candidate_content_provenance
        if capability.fact_id in binding.fact_ids
        and binding.provenance_id.startswith("template.section.key_capabilities.claim:")
    ]
    assert len(capability_bindings) == 2
    assert all(
        candidate.encode("utf-8")[binding.candidate_byte_start : binding.candidate_byte_end].strip()
        for binding in capability_bindings
    )
    assert claim_map.candidate_sha256 == document_plan.candidate_sha256


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


def test_generic_endpoint_requires_an_exact_cited_fact_phrase():
    facts, _revision = _facts()
    formats = facts.selected_fact("product.formats")
    facts = facts.model_copy(
        update={
            "facts": [
                fact.model_copy(update={"value": ["document files"]})
                if fact.field == "product.formats"
                else fact
                for fact in facts.facts
            ]
        }
    )

    validate_diagram_role_fact_semantics(
        [
            AgenticDiagramNodeV1(
                role="input",
                label="document files",
                supporting_fact_ids=[formats.fact_id],
            )
        ],
        facts,
    )
    with pytest.raises(LLMError, match="not an explicitly verified consumed input"):
        validate_diagram_role_fact_semantics(
            [
                AgenticDiagramNodeV1(
                    role="input",
                    label="content files",
                    supporting_fact_ids=[formats.fact_id],
                )
            ],
            facts,
        )


def test_passive_content_capabilities_are_not_reclassified_as_outputs():
    facts, _revision = _facts()
    replacements = {
        "product.formats": ["Input format: Microsoft OneNote (.one)", "Output format: PDF"],
        "product.capabilities": [
            "Document and traversal",
            "Page and Title nodes",
            "RichText with formatting runs",
            "Image and AttachedFile content",
            "Table with rows and cells",
            "OneNote tags on content nodes",
            "Numbered lists and outline elements",
            "PDF export via SaveFormat.Pdf",
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
    outputs = {node.label for node in nodes if node.role == "output"}

    assert outputs == {"PDF files"}


def test_llm_cannot_reclassify_a_passive_content_capability_as_an_output():
    facts, _revision = _facts()
    formats = facts.selected_fact("product.formats")
    capabilities = facts.selected_fact("product.capabilities")
    replacements = {
        "product.formats": ["Input format: Microsoft OneNote (.one)", "Output format: PDF"],
        "product.capabilities": ["Page and Title nodes", "PDF export via SaveFormat.Pdf"],
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
    adversarial_proposal = [
        AgenticDiagramNodeV1(
            role="output",
            label="Page and Title nodes",
            supporting_fact_ids=[capabilities.fact_id],
        ),
        AgenticDiagramNodeV1(
            role="input",
            label="PDF files",
            supporting_fact_ids=[formats.fact_id],
        ),
    ]

    nodes = normalize_diagram_role_nodes(
        adversarial_proposal,
        facts,
        {"input": 1, "capability": 1, "output": 1},
    )

    assert {node.label for node in nodes if node.role == "output"} == {"PDF files"}
    assert {node.label for node in nodes if node.role == "input"} == {
        "Microsoft OneNote (.one) files"
    }
    assert "Page and Title nodes" in {node.label for node in nodes if node.role == "capability"}


def test_diagram_normalization_is_stable_across_different_llm_proposals():
    facts, _revision = _facts()
    formats = facts.selected_fact("product.formats")
    capabilities = facts.selected_fact("product.capabilities")
    first = [
        AgenticDiagramNodeV1(
            role="input",
            label="XLSX workbooks",
            supporting_fact_ids=[formats.fact_id],
        )
    ]
    second = [
        AgenticDiagramNodeV1(
            role="output",
            label="Create workbooks",
            supporting_fact_ids=[capabilities.fact_id],
        )
    ]

    first_normalized = normalize_diagram_role_nodes(
        first,
        facts,
        {"input": 1, "capability": 1, "output": 1},
    )
    second_normalized = normalize_diagram_role_nodes(
        second,
        facts,
        {"input": 1, "capability": 1, "output": 1},
    )

    assert [node.model_dump(mode="json") for node in first_normalized] == [
        node.model_dump(mode="json") for node in second_normalized
    ]


def test_diagram_normalization_accepts_only_a_complete_authoritative_reordering():
    facts, _revision = _facts()
    canonical = normalize_diagram_role_nodes(
        [],
        facts,
        {"input": 1, "capability": 1, "output": 1},
    )
    proposed = [
        node
        for role in ("input", "capability", "output")
        for node in reversed([item for item in canonical if item.role == role])
    ]

    reordered = normalize_diagram_role_nodes(
        proposed,
        facts,
        {"input": 1, "capability": 1, "output": 1},
    )

    for role in ("input", "capability", "output"):
        expected = [node.label for node in proposed if node.role == role]
        actual = [node.label for node in reordered if node.role == role]
        assert actual == expected


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


def test_document_validation_does_not_force_extra_problem_phrases_into_the_diagram():
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
    assert problem.fact_id not in document_plan.header_visuals.diagram_fact_ids
    assert candidate.count("Secondary verified task") == 0
    assert '["Secondary verified task"]' not in candidate


def test_taxonomy_opening_is_replaced_with_verified_directional_format_prose():
    facts, revision = _facts()
    replacements = {
        "product.identity": {
            "product_name": "Aspose.Note",
            "family": "note",
            "ecosystem": "python",
        },
        "product.audience": ["Developers using Python."],
        "product.problems_solved": ["Document and traversal"],
        "product.formats": [
            "Input format: Microsoft OneNote (.one)",
            "Output format: PDF",
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
    problem = facts.selected_fact("product.problems_solved")
    facts = facts.model_copy(
        update={
            "facts": [
                fact.model_copy(
                    update={
                        "source": fact.source.model_copy(
                            update={"source_type": "mechanical_repository"}
                        )
                    }
                )
                if fact.fact_id == problem.fact_id
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
    draft["opening_summary"] = {
        "text": (
            "Aspose.Note FOSS for Python is free and handles OneNote. "
            "For Developers using Python., it provides an Aspose-like API."
        ),
        "supporting_fact_ids": [
            facts.selected_fact_ids["product.identity"],
            facts.selected_fact_ids["product.audience"],
            facts.selected_fact_ids["product.problems_solved"],
        ],
    }

    plan = plan_readme_composition(
        facts.org_repo,
        source,
        facts,
        assessment,
        client=_client(draft),
        max_attempts=1,
    )

    assert plan.opening_summary is not None
    assert plan.opening_summary.text == (
        "Aspose.Note FOSS for Python is an open-source library for developers using Python. "
        "It reads Microsoft OneNote (.one) files and writes PDF files."
    )


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
    candidate, document_plan = build_readme_document_candidate(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
        agentic_composition_plan=plan.model_dump(mode="json"),
    )
    decision = validate_readme_document_candidate(source, candidate, document_plan, facts)

    assert "maintainer_api_contract()" not in candidate
    assert decision.valid is False
    assert decision.checks["claim_accountability_complete"] is False
    assert document_plan.claim_accountability is not None
    protected_source = next(
        record
        for record in document_plan.claim_accountability.claims
        if record.stage == "source" and record.source_byte_start > 0
    )
    assert protected_source.survives_in_candidate is False
    assert protected_source.currently_accountable is False
    assert any("claim accountability has" in error for error in decision.errors)


def test_real_3d_python_preserve_plan_keeps_exact_claims_and_corrects_only_owned_claims():
    source = (
        PROJECT_ROOT / "tests" / "fixtures" / "readmes" / "real_audit_2026-07-17" / "3d-python.md"
    ).read_text(encoding="utf-8")
    facts = ProductFactsV2.model_validate_json(
        (
            PROJECT_ROOT
            / "tests"
            / "fixtures"
            / "readmes"
            / "verified_source_assurance"
            / "aspose-3d-python-facts-ab1a2267.json"
        ).read_text(encoding="utf-8")
    )
    revision = "ab1a2267a0ba6302311d0c7c4ad01494974c7d76"
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
    )
    composition = build_verified_preservation_composition_plan(
        facts.org_repo,
        source,
        facts,
        assessment,
        lifecycle_status="FACTS_READY",
    )
    assert composition is not None

    candidate, document_plan = build_readme_document_candidate(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
        agentic_composition_plan=composition.model_dump(mode="json"),
    )
    decision = validate_readme_document_candidate(source, candidate, document_plan, facts)
    preserved = next(
        claim
        for claim in assessment.material_claims
        if claim.claim_id == "claim:29:47f5129fce47e0c8"
    )
    preserved_text = source.encode("utf-8")[
        preserved.source_byte_start : preserved.source_byte_end
    ].decode("utf-8")
    preserved_resolution = next(
        item
        for item in document_plan.source_claim_resolutions
        if item.claim_id == preserved.claim_id
    )
    promo = next(
        claim
        for claim in assessment.material_claims
        if claim.disposition == "remove_update" and claim.source_byte_start == 349
    )
    promo_resolution = next(
        (
            item
            for item in document_plan.source_claim_resolutions
            if item.claim_id == promo.claim_id
        ),
        None,
    )
    assert document_plan.claim_accountability is not None
    promo_accountability = next(
        item
        for item in document_plan.claim_accountability.claims
        if item.stage == "source"
        and item.source_byte_start == promo.source_byte_start
        and item.source_byte_end == promo.source_byte_end
    )

    assert decision.valid is False
    assert decision.checks["adoption_preserved_source"] is True
    assert decision.checks["no_introduced_duplicate_headings"] is True
    assert decision.checks["claim_accountability_complete"] is False
    assert decision.checks["claim_accountability_gaps_visible"] is True
    assert candidate.count(preserved_text) == 0
    assert preserved_resolution.source_byte_start == preserved.source_byte_start
    assert preserved_resolution.source_byte_end == preserved.source_byte_end
    assert preserved_resolution.content_sha256 == preserved.content_sha256
    assert preserved_resolution.resolution == "deferred_verification"
    assert preserved_resolution.obligation_id is None
    assert preserved_resolution.fact_ids == []
    assert preserved_resolution.replacement_provenance_ids == []
    assert f"source-claim:{preserved.claim_id}" in preserved_resolution.evidence
    assert f"source-content-sha256:{preserved.content_sha256}" in preserved_resolution.evidence
    assert "unverified-source-detail-for:product_overview" in preserved_resolution.evidence
    assert "candidate-core-validated-separately" in preserved_resolution.evidence
    assert promo_resolution is None
    assert promo_accountability.expected_disposition == "required_correction"
    assert promo_accountability.currently_accountable is False
    assert candidate.count("# Aspose.3D FOSS for Python") == 1
    assert candidate.count("## Navigation") == 1
    assert candidate.count("## License") == 1
    assert candidate.count("```mermaid") == 1
    assert "# Create a new scene" not in candidate
    assert "# Import an OBJ file" not in candidate
    assert "# Access imported data" not in candidate
    assert 'scene.open("model.obj", options)' not in candidate
    preserved_accountability = next(
        item
        for item in document_plan.claim_accountability.claims
        if item.stage == "source"
        and item.source_byte_start == preserved.source_byte_start
        and item.source_byte_end == preserved.source_byte_end
    )
    assert preserved_accountability.expected_disposition == "deferred_verification"
    assert preserved_accountability.currently_accountable is True
    assert preserved_accountability.survives_in_candidate is False
    assert preserved_accountability.accepted_fact_ids == []
    comment_corrections = [
        correction
        for resolution in document_plan.source_claim_resolutions
        for correction in resolution.policy_corrections
        if "readme.no_comments" in correction.configured_standard_ids
    ]
    assert not comment_corrections
    ledger = document_plan.composition_ledger
    assert ledger.candidate_sha256 == document_plan.candidate_sha256
    assert ledger.operation_reconstruction_sha256 == document_plan.candidate_sha256
    assert b"".join(segment.content_text.encode("utf-8") for segment in ledger.segments) == (
        candidate.encode("utf-8")
    )
    assert not ledger.source_placements
    assert all(
        segment.fact_ids or segment.configured_standard_ids
        for segment in ledger.segments
        if segment.origin != "source_preserved"
    )

    rerun_assessment = assess_readme_document(
        facts.org_repo,
        candidate,
        facts,
        base_revision=revision,
    )
    rerun_composition = build_verified_preservation_composition_plan(
        facts.org_repo,
        candidate,
        facts,
        rerun_assessment,
        lifecycle_status="FACTS_READY",
    )
    assert rerun_composition is not None
    rerendered, rerun_plan = build_readme_document_candidate(
        facts.org_repo,
        candidate,
        facts,
        base_revision=revision,
        agentic_composition_plan=rerun_composition.model_dump(mode="json"),
    )
    assert rerendered == candidate
    assert rerun_plan.operations == []
    assert rerun_plan.candidate_sha256 == document_plan.candidate_sha256
    assert rerun_plan.source_claim_resolutions == []
    assert [
        placement.placement_basis for placement in rerun_plan.composition_ledger.source_placements
    ] == ["no_op_whole_source"]

    mixed_source = (
        "# Aspose.3D FOSS for Python\n\n"
        "## Overview\n\n"
        "Aspose.3D FOSS for Python supports XYZQ teleport conversion under the MIT license.\n"
    )
    with pytest.raises(
        ValueError,
        match="fact-authorized preservation claim range is partial, spoofed, or stale",
    ):
        build_source_claim_resolutions(
            mixed_source,
            candidate,
            facts,
            document_plan.candidate_content_provenance,
            preserved_source_ranges=[(0, len(mixed_source.encode("utf-8")))],
        )

    malicious_claim = next(
        claim
        for claim in assess_readme_document(
            facts.org_repo,
            mixed_source,
            facts,
            base_revision=revision,
        ).material_claims
        if "XYZQ teleport"
        in mixed_source.encode()[claim.source_byte_start : claim.source_byte_end].decode()
    )
    unauthorized = build_source_claim_resolutions(
        mixed_source,
        candidate,
        facts,
        document_plan.candidate_content_provenance,
        authoritative_correction_ranges=[
            (malicious_claim.source_byte_start, malicious_claim.source_byte_end)
        ],
    )
    assert all(item.claim_id != malicious_claim.claim_id for item in unauthorized)


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


def test_agentic_plan_repairs_opening_that_only_paraphrases_audience():
    facts, revision = _facts()
    source = "# Product\n"
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
    )
    invalid = _cover_assessment(_draft(facts), assessment)
    invalid["opening_summary"]["text"] = (
        "Aspose.Cells FOSS for Java is an open-source spreadsheet library for programmers."
    )
    valid = _cover_assessment(_draft(facts), assessment)

    plan = plan_readme_composition(
        facts.org_repo,
        source,
        facts,
        assessment,
        client=_client(invalid, valid),
    )

    assert _first_text(facts.selected_fact("product.audience").value) in plan.opening_summary.text
    assert plan.attempt_count == 2


def test_agentic_plan_repairs_opening_that_embeds_raw_capability_inventory():
    facts, revision = _facts()
    capabilities = facts.selected_fact("product.capabilities")
    replacement = capabilities.model_copy(
        update={"value": ["Workbook and worksheet content", "Cell values and formulas"]}
    )
    facts = facts.model_copy(
        update={
            "facts": [
                replacement if fact.fact_id == capabilities.fact_id else fact
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
    invalid = _cover_assessment(_draft(facts), assessment)
    audience = _first_text(facts.selected_fact("product.audience").value)
    invalid["opening_summary"]["text"] = (
        "Aspose.Cells FOSS for Java provides Workbook and worksheet content and Cell values "
        "and formulas "
        f"for {audience.rstrip('.').casefold()}."
    )
    valid = _cover_assessment(_draft(facts), assessment)
    valid["opening_summary"]["text"] = (
        "Aspose.Cells FOSS for Java is an open-source Java library for "
        f"{audience.rstrip('.').casefold()} that reads and writes XLSX workbooks."
    )

    plan = plan_readme_composition(
        facts.org_repo,
        source,
        facts,
        assessment,
        client=_client(invalid, valid),
    )

    assert plan.opening_summary.text == valid["opening_summary"]["text"]
    assert plan.attempt_count == 2


def test_agentic_plan_uses_fact_literal_format_fallback_after_repeated_raw_inventory():
    facts, revision = _facts()
    replacements = {
        "product.formats": ["Input format: XLSX", "Output format: CSV"],
        "product.capabilities": ["Workbook and worksheet content", "Cell values and formulas"],
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
    source = "# Product\n"
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
    )
    invalid = _cover_assessment(_draft(facts), assessment)
    audience = _first_text(facts.selected_fact("product.audience").value)
    invalid["opening_summary"]["text"] = (
        "Aspose.Cells FOSS for Java provides Workbook and worksheet content and Cell values "
        f"and formulas for {audience.rstrip('.').casefold()}."
    )

    plan = plan_readme_composition(
        facts.org_repo,
        source,
        facts,
        assessment,
        client=_client(invalid, invalid),
    )

    assert "It reads XLSX files and writes CSV files." in plan.opening_summary.text
    assert "provides Workbook and worksheet content" not in plan.opening_summary.text
    assert plan.opening_summary.supporting_fact_ids == [
        facts.selected_fact("product.identity").fact_id,
        facts.selected_fact("product.audience").fact_id,
        facts.selected_fact("product.formats").fact_id,
    ]
    assert facts.selected_fact("product.formats").fact_id in literal_fact_ids(
        plan.opening_summary.text,
        facts,
        [facts.selected_fact("product.formats").fact_id],
    )
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


def test_agentic_plan_uses_format_fallback_after_repeated_promotional_opening():
    facts, revision = _facts()
    formats = facts.selected_fact("product.formats")
    facts = facts.model_copy(
        update={
            "facts": [
                fact.model_copy(update={"value": ["Input format: XLSX", "Output format: CSV"]})
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
    invalid = _cover_assessment(_draft(facts), assessment)
    invalid["opening_summary"]["text"] += " Compare the Enterprise Edition."

    plan = plan_readme_composition(
        facts.org_repo,
        source,
        facts,
        assessment,
        client=_client(invalid, invalid),
    )

    assert "Enterprise Edition" not in plan.opening_summary.text
    assert "It reads XLSX files and writes CSV files." in plan.opening_summary.text
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


def test_agentic_plan_cannot_reclassify_a_format_as_an_extra_capability():
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

    assert all(node.label != "Load XLSX workbooks" for node in plan.diagram.nodes)
    assert any(node.role == "input" and "XLSX" in node.label for node in plan.diagram.nodes)
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
