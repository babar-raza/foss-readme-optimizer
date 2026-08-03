"""Compact factual-review packet preserves grounding while excluding producer bulk."""

import json
from copy import deepcopy

import pytest

from readme_agent.readme.document_hashing import sha256_hex
from readme_agent.specialists.factual_review_packet import build_factual_review_packet
from readme_agent.specialists.factual_review_projection import compact_plan_context
from readme_agent.specialists.readme_review_roles import json_hash
from readme_agent.specialists.review_finding_grounding import (
    GroundedReviewFindingV1,
    validate_review_findings,
)


def _inputs():
    candidate = "# Example\n\nExample reads ONE files.\n"
    claim_text = "Example reads ONE files."
    start = len(candidate[: candidate.index(claim_text)].encode("utf-8"))
    end = start + len(claim_text.encode("utf-8"))
    facts = {
        "selected_fact_ids": {"product.identity": "fact-1"},
        "facts": [
            {
                "fact_id": "fact-1",
                "field": "product.identity",
                "value": {"product_name": "Example"},
                "verification_state": "verified",
                "source": {"location": "repository://pyproject.toml"},
                "conflicts": [],
                "evidence_assessments": [],
            },
            {
                "fact_id": "fact-unselected",
                "field": "product.capabilities",
                "value": "UNSELECTED_SENTINEL",
                "verification_state": "verified",
                "source": {"location": "repository://README.md"},
                "conflicts": [],
            },
        ],
    }
    operation = {
        "operation_id": "readme.overview",
        "operation": "replace",
        "replacement_text": "RAW_REPLACEMENT_SENTINEL" * 100,
        "fact_ids": ["fact-1"],
        "protected_content_treatment": "authoritative_fact_correction",
        "rationale": "Use the accepted identity.",
    }
    plan = {
        "presentation_plan": {
            "schema_version": 1,
            "archetype": "python-library",
            "actions": [{"action_id": "readme"}],
        },
        "readme_document_plan": {"operations": [operation]},
        "readme_assessment": {
            "sections": [
                {
                    "section_id": "opening",
                    "heading": "Opening",
                    "disposition": "repair",
                    "fact_ids": ["fact-1"],
                    "protected_fragment_ids": ["technical:1"],
                    "rationale": "Correct the product identity.",
                }
            ],
            "material_claims": ["ASSESSMENT_BULK_SENTINEL" * 100],
        },
        "claim_map": {
            "claims": [
                {
                    "claim_id": "readme.overview:product.identity",
                    "operation_id": "readme.overview",
                    "fact_id": "fact-1",
                    "field": "product.identity",
                    "coordinate_space": "candidate_utf8",
                    "byte_start": start,
                    "byte_end": end,
                    "claim_text_sha256": sha256_hex(claim_text),
                    "rationale": "Use the accepted identity.",
                }
            ]
        },
    }
    return candidate, facts, plan


def test_packet_retains_selected_grounding_and_excludes_large_producer_fields():
    candidate, facts, plan = _inputs()

    packet = build_factual_review_packet("example/example-foss", candidate, facts, plan)
    payload = packet.model_dump(mode="json")
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)

    assert packet.product_facts_sha256 == json_hash(facts)
    assert packet.presentation_plan_sha256 == json_hash(plan)
    assert packet.candidate_sha256 == sha256_hex(candidate)
    assert [fact.fact_id for fact in packet.selected_facts] == ["fact-1"]
    assert packet.candidate_claims[0].claim_text == "Example reads ONE files."
    assert packet.candidate_claims[0].verification_state == "verified"
    assert packet.candidate_claims[0].evidence_location == "repository://pyproject.toml"
    assert packet.candidate_claims[0].evidence_excerpt == "Example"
    assert packet.candidate_claims[0].unresolved_conflicts == []
    assert packet.operations[0].operation_id == "readme.overview"
    assert "RAW_REPLACEMENT_SENTINEL" not in serialized
    assert "ASSESSMENT_BULK_SENTINEL" not in serialized
    assert "UNSELECTED_SENTINEL" not in serialized
    assert len(serialized) < len(json.dumps(plan)) // 2


def test_packet_excludes_native_execution_transcripts_but_keeps_full_fact_hash():
    candidate, facts, plan = _inputs()
    facts["selected_fact_ids"]["example.minimal"] = "fact-example"
    facts["facts"].append(
        {
            "fact_id": "fact-example",
            "field": "example.minimal",
            "value": {
                "language": "csharp",
                "code": "Scene scene = new Scene();",
                "verification_outcome": "VERIFIED",
                "compiled_consumer": {"stdout": "native-proof" * 100_000},
            },
            "verification_state": "verified",
            "source": {"location": "local-verifier://example.minimal"},
            "conflicts": [],
            "evidence_assessments": [],
        }
    )

    packet = build_factual_review_packet("example/example-foss", candidate, facts, plan)
    serialized = json.dumps(packet.fact_context(), ensure_ascii=False, sort_keys=True)
    example = next(fact for fact in packet.selected_facts if fact.field == "example.minimal")

    assert packet.product_facts_sha256 == json_hash(facts)
    assert example.value["code"] == "Scene scene = new Scene();"
    assert "compiled_consumer" not in example.value
    assert "native-proof" not in serialized
    assert len(serialized) < 5_000


def test_packet_compacts_api_inventory_and_evidence_context_without_losing_citations():
    candidate, facts, plan = _inputs()
    api_value = {
        "modules": [
            {
                "module": "example.api",
                "exports": [f"Export{index}" for index in range(100)],
                "source_path": "src/example/api.py",
                "source_sha256": "a" * 64,
            }
        ],
        "classes": [
            {
                "name": f"Class{index}",
                "members": [{"surface": f"Class{index}.load(path)"}],
                "source_path": f"src/class_{index}.py",
                "source_sha256": "b" * 64,
            }
            for index in range(100)
        ],
    }
    facts["selected_fact_ids"]["api.public_surface"] = "fact-api"
    facts["facts"].append(
        {
            "fact_id": "fact-api",
            "field": "api.public_surface",
            "value": api_value,
            "verification_state": "verified",
            "source": {"location": "repository://src/example/api.py"},
            "conflicts": [],
            "evidence_assessments": [
                {
                    "claim_text": "Export0",
                    "expected_polarity": "positive_implementation",
                    "observed_polarity": "positive_implementation",
                    "source_path": "src/example/api.py",
                    "line_number": 10,
                    "anchor": "Export0",
                    "exact_excerpt": "class Export0:",
                    "context_excerpt": "native-source-window" * 10_000,
                    "observed_at": "2026-08-03T00:00:00Z",
                    "accepted": True,
                }
            ],
        }
    )

    packet = build_factual_review_packet("example/example-foss", candidate, facts, plan)
    serialized = json.dumps(packet.fact_context(), ensure_ascii=False, sort_keys=True)
    api = next(fact for fact in packet.selected_facts if fact.field == "api.public_surface")

    assert packet.product_facts_sha256 == json_hash(facts)
    assert api.value["inventory_counts"]["exports"] == 100
    assert len(api.value["representative_exports"]) == 16
    assert api.evidence_assessments == [
        {
            "claim_text": "Export0",
            "expected_polarity": "positive_implementation",
            "observed_polarity": "positive_implementation",
            "source_path": "src/example/api.py",
            "line_number": 10,
            "anchor": "Export0",
            "exact_excerpt": "class Export0:",
            "accepted": True,
        }
    ]
    assert "native-source-window" not in serialized
    assert "source_sha256" not in serialized
    assert len(serialized) < len(json.dumps(facts)) // 10


def test_packet_rejects_a_candidate_claim_whose_hash_does_not_match():
    candidate, facts, plan = _inputs()
    plan["claim_map"]["claims"][0]["claim_text_sha256"] = "0" * 64

    with pytest.raises(ValueError, match="claim hash mismatch"):
        build_factual_review_packet("example/example-foss", candidate, facts, plan)


def test_plan_prompt_projection_retains_accountability_and_hashes_omitted_producer_bulk():
    candidate, facts, plan = _inputs()
    plan["presentation_plan"]["actions"][0]["claims"] = [
        {"evidence": "DUPLICATED_ACTION_EVIDENCE" * 10_000}
    ]
    packet = build_factual_review_packet("example/example-foss", candidate, facts, plan)
    context = packet.plan_context()
    serialized = json.dumps(context, ensure_ascii=False, sort_keys=True)
    full_prompt_sources = json.dumps(
        {
            "surface_plan": packet.surface_plan,
            "source_sections": [item.model_dump(mode="json") for item in packet.source_sections],
            "operations": [item.model_dump(mode="json") for item in packet.operations],
            "candidate_claims": [item.model_dump(mode="json") for item in packet.candidate_claims],
        },
        ensure_ascii=False,
        sort_keys=True,
    )

    accountability = context["claim_accountability"]
    assert accountability["total_claim_count"] == 1
    assert accountability["accountable_claim_count"] == 1
    assert accountability["exception_claim_count"] == 0
    assert accountability["exception_claims"] == []
    assert accountability["coverage_by_fact"][0]["fact_id"] == "fact-1"
    assert accountability["coverage_by_fact"][0]["claim_count"] == 1
    assert accountability["coverage_by_fact"][0]["section_ids"] == ["readme.overview"]
    assert "DUPLICATED_ACTION_EVIDENCE" not in serialized
    assert "Use the accepted identity." not in serialized
    assert len(serialized) < len(full_prompt_sources) // 3

    changed_plan = deepcopy(plan)
    changed_plan["presentation_plan"]["actions"][0]["claims"][0]["evidence"] += "changed"
    changed = build_factual_review_packet("example/example-foss", candidate, facts, changed_plan)
    assert changed.presentation_plan_sha256 != packet.presentation_plan_sha256

    changed_claim_plan = deepcopy(plan)
    changed_claim_plan["claim_map"]["claims"][0]["rationale"] = "Different accountability."
    changed_claim = build_factual_review_packet(
        "example/example-foss", candidate, facts, changed_claim_plan
    )
    assert (
        changed_claim.plan_context()["claim_accountability"]["full_artifact_sha256"]
        != accountability["full_artifact_sha256"]
    )


def test_fact_prompt_projection_includes_only_plan_or_claim_referenced_facts():
    candidate, facts, plan = _inputs()
    facts["selected_fact_ids"]["support.routes"] = "fact-support"
    facts["facts"].append(
        {
            **facts["facts"][0],
            "fact_id": "fact-support",
            "field": "support.routes",
            "value": ["Support route omitted from this candidate"],
        }
    )

    packet = build_factual_review_packet("example/example-foss", candidate, facts, plan)
    context = packet.fact_context()

    assert context["selected_fact_ids"] == {"product.identity": "fact-1"}
    assert [fact["fact_id"] for fact in context["selected_facts"]] == ["fact-1"]
    assert context["selected_fact_inventory"]["total_count"] == 2
    assert context["selected_fact_inventory"]["included_count"] == 1
    assert len(context["selected_fact_inventory"]["full_artifact_sha256"]) == 64


def test_unverified_candidate_claim_remains_visible_and_cannot_support_acceptance():
    candidate, facts, plan = _inputs()
    facts["facts"][0]["verification_state"] = "unverified"
    packet = build_factual_review_packet("example/example-foss", candidate, facts, plan)
    accountability = packet.plan_context()["claim_accountability"]
    claim = accountability["exception_claims"][0]

    assert accountability["exception_claim_count"] == 1
    assert claim["verification_state"] == "unverified"
    assert claim["accountability_disposition"] == "blocked_unverified_fact"
    assert claim["evidence_location"] == "repository://pyproject.toml"
    assert claim["evidence_excerpt"] == "Example"
    assert claim["rationale"] == "Use the accepted identity."
    grounding = validate_review_findings(
        candidate_text=candidate,
        product_facts=facts,
        findings=[
            GroundedReviewFindingV1(
                finding_id="factual.unsupported-accept",
                kind="factual",
                criterion="factuality",
                section="overview",
                claim="The candidate claim is supported.",
                quoted_candidate_span="Example reads ONE files.",
                disposition="supports_acceptance",
                fact_id="fact-1",
                evidence_excerpt="Example",
                evidence_location="repository://pyproject.toml",
                expected_polarity="positive_implementation",
                observed_polarity="positive_implementation",
                polarity_result="supports",
                required_repair="",
            )
        ],
    )

    assert not grounding.valid
    assert any("fact is not accepted" in error for error in grounding.errors)


def test_large_accountable_claim_corpus_projects_to_hash_bound_coverage():
    claims = [
        {
            "claim_id": f"claim-{index}",
            "operation_id": f"section-{index % 8}",
            "fact_id": f"fact-{index % 12}",
            "field": f"field-{index % 12}",
            "claim_text": "Accountable claim text that must not be repeated in the prompt.",
            "verification_state": "verified",
            "expected_polarity": "positive_implementation",
            "observed_polarity": "positive_implementation",
            "polarity_result": "supports",
            "accountability_disposition": "accepted_fact",
            "unresolved_conflicts": [],
            "rationale": "Bound by deterministic claim map.",
        }
        for index in range(242)
    ]
    context = compact_plan_context(
        surface_plan={"actions": []},
        source_sections=[],
        operations=[],
        candidate_claims=claims,
    )
    serialized = json.dumps(context, ensure_ascii=False, sort_keys=True)
    accountability = context["claim_accountability"]

    assert accountability["total_claim_count"] == 242
    assert accountability["accountable_claim_count"] == 242
    assert accountability["exception_claim_count"] == 0
    assert len(accountability["coverage_by_fact"]) == 12
    assert "operation_ids" not in accountability["coverage_by_fact"][0]
    assert "Accountable claim text" not in serialized
    assert len(serialized.encode("utf-8")) < 20_000

    changed = deepcopy(claims)
    changed[100]["claim_text"] = "Changed full claim."
    changed_context = compact_plan_context(
        surface_plan={"actions": []},
        source_sections=[],
        operations=[],
        candidate_claims=changed,
    )
    assert (
        changed_context["claim_accountability"]["full_artifact_sha256"]
        != accountability["full_artifact_sha256"]
    )


def test_source_sections_summarize_preserves_and_retain_non_preserve_details():
    sections = [
        {
            "section_id": f"preserved-{index}",
            "heading": f"Preserved {index}",
            "disposition": "preserve",
            "fact_ids": ["fact-1"],
            "protected_fragment_ids": [f"protected-{index}"],
        }
        for index in range(100)
    ]
    sections.append(
        {
            "section_id": "repair-me",
            "heading": "Repair Me",
            "disposition": "repair",
            "fact_ids": ["fact-2"],
            "protected_fragment_ids": ["protected-repair"],
        }
    )

    context = compact_plan_context(
        surface_plan={"actions": []},
        source_sections=sections,
        operations=[],
        candidate_claims=[],
    )
    projection = context["source_sections"]
    serialized = json.dumps(projection, ensure_ascii=False, sort_keys=True)

    assert projection["total_section_count"] == 101
    assert projection["disposition_counts"] == {"preserve": 100, "repair": 1}
    assert projection["protected_fragment_count"] == 101
    assert projection["detailed_non_preserve_sections"] == [sections[-1]]
    assert "Preserved 99" not in serialized

    changed_sections = deepcopy(sections)
    changed_sections[0]["heading"] = "Changed preserved heading"
    changed = compact_plan_context(
        surface_plan={"actions": []},
        source_sections=changed_sections,
        operations=[],
        candidate_claims=[],
    )
    assert changed["source_sections"]["full_artifact_sha256"] != projection["full_artifact_sha256"]


def test_unaccountable_claim_remains_full_after_large_corpus_projection():
    claims = [
        {
            "claim_id": f"claim-{index}",
            "operation_id": f"section-{index % 8}.claim:{index}",
            "fact_id": f"fact-{index % 12}",
            "field": f"field-{index % 12}",
            "claim_text": "Accountable claim.",
            "verification_state": "verified",
            "expected_polarity": "positive_implementation",
            "observed_polarity": "positive_implementation",
            "polarity_result": "supports",
            "accountability_disposition": "accepted_fact",
            "unresolved_conflicts": [],
        }
        for index in range(242)
    ]
    claims[117] = {
        **claims[117],
        "claim_text": "This unsupported claim must remain reviewable.",
        "verification_state": "unverified",
        "accountability_disposition": "blocked_unverified_fact",
    }

    context = compact_plan_context(
        surface_plan={"actions": []},
        source_sections=[],
        operations=[],
        candidate_claims=claims,
    )
    accountability = context["claim_accountability"]

    assert accountability["exception_claim_count"] == 1
    assert accountability["exception_claims"] == [claims[117]]
    assert accountability["coverage_by_fact"][0]["section_ids"]
    assert all(
        ".claim:" not in section_id
        for coverage in accountability["coverage_by_fact"]
        for section_id in coverage["section_ids"]
    )
