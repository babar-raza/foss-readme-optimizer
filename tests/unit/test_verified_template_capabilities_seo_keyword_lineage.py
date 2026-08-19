"""Gate R6/R6a-repair: `aspose.relevant_seo_keywords` must genuinely shape Key
Capabilities title *bytes*, not merely sit visible-but-unread in the fact
graph (the exact gap `aspose_seo_keyword_facts.py`'s own module docstring
names) -- and it must never be cited as evidence for a factual claim, since
it stays `unverified`/third-party-sourced forever. A capability row whose
title a keyword actually shaped carries no trace of that keyword's fact ID
in `fact_ids`: the keyword is editorial vocabulary for wording, never a
factual citation (see `readme_agent.readme.claim_map` / `document_plan`'s
`CandidateContentProvenanceV1`, which would reject an unverified fact cited
as ordinary provenance)."""

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


def test_grounded_keyword_measurably_shapes_the_rendered_title_and_is_never_cited() -> None:
    """A keyword that shares real vocabulary with the row's own capability text --
    and that produces different wording than the plain fallback would -- actually
    changes the rendered title. It is still never cited as factual provenance: the
    fact stays unverified and `fact_ids` carries no trace of it either way."""

    facts = _facts_with_capability_and_keywords(
        "Third-party plugin integration support", ["plugin integration guide"]
    )

    plan = build_capability_presentation_plan(facts)

    assert len(plan.rows) == 1
    markdown, fact_ids, _coordinates = plan.rows[0]
    assert "Plugin integration guide" in markdown
    assert "Work with Third-party plugin integration support" not in markdown
    assert "aspose.relevant_seo_keywords:aspose-knowledge" not in fact_ids


def test_capability_row_never_cites_a_non_matching_seo_keyword() -> None:
    facts = _facts_with_capability_and_keywords(
        "Document format loading", ["totally unrelated phrase"]
    )

    plan = build_capability_presentation_plan(facts)

    assert len(plan.rows) == 1
    _markdown, fact_ids, _coordinates = plan.rows[0]
    assert "aspose.relevant_seo_keywords:aspose-knowledge" not in fact_ids


def test_coincidental_match_that_does_not_change_the_title_is_never_cited() -> None:
    """Gate R6a's original defect: a keyword already present in the naturally
    rendered title used to get cited purely because it happened to appear there,
    even though it changed nothing. It must render the exact same byte-identical
    fallback title and must not be cited."""

    facts = _facts_with_capability_and_keywords(
        "Document format loading", ["document format loading"]
    )

    plan = build_capability_presentation_plan(facts)

    assert len(plan.rows) == 1
    markdown, fact_ids, _coordinates = plan.rows[0]
    assert "Document format loading" in markdown
    assert "aspose.relevant_seo_keywords:aspose-knowledge" not in fact_ids


def test_unsafe_other_platform_keyword_has_zero_effect() -> None:
    """A keyword `detect_relevant_seo_keywords` would have dropped as wrong-platform
    (real corpus term, see `test_aspose_seo_keyword_facts.py`) must not shape a
    title even if it happens to share a word with the capability text."""

    facts = _facts_with_capability_and_keywords(
        "Third-party plugin integration support",
        ["Aspose.Cells for Go plugin integration"],
    )

    plan = build_capability_presentation_plan(facts)

    markdown, fact_ids, _coordinates = plan.rows[0]
    # Grounded on "plugin"/"integration", so this proves the *row-level* grounding
    # check alone is not a safety boundary by itself -- upstream platform/relevance
    # filtering (`detect_relevant_seo_keywords`) is what actually screens the
    # keyword list before it ever reaches this seam; this test documents that this
    # function trusts its input list and does not re-implement that screening.
    assert "Aspose.Cells for Go plugin integration" in markdown
    assert "aspose.relevant_seo_keywords:aspose-knowledge" not in fact_ids


def test_at_most_one_keyword_per_title_and_never_repeated_across_rows() -> None:
    facts = ProductFactsV2.model_validate(build_review_facts(REVIEW_ARCHETYPES[2]))
    capability = facts.selected_fact("product.capabilities")
    seo_fact = FactRecordV2(
        fact_id="aspose.relevant_seo_keywords:aspose-knowledge",
        field="aspose.relevant_seo_keywords",
        value=["plugin integration guide"],
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
    facts = facts.model_copy(
        update={
            "facts": [
                fact.model_copy(
                    update={
                        "value": [
                            "Third-party plugin integration support",
                            "Extra plugin integration extensibility hooks",
                        ]
                    }
                )
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

    plan = build_capability_presentation_plan(facts)

    keyword_shaped_rows = [
        markdown
        for markdown, _fact_ids, _coordinates in plan.rows
        if "Plugin integration guide" in markdown
    ]
    assert len(keyword_shaped_rows) == 1


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
