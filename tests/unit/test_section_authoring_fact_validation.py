"""Regressions for the two quick_start false-positive blocks found in the
2026-08-26 aspose-pdf-foss fleet pass: a C++ direct-initialization example
never authorizing create/build/instantiate claims (no `=` present), and a
filename-embedded format extension ("input.pdf") never authorizing the format
it names (canonical_document_format() rejects the whole compound token)."""

from __future__ import annotations

from readme_agent.specialists.section_authoring_contracts import (
    FactCorroborationV1,
    FactSourceRefV1,
    SectionAuthoringFactV1,
    SectionAuthoringPacketV1,
    SectionClusterUnitV1,
)
from readme_agent.specialists.section_authoring_fact_validation import (
    _known_format_tokens,
    section_authoring_fact_errors,
)

_PROTECTED_LITERAL_HASH = "0" * 64


def _minimal_example_fact(code: str) -> SectionAuthoringFactV1:
    return SectionAuthoringFactV1(
        fact_id="fact:example.minimal:1",
        field="example.minimal",
        value={"code": code, "module": "Aspose.PDF"},
        verification_state="verified",
        corroboration=FactCorroborationV1(
            evidence_assessment_count=1,
            has_unresolved_conflict=False,
            resolved_conflict_count=0,
        ),
        polarity="positive_implementation",
        source=FactSourceRefV1(source_type="repository_file", location="Example.cpp"),
    )


def _packet(fact: SectionAuthoringFactV1) -> SectionAuthoringPacketV1:
    return SectionAuthoringPacketV1(
        org_repo="aspose-pdf-foss/Aspose.PDF-FOSS-for-Cpp",
        public_product_name="Aspose.PDF FOSS for Cpp",
        source_revision="deadbeef",
        target_section_id="quick_start",
        task_family="verified_example_framing",
        section_objective="Demonstrate the minimal example.",
        accepted_facts=(fact,),
        protected_literal_hash=_PROTECTED_LITERAL_HASH,
    )


def test_cpp_direct_initialization_authorizes_construction_claims():
    """`Type identifier(args);` has no `=`, unlike `Type identifier = Type(args);`,
    but is exactly as unambiguous a construction as the assignment form."""

    fact = _minimal_example_fact('Aspose::Pdf::Document doc("input.pdf");')
    unit = SectionClusterUnitV1(
        heading="Create a minimal C++ program",
        text="This example creates a document and instantiates the API client.",
        fact_ids=(fact.fact_id,),
    )

    errors = section_authoring_fact_errors(_packet(fact), unit)

    assert not any("does not execute the claimed" in error for error in errors), errors


def test_cpp_member_call_alone_does_not_authorize_construction_claims():
    """A plain member-call expression (`doc.Save(...)`) must not be mistaken for a
    two-identifier direct-initialization -- the `.` sits where the fix's required
    whitespace would be, so this negative control must still reject a bare "create"
    claim the example itself never demonstrates."""

    fact = _minimal_example_fact('doc.save("output.pdf");')
    unit = SectionClusterUnitV1(
        heading="Create a minimal C++ program",
        text="This example creates a document.",
        fact_ids=(fact.fact_id,),
    )

    errors = section_authoring_fact_errors(_packet(fact), unit)

    assert any("does not execute the claimed 'create' operation" in error for error in errors), (
        errors
    )


def test_filename_embedded_extension_authorizes_its_format():
    """ "input.pdf"/"output.pdf" are compound tokens (filename + extension) that
    canonical_document_format() rejects whole -- the extension after the last dot
    must still resolve to the same canonical format as writing "PDF" alone."""

    # "doc" is deliberately avoided as a variable name here -- it independently
    # aliases to the canonical Word format "DOC", unrelated to this dot-suffix fix.
    assert _known_format_tokens('instance.Save("output.pdf")') == {"PDF"}
    assert _known_format_tokens('PdfDocument instance("input.pdf")') == {"PDF"}


def test_filename_embedded_extension_authorizes_quick_start_prose():
    fact = _minimal_example_fact('doc.Save("output.pdf");')
    unit = SectionClusterUnitV1(
        heading="Create a minimal C++ program",
        text="This example writes the document to a PDF file.",
        fact_ids=(fact.fact_id,),
    )

    errors = section_authoring_fact_errors(_packet(fact), unit)

    assert not any("recognized file formats are absent" in error for error in errors), errors
