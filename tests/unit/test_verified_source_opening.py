"""Tests for selecting a verified maintainer-authored README opening."""

from pathlib import Path

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.presentation.verified_template_document import (
    build_verified_template_document_candidate,
)
from readme_agent.presentation.verified_template_draft import (
    _complete_source_opening_overview,
    verified_source_opening_summary,
)
from readme_agent.readme.assessment import assess_readme_document
from readme_agent.readme.claim_accountability_validation import (
    validate_claim_accountability_map,
)
from readme_agent.readme.verified_preservation_composition import (
    build_verified_preservation_composition_plan,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PDF_EVIDENCE = (
    PROJECT_ROOT
    / "plans"
    / "investigations"
    / "evidence"
    / "finalized-repository-readmes-v1"
    / "repositories"
    / "python"
    / "pdf--537b8273b185--bd8699b68869"
)


def test_verified_pdf_source_opening_replaces_a_redundant_generated_summary() -> None:
    source = (PDF_EVIDENCE / "ORIGINAL-README.md").read_text(encoding="utf-8")
    facts = ProductFactsV2.model_validate_json(
        (PDF_EVIDENCE / "product-facts.json").read_text(encoding="utf-8")
    )

    result = verified_source_opening_summary(source, facts, "Aspose.PDF FOSS for Python")

    assert result is not None
    summary, fields = result
    assert summary == (
        "Aspose.PDF FOSS for Python is an open-source Python library for creating,\n"
        "reading, editing, rendering, and validating PDF documents."
    )
    assert "product.identity" in fields
    assert {"product.formats", "repository.public_guidance"}.intersection(fields)


def test_verified_pdf_source_opening_adds_the_accepted_audience_without_llm_prose() -> None:
    facts = ProductFactsV2.model_validate_json(
        (PDF_EVIDENCE / "product-facts.json").read_text(encoding="utf-8")
    )

    summary, fields = _complete_source_opening_overview(
        "Aspose.PDF FOSS for Python creates and renders PDF documents.",
        ["product.identity", "product.problems_solved"],
        facts,
    )

    assert summary == (
        "Aspose.PDF FOSS for Python creates and renders PDF documents.\n\n"
        "It is designed for developers using Python."
    )
    assert fields == ["product.audience", "product.identity", "product.problems_solved"]


def test_verified_pdf_opening_keeps_source_and_audience_provenance_exact() -> None:
    source = (PDF_EVIDENCE / "ORIGINAL-README.md").read_text(encoding="utf-8")
    facts = ProductFactsV2.model_validate_json(
        (PDF_EVIDENCE / "product-facts.json").read_text(encoding="utf-8")
    )
    revision = "537b8273b185e4f7440b201cacad56567e55b2f0"
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
    )
    agentic_plan = build_verified_preservation_composition_plan(
        facts.org_repo,
        source,
        facts,
        assessment,
        lifecycle_status="FACTS_READY",
    )
    assert agentic_plan is not None

    candidate, plan = build_verified_template_document_candidate(
        facts,
        source,
        revision,
        agentic_plan,
    )
    validation = validate_claim_accountability_map(
        plan.claim_accountability,
        source_text=source,
        candidate_text=candidate,
        facts=facts,
        operations=plan.operations,
        candidate_content_provenance=plan.candidate_content_provenance,
        source_claim_resolutions=plan.source_claim_resolutions,
        composition_ledger=plan.composition_ledger,
    )
    candidate_bytes = candidate.encode("utf-8")
    summary_bindings = [
        binding
        for binding in plan.candidate_content_provenance
        if binding.provenance_id.startswith("template.summary.")
    ]
    bound_claims = {
        candidate_bytes[binding.candidate_byte_start : binding.candidate_byte_end]
        .decode("utf-8")
        .strip(): {facts.fact_by_id(fact_id).field for fact_id in binding.fact_ids}
        for binding in summary_bindings
    }

    assert validation.valid, validation.errors
    assert len(summary_bindings) == 2
    assert "repository.public_guidance" in next(
        fields for text, fields in bound_claims.items() if text.startswith("Aspose.PDF FOSS")
    )
    assert bound_claims["It is designed for developers using Python."] == {"product.audience"}
