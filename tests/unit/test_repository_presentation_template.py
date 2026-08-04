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
from readme_agent.presentation.verified_template_draft import build_verified_template_draft
from readme_agent.presentation.verified_template_provenance import build_template_provenance
from readme_agent.presentation.verified_template_sections import (
    additional_examples_markdown,
    contributing_markdown,
    dependency_markdown,
    development_markdown,
    optional_extras_markdown,
    package_status_markdown,
    repository_documents_markdown,
    security_markdown,
)
from readme_agent.presentation.visitor_contract import build_presentation_visitor_contract
from readme_agent.readme.agentic_composition_models import ReadmeAgenticCompositionPlanV1
from readme_agent.readme.document_templates import installation_text
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
flowchart LR
  subgraph Inputs["Inputs and formats"]
    I1["XPS documents"]
  end
  PRODUCT["Aspose.Page FOSS for Python"]
  subgraph Capabilities["Core capabilities"]
    C1["Read document structure"]
    C2["Inspect pages and resources"]
    C3["Convert supported content"]
  end
  subgraph Outputs["Outputs and accessible content"]
    O1["Structured page data"]
  end
  I1 --- PRODUCT
  PRODUCT --- C1
  PRODUCT --- C2
  PRODUCT --- C3
  C1 --- O1
```""",
                "identity:page",
                "formats:page",
                "capabilities:page",
            ),
            "key_capabilities": _fact(
                "- Read XPS documents.\n- Inspect pages.\n- Convert supported content.",
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


def test_accepted_note_reference_reconstructs_byte_for_byte() -> None:
    markdown = REFERENCE.read_text(encoding="utf-8")
    template_input = adopt_accepted_reference(
        markdown,
        org_repo="aspose-note-foss/Aspose.Note-FOSS-for-Python",
        source_revision="6d97a522a9ed24708687911f1aabb76e2dea2da7",
    )

    candidate = compile_repository_presentation(template_input)

    assert candidate == markdown
    assert validate_repository_presentation(candidate, template_input) == []


def test_compact_page_profile_is_product_specific_and_valid() -> None:
    template_input = _page_input()

    candidate = compile_repository_presentation(template_input)

    assert select_density_profile(template_input.source_line_count) == "compact"
    assert "Aspose.Page FOSS for Python" in candidate
    assert "Aspose.Note" not in candidate
    assert ".one" not in candidate
    assert validate_repository_presentation(candidate, template_input) == []


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
        if item.provenance_id == "template.section.installation.verified_acquisition"
    )
    bound = candidate.encode("utf-8")[
        binding.candidate_byte_start : binding.candidate_byte_end
    ].decode("utf-8")
    assert bound == installation_text(facts, facts.org_repo, "a" * 40)
    assert {facts.fact_by_id(fact_id).field for fact_id in binding.fact_ids} == {
        "installation.coordinates",
        "installation.verified_acquisition",
    }


def test_source_build_optional_extras_use_the_local_checkout_target() -> None:
    facts = ProductFactsV2.model_validate(build_review_facts(REVIEW_ARCHETYPES[2]))
    source = FactSourceV2(
        source_type="mechanical_repository",
        location="repository://pyproject.toml",
        source_revision="a" * 40,
    )
    values = {
        "installation.optional_extras": {
            "manifest_path": "pyproject.toml",
            "extras": {"test": ["pytest>=8"]},
        },
        "installation.coordinates": [{"name": "aspose-page-foss"}],
        "installation.verified_acquisition": {"method": "source_build"},
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
    assert "python -m pip install fastmcp" in (dependency_markdown(facts) or "")
    assert "**Alpha**" in (package_status_markdown(facts) or "")
    assert "supported-features.md" in (repository_documents_markdown(facts) or "")
    development = development_markdown(facts) or ""
    assert "scripts/check.sh" in development
    assert "1 source-bound validation command" in development
    assert "1 source-bound validation commands" not in development
    assert "scripts/check.sh" in (contributing_markdown(facts) or "")
    assert "private vulnerability reporting" in (security_markdown(facts) or "")
    assert "shared resource limits" in (security_markdown(facts) or "")
    assert "unlimited()` disables every safeguard" in (security_markdown(facts) or "")
    assert "not a complete denial-of-service sandbox" in (security_markdown(facts) or "")

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
    template_input = _page_input()
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


def _additional_examples_provenance(markdown: str):
    template_input = _page_input()
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
    facts = ProductFactsV2.model_validate(build_review_facts(REVIEW_ARCHETYPES[2]))
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
flowchart LR
  subgraph Inputs["Inputs and formats"]
    I1["PDF files"]
  end
  PRODUCT["AcmePDF Python"]
  subgraph Capabilities["Core capabilities"]
    C1["Open PDF pages"]
    C2["Inspect page content"]
    C3["Extract text"]
  end
  subgraph Outputs["Outputs and accessible content"]
    O1["Page text"]
  end
  I1 --- PRODUCT
  PRODUCT --- C1
  PRODUCT --- C2
  PRODUCT --- C3
  C3 --- O1
```""",
                "product.identity",
                "product.formats",
                "product.capabilities",
            ),
            "key_capabilities": include(
                "- Extract text from text-based PDF pages.",
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
        "Read XPS documents.",
        "Read XPS documents and Microsoft OneNote .one files with Aspose.Note FOSS for Python.",
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
        candidate.replace("I1 --- PRODUCT", "I1 --> PRODUCT")
        + "\n<!-- generated -->\nStatus: 🚀\nCopyright © 2026\n"
    )

    errors = validate_repository_presentation(invalid, template_input)

    assert "Mermaid overview must not imply a mandatory directional workflow" in errors
    assert "candidate contains a visible or code comment" in errors
    assert "candidate contains emoji" in errors
    assert "candidate contains a default copyright declaration" in errors


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
        "At a glance",
    ]
    assert standards["readme.at_a_glance_mermaid"]["minimum_capabilities"] == 1
    assert standards["readme.at_a_glance_mermaid"]["target_capabilities"] == 6
    assert standards["readme.at_a_glance_mermaid"]["capability_coverage"] == "all_selected_verified"
    assert standards["readme.at_a_glance_mermaid"]["maximum_capabilities_per_group"] == 6
    assert standards["readme.at_a_glance_mermaid"]["target_outputs"] == 5
    assert standards["readme.at_a_glance_mermaid"]["directional_workflow"] is False
    assert standards["readme.primary_example"] == {
        "heading": "Quick start",
        "maximum_fenced_blocks": 1,
        "maximum_nonblank_code_lines": 12,
        "secondary_examples": "collapsed_below_primary",
    }
    assert standards["readme.badges"]["allowed_badge_kinds"] == [
        "package",
        "platform",
        "license",
        "contributors",
    ]
    assert standards["readme.enterprise_edition_terminology"]["required_section"] == (
        "Scope and limitations"
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
        "At a glance",
        "Key capabilities",
    ]
    assert standards["readme.navigation"]["required_labels"] == [
        "At a glance",
        "Key capabilities",
        "Requirements",
        "Feature Boundaries",
        "License",
        "Scope and limitations",
    ]
