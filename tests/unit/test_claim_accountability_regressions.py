"""Regression controls for verified README claim-accountability false approvals."""

from __future__ import annotations

import hashlib

from readme_agent.facts.render_views import visitor_fact_render_view
from readme_agent.facts.schema_v2 import FactRecordV2, FactSourceV2, ProductFactsV2
from readme_agent.golden_set.review_fixtures import REVIEW_ARCHETYPES, build_review_facts
from readme_agent.presentation.verified_template_provenance import build_source_claim_resolutions
from readme_agent.presentation.verified_template_runtime import declared_preserve_ranges
from readme_agent.presentation.verified_template_sections import additional_examples_markdown
from readme_agent.readme.assessment import assess_readme_document
from readme_agent.readme.claim_accountability_models import ReadmeClaimAccountabilityV1
from readme_agent.readme.claim_replacement_validation import (
    replacement_candidate_claims_are_exact,
)
from readme_agent.readme.document_plan import (
    CandidateContentProvenanceV1,
    SourceClaimResolutionV1,
)
from readme_agent.readme.document_structure import introduced_duplicate_headings
from readme_agent.readme.document_templates import DOCUMENT_CONTRACT_IMPLEMENTATION_PATHS
from readme_agent.readme.example_assurance_validation import (
    unsupported_example_assurance_claims,
)
from readme_agent.readme.limitation_validation import verified_limitations_are_represented


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
    assert "were inventoried at the verified source revision" in rendered
    assert "matched to the repository's static public API" not in rendered
    assert "not executed or syntax-checked" in rendered


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
                    "title": "Quick Start",
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
    assert "### Quick Start (2)" in rendered
    assert "### Quick Start (3)" in rendered
    assert introduced_duplicate_headings("", "## Quick start\n\n" + rendered) == []
    assert "The inline workflows below were syntax-checked" in rendered
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


def test_email_declared_preserve_sections_are_binding_even_without_fact_ids() -> None:
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
    section = next(item for item in assessment.sections if item.heading == "Package Entry Points")

    assert section.disposition == "preserve"
    assert (section.source_byte_start, section.source_byte_end) in declared_preserve_ranges(
        assessment
    )


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


def test_claim_accountability_helper_modules_are_document_contract_inputs() -> None:
    assert {
        "src/readme_agent/readme/claim_replacement_validation.py",
        "src/readme_agent/readme/example_assurance_validation.py",
        "src/readme_agent/readme/limitation_validation.py",
    }.issubset(DOCUMENT_CONTRACT_IMPLEMENTATION_PATHS)
