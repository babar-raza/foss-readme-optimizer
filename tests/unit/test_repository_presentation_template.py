"""Prove the accepted README structure compiles without cross-product leakage."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from readme_agent.facts.schema_v2 import FactRecordV2, FactSourceV2, ProductFactsV2
from readme_agent.golden_set.review_fixtures import REVIEW_ARCHETYPES, build_review_facts
from readme_agent.presentation.template_adapters import (
    adopt_accepted_reference,
    bind_product_facts,
)
from readme_agent.presentation.template_compiler import (
    compile_repository_presentation,
    select_density_profile,
)
from readme_agent.presentation.template_schema import (
    BoundTemplateContentV1,
    FactFieldTemplateContentV1,
    PresentationTemplateDependenciesV1,
    PresentationTemplateInputV1,
    ProductFactsTemplateDraftV1,
    load_repository_presentation_template,
    repository_presentation_template_hash,
)
from readme_agent.presentation.verified_preservation_sections import (
    build_verified_source_preservation_selection,
)
from readme_agent.presentation.verified_source_claim_resolution_engine import resolve_source_claims
from readme_agent.presentation.verified_source_density import apply_verified_source_density
from readme_agent.presentation.verified_template_capabilities import (
    capability_claim_fact_ids,
    capability_highlights_markdown,
)
from readme_agent.presentation.verified_template_draft import build_verified_template_draft
from readme_agent.presentation.verified_template_example_presentation import (
    public_examples_introduction,
)
from readme_agent.presentation.verified_template_provenance import build_template_provenance
from readme_agent.presentation.verified_template_sections import (
    additional_examples_markdown,
    contributing_markdown,
    dependency_markdown,
    development_markdown,
    optional_extras_markdown,
    package_status_markdown,
    repository_documents_markdown,
    scenario_dependency_markdown,
    security_markdown,
)
from readme_agent.presentation.visitor_contract import build_presentation_visitor_contract
from readme_agent.readme.agentic_composition_models import ReadmeAgenticCompositionPlanV1
from readme_agent.readme.assessment import assess_readme_document
from readme_agent.readme.assessment_claims import assess_material_claims
from readme_agent.readme.composition_lineage_models import ExactSourcePlacementV1
from readme_agent.readme.document_plan import CandidateContentProvenanceV1
from readme_agent.readme.document_renderer import build_readme_document_candidate
from readme_agent.readme.document_structure import parse_headings
from readme_agent.readme.presentation_lint import lint_readme_presentation
from readme_agent.readme.source_claim_policy import SourceClaimPolicyCorrectionV1
from readme_agent.readme.verified_preservation_composition import (
    build_verified_preservation_composition_plan,
)
from readme_agent.validation.presentation_template import validate_repository_presentation

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = (
    ROOT
    / "plans"
    / "investigations"
    / "evidence"
    / "readme-presentation-contract-v1"
    / "aspose-note-foss-python-golden.md"
)
HASH = "0" * 64


def _verified_3d_inputs(
    source: str | None = None,
    *,
    include_api_surface: bool = False,
) -> tuple[str, ProductFactsV2, str, ReadmeAgenticCompositionPlanV1]:
    source = source or (
        ROOT / "tests" / "fixtures" / "readmes" / "real_audit_2026-07-17" / "3d-python.md"
    ).read_text(encoding="utf-8")
    facts = ProductFactsV2.model_validate_json(
        (
            ROOT
            / "tests"
            / "fixtures"
            / "readmes"
            / "verified_source_assurance"
            / "aspose-3d-python-facts-ab1a2267.json"
        ).read_text(encoding="utf-8")
    )
    revision = "ab1a2267a0ba6302311d0c7c4ad01494974c7d76"
    if include_api_surface:
        payload = facts.model_dump(mode="json")
        fact_id = "api.public_surface:template-test"
        payload["facts"].append(
            FactRecordV2(
                fact_id=fact_id,
                field="api.public_surface",
                value={
                    "modules": [
                        {
                            "module": "aspose.threed",
                            "exports": ["Scene", "Node", "Mesh"],
                        }
                    ],
                    "classes": [
                        {
                            "name": name,
                            "source_path": "aspose/threed/__init__.py",
                            "source_sha256": character * 64,
                            "members": [],
                        }
                        for name, character in (("Scene", "a"), ("Node", "b"), ("Mesh", "c"))
                    ],
                },
                source=FactSourceV2(
                    source_type="mechanical_repository",
                    location="repository://aspose/threed/__init__.py",
                    source_revision=revision,
                ),
                verification_state="verified",
                authoritative_owner="repository-source",
                confidence=1.0,
                affected_surfaces=["readme.api_reference"],
            ).model_dump(mode="json")
        )
        payload["selected_fact_ids"]["api.public_surface"] = fact_id
        facts = ProductFactsV2.model_validate(payload)
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
    )
    plan = build_verified_preservation_composition_plan(
        facts.org_repo,
        source,
        facts,
        assessment,
        lifecycle_status="FACTS_READY",
    )
    assert plan is not None
    return source, facts, revision, plan


def _fact(markdown: str, *ids: str) -> BoundTemplateContentV1:
    return BoundTemplateContentV1(
        markdown=markdown,
        source_kind="repository_fact",
        fact_ids=list(ids),
    )


def _configured(markdown: str, standard: str) -> BoundTemplateContentV1:
    return BoundTemplateContentV1(
        markdown=markdown,
        source_kind="configured_standard",
        standard_ids=[standard],
    )


def _page_input() -> PresentationTemplateInputV1:
    return PresentationTemplateInputV1(
        org_repo="aspose-page-foss/Aspose.Page-FOSS-for-Python",
        source_revision="page-revision",
        source_line_count=120,
        title=_fact("Aspose.Page FOSS for Python", "identity:page"),
        badges=_fact(
            "[![PyPI](https://img.shields.io/pypi/v/aspose-page.svg)]"
            "(https://pypi.org/project/aspose-page/)",
            "acquisition:page",
        ),
        summary=_fact(
            "Aspose.Page FOSS for Python reads and converts page-description documents.",
            "identity:page",
            "problems:page",
        ),
        sections={
            "at_a_glance": _fact(
                """```mermaid
block-beta
  columns 5
  block:Inputs
    columns 1
    IH["Inputs and Formats"]
    I1["XPS documents"]
  end
  PRODUCT["Aspose.Page FOSS for Python"]
  block:Capabilities:2
    columns 2
    C1["Read document structure"]:2
    C2["Inspect pages and resources"]:2
    CH["Core Capabilities"]:2
    C3["Convert supported content"]:2
  end
  block:Outputs
    columns 1
    OH["Outputs"]
    O1["Structured page data"]
  end
  style IH fill:none,stroke:none,font-weight:bold
  style OH fill:none,stroke:none,font-weight:bold
  I1 --- PRODUCT
  PRODUCT --- CH
  CH --- O1
```""",
                "identity:page",
                "formats:page",
                "capabilities:page",
            ),
            "key_capabilities": _fact(
                "- **Read XPS documents** - Inspect XPS document content.\n"
                "- **Inspect pages** - Access pages and resources.\n"
                "- **Convert supported content** - Export supported output formats.",
                "capabilities:page",
            ),
            "installation": _fact(
                "Install the verified package:\n\n```bash\npython -m pip install aspose-page\n```",
                "acquisition:page",
            ),
            "quick_start": _fact(
                "Load a document:\n\n```python\nfrom aspose.page import Document\n```",
                "example:page",
            ),
            "scope_and_limitations": _fact(
                "Support is limited to the formats verified in this repository.",
                "limitations:page",
            ),
            "license": _configured(
                "This project uses the [MIT License](LICENSE), which permits use, modification, "
                "distribution, and commercial use when its notice is retained.",
                "license-benefits-v1",
            ),
        },
    )


def _page_input_for_facts(facts: ProductFactsV2) -> PresentationTemplateInputV1:
    """Rebind the synthetic Page layout to one concrete fact graph."""

    template_input = _page_input()
    aliases = {
        "identity:page": "product.identity",
        "acquisition:page": "installation.verified_acquisition",
        "problems:page": "product.problems_solved",
        "formats:page": "product.formats",
        "capabilities:page": "product.capabilities",
        "example:page": "example.minimal",
        "limitations:page": "product.limitations",
    }

    def rebind(content: BoundTemplateContentV1) -> BoundTemplateContentV1:
        return content.model_copy(
            update={
                "fact_ids": [
                    facts.selected_fact_ids[aliases.get(fact_id, fact_id)]
                    for fact_id in content.fact_ids
                ]
            }
        )

    return template_input.model_copy(
        update={
            "title": rebind(template_input.title),
            "badges": rebind(template_input.badges),
            "summary": rebind(template_input.summary),
            "sections": {
                slot: rebind(content) for slot, content in template_input.sections.items()
            },
        }
    )


def test_superseded_note_reference_cannot_be_adopted_as_current() -> None:
    markdown = REFERENCE.read_text(encoding="utf-8")

    with pytest.raises(ValueError, match="requires current canonical requalification"):
        adopt_accepted_reference(
            markdown,
            org_repo="aspose-note-foss/Aspose.Note-FOSS-for-Python",
            source_revision="6d97a522a9ed24708687911f1aabb76e2dea2da7",
        )


def test_compact_page_profile_is_product_specific_and_valid() -> None:
    template_input = _page_input()

    candidate = compile_repository_presentation(template_input)

    assert select_density_profile(template_input.source_line_count) == "compact"
    assert "Aspose.Page FOSS for Python" in candidate
    assert "Aspose.Note" not in candidate
    assert ".one" not in candidate
    assert validate_repository_presentation(candidate, template_input) == []


def test_capability_renderer_binds_cleaned_public_label_to_exact_facts() -> None:
    facts = ProductFactsV2.model_validate(build_review_facts(REVIEW_ARCHETYPES[2]))
    capability = facts.selected_fact("product.capabilities")
    facts = facts.model_copy(
        update={
            "facts": [
                fact.model_copy(update={"value": ["PDF export via SaveFormat.Pdf"]})
                if fact.fact_id == capability.fact_id
                else fact
                for fact in facts.facts
            ]
        }
    )

    rendered = capability_highlights_markdown(facts)

    assert rendered is not None
    assert "SaveFormat.Pdf" not in rendered
    assert "**Export PDF files**" in rendered
    assert "Create files in the listed output formats" in rendered
    assert "verified output" not in rendered.casefold()
    assert capability_claim_fact_ids(rendered, facts) == sorted(
        {capability.fact_id, facts.selected_fact_ids["product.formats"]}
    )


@pytest.mark.parametrize(
    "capability_text",
    [
        "Export PDF documents",
        "Save and write supported document output",
        "Render pages to PNG or TIFF",
    ],
)
def test_capability_output_never_exposes_internal_assurance_narration(
    capability_text: str,
) -> None:
    facts = ProductFactsV2.model_validate(build_review_facts(REVIEW_ARCHETYPES[2]))
    capability = facts.selected_fact("product.capabilities")
    facts = facts.model_copy(
        update={
            "facts": [
                fact.model_copy(update={"value": [capability_text]})
                if fact.fact_id == capability.fact_id
                else fact
                for fact in facts.facts
            ]
        }
    )

    rendered = capability_highlights_markdown(facts)

    assert rendered is not None
    public_text = rendered.casefold()
    for forbidden in (
        "verified output",
        "source-bound",
        "source revision",
        "inventory receipt",
        "verification environment",
        "syntax-checked",
        "not executed",
    ):
        assert forbidden not in public_text


def _render_scope_with_limitations(statements: list[str]) -> str:
    source, facts, revision, plan = _verified_3d_inputs()
    limitations_id = facts.selected_fact_ids["product.limitations"]
    facts = facts.model_copy(
        update={
            "facts": [
                fact.model_copy(
                    update={
                        "value": [
                            {"statement": statement, "path": "src/acme/reader.py"}
                            for statement in statements
                        ]
                    }
                )
                if fact.fact_id == limitations_id
                else fact
                for fact in facts.facts
            ]
        }
    )

    draft = build_verified_template_draft(facts, source, revision, plan)

    return draft.sections["scope_and_limitations"].markdown


def test_limitation_renderer_projects_exception_facts_into_public_copy() -> None:
    rendered = _render_scope_with_limitations(
        [
            "Password-protected documents are not supported",
            "Unsupported format/options argument",
            "Only PDF save is supported",
            "Only .pDf file targets are supported for save operations",
            "PDF export requires reportlab",
        ]
    )

    assert "- Password-protected documents are not supported as input." in rendered
    assert rendered.count("- Output is limited to PDF files.") == 1
    assert "- PDF exports require ReportLab." in rendered
    assert "Unsupported format/options argument" not in rendered
    assert ".PDF file targets" not in rendered
    assert "documented output formats" not in rendered


def test_limitation_renderer_is_format_generic_and_preserves_distinct_boundaries() -> None:
    rendered = _render_scope_with_limitations(
        [
            "Only xPs and ePs output is supported",
            "Only .XPS and .EPS file targets are supported for save operations",
            "Unsupported options argument",
            "SVG export requires CairoSVG",
            "Mesh export is not implemented",
        ]
    )

    assert rendered.count("- Output is limited to XPS and EPS files.") == 1
    assert "- SVG exports require CairoSVG." in rendered
    assert "- Mesh export is not implemented." in rendered
    assert "Unsupported options argument" not in rendered
    assert "documented save options" not in rendered


@pytest.mark.parametrize(
    ("exception_fragment", "visitor_copy"),
    [
        (
            "Unsupported format/options argument",
            "Only documented output formats and save options are supported.",
        ),
        ("Unsupported format argument", "Only documented output formats are supported."),
        ("Unsupported options argument", "Only documented save options are supported."),
    ],
)
def test_limitation_renderer_rephrases_a_standalone_exception_fragment(
    exception_fragment: str,
    visitor_copy: str,
) -> None:
    rendered = _render_scope_with_limitations([exception_fragment])

    assert f"- {visitor_copy}" in rendered
    assert exception_fragment not in rendered


def test_capability_renderer_keeps_first_rich_row_and_omits_semantic_repeats() -> None:
    facts = ProductFactsV2.model_validate(build_review_facts(REVIEW_ARCHETYPES[2]))
    capability = facts.selected_fact("product.capabilities")
    facts = facts.model_copy(
        update={
            "facts": [
                fact.model_copy(
                    update={
                        "value": [
                            "Run heuristic PDF/A and PDF/UA validation",
                            "PDF/A and PDF/UA validation",
                        ]
                    }
                )
                if fact.fact_id == capability.fact_id
                else fact
                for fact in facts.facts
            ]
        }
    )

    rendered = capability_highlights_markdown(facts)

    assert rendered is not None
    assert len(rendered.splitlines()) == 1
    assert "**Validate PDF/A and PDF/UA documents**" in rendered
    assert "Run heuristic checks" in rendered


def test_capability_renderer_applies_the_same_semantic_contract_after_seo_rendering() -> None:
    facts = ProductFactsV2.model_validate(build_review_facts(REVIEW_ARCHETYPES[2]))
    capability = facts.selected_fact("product.capabilities")
    identity = facts.selected_fact("product.identity")
    identity = identity.model_copy(
        update={
            "value": {
                **(identity.value if isinstance(identity.value, dict) else {}),
                "product_name": "Aspose.PDF",
                "platform": "python",
            }
        }
    )
    api = FactRecordV2(
        fact_id="api.public_surface:capability-dedup-test",
        field="api.public_surface",
        value={"modules": [], "classes": [{"name": "Document"}]},
        source=identity.source,
        verification_state="verified",
        authoritative_owner="repository-source",
        confidence=1.0,
        affected_surfaces=["readme"],
    )
    facts = facts.model_copy(
        update={
            "facts": [
                identity
                if fact.fact_id == identity.fact_id
                else fact.model_copy(
                    update={
                        "value": [
                            "Encrypt, decrypt, optimize, and compress PDF documents",
                            "Document lifecycle management",
                        ]
                    }
                )
                if fact.fact_id == capability.fact_id
                else fact
                for fact in facts.facts
                if fact.field != "api.public_surface"
            ]
            + [api],
            "selected_fact_ids": {
                **facts.selected_fact_ids,
                "api.public_surface": api.fact_id,
            },
        }
    )

    rendered = capability_highlights_markdown(facts)

    assert rendered is not None
    assert len(rendered.splitlines()) == 1
    assert "Encrypt, decrypt, optimize, and compress PDF documents" in rendered
    assert "Document lifecycle management" not in rendered


def test_pdf_capabilities_share_one_normalized_public_semantic_view() -> None:
    facts = ProductFactsV2.model_validate(build_review_facts(REVIEW_ARCHETYPES[2]))
    capability = facts.selected_fact("product.capabilities")
    facts = facts.model_copy(
        update={
            "facts": [
                fact.model_copy(
                    update={
                        "value": [
                            "Create, load, save, merge, and inspect PDF documents",
                            (
                                "Add and edit text and images, including text replacement "
                                "and redaction"
                            ),
                            "Run heuristic PDF/A and PDF/UA validation",
                            "Encrypt, decrypt, optimize, and compress PDF documents",
                            "Document lifecycle management",
                            "PDF file editing operations",
                            "PDF/A and PDF/UA validation",
                            "Resource limit configuration",
                            "Digital signature support",
                        ]
                    }
                )
                if fact.fact_id == capability.fact_id
                else fact
                for fact in facts.facts
            ]
        }
    )

    rendered = capability_highlights_markdown(facts)

    assert rendered is not None
    assert "Document lifecycle management" not in rendered
    assert "PDF file editing operations" not in rendered
    assert len([line for line in rendered.splitlines() if "PDF/A and PDF/UA" in line]) == 1
    assert "Use " not in rendered
    assert "Create and manage PDF documents" in rendered
    assert "Edit text and images in PDF documents" in rendered
    assert "Configure PDF resource limits" in rendered
    assert "Work with PDF digital signatures" in rendered
    assert "Create and manage PDF documents** - Create and manage PDF documents" not in rendered
    assert "Edit text and images in PDF documents** - Edit text and images" not in rendered
    assert "Validate PDF/A and PDF/UA documents" in rendered
    assert "Run heuristic checks for archival and accessibility conformance profiles" in rendered
    assert "Protect document content through encryption while controlling file size" in rendered


def test_pdf_capability_rows_deduplicate_seo_titles_and_avoid_generic_copy() -> None:
    facts = ProductFactsV2.model_validate(build_review_facts(REVIEW_ARCHETYPES[2]))
    capability = facts.selected_fact("product.capabilities")
    formats = facts.selected_fact("product.formats")
    facts = facts.model_copy(
        update={
            "facts": [
                fact.model_copy(
                    update={
                        "value": [
                            "Extract text, images, and attachments",
                            "Extract images and attachments",
                            "Encrypt and decrypt documents with RC4 or AES",
                            "Optimize streams, images, fonts, and unused objects",
                            "Perform heuristic PDF/A and PDF/UA checks and conversions",
                            "Render pages to PNG or TIFF",
                        ]
                    }
                )
                if fact.fact_id == capability.fact_id
                else fact.model_copy(update={"value": ["PDF", "PNG", "TIFF"]})
                if fact.fact_id == formats.fact_id
                else fact
                for fact in facts.facts
            ]
        }
    )

    rendered = capability_highlights_markdown(facts)

    assert rendered is not None
    assert len([line for line in rendered.splitlines() if line.startswith("- **Extract")]) == 1
    assert "Protect PDF content with RC4 or AES encryption" in rendered
    assert "Compress streams and consolidate unused image" in rendered
    assert "Validate and convert PDF/A and PDF/UA documents" in rendered
    assert "Apply the operation" not in rendered
    render_row = next(line for line in rendered.splitlines() if "Render pages" in line)
    assert facts.selected_fact_ids["product.formats"] in capability_claim_fact_ids(
        render_row,
        facts,
    )

    template_input = _page_input()
    for action in ("Add", "Concatenate", "Configure", "Encrypt", "Run", "Work"):
        candidate = compile_repository_presentation(template_input).replace(
            "**Read XPS documents**",
            f"**{action} verified PDF content**",
        )
        assert validate_repository_presentation(candidate, template_input) == []


def test_current_pdf_xmp_detail_becomes_one_concrete_fact_bound_capability() -> None:
    """Regress the 537b827 PDF/Python duplicate rejected by independent review."""

    facts = ProductFactsV2.model_validate(build_review_facts(REVIEW_ARCHETYPES[2]))
    capability = facts.selected_fact("product.capabilities")
    api = FactRecordV2(
        fact_id="api.public_surface:pdf-xmp-537b827",
        field="api.public_surface",
        value={
            "modules": [{"module": "aspose_pdf", "exports": []}],
            "classes": [
                {"name": name, "module": "aspose_pdf", "members": []}
                for name in ("XmpPacket", "parse_xmp", "serialize_xmp", "CosExtractor")
            ],
        },
        source=capability.source,
        verification_state="verified",
        authoritative_owner="repository-source",
        confidence=1.0,
        affected_surfaces=["readme"],
    )
    facts = facts.model_copy(
        update={
            "facts": [
                fact.model_copy(update={"value": ["XMP metadata handling"]})
                if fact.fact_id == capability.fact_id
                else fact
                for fact in facts.facts
                if fact.field != "api.public_surface"
            ]
            + [api],
            "selected_fact_ids": {**facts.selected_fact_ids, "api.public_surface": api.fact_id},
        }
    )
    source = (
        "# Aspose.PDF FOSS for Python\n\n"
        "## Features\n\n"
        "- Work with XMP metadata and low-level PDF objects\n"
    )

    rendered = capability_highlights_markdown(facts, source_text=source)

    assert rendered is not None
    assert rendered.count("XMP metadata") == 1
    assert "**Work with XMP metadata and low-level PDF objects**" in rendered
    assert "Parse and serialize metadata packets while inspecting low-level PDF objects" in rendered
    assert "`XmpPacket`, `parse_xmp`, `serialize_xmp`, and `CosExtractor` APIs" in rendered
    assert "Apply the operation through the product's public API" not in rendered
    assert capability.fact_id in capability_claim_fact_ids(rendered, facts)


def test_example_introduction_uses_parallel_visitor_facing_gerunds() -> None:
    rendered = public_examples_introduction(
        [
            "Assign a PBR Material and Export to GLTF",
            "Build a Cube and Export It to 3MF",
            "Explore the Scene API",
            "Convert a Primitive to a Mesh",
            "Inspect Another Workflow",
        ],
        has_repository_files=False,
        has_result_assets=False,
    )

    assert "assigning a PBR material and exporting to GLTF" in rendered
    assert "building a cube and exporting It to 3MF" in rendered
    assert "plus 1 more workflow" in rendered


def test_verified_template_omits_missing_compatibility_from_installation_binding() -> None:
    facts = ProductFactsV2.model_validate(build_review_facts(REVIEW_ARCHETYPES[2]))
    compatibility_id = facts.selected_fact_ids["product.compatibility"]
    limitations_id = facts.selected_fact_ids["product.limitations"]
    identity_id = facts.selected_fact_ids["product.identity"]
    replacement_values = {
        facts.selected_fact_ids["installation.coordinates"]: [
            {"name": "acme-pdf", "version": "1.0.0"}
        ],
        facts.selected_fact_ids["installation.verified_acquisition"]: {
            "method": "pypi",
            "coordinate": {"name": "acme-pdf"},
        },
        facts.selected_fact_ids["example.minimal"]: {
            "language": "python",
            "code": "from acme.pdf import Document\n",
            "input_fixture_bindings": [],
        },
    }
    payload = facts.model_dump(mode="json")
    for record in payload["facts"]:
        if record["fact_id"] == compatibility_id:
            record.update(verification_state="missing", value=None, confidence=0.0)
        elif record["fact_id"] == limitations_id:
            record.update(verification_state="missing", value=None, confidence=0.0)
        elif record["fact_id"] == identity_id:
            record["value"] = {
                "product_name": "Aspose.PDF",
                "family": "pdf",
                "ecosystem": "python",
                "platform": "python",
            }
        elif record["fact_id"] in replacement_values:
            record["value"] = replacement_values[record["fact_id"]]
    facts = ProductFactsV2.model_validate(payload)
    plan = ReadmeAgenticCompositionPlanV1(
        org_repo=facts.org_repo,
        source_sha256=HASH,
        facts_hash=facts.canonical_hash(),
        assessment_hash=HASH,
        prompt_sha256=HASH,
        tool_schema_sha256=HASH,
        input_sha256=HASH,
        model="fixture",
        attempt_count=1,
        repository_summary="Use only accepted repository facts.",
        section_decisions=[],
        overview_sentences=[],
    )

    draft = build_verified_template_draft(facts, "# Existing README\n", "a" * 40, plan)
    template_input = bind_product_facts(facts, draft)

    assert "product.compatibility" not in draft.sections["installation"].fact_fields
    assert (
        template_input.sections["installation"].source_kind
        == "repository_fact_and_configured_standard"
    )
    candidate = compile_repository_presentation(template_input)
    provenance = build_template_provenance(candidate, template_input, facts)
    binding = next(
        item
        for item in provenance
        if {facts.fact_by_id(fact_id).field for fact_id in item.fact_ids}
        == {"installation.coordinates", "installation.verified_acquisition"}
    )
    bound = candidate.encode("utf-8")[
        binding.candidate_byte_start : binding.candidate_byte_end
    ].decode("utf-8")
    assert bound == "```bash\npython -m pip install acme-pdf\n```"
    assert {facts.fact_by_id(fact_id).field for fact_id in binding.fact_ids} == {
        "installation.coordinates",
        "installation.verified_acquisition",
    }


def test_verified_template_generates_fact_backed_optional_slot_when_source_lacks_it() -> None:
    source, facts, revision, plan = _verified_3d_inputs(include_api_surface=True)

    draft = build_verified_template_draft(facts, source, revision, plan)

    api_reference = draft.sections["api_reference"]
    assert api_reference.disposition == "include"
    assert api_reference.fact_fields == ["api.public_surface", "documentation.links"]
    assert api_reference.standard_ids == ["readme.api_reference"]


def test_verified_template_omits_license_when_repository_has_no_accepted_license_fact() -> None:
    source, facts, revision, plan = _verified_3d_inputs()
    license_id = facts.selected_fact_ids["product.license"]
    payload = facts.model_dump(mode="json")
    for record in payload["facts"]:
        if record["fact_id"] == license_id:
            record.update(verification_state="missing", value=None, confidence=0.0)
    facts = ProductFactsV2.model_validate(payload)

    draft = build_verified_template_draft(facts, source, revision, plan)
    template_input = bind_product_facts(facts, draft)
    candidate = compile_repository_presentation(template_input)

    assert draft.sections["license"].disposition == "omit"
    assert "## License" not in candidate
    assert "(#license)" not in candidate
    assert "License-" not in candidate


def test_verified_template_does_not_defer_optional_slot_from_heading_presence_alone() -> None:
    source, facts, revision, _ = _verified_3d_inputs(include_api_surface=True)
    contract = load_repository_presentation_template()
    source = (
        source.rstrip()
        + f"\n\n## {contract.headings['api_reference']}\n\n"
        + "The curated public surface includes `Scene`, `Node`, and `Mesh`.\n"
    )
    source, facts, revision, plan = _verified_3d_inputs(source, include_api_surface=True)

    draft = build_verified_template_draft(facts, source, revision, plan)

    api_reference = draft.sections["api_reference"]
    assert api_reference.disposition == "include"
    assert api_reference.fact_fields == ["api.public_surface", "documentation.links"]
    assert api_reference.standard_ids == ["readme.api_reference"]


def test_source_owned_optional_slot_is_preserved_exactly_once() -> None:
    source, facts, revision, _ = _verified_3d_inputs(include_api_surface=True)
    contract = load_repository_presentation_template()
    exact_body = "- `Scene`, `Node`, `Mesh`\n"
    source = source.rstrip() + f"\n\n## {contract.headings['api_reference']}\n\n" + exact_body
    source, facts, revision, plan = _verified_3d_inputs(source, include_api_surface=True)
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
    )
    api_section = next(
        section
        for section in assessment.sections
        if section.heading == contract.headings["api_reference"]
    )

    candidate, document_plan = build_readme_document_candidate(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
        agentic_composition_plan=plan.model_dump(mode="json"),
    )

    assert candidate.count(f"## {contract.headings['api_reference']}") == 1
    assert candidate.count(exact_body.strip()) == 1
    assert any(
        placement.source_byte_start >= api_section.source_byte_start
        and placement.source_byte_end <= api_section.source_byte_end
        for placement in document_plan.composition_ledger.source_placements
    )


def test_source_owned_security_detail_keeps_a_generated_canonical_destination() -> None:
    source, facts, revision, _ = _verified_3d_inputs(include_api_surface=True)
    source_fact = facts.selected_fact("product.identity").source
    security_fact = FactRecordV2(
        fact_id="repository.security_guidance:test",
        field="repository.security_guidance",
        value={
            "policy": {
                "path": "SECURITY.md",
                "private_reporting_url": (
                    "https://github.com/aspose-3d-foss/"
                    "Aspose.3D-FOSS-for-Python/security/advisories/new"
                ),
            }
        },
        source=source_fact,
        verification_state="verified",
        authoritative_owner="repository-owner",
        confidence=1.0,
        affected_surfaces=["readme"],
    )
    facts = facts.model_copy(
        update={
            "facts": [
                *[item for item in facts.facts if item.field != security_fact.field],
                security_fact,
            ],
            "selected_fact_ids": {
                **facts.selected_fact_ids,
                security_fact.field: security_fact.fact_id,
            },
        }
    )
    source = (
        source.rstrip()
        + "\n\n## Security\n\n"
        + "Follow [SECURITY.md](SECURITY.md) and use private vulnerability reporting.\n"
    )
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
    )
    plan = build_verified_preservation_composition_plan(
        facts.org_repo,
        source,
        facts,
        assessment,
        lifecycle_status="FACTS_READY",
    )
    assert plan is not None

    candidate, _ = build_readme_document_candidate(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
        agentic_composition_plan=plan.model_dump(mode="json"),
    )

    assert candidate.count("## Security") == 1
    assert "- [Security](#security)" in candidate
    assert candidate.count("Follow [SECURITY.md](SECURITY.md)") == 1


def test_no_op_uses_source_lineage_and_changed_candidate_uses_verified_equivalence() -> None:
    _, facts, _, _ = _verified_3d_inputs(include_api_surface=True)
    source = "## Key capabilities\n\nVerified public capability.\n"
    source_claim = assess_material_claims(source)[0]
    fact_id = facts.selected_fact_ids["api.public_surface"]

    assert (
        resolve_source_claims(
            source,
            source,
            facts,
            fail_on_unresolved_preserve=False,
        )
        == []
    )

    candidate = "# Aspose.3D FOSS for Python\n\n" + source
    candidate_claim = next(
        claim
        for claim in assess_material_claims(candidate)
        if claim.content_sha256 == source_claim.content_sha256
    )
    provenance = CandidateContentProvenanceV1(
        provenance_id="template.section.api_reference",
        candidate_byte_start=candidate_claim.source_byte_start,
        candidate_byte_end=candidate_claim.source_byte_end - 1,
        fact_ids=[fact_id],
        rationale="Bind material claim bytes while excluding only the trailing newline.",
    )

    resolutions = resolve_source_claims(
        source,
        candidate,
        facts,
        [provenance],
        fail_on_unresolved_preserve=False,
    )

    assert len(resolutions) == 1
    assert resolutions[0].resolution == "verified_equivalence"
    assert resolutions[0].fact_ids == [fact_id]
    assert resolutions[0].candidate_claim_id == candidate_claim.claim_id


@pytest.mark.parametrize(
    ("source", "candidate", "with_fact_provenance"),
    [
        (
            "## Key capabilities\n\nVerified public capability.\n",
            "## Key capabilities\n\nVerified public capability.\n\nVerified public capability.\n",
            True,
        ),
        (
            "## Key capabilities\n\nVerified public capability.\n",
            "## Key capabilities\n\nVerified public capability with extra scope.\n",
            True,
        ),
        (
            "## Key capabilities\n\nVerified public capability.\n",
            "## Key capabilities\n\nVerified public capability.\n",
            False,
        ),
        (
            "## Key capabilities\n\nStale public capability.\n",
            "## Key capabilities\n\nVerified public capability.\n",
            True,
        ),
    ],
    ids=["ambiguous-duplicate", "partial", "unfacted", "stale"],
)
def test_unproven_candidate_claims_do_not_become_verified_equivalence(
    source: str,
    candidate: str,
    with_fact_provenance: bool,
) -> None:
    _, facts, _, _ = _verified_3d_inputs(include_api_surface=True)
    candidate_claim = assess_material_claims(candidate)[0]
    provenance = (
        [
            CandidateContentProvenanceV1(
                provenance_id="template.section.api_reference",
                candidate_byte_start=candidate_claim.source_byte_start,
                candidate_byte_end=candidate_claim.source_byte_end,
                fact_ids=[facts.selected_fact_ids["api.public_surface"]],
                rationale="Negative-control fact binding.",
            )
        ]
        if with_fact_provenance
        else []
    )

    resolutions = resolve_source_claims(
        source,
        candidate,
        facts,
        provenance,
        fail_on_unresolved_preserve=False,
    )

    assert not any(item.resolution == "verified_equivalence" for item in resolutions)


def test_unproven_leaf_in_required_role_is_removed_but_remains_blocking() -> None:
    source, facts, revision, plan = _verified_3d_inputs()
    candidate = compile_repository_presentation(
        bind_product_facts(
            facts,
            build_verified_template_draft(facts, source, revision, plan),
        )
    )
    contract = load_repository_presentation_template()
    next_heading = f"## {contract.headings['installation']}"
    unsupported_leaf = "Maintainer-specific deployment note with no verified fact."
    mutated = candidate.replace(
        next_heading,
        f"{unsupported_leaf}\n\n{next_heading}",
        1,
    )
    assessment = assess_readme_document(
        facts.org_repo,
        mutated,
        facts,
        base_revision=revision,
    )
    rerun_plan = build_verified_preservation_composition_plan(
        facts.org_repo,
        mutated,
        facts,
        assessment,
        lifecycle_status="FACTS_READY",
    )
    assert rerun_plan is not None
    leaf_claim = next(
        claim
        for claim in assessment.material_claims
        if unsupported_leaf
        in mutated.encode("utf-8")[claim.source_byte_start : claim.source_byte_end].decode("utf-8")
    )
    repaired, document_plan = build_readme_document_candidate(
        facts.org_repo,
        mutated,
        facts,
        base_revision=revision,
        agentic_composition_plan=rerun_plan.model_dump(mode="json"),
    )

    assert unsupported_leaf not in repaired
    placements = document_plan.composition_ledger.source_placements
    assert not any(placement.source_owner_id == leaf_claim.claim_id for placement in placements)
    assert document_plan.claim_accountability is not None
    source_record = next(
        record
        for record in document_plan.claim_accountability.claims
        if record.claim_id == f"source:{leaf_claim.claim_id}"
    )
    assert source_record.currently_accountable is False
    assert source_record.survives_in_candidate is False


def test_preservation_selection_rejects_partial_spoofed_and_stale_coordinates() -> None:
    source, facts, revision, _ = _verified_3d_inputs(include_api_surface=True)
    contract = load_repository_presentation_template()
    exact_body = "- `Scene`, `Node`, `Mesh`\n"
    source = source.rstrip() + f"\n\n## {contract.headings['api_reference']}\n\n" + exact_body
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
    )
    preserve_claim = next(
        claim
        for claim in assessment.material_claims
        if exact_body.strip()
        == source.encode("utf-8")[claim.source_byte_start : claim.source_byte_end]
        .decode("utf-8")
        .strip()
    )
    correction_ranges = [
        (claim.source_byte_start, claim.source_byte_end)
        for claim in assessment.material_claims
        if claim.disposition == "preserve" and claim.claim_id != preserve_claim.claim_id
    ]

    with pytest.raises(ValueError, match="partial, spoofed, or stale"):
        build_verified_source_preservation_selection(
            source,
            assessment,
            fact_authorized_ranges=[
                (preserve_claim.source_byte_start + 1, preserve_claim.source_byte_end)
            ],
            correction_candidate_ranges=correction_ranges,
            resolved_claim_ids=set(),
        )

    selection = build_verified_source_preservation_selection(
        source,
        assessment,
        fact_authorized_ranges=[(preserve_claim.source_byte_start, preserve_claim.source_byte_end)],
        correction_candidate_ranges=correction_ranges,
        resolved_claim_ids=set(),
    )
    with pytest.raises(ValueError, match="stale for source bytes"):
        selection.validate(source + "\n", assessment)


def test_source_build_optional_extras_use_the_local_checkout_target() -> None:
    facts = ProductFactsV2.model_validate(build_review_facts(REVIEW_ARCHETYPES[2]))
    source = FactSourceV2(
        source_type="mechanical_repository",
        location="repository://pyproject.toml",
        source_revision="a" * 40,
    )
    values = {
        "product.identity": {
            "name": "Aspose.Page FOSS for Python",
            "ecosystem": "python",
        },
        "installation.optional_extras": {
            "manifest_path": "pyproject.toml",
            "extras": {"test": ["pytest>=8"]},
        },
        "installation.coordinates": [{"ecosystem": "python", "name": "aspose-page-foss"}],
        "installation.verified_acquisition": {
            "ecosystem": "python",
            "method": "source_build",
            "outcome": "SOURCE_BUILD_VERIFIED",
            "source_build_receipt": {"truth_eligible": True},
            "truth_eligible": True,
        },
    }
    added_records = [
        FactRecordV2(
            fact_id=f"{field}:test",
            field=field,
            value=value,
            source=source,
            verification_state="verified",
            authoritative_owner="repository-owner",
            confidence=1.0,
            affected_surfaces=["readme"],
        )
        for field, value in values.items()
    ]
    added_fields = set(values)
    facts = facts.model_copy(
        update={
            "facts": [
                *[record for record in facts.facts if record.field not in added_fields],
                *added_records,
            ],
            "selected_fact_ids": {
                **facts.selected_fact_ids,
                **{record.field: record.fact_id for record in added_records},
            },
        }
    )

    rendered = optional_extras_markdown(facts)

    assert rendered is not None
    assert 'python -m pip install ".[test]"' in rendered
    assert "aspose-page-foss[test]" not in rendered

    non_python = facts.model_copy(
        update={
            "facts": [
                record.model_copy(update={"value": {**record.value, "ecosystem": "java"}})
                if record.field == "product.identity" and isinstance(record.value, dict)
                else record
                for record in facts.facts
            ]
        }
    )
    assert optional_extras_markdown(non_python) is None

    incomplete_source_build = facts.model_copy(
        update={
            "facts": [
                record.model_copy(
                    update={
                        "value": {
                            "ecosystem": "python",
                            "method": "source_build",
                            "outcome": "SOURCE_BUILD_FAILED",
                            "truth_eligible": False,
                        }
                    }
                )
                if record.field == "installation.verified_acquisition"
                else record
                for record in facts.facts
            ]
        }
    )
    assert optional_extras_markdown(incomplete_source_build) is None

    registry = facts.model_copy(
        update={
            "facts": [
                record.model_copy(
                    update={
                        "value": {
                            "ecosystem": "python",
                            "method": "pypi",
                            "outcome": "REGISTRY_VERIFIED",
                            "coordinate": {"name": "aspose-page-foss"},
                            "registry_receipt": {
                                "coordinate": {"name": "aspose-page-foss"},
                                "found": True,
                            },
                            "truth_eligible": True,
                        }
                    }
                )
                if record.field == "installation.verified_acquisition"
                else record
                for record in facts.facts
            ]
        }
    )
    registry_rendered = optional_extras_markdown(registry)
    assert registry_rendered is not None
    assert 'python -m pip install "aspose-page-foss[test]"' in registry_rendered
    assert 'python -m pip install ".[test]"' not in registry_rendered


def test_repository_enrichment_sections_render_only_selected_accepted_facts() -> None:
    facts = ProductFactsV2.model_validate(build_review_facts(REVIEW_ARCHETYPES[2]))
    source = FactSourceV2(
        source_type="mechanical_repository",
        location="repository://pyproject.toml,SECURITY.md,supported-features.md,scripts/check.sh",
        source_revision="a" * 40,
    )
    values = {
        "python.distribution": {
            "manifest_path": "pyproject.toml",
            "runtime_dependencies": ["cryptography>=42", "asn1crypto>=1.5"],
            "development_status": "Alpha",
            "typed_classifier": True,
            "typed_marker": {"path": "src/acme/py.typed", "sha256": HASH},
        },
        "installation.capability_dependencies": {
            "entries": [
                {
                    "distribution": "fastmcp",
                    "purpose": "MCP server hosting",
                    "install_command": "python -m pip install fastmcp",
                }
            ]
        },
        "development.commands": {
            "entries": [{"kind": "repository_script", "command": "scripts/check.sh"}]
        },
        "repository.documentation_assets": {
            "entries": [{"path": "supported-features.md", "sha256": HASH}]
        },
        "repository.contribution_guidance": {
            "validation_scripts": [{"path": "scripts/check.sh", "sha256": HASH}]
        },
        "repository.security_guidance": {
            "policy": {
                "path": "SECURITY.md",
                "sha256": HASH,
                "private_reporting_url": "https://github.com/acme/pdf/security/advisories/new",
            },
            "resource_limits": {
                "class": "PdfLoadLimits",
                "fields": ["max_input_bytes"],
                "entry_points": ["__init__", "load_from", "open_streaming"],
            },
            "operational_guidance": {
                "lazy_work_uses_shared_limits": True,
                "unlimited_disables_safeguards": True,
                "limits_are_not_a_complete_dos_sandbox": True,
                "isolate_highly_hostile_documents": True,
            },
        },
    }
    additions = [
        FactRecordV2(
            fact_id=f"{field}:test",
            field=field,
            value=value,
            source=source,
            verification_state="verified",
            authoritative_owner="repository-owner",
            confidence=1.0,
            affected_surfaces=["readme"],
        )
        for field, value in values.items()
    ]
    facts = facts.model_copy(
        update={
            "facts": [*facts.facts, *additions],
            "selected_fact_ids": {
                **facts.selected_fact_ids,
                **{fact.field: fact.fact_id for fact in additions},
            },
        }
    )

    assert "cryptography>=42" in (dependency_markdown(facts) or "")
    assert "python -m pip install fastmcp" in (scenario_dependency_markdown(facts) or "")
    assert "**Alpha**" in (package_status_markdown(facts) or "")
    assert "supported-features.md" in (repository_documents_markdown(facts) or "")
    development = development_markdown(facts) or ""
    assert "scripts/check.sh" in development
    for forbidden in (
        "source-bound",
        "validation command",
        "source revision",
        "inventory receipt",
        "verification environment",
        "syntax-checked",
        "not executed",
    ):
        assert forbidden not in development.casefold()
    assert "scripts/check.sh" in (contributing_markdown(facts) or "")
    assert "private vulnerability reporting" in (security_markdown(facts) or "")
    assert "shared resource limits" in (security_markdown(facts) or "")
    assert "unlimited()` disables every safeguard" in (security_markdown(facts) or "")
    assert "not a complete denial-of-service sandbox" in (security_markdown(facts) or "")
    assert "source-defined" not in (security_markdown(facts) or "").casefold()

    blocked = additions[0].model_copy(update={"verification_state": "blocked"})
    blocked_facts = facts.model_copy(
        update={
            "facts": [blocked if item.fact_id == blocked.fact_id else item for item in facts.facts]
        }
    )
    assert "cryptography>=42" not in (dependency_markdown(blocked_facts) or "")


def test_curated_repository_claims_receive_exact_fact_or_structural_provenance() -> None:
    facts = ProductFactsV2.model_validate(build_review_facts(REVIEW_ARCHETYPES[2]))
    source = FactSourceV2(
        source_type="mechanical_repository",
        location="repository://pyproject.toml,SECURITY.md,supported-features.md,scripts",
        source_revision="a" * 40,
    )
    values = {
        "installation.capability_dependencies": {
            "entries": [
                {
                    "distribution": "Pillow",
                    "purpose": "optional image capability",
                    "install_command": "python -m pip install Pillow",
                }
            ]
        },
        "python.distribution": {
            "manifest_path": "pyproject.toml",
            "development_status": "Alpha",
        },
        "development.commands": {
            "entries": [
                {"command": "scripts/build.sh"},
                {"command": "scripts/check.sh"},
            ]
        },
        "repository.documentation_assets": {
            "entries": [{"path": "supported-features.md", "sha256": HASH}]
        },
        "repository.contribution_guidance": {
            "validation_scripts": [{"path": "scripts/check.sh", "sha256": HASH}]
        },
        "repository.security_guidance": {
            "policy": {
                "path": "SECURITY.md",
                "private_reporting_url": "https://github.com/acme/widget/security/advisories/new",
            }
        },
    }
    additions = [
        FactRecordV2(
            fact_id=f"{field}:claim-test",
            field=field,
            value=value,
            source=source,
            verification_state="verified",
            authoritative_owner="repository-owner",
            confidence=1.0,
            affected_surfaces=["readme"],
        )
        for field, value in values.items()
    ]
    added_fields = set(values)
    facts = facts.model_copy(
        update={
            "facts": [
                *[record for record in facts.facts if record.field not in added_fields],
                *additions,
            ],
            "selected_fact_ids": {
                **facts.selected_fact_ids,
                **{fact.field: fact.fact_id for fact in additions},
            },
        }
    )
    fact_ids = {fact.field: fact.fact_id for fact in additions}
    template_input = _page_input_for_facts(facts)
    sections = {
        **template_input.sections,
        "installation": BoundTemplateContentV1(
            markdown="- optional capability: python -m pip install Pillow",
            source_kind="repository_fact",
            fact_ids=[fact_ids["installation.capability_dependencies"]],
        ),
        "scope_and_limitations": BoundTemplateContentV1(
            markdown=(
                "The package status is **Alpha**. See [supported features](supported-features.md)."
            ),
            source_kind="repository_fact",
            fact_ids=[
                fact_ids["python.distribution"],
                fact_ids["repository.documentation_assets"],
            ],
        ),
        "development_and_testing": BoundTemplateContentV1(
            markdown="```bash\nscripts/build.sh\n```\n\n```bash\nscripts/check.sh\n```",
            source_kind="repository_fact",
            fact_ids=[fact_ids["development.commands"]],
        ),
        "contributing": BoundTemplateContentV1(
            markdown=(
                "Validate a proposed change with the checked-in repository scripts:\n\n"
                "- [scripts/check.sh](scripts/check.sh)"
            ),
            source_kind="repository_fact_and_configured_standard",
            fact_ids=[fact_ids["repository.contribution_guidance"]],
            standard_ids=["readme.contributing"],
        ),
        "security": BoundTemplateContentV1(
            markdown=(
                "Review [SECURITY.md](SECURITY.md) and use "
                "[private vulnerability reporting]"
                "(https://github.com/acme/widget/security/advisories/new)."
            ),
            source_kind="repository_fact",
            fact_ids=[fact_ids["repository.security_guidance"]],
        ),
    }
    ordered_sections = {
        slot: sections[slot]
        for slot in load_repository_presentation_template().section_order
        if slot in sections
    }
    template_input = template_input.model_copy(update={"sections": ordered_sections})
    candidate = compile_repository_presentation(template_input)

    provenance = build_template_provenance(candidate, template_input, facts)
    claim_bindings = {
        candidate.encode("utf-8")[binding.candidate_byte_start : binding.candidate_byte_end]
        .decode("utf-8")
        .strip(): binding
        for binding in provenance
        if ".claim:" in binding.provenance_id
    }

    expected_fact_bindings = {
        "- optional capability: python -m pip install Pillow": [
            fact_ids["installation.capability_dependencies"]
        ],
        "```bash\nscripts/build.sh\n```": [fact_ids["development.commands"]],
        "```bash\nscripts/check.sh\n```": [fact_ids["development.commands"]],
        "- [scripts/check.sh](scripts/check.sh)": [fact_ids["repository.contribution_guidance"]],
    }
    for claim, expected_ids in expected_fact_bindings.items():
        assert claim_bindings[claim].fact_ids == expected_ids

    contributing_intro = claim_bindings[
        "Validate a proposed change with the checked-in repository scripts:"
    ]
    assert contributing_intro.fact_ids == []
    assert contributing_intro.configured_standard_ids == ["readme.contributing"]
    assert claim_bindings[
        "The package status is **Alpha**. See [supported features](supported-features.md)."
    ].fact_ids == [
        fact_ids["python.distribution"],
        fact_ids["repository.documentation_assets"],
    ]
    assert claim_bindings[
        "Review [SECURITY.md](SECURITY.md) and use [private vulnerability reporting]"
        "(https://github.com/acme/widget/security/advisories/new)."
    ].fact_ids == [fact_ids["repository.security_guidance"]]


@pytest.mark.parametrize(
    ("line_count", "expected"),
    [(180, "compact"), (181, "standard"), (420, "standard"), (421, "extended")],
)
def test_density_profile_auto_selection(line_count: int, expected: str) -> None:
    assert select_density_profile(line_count) == expected


def test_configured_density_profile_supersedes_auto_selection() -> None:
    assert select_density_profile(10, configured_profile="extended") == "extended"


def _preserved_density_case(title: str, body: str):
    padding = "\n".join(f"source context {index}" for index in range(181)) + "\n\n"
    exact_section = f"## {title}\n\n{body}\n\n"
    policy_source = "Maintainer policy term"
    source = padding + exact_section + policy_source + "\n"
    candidate = (
        "# Product\n\n## Navigation\n\n- [License](#license)\n\n"
        + exact_section
        + "## License\n\n"
        + policy_source
        + "\n"
    )
    source_bytes = source.encode("utf-8")
    candidate_bytes = candidate.encode("utf-8")
    source_start = len(padding.encode("utf-8"))
    candidate_start = candidate_bytes.index(exact_section.encode("utf-8"))
    section_hash = hashlib.sha256(exact_section.encode("utf-8")).hexdigest()
    placement = ExactSourcePlacementV1(
        placement_id="source.section.0000",
        placement_basis="composer_inserted_exact",
        source_owner_id="section:secondary-detail",
        source_byte_start=source_start,
        source_byte_end=source_start + len(exact_section.encode("utf-8")),
        source_content_sha256=section_hash,
        final_byte_start=candidate_start,
        final_byte_end=candidate_start + len(exact_section.encode("utf-8")),
        final_content_sha256=section_hash,
    )
    policy_source_start = source_bytes.index(policy_source.encode("utf-8"), source_start)
    policy_candidate_start = candidate_bytes.index(
        policy_source.encode("utf-8"), placement.final_byte_end
    )
    policy_hash = hashlib.sha256(policy_source.encode("utf-8")).hexdigest()
    provenance = CandidateContentProvenanceV1(
        provenance_id="source.policy.term",
        candidate_byte_start=policy_candidate_start,
        candidate_byte_end=policy_candidate_start + len(policy_source.encode("utf-8")),
        configured_standard_ids=["readme.test_policy"],
        rationale="Exercise density rebasing after one generated policy replacement.",
    )
    correction = SourceClaimPolicyCorrectionV1(
        correction_id="source.policy.term",
        disposition="replace",
        source_byte_start=policy_source_start,
        source_byte_end=policy_source_start + len(policy_source.encode("utf-8")),
        source_content_sha256=policy_hash,
        candidate_byte_start=policy_candidate_start,
        candidate_byte_end=policy_candidate_start + len(policy_source.encode("utf-8")),
        candidate_content_sha256=policy_hash,
        configured_standard_ids=["readme.test_policy"],
        replacement_provenance_id=provenance.provenance_id,
        operation_id="readme.verified-template.compile",
    )
    return source, candidate, exact_section, [provenance], [placement], [correction]


@pytest.mark.parametrize(
    "title",
    ["Additional examples", "API reference"],
)
def test_long_exact_preserved_secondary_slots_use_density_without_losing_lineage(
    title: str,
) -> None:
    body = "\n".join(f"- Exact repository detail {index}" for index in range(12))
    source, candidate, exact_section, provenance, placements, corrections = _preserved_density_case(
        title, body
    )

    result = apply_verified_source_density(
        candidate,
        source,
        provenance,
        placements,
        corrections,
    )
    repeated = apply_verified_source_density(
        candidate,
        source,
        provenance,
        placements,
        corrections,
    )

    assert result == repeated
    assert result.candidate.count("<details>") == 1
    assert result.candidate.count("</details>") == 1
    assert f"<summary>Show {title.casefold()}</summary>" in result.candidate
    source_bytes = source.encode("utf-8")
    candidate_bytes = result.candidate.encode("utf-8")
    exact_fragments = sorted(
        (
            placement
            for placement in result.source_placements
            if placement.source_owner_id == "section:secondary-detail"
        ),
        key=lambda item: item.source_byte_start,
    )
    assert b"".join(
        candidate_bytes[item.final_byte_start : item.final_byte_end] for item in exact_fragments
    ) == exact_section.encode("utf-8")
    assert all(
        candidate_bytes[item.final_byte_start : item.final_byte_end]
        == source_bytes[item.source_byte_start : item.source_byte_end]
        for item in exact_fragments
    )
    wrapper_bindings = [
        binding
        for binding in result.provenance
        if "readme.secondary_detail_density" in binding.configured_standard_ids
    ]
    assert len(wrapper_bindings) == 2
    assert all(
        not any(
            placement.final_byte_start < binding.candidate_byte_end
            and binding.candidate_byte_start < placement.final_byte_end
            for placement in result.source_placements
        )
        for binding in wrapper_bindings
    )
    policy = result.source_policy_corrections[0]
    assert (
        hashlib.sha256(
            candidate_bytes[policy.candidate_byte_start : policy.candidate_byte_end]
        ).hexdigest()
        == policy.candidate_content_sha256
    )
    policy_binding = next(
        binding
        for binding in result.provenance
        if binding.provenance_id == policy.replacement_provenance_id
    )
    assert (policy_binding.candidate_byte_start, policy_binding.candidate_byte_end) == (
        policy.candidate_byte_start,
        policy.candidate_byte_end,
    )


def test_long_exact_preserved_development_slot_remains_visible() -> None:
    body = "\n".join(f"- Exact repository detail {index}" for index in range(12))
    source, candidate, _exact, provenance, placements, corrections = _preserved_density_case(
        "Development and testing", body
    )

    result = apply_verified_source_density(
        candidate,
        source,
        provenance,
        placements,
        corrections,
    )

    assert "<details>" not in result.candidate
    assert "Exact repository detail 11" in result.candidate


@pytest.mark.parametrize(
    ("title", "body"),
    [
        (
            "Development and testing",
            "\n".join(f"- Short detail {index}" for index in range(11)),
        ),
        (
            "API reference",
            "<details>\n<summary>Existing disclosure</summary>\n\n"
            + "\n".join(f"- Existing detail {index}" for index in range(12))
            + "\n\n</details>",
        ),
        (
            "Architecture",
            "\n".join(f"- Non-target detail {index}" for index in range(12)),
        ),
    ],
    ids=["short", "already-collapsed", "non-target"],
)
def test_density_does_not_change_ineligible_preserved_sections(title: str, body: str) -> None:
    source, candidate, _, provenance, placements, corrections = _preserved_density_case(title, body)

    result = apply_verified_source_density(
        candidate,
        source,
        provenance,
        placements,
        corrections,
    )

    assert result.candidate == candidate
    assert result.provenance == provenance
    assert result.source_placements == placements
    assert result.source_policy_corrections == corrections


def test_unverified_development_density_source_is_not_reinserted() -> None:
    source, _, _, _ = _verified_3d_inputs()
    body = "\n".join(f"- Run repository validation workflow `{index}`." for index in range(12))
    source = source.rstrip() + f"\n\n## Development and testing\n\n{body}\n"
    source, facts, revision, plan = _verified_3d_inputs(source)

    candidate, document_plan = build_readme_document_candidate(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
        agentic_composition_plan=plan.model_dump(mode="json"),
    )
    repeated, repeated_plan = build_readme_document_candidate(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
        agentic_composition_plan=plan.model_dump(mode="json"),
    )

    assert candidate == repeated
    assert document_plan.model_dump(mode="json") == repeated_plan.model_dump(mode="json")
    assert "<summary>Show development and testing</summary>" not in candidate
    assert body not in candidate
    lint = lint_readme_presentation(candidate, facts)
    assert not [
        finding for finding in lint.findings if finding.rule_id == "uncollapsed_secondary_detail"
    ]
    source_section = next(
        heading for heading in parse_headings(source) if heading.title == "Development and testing"
    )
    source_start = len(source[: source_section.start].encode("utf-8"))
    source_end = len(source[: source_section.section_end].encode("utf-8"))
    source_bytes = source.encode("utf-8")
    candidate_bytes = candidate.encode("utf-8")
    placements = sorted(
        (
            placement
            for placement in document_plan.composition_ledger.source_placements
            if source_start <= placement.source_byte_start
            and placement.source_byte_end <= source_end
        ),
        key=lambda item: item.source_byte_start,
    )
    assert not placements
    assert source_bytes[source_start:source_end] not in candidate_bytes
    for correction in (
        correction
        for resolution in document_plan.source_claim_resolutions
        for correction in resolution.policy_corrections
    ):
        final = candidate_bytes[correction.candidate_byte_start : correction.candidate_byte_end]
        assert hashlib.sha256(final).hexdigest() == correction.candidate_content_sha256


def _additional_examples_provenance(markdown: str):
    facts = ProductFactsV2.model_validate(build_review_facts(REVIEW_ARCHETYPES[2]))
    template_input = _page_input_for_facts(facts)
    original_sections = dict(template_input.sections)
    original_sections["installation"] = _configured(
        original_sections["installation"].markdown,
        "readme.verified_acquisition",
    )
    original_sections["additional_examples"] = _configured(
        markdown,
        "readme.additional_examples",
    )
    sections = {
        slot: original_sections[slot]
        for slot in load_repository_presentation_template().section_order
        if slot in original_sections
    }
    template_input = template_input.model_copy(update={"profile": "extended", "sections": sections})
    sections = dict(template_input.sections)
    sections["scope_and_limitations"] = sections["scope_and_limitations"].model_copy(
        update={"fact_ids": [facts.selected_fact_ids["product.limitations"]]}
    )
    template_input = template_input.model_copy(update={"sections": sections})
    candidate = compile_repository_presentation(template_input)
    provenance = build_template_provenance(candidate, template_input, facts)
    return candidate, [
        binding
        for binding in provenance
        if binding.provenance_id.startswith("template.section.additional_examples.")
    ]


def test_additional_examples_assurance_is_not_a_standards_only_shell() -> None:
    disclosure = (
        "These additional workflows were syntax-checked and matched to the repository's static "
        "public API. They were not executed by the evidence collector."
    )

    candidate, bindings = _additional_examples_provenance(disclosure)

    assert disclosure in candidate
    assert bindings == []


def test_additional_examples_remove_source_comments_but_preserve_string_literals() -> None:
    facts = ProductFactsV2.model_validate(build_review_facts(REVIEW_ARCHETYPES[2]))
    source = FactSourceV2(
        source_type="mechanical_repository",
        location="repository://README.md",
        source_revision="a" * 40,
    )
    examples = FactRecordV2(
        fact_id="repository.examples:test",
        field="repository.examples",
        value={
            "inline_examples": [
                {
                    "title": "Quick Start",
                    "language": "python",
                    "code": (
                        'url = "https://example.test/value#literal"\n'
                        "svg = barcode.to_svg()  # -> str\n"
                        "png = barcode.to_png()  # -> bytes\n"
                    ),
                    "static_api_verified": True,
                }
            ]
        },
        source=source,
        verification_state="verified",
        authoritative_owner="repository-owner",
        confidence=1.0,
        affected_surfaces=["readme"],
    )
    facts = facts.model_copy(
        update={
            "facts": [*facts.facts, examples],
            "selected_fact_ids": {
                **facts.selected_fact_ids,
                examples.field: examples.fact_id,
            },
        }
    )

    rendered = additional_examples_markdown(facts)

    assert rendered is not None
    assert '"https://example.test/value#literal"' in rendered
    assert "# -> str" not in rendered
    assert "# -> bytes" not in rendered


@pytest.mark.parametrize(
    "unsupported_claim",
    [
        (
            "These additional workflows were runtime-checked and matched to the repository's "
            "public API. They were not executed by the evidence collector."
        ),
        "Aspose.Note FOSS for Python converts every supported file without limitations.",
    ],
)
def test_additional_examples_standard_does_not_cover_variable_claims(
    unsupported_claim: str,
) -> None:
    _candidate, bindings = _additional_examples_provenance(unsupported_claim)

    assert bindings == []


def test_missing_required_slot_fails_closed() -> None:
    template_input = _page_input()
    sections = dict(template_input.sections)
    del sections["installation"]

    with pytest.raises(ValueError, match="missing required slot 'installation'"):
        compile_repository_presentation(template_input.model_copy(update={"sections": sections}))


def test_unaccountable_variable_content_fails_schema() -> None:
    with pytest.raises(ValueError, match="requires fact_ids"):
        BoundTemplateContentV1(markdown="Unsupported prose", source_kind="repository_fact")


def test_product_facts_adapter_uses_the_same_structural_contract() -> None:
    facts = ProductFactsV2.model_validate(build_review_facts(REVIEW_ARCHETYPES[2]))
    include = lambda markdown, *fields: FactFieldTemplateContentV1(  # noqa: E731
        disposition="include",
        markdown=markdown,
        fact_fields=list(fields),
    )
    omit = lambda reason: FactFieldTemplateContentV1(  # noqa: E731
        disposition="omit",
        omission_reason=reason,
    )
    draft = ProductFactsTemplateDraftV1(
        source_revision="golden-set-revision",
        source_line_count=120,
        title=include("AcmePDF Python", "product.identity"),
        badges=include(
            "![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)",
            "product.license",
        ),
        summary=include(
            "AcmePDF Python extracts text from text-based PDF pages.",
            "product.identity",
            "product.capabilities",
        ),
        sections={
            "at_a_glance": include(
                """```mermaid
block-beta
  columns 5
  block:Inputs
    columns 1
    IH["Inputs and Formats"]
    I1["PDF files"]
  end
  PRODUCT["AcmePDF Python"]
  block:Capabilities:2
    columns 2
    C1["Open PDF pages"]:2
    C2["Inspect page content"]:2
    CH["Core Capabilities"]:2
    C3["Extract text"]:2
  end
  block:Outputs
    columns 1
    OH["Outputs"]
    O1["Page text"]
  end
  style IH fill:none,stroke:none,font-weight:bold
  style OH fill:none,stroke:none,font-weight:bold
  I1 --- PRODUCT
  PRODUCT --- CH
  CH --- O1
```""",
                "product.identity",
                "product.formats",
                "product.capabilities",
            ),
            "key_capabilities": include(
                "- **Extract text from PDF pages** - Extract text from text-based PDF pages.",
                "product.capabilities",
            ),
            "installation": include(
                "Install the verified package described by repository evidence.",
                "installation.verified_acquisition",
            ),
            "quick_start": include(
                "Use the verified minimal example from the repository.",
                "example.minimal",
            ),
            "additional_examples": omit("No additional verified examples."),
            "api_reference": omit("No complete API inventory is verified."),
            "documentation_resources": omit("No accepted documentation catalog links."),
            "scope_and_limitations": include(
                "This package does not perform OCR.",
                "product.limitations",
            ),
            "development_and_testing": omit("Not required in the compact profile."),
            "contributing": omit("No separately verified contribution guidance."),
            "security": omit("No separately verified security guidance."),
            "third_party_notices": omit("No notice file was found."),
            "license": include(
                "This project uses the [Apache License](LICENSE), which permits use, "
                "modification, and distribution subject to its terms.",
                "product.license",
            ),
        },
    )

    template_input = bind_product_facts(facts, draft)
    candidate = compile_repository_presentation(template_input)

    assert template_input.title.source_kind == "repository_fact"
    assert template_input.title.fact_ids == ["product.identity:golden"]
    assert "AcmePDF Python" in candidate
    assert validate_repository_presentation(candidate, template_input) == []


def test_product_facts_adapter_rejects_unverified_selected_content() -> None:
    facts = ProductFactsV2.model_validate(build_review_facts(REVIEW_ARCHETYPES[2]))
    identity = facts.selected_fact("product.identity")
    blocked_identity = identity.model_copy(update={"verification_state": "blocked"})
    facts = facts.model_copy(
        update={
            "facts": [
                blocked_identity if fact.fact_id == identity.fact_id else fact
                for fact in facts.facts
            ]
        }
    )
    include = FactFieldTemplateContentV1(
        disposition="include",
        markdown="AcmePDF Python",
        fact_fields=["product.identity"],
    )
    omit = FactFieldTemplateContentV1(
        disposition="omit",
        omission_reason="Not part of this focused negative control.",
    )
    draft = ProductFactsTemplateDraftV1(
        source_revision="golden-set-revision",
        source_line_count=10,
        title=include,
        badges=include,
        summary=include,
        sections={
            slot: omit
            for slot in load_repository_presentation_template().section_order
            if slot != "navigation"
        },
    )

    with pytest.raises(ValueError, match="not an accepted selected fact"):
        bind_product_facts(facts, draft)


def test_note_specific_leakage_is_detectable_in_page_candidate() -> None:
    template_input = _page_input()
    candidate = compile_repository_presentation(template_input)
    leaked = candidate.replace(
        "Inspect XPS document content.",
        "Inspect XPS and Microsoft OneNote content with Aspose.Note FOSS for Python.",
    )

    errors = validate_repository_presentation(leaked, template_input)

    assert "candidate contains cross-product Aspose FOSS identity leakage" in errors


def test_noncanonical_enterprise_product_label_fails_compiled_candidate() -> None:
    template_input = _page_input()
    candidate = compile_repository_presentation(template_input)
    invalid = candidate.replace(
        "Aspose.Page FOSS for Python reads and converts page-description documents.",
        "Aspose.Page FOSS for Python is an alternative to the commercial Aspose.Page product.",
    )

    errors = validate_repository_presentation(invalid, template_input)

    assert "candidate contains noncanonical Aspose Enterprise Edition terminology" in errors


def test_unbound_extra_badge_fails_closed() -> None:
    template_input = _page_input()
    candidate = compile_repository_presentation(template_input)
    invalid = candidate.replace(
        template_input.badges.markdown,
        template_input.badges.markdown
        + " ![Downloads](https://img.shields.io/badge/downloads-unknown-blue)",
    )

    assert (
        "candidate badge row differs from the bound applicable badge set"
        in validate_repository_presentation(invalid, template_input)
    )


def test_comments_emoji_directional_mermaid_and_copyright_fail() -> None:
    template_input = _page_input()
    candidate = compile_repository_presentation(template_input)
    invalid = (
        candidate.replace("block-beta\n", "block-beta\n  PRODUCT --> CH\n")
        + "\n<!-- generated -->\nStatus: 🚀\nCopyright © 2026\n"
    )

    errors = validate_repository_presentation(invalid, template_input)

    assert "Mermaid overview must use only visible undirected relationships" in errors
    assert "candidate contains a visible or code comment" in errors
    assert "candidate contains emoji" in errors
    assert "candidate contains a default copyright declaration" in errors


def test_capability_examples_and_api_style_regressions_fail() -> None:
    template_input = _page_input()
    candidate = compile_repository_presentation(template_input)
    invalid_capabilities = candidate.replace(
        "- **Read XPS documents** - Inspect XPS document content.",
        "- Read XPS documents.",
    )
    assert (
        "Key capabilities must use bold feature names with same-line explanations"
        in validate_repository_presentation(invalid_capabilities, template_input)
    )
    invalid_seo_title = candidate.replace(
        "- **Read XPS documents** - Inspect XPS document content.",
        "- **XPS document support** - Inspect XPS document content.",
    )
    assert "Key capability titles must be action-led search phrases" in (
        validate_repository_presentation(invalid_seo_title, template_input)
    )
    invalid_layout = candidate.replace(
        '    C1["Read document structure"]:2\n',
        '    C1["Read document structure"]\n',
    )
    assert "Mermaid capability nodes must use the adaptive column layout" in (
        validate_repository_presentation(invalid_layout, template_input)
    )

    sections = {
        **template_input.sections,
        "additional_examples": _fact(
            "Expand this section to view examples for inspecting a page.\n\n"
            "<details>\n<summary>View additional examples and results</summary>\n\n"
            "### Inspect a page\n\n```python\nprint('page')\n```\n\n</details>",
            "examples:page",
        ),
        "api_reference": _fact(
            "Two public exports.\n\n<details>\n"
            "<summary>View public API by namespace</summary>\n\n"
            "### `aspose.page`\n\n| Type | Description |\n| --- | --- |\n"
            "| `Document` | Document: load content. |\n"
            "| `Page` | Page: load content. |\n\n</details>",
            "api:page",
        ),
    }
    extended = template_input.model_copy(update={"sections": sections})
    extended_candidate = compile_repository_presentation(extended)
    invalid_examples = extended_candidate.replace(
        "Expand this section to view examples for inspecting a page.",
        "The inline workflows below were checked but not executed.",
    )
    invalid_api = extended_candidate.replace(
        "| `Page` | Page: load content. |",
        "| `Page` | Document: load content. |",
    )

    assert (
        "Additional examples must preview named workflows and use meaningful headings"
        in validate_repository_presentation(invalid_examples, extended)
    )
    assert "candidate exposes internal verification commentary" in validate_repository_presentation(
        invalid_examples, extended
    )
    assert "API reference contains duplicated descriptions" in validate_repository_presentation(
        invalid_api, extended
    )


def test_third_party_notice_link_uses_normal_markdown_link_text() -> None:
    template_input = _page_input()
    sections = {
        **template_input.sections,
        "third_party_notices": _fact(
            "Third-party attribution and dependency license notices are recorded in "
            "[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).",
            "notices:page",
        ),
    }
    extended = template_input.model_copy(update={"sections": sections})
    candidate = compile_repository_presentation(extended)

    assert validate_repository_presentation(candidate, extended) == []
    code_styled = candidate.replace(
        "[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)",
        "[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)",
    )
    assert "Third-party notices link text must use normal link styling" in (
        validate_repository_presentation(code_styled, extended)
    )


def test_cache_key_changes_for_every_correctness_dependency() -> None:
    contract = load_repository_presentation_template()
    baseline = PresentationTemplateDependenciesV1(
        template_version=contract.template_version,
        template_sha256=repository_presentation_template_hash(),
        accepted_reference_sha256=contract.accepted_reference_sha256,
        source_revision="revision-a",
        fact_sha256=HASH,
        prompt_sha256=HASH,
        policy_sha256=HASH,
        validator_version="presentation-template-validator-v1",
        reviewer_standard_sha256=HASH,
        protected_content_sha256=HASH,
    )
    baseline_key = baseline.cache_key()
    fields = (
        "source_revision",
        "template_sha256",
        "fact_sha256",
        "prompt_sha256",
        "policy_sha256",
        "reviewer_standard_sha256",
        "protected_content_sha256",
    )
    for field in fields:
        replacement = "revision-b" if field == "source_revision" else "1" * 64
        assert baseline.model_copy(update={field: replacement}).cache_key() != baseline_key
    changed_version = baseline.model_copy(update={"template_version": "1.0.1"})
    assert changed_version.cache_key() != baseline_key
    changed_validator = baseline.model_copy(update={"validator_version": "validator-v2"})
    assert changed_validator.cache_key() != baseline_key


def test_governed_reference_hash_matches_template_contract() -> None:
    contract = load_repository_presentation_template()
    assert hashlib.sha256(REFERENCE.read_bytes()).hexdigest() == (
        contract.accepted_reference_sha256
    )


def test_blind_visitor_contract_is_derived_from_the_accepted_template() -> None:
    contract = load_repository_presentation_template()
    visitor = build_presentation_visitor_contract(contract)
    standards = {
        item["standard_id"]: item["parameters"] for item in visitor["configured_standards"]
    }

    assert visitor["template_version"] == contract.template_version
    assert standards["readme.header"]["required_h2_prefix"][:2] == [
        "Navigation",
        "At a Glance",
    ]
    assert standards["readme.at_a_glance_mermaid"]["minimum_capabilities"] == 1
    assert standards["readme.at_a_glance_mermaid"]["target_capabilities"] == 6
    assert standards["readme.at_a_glance_mermaid"]["capability_coverage"] == "all_selected_verified"
    assert standards["readme.at_a_glance_mermaid"]["maximum_capabilities_per_group"] == 6
    assert standards["readme.at_a_glance_mermaid"]["target_outputs"] == 5
    assert standards["readme.at_a_glance_mermaid"]["directional_workflow"] is False
    assert (
        standards["readme.at_a_glance_mermaid"]["capability_layout"] == "adaptive_vertical_columns"
    )
    assert standards["readme.at_a_glance_mermaid"]["capability_column_threshold"] == 5
    assert (
        standards["readme.at_a_glance_mermaid"]["topology"] == "inputs-product-capabilities-outputs"
    )
    assert standards["readme.primary_example"] == {
        "heading": "Quick Start",
        "maximum_fenced_blocks": 1,
        "maximum_nonblank_code_lines": 12,
        "secondary_examples": "collapsed_below_primary",
        "secondary_examples_intro": "workflow_preview",
        "public_internal_assurance": "forbidden",
        "duplicate_generic_headings": "forbidden",
    }
    assert standards["readme.badges"]["allowed_badge_kinds"] == [
        "package",
        "platform",
        "license",
        "contributors",
    ]
    assert standards["readme.enterprise_edition_terminology"]["required_section"] == (
        "Scope and Limitations"
    )
    assert standards["readme.no_comments"]["code_comments"] == "forbidden"


def test_primary_example_line_budget_is_language_aware() -> None:
    visitor = build_presentation_visitor_contract(primary_example_language="java")
    standards = {
        item["standard_id"]: item["parameters"] for item in visitor["configured_standards"]
    }

    assert standards["readme.primary_example"]["maximum_nonblank_code_lines"] == 24


def test_blind_visitor_contract_resolves_navigation_to_applicable_candidate_sections() -> None:
    visitor = build_presentation_visitor_contract(
        applicable_h2_headings=[
            "Navigation",
            "At a glance",
            "Key capabilities",
            "Requirements",
            "Feature Boundaries",
            "License",
            "Scope and limitations",
        ]
    )
    standards = {
        item["standard_id"]: item["parameters"] for item in visitor["configured_standards"]
    }

    assert visitor["applicability_basis"] == "validated_candidate_h2_headings"
    assert standards["readme.header"]["required_h2_prefix"] == [
        "Navigation",
        "At a Glance",
        "Key Capabilities",
    ]
    assert standards["readme.navigation"]["required_labels"] == [
        "At a Glance",
        "Key Capabilities",
        "Requirements",
        "Feature Boundaries",
        "License",
        "Scope and Limitations",
    ]
