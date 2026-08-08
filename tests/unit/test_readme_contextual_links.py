"""Prove contextual links and Enterprise terminology through the README document seam."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.links.catalog import load_aspose_link_catalogs
from readme_agent.links.catalog_models import AsposeLinkCatalogSetV1
from readme_agent.presentation.verified_template_document import (
    build_verified_template_document_candidate,
)
from readme_agent.readme.agentic_composition_models import (
    AgenticDiagramNodeV1,
    AgenticDiagramV1,
    AgenticOverviewSentenceV1,
    AgenticSectionDecisionV1,
    ReadmeAgenticCompositionPlanV1,
)
from readme_agent.readme.assessment import assess_readme_document
from readme_agent.readme.document_plan import ReadmeDocumentPlanV1
from readme_agent.readme.document_renderer import build_readme_document_candidate
from readme_agent.readme.document_validation import (
    DocumentCandidateValidationV1,
    validate_readme_document_candidate,
)
from readme_agent.registry.models import LinkAllocationPolicyV1

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FACTS_PATH = (
    PROJECT_ROOT
    / "plans/investigations/evidence/level8-readme-header-visual-contract"
    / "representatives/python/product-facts-v2.json"
)
VERIFIED_FACTS_PATH = (
    PROJECT_ROOT
    / "plans"
    / "investigations"
    / "evidence"
    / "level8-local-immutable-snapshot-and-facts-corrected-acquisition-2026-07-24"
    / "immutable-snapshot-and-product-facts-proof.json"
)
ORG_REPO = "aspose-3d-foss/Aspose.3D-FOSS-for-Python"
REPRESENTATIVE_ROOT = (
    PROJECT_ROOT
    / "plans/investigations/evidence/level8-readme-header-visual-contract/representatives"
)


def _facts() -> ProductFactsV2:
    return ProductFactsV2.model_validate(json.loads(FACTS_PATH.read_text(encoding="utf-8")))


def _verified_facts() -> ProductFactsV2:
    proof = json.loads(VERIFIED_FACTS_PATH.read_text(encoding="utf-8"))
    pilot = next(
        item
        for item in proof["current_pilots"]
        if item["org_repo"] == "aspose-cells-foss/Aspose.Cells-FOSS-for-Java"
    )
    return ProductFactsV2.model_validate(pilot["product_facts_v2"])


def _verified_plan(facts: ProductFactsV2, source: str) -> ReadmeAgenticCompositionPlanV1:
    identity = facts.selected_fact("product.identity")
    audience = facts.selected_fact("product.audience")
    problems = facts.selected_fact("product.problems_solved")
    capabilities = facts.selected_fact("product.capabilities")
    formats = facts.selected_fact("product.formats")
    audience_text = str(audience.value[0] if isinstance(audience.value, list) else audience.value)
    problem_text = str(problems.value[0] if isinstance(problems.value, list) else problems.value)
    capability_values = (
        capabilities.value if isinstance(capabilities.value, list) else [capabilities.value]
    )
    format_value = str(formats.value[0] if isinstance(formats.value, list) else formats.value)
    revision = facts.selected_fact("product.identity").source.source_revision
    assert revision is not None
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
    )
    return ReadmeAgenticCompositionPlanV1(
        org_repo=facts.org_repo,
        source_sha256=assessment.source_sha256,
        facts_hash=facts.canonical_hash(),
        assessment_hash=assessment.canonical_hash(),
        prompt_sha256="c" * 64,
        tool_schema_sha256="d" * 64,
        input_sha256="e" * 64,
        model="fixture-author",
        attempt_count=1,
        repository_summary="Organize the accepted repository facts for a visitor.",
        section_decisions=[
            AgenticSectionDecisionV1(
                section_id="opening",
                disposition="rewrite",
                priority=100,
                supporting_fact_ids=[identity.fact_id, audience.fact_id],
                rationale="Lead with accepted identity and audience evidence.",
            )
        ],
        overview_sentences=[
            AgenticOverviewSentenceV1(
                text=audience_text,
                supporting_fact_ids=[audience.fact_id],
            ),
            AgenticOverviewSentenceV1(
                text=problem_text,
                supporting_fact_ids=[problems.fact_id],
            ),
        ],
        opening_summary=AgenticOverviewSentenceV1(
            text=(
                f"{identity.value} helps {audience_text.rstrip('.').lower()} work with "
                f"{format_value} content."
            ),
            supporting_fact_ids=[identity.fact_id, audience.fact_id, formats.fact_id],
        ),
        diagram=AgenticDiagramV1(
            nodes=[
                AgenticDiagramNodeV1(
                    role="input",
                    label=format_value,
                    supporting_fact_ids=[formats.fact_id],
                ),
                AgenticDiagramNodeV1(
                    role="input",
                    label=f"{format_value} files",
                    supporting_fact_ids=[formats.fact_id],
                ),
                AgenticDiagramNodeV1(
                    role="input",
                    label=f"{format_value} streams",
                    supporting_fact_ids=[formats.fact_id],
                ),
                *[
                    AgenticDiagramNodeV1(
                        role="capability",
                        label=str(value),
                        supporting_fact_ids=[capabilities.fact_id],
                    )
                    for value in capability_values[:3]
                ],
                AgenticDiagramNodeV1(
                    role="capability",
                    label=format_value,
                    supporting_fact_ids=[formats.fact_id],
                ),
                AgenticDiagramNodeV1(
                    role="capability",
                    label=f"Inspect {format_value}",
                    supporting_fact_ids=[capabilities.fact_id],
                ),
                AgenticDiagramNodeV1(
                    role="capability",
                    label=f"Update {format_value}",
                    supporting_fact_ids=[capabilities.fact_id],
                ),
                AgenticDiagramNodeV1(
                    role="capability",
                    label=f"Process {format_value} content",
                    supporting_fact_ids=[capabilities.fact_id],
                ),
                AgenticDiagramNodeV1(
                    role="output",
                    label=f"Updated {format_value}",
                    supporting_fact_ids=[formats.fact_id],
                ),
                AgenticDiagramNodeV1(
                    role="output",
                    label=f"{format_value} content",
                    supporting_fact_ids=[capabilities.fact_id],
                ),
                AgenticDiagramNodeV1(
                    role="output",
                    label=f"{format_value} metadata",
                    supporting_fact_ids=[capabilities.fact_id],
                ),
                AgenticDiagramNodeV1(
                    role="output",
                    label=f"{format_value} structure",
                    supporting_fact_ids=[capabilities.fact_id],
                ),
                AgenticDiagramNodeV1(
                    role="output",
                    label=f"Processed {format_value}",
                    supporting_fact_ids=[formats.fact_id],
                ),
            ]
        ),
    )


def _assert_contextual_compatibility_claim_block(
    validation: DocumentCandidateValidationV1,
    plan: ReadmeDocumentPlanV1,
) -> None:
    """Keep link/no-op proof distinct from verified candidate approval."""

    assert validation.valid is False
    assert validation.checks["contextual_links"] is True
    assert validation.checks["document_reconstruction"] is True
    assert validation.checks["source_span_hashes"] is True
    assert validation.checks["fact_citations"] is True
    assert validation.checks["claim_accountability_complete"] is False
    assert validation.checks["claim_accountability_gaps_visible"] is True
    assert plan.claim_accountability is not None
    blockers = sorted(
        record.claim_id
        for record in plan.claim_accountability.claims
        if not record.currently_accountable
    )
    expected = f"claim accountability has {len(blockers)} blocking claim(s): " + ", ".join(
        blockers[:10]
    )
    assert expected in validation.errors


def test_verified_opening_summary_is_not_padded_with_fragmentary_overview_phrases() -> None:
    facts = _verified_facts()
    revision = facts.selected_fact("product.identity").source.source_revision
    assert revision is not None
    source = "# Existing title\n"
    plan = _verified_plan(facts, source)
    assert plan.opening_summary is not None
    problem_text = plan.overview_sentences[1].text

    candidate, _document_plan = build_verified_template_document_candidate(
        facts,
        source,
        revision,
        plan,
    )
    opening = candidate.split("\n## Navigation", 1)[0]

    assert plan.opening_summary.text in opening
    assert problem_text not in opening


@pytest.fixture(scope="module")
def catalogs() -> AsposeLinkCatalogSetV1:
    return load_aspose_link_catalogs()


def test_document_prioritizes_verified_product_relationship_then_noops() -> None:
    facts = _facts()
    revision = facts.selected_fact("product.identity").source.source_revision
    assert revision is not None
    source = """# Aspose.3D FOSS for Python

Maintainer introduction.

## Quick start

Run the minimal example below.

## Editions

For a broader feature set, see the [commercial On-Premise edition](https://products.aspose.com/3d/python-net/).
"""
    catalogs = load_aspose_link_catalogs()
    policy = LinkAllocationPolicyV1()

    candidate, plan = build_readme_document_candidate(
        ORG_REPO,
        source,
        facts,
        base_revision=revision,
        link_catalogs=catalogs,
        link_allocation_policy=policy,
    )
    validation = validate_readme_document_candidate(
        source,
        candidate,
        plan,
        facts,
        link_catalogs=catalogs,
    )

    _assert_contextual_compatibility_claim_block(validation, plan)
    assert plan.contextual_links is not None
    assert len(plan.contextual_links.bindings) == 2
    assert {binding.context_kind for binding in plan.contextual_links.bindings} == {"relationship"}
    assert {binding.target_url for binding in plan.contextual_links.bindings} == {
        "https://products.aspose.org/3d/python/",
        "https://products.aspose.com/3d/python-net/",
    }
    assert (
        "[full-featured Aspose.3D Enterprise Edition]"
        "(https://products.aspose.com/3d/python-net/)" in candidate
    )
    assert "Aspose.3D FOSS for Python" in candidate
    assert "FOSS for python" not in candidate
    assert "## Scope and Limitations" in candidate
    assert candidate.count("products.aspose.org") == 1
    assert candidate.count("products.aspose.com") == 1
    assert "https://kb.aspose.org/3d/python/how-to-get-started-3d-python/" not in candidate
    assert "commercial On-Premise edition" not in candidate

    rerendered, rerun_plan = build_readme_document_candidate(
        ORG_REPO,
        candidate,
        facts,
        base_revision=revision,
        link_catalogs=catalogs,
        link_allocation_policy=policy,
    )

    assert rerendered == candidate
    assert rerun_plan.contextual_links is not None
    assert rerun_plan.contextual_links.omission_reason in {"none", "budget_exhausted"}
    assert rerun_plan.operations == []


def test_configured_single_link_slot_prefers_enterprise_product_context() -> None:
    facts = _facts()
    revision = facts.selected_fact("product.identity").source.source_revision
    assert revision is not None
    policy = LinkAllocationPolicyV1.model_validate(
        {
            "mode": "configured",
            "max_total": 1,
            "domain_maxima": {"aspose.org": 1, "aspose.com": 1},
            "surface_maxima": {
                "products": 1,
                "docs": 0,
                "kb": 0,
                "blog": 0,
                "reference": 0,
            },
        }
    )
    candidate, plan = build_readme_document_candidate(
        ORG_REPO,
        "# Aspose.3D FOSS for Python\n\n## Quick start\n\nExisting guidance.\n",
        facts,
        base_revision=revision,
        link_catalogs=load_aspose_link_catalogs(),
        link_allocation_policy=policy,
    )

    assert plan.contextual_links is not None
    assert len(plan.contextual_links.bindings) == 1
    binding = plan.contextual_links.bindings[0]
    assert binding.context_kind == "relationship"
    assert binding.parent_domain == "aspose.com"
    assert candidate.count("products.aspose.com") == 1
    assert "products.aspose.org" not in candidate


def test_verified_template_binds_contextual_plan_before_compilation() -> None:
    facts = _verified_facts()
    revision = facts.selected_fact("product.identity").source.source_revision
    assert revision is not None
    catalogs = load_aspose_link_catalogs()
    source = "# Aspose.Cells FOSS for Java\n"
    candidate, plan = build_verified_template_document_candidate(
        facts,
        source,
        revision,
        _verified_plan(facts, source),
        link_catalogs=catalogs,
        link_allocation_policy=LinkAllocationPolicyV1(),
    )
    validation = validate_readme_document_candidate(
        source,
        candidate,
        plan,
        facts,
        link_catalogs=catalogs,
    )

    assert plan.contextual_links is not None
    assert validation.checks["contextual_links"] is True
    assert candidate.count("products.aspose.com") == 1
    assert candidate.count("products.aspose.org") == 1
    assert candidate.count("Enterprise Edition") == 1
    assert any(
        "readme.contextual_links" in binding.configured_standard_ids
        for binding in plan.candidate_content_provenance
    )
    assert plan.claim_accountability is not None
    contextual_candidate_claims = [
        record
        for record in plan.claim_accountability.claims
        if record.stage == "candidate"
        and "readme.contextual_links" in record.configured_standard_ids
    ]
    assert contextual_candidate_claims
    assert all(record.currently_accountable for record in contextual_candidate_claims)


@pytest.mark.parametrize("platform", ["python", "net", "java", "cpp", "typescript", "rust", "go"])
@pytest.mark.parametrize(
    "policy",
    [
        LinkAllocationPolicyV1(),
        LinkAllocationPolicyV1.model_validate(
            {
                "mode": "configured",
                "max_total": 6,
                "domain_maxima": {"aspose.org": 3, "aspose.com": 4},
                "surface_maxima": {
                    "products": 2,
                    "docs": 2,
                    "kb": 2,
                    "blog": 1,
                    "reference": 2,
                },
            }
        ),
    ],
    ids=["auto", "configured"],
)
def test_seven_real_representatives_compatibility_allocate_and_noop_under_both_modes(
    platform: str,
    policy: LinkAllocationPolicyV1,
    catalogs: AsposeLinkCatalogSetV1,
) -> None:
    root = REPRESENTATIVE_ROOT / platform
    facts = ProductFactsV2.model_validate(
        json.loads((root / "product-facts-v2.json").read_text(encoding="utf-8"))
    )
    source = (root / "original-readme.md").read_text(encoding="utf-8")
    revision = facts.selected_fact("product.identity").source.source_revision
    assert revision is not None

    candidate, plan = build_readme_document_candidate(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
        link_catalogs=catalogs,
        link_allocation_policy=policy,
    )
    validation = validate_readme_document_candidate(
        source,
        candidate,
        plan,
        facts,
        link_catalogs=catalogs,
    )

    _assert_contextual_compatibility_claim_block(validation, plan)
    assert plan.contextual_links is not None
    assert plan.contextual_links.bindings or plan.contextual_links.omission_reason != "none"

    rerendered, rerun_plan = build_readme_document_candidate(
        facts.org_repo,
        candidate,
        facts,
        base_revision=revision,
        link_catalogs=catalogs,
        link_allocation_policy=policy,
    )
    assert rerendered == candidate
    assert rerun_plan.contextual_links is not None
    assert rerun_plan.operations == []
