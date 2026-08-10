"""Prove exact template structure receives narrow configured-standard lineage."""

from __future__ import annotations

import hashlib
from pathlib import Path

from readme_agent.facts.schema_v2 import FactRecordV2, ProductFactsV2
from readme_agent.presentation.template_compiler import compile_repository_presentation
from readme_agent.presentation.template_schema import (
    BoundTemplateContentV1,
    PresentationTemplateInputV1,
)
from readme_agent.presentation.verified_template_api_reference import api_reference_markdown
from readme_agent.presentation.verified_template_capabilities import (
    capability_highlights_markdown,
)
from readme_agent.presentation.verified_template_provenance import build_template_provenance
from readme_agent.presentation.verified_template_sections import (
    additional_examples_markdown,
    development_markdown,
)
from readme_agent.readme.assessment_claims import assess_material_claims
from readme_agent.readme.composition_lineage import build_composition_ledger
from readme_agent.readme.composition_operation_origins import (
    legacy_operation_provenance,
    replay_operation_origins,
)
from readme_agent.readme.diagram_semantic_candidates import (
    output_node_candidates,
    selected_verified_capability_nodes,
)
from readme_agent.readme.document_operations import build_operation
from readme_agent.readme.document_structure import parse_headings
from readme_agent.readme.document_templates import example_text, installation_text
from readme_agent.readme.public_text import (
    canonical_abbreviations_from_facts,
    canonicalize_public_markdown,
)

ROOT = Path(__file__).resolve().parents[2]
FACTS_PATH = (
    ROOT
    / "tests"
    / "fixtures"
    / "readmes"
    / "verified_source_assurance"
    / "aspose-3d-python-facts-ab1a2267.json"
)


def _facts() -> ProductFactsV2:
    facts = ProductFactsV2.model_validate_json(FACTS_PATH.read_text(encoding="utf-8"))
    source = facts.selected_fact("product.identity").source
    api = FactRecordV2(
        fact_id="api.public_surface:structural-lineage-test",
        field="api.public_surface",
        value={
            "modules": [{"module": "aspose.threed", "exports": ["Scene"]}],
            "package_namespaces": ["aspose.threed", "aspose.threed.animation"],
            "classes": [
                {
                    "name": "Scene",
                    "source_path": "aspose/threed/Scene.py",
                    "source_sha256": "a" * 64,
                    "members": [
                        {
                            "name": "open",
                            "kind": "method",
                            "surface": "open(file_or_stream, options=None)",
                            "source_path": "aspose/threed/Scene.py",
                            "source_sha256": "a" * 64,
                        }
                    ],
                }
            ],
        },
        source=source,
        verification_state="verified",
        authoritative_owner="repository-source",
        confidence=1.0,
        affected_surfaces=["readme.api_reference"],
    )
    examples = FactRecordV2(
        fact_id="repository.examples:structural-lineage-test",
        field="repository.examples",
        value={
            "files": [],
            "execution_policy": "inventory_only",
            "inline_examples": [
                {
                    "title": "Inspect a scene",
                    "language": "python",
                    "code": (
                        "from aspose.threed import Scene\n\n"
                        "scene = Scene()\n"
                        'scene.open("model.obj")\n'
                    ),
                    "static_api_verified": True,
                    "execution_verified": False,
                    "evidence_modules": ["aspose.threed"],
                }
            ],
            "result_assets": [],
        },
        source=source,
        verification_state="verified",
        authoritative_owner="repository-source",
        confidence=1.0,
        affected_surfaces=["readme.additional_examples"],
    )
    return facts.model_copy(
        update={
            "facts": [*facts.facts, api, examples],
            "selected_fact_ids": {
                **facts.selected_fact_ids,
                api.field: api.fact_id,
                examples.field: examples.fact_id,
            },
        }
    )


def _bound(
    facts: ProductFactsV2,
    markdown: str,
    *fields: str,
    standards: tuple[str, ...] = (),
) -> BoundTemplateContentV1:
    fact_ids = [facts.selected_fact(field).fact_id for field in fields]
    return BoundTemplateContentV1(
        markdown=canonicalize_public_markdown(markdown, canonical_abbreviations_from_facts(facts)),
        source_kind=("repository_fact_and_configured_standard" if standards else "repository_fact"),
        fact_ids=fact_ids,
        standard_ids=list(standards),
    )


def _template_input(facts: ProductFactsV2) -> PresentationTemplateInputV1:
    revision = facts.selected_fact("product.identity").source.source_revision
    assert revision is not None
    additional = additional_examples_markdown(
        facts,
        reserved_heading_titles=("Aspose.3D FOSS for Python",),
    )
    api = api_reference_markdown(facts)
    development = development_markdown(facts)
    acquisition = installation_text(facts, facts.org_repo, revision)
    assert additional and api and development and acquisition
    return PresentationTemplateInputV1(
        org_repo=facts.org_repo,
        source_revision=revision,
        source_line_count=500,
        title=_bound(
            facts, "Aspose.3D FOSS for Python", "product.identity", standards=("readme.header",)
        ),
        badges=_bound(
            facts,
            "[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)",
            "product.license",
            standards=("readme.badges",),
        ),
        summary=_bound(
            facts, "Aspose.3D FOSS for Python handles verified 3D workflows.", "product.identity"
        ),
        sections={
            "at_a_glance": _bound(
                facts,
                "```mermaid\n"
                "flowchart LR\n"
                "  INPUT[Input] --- PRODUCT[Product]\n"
                "  PRODUCT --- OUTPUT[Output]\n"
                "```",
                "product.identity",
                standards=("readme.at_a_glance_mermaid",),
            ),
            "key_capabilities": _bound(
                facts,
                "- **File format import and export** - Work with OBJ, GLTF, STL, and 3MF.",
                "product.capabilities",
            ),
            "installation": _bound(
                facts,
                acquisition,
                "installation.coordinates",
                "installation.verified_acquisition",
                standards=("readme.verified_acquisition",),
            ),
            "quick_start": _bound(
                facts,
                "```python\nfrom aspose.threed import Scene\n\nscene = Scene()\n```",
                "example.minimal",
                standards=("readme.primary_example",),
            ),
            "additional_examples": _bound(
                facts,
                additional,
                "repository.examples",
                standards=("readme.additional_examples",),
            ),
            "api_reference": _bound(
                facts,
                api,
                "api.public_surface",
                standards=("readme.api_reference",),
            ),
            "scope_and_limitations": _bound(
                facts,
                "Only repository-verified capabilities are presented.",
                "product.identity",
                standards=("readme.enterprise_edition_terminology",),
            ),
            "development_and_testing": _bound(
                facts,
                development,
                "development.assets",
                standards=("readme.development_and_testing",),
            ),
            "license": _bound(
                facts,
                "This project is licensed under the MIT License.",
                "product.license",
                standards=("readme.license",),
            ),
        },
    )


def test_api_reference_is_one_type_description_table_per_namespace() -> None:
    api = api_reference_markdown(_facts())

    assert api is not None
    assert "<summary>View public API by namespace</summary>" in api
    assert api.count("### Aspose.3D Namespace (`aspose.threed`)") == 1
    assert api.count("| Type | Description |") == 1
    assert (
        "| `Scene` | Represents a Scene in the public threed API for Aspose.3D. "
        "Supports opening content. |"
    ) in api
    assert "`aspose.threed.animation`" in api
    assert "\n- `Scene`" not in api


def test_api_reference_preserves_identifier_and_humanizes_namespace_heading() -> None:
    facts = _facts()
    api_fact = facts.selected_fact("api.public_surface")
    replacement = api_fact.model_copy(
        update={
            "value": {
                "modules": [
                    {"module": "aspose.threed.pdf_writer", "exports": ["Scene"]},
                    {"module": "aspose.threed.A3DObject", "exports": ["Scene"]},
                ],
                "classes": [
                    {"module": "aspose.threed.pdf_writer", "name": "Scene", "members": []},
                ],
            }
        }
    )
    facts = facts.model_copy(
        update={
            "facts": [
                replacement if fact.fact_id == api_fact.fact_id else fact for fact in facts.facts
            ]
        }
    )

    api = api_reference_markdown(facts)

    assert api is not None
    assert "### Aspose.3D.PDF Writer Namespace (`aspose.threed.pdf_writer`)" in api
    assert "### Aspose.3D.A3DObject Namespace (`aspose.threed.A3DObject`)" in api


def test_api_reference_humanizes_underscore_root_without_repeating_product_family() -> None:
    facts = _facts()
    identity = facts.selected_fact("product.identity")
    api_fact = facts.selected_fact("api.public_surface")
    replacements = {
        identity.fact_id: identity.model_copy(
            update={"value": {**identity.value, "family": "PDF"}}
        ),
        api_fact.fact_id: api_fact.model_copy(
            update={
                "value": {
                    "modules": [
                        {
                            "module": "aspose_pdf.annotations",
                            "exports": ["PdfPlugin"],
                        }
                    ],
                    "classes": [
                        {
                            "module": "aspose_pdf.annotations",
                            "name": "PdfPlugin",
                            "members": [{"name": "process", "kind": "method"}],
                        }
                    ],
                }
            }
        ),
    }
    facts = facts.model_copy(
        update={"facts": [replacements.get(fact.fact_id, fact) for fact in facts.facts]}
    )

    api = api_reference_markdown(facts)

    assert api is not None
    assert "### Aspose.PDF.Annotations Namespace (`aspose_pdf.annotations`)" in api
    assert "Aspose PDF.PDF" not in api
    assert (
        "Represents a PDF Plugin in the public annotations API for Aspose.PDF. "
        "Supports processing documents."
    ) in api


def test_function_only_namespace_is_not_mislabeled_as_a_type_table() -> None:
    facts = _facts()
    api_fact = facts.selected_fact("api.public_surface")
    replacement = api_fact.model_copy(
        update={
            "value": {
                "modules": [
                    {"module": "aspose.page.mcp", "exports": ["create_server", "run"]},
                    {
                        "module": "aspose.page.mcp.server",
                        "exports": ["create_server", "run"],
                    },
                ],
                "classes": [],
            }
        }
    )
    facts = facts.model_copy(
        update={
            "facts": [
                replacement if fact.fact_id == api_fact.fact_id else fact for fact in facts.facts
            ]
        }
    )

    api = api_reference_markdown(facts)

    assert api is None


def test_capabilities_use_bold_features_with_same_line_explanations() -> None:
    capabilities = capability_highlights_markdown(_facts())

    assert capabilities is not None
    assert all(
        line.startswith("- **") and "** - " in line and line.endswith(".")
        for line in capabilities.splitlines()
    )
    assert "**Import and export OBJ, GLTF, STL, and 3MF files**" in capabilities
    assert "Convert GLTF - GL Transmission Format (glTF 2.0) files to GLTF" not in capabilities
    assert "Exchange content across the listed supported file formats" in capabilities
    assert "Build reusable scene geometry from the listed primitive types" in capabilities
    assert "Animate scene properties with time-based keyframe data" in capabilities


def test_diagram_derives_every_explicit_import_export_output_without_dangling_text() -> None:
    facts = _facts()

    assert {node.label for node in output_node_candidates(facts)} >= {
        "OBJ files",
        "GLTF files",
        "STL files",
        "3MF files",
    }
    assert all(
        not node.label.endswith((",", ";", ":", "-"))
        for node in selected_verified_capability_nodes(facts)
    )


def test_additional_examples_preview_public_workflows_without_internal_assurance() -> None:
    examples = additional_examples_markdown(_facts())

    assert examples is not None
    assert examples.startswith("Expand this section to view examples for ")
    assert "| Example source | Verification |" not in examples
    assert "source revision" not in examples
    assert "not executed" not in examples
    assert "The inline workflows below" not in examples


def _covered_heading_titles(
    candidate: str,
    provenance,
) -> set[tuple[int, str]]:
    covered = set()
    for heading in parse_headings(candidate):
        if heading.level not in {2, 3}:
            continue
        start = len(candidate[: heading.start].encode("utf-8"))
        visible = f"{'#' * heading.level} {heading.title}"
        end = start + len(visible.encode("utf-8"))
        if any(
            binding.configured_standard_ids
            and binding.candidate_byte_start <= start
            and end <= binding.candidate_byte_end
            for binding in provenance
        ):
            covered.add((heading.level, heading.title))
    return covered


def test_canonical_compiler_h2_and_fact_renderer_h3_have_exact_lineage() -> None:
    facts = _facts()
    template_input = _template_input(facts)
    candidate = compile_repository_presentation(template_input)
    provenance = build_template_provenance(candidate, template_input, facts)

    expected = {
        (heading.level, heading.title)
        for heading in parse_headings(candidate)
        if heading.level in {2, 3}
    }

    assert _covered_heading_titles(candidate, provenance) == expected
    assert any(
        item.provenance_id.startswith("template.structure.h3.additional_examples")
        for item in provenance
    )
    assert any(
        item.provenance_id.startswith("template.structure.h3.api_reference") for item in provenance
    )
    assert any(
        item.provenance_id.startswith("template.structure.h3.development_and_testing")
        for item in provenance
    )
    api_heading = next(
        heading for heading in parse_headings(candidate) if heading.title == "API Reference"
    )
    api_start = len(candidate[: api_heading.start].encode("utf-8"))
    api_end = len(candidate[: api_heading.section_end].encode("utf-8"))
    api_fact_id = facts.selected_fact_ids["api.public_surface"]
    api_claims = [
        claim
        for claim in assess_material_claims(candidate)
        if api_start <= claim.source_byte_start
        and claim.source_byte_end <= api_end
        and candidate.encode("utf-8")[claim.source_byte_start : claim.source_byte_end]
        .decode("utf-8")
        .startswith("| Type | Description |")
    ]
    assert api_claims
    assert all(
        any(
            binding.candidate_byte_start <= claim.source_byte_start
            and claim.source_byte_end <= binding.candidate_byte_end
            and (api_fact_id in binding.fact_ids or bool(binding.configured_standard_ids))
            for binding in provenance
        )
        for claim in api_claims
    )
    source = b"# Legacy\n"
    operation = build_operation(
        operation_id="readme.verified-template.compile",
        operation="replace",
        source=source,
        start=0,
        end=len(source),
        replacement=candidate,
        fact_ids=[],
        treatment="presentation_policy_correction",
        rationale="Exercise exact generated structural lineage.",
    )
    replay = replay_operation_origins(source, [operation])
    ledger = build_composition_ledger(
        source.decode(),
        candidate,
        [operation],
        [*provenance, *legacy_operation_provenance(replay)],
    )
    assert not any(
        segment.authority == "unbound"
        and (segment.content_text.lstrip().startswith("#") or not segment.content_text.strip())
        for segment in ledger.segments
    )


def test_modified_fact_section_cannot_inherit_canonical_h3_authority() -> None:
    facts = _facts()
    template_input = _template_input(facts)
    api = template_input.sections["api_reference"]
    spoofed = api.model_copy(
        update={
            "markdown": api.markdown + "\n\n### Fabricated benchmark\n\nOne million operations."
        }
    )
    template_input = template_input.model_copy(
        update={"sections": {**template_input.sections, "api_reference": spoofed}}
    )
    candidate = compile_repository_presentation(template_input)
    provenance = build_template_provenance(candidate, template_input, facts)
    spoof = next(
        heading for heading in parse_headings(candidate) if heading.title == "Fabricated benchmark"
    )
    start = len(candidate[: spoof.start].encode("utf-8"))
    end = start + len(f"### {spoof.title}".encode())

    assert not any(
        item.candidate_byte_start <= start
        and end <= item.candidate_byte_end
        and item.configured_standard_ids
        for item in provenance
    )
    assert not any(
        item.provenance_id.startswith("template.structure.h3.api_reference") for item in provenance
    )


def test_verified_input_fixture_does_not_add_generated_narration() -> None:
    facts = _facts()
    example = facts.selected_fact("example.minimal")
    value = dict(example.value)
    value["input_fixture_bindings"] = [
        {
            "source_path": "testfiles/scene.obj",
            "target_path": "testfiles/scene.obj",
        }
    ]
    replacement = example.model_copy(update={"value": value})
    facts = facts.model_copy(
        update={
            "facts": [
                replacement if item.fact_id == example.fact_id else item for item in facts.facts
            ]
        }
    )
    revision = facts.selected_fact("product.identity").source.source_revision
    assert revision is not None
    template_input = _template_input(facts)
    template_input = template_input.model_copy(
        update={
            "sections": {
                **template_input.sections,
                "quick_start": _bound(
                    facts,
                    example_text(facts, revision),
                    "example.minimal",
                    standards=("readme.primary_example",),
                ),
            }
        }
    )
    candidate = compile_repository_presentation(template_input)
    provenance = build_template_provenance(candidate, template_input, facts)
    assert "verification used the repository fixture" not in candidate
    assert any(
        item.provenance_id.startswith("template.section.quick_start")
        and example.fact_id in item.fact_ids
        for item in provenance
    )


def test_readme_inherited_variable_h3_remains_unbound() -> None:
    facts = _facts()
    template_input = _template_input(facts)
    inherited_markdown = "### Maintainer benchmark\n\nFastest in every workload."
    inherited = BoundTemplateContentV1(
        markdown=inherited_markdown,
        source_kind="readme_inherited",
        source_sha256=hashlib.sha256(inherited_markdown.encode("utf-8")).hexdigest(),
    )
    template_input = template_input.model_copy(
        update={"sections": {**template_input.sections, "api_reference": inherited}}
    )
    candidate = compile_repository_presentation(template_input)
    provenance = build_template_provenance(candidate, template_input, facts)
    heading = next(
        heading for heading in parse_headings(candidate) if heading.title == "Maintainer benchmark"
    )
    start = len(candidate[: heading.start].encode("utf-8"))
    end = start + len(f"### {heading.title}".encode())

    assert not any(
        item.candidate_byte_start <= start
        and end <= item.candidate_byte_end
        and item.configured_standard_ids
        for item in provenance
    )
