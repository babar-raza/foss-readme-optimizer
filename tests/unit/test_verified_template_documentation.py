"""Verified documentation-resource slot tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from readme_agent.facts.schema_v2 import FactRecordV2, FactSourceV2, ProductFactsV2
from readme_agent.presentation.template_adapters import bind_product_facts
from readme_agent.presentation.template_compiler import compile_repository_presentation
from readme_agent.presentation.verified_template_documentation import (
    documentation_resources_markdown,
)
from readme_agent.presentation.verified_template_draft import build_verified_template_draft
from readme_agent.presentation.verified_template_provenance import build_template_provenance
from readme_agent.readme.assessment import assess_readme_document
from readme_agent.readme.fact_grounding import literal_fact_ids
from readme_agent.readme.verified_preservation_composition import (
    build_verified_preservation_composition_plan,
)

ROOT = Path(__file__).resolve().parents[2]
REVISION = "ab1a2267a0ba6302311d0c7c4ad01494974c7d76"
FACT_ID = "documentation.links:governed-aspose-org-catalog"


def _base_facts() -> ProductFactsV2:
    return ProductFactsV2.model_validate_json(
        (
            ROOT
            / "tests"
            / "fixtures"
            / "readmes"
            / "verified_source_assurance"
            / "aspose-3d-python-facts-ab1a2267.json"
        ).read_text(encoding="utf-8")
    )


def _catalog_rows() -> list[dict[str, object]]:
    common = {
        "title": "Aspose.3D-FOSS-for-Python",
        "family": "3d",
        "platform": "python",
        "product": "Aspose.3D-FOSS-for-Python",
        "source_revision_or_hash": "catalog-revision",
    }
    return [
        {
            **common,
            "surface": "reference",
            "url": "https://reference.aspose.org/3d/python/",
            "record_id": "org:reference:3d:python:1",
            "source_location": "content/reference.aspose.org/3d/python/_index.md",
        },
        {
            **common,
            "surface": "docs",
            "url": "https://docs.aspose.org/3d/python/",
            "record_id": "org:docs:3d:python:1",
            "source_location": "content/docs.aspose.org/en/3d/python/_index.md",
        },
        {
            **common,
            "surface": "kb",
            "url": "https://kb.aspose.org/3d/python/",
            "record_id": "org:kb:3d:python:1",
            "source_location": "content/kb.aspose.org/3d/python/_index.md",
        },
        {
            **common,
            "surface": "blog",
            "url": "https://blog.aspose.org/3d/example/",
            "record_id": "org:blog:3d:python:1",
            "source_location": "content/blog.aspose.org/3d/example.md",
        },
    ]


def _with_documentation_fact(
    *,
    value: object | None = None,
    verification_state: str = "verified",
    source_type: str = "external_registry",
    source_location: str = "data/aspose_org_links.json",
) -> ProductFactsV2:
    facts = _base_facts()
    payload = facts.model_dump(mode="json")
    payload["facts"] = [item for item in payload["facts"] if item["field"] != "documentation.links"]
    payload["facts"].append(
        FactRecordV2(
            fact_id=FACT_ID,
            field="documentation.links",
            value=_catalog_rows() if value is None else value,
            source=FactSourceV2(
                source_type=source_type,
                location=source_location,
                source_revision=REVISION,
            ),
            verification_state=verification_state,
            authoritative_owner="documentation-catalog-owner",
            confidence=1.0,
            affected_surfaces=["readme.documentation_resources"],
        ).model_dump(mode="json")
    )
    payload["selected_fact_ids"] = {
        **payload["selected_fact_ids"],
        "documentation.links": FACT_ID,
    }
    return ProductFactsV2.model_validate(payload)


def test_documentation_resources_render_selected_catalog_rows_in_stable_order() -> None:
    markdown = documentation_resources_markdown(_with_documentation_fact())

    assert markdown == "\n".join(
        (
            "- **[Getting started guide](https://docs.aspose.org/3d/python/)** - installation, "
            "walkthroughs, and feature guides for this library.",
            "- **[How-to guides and FAQ](https://kb.aspose.org/3d/python/)** - task-focused "
            "answers for common product questions.",
            "- **[Full API reference](https://reference.aspose.org/3d/python/)** - the complete "
            "browsable reference for the public API.",
            "- Found a bug or have a feature request? "
            "[Open an issue](https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Python/issues) "
            "on GitHub.",
        )
    )

    assert documentation_resources_markdown(_with_documentation_fact(), link_limit=2) == "\n".join(
        (
            "- **[Getting started guide](https://docs.aspose.org/3d/python/)** - installation, "
            "walkthroughs, and feature guides for this library.",
            "- **[How-to guides and FAQ](https://kb.aspose.org/3d/python/)** - task-focused "
            "answers for common product questions.",
            "- Found a bug or have a feature request? "
            "[Open an issue](https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Python/issues) "
            "on GitHub.",
        )
    )
    assert "blog.aspose.org" not in markdown


@pytest.mark.parametrize(
    "facts",
    [
        _base_facts(),
        _with_documentation_fact(verification_state="unverified"),
        _with_documentation_fact(source_type="approved_policy"),
        _with_documentation_fact(source_location="policy://documentation-links"),
        _with_documentation_fact(
            value=[
                {
                    "surface": "docs",
                    "url": "https://example.invalid/invented/",
                }
            ]
        ),
    ],
    ids=("legacy-policy", "unverified", "non-catalog-source", "wrong-catalog", "malformed-row"),
)
def test_documentation_resources_omit_unavailable_or_unaccepted_evidence(
    facts: ProductFactsV2,
) -> None:
    assert documentation_resources_markdown(facts) is None


def test_verified_draft_and_candidate_bind_exact_documentation_fact() -> None:
    facts = _with_documentation_fact()
    source = (
        ROOT / "tests" / "fixtures" / "readmes" / "real_audit_2026-07-17" / "3d-python.md"
    ).read_text(encoding="utf-8")
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision=REVISION,
    )
    agentic_plan = build_verified_preservation_composition_plan(
        facts.org_repo,
        source,
        facts,
        assessment,
        lifecycle_status="FACTS_READY",
    )
    assert agentic_plan is not None

    draft = build_verified_template_draft(facts, source, REVISION, agentic_plan)
    documentation = draft.sections["documentation_resources"]
    assert documentation.disposition == "include"
    assert documentation.fact_fields == ["documentation.links", "product.identity"]
    assert documentation.standard_ids == ["readme.documentation_resources"]

    template_input = bind_product_facts(facts, draft)
    bound = template_input.sections["documentation_resources"]
    assert bound.fact_ids == [FACT_ID, "product.identity:manifest-and-registry"]
    candidate = compile_repository_presentation(template_input)
    assert "## Documentation and Resources" in candidate
    assert "blog.aspose.org" not in candidate
    provenance = build_template_provenance(candidate, template_input, facts)
    exact = next(
        binding
        for binding in provenance
        if binding.provenance_id == "template.section.documentation_resources"
    )
    assert exact.fact_ids == [FACT_ID, "product.identity:manifest-and-registry"]
    assert (
        candidate.encode("utf-8")[exact.candidate_byte_start : exact.candidate_byte_end].decode(
            "utf-8"
        )
        == bound.markdown
    )
    lines = bound.markdown.splitlines()
    for line in lines[:3]:
        assert literal_fact_ids(line, facts, [FACT_ID]) == [FACT_ID]
    assert "Aspose.3D-FOSS-for-Python/issues" in lines[3]
    assert exact.configured_standard_ids == ["readme.documentation_resources"]
