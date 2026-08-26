"""Prove `_richer_fact_bound_source_capability` accepts genuinely rich, soft-wrapped
aspose.org-style source claims instead of rejecting them purely for internal line-wrap
newlines or moderate length, while its remaining safety filters (verb, discriminator,
domain, semantic-overlap) still correctly disqualify genuinely mismatched claims.

Mission recovery context: `plans/investigations/evidence/mission-recovery-2026-08-18/
s1-residue-closure-map.md` (Lane B) names six real blocked claims across barcode/font/
slides that were expected to survive this candidacy check once composition preferred
richer, already-verified source detail over a short generic phrase. Live diagnosis (this
worktree) found the six claims never even reach this function: their source bullets fail
to bind to any accepted fact upstream, in `complete_source_claim_fact_binding`
(`readme_agent.readme.source_claim_fact_binding`) -- a separate, out-of-scope gap
belonging to the API-surface-evidence lane described in
`aspose-org-lesson-2-api-surface-evidence.md`. What *is* squarely in this function's scope,
and independently real, is that every one of the six claims is a single-sentence bullet
that aspose.org's source Markdown soft-wraps across two-to-five physical lines, and each
one is longer than the previous 160-character cap once whitespace-normalized (162-473
characters). These tests reproduce that exact shape directly against this function, using
one of the six real claims' literal text (font-python's TTF/OTF/CFF/.../EOT load surface)
bound synthetically, bypassing the unrelated upstream binding gap on purpose.
"""

from __future__ import annotations

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.golden_set.review_fixtures import REVIEW_ARCHETYPES, build_review_facts
from readme_agent.presentation.verified_template_capabilities import (
    _richer_fact_bound_source_capability,
)
from readme_agent.readme.source_claim_fact_binding import CompleteSourceClaimFactBindingV1

_FONT_LOAD_SURFACE_CLAIM = (
    "- Load, auto-detect, and inspect TrueType (TTF), OpenType (OTF), CFF, Type 1, WOFF, WOFF2,\n"
    "  and EOT fonts from a file path, raw bytes, or a stream with `FontLoader.open()`/\n"
    "  `FontLoader.load()` — magic-byte detection picks the format automatically unless you\n"
    "  pass `font_type` explicitly.\n"
)


def _facts_with_capability(phrase: str) -> ProductFactsV2:
    facts = ProductFactsV2.model_validate(build_review_facts(REVIEW_ARCHETYPES[2]))
    capability = facts.selected_fact("product.capabilities")
    return facts.model_copy(
        update={
            "facts": [
                fact.model_copy(update={"value": [phrase]})
                if fact.fact_id == capability.fact_id
                else fact
                for fact in facts.facts
            ]
        }
    )


def _bound(fact_id: str) -> CompleteSourceClaimFactBindingV1:
    return CompleteSourceClaimFactBindingV1(fact_ids=frozenset({fact_id}), fact_coordinates=())


def test_soft_wrapped_richer_claim_survives_instead_of_rejected_for_internal_newlines() -> None:
    facts = _facts_with_capability("Font format loading")
    capability_fact_id = facts.selected_fact_ids["product.capabilities"]
    source_bindings = [(_FONT_LOAD_SURFACE_CLAIM, _bound(capability_fact_id))]

    result = _richer_fact_bound_source_capability(source_bindings, "Font format loading", facts)

    assert result is not None
    public_claim, fact_ids, _coordinates = result
    assert "\n" not in public_claim
    assert len(public_claim) > 160
    assert "magic-byte detection" in public_claim
    assert capability_fact_id in fact_ids


def test_claim_over_the_previous_160_character_cap_no_longer_disqualified_alone() -> None:
    facts = _facts_with_capability("Font format loading")
    capability_fact_id = facts.selected_fact_ids["product.capabilities"]
    single_line_claim = " ".join(_FONT_LOAD_SURFACE_CLAIM.strip().split())
    assert len(single_line_claim.removeprefix("- ")) > 160
    source_bindings = [(single_line_claim, _bound(capability_fact_id))]

    result = _richer_fact_bound_source_capability(source_bindings, "Font format loading", facts)

    assert result is not None


def test_claim_far_past_the_new_cap_still_disqualified() -> None:
    facts = _facts_with_capability("Font format loading")
    capability_fact_id = facts.selected_fact_ids["product.capabilities"]
    runaway_claim = "- Load fonts from " + ("many supported formats, " * 40) + "and containers."
    assert len(runaway_claim) > 480
    source_bindings = [(runaway_claim, _bound(capability_fact_id))]

    result = _richer_fact_bound_source_capability(source_bindings, "Font format loading", facts)

    assert result is None


def test_genuine_multi_paragraph_source_block_still_disqualified() -> None:
    """A blank line marks a real block boundary (e.g. two bullets or a fenced code block
    glued together by the source parser) and must stay disqualifying -- only single-paragraph
    soft-wrap should be tolerated."""

    facts = _facts_with_capability("Font format loading")
    capability_fact_id = facts.selected_fact_ids["product.capabilities"]
    two_paragraph_claim = (
        "- Load fonts from TrueType and OpenType files with `FontLoader.open()`.\n"
        "\n"
        "  This is a second, unrelated paragraph glued to the same claim by the parser.\n"
    )
    source_bindings = [(two_paragraph_claim, _bound(capability_fact_id))]

    result = _richer_fact_bound_source_capability(source_bindings, "Font format loading", facts)

    assert result is None


def test_leading_verb_not_in_the_approved_list_still_disqualified() -> None:
    """A leading word outside the approved public capability action verbs stays
    disqualified -- the accept-list is a genuine, untouched safety filter.

    This originally used barcode-python's real blocked claim, which starts with
    "Select". `_ACTION_VERBS` was later widened deliberately (0965b8269) because a
    legitimate imperative verb missing from an accept-list rejects a correct
    heading, and "Select any symbology by name" is verb-first and idiomatic, so
    "select" is now approved. The property under test is unchanged; it needs a
    word that is genuinely not an imperative technical action, and vague framing
    verbs like "Leverage" are exactly what the filter exists to reject."""

    facts = _facts_with_capability("Symbology dispatch by name")
    capability_fact_id = facts.selected_fact_ids["product.capabilities"]
    claim = (
        "Leverage any symbology by name through the shared dispatch entry point "
        "for every symbology."
    )
    source_bindings = [(claim, _bound(capability_fact_id))]

    result = _richer_fact_bound_source_capability(
        source_bindings, "Symbology dispatch by name", facts
    )

    assert result is None


def test_discriminator_mismatch_still_disqualified() -> None:
    facts = _facts_with_capability("Render pages as PNG images")
    capability_fact_id = facts.selected_fact_ids["product.capabilities"]
    claim = "Render pages as SVG images through the public RenderOptions rendering API."
    source_bindings = [(claim, _bound(capability_fact_id))]

    result = _richer_fact_bound_source_capability(
        source_bindings, "Render pages as PNG images", facts
    )

    assert result is None


def test_domain_mismatch_still_disqualified() -> None:
    facts = _facts_with_capability("Manage document digital signatures for approval workflows")
    capability_fact_id = facts.selected_fact_ids["product.capabilities"]
    claim = "Manage document annotations for approval workflows through the public API."
    source_bindings = [(claim, _bound(capability_fact_id))]

    result = _richer_fact_bound_source_capability(
        source_bindings,
        "Manage document digital signatures for approval workflows",
        facts,
    )

    assert result is None
