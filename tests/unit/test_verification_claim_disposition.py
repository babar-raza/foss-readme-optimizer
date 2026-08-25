"""2026-08-18: `verification/claim_disposition.py`'s corroboration logic --
the same "who verifies the verifier" answer `prose_quality.py` established.
A classification is only accepted if the model's own cited evidence
actually appears, verbatim, in the exact location it claims to have read."""

from pathlib import Path

from readme_agent.errors import LLMError
from readme_agent.llm.claim_disposition_prompts import CLAIM_DISPOSITION_TOOL_SCHEMA
from readme_agent.llm.schema import LLMResponseMeta
from readme_agent.llm.verifier_client import FixtureForcedToolClient, ForcedToolResult
from readme_agent.verification.claim_disposition import (
    check_claim_disposition,
    corroborate_claim_disposition,
    repository_file_listing,
)


def test_claim_disposition_schema_bounds_free_text_output() -> None:
    parameters = CLAIM_DISPOSITION_TOOL_SCHEMA["function"]["parameters"]
    properties = parameters["properties"]

    assert parameters["additionalProperties"] is False
    assert properties["evidence_ref"]["maxLength"] == 512
    assert properties["evidence_quote"]["maxLength"] == 800
    assert properties["reasoning"]["maxLength"] == 500


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

    def test_a_named_binary_fixture_is_corroborated_by_existence_alone(self, tmp_path):
        """2026-08-19: direct investigation of aspose.org's live behavior on
        note-python's Document('SimpleTable.one') claim found their
        equivalent verification (content-example-dispositions.json) cites
        exactly this evidence_type/status pair with NO quote for a real,
        existing binary test document -- a quote-inside-a-binary-file check
        is not meaningful. Safe by construction: the claim text must
        already name the exact filename (the model cannot invent a path)
        and the file must genuinely exist under the repository root."""

        (tmp_path / "testfiles").mkdir()
        (tmp_path / "testfiles" / "SimpleTable.one").write_bytes(b"\x00\x01\x02")
        result = corroborate_claim_disposition(
            CLAIM_ID,
            CONTENT_SHA,
            "candidate text",
            tmp_path,
            {
                "classification": "verified_against_source",
                "evidence_type": "clone_cache_path",
                "evidence_ref": "testfiles/SimpleTable.one",
                "evidence_quote": "",
                "reasoning": "the claim opens this real fixture document",
            },
            claim_text='doc = Document("SimpleTable.one")',
        )
        assert result.classification == "verified_against_source"
        assert result.corroborated is True
        assert result.evidence_ref == "testfiles/SimpleTable.one"

    def test_a_fixture_not_named_in_the_claim_text_is_refused(self, tmp_path):
        """The existence-only path never trusts the model's evidence_ref
        alone -- the exact filename must independently appear in the
        original claim text, or the citation is refused."""

        (tmp_path / "testfiles").mkdir()
        (tmp_path / "testfiles" / "SimpleTable.one").write_bytes(b"\x00\x01\x02")
        result = corroborate_claim_disposition(
            CLAIM_ID,
            CONTENT_SHA,
            "candidate text",
            tmp_path,
            {
                "classification": "verified_against_source",
                "evidence_type": "clone_cache_path",
                "evidence_ref": "testfiles/SimpleTable.one",
                "evidence_quote": "",
                "reasoning": "plausible-sounding but the claim never names this file",
            },
            claim_text="This example loads a sample document.",
        )
        assert result.classification == "unverifiable"
        assert result.corroborated is False

    def test_an_empty_quote_citing_a_missing_file_is_refused(self, tmp_path):
        result = corroborate_claim_disposition(
            CLAIM_ID,
            CONTENT_SHA,
            "candidate text",
            tmp_path,
            {
                "classification": "verified_against_source",
                "evidence_type": "clone_cache_path",
                "evidence_ref": "testfiles/DoesNotExist.one",
                "evidence_quote": "",
                "reasoning": "hallucinated path",
            },
            claim_text='doc = Document("DoesNotExist.one")',
        )
        assert result.classification == "unverifiable"
        assert result.corroborated is False

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

    def test_a_quote_from_the_repository_readme_itself_is_refused(self, tmp_path):
        """The README-circularity soundness hole (closed 2026-08-18): the
        source README contains every inherited claim by construction, so a
        quote 'found' there is circular, never corroborating evidence."""
        (tmp_path / "README.md").write_text(
            "The generator honors unset fields via the symbology's own default.",
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
                "evidence_ref": "README.md",
                "evidence_quote": "unset fields via the symbology's own default",
                "reasoning": "confirmed in README.md",
            },
        )
        assert result.classification == "unverifiable"
        assert result.corroborated is False

    def test_the_same_quote_in_a_real_source_file_still_corroborates(self, tmp_path):
        """The circularity refusal is scoped to READMEs only: identical
        evidence living in genuine repository source stays eligible."""
        shared_quote = "unset fields fall back to the symbology's own default"
        (tmp_path / "README.md").write_text(shared_quote, encoding="utf-8")
        (tmp_path / "resolver.py").write_text(
            f"def resolve():\n    # {shared_quote}\n    pass\n", encoding="utf-8"
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
                "evidence_quote": shared_quote,
                "reasoning": "confirmed in resolver.py",
            },
        )
        assert result.classification == "verified_against_source"
        assert result.corroborated is True

    def test_readme_named_evidence_is_refused_regardless_of_casing_or_location(self, tmp_path):
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "ReadMe.rst").write_text("a detail stated only here", encoding="utf-8")
        result = corroborate_claim_disposition(
            CLAIM_ID,
            CONTENT_SHA,
            "candidate text",
            tmp_path,
            {
                "classification": "verified_against_source",
                "evidence_type": "clone_cache_path",
                "evidence_ref": "docs/ReadMe.rst",
                "evidence_quote": "a detail stated only here",
                "reasoning": "confirmed in docs/ReadMe.rst",
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


class TestApiSurfaceMemberEvidence:
    """2026-08-19: the second aspose.org lesson -- a claim that is EDITORIAL
    PARAPHRASE of a real API member's behavior (barcode-python's `generate()`
    Key-Capabilities bullet, aspose.org's own content-dispositions.json
    unit_id u0017) is corroborated by confirming the named member is real,
    never by trusting a text quote. Safe by construction: the bare member
    name must already appear as inline code in the claim text (the model
    cannot invent a name, only confirm one the claim already names) AND
    match a real member of the supplied API-surface data, AND evidence_quote
    must stay empty -- a shape confirmation, never a text quote."""

    CLAIM_TEXT = (
        "Select any symbology by name -- canonical or alias -- through the generic "
        "`generate()` entry point."
    )

    def _verdict(self, evidence_ref: str, evidence_quote: str = "") -> dict:
        return {
            "classification": "verified_against_source",
            "evidence_type": "api_surface_member",
            "evidence_ref": evidence_ref,
            "evidence_quote": evidence_quote,
            "reasoning": "generate() is a real, public entry point",
        }

    def test_a_real_member_named_inline_in_the_claim_is_corroborated(self):
        result = corroborate_claim_disposition(
            CLAIM_ID,
            CONTENT_SHA,
            "candidate text",
            Path("/nonexistent"),
            self._verdict("generate"),
            claim_text=self.CLAIM_TEXT,
            known_api_member_names=frozenset({"generate", "encode"}),
        )
        assert result.classification == "verified_against_source"
        assert result.corroborated is True
        assert result.evidence_type == "api_surface_member"
        assert result.evidence_ref == "generate"
        assert result.evidence_quote == ""

    def test_a_member_name_not_present_in_the_claim_text_is_refused(self):
        """The model cannot cite a name the claim never actually mentions,
        even if that name is genuinely real -- it can only confirm one the
        claim already names verbatim as inline code."""
        result = corroborate_claim_disposition(
            CLAIM_ID,
            CONTENT_SHA,
            "candidate text",
            Path("/nonexistent"),
            self._verdict("encode"),
            claim_text=self.CLAIM_TEXT,
            known_api_member_names=frozenset({"generate", "encode"}),
        )
        assert result.classification == "unverifiable"
        assert result.corroborated is False

    def test_a_name_not_a_real_surface_member_is_refused(self):
        result = corroborate_claim_disposition(
            CLAIM_ID,
            CONTENT_SHA,
            "candidate text",
            Path("/nonexistent"),
            self._verdict("generate"),
            claim_text=self.CLAIM_TEXT,
            known_api_member_names=frozenset({"encode", "render"}),
        )
        assert result.classification == "unverifiable"
        assert result.corroborated is False

    def test_a_nonempty_evidence_quote_is_refused_shape_only_no_quotes(self):
        """Same discipline as the fixture-existence fix: this is a shape
        confirmation, never a text-quote match -- a quote alongside it is
        refused rather than silently accepted."""
        result = corroborate_claim_disposition(
            CLAIM_ID,
            CONTENT_SHA,
            "candidate text",
            Path("/nonexistent"),
            self._verdict("generate", "the generic generate() entry point"),
            claim_text=self.CLAIM_TEXT,
            known_api_member_names=frozenset({"generate"}),
        )
        assert result.classification == "unverifiable"
        assert result.corroborated is False

    def test_no_surface_data_supplied_is_refused_fail_closed(self):
        """`known_api_member_names=None` (every existing caller that
        predates this parameter) means this branch never corroborates --
        fail-closed, matching every other missing-input case in this
        function."""
        result = corroborate_claim_disposition(
            CLAIM_ID,
            CONTENT_SHA,
            "candidate text",
            Path("/nonexistent"),
            self._verdict("generate"),
            claim_text=self.CLAIM_TEXT,
        )
        assert result.classification == "unverifiable"
        assert result.corroborated is False

    def test_empty_surface_data_supplied_is_also_refused(self):
        result = corroborate_claim_disposition(
            CLAIM_ID,
            CONTENT_SHA,
            "candidate text",
            Path("/nonexistent"),
            self._verdict("generate"),
            claim_text=self.CLAIM_TEXT,
            known_api_member_names=frozenset(),
        )
        assert result.classification == "unverifiable"
        assert result.corroborated is False


class TestExcludedWithReasonPredicates:
    """E5 slice 1: the excluded_with_reason classification is accepted only
    when its cited machine-checkable predicate re-verifies in deterministic
    code -- the model's free-text reasoning is never load-bearing."""

    FIXTURE_CLAIM = 'doc = Document("SimpleTable.one")\nprint(doc.title)\n'

    def _verdict(self, evidence_ref: str, evidence_quote: str = "") -> dict:
        return {
            "classification": "excluded_with_reason",
            "evidence_type": "checkable_predicate",
            "evidence_ref": evidence_ref,
            "evidence_quote": evidence_quote,
            "reasoning": "checkable exclusion",
        }

    def test_unverifiable_fixture_dependency_corroborates(self, tmp_path):
        package = tmp_path / "src" / "widget"
        package.mkdir(parents=True)
        (package / "__init__.py").write_text("", encoding="utf-8")
        result = corroborate_claim_disposition(
            CLAIM_ID,
            CONTENT_SHA,
            "candidate text",
            tmp_path,
            self._verdict("unverifiable_fixture_dependency:SimpleTable.one"),
            claim_text=self.FIXTURE_CLAIM,
        )
        assert result.classification == "excluded_with_reason"
        assert result.corroborated is True
        assert result.evidence_type == "checkable_predicate"

    def test_fixture_dependency_shipping_with_package_sources_is_refused(self, tmp_path):
        package = tmp_path / "src" / "widget"
        data = package / "data"
        data.mkdir(parents=True)
        (package / "__init__.py").write_text("", encoding="utf-8")
        (data / "SimpleTable.one").write_bytes(b"\x00")
        result = corroborate_claim_disposition(
            CLAIM_ID,
            CONTENT_SHA,
            "candidate text",
            tmp_path,
            self._verdict("unverifiable_fixture_dependency:SimpleTable.one"),
            claim_text=self.FIXTURE_CLAIM,
        )
        assert result.classification == "unverifiable"
        assert result.corroborated is False

    def test_fixture_path_not_verbatim_in_the_claim_is_refused(self, tmp_path):
        result = corroborate_claim_disposition(
            CLAIM_ID,
            CONTENT_SHA,
            "candidate text",
            tmp_path,
            self._verdict("unverifiable_fixture_dependency:OtherFile.one"),
            claim_text=self.FIXTURE_CLAIM,
        )
        assert result.classification == "unverifiable"
        assert result.corroborated is False

    def test_superseded_by_verified_slot_corroborates_with_a_long_verbatim_quote(self):
        quote = "Generate every supported symbology through the verified entry point."
        candidate = f"# Widget\n\n## Key Capabilities\n\n{quote}\n"
        result = corroborate_claim_disposition(
            CLAIM_ID,
            CONTENT_SHA,
            candidate,
            Path("/nonexistent"),
            self._verdict("superseded_by_verified_slot:key-capabilities", quote),
            claim_text="an inherited capability sentence",
        )
        assert result.classification == "excluded_with_reason"
        assert result.corroborated is True

    def test_superseded_by_verified_slot_refuses_a_short_quote(self):
        quote = "short quote"
        candidate = f"# Widget\n\n{quote}\n"
        result = corroborate_claim_disposition(
            CLAIM_ID,
            CONTENT_SHA,
            candidate,
            Path("/nonexistent"),
            self._verdict("superseded_by_verified_slot:key-capabilities", quote),
            claim_text="an inherited capability sentence",
        )
        assert result.classification == "unverifiable"
        assert result.corroborated is False

    def test_superseded_by_verified_slot_refuses_a_quote_absent_from_the_candidate(self):
        quote = "Generate every supported symbology through the verified entry point."
        result = corroborate_claim_disposition(
            CLAIM_ID,
            CONTENT_SHA,
            "# Widget\n\nSomething else entirely.\n",
            Path("/nonexistent"),
            self._verdict("superseded_by_verified_slot:key-capabilities", quote),
            claim_text="an inherited capability sentence",
        )
        assert result.classification == "unverifiable"
        assert result.corroborated is False

    def test_stale_version_string_corroborates(self):
        result = corroborate_claim_disposition(
            CLAIM_ID,
            CONTENT_SHA,
            "# Widget\n\nRequires widget 2.0 or newer.\n",
            Path("/nonexistent"),
            self._verdict("stale_version_string:1.2.3"),
            claim_text="Requires widget 1.2.3 exactly.",
        )
        assert result.classification == "excluded_with_reason"
        assert result.corroborated is True

    def test_stale_version_string_still_present_in_the_candidate_is_refused(self):
        result = corroborate_claim_disposition(
            CLAIM_ID,
            CONTENT_SHA,
            "# Widget\n\nRequires widget 1.2.3 exactly.\n",
            Path("/nonexistent"),
            self._verdict("stale_version_string:1.2.3"),
            claim_text="Requires widget 1.2.3 exactly.",
        )
        assert result.classification == "unverifiable"
        assert result.corroborated is False

    def test_an_unmatched_or_malformed_predicate_fails_closed(self):
        for evidence_ref in (
            "because_i_said_so:whatever",
            "stale_version_string:",
            "unverifiable_fixture_dependency",
            "",
        ):
            result = corroborate_claim_disposition(
                CLAIM_ID,
                CONTENT_SHA,
                "candidate text",
                Path("/nonexistent"),
                self._verdict(evidence_ref, "x" * 50),
                claim_text="Requires widget 1.2.3 exactly.",
            )
            assert result.classification == "unverifiable", evidence_ref
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

    def test_lists_every_real_file_except_noise_directories(self, tmp_path):
        """2026-08-19: broadened from a source-extension allowlist to
        list-everything-except-noise after direct investigation of
        aspose.org's live behavior found their equivalent verification
        cites real, non-text fixture files (e.g. a binary test document a
        code example opens) that the old extension allowlist hid from the
        model entirely -- it could never cite what it was never shown."""

        (tmp_path / "module.py").write_text("pass", encoding="utf-8")
        (tmp_path / "README.md").write_text("# Title", encoding="utf-8")
        (tmp_path / "testfiles").mkdir()
        (tmp_path / "testfiles" / "SimpleTable.one").write_bytes(b"\x00\x01")
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "config").write_text("", encoding="utf-8")
        cache_dir = tmp_path / "__pycache__"
        cache_dir.mkdir()
        (cache_dir / "module.cpython-313.pyc").write_bytes(b"\x00\x01")

        listing = repository_file_listing(tmp_path)

        assert "module.py" in listing
        assert "README.md" in listing
        assert "testfiles/SimpleTable.one" in listing
        assert ".git" not in listing
        assert "__pycache__" not in listing
