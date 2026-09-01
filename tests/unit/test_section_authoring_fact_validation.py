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
    SectionClusterAuthoringResultV1,
    SectionClusterUnitV1,
)
from readme_agent.specialists.section_authoring_fact_validation import (
    _known_format_tokens,
    _unsupported_format_errors,
    remove_reserved_directional_units,
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


def _acquisition_fact() -> SectionAuthoringFactV1:
    """A fact shape an "installation" section would actually cite -- carries no
    format tokens and is not a `product.identity` fact, unlike every other fact
    fixture in this file."""

    return SectionAuthoringFactV1(
        fact_id="fact:installation.acquisition:1",
        field="installation.acquisition",
        value={"package_manager": "pip", "package_name": "aspose-html-foss"},
        verification_state="verified",
        corroboration=FactCorroborationV1(
            evidence_assessment_count=1,
            has_unresolved_conflict=False,
            resolved_conflict_count=0,
        ),
        polarity="positive_implementation",
        source=FactSourceRefV1(source_type="repository_file", location="pyproject.toml"),
    )


def test_own_eponymous_format_in_public_name_authorizes_installation_prose():
    """PWD-028: real `aspose-html-foss/Aspose.HTML-FOSS-for-Python` bug -- the
    "installation" section cites only acquisition facts, never `product.identity`,
    so naming the product's own public name ("Aspose.HTML FOSS for Python") in an
    installation heading was rejected as an unsupported "HTML" format claim, even
    though it names the product, not a claimed operation."""

    fact = _acquisition_fact()
    unit = SectionClusterUnitV1(
        heading="Acquire Aspose.HTML FOSS for Python from source",
        text="Clone the repository and install it directly from source.",
        fact_ids=(fact.fact_id,),
    )
    packet = SectionAuthoringPacketV1(
        org_repo="aspose-html-foss/Aspose.HTML-FOSS-for-Python",
        public_product_name="Aspose.HTML FOSS for Python",
        source_revision="deadbeef",
        target_section_id="installation",
        task_family="verified_example_framing",
        section_objective="Explain how to acquire the package.",
        accepted_facts=(fact,),
        protected_literal_hash=_PROTECTED_LITERAL_HASH,
    )

    errors = section_authoring_fact_errors(packet, unit)

    assert not any("recognized file formats are absent" in error for error in errors), errors


def test_unsupported_format_errors_negative_control_without_public_product_name():
    """Negative control: omitting `public_product_name` (the pre-fix call shape)
    must still reproduce the real bug -- proves the fix, not the test setup, is
    what clears the false positive above."""

    fact = _acquisition_fact()
    unit = SectionClusterUnitV1(
        heading="Acquire Aspose.HTML FOSS for Python from source",
        text="Clone the repository and install it directly from source.",
        fact_ids=(fact.fact_id,),
    )

    errors = _unsupported_format_errors(unit, [fact], [fact], set())

    assert any(
        "recognized file formats are absent from cited accepted facts" in error for error in errors
    ), errors

    fixed_errors = _unsupported_format_errors(
        unit, [fact], [fact], set(), "Aspose.HTML FOSS for Python"
    )

    assert not any("recognized file formats are absent" in error for error in fixed_errors), (
        fixed_errors
    )


def _limitation_fact() -> SectionAuthoringFactV1:
    return SectionAuthoringFactV1(
        fact_id="fact:product.limitations:1",
        field="product.limitations",
        value=(
            "3MF import/export (`ThreeMfImporter`/`ThreeMfExporter`) requires the `adm-zip` "
            "package at runtime — see upstream-issues.md for a real packaging gap."
        ),
        verification_state="verified",
        corroboration=FactCorroborationV1(
            evidence_assessment_count=1,
            has_unresolved_conflict=False,
            resolved_conflict_count=0,
        ),
        polarity="explicit_constraint",
        source=FactSourceRefV1(source_type="repository_file", location="bootstrap.ts"),
    )


def _reserved_3mf_format_fact() -> SectionAuthoringFactV1:
    """A `product.formats` fact reserved for a different section to claim -- the shape
    `remove_reserved_directional_units()`/`section_authoring_fact_errors()` treat as "this
    section may not itself assert a 3MF direction"."""

    return SectionAuthoringFactV1(
        fact_id="fact:product.formats:1",
        field="product.formats",
        value=["Input format: 3MF", "Output format: 3MF"],
        verification_state="verified",
        corroboration=FactCorroborationV1(
            evidence_assessment_count=1,
            has_unresolved_conflict=False,
            resolved_conflict_count=0,
        ),
        polarity="positive_implementation",
        source=FactSourceRefV1(source_type="repository_file", location="bootstrap.ts"),
    )


def _scope_and_limitations_packet(
    limitation: SectionAuthoringFactV1,
    reserved_format: SectionAuthoringFactV1,
    *,
    target_section_id: str,
) -> SectionAuthoringPacketV1:
    return SectionAuthoringPacketV1(
        org_repo="aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript",
        public_product_name="Aspose.3D FOSS for TypeScript",
        source_revision="deadbeef",
        target_section_id=target_section_id,
        task_family="verified_example_framing",
        section_objective="Describe scope and limitations.",
        accepted_facts=(limitation,),
        do_not_claim=(reserved_format,),
        protected_literal_hash=_PROTECTED_LITERAL_HASH,
    )


def _3mf_limitation_unit(limitation: SectionAuthoringFactV1) -> SectionClusterUnitV1:
    return SectionClusterUnitV1(
        heading="Feature and Workflow Boundaries",
        text=(
            "3MF import/export (`ThreeMfImporter`/`ThreeMfExporter`) requires the `adm-zip` "
            "package at runtime — see upstream-issues.md for a real packaging gap."
        ),
        fact_ids=(limitation.fact_id,),
    )


def test_scope_and_limitations_may_name_an_already_authorized_format_as_a_caveat():
    """PWD-047: `aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript`'s real, only limitation names
    an already-authorized format (3MF) alongside import/export-shaped wording while
    describing a real runtime packaging caveat, not asserting a new capability. This must
    not be rejected as "crossing the deterministic format-rendering boundary" -- the section
    whose entire purpose is describing constraints on established capabilities is exempt."""

    limitation = _limitation_fact()
    reserved_format = _reserved_3mf_format_fact()
    packet = _scope_and_limitations_packet(
        limitation, reserved_format, target_section_id="scope_and_limitations"
    )
    unit = _3mf_limitation_unit(limitation)

    errors = section_authoring_fact_errors(packet, unit)
    assert not any("reserved for deterministic rendering" in error for error in errors), errors

    result, rejected_hashes, omitted_ids = remove_reserved_directional_units(
        packet, SectionClusterAuthoringResultV1(units=(unit,))
    )
    assert result.units == (unit,)
    assert rejected_hashes == ()
    assert omitted_ids == ()


def test_other_sections_still_reject_the_same_reserved_directional_claim():
    """Negative control: the identical 3MF-mentioning unit, authored for a DIFFERENT section
    (not scope_and_limitations), must still be rejected -- the exemption is scoped to the one
    section confirmed to need it, not a general loosening of this gate."""

    limitation = _limitation_fact()
    reserved_format = _reserved_3mf_format_fact()
    packet = _scope_and_limitations_packet(
        limitation, reserved_format, target_section_id="key_capabilities"
    )
    unit = _3mf_limitation_unit(limitation)

    errors = section_authoring_fact_errors(packet, unit)
    assert any("reserved for deterministic rendering" in error for error in errors), errors

    result, rejected_hashes, omitted_ids = remove_reserved_directional_units(
        packet, SectionClusterAuthoringResultV1(units=(unit,))
    )
    assert result.units == ()
    assert rejected_hashes != ()
    assert omitted_ids == (limitation.fact_id,)
