"""Regression controls for verified README claim-accountability false approvals."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from readme_agent.facts.render_views import visitor_fact_render_view
from readme_agent.facts.schema_v2 import FactRecordV2, FactSourceV2, ProductFactsV2
from readme_agent.golden_set.review_fixtures import REVIEW_ARCHETYPES, build_review_facts
from readme_agent.presentation.verified_preservation_sections import preserved_h2_sections
from readme_agent.presentation.verified_preservation_segments import (
    CandidateEdit,
    apply_edit,
    rebase_provenance,
)
from readme_agent.presentation.verified_template_provenance import build_source_claim_resolutions
from readme_agent.presentation.verified_template_runtime import declared_preserve_ranges
from readme_agent.presentation.verified_template_sections import additional_examples_markdown
from readme_agent.readme.assessment import assess_readme_document
from readme_agent.readme.claim_accountability_candidate_policy import (
    accepted_candidate_policy_fact_ids,
    exact_candidate_policy_correction,
)
from readme_agent.readme.claim_accountability_helpers import expected_disposition
from readme_agent.readme.claim_accountability_models import ReadmeClaimAccountabilityV1
from readme_agent.readme.claim_replacement_validation import (
    replacement_candidate_claims_are_exact,
    replacement_provenance_is_exact,
)
from readme_agent.readme.document_plan import (
    CandidateContentProvenanceV1,
    SourceClaimResolutionV1,
)
from readme_agent.readme.document_structure import introduced_duplicate_headings
from readme_agent.readme.document_templates import (
    DOCUMENT_CONTRACT_IMPLEMENTATION_GLOBS,
    DOCUMENT_CONTRACT_IMPLEMENTATION_PATHS,
    document_template_hash,
)
from readme_agent.readme.example_assurance_validation import (
    unsupported_example_assurance_claims,
)
from readme_agent.readme.limitation_validation import verified_limitations_are_represented
from readme_agent.readme.source_claim_policy import SourceClaimPolicyCorrectionV1


def _facts() -> ProductFactsV2:
    return ProductFactsV2.model_validate(build_review_facts(REVIEW_ARCHETYPES[2]))


def _replace_selected_value(
    facts: ProductFactsV2,
    field: str,
    value: object,
) -> ProductFactsV2:
    selected = facts.selected_fact(field)
    replacement = selected.model_copy(update={"verification_state": "verified", "value": value})
    return facts.model_copy(
        update={
            "facts": [
                replacement if fact.fact_id == selected.fact_id else fact for fact in facts.facts
            ]
        }
    )


def _with_repository_examples(facts: ProductFactsV2, value: dict) -> ProductFactsV2:
    examples = FactRecordV2(
        fact_id="repository.examples:regression",
        field="repository.examples",
        value=value,
        source=FactSourceV2(
            source_type="mechanical_repository",
            location="repository://examples",
            source_revision="a" * 40,
        ),
        verification_state="verified",
        authoritative_owner="repository-owner",
        confidence=1.0,
        affected_surfaces=["readme"],
    )
    return facts.model_copy(
        update={
            "facts": [*facts.facts, examples],
            "selected_fact_ids": {**facts.selected_fact_ids, examples.field: examples.fact_id},
        }
    )


def _binding(candidate: str, fact_id: str) -> list[CandidateContentProvenanceV1]:
    return [
        CandidateContentProvenanceV1(
            provenance_id="template.section.additional_examples.claim",
            candidate_byte_start=0,
            candidate_byte_end=len(candidate.encode("utf-8")),
            fact_ids=[fact_id],
            rationale="Bind the exact additional-examples claim to repository evidence.",
        )
    ]


def test_barcode_keeps_every_limitation_that_names_a_public_api() -> None:
    facts = _replace_selected_value(
        _facts(),
        "product.limitations",
        [
            "PDF output is not yet implemented (to_pdf raises NotImplementedError).",
            "UPC-E requires number system digit 0 (GTIN-12 must be zero-suppressible).",
        ],
    )

    view = visitor_fact_render_view(facts, "product.limitations")

    assert view is not None
    assert view.phrases == facts.selected_fact("product.limitations").value
    candidate = "\n".join(f"- {item}" for item in view.phrases)
    assert verified_limitations_are_represented(facts, candidate) is True
    assert (
        verified_limitations_are_represented(facts, candidate.replace(view.phrases[0], "")) is False
    )


def test_limitation_view_still_rejects_internal_structured_values() -> None:
    facts = _replace_selected_value(_facts(), "product.limitations", ["internal_state_key"])

    view = visitor_fact_render_view(facts, "product.limitations")

    assert view is not None
    assert view.phrases == []


def test_public_acronym_case_does_not_break_limitation_accountability() -> None:
    facts = _replace_selected_value(
        _facts(),
        "product.limitations",
        [{"statement": "Only .pdf file targets are supported for save operations"}],
    )
    candidate = "- Only .PDF file targets are supported for save operations"

    assert verified_limitations_are_represented(facts, candidate) is True


def test_email_inventory_does_not_claim_syntax_or_api_verification() -> None:
    facts = _with_repository_examples(
        _facts(),
        {
            "execution_policy": "inventory_only",
            "files": [{"path": "examples/convert.py", "execution_verified": False}],
        },
    )

    rendered = additional_examples_markdown(facts)

    assert rendered is not None
    assert "browsing repository example files" in rendered
    assert "### Repository example files" in rendered
    assert "Inventoried at the source revision" not in rendered
    assert "| Example source | Verification |" not in rendered


def test_inventory_fact_cannot_support_a_forged_syntax_check_claim() -> None:
    facts = _with_repository_examples(
        _facts(),
        {
            "execution_policy": "inventory_only",
            "files": [{"path": "examples/convert.py", "execution_verified": False}],
        },
    )
    candidate = (
        "These additional workflows were syntax-checked and matched to the repository's static "
        "public API. They were not executed by the evidence collector."
    )
    fact_id = facts.selected_fact_ids["repository.examples"]

    unsupported = unsupported_example_assurance_claims(
        candidate,
        facts,
        _binding(candidate, fact_id),
    )

    assert unsupported


def test_verified_inline_examples_support_scoped_assurance_and_unique_headings() -> None:
    facts = _with_repository_examples(
        _facts(),
        {
            "inline_examples": [
                {
                    "title": "🚀 Quick Start",
                    "language": "python",
                    "code": "first()",
                    "static_api_verified": True,
                },
                {
                    "title": "Quick Start",
                    "language": "python",
                    "code": "second()",
                    "static_api_verified": True,
                },
            ]
        },
    )

    rendered = additional_examples_markdown(facts)

    assert rendered is not None
    assert "### Explore another repository workflow" in rendered
    assert "### Explore another repository workflow with Python" in rendered
    assert "Quick Start (" not in rendered
    assert "🚀" not in rendered
    assert introduced_duplicate_headings("", "## Quick start\n\n" + rendered) == []
    assert rendered.startswith("Expand this section to view examples for ")
    assert "| Example source | Verification |" not in rendered
    assert "Syntax and static public API checked" not in rendered
    fact_id = facts.selected_fact_ids["repository.examples"]
    assert (
        unsupported_example_assurance_claims(
            rendered,
            facts,
            _binding(rendered, fact_id),
        )
        == []
    )


def test_mixed_example_inventory_rejects_blanket_assurance_but_accepts_exact_scope() -> None:
    facts = _with_repository_examples(
        _facts(),
        {
            "inline_examples": [
                {
                    "title": "Parse a message",
                    "language": "python",
                    "code": "parse_message()",
                    "static_api_verified": True,
                }
            ],
            "files": [{"path": "examples/convert.py", "execution_verified": False}],
        },
    )
    fact_id = facts.selected_fact_ids["repository.examples"]
    blanket = "All repository examples were syntax-checked and matched to the static public API."
    scoped = (
        "The inline workflows below were syntax-checked and matched to the static public API. "
        "They were not executed by the evidence collector."
    )
    inventory = (
        "The repository example files below were inventoried at the verified source revision. "
        "They were not executed or syntax-checked by the evidence collector."
    )

    assert unsupported_example_assurance_claims(blanket, facts, _binding(blanket, fact_id))
    assert unsupported_example_assurance_claims(scoped, facts, _binding(scoped, fact_id)) == []
    assert (
        unsupported_example_assurance_claims(inventory, facts, _binding(inventory, fact_id)) == []
    )


def test_exact_additional_example_disclosure_binds_its_repository_fact() -> None:
    facts = _with_repository_examples(
        _facts(),
        {
            "inline_examples": [
                {
                    "title": "Convert a file",
                    "language": "python",
                    "code": "convert()",
                    "static_api_verified": True,
                }
            ]
        },
    )
    claim = (
        "The inline workflows below were syntax-checked and matched to the repository's static "
        "public API. They were not executed by the evidence collector."
    )
    fact_id = facts.selected_fact_ids["repository.examples"]

    assert accepted_candidate_policy_fact_ids(claim, facts, _binding(claim, fact_id)) == {fact_id}


def test_canonical_public_example_preview_binds_its_repository_fact() -> None:
    facts = _with_repository_examples(
        _facts(),
        {
            "inline_examples": [
                {
                    "title": "Convert a file",
                    "language": "python",
                    "code": "convert()",
                    "static_api_verified": True,
                }
            ]
        },
    )
    claim = "Expand this section to view examples for converting a file."
    fact_id = facts.selected_fact_ids["repository.examples"]
    binding = _binding(claim, fact_id)[0].model_copy(
        update={"configured_standard_ids": ["readme.additional_examples"]}
    )

    assert accepted_candidate_policy_fact_ids(claim, facts, [binding]) == {fact_id}
    assert accepted_candidate_policy_fact_ids(claim, facts, _binding(claim, fact_id)) == set()


def test_validated_mermaid_span_binds_its_selected_visual_facts() -> None:
    facts = _facts()
    fact_id = facts.selected_fact_ids["product.formats"]
    claim = '```mermaid\nflowchart LR\n  input_1["PDF files"] --- product\n```\n'
    bindings = [
        CandidateContentProvenanceV1(
            provenance_id="template.section.at_a_glance",
            candidate_byte_start=0,
            candidate_byte_end=len(claim.encode("utf-8")),
            fact_ids=[fact_id],
            configured_standard_ids=["readme.at_a_glance_mermaid"],
            rationale="Bind the exact validated Mermaid span to its selected format fact.",
        )
    ]

    assert accepted_candidate_policy_fact_ids(claim, facts, bindings) == {fact_id}


def test_mermaid_fact_binding_requires_both_fence_and_configured_standard() -> None:
    facts = _facts()
    fact_id = facts.selected_fact_ids["product.formats"]
    claim = '```mermaid\nflowchart LR\n  input_1["PDF files"] --- product\n```'
    binding = CandidateContentProvenanceV1(
        provenance_id="template.section.at_a_glance",
        candidate_byte_start=0,
        candidate_byte_end=len(claim.encode("utf-8")),
        fact_ids=[fact_id],
        configured_standard_ids=[],
        rationale="Exercise the fail-closed Mermaid policy boundary.",
    )

    assert accepted_candidate_policy_fact_ids(claim, facts, [binding]) == set()
    configured = binding.model_copy(
        update={"configured_standard_ids": ["readme.at_a_glance_mermaid"]}
    )
    assert accepted_candidate_policy_fact_ids("PDF files", facts, [configured]) == set()


def test_canonical_api_table_binds_only_with_api_fact_and_standard() -> None:
    facts = _facts()
    source = facts.selected_fact("product.identity").source
    api = FactRecordV2(
        fact_id="api.public_surface:canonical-table-test",
        field="api.public_surface",
        value={"modules": [{"module": "aspose.page", "exports": ["Document"]}]},
        source=source,
        verification_state="verified",
        authoritative_owner="repository-source",
        confidence=1.0,
        affected_surfaces=["readme.api_reference"],
    )
    facts = facts.model_copy(
        update={
            "facts": [*facts.facts, api],
            "selected_fact_ids": {**facts.selected_fact_ids, api.field: api.fact_id},
        }
    )
    claim = (
        "| Type | Description |\n"
        "| --- | --- |\n"
        "| `Document` | Public `Document` export provided by `aspose.page`. |\n"
    )
    binding = CandidateContentProvenanceV1(
        provenance_id=(
            "template.section.api_reference.claim:0:"
            + hashlib.sha256(claim.encode("utf-8")).hexdigest()[:16]
        ),
        candidate_byte_start=0,
        candidate_byte_end=len(claim.encode("utf-8")),
        fact_ids=[api.fact_id],
        configured_standard_ids=["readme.api_reference"],
        rationale="Bind an exact canonical API table to the selected source fact.",
    )

    assert accepted_candidate_policy_fact_ids(claim, facts, [binding]) == {api.fact_id}
    assert (
        accepted_candidate_policy_fact_ids(
            claim.replace("Public", "Fabricated benchmark for"), facts, [binding]
        )
        == set()
    )
    assert (
        accepted_candidate_policy_fact_ids(
            claim,
            facts,
            [binding.model_copy(update={"configured_standard_ids": []})],
        )
        == set()
    )


def test_contextual_policy_correction_requires_generated_fact_bound_prose() -> None:
    fact_ids = {_facts().selected_fact_ids["product.identity"]}

    assert exact_candidate_policy_correction(
        "remove_update",
        {"readme.contextual_links"},
        fact_ids,
    )
    assert not exact_candidate_policy_correction(
        "remove_update",
        {"readme.contextual_links"},
        set(),
    )
    assert not exact_candidate_policy_correction(
        "remove_update",
        {"readme.enterprise_edition_terminology"},
        fact_ids,
    )


def _replacement_resolution() -> SourceClaimResolutionV1:
    return SourceClaimResolutionV1(
        claim_id="source-claim",
        source_byte_start=0,
        source_byte_end=1,
        content_sha256=hashlib.sha256(b"x").hexdigest(),
        resolution="verified_obligation_replacement",
        obligation_id="major_capabilities",
        fact_ids=["fact-1"],
        replacement_provenance_ids=["binding-a", "binding-b"],
        evidence=["negative-control"],
        rationale="Exercise exact fact and candidate-span binding identity.",
    )


def _candidate_accountability(start: int, end: int) -> ReadmeClaimAccountabilityV1:
    return ReadmeClaimAccountabilityV1(
        claim_id="candidate-claim",
        stage="candidate",
        origin="generated",
        source_byte_start=start,
        source_byte_end=end,
        content_sha256=hashlib.sha256(b"candidate").hexdigest(),
        current_disposition="add",
        accepted_fact_ids=["fact-1"],
        expected_disposition="accepted_fact",
        currently_accountable=True,
        rationale="Exercise exact replacement accountability.",
    )


@pytest.mark.parametrize("disposition", ["rewrite", "repair", "remove_update", "replace_generic"])
def test_unresolved_correction_disposition_remains_blocking(disposition: str) -> None:
    expected, accountable, rationale = expected_disposition(
        stage="source",
        origin="inherited",
        current=disposition,  # type: ignore[arg-type]
        accepted_fact_ids=set(),
        configured_standard_ids=set(),
        survives_in_candidate=False,
    )

    assert expected == "required_correction"
    assert accountable is False
    assert "no accepted typed source-claim resolution" in rationale


def test_typed_authoritative_correction_preserves_resolved_accountability() -> None:
    resolution = SourceClaimResolutionV1(
        claim_id="source-correction",
        source_byte_start=0,
        source_byte_end=1,
        content_sha256=hashlib.sha256(b"x").hexdigest(),
        resolution="authoritative_correction",
        fact_ids=["fact-1"],
        evidence=["accepted-fact:fact-1"],
        rationale="Bind the correction to an accepted typed source-claim resolution.",
    )

    expected, accountable, rationale = expected_disposition(
        stage="source",
        origin="inherited",
        current="remove_update",
        accepted_fact_ids=set(),
        configured_standard_ids=set(),
        survives_in_candidate=False,
        source_resolution=resolution,
    )

    assert expected == "required_correction"
    assert accountable is True
    assert "accepted-fact correction" in rationale


@pytest.mark.parametrize(
    ("accepted_fact_ids", "accountable"),
    [(set(), False), ({"fact-1"}, True)],
    ids=["lineage-only-is-not-factual-approval", "independently-fact-backed"],
)
def test_presentation_policy_correction_does_not_approve_retained_claim_content(
    accepted_fact_ids: set[str],
    accountable: bool,
) -> None:
    resolution = SourceClaimResolutionV1(
        claim_id="source-policy-correction",
        source_byte_start=0,
        source_byte_end=2,
        content_sha256=hashlib.sha256(b"xy").hexdigest(),
        resolution="presentation_policy_correction",
        policy_corrections=[
            SourceClaimPolicyCorrectionV1(
                correction_id="source.policy.0-1",
                disposition="omit",
                source_byte_start=0,
                source_byte_end=1,
                source_content_sha256=hashlib.sha256(b"x").hexdigest(),
                candidate_byte_start=0,
                candidate_byte_end=0,
                candidate_content_sha256=hashlib.sha256(b"").hexdigest(),
                configured_standard_ids=["readme.no_comments"],
                operation_id="readme.verified-template.compile",
            )
        ],
        evidence=["configured-standard:readme.no_comments"],
        rationale="Remove one policy-owned comment without approving the retained claim.",
    )

    expected, actual, rationale = expected_disposition(
        stage="source",
        origin="inherited",
        current="preserve",
        accepted_fact_ids=accepted_fact_ids,
        configured_standard_ids=set(),
        survives_in_candidate=False,
        source_resolution=resolution,
    )

    assert expected == (
        "presentation_policy_correction" if accountable else "authoritative_owner_validation"
    )
    assert actual is accountable
    assert ("requires an accepted fact" in rationale) is (not accountable)


def test_complete_structural_policy_omission_is_accountable_without_a_product_fact() -> None:
    resolution = SourceClaimResolutionV1(
        claim_id="source-navigation",
        source_byte_start=0,
        source_byte_end=1,
        content_sha256=hashlib.sha256(b"x").hexdigest(),
        resolution="presentation_policy_correction",
        policy_corrections=[
            SourceClaimPolicyCorrectionV1(
                correction_id="source.policy.navigation",
                disposition="omit",
                source_byte_start=0,
                source_byte_end=1,
                source_content_sha256=hashlib.sha256(b"x").hexdigest(),
                candidate_byte_start=0,
                candidate_byte_end=0,
                candidate_content_sha256=hashlib.sha256(b"").hexdigest(),
                configured_standard_ids=["readme.navigation"],
                operation_id="readme.verified-template.compile",
            )
        ],
        evidence=["configured-standard:readme.navigation"],
        rationale="Replace the complete source navigation with the canonical generated shell.",
    )

    expected, accountable, _ = expected_disposition(
        stage="source",
        origin="inherited",
        current="preserve",
        accepted_fact_ids=set(),
        configured_standard_ids=set(),
        survives_in_candidate=False,
        source_resolution=resolution,
    )

    assert expected == "presentation_policy_correction"
    assert accountable is True


def _crossed_replacement_bindings() -> dict[str, CandidateContentProvenanceV1]:
    return {
        "binding-a": CandidateContentProvenanceV1(
            provenance_id="binding-a",
            candidate_byte_start=0,
            candidate_byte_end=5,
            fact_ids=["fact-1"],
            rationale="The correct fact on the nonoverlapping span.",
        ),
        "binding-b": CandidateContentProvenanceV1(
            provenance_id="binding-b",
            candidate_byte_start=10,
            candidate_byte_end=20,
            fact_ids=["fact-2"],
            rationale="A different fact on the overlapping span.",
        ),
    }


def test_replacement_candidate_exactness_rejects_crossed_fact_and_span_bindings() -> None:
    assert (
        replacement_candidate_claims_are_exact(
            _replacement_resolution(),
            [_candidate_accountability(10, 20)],
            _crossed_replacement_bindings(),
        )
        is False
    )


def test_replacement_candidate_exactness_accepts_same_fact_and_span_binding() -> None:
    assert (
        replacement_candidate_claims_are_exact(
            _replacement_resolution(),
            [_candidate_accountability(0, 5)],
            _crossed_replacement_bindings(),
        )
        is True
    )


def test_non_overview_replacement_rejects_an_extra_bound_accepted_fact() -> None:
    facts = _facts()
    capability_id = facts.selected_fact_ids["product.capabilities"]
    license_id = facts.selected_fact_ids["product.license"]
    resolution = SourceClaimResolutionV1(
        claim_id="source-capability",
        source_byte_start=0,
        source_byte_end=1,
        content_sha256=hashlib.sha256(b"x").hexdigest(),
        resolution="verified_obligation_replacement",
        obligation_id="major_capabilities",
        fact_ids=[capability_id, license_id],
        replacement_provenance_ids=["template.section.key_capabilities"],
        evidence=["negative-control"],
        rationale="An unrelated accepted fact cannot broaden a non-overview replacement.",
    )
    provenance = CandidateContentProvenanceV1(
        provenance_id="template.section.key_capabilities",
        candidate_byte_start=0,
        candidate_byte_end=1,
        fact_ids=[capability_id, license_id],
        rationale="Bind both facts to prove exact-source equality remains mandatory.",
    )

    assert (
        replacement_provenance_is_exact(
            resolution,
            facts,
            {provenance.provenance_id: provenance},
            exact_source_fact_ids=[capability_id],
        )
        is False
    )


def test_overview_replacement_accepts_exact_title_and_summary_facts() -> None:
    facts = _facts()
    identity_id = facts.selected_fact_ids["product.identity"]
    audience_id = facts.selected_fact_ids["product.audience"]
    formats_id = facts.selected_fact_ids["product.formats"]
    resolution = SourceClaimResolutionV1(
        claim_id="source-overview",
        source_byte_start=0,
        source_byte_end=1,
        content_sha256=hashlib.sha256(b"x").hexdigest(),
        resolution="verified_obligation_replacement",
        obligation_id="product_overview",
        fact_ids=[identity_id, audience_id, formats_id],
        replacement_provenance_ids=["template.title", "template.summary"],
        evidence=["positive-control"],
        rationale="The title and summary jointly replace the exact inherited overview claim.",
    )
    title = CandidateContentProvenanceV1(
        provenance_id="template.title",
        candidate_byte_start=0,
        candidate_byte_end=1,
        fact_ids=[identity_id],
        rationale="Bind the product identity in the title.",
    )
    summary = CandidateContentProvenanceV1(
        provenance_id="template.summary",
        candidate_byte_start=1,
        candidate_byte_end=2,
        fact_ids=[audience_id, formats_id],
        rationale="Bind the exact audience and format facts used by the summary.",
    )

    assert (
        replacement_provenance_is_exact(
            resolution,
            facts,
            {title.provenance_id: title, summary.provenance_id: summary},
            exact_source_fact_ids=[identity_id],
        )
        is True
    )


def test_contradicted_replacement_accepts_only_a_source_fact_subset() -> None:
    facts = _facts()
    capability_id = facts.selected_fact_ids["product.capabilities"]
    license_id = facts.selected_fact_ids["product.license"]
    resolution = SourceClaimResolutionV1(
        claim_id="source-capability",
        source_byte_start=0,
        source_byte_end=1,
        content_sha256=hashlib.sha256(b"x").hexdigest(),
        resolution="verified_obligation_replacement",
        obligation_id="major_capabilities",
        fact_ids=[capability_id],
        contradiction_fact_ids=[license_id],
        replacement_provenance_ids=["template.section.key_capabilities"],
        evidence=["positive-control"],
        rationale="A contradiction may remove only the disproved part of the inherited claim.",
    )
    provenance = CandidateContentProvenanceV1(
        provenance_id="template.section.key_capabilities",
        candidate_byte_start=0,
        candidate_byte_end=1,
        fact_ids=[capability_id],
        rationale="Bind the surviving accepted capability fact.",
    )

    assert (
        replacement_provenance_is_exact(
            resolution,
            facts,
            {provenance.provenance_id: provenance},
            exact_source_fact_ids=[capability_id, license_id],
            allow_contradicted_source_subset=True,
        )
        is True
    )

    broadened = resolution.model_copy(update={"fact_ids": [capability_id, license_id]})
    assert (
        replacement_provenance_is_exact(
            broadened,
            facts,
            {provenance.provenance_id: provenance},
            exact_source_fact_ids=[capability_id],
            allow_contradicted_source_subset=True,
        )
        is False
    )


def test_api_replacement_accepts_only_a_needed_fact_exact_supplement() -> None:
    facts = _facts()
    api = FactRecordV2(
        fact_id="api.public_surface:regression",
        field="api.public_surface",
        value={"classes": []},
        source=FactSourceV2(
            source_type="mechanical_repository",
            location="repository://api",
            source_revision="a" * 40,
        ),
        verification_state="verified",
        authoritative_owner="repository-owner",
        confidence=1.0,
        affected_surfaces=["readme"],
    )
    facts = facts.model_copy(
        update={
            "facts": [*facts.facts, api],
            "selected_fact_ids": {**facts.selected_fact_ids, api.field: api.fact_id},
        }
    )
    capability_id = facts.selected_fact_ids["product.capabilities"]
    resolution = SourceClaimResolutionV1(
        claim_id="source-api-overview",
        source_byte_start=0,
        source_byte_end=1,
        content_sha256=hashlib.sha256(b"x").hexdigest(),
        resolution="verified_obligation_replacement",
        obligation_id="api_public_surface",
        fact_ids=[api.fact_id, capability_id],
        replacement_provenance_ids=[
            "template.section.api_reference.claim",
            "template.section.key_capabilities.claim",
        ],
        evidence=["positive-control"],
        rationale="The API slot and one capability claim jointly replace the exact source facts.",
    )
    primary = CandidateContentProvenanceV1(
        provenance_id="template.section.api_reference.claim",
        candidate_byte_start=0,
        candidate_byte_end=1,
        fact_ids=[api.fact_id],
        rationale="Bind the API replacement.",
    )
    supplemental = CandidateContentProvenanceV1(
        provenance_id="template.section.key_capabilities.claim",
        candidate_byte_start=1,
        candidate_byte_end=2,
        fact_ids=[capability_id],
        rationale="Bind the one missing source capability fact.",
    )
    provenance = {
        primary.provenance_id: primary,
        supplemental.provenance_id: supplemental,
    }

    assert (
        replacement_provenance_is_exact(
            resolution,
            facts,
            provenance,
            exact_source_fact_ids=[api.fact_id, capability_id],
        )
        is True
    )

    unrelated = supplemental.model_copy(
        update={
            "fact_ids": [capability_id, facts.selected_fact_ids["product.license"]],
        }
    )
    assert (
        replacement_provenance_is_exact(
            resolution,
            facts,
            {**provenance, unrelated.provenance_id: unrelated},
            exact_source_fact_ids=[api.fact_id, capability_id],
        )
        is False
    )


def test_email_declared_preserve_claims_are_binding_even_without_fact_ids() -> None:
    facts = _facts()
    source = (
        "# Email library\n\n"
        "## Package Entry Points\n\n"
        "Use MapiMessage, MsgReader, MsgWriter, CFBReader, and CFBWriter.\n"
    )
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision="a" * 40,
    )
    claim = next(
        item
        for item in assessment.material_claims
        if "MapiMessage" in source.encode()[item.source_byte_start : item.source_byte_end].decode()
    )

    assert claim.disposition == "preserve"
    assert (claim.source_byte_start, claim.source_byte_end) in declared_preserve_ranges(assessment)


def test_opening_promo_correction_cannot_capture_sibling_preserve_claim() -> None:
    facts = _facts()
    source = (
        "# Widget\n\n"
        "Widget reads and writes verified document formats.\n\n"
        "> Widget is the 100% free official Aspose project. Visit "
        "https://products.aspose.org/widget and https://products.aspose.com/widget.\n"
    )
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision="a" * 40,
    )
    preserve = next(
        claim
        for claim in assessment.material_claims
        if "reads and writes"
        in source.encode()[claim.source_byte_start : claim.source_byte_end].decode()
    )
    correction = next(
        claim
        for claim in assessment.material_claims
        if "100% free" in source.encode()[claim.source_byte_start : claim.source_byte_end].decode()
    )

    ranges = declared_preserve_ranges(assessment)

    assert preserve.disposition == "preserve"
    assert correction.disposition == "remove_update"
    assert (preserve.source_byte_start, preserve.source_byte_end) in ranges
    assert (correction.source_byte_start, correction.source_byte_end) not in ranges


def test_duplicate_preserve_headings_fail_before_source_splicing() -> None:
    facts = _facts()
    source = (
        "# Email library\n\n"
        "## Package Entry Points\n\nUse MapiMessage.\n\n"
        "## Package Entry Points\n\nUse MsgReader.\n"
    )
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision="a" * 40,
    )

    with pytest.raises(ValueError, match="duplicate H2 headings"):
        preserved_h2_sections(source, assessment, set(), "# Email library\n\n## Navigation\n")


def test_malformed_preserve_coordinates_fail_before_source_splicing() -> None:
    facts = _facts()
    source = "# Email library\n\n## Package Entry Points\n\nUse MapiMessage.\n"
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision="a" * 40,
    )
    target = next(item for item in assessment.sections if item.heading == "Package Entry Points")
    malformed = assessment.model_copy(
        update={
            "sections": [
                item.model_copy(update={"source_byte_end": item.source_byte_end - 1})
                if item.section_id == target.section_id
                else item
                for item in assessment.sections
            ]
        }
    )

    with pytest.raises(ValueError, match="not an exact CommonMark H2 section"):
        preserved_h2_sections(source, malformed, set(), "# Email library\n\n## Navigation\n")


def test_emoji_decorated_preserve_heading_uses_canonical_identity() -> None:
    facts = _facts()
    source = "# Email library\n\n## ✨ Features\n\nRepository details.\n"
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision="a" * 40,
    )

    preserved_h2_sections(source, assessment, set(), "# Email library\n")


def test_preserve_h2_cannot_copy_nested_repair_h3_bytes() -> None:
    facts = _facts()
    source = (
        "# Email library\n\n"
        "## Package Entry Points\n\n"
        "Use MapiMessage, MsgReader, and MsgWriter.\n\n"
        "### Generated installation\n\n"
        "pip install unverified-package\n"
    )
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision="a" * 40,
    )
    parent = next(item for item in assessment.sections if item.heading == "Package Entry Points")
    child = next(item for item in assessment.sections if item.heading == "Generated installation")
    mixed = assessment.model_copy(
        update={
            "sections": [
                item.model_copy(update={"disposition": "preserve"})
                if item.section_id == parent.section_id
                else item.model_copy(update={"disposition": "repair"})
                if item.section_id == child.section_id
                else item
                for item in assessment.sections
            ]
        }
    )

    with pytest.raises(ValueError, match="correction-owned child sections"):
        preserved_h2_sections(source, mixed, set(), "# Email library\n\n## Navigation\n")


def test_generic_capability_slot_cannot_replace_an_unbound_source_claim() -> None:
    facts = _facts()
    source = (
        "# Widget\n\n## Features\n\nPackage entry points include Reader, Writer, and Converter.\n"
    )
    candidate = "# Widget\n\n## Key capabilities\n\n- General document processing.\n"
    capability_id = facts.selected_fact_ids["product.capabilities"]
    provenance = [
        CandidateContentProvenanceV1(
            provenance_id="template.section.key_capabilities",
            candidate_byte_start=0,
            candidate_byte_end=len(candidate.encode("utf-8")),
            fact_ids=[capability_id],
            rationale="Negative control for a generic category-level replacement.",
        )
    ]

    resolutions = build_source_claim_resolutions(source, candidate, facts, provenance)

    assert not any(item.resolution == "verified_obligation_replacement" for item in resolutions)


def test_exact_correction_range_does_not_treat_a_factual_slot_as_contradiction_proof() -> None:
    facts = _facts()
    source = (
        "# Widget\n\n## Features\n\nPackage entry points include Reader, Writer, and Converter.\n"
    )
    candidate = "# Widget\n\n## Key capabilities\n\n- General document processing.\n"
    claim = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision="a" * 40,
    ).material_claims[0]
    capability_id = facts.selected_fact_ids["product.capabilities"]
    provenance = [
        CandidateContentProvenanceV1(
            provenance_id="template.section.key_capabilities",
            candidate_byte_start=0,
            candidate_byte_end=len(candidate.encode("utf-8")),
            fact_ids=[capability_id],
            rationale="Bind the complete corrected capability slot to repository evidence.",
        )
    ]

    resolutions = build_source_claim_resolutions(
        source,
        candidate,
        facts,
        provenance,
        authoritative_correction_ranges=[(claim.source_byte_start, claim.source_byte_end)],
    )

    assert resolutions == []


def test_exact_correction_authority_rejects_wrong_replacement_fact_family() -> None:
    facts = _facts()
    source = (
        "# Widget\n\n## Features\n\nPackage entry points include Reader, Writer, and Converter.\n"
    )
    candidate = "# Widget\n\n## Key capabilities\n\n- General document processing.\n"
    claim = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision="a" * 40,
    ).material_claims[0]
    license_id = facts.selected_fact_ids["product.license"]
    provenance = [
        CandidateContentProvenanceV1(
            provenance_id="template.section.key_capabilities",
            candidate_byte_start=0,
            candidate_byte_end=len(candidate.encode("utf-8")),
            fact_ids=[license_id],
            rationale="Negative control with the wrong fact family.",
        )
    ]

    resolutions = build_source_claim_resolutions(
        source,
        candidate,
        facts,
        provenance,
        authoritative_correction_ranges=[(claim.source_byte_start, claim.source_byte_end)],
    )

    assert resolutions == []


def test_caller_supplied_correction_range_cannot_authorize_a_preserve_claim() -> None:
    facts = _facts()
    source = "# Widget\n\n## Features\n\nPackage entry points include Reader and Writer.\n"
    candidate = "# Widget\n\n## Key capabilities\n\n- General document processing.\n"
    capability_id = facts.selected_fact_ids["product.capabilities"]
    license_id = facts.selected_fact_ids["product.license"]

    def provenance(fact_id: str) -> list[CandidateContentProvenanceV1]:
        return [
            CandidateContentProvenanceV1(
                provenance_id="template.section.key_capabilities",
                candidate_byte_start=0,
                candidate_byte_end=len(candidate.encode("utf-8")),
                fact_ids=[fact_id],
                rationale="Bind the negative control span to one selected fact.",
            )
        ]

    correction_range = [(0, len(source.encode("utf-8")))]
    for fact_id in (capability_id, license_id):
        with pytest.raises(ValueError, match="partial, spoofed, or stale"):
            build_source_claim_resolutions(
                source,
                candidate,
                facts,
                provenance(fact_id),
                authoritative_correction_ranges=correction_range,
            )


def test_source_splice_rebases_generated_duplicate_text_without_rediscovery() -> None:
    candidate = "# Widget\n\n## Navigation\n\n- [License](#license)\n\n## License\n\nShared text.\n"
    generated_start = candidate.rindex("Shared text.")
    binding = CandidateContentProvenanceV1(
        provenance_id="template.section.license",
        candidate_byte_start=len(candidate[:generated_start].encode("utf-8")),
        candidate_byte_end=len(candidate[: generated_start + len("Shared text.")].encode("utf-8")),
        fact_ids=[_facts().selected_fact_ids["product.license"]],
        rationale="Bind the generated occurrence before inserting duplicate source text.",
    )
    insertion_character = candidate.index("## License")
    insertion_byte = len(candidate[:insertion_character].encode("utf-8"))
    edit = CandidateEdit(
        insertion_byte,
        insertion_byte,
        "## Maintainer context\n\nShared text.\n\n",
    )

    composed = apply_edit(candidate, edit)
    rebased = rebase_provenance([binding], edit, composed)[0]
    bound_text = composed.encode("utf-8")[
        rebased.candidate_byte_start : rebased.candidate_byte_end
    ].decode("utf-8")

    assert bound_text == "Shared text."
    assert rebased.candidate_byte_start > len(composed[: composed.index("Shared text.")].encode())


def test_claim_accountability_helper_modules_are_document_contract_inputs() -> None:
    assert {
        "src/readme_agent/readme/claim_replacement_validation.py",
        "src/readme_agent/readme/claim_accountability_candidate_policy.py",
        "src/readme_agent/readme/example_assurance_validation.py",
        "src/readme_agent/readme/limitation_validation.py",
        "src/readme_agent/presentation/verified_preservation_sections.py",
        "src/readme_agent/presentation/verified_preservation_segments.py",
        "src/readme_agent/presentation/verified_source_preservation.py",
        "src/readme_agent/presentation/verified_source_placements.py",
    }.issubset(DOCUMENT_CONTRACT_IMPLEMENTATION_PATHS)


def test_verified_claim_contract_families_are_hashed_as_document_inputs() -> None:
    assert {
        "src/readme_agent/presentation/verified_*.py",
        "src/readme_agent/readme/claim_*.py",
        "src/readme_agent/readme/source_claim_*.py",
    }.issubset(set(DOCUMENT_CONTRACT_IMPLEMENTATION_GLOBS))


@pytest.mark.parametrize(
    "relative_owner",
    (
        "src/readme_agent/presentation/verified_preservation_sections.py",
        "src/readme_agent/presentation/verified_preservation_segments.py",
        "src/readme_agent/presentation/verified_source_preservation.py",
        "src/readme_agent/presentation/verified_source_placements.py",
    ),
)
def test_each_preservation_owner_change_invalidates_document_contract_hash(
    monkeypatch,
    relative_owner: str,
) -> None:
    baseline = document_template_hash()
    project_root = Path(__file__).resolve().parents[2]
    owner = (project_root / relative_owner).resolve()
    original_read_bytes = Path.read_bytes

    def changed_owner_bytes(path: Path) -> bytes:
        content = original_read_bytes(path)
        return content + b"\ncontract-hash-control" if path.resolve() == owner else content

    monkeypatch.setattr(Path, "read_bytes", changed_owner_bytes)

    assert document_template_hash() != baseline
