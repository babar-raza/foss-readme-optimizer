"""Fact-bound agentic README composition and deterministic rendering tests."""

from __future__ import annotations

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
from readme_agent.readme.agentic_operation_coverage import (
    validate_agentic_operation_coverage,
)
from readme_agent.readme.assessment import assess_readme_document
from readme_agent.readme.claim_map import build_readme_claim_map
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
    return ProductFactsV2.model_validate(pilot["product_facts_v2"]), pilot["snapshot"][
        "source_revision"
    ]


def _first_text(value: object) -> str:
    if isinstance(value, list):
        return str(value[0])
    return str(value)


def _draft(facts: ProductFactsV2, *, fact_id: str | None = None) -> dict:
    audience = facts.selected_fact("product.audience")
    problem = facts.selected_fact("product.problems_solved")
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
    }


def _tool_arguments(draft: dict) -> dict:
    return {
        "repository_summary": draft["repository_summary"],
        "section_decisions": draft["section_decisions"],
        "overview_fact_ids": [
            sentence["supporting_fact_ids"][0] for sentence in draft["overview_sentences"]
        ],
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


def test_agentic_plan_is_source_and_fact_bound_and_changes_the_candidate():
    facts, revision = _facts()
    source = "# Aspose.Cells FOSS for Java\n\nMaintainer introduction.\n"
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
    )
    client = _client(_cover_assessment(_draft(facts), assessment))

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

    assert plan.model == "fixture-author"
    assert plan.attempt_count == 1
    assert plan.input_sha256
    assert plan.prompt_sha256
    assert plan.tool_schema_sha256
    assert _first_text(facts.selected_fact("product.audience").value) in candidate
    assert "Lead with the verified spreadsheet audience" not in candidate
    cited_ids = {
        fact_id for operation in document_plan.operations for fact_id in operation.fact_ids
    }
    assert {
        fact_id for sentence in plan.overview_sentences for fact_id in sentence.supporting_fact_ids
    } <= cited_ids
    assert facts.selected_fact("product.formats").fact_id not in cited_ids
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
    assert "Primary verified task" in candidate
    assert "Secondary verified task" not in candidate


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
            "failed_criteria": ["opening clarity"],
            "sections_affected": ["At a glance"],
            "required_repair": "Replace the malformed candidate overview.",
            "preserve": ["maintainer introduction"],
        },
    )

    retry_prompt = messages_seen[1][1]["content"]
    assert plan.attempt_count == 2
    assert "Replace the malformed candidate overview." in retry_prompt
    assert "copy its paired disposition exactly" in retry_prompt
    assert '"section_id": "missing:at-a-glance"' in retry_prompt
    assert '"disposition": "add"' in retry_prompt


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
