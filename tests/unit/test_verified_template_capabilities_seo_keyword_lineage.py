"""Gate R6: `aspose.relevant_seo_keywords` must genuinely influence Key
Capabilities output lineage, not merely sit visible-but-unread in the fact
graph (the exact gap `aspose_seo_keyword_facts.py`'s own module docstring
names). A capability row whose SEO title names one of this product's own
relevance-filtered keywords must cite that keyword fact in its `fact_ids` --
real lineage, never fabricated content (the keyword list only ever
attributes an already-verified row, never invents one)."""

from __future__ import annotations

from readme_agent.facts.schema_v2 import FactRecordV2, FactSourceV2, ProductFactsV2
from readme_agent.golden_set.review_fixtures import REVIEW_ARCHETYPES, build_review_facts
from readme_agent.presentation.verified_template_capabilities import (
    build_capability_presentation_plan,
)


def _facts_with_capability_and_keywords(phrase: str, keywords: list[str]) -> ProductFactsV2:
    facts = ProductFactsV2.model_validate(build_review_facts(REVIEW_ARCHETYPES[2]))
    capability = facts.selected_fact("product.capabilities")
    seo_fact = FactRecordV2(
        fact_id="aspose.relevant_seo_keywords:aspose-knowledge",
        field="aspose.relevant_seo_keywords",
        value=keywords,
        source=FactSourceV2(
            source_type="approved_documentation",
            location="data/imported:golden/python",
            retrieved_at="2026-08-19",
        ),
        verification_state="unverified",
        authoritative_owner="aspose.org",
        confidence=0.6,
        affected_surfaces=["metadata.topics", "readme.opening"],
    )
    return facts.model_copy(
        update={
            "facts": [
                fact.model_copy(update={"value": [phrase]})
                if fact.fact_id == capability.fact_id
                else fact
                for fact in facts.facts
            ]
            + [seo_fact],
            "selected_fact_ids": {
                **facts.selected_fact_ids,
                "aspose.relevant_seo_keywords": seo_fact.fact_id,
            },
        }
    )


def test_capability_row_cites_matching_seo_keyword_fact() -> None:
    facts = _facts_with_capability_and_keywords(
        "Document format loading", ["document format loading"]
    )

    plan = build_capability_presentation_plan(facts)

    assert len(plan.rows) == 1
    markdown, fact_ids, _coordinates = plan.rows[0]
    assert "Document format loading" in markdown
    assert "aspose.relevant_seo_keywords:aspose-knowledge" in fact_ids


def test_capability_row_never_cites_a_non_matching_seo_keyword() -> None:
    facts = _facts_with_capability_and_keywords(
        "Document format loading", ["totally unrelated phrase"]
    )

    plan = build_capability_presentation_plan(facts)

    assert len(plan.rows) == 1
    _markdown, fact_ids, _coordinates = plan.rows[0]
    assert "aspose.relevant_seo_keywords:aspose-knowledge" not in fact_ids


def test_capability_row_generation_is_unaffected_when_no_seo_keywords_exist() -> None:
    """No aspose.relevant_seo_keywords fact at all (the common case for most
    repositories) -- generation must proceed exactly as before, never error."""

    facts = ProductFactsV2.model_validate(build_review_facts(REVIEW_ARCHETYPES[2]))
    capability = facts.selected_fact("product.capabilities")
    facts = facts.model_copy(
        update={
            "facts": [
                fact.model_copy(update={"value": ["Document format loading"]})
                if fact.fact_id == capability.fact_id
                else fact
                for fact in facts.facts
            ]
        }
    )

    plan = build_capability_presentation_plan(facts)

    assert len(plan.rows) == 1
    markdown, fact_ids, _coordinates = plan.rows[0]
    assert "Document format loading" in markdown
    assert all("aspose.relevant_seo_keywords" not in fact_id for fact_id in fact_ids)
