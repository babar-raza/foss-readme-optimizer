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
from readme_agent.presentation.verified_template_provenance import build_template_provenance
from readme_agent.presentation.verified_template_sections import optional_extras_markdown
from readme_agent.presentation.visitor_contract import build_presentation_visitor_contract
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
    candidate = compile_repository_presentation(template_input)
    facts = ProductFactsV2.model_validate(build_review_facts(REVIEW_ARCHETYPES[2]))
    provenance = build_template_provenance(candidate, template_input, facts)
    return candidate, [
        binding
        for binding in provenance
        if binding.provenance_id.startswith("template.section.additional_examples.")
    ]


def test_additional_examples_execution_disclosure_has_exact_standard_provenance() -> None:
    disclosure = (
        "These additional workflows were syntax-checked and matched to the repository's static "
        "public API. They were not executed by the evidence collector."
    )

    candidate, bindings = _additional_examples_provenance(disclosure)

    assert len(bindings) == 1
    binding = bindings[0]
    bound_text = candidate.encode("utf-8")[
        binding.candidate_byte_start : binding.candidate_byte_end
    ].decode("utf-8")
    assert bound_text == disclosure
    assert binding.fact_ids == []
    assert binding.configured_standard_ids == ["readme.additional_examples"]


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
