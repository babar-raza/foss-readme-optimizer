"""Compact factual-review packet preserves grounding while excluding producer bulk."""

import json

import pytest

from readme_agent.readme.document_hashing import sha256_hex
from readme_agent.specialists.factual_review_packet import build_factual_review_packet
from readme_agent.specialists.readme_review_roles import json_hash


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


def test_packet_rejects_a_candidate_claim_whose_hash_does_not_match():
    candidate, facts, plan = _inputs()
    plan["claim_map"]["claims"][0]["claim_text_sha256"] = "0" * 64

    with pytest.raises(ValueError, match="claim hash mismatch"):
        build_factual_review_packet("example/example-foss", candidate, facts, plan)
