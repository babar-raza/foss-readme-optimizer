"""Fact-bound agentic README composition and deterministic rendering tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from readme_agent.errors import LLMError
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.llm.analysis_client import AnalysisResult, FixtureAnalysisClient
from readme_agent.llm.schema import LLMResponseMeta
from readme_agent.readme.agentic_composition import plan_readme_composition
from readme_agent.readme.assessment import assess_readme_document
from readme_agent.readme.claim_map import build_readme_claim_map
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
    client = FixtureAnalysisClient(
        [
            AnalysisResult(
                parsed=_cover_assessment(_draft(facts), assessment),
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
    candidate, document_plan = build_readme_document_candidate(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
        agentic_composition_plan=plan.model_dump(mode="json"),
    )

    assert plan.model == "fixture-author"
    assert plan.input_sha256
    assert plan.prompt_sha256
    assert _first_text(facts.selected_fact("product.audience").value) in candidate
    assert "Lead with the verified spreadsheet audience" not in candidate
    cited_ids = {
        fact_id for operation in document_plan.operations for fact_id in operation.fact_ids
    }
    assert {
        fact_id for sentence in plan.overview_sentences for fact_id in sentence.supporting_fact_ids
    } <= cited_ids
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
    client = FixtureAnalysisClient(
        [
            AnalysisResult(
                parsed=_cover_assessment(
                    _draft(facts, fact_id="invented:fact"),
                    assessment,
                ),
                meta=LLMResponseMeta(model="fixture-author"),
            )
        ]
    )

    with pytest.raises(LLMError, match="unaccepted fact IDs"):
        plan_readme_composition(
            facts.org_repo,
            source,
            facts,
            assessment,
            client=client,
        )


def test_agentic_plan_rejects_extra_uncited_prose_around_a_literal_fact():
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
    client = FixtureAnalysisClient(
        [AnalysisResult(parsed=draft, meta=LLMResponseMeta(model="fixture-author"))]
    )

    with pytest.raises(LLMError, match="exact literal cited fact phrase"):
        plan_readme_composition(
            facts.org_repo,
            source,
            facts,
            assessment,
            client=client,
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
        client=FixtureAnalysisClient(
            [
                AnalysisResult(
                    parsed=_cover_assessment(_draft(facts), assessment),
                    meta=LLMResponseMeta(model="fixture-author"),
                )
            ]
        ),
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
            client=FixtureAnalysisClient(
                [AnalysisResult(parsed=_draft(facts), meta=LLMResponseMeta(model="fixture"))]
            ),
        )
