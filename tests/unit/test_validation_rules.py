from pathlib import Path

from readme_agent.llm.schema import LLMBlockResponse, LLMClaims
from readme_agent.readme.gap_detector import GapReport
from readme_agent.readme.markers import upsert_span
from readme_agent.registry.loader import load_policy
from readme_agent.validation import registry
from readme_agent.validation.context import ValidationContext
from readme_agent.validation.rules import (
    change_boundary,
    commercial_mention_discipline,
    idempotency,
    link_whitelist,
    product_first_opening,
    prohibited_terms,
    prominence,
    referential_integrity,
    talking_points,
    word_count,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINE = "# Aspose.Example FOSS for Java\n\nAn intro paragraph.\n\n## Features\n\n- one\n"


def _policy():
    return load_policy("aspose-3d-foss", REPO_ROOT / "config" / "policies")


def _valid_llm_response(paragraph=None):
    return LLMBlockResponse(
        relationship_paragraph=paragraph
        or (
            "This repository is the free, open-source FOSS edition of the "
            "corresponding commercial Aspose product. Upgrade to the "
            "commercial edition when you need a broader feature set, "
            "additional format support, or dedicated commercial support."
        ),
        talking_points_covered=["open_source_scope", "commercial_upgrade_path"],
        claims=LLMClaims(
            license_name="MIT",
            commercial_link_url=_policy().required_elements.products_com_link.url,
        ),
    )


def _base_ctx(**overrides) -> ValidationContext:
    defaults = dict(
        readme_text=BASELINE,
        baseline_readme_text=BASELINE,
        policy=_policy(),
        pre_render_gap_report=GapReport(
            license_mentioned=True,
            products_org_link=False,
            products_com_link=True,
            relationship_explained=False,
        ),
        rendered_spans={},
        llm_response=None,
        facts_hash="factshash",
        embedded_hash=None,
        detected_license="MIT",
    )
    defaults.update(overrides)
    return ValidationContext(**defaults)


class TestWordCount:
    def test_passes_within_range(self):
        ctx = _base_ctx(llm_response=_valid_llm_response())
        assert word_count.check(ctx).passed

    def test_fails_too_short(self):
        ctx = _base_ctx(llm_response=_valid_llm_response(paragraph="Too short."))
        assert not word_count.check(ctx).passed

    def test_fails_too_long(self):
        ctx = _base_ctx(llm_response=_valid_llm_response(paragraph="word " * 200))
        assert not word_count.check(ctx).passed

    def test_passes_trivially_with_no_llm_response(self):
        assert word_count.check(_base_ctx()).passed


class TestProhibitedTerms:
    def test_passes_clean_content(self):
        ctx = _base_ctx(rendered_spans={"resources": "Everything here is fine."})
        assert prohibited_terms.check(ctx).passed

    def test_fails_on_prohibited_phrase(self):
        ctx = _base_ctx(rendered_spans={"resources": "We guarantee 100% satisfaction."})
        result = prohibited_terms.check(ctx)
        assert not result.passed
        assert "guarantee" in result.message


class TestLinkWhitelist:
    def test_passes_whitelisted_domain(self):
        ctx = _base_ctx(
            rendered_spans={"resources": "[link](https://products.aspose.com/3d/java/)"}
        )
        assert link_whitelist.check(ctx).passed

    def test_fails_off_whitelist_domain(self):
        ctx = _base_ctx(rendered_spans={"resources": "[link](https://evil.example.com/phish)"})
        result = link_whitelist.check(ctx)
        assert not result.passed
        assert "evil.example.com" in result.message


class TestChangeBoundary:
    def test_passes_when_only_spans_changed(self):
        with_span = upsert_span(BASELINE, "resources", "resources content", "aaa111")
        ctx = _base_ctx(readme_text=with_span)
        assert change_boundary.check(ctx).passed

    def test_fails_when_content_outside_spans_also_changed(self):
        with_span = upsert_span(BASELINE, "resources", "resources content", "aaa111")
        tampered = with_span.replace("An intro paragraph.", "A DIFFERENT intro paragraph.")
        ctx = _base_ctx(readme_text=tampered)
        assert not change_boundary.check(ctx).passed


class TestTalkingPoints:
    def test_passes_when_claims_match_prose(self):
        ctx = _base_ctx(llm_response=_valid_llm_response())
        assert talking_points.check(ctx).passed

    def test_fails_when_llm_claims_a_point_not_in_prose(self):
        response = LLMBlockResponse(
            relationship_paragraph="This is a nice open-source project.",
            talking_points_covered=["open_source_scope", "commercial_upgrade_path"],
            claims=LLMClaims(),
        )
        ctx = _base_ctx(llm_response=response)
        result = talking_points.check(ctx)
        assert not result.passed
        assert "commercial_upgrade_path" in result.message

    def test_fails_when_required_point_not_claimed_at_all(self):
        response = LLMBlockResponse(
            relationship_paragraph="This is open-source and has a commercial upgrade.",
            talking_points_covered=["open_source_scope"],
            claims=LLMClaims(),
        )
        ctx = _base_ctx(llm_response=response)
        assert not talking_points.check(ctx).passed

    def test_passes_trivially_with_no_llm_response(self):
        assert talking_points.check(_base_ctx()).passed


class TestReferentialIntegrity:
    def test_passes_when_claims_match_ground_truth(self):
        ctx = _base_ctx(llm_response=_valid_llm_response())
        assert referential_integrity.check(ctx).passed

    def test_fails_when_claimed_license_does_not_match_detected(self):
        response = LLMBlockResponse(
            relationship_paragraph="Some prose here that is long enough to pass word count checks.",
            talking_points_covered=[],
            claims=LLMClaims(license_name="Apache-2.0"),
        )
        ctx = _base_ctx(llm_response=response, detected_license="MIT")
        result = referential_integrity.check(ctx)
        assert not result.passed
        assert "Apache-2.0" in result.message

    def test_fails_when_claimed_commercial_link_is_not_the_policy_url(self):
        response = LLMBlockResponse(
            relationship_paragraph="Some prose here that is long enough to pass word count checks.",
            talking_points_covered=[],
            claims=LLMClaims(commercial_link_url="https://example.com/not-the-real-one"),
        )
        ctx = _base_ctx(llm_response=response)
        assert not referential_integrity.check(ctx).passed


class TestIdempotency:
    def test_passes_when_no_existing_span(self):
        assert idempotency.check(_base_ctx(embedded_hash=None)).passed

    def test_passes_when_hashes_match(self):
        ctx = _base_ctx(facts_hash="samehash", embedded_hash="samehash")
        assert idempotency.check(ctx).passed

    def test_fails_when_hashes_differ(self):
        ctx = _base_ctx(facts_hash="new", embedded_hash="old")
        assert not idempotency.check(ctx).passed


class TestProminence:
    def test_passes_when_present_link_is_near_the_top(self):
        text = "# Title\n\nSee https://products.aspose.com/3d/java/ right here.\n"
        report = GapReport(True, False, True, True)
        ctx = _base_ctx(readme_text=text, pre_render_gap_report=report)
        assert prominence.check(ctx).passed

    def test_warns_when_present_link_is_buried(self):
        filler = "\n".join(f"paragraph {i} " * 20 for i in range(200))
        text = f"# Title\n\n{filler}\n\nhttps://products.aspose.com/3d/java/\n"
        report = GapReport(True, False, True, True)
        ctx = _base_ctx(readme_text=text, pre_render_gap_report=report)
        result = prominence.check(ctx)
        assert not result.passed
        assert result.severity == "WARNING"


class TestRegistryAggregation:
    def test_prominence_warning_does_not_fail_overall_registry(self):
        # Opening explains the product (satisfies product_first_opening)
        # *before* the buried link further down (still fails prominence,
        # which is what this test is actually about) -- isolates the one
        # WARNING this test targets from the two new Phase 21 ERROR gates.
        opening = "Title is a Java library for creating, reading, and modifying files.\n\n"
        filler = "\n".join(f"paragraph {i} " * 20 for i in range(200))
        text = f"# Title\n\n{opening}{filler}\n\nhttps://products.aspose.com/3d/java/\n"
        report = GapReport(True, False, True, True)
        ctx = _base_ctx(readme_text=text, baseline_readme_text=text, pre_render_gap_report=report)

        results = registry.run_all(ctx)
        prominence_result = next(r for r in results if r.rule_name == "prominence")
        assert prominence_result.severity == "WARNING"
        assert not prominence_result.passed
        assert registry.passed(results)  # a WARNING alone must not fail the overall gate

    def test_a_hard_error_fails_the_overall_registry(self):
        ctx = _base_ctx(rendered_spans={"resources": "We guarantee everything."})
        results = registry.run_all(ctx)
        assert not registry.passed(results)


# Phase 21 (decision #9 as corrected). Both new rules check ctx.readme_text --
# the *final* document -- not ctx.rendered_spans, so they fire on pre-existing
# content too, not just what this run rendered.

_GOOD_OPENING = (
    "# Example FOSS\n\n"
    "Example FOSS is a Java library for creating, reading, and modifying "
    "spreadsheet files.\n\n"
    "See the commercial edition at https://products.example.com/cells/java/ "
    "for more features.\n"
)
_PROMO_BEFORE_EXPLANATION = (
    "# Example FOSS\n\n"
    "Get the commercial edition at https://products.example.com/cells/java/ today!\n\n"
    "Example FOSS is a Java library for creating, reading, and modifying "
    "spreadsheet files.\n"
)
_NO_EXPLANATION_AT_ALL = "# Example FOSS\n\nGet it at https://products.example.com/cells/java/.\n"
_NO_COMMERCIAL_LINK = (
    "# Example FOSS\n\nExample FOSS is a Java library for creating, reading, "
    "and modifying spreadsheet files.\n"
)


class TestProductFirstOpening:
    def test_passes_when_product_explained_before_commercial_link(self):
        ctx = _base_ctx(readme_text=_GOOD_OPENING)
        assert product_first_opening.check(ctx).passed

    def test_passes_trivially_with_no_commercial_link(self):
        ctx = _base_ctx(readme_text=_NO_COMMERCIAL_LINK)
        assert product_first_opening.check(ctx).passed

    def test_fails_when_commercial_link_precedes_explanation(self):
        ctx = _base_ctx(readme_text=_PROMO_BEFORE_EXPLANATION)
        result = product_first_opening.check(ctx)
        assert not result.passed
        assert result.severity == "ERROR"

    def test_fails_when_commercial_link_present_but_no_explanation_found(self):
        ctx = _base_ctx(readme_text=_NO_EXPLANATION_AT_ALL)
        assert not product_first_opening.check(ctx).passed


_NATURAL_SINGLE_MENTION = (
    "# Example FOSS\n\n"
    "Example FOSS is a Java library for creating, reading, and modifying spreadsheet "
    "files. It is API-compatible with [Example for Java]"
    "(https://products.example.com/cells/java/), the commercial edition with a "
    "broader feature set.\n"
)
# Real evidence this shape is modeled on: aspose-3d-foss/...Java's bot-authored
# Resources section (see docs/presentation-standard.md dimension 10).
_LINK_FARM = (
    "# Example FOSS\n\n"
    "Example FOSS is a Java library for creating, reading, and modifying "
    "spreadsheet files.\n\n"
    "## Resources\n\n"
    "- [Example for Java](https://products.example.com/cells/java/) -- commercial edition\n"
    "- [Example family](https://products.example.com/cells/) -- overview\n"
)
_PROMOTIONAL_LANGUAGE = (
    "# Example FOSS\n\n"
    "Example FOSS is a Java library for creating, reading, and modifying spreadsheet "
    "files. Buy now the world-class commercial edition at "
    "https://products.example.com/cells/java/!\n"
)


class TestCommercialMentionDiscipline:
    def test_passes_a_single_natural_mention(self):
        ctx = _base_ctx(readme_text=_NATURAL_SINGLE_MENTION)
        assert commercial_mention_discipline.check(ctx).passed

    def test_passes_trivially_with_no_commercial_link(self):
        ctx = _base_ctx(readme_text=_NO_COMMERCIAL_LINK)
        assert commercial_mention_discipline.check(ctx).passed

    def test_fails_on_a_link_farm_pattern(self):
        ctx = _base_ctx(readme_text=_LINK_FARM)
        result = commercial_mention_discipline.check(ctx)
        assert not result.passed
        assert "list item" in result.message

    def test_fails_on_promotional_language(self):
        ctx = _base_ctx(readme_text=_PROMOTIONAL_LANGUAGE)
        result = commercial_mention_discipline.check(ctx)
        assert not result.passed
        assert "promotional" in result.message
