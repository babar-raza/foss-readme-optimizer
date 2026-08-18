"""2026-08-18: `verification/claim_disposition.py`'s corroboration logic --
the same "who verifies the verifier" answer `prose_quality.py` established.
A classification is only accepted if the model's own cited evidence
actually appears, verbatim, in the exact location it claims to have read."""

from pathlib import Path

from readme_agent.errors import LLMError
from readme_agent.llm.schema import LLMResponseMeta
from readme_agent.llm.verifier_client import FixtureForcedToolClient, ForcedToolResult
from readme_agent.verification.claim_disposition import (
    check_claim_disposition,
    corroborate_claim_disposition,
    repository_file_listing,
)

CLAIM_ID = "source:claim:100:abcdef0123456789"
CONTENT_SHA = "a" * 64


class TestCorroborateClaimDisposition:
    def test_redundant_with_a_verbatim_candidate_quote_is_corroborated(self):
        candidate_text = "## Key Capabilities\n\nSelect any symbology by name via generate()."
        result = corroborate_claim_disposition(
            CLAIM_ID,
            CONTENT_SHA,
            candidate_text,
            Path("/nonexistent"),
            {
                "classification": "redundant_with_candidate",
                "evidence_type": "candidate_section_reference",
                "evidence_ref": "Key Capabilities",
                "evidence_quote": "Select any symbology by name via generate()",
                "reasoning": "already covered",
            },
        )
        assert result.classification == "redundant_with_candidate"
        assert result.corroborated is True

    def test_redundant_with_a_hallucinated_quote_is_downgraded_to_unverifiable(self):
        """The central regress-resolving property: the LLM's own claim is
        never trusted at face value -- a quote that doesn't actually appear
        in the candidate is discarded, not acted upon."""
        candidate_text = "## Key Capabilities\n\nSomething entirely different."
        result = corroborate_claim_disposition(
            CLAIM_ID,
            CONTENT_SHA,
            candidate_text,
            Path("/nonexistent"),
            {
                "classification": "redundant_with_candidate",
                "evidence_type": "candidate_section_reference",
                "evidence_ref": "Key Capabilities",
                "evidence_quote": "text that was never actually in the candidate",
                "reasoning": "claims coverage",
            },
        )
        assert result.classification == "unverifiable"
        assert result.corroborated is False
        assert result.evidence_quote == ""

    def test_verified_against_a_real_file_with_a_verbatim_quote_is_corroborated(self, tmp_path):
        (tmp_path / "resolver.py").write_text(
            "def resolve():\n    # unset fields fall back to the symbology's own default\n"
            "    pass\n",
            encoding="utf-8",
        )
        result = corroborate_claim_disposition(
            CLAIM_ID,
            CONTENT_SHA,
            "candidate text",
            tmp_path,
            {
                "classification": "verified_against_source",
                "evidence_type": "clone_cache_path",
                "evidence_ref": "resolver.py",
                "evidence_quote": "unset fields fall back to the symbology's own default",
                "reasoning": "confirmed in resolver.py",
            },
        )
        assert result.classification == "verified_against_source"
        assert result.corroborated is True
        assert result.evidence_ref == "resolver.py"

    def test_verified_against_source_with_a_hallucinated_quote_is_downgraded(self, tmp_path):
        (tmp_path / "resolver.py").write_text("def resolve():\n    pass\n", encoding="utf-8")
        result = corroborate_claim_disposition(
            CLAIM_ID,
            CONTENT_SHA,
            "candidate text",
            tmp_path,
            {
                "classification": "verified_against_source",
                "evidence_type": "clone_cache_path",
                "evidence_ref": "resolver.py",
                "evidence_quote": "a sentence that does not exist in this file",
                "reasoning": "confirmed",
            },
        )
        assert result.classification == "unverifiable"
        assert result.corroborated is False

    def test_verified_against_source_with_a_path_escape_attempt_is_rejected(self, tmp_path):
        (tmp_path / "real.py").write_text("secret content here", encoding="utf-8")
        outside = tmp_path.parent / "outside-secret.py"
        outside.write_text("secret content here", encoding="utf-8")
        try:
            result = corroborate_claim_disposition(
                CLAIM_ID,
                CONTENT_SHA,
                "candidate text",
                tmp_path,
                {
                    "classification": "verified_against_source",
                    "evidence_type": "clone_cache_path",
                    "evidence_ref": "../outside-secret.py",
                    "evidence_quote": "secret content here",
                    "reasoning": "confirmed",
                },
            )
            assert result.classification == "unverifiable"
            assert result.corroborated is False
        finally:
            outside.unlink()

    def test_narrative_filler_is_accepted_without_evidence(self):
        result = corroborate_claim_disposition(
            CLAIM_ID,
            CONTENT_SHA,
            "candidate text",
            Path("/nonexistent"),
            {
                "classification": "narrative_filler",
                "evidence_type": "none",
                "evidence_ref": "",
                "reasoning": "pure transitional sentence introducing an example",
            },
        )
        assert result.classification == "narrative_filler"
        assert result.corroborated is True

    def test_unverifiable_classification_stays_unverifiable(self):
        result = corroborate_claim_disposition(
            CLAIM_ID,
            CONTENT_SHA,
            "candidate text",
            Path("/nonexistent"),
            {"classification": "unverifiable", "evidence_type": "none", "reasoning": "unsure"},
        )
        assert result.classification == "unverifiable"
        assert result.corroborated is False


class TestCheckClaimDisposition:
    def test_no_client_configured_stays_unverifiable(self):
        result = check_claim_disposition(
            CLAIM_ID, CONTENT_SHA, "a claim", "candidate text", Path("/nonexistent"), None
        )
        assert result.classification == "unverifiable"
        assert result.corroborated is False
        assert "no verifier client configured" in result.reasoning

    def test_a_corroborated_verdict_propagates(self):
        candidate_text = "## Key Capabilities\n\nSelect any symbology by name via generate()."
        client = FixtureForcedToolClient(
            [
                ForcedToolResult(
                    arguments={
                        "classification": "redundant_with_candidate",
                        "evidence_type": "candidate_section_reference",
                        "evidence_ref": "Key Capabilities",
                        "evidence_quote": "Select any symbology by name via generate()",
                        "reasoning": "already covered",
                    },
                    meta=LLMResponseMeta(),
                )
            ]
        )
        result = check_claim_disposition(
            CLAIM_ID,
            CONTENT_SHA,
            "Select any symbology by name via generate().",
            candidate_text,
            Path("/nonexistent"),
            client,
        )
        assert result.classification == "redundant_with_candidate"
        assert result.corroborated is True

    def test_llm_error_propagates_uncaught(self):
        """`LLMError` must never be silently mapped to accept/reject here --
        it propagates so the caller's own execution_error/repair machinery
        handles it."""

        class _RaisingClient:
            def call(self, messages, tool_schema):
                raise LLMError("gateway unreachable")

        raised = False
        try:
            check_claim_disposition(
                CLAIM_ID,
                CONTENT_SHA,
                "a claim",
                "candidate text",
                Path("/nonexistent"),
                _RaisingClient(),
            )
        except LLMError:
            raised = True
        assert raised


class TestRepositoryFileListing:
    def test_missing_directory_reports_no_clone(self):
        assert repository_file_listing(Path("/definitely/not/a/real/path")) == (
            "(no repository clone available)"
        )

    def test_lists_only_text_like_files_relative_to_root(self, tmp_path):
        (tmp_path / "module.py").write_text("pass", encoding="utf-8")
        (tmp_path / "README.md").write_text("# Title", encoding="utf-8")
        (tmp_path / "binary.so").write_bytes(b"\x00\x01")
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "config").write_text("", encoding="utf-8")

        listing = repository_file_listing(tmp_path)

        assert "module.py" in listing
        assert "README.md" in listing
        assert "binary.so" not in listing
        assert ".git" not in listing
