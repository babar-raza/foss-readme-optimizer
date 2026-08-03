"""Verified-template claim bridging into repository presentation actions."""

import json
from pathlib import Path

import pytest

from readme_agent.facts.gating import validate_claim_citations
from readme_agent.facts.render_views import visitor_fact_render_view
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.llm.schema import LLMResponseMeta
from readme_agent.llm.verifier_client import FixtureForcedToolClient, ForcedToolResult
from readme_agent.presentation import document_planner
from readme_agent.readme.agentic_composition import plan_readme_composition
from readme_agent.readme.agentic_composition_validation import planning_sections
from readme_agent.readme.assessment import assess_readme_document
from readme_agent.readme.document_renderer import build_readme_document_candidate
from readme_agent.registry.loader import load_policy, require_listed

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FACTS_PROOF = (
    PROJECT_ROOT
    / "plans"
    / "investigations"
    / "evidence"
    / "level8-local-immutable-snapshot-and-facts-corrected-acquisition-2026-07-24"
    / "immutable-snapshot-and-product-facts-proof.json"
)
ORG_REPO = "aspose-cells-foss/Aspose.Cells-FOSS-for-Java"
SOURCE = "# Aspose.Cells FOSS for Java\n"
REVISION = "fixture-revision"


def _facts() -> ProductFactsV2:
    proof = json.loads(FACTS_PROOF.read_text(encoding="utf-8"))
    pilot = next(item for item in proof["current_pilots"] if item["org_repo"] == ORG_REPO)
    return ProductFactsV2.model_validate(pilot["product_facts_v2"])


def _agentic_plan(facts: ProductFactsV2) -> dict:
    assessment = assess_readme_document(ORG_REPO, SOURCE, facts, base_revision=REVISION)
    identity = visitor_fact_render_view(facts, "product.identity")
    audience_view = visitor_fact_render_view(facts, "product.audience")
    problem_view = visitor_fact_render_view(facts, "product.problems_solved")
    audience = facts.selected_fact("product.audience")
    problem = facts.selected_fact("product.problems_solved")
    formats = facts.selected_fact("product.formats")
    capabilities = facts.selected_fact("product.capabilities")
    assert identity is not None and identity.phrases
    assert audience_view is not None and audience_view.phrases
    assert problem_view is not None and problem_view.phrases
    client = FixtureForcedToolClient(
        [
            ForcedToolResult(
                arguments={
                    "repository_summary": "Lead with the verified spreadsheet task.",
                    "section_decisions": [
                        {
                            "section_id": section.section_id,
                            "disposition": section.disposition,
                            "priority": 50,
                            "supporting_fact_ids": [],
                            "rationale": "Retain the source-bound disposition.",
                        }
                        for section in planning_sections(assessment)
                    ],
                    "overview_fact_ids": [audience.fact_id, problem.fact_id],
                    "opening_summary": {
                        "text": (
                            f"{identity.phrases[0]} serves "
                            f"{audience_view.phrases[0].rstrip('.').lower()} "
                            f"It lets them {problem_view.phrases[0].rstrip('.').lower()}."
                        ),
                        "supporting_fact_ids": [
                            identity.fact_id,
                            audience.fact_id,
                            problem.fact_id,
                        ],
                    },
                    "diagram": {
                        "nodes": [
                            {
                                "role": "input",
                                "label": "XLSX workbooks",
                                "supporting_fact_ids": [formats.fact_id],
                            },
                            {
                                "role": "input",
                                "label": "Spreadsheet files",
                                "supporting_fact_ids": [formats.fact_id],
                            },
                            {
                                "role": "input",
                                "label": "Workbook streams",
                                "supporting_fact_ids": [formats.fact_id],
                            },
                            {
                                "role": "capability",
                                "label": "Create spreadsheet files",
                                "supporting_fact_ids": [capabilities.fact_id],
                            },
                            {
                                "role": "capability",
                                "label": "Read spreadsheet content",
                                "supporting_fact_ids": [capabilities.fact_id],
                            },
                            {
                                "role": "capability",
                                "label": "Process workbooks without Excel",
                                "supporting_fact_ids": [problem.fact_id],
                            },
                            {
                                "role": "capability",
                                "label": "Inspect worksheet data",
                                "supporting_fact_ids": [capabilities.fact_id],
                            },
                            {
                                "role": "capability",
                                "label": "Update workbook content",
                                "supporting_fact_ids": [capabilities.fact_id],
                            },
                            {
                                "role": "capability",
                                "label": "Access spreadsheet structure",
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
                                "label": "Formula information",
                                "supporting_fact_ids": [capabilities.fact_id],
                            },
                            {
                                "role": "output",
                                "label": "Spreadsheet documents",
                                "supporting_fact_ids": [formats.fact_id],
                            },
                        ]
                    },
                },
                meta=LLMResponseMeta(model="fixture-author"),
            )
        ]
    )
    return plan_readme_composition(
        ORG_REPO,
        SOURCE,
        facts,
        assessment,
        client=client,
    ).model_dump(mode="json")


def _ownership():
    entry = require_listed(ORG_REPO)
    assert entry.policy_profile is not None
    return load_policy(entry.policy_profile).surface_ownership


def test_verified_template_provenance_makes_presentation_action_eligible() -> None:
    facts = _facts()
    agentic_plan = _agentic_plan(facts)
    candidate, document_plan = build_readme_document_candidate(
        ORG_REPO,
        SOURCE,
        facts,
        base_revision=REVISION,
        agentic_composition_plan=agentic_plan,
    )
    assert document_plan.operations[0].fact_ids == []
    assert any(binding.fact_ids for binding in document_plan.candidate_content_provenance)

    plan, _, executable, _ = document_planner.build_document_repository_presentation_plan(
        ORG_REPO,
        SOURCE,
        SOURCE,
        candidate,
        facts,
        _ownership(),
        base_revision=REVISION,
        agentic_composition_plan=agentic_plan,
    )

    action = plan.actions[0]
    assert executable is True
    assert action.disposition == "eligible"
    assert action.claims
    assert action.fact_ids


def test_unselected_provenance_fact_blocks_presentation_action(monkeypatch) -> None:
    facts = _facts()
    selected = facts.selected_fact("product.identity")
    unselected = selected.model_copy(update={"fact_id": f"{selected.fact_id}.unselected"})
    facts = facts.model_copy(update={"facts": [*facts.facts, unselected]})
    agentic_plan = _agentic_plan(facts)
    candidate, document_plan = build_readme_document_candidate(
        ORG_REPO,
        SOURCE,
        facts,
        base_revision=REVISION,
        agentic_composition_plan=agentic_plan,
    )
    provenance = list(document_plan.candidate_content_provenance)
    target_index = next(index for index, binding in enumerate(provenance) if binding.fact_ids)
    provenance[target_index] = provenance[target_index].model_copy(
        update={"fact_ids": [unselected.fact_id]}
    )
    tampered_plan = document_plan.model_copy(update={"candidate_content_provenance": provenance})
    monkeypatch.setattr(
        document_planner,
        "build_readme_document_candidate",
        lambda *args, **kwargs: (candidate, tampered_plan),
    )

    claims = document_planner._claims(
        facts,
        tampered_plan.operations,
        tampered_plan.candidate_content_provenance,
    )
    citation_decision = validate_claim_citations(facts, claims)
    assert citation_decision.valid is False
    assert any("is not selected" in reason for reason in citation_decision.reasons)

    with pytest.raises(ValueError, match="candidate provenance cites non-selected fact"):
        document_planner.build_document_repository_presentation_plan(
            ORG_REPO,
            SOURCE,
            SOURCE,
            candidate,
            facts,
            _ownership(),
            base_revision=REVISION,
            agentic_composition_plan=agentic_plan,
        )
