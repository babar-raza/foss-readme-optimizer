"""Wave 8.6 (`VER-006` reversal): `verification/prose_quality.py`'s
corroboration logic -- the structural answer to "who verifies the
verifier." A flagged finding only becomes actionable if the LLM's own
quoted span actually appears, verbatim, in the text it was shown."""

from readme_agent.errors import LLMError
from readme_agent.llm.schema import LLMResponseMeta
from readme_agent.llm.verifier_client import FixtureForcedToolClient, ForcedToolResult
from readme_agent.readme.markers import render_span
from readme_agent.verification.prose_quality import check_prose_quality, corroborate_prose_finding


class TestCorroborateProseFinding:
    def test_not_flagged_is_never_corroborated(self):
        result = corroborate_prose_finding(
            "some paragraph text", {"flagged": False, "reason": "fine"}
        )
        assert result["flagged"] is False
        assert result["corroborated"] is False

    def test_flagged_with_a_verbatim_quoted_span_is_corroborated(self):
        span_text = "This is a generic, mechanically-inserted paragraph."
        result = corroborate_prose_finding(
            span_text,
            {
                "flagged": True,
                "quoted_span": "mechanically-inserted paragraph",
                "reason": "generic phrasing",
            },
        )
        assert result["flagged"] is True
        assert result["corroborated"] is True

    def test_flagged_with_a_hallucinated_quoted_span_is_discarded(self):
        """The central regress-resolving property: the LLM's own claim is
        never trusted at face value -- a quote that doesn't actually appear
        in the reviewed text is discarded, not acted upon."""
        span_text = "This is a perfectly reasonable, specific paragraph about the product."
        result = corroborate_prose_finding(
            span_text,
            {
                "flagged": True,
                "quoted_span": "text that was never actually in the paragraph",
                "reason": "claims genericness",
            },
        )
        assert result["flagged"] is True
        assert result["corroborated"] is False

    def test_flagged_with_an_empty_quoted_span_is_never_corroborated(self):
        result = corroborate_prose_finding(
            "some text", {"flagged": True, "quoted_span": "", "reason": "vague"}
        )
        assert result["corroborated"] is False


class TestCheckProseQuality:
    def test_no_client_configured_never_flags(self):
        final_text = "# Title\n\n" + render_span("resources", "Some paragraph.", "abc123")
        result = check_prose_quality(final_text, None)
        assert result["flagged"] is False
        assert result["corroborated"] is False

    def test_no_resources_span_never_flags(self):
        result = check_prose_quality(
            "# Title\n\nJust a plain README with no owned span.",
            FixtureForcedToolClient([]),
        )
        assert result["flagged"] is False

    def test_a_flagged_and_corroborated_finding_propagates(self):
        paragraph = "This is boilerplate generic filler text about the product."
        final_text = "# Title\n\n" + render_span("resources", paragraph, "abc123")
        client = FixtureForcedToolClient(
            [
                ForcedToolResult(
                    arguments={
                        "flagged": True,
                        "quoted_span": "boilerplate generic filler text",
                        "reason": "reads as generic filler",
                    },
                    meta=LLMResponseMeta(),
                )
            ]
        )
        result = check_prose_quality(final_text, client)
        assert result["flagged"] is True
        assert result["corroborated"] is True

    def test_llm_error_propagates_uncaught(self):
        """`LLMError` must never be silently mapped to accept/reject here --
        it propagates so the caller's own execution_error/repair machinery
        handles it."""

        class _RaisingClient:
            def call(self, messages, tool_schema):
                raise LLMError("gateway unreachable")

        final_text = "# Title\n\n" + render_span("resources", "Some paragraph.", "abc123")
        try:
            check_prose_quality(final_text, _RaisingClient())
            raised = False
        except LLMError:
            raised = True
        assert raised
