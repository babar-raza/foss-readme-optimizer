"""Prove complete source-claim fact binding before preservation."""

from __future__ import annotations

import pytest

import readme_agent.presentation.verified_template_capabilities as capabilities_module
from readme_agent.facts.schema_v2 import FactRecordV2, ProductFactsV2
from readme_agent.golden_set.review_fixtures import REVIEW_ARCHETYPES, build_review_facts
from readme_agent.presentation.verified_source_claim_matching import (
    _coordinates_cover,
    equivalent_source_claim_resolution,
    fact_bound_capability_candidate_claims,
    index_equivalent_candidate_claims,
)
from readme_agent.presentation.verified_source_claim_resolutions import (
    build_source_claim_resolutions,
)
from readme_agent.presentation.verified_template_capabilities import (
    capability_claim_fact_coordinates,
    capability_claim_fact_ids,
    capability_highlights_markdown,
)
from readme_agent.readme.assessment import assess_readme_document
from readme_agent.readme.assessment_claims import assess_material_claims
from readme_agent.readme.claim_accountability_api_coordinates import (
    api_class_fact_coordinates,
)
from readme_agent.readme.claim_accountability_coordinates import (
    literal_list_fact_coordinates,
    structured_list_item_coordinate,
)
from readme_agent.readme.document_plan import CandidateContentProvenanceV1
from readme_agent.readme.source_claim_assurance import build_source_claim_assurance
from readme_agent.readme.source_claim_fact_binding import (
    CompleteSourceClaimFactBindingV1,
    accepted_source_claim_fact_ids,
    complete_source_claim_fact_binding,
)


def _class(name: str, *surfaces: str) -> dict:
    return {
        "name": name,
        "source_path": f"package/{name}.py",
        "source_sha256": "a" * 64,
        "members": [
            {
                "name": surface.split("(", 1)[0].split(":", 1)[0],
                "surface": surface,
                "source_path": f"package/{name}.py",
                "source_sha256": "a" * 64,
            }
            for surface in surfaces
        ],
    }


def _facts() -> ProductFactsV2:
    facts = ProductFactsV2.model_validate(build_review_facts(REVIEW_ARCHETYPES[2]))
    identity = facts.selected_fact("product.identity")
    api = FactRecordV2(
        fact_id="api.public_surface:source-assurance-test",
        field="api.public_surface",
        verification_state="verified",
        value={
            "classes": [
                _class(
                    "Matrix4",
                    "translate(tx, ty=None, tz=None)",
                    "inverse()",
                ),
                _class("Material", "get_texture(slot_name)"),
            ],
            "modules": [],
        },
        source=identity.source,
        authoritative_owner="repository-source",
        confidence=1.0,
        affected_surfaces=["readme"],
    )
    capabilities = facts.selected_fact("product.capabilities")
    replacements = {
        capabilities.fact_id: capabilities.model_copy(
            update={
                "verification_state": "verified",
                "value": ["Build verified meshes"],
            }
        ),
    }
    return facts.model_copy(
        update={
            "facts": [
                *[replacements.get(fact.fact_id, fact) for fact in facts.facts],
                api,
            ],
            "selected_fact_ids": {
                **facts.selected_fact_ids,
                "api.public_surface": api.fact_id,
            },
        }
    )


def _page_mcp_facts() -> ProductFactsV2:
    facts = _facts()
    identity = facts.selected_fact("product.identity")
    identity = identity.model_copy(
        update={
            "value": {
                "family": "page",
                "platform": "python",
                "ecosystem": "python",
                "repository": facts.org_repo,
                "product_name": "Aspose.Page",
            }
        }
    )
    capabilities = facts.selected_fact("product.capabilities").model_copy(
        update={
            "value": [
                "PS/EPS to PDF conversion",
                "PS/EPS to image conversion",
                "XPS to PDF conversion",
                "XPS to image conversion",
                "MCP server hosting",
            ]
        }
    )
    api = facts.selected_fact("api.public_surface").model_copy(
        update={
            "value": {
                "modules": [
                    {
                        "module": "aspose.page.image.encoders",
                        "exports": ["encode_png", "encode_jpeg"],
                    }
                ],
                "mcp_server": {
                    "module": "aspose.page.mcp",
                    "factory": "create_server",
                    "runner": "run",
                    "factory_instance_run": True,
                    "tools": [
                        "eps_metadata",
                        "ps_to_image",
                        "ps_to_pdf",
                        "xps_to_image",
                        "xps_to_pdf",
                    ],
                    "runner_defaults": {"host": "127.0.0.1", "port": 8000},
                    "dependency_package": "fastmcp",
                },
            }
        }
    )
    dependencies = FactRecordV2(
        fact_id="installation.capability_dependencies:page-mcp-test",
        field="installation.capability_dependencies",
        verification_state="verified",
        value={
            "entries": [
                {
                    "distribution": "fastmcp",
                    "purpose": "MCP server hosting",
                    "install_command": "python -m pip install fastmcp",
                },
                {
                    "distribution": "skia-python",
                    "purpose": "image conversion",
                    "install_command": "python -m pip install skia-python",
                },
            ]
        },
        source=identity.source,
        authoritative_owner="repository-source",
        confidence=1.0,
        affected_surfaces=["readme"],
    )
    examples = FactRecordV2(
        fact_id="repository.examples:page-result-test",
        field="repository.examples",
        verification_state="verified",
        value={
            "result_assets": [
                {
                    "alt": "PS to image sample",
                    "path": "readme.resources/RGB10.png",
                    "sha256": "b" * 64,
                }
            ]
        },
        source=identity.source,
        authoritative_owner="repository-source",
        confidence=1.0,
        affected_surfaces=["readme"],
    )
    replacements = {
        facts.selected_fact_ids["product.identity"]: identity,
        facts.selected_fact_ids["product.capabilities"]: capabilities,
        facts.selected_fact_ids["api.public_surface"]: api,
    }
    return facts.model_copy(
        update={
            "facts": [
                *[replacements.get(fact.fact_id, fact) for fact in facts.facts],
                dependencies,
                examples,
            ],
            "selected_fact_ids": {
                **facts.selected_fact_ids,
                "installation.capability_dependencies": dependencies.fact_id,
                "repository.examples": examples.fact_id,
            },
        }
    )


def _note_architecture_facts() -> ProductFactsV2:
    facts = _facts()
    identity = facts.selected_fact("product.identity").model_copy(
        update={
            "value": {
                "family": "note",
                "platform": "python",
                "ecosystem": "python",
                "repository": facts.org_repo,
                "product_name": "Aspose.Note",
            }
        }
    )
    api = facts.selected_fact("api.public_surface").model_copy(
        update={
            "value": {
                "modules": [{"module": "aspose.note", "exports": ["Document"]}],
                "package_namespaces": ["aspose.note", "aspose.note.saving"],
                "classes": [],
            }
        }
    )
    formats = facts.selected_fact("product.formats").model_copy(
        update={"verification_state": "verified", "value": ["Input format: OneNote (.one)"]}
    )
    implementation = FactRecordV2(
        fact_id="repository.implementation_components:python-test",
        field="repository.implementation_components",
        verification_state="verified",
        value={
            "components": [
                {
                    "kind": "parser",
                    "labels": ["MS-ONE", "OneStore"],
                    "path": "src/aspose/note/_internal/onestore/parser.py",
                    "source_sha256": "b" * 64,
                }
            ]
        },
        source=identity.source,
        authoritative_owner="repository-source",
        confidence=1.0,
        affected_surfaces=["readme.opening", "readme.api_reference"],
    )
    replacements = {
        identity.fact_id: identity,
        api.fact_id: api,
        formats.fact_id: formats,
    }
    return facts.model_copy(
        update={
            "facts": [
                *[replacements.get(fact.fact_id, fact) for fact in facts.facts],
                implementation,
            ],
            "selected_fact_ids": {
                **facts.selected_fact_ids,
                "repository.implementation_components": implementation.fact_id,
            },
        }
    )


@pytest.mark.parametrize(
    "claim",
    [
        (
            "This repository provides a Python library with a subset-compatible "
            "Aspose.Note for .NET-shaped public API for reading Microsoft OneNote files "
            "(`.one`)."
        ),
        (
            "The goal is to offer a familiar surface (`aspose.note.*`) inspired by "
            "Aspose.Note for .NET, backed by this repository's built-in MS-ONE/OneStore parser."
        ),
    ],
)
def test_note_architecture_claims_bind_to_repository_source_facts(claim: str) -> None:
    facts = _note_architecture_facts()
    material_claim = assess_material_claims(claim)[0]

    binding = complete_source_claim_fact_binding(claim, material_claim, facts)

    assert binding is not None
    assert facts.selected_fact_ids["api.public_surface"] in binding.fact_ids
    assert facts.selected_fact_ids["product.identity"] in binding.fact_ids


def test_note_parser_claim_fails_closed_without_implementation_fact() -> None:
    facts = _note_architecture_facts()
    implementation_id = facts.selected_fact_ids["repository.implementation_components"]
    facts = facts.model_copy(
        update={
            "facts": [fact for fact in facts.facts if fact.fact_id != implementation_id],
            "selected_fact_ids": {
                field: fact_id
                for field, fact_id in facts.selected_fact_ids.items()
                if field != "repository.implementation_components"
            },
        }
    )
    claim = (
        "The goal is to offer a familiar surface (`aspose.note.*`) inspired by "
        "Aspose.Note for .NET, backed by this repository's built-in MS-ONE/OneStore parser."
    )

    binding = complete_source_claim_fact_binding(claim, assess_material_claims(claim)[0], facts)

    assert binding is None


def _assurance(source: str):
    facts = _facts()
    revision = facts.selected_fact("product.identity").source.source_revision
    assert revision is not None
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
    )
    return facts, assessment, build_source_claim_assurance(source, facts, assessment)


def test_page_conversion_and_mcp_source_claims_receive_exact_fact_authority() -> None:
    facts = _page_mcp_facts()
    source = """# Aspose.Page FOSS for Python

## Currently Available Features

- Convert PS/EPS to PDF in Python
- Convert PS/EPS to PNG and JPEG in Python
- Convert XPS to PDF in Python
- Convert XPS to PNG and JPEG in Python
- Integrate conversion workflows through MCP server tools
- PS/EPS to PNG/JPEG conversion
- XPS to PNG/JPEG conversion

![PS to image sample](readme.resources/RGB10.png)

## MCP Server

MCP tools currently exposed:

- `ps_to_pdf`
- `ps_to_image`
- `xps_to_pdf`
- `xps_to_image`
- `eps_metadata`

Run MCP server:

```python
from aspose.page.mcp import create_server

server = create_server()
server.run(host="127.0.0.1", port=8000)
```

Important notes:

- `FastMCP` is required to start the MCP server.
- `skia-python` is required for image conversion flows (`ps_to_image`, `xps_to_image`).
"""
    revision = facts.selected_fact("product.identity").source.source_revision
    assert revision is not None
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
    )

    assurance = build_source_claim_assurance(source, facts, assessment)

    preserve_claims = [
        claim for claim in assessment.material_claims if claim.disposition == "preserve"
    ]
    assert assurance.fact_authorized_claim_count == len(preserve_claims)
    assert assurance.correction_candidate_count == 0


def test_page_capabilities_keep_distinct_format_directions_and_concrete_mcp_prose() -> None:
    facts = _page_mcp_facts()
    source = """# Aspose.Page FOSS for Python

## Currently Available Features

- Convert PS/EPS to PDF in Python
- Convert PS/EPS to PNG and JPEG in Python
- Convert XPS to PDF in Python
- Convert XPS to PNG and JPEG in Python
- Integrate conversion workflows through MCP server tools
"""

    rendered = capability_highlights_markdown(facts, source_text=source)

    assert rendered is not None
    assert len(rendered.splitlines()) == 5
    assert "**Convert PS/EPS files to PDF in Python**" in rendered
    assert "**Convert PS/EPS files to PNG and JPEG in Python**" in rendered
    assert "**Convert XPS files to PDF in Python**" in rendered
    assert "**Convert XPS files to PNG and JPEG in Python**" in rendered
    assert "**Host MCP servers**" in rendered
    assert "Create and run the MCP server" in rendered
    assert "Apply the operation through the product's public API" not in rendered

    candidate = "# Aspose.Page FOSS for Python\n\n## Key Capabilities\n\n" + rendered + "\n"
    candidate_claims = assess_material_claims(candidate)
    candidate_bytes = candidate.encode("utf-8")
    identity_fact_id = facts.selected_fact_ids["product.identity"]
    api_fact_id = facts.selected_fact_ids["api.public_surface"]
    provenance = [
        CandidateContentProvenanceV1(
            provenance_id=f"template.section.key_capabilities.claim:{index}",
            candidate_byte_start=claim.source_byte_start,
            candidate_byte_end=claim.source_byte_end,
            fact_ids=sorted(
                {
                    *capability_claim_fact_ids(
                        candidate_bytes[claim.source_byte_start : claim.source_byte_end].decode(
                            "utf-8"
                        ),
                        facts,
                    ),
                    api_fact_id,
                }
            ),
            fact_coordinates=capability_claim_fact_coordinates(
                candidate_bytes[claim.source_byte_start : claim.source_byte_end].decode("utf-8"),
                facts,
                source_text=source,
            ),
            rationale="Bind the generated Page capability to accepted facts.",
        )
        for index, claim in enumerate(candidate_claims)
    ]
    assert all(identity_fact_id in item.fact_ids for item in provenance[:4])
    image_source = "- Convert PS/EPS to PNG and JPEG in Python\n"
    image_claim = assess_material_claims(image_source)[0]
    image_binding = complete_source_claim_fact_binding(image_source, image_claim, facts)
    assert image_binding is not None
    assert {coordinate.path for coordinate in image_binding.fact_coordinates} == {
        "/items/79de03fbaaa90ab1",
        "/modules/aspose.page.image.encoders/exports/encode_jpeg",
        "/modules/aspose.page.image.encoders/exports/encode_png",
    }
    mcp_binding = next(
        binding
        for binding in provenance
        if "Host MCP servers"
        in candidate_bytes[binding.candidate_byte_start : binding.candidate_byte_end].decode(
            "utf-8"
        )
    )
    assert {
        "/mcp_server/factory",
        "/mcp_server/runner",
        "/mcp_server/tools/ps_to_image",
        "/mcp_server/tools/ps_to_pdf",
        "/mcp_server/tools/xps_to_image",
        "/mcp_server/tools/xps_to_pdf",
    }.issubset({coordinate.path for coordinate in mcp_binding.fact_coordinates})
    for inherited_claim in (
        "- Convert PS/EPS to PDF in Python",
        "- Convert PS/EPS to PNG and JPEG in Python",
        "- Convert XPS to PDF in Python",
        "- Convert XPS to PNG and JPEG in Python",
    ):
        assert (
            len(
                fact_bound_capability_candidate_claims(
                    inherited_claim,
                    candidate_bytes,
                    candidate_claims,
                    facts,
                    provenance,
                )
            )
            == 1
        )


def test_page_mcp_source_binding_rejects_unknown_tool_and_changed_runner_port() -> None:
    facts = _page_mcp_facts()
    source = """# Aspose.Page FOSS for Python

## MCP Server

- `delete_everything`

```python
from aspose.page.mcp import create_server

server = create_server()
server.run(host="127.0.0.1", port=9000)
```
"""
    revision = facts.selected_fact("product.identity").source.source_revision
    assert revision is not None
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
    )

    assurance = build_source_claim_assurance(source, facts, assessment)

    assert assurance.fact_authorized_claim_count == 0
    assert assurance.correction_candidate_count == 2


def test_fact_authorized_result_image_reuses_the_fact_bound_candidate_claim() -> None:
    facts = _page_mcp_facts()
    image = "![PS to image sample](readme.resources/RGB10.png)"
    source = f"# Product\n\n## Example Results\n\n{image}\n"
    candidate = f"# Product\n\n## Additional examples\n\n### Example results\n\n{image}\n"
    source_claim = assess_material_claims(source)[0]
    candidate_claim = assess_material_claims(candidate)[0]
    examples = facts.selected_fact("repository.examples")
    provenance = [
        CandidateContentProvenanceV1(
            provenance_id="template.section.additional_examples.result-image",
            candidate_byte_start=candidate_claim.source_byte_start,
            candidate_byte_end=candidate_claim.source_byte_end,
            fact_ids=[examples.fact_id],
            rationale="Bind the exact result image to its checksum-bound repository inventory.",
        )
    ]

    resolutions = build_source_claim_resolutions(
        source,
        candidate,
        facts,
        provenance,
        preserved_source_ranges=[(source_claim.source_byte_start, source_claim.source_byte_end)],
    )

    assert len(resolutions) == 1
    assert resolutions[0].resolution == "verified_equivalence"
    assert resolutions[0].candidate_claim_id == candidate_claim.claim_id


def _with_repository_example(facts: ProductFactsV2, code: str) -> ProductFactsV2:
    identity = facts.selected_fact("product.identity")
    examples = FactRecordV2(
        fact_id="repository.examples:source-assurance-example",
        field="repository.examples",
        verification_state="verified",
        value={
            "inline_examples": [
                {
                    "title": "Save a widget",
                    "language": "python",
                    "code": code,
                    "static_api_verified": True,
                    "execution_verified": False,
                }
            ]
        },
        source=identity.source,
        authoritative_owner="repository-source",
        confidence=1.0,
        affected_surfaces=["readme"],
    )
    return facts.model_copy(
        update={
            "facts": [*facts.facts, examples],
            "selected_fact_ids": {
                **facts.selected_fact_ids,
                "repository.examples": examples.fact_id,
            },
        }
    )


def test_exact_structured_api_claim_is_preservation_eligible() -> None:
    source = "# Product\n\n## API reference\n\n- `Matrix4` — `translate()`, `inverse()`\n"

    facts, assessment, assurance = _assurance(source)
    claim = assessment.material_claims[0]
    binding = complete_source_claim_fact_binding(source, claim, facts)

    assert binding is not None
    assert binding.fact_ids == frozenset({facts.selected_fact_ids["api.public_surface"]})
    assert {coordinate.path for coordinate in binding.fact_coordinates} == {
        "/classes/Matrix4",
        "/classes/Matrix4/members/inverse",
        "/classes/Matrix4/members/translate",
    }
    assert assurance.preserve_ranges == [(claim.source_byte_start, claim.source_byte_end)]
    assert assurance.correction_ranges == []
    assert assurance.fact_authorized_claim_count == 1
    assert assurance.correction_candidate_count == 0


def test_coordinate_equivalence_rejects_a_different_api_member_in_the_same_fact() -> None:
    facts = _facts()
    api = facts.selected_fact("api.public_surface")
    matrix = set(api_class_fact_coordinates(api.fact_id, api.value, ["Matrix4"]))
    material = set(api_class_fact_coordinates(api.fact_id, api.value, ["Material"]))

    assert matrix
    assert material
    assert _coordinates_cover(matrix, matrix)
    assert not _coordinates_cover(matrix, material)


def test_equivalence_resolver_rejects_wrong_api_coordinate_under_same_fact() -> None:
    facts = _facts()
    api = facts.selected_fact("api.public_surface")
    source = "- `Matrix4` \N{EM DASH} `translate()`\n"
    candidate = "- **`Matrix4`** \N{EM DASH} `translate()`\n"
    source_claim = assess_material_claims(source)[0]
    candidate_claim = assess_material_claims(candidate)[0]
    wrong_coordinates = api_class_fact_coordinates(api.fact_id, api.value, ["Material"])
    provenance = [
        CandidateContentProvenanceV1(
            provenance_id="template.section.api_reference.claim:wrong-coordinate",
            candidate_byte_start=candidate_claim.source_byte_start,
            candidate_byte_end=candidate_claim.source_byte_end,
            fact_ids=[api.fact_id],
            fact_coordinates=wrong_coordinates,
            rationale="Exercise rejection of an aggregate fact with the wrong exact coordinate.",
        )
    ]

    assert (
        equivalent_source_claim_resolution(
            source_claim,
            source,
            candidate.encode("utf-8"),
            index_equivalent_candidate_claims(
                candidate.encode("utf-8"),
                [candidate_claim],
            ),
            facts,
            provenance,
        )
        is None
    )


@pytest.mark.parametrize(
    "claim_text",
    [
        "- `Matrix4` — `translate()`, `unsupported()`",
        "- `Material` (base) — `get_texture(slot_name)`",
        "- `Matrix4` — `translate()` plus an unverified performance guarantee",
    ],
)
def test_partial_structured_coordinates_do_not_approve_the_whole_claim(
    claim_text: str,
) -> None:
    source = f"# Product\n\n## API reference\n\n{claim_text}\n"

    facts, assessment, assurance = _assurance(source)
    claim = assessment.material_claims[0]

    assert complete_source_claim_fact_binding(source, claim, facts) is None
    assert assurance.preserve_ranges == []
    assert assurance.correction_ranges == [(claim.source_byte_start, claim.source_byte_end)]
    assert assurance.fact_authorized_claim_count == 0
    assert assurance.correction_candidate_count == 1


def test_exact_literal_fact_claim_requires_complete_visitor_meaning() -> None:
    exact = "# Product\n\n## Capabilities\n\n- Build verified meshes\n"
    partial = exact.replace("meshes\n", "meshes with imaginary acceleration\n")

    _, exact_assessment, exact_assurance = _assurance(exact)
    _, partial_assessment, partial_assurance = _assurance(partial)

    exact_claim = exact_assessment.material_claims[0]
    partial_claim = partial_assessment.material_claims[0]
    assert exact_assurance.preserve_ranges == [
        (exact_claim.source_byte_start, exact_claim.source_byte_end)
    ]
    assert partial_assurance.preserve_ranges == []
    assert partial_assurance.correction_ranges == [
        (partial_claim.source_byte_start, partial_claim.source_byte_end)
    ]


def test_exact_repository_example_is_fact_bound_but_comment_cleanup_requires_correction() -> None:
    code = "from acme import Widget\n\n# Save the verified widget.\nWidget().save('out.bin')\n"
    source = f"# Product\n\n## Examples\n\n```python\n{code}```\n"
    facts = _with_repository_example(_facts(), code)
    revision = facts.selected_fact("product.identity").source.source_revision or "a" * 40
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
    )
    claim = assessment.material_claims[0]
    assurance = build_source_claim_assurance(source, facts, assessment)

    binding = complete_source_claim_fact_binding(source, claim, facts)

    assert binding is not None
    assert binding.fact_ids == frozenset({facts.selected_fact_ids["repository.examples"]})
    assert assurance.preserve_ranges == []
    assert assurance.correction_ranges == [(claim.source_byte_start, claim.source_byte_end)]


def test_comment_free_repository_example_requires_exact_ast_and_complete_provenance() -> None:
    code = "from acme import Widget\n\n# Save the verified widget.\nWidget().save('out.bin')\n"
    source = f"# Product\n\n## Examples\n\n```python\n{code}```\n"
    candidate = (
        "# Product\n\n## Examples\n\n"
        "```python\nfrom acme import Widget\n\nWidget().save('out.bin')\n```\n"
    )
    facts = _with_repository_example(_facts(), code)
    source_claim = assess_material_claims(source)[0]
    candidate_claims = assess_material_claims(candidate)
    candidate_claim = candidate_claims[0]
    provenance = CandidateContentProvenanceV1(
        provenance_id="repository-example-comment-cleanup",
        candidate_byte_start=candidate_claim.source_byte_start,
        candidate_byte_end=candidate_claim.source_byte_end,
        fact_ids=[facts.selected_fact_ids["repository.examples"]],
        rationale="Bind the comment-free code fence to the verified repository example.",
    )

    resolution = equivalent_source_claim_resolution(
        source_claim,
        source.encode()[source_claim.source_byte_start : source_claim.source_byte_end].decode(),
        candidate.encode(),
        index_equivalent_candidate_claims(candidate.encode(), candidate_claims),
        facts,
        [provenance],
    )

    assert resolution is not None
    assert resolution.resolution == "verified_equivalence"
    assert resolution.fact_ids == [facts.selected_fact_ids["repository.examples"]]

    changed = candidate.replace("out.bin", "other.bin")
    changed_claims = assess_material_claims(changed)
    assert (
        equivalent_source_claim_resolution(
            source_claim,
            source.encode()[source_claim.source_byte_start : source_claim.source_byte_end].decode(),
            changed.encode(),
            index_equivalent_candidate_claims(changed.encode(), changed_claims),
            facts,
            [
                provenance.model_copy(
                    update={
                        "candidate_byte_start": changed_claims[0].source_byte_start,
                        "candidate_byte_end": changed_claims[0].source_byte_end,
                    }
                )
            ],
        )
        is None
    )


def test_source_capability_bindings_are_computed_once_per_claim(monkeypatch) -> None:
    facts = _page_mcp_facts()
    source = """# Aspose.Page FOSS for Python

## Currently Available Features

- Convert PS/EPS to PDF in Python
- Convert PS/EPS to PNG and JPEG in Python
- Convert XPS to PDF in Python
- Convert XPS to PNG and JPEG in Python
- Integrate conversion workflows through MCP server tools
"""
    expected_calls = len(assess_material_claims(source))
    actual_calls = 0
    original = capabilities_module.complete_source_claim_fact_binding

    def counted_binding(document, claim, product_facts):
        nonlocal actual_calls
        actual_calls += 1
        return original(document, claim, product_facts)

    monkeypatch.setattr(
        capabilities_module,
        "complete_source_claim_fact_binding",
        counted_binding,
    )

    assert capability_highlights_markdown(facts, source_text=source) is not None
    assert actual_calls == expected_calls


def test_source_capability_index_does_not_leak_compound_or_ambiguous_evidence() -> None:
    facts = _page_mcp_facts()
    capabilities = facts.selected_fact("product.capabilities")
    formats = facts.selected_fact("product.formats")
    capability_a = structured_list_item_coordinate(
        capabilities.fact_id,
        capabilities.field,
        "PS/EPS to PDF conversion",
    )
    capability_b = structured_list_item_coordinate(
        capabilities.fact_id,
        capabilities.field,
        "XPS to PDF conversion",
    )
    png = structured_list_item_coordinate(formats.fact_id, formats.field, "PNG")
    tiff = structured_list_item_coordinate(formats.fact_id, formats.field, "TIFF")
    compound = CompleteSourceClaimFactBindingV1(
        fact_ids=frozenset({capabilities.fact_id, formats.fact_id}),
        fact_coordinates=(capability_a, capability_b, png),
    )
    compound_index = capabilities_module._source_capability_coordinate_index(
        [("compound", compound)]
    )

    fact_ids, coordinates = capabilities_module._source_coordinates_for_capability_row(
        compound_index,
        [capability_a],
    )

    assert fact_ids == []
    assert coordinates == []

    first = CompleteSourceClaimFactBindingV1(
        fact_ids=frozenset({capabilities.fact_id, formats.fact_id}),
        fact_coordinates=(capability_a, png),
    )
    second = CompleteSourceClaimFactBindingV1(
        fact_ids=frozenset({capabilities.fact_id, formats.fact_id}),
        fact_coordinates=(capability_a, tiff),
    )
    ambiguous_index = capabilities_module._source_capability_coordinate_index(
        [("first", first), ("second", second)]
    )

    fact_ids, coordinates = capabilities_module._source_coordinates_for_capability_row(
        ambiguous_index,
        [capability_a],
    )

    assert fact_ids == [capabilities.fact_id]
    assert coordinates == [capability_a]


def test_directional_format_coordinates_require_local_input_or_output_language() -> None:
    fact_id = "product.formats:direction-test"
    values = [
        "Input format: PDF",
        "Output format: PDF",
        "Output format: PNG",
        "Output format: TIFF",
    ]

    overview = literal_list_fact_coordinates(
        "Create, read, edit, render, and validate PDF documents.",
        fact_id,
        "product.formats",
        values,
    )
    directional = literal_list_fact_coordinates(
        "Reads PDF files and writes PDF files, PNG files, and TIFF files.",
        fact_id,
        "product.formats",
        values,
    )
    rendered = literal_list_fact_coordinates(
        "Render pages to PNG or TIFF.",
        fact_id,
        "product.formats",
        values,
    )

    assert overview == [
        structured_list_item_coordinate(fact_id, "product.formats", "Input format: PDF")
    ]
    assert directional == [
        structured_list_item_coordinate(fact_id, "product.formats", value) for value in values
    ]
    assert rendered == [
        structured_list_item_coordinate(fact_id, "product.formats", value) for value in values[2:]
    ]


def test_capability_presentation_plan_is_reused_without_rebinding(monkeypatch) -> None:
    facts = _page_mcp_facts()
    source = """# Aspose.Page FOSS for Python

## Currently Available Features

- Convert PS/EPS to PDF in Python
- Integrate conversion workflows through MCP server tools
"""
    plan = capabilities_module.build_capability_presentation_plan(
        facts,
        source_text=source,
    )

    def unexpected_rebind(*_args, **_kwargs):
        raise AssertionError("precomputed capability plan must not rebind source claims")

    monkeypatch.setattr(
        capabilities_module,
        "complete_source_claim_fact_binding",
        unexpected_rebind,
    )
    rendered = capability_highlights_markdown(
        facts,
        source_text=source,
        presentation_plan=plan,
    )
    assert rendered is not None
    for markdown, fact_ids, coordinates in plan.rows:
        assert capabilities_module.capability_claim_fact_ids(
            markdown,
            facts,
            presentation_plan=plan,
        )
        assert set(
            capabilities_module.capability_claim_fact_coordinates(
                markdown,
                facts,
                source_text=source,
                presentation_plan=plan,
            )
        ) == set(coordinates)
        assert set(fact_ids).issubset(
            capabilities_module.capability_claim_fact_ids(
                markdown,
                facts,
                presentation_plan=plan,
            )
        )


def test_capability_equivalence_rejects_a_candidate_missing_one_structured_fact() -> None:
    facts = _facts()
    capability_fact_id = facts.selected_fact_ids["product.capabilities"]
    api_fact_id = facts.selected_fact_ids["api.public_surface"]
    source = "- Work with build verified meshes\n"
    candidate = "- **Build verified meshes** - Supports build verified meshes.\n"
    source_claim = assess_material_claims(source)[0]
    candidate_claim = assess_material_claims(candidate)[0]
    source_binding = complete_source_claim_fact_binding(source, source_claim, facts)
    assert source_binding is not None
    assert source_binding.fact_ids == frozenset({capability_fact_id, api_fact_id})
    provenance = CandidateContentProvenanceV1(
        provenance_id="template.section.key_capabilities.claim:test",
        candidate_byte_start=candidate_claim.source_byte_start,
        candidate_byte_end=candidate_claim.source_byte_end,
        fact_ids=[capability_fact_id],
        rationale="Bind only the narrower generated capability claim.",
    )

    assert (
        fact_bound_capability_candidate_claims(
            source,
            candidate.encode(),
            [candidate_claim],
            facts,
            [provenance],
        )
        == []
    )

    resolution = equivalent_source_claim_resolution(
        source_claim,
        source.encode()[source_claim.source_byte_start : source_claim.source_byte_end].decode(),
        candidate.encode(),
        index_equivalent_candidate_claims(candidate.encode(), [candidate_claim]),
        facts,
        [provenance],
    )

    assert resolution is None


def test_capability_equivalence_accepts_complete_renderer_format_provenance() -> None:
    facts = ProductFactsV2.model_validate(build_review_facts(REVIEW_ARCHETYPES[2]))
    capability = facts.selected_fact("product.capabilities")
    formats = facts.selected_fact("product.formats")
    facts = facts.model_copy(
        update={
            "facts": [
                fact.model_copy(update={"value": ["Render pages to PNG or TIFF"]})
                if fact.fact_id == capability.fact_id
                else fact.model_copy(update={"value": ["PDF", "PNG", "TIFF"]})
                if fact.fact_id == formats.fact_id
                else fact
                for fact in facts.facts
            ]
        }
    )
    source = "- Render pages to PNG or TIFF\n"
    candidate = (
        "- **Render pages to PNG or TIFF** - Produce PNG and TIFF image output "
        "from individual pages.\n"
    )
    candidate_claim = assess_material_claims(candidate)[0]
    provenance = CandidateContentProvenanceV1(
        provenance_id="template.section.key_capabilities.claim:render",
        candidate_byte_start=candidate_claim.source_byte_start,
        candidate_byte_end=candidate_claim.source_byte_end,
        fact_ids=[capability.fact_id, formats.fact_id],
        fact_coordinates=[
            structured_list_item_coordinate(
                capability.fact_id,
                capability.field,
                "Render pages to PNG or TIFF",
            ),
            structured_list_item_coordinate(formats.fact_id, formats.field, "PNG"),
            structured_list_item_coordinate(formats.fact_id, formats.field, "TIFF"),
        ],
        rationale="Bind the generated capability row to its capability and format facts.",
    )

    matches = fact_bound_capability_candidate_claims(
        source,
        candidate.encode(),
        [candidate_claim],
        facts,
        [provenance],
    )

    assert matches == [candidate_claim]
    source_claim = assess_material_claims(source)[0]
    resolution = equivalent_source_claim_resolution(
        source_claim,
        source,
        candidate.encode(),
        index_equivalent_candidate_claims(candidate.encode(), [candidate_claim]),
        facts,
        [provenance],
    )
    assert resolution is not None
    assert resolution.resolution == "verified_equivalence"


def test_capability_equivalence_rejects_wrong_coordinate_under_same_fact_id() -> None:
    facts = ProductFactsV2.model_validate(build_review_facts(REVIEW_ARCHETYPES[2]))
    capability = facts.selected_fact("product.capabilities")
    formats = facts.selected_fact("product.formats")
    facts = facts.model_copy(
        update={
            "facts": [
                fact.model_copy(
                    update={
                        "value": [
                            "Render pages to PNG or TIFF",
                            "Extract text from PDF pages",
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
    source = "- Render pages to PNG or TIFF\n"
    candidate = "- **Render pages to PNG or TIFF** - Produce raster image output.\n"
    candidate_claim = assess_material_claims(candidate)[0]
    provenance = CandidateContentProvenanceV1(
        provenance_id="template.section.key_capabilities.claim:wrong-coordinate",
        candidate_byte_start=candidate_claim.source_byte_start,
        candidate_byte_end=candidate_claim.source_byte_end,
        fact_ids=[capability.fact_id, formats.fact_id],
        fact_coordinates=[
            structured_list_item_coordinate(
                capability.fact_id,
                capability.field,
                "Extract text from PDF pages",
            ),
            structured_list_item_coordinate(formats.fact_id, formats.field, "PNG"),
            structured_list_item_coordinate(formats.fact_id, formats.field, "TIFF"),
        ],
        rationale="Deliberately bind the wrong capability coordinate for the negative control.",
    )

    assert (
        fact_bound_capability_candidate_claims(
            source,
            candidate.encode(),
            [candidate_claim],
            facts,
            [provenance],
        )
        == []
    )


def test_capability_equivalence_rejects_a_dropped_limitation_qualifier() -> None:
    facts = ProductFactsV2.model_validate(build_review_facts(REVIEW_ARCHETYPES[2]))
    capability = facts.selected_fact("product.capabilities")
    limitation = facts.selected_fact("product.limitations")
    facts = facts.model_copy(
        update={
            "facts": [
                fact.model_copy(update={"value": ["Perform heuristic PDF/A validation"]})
                if fact.fact_id == capability.fact_id
                else fact.model_copy(
                    update={"value": ["checks are not certification-grade conformance"]}
                )
                if fact.fact_id == limitation.fact_id
                else fact
                for fact in facts.facts
            ]
        }
    )
    source = (
        "- Perform heuristic PDF/A validation; checks are not certification-grade conformance\n"
    )
    candidate = "- **Perform heuristic PDF/A validation** - Check archival conformance profiles.\n"
    candidate_claim = assess_material_claims(candidate)[0]
    provenance = CandidateContentProvenanceV1(
        provenance_id="template.section.key_capabilities.claim:dropped-limitation",
        candidate_byte_start=candidate_claim.source_byte_start,
        candidate_byte_end=candidate_claim.source_byte_end,
        fact_ids=[capability.fact_id],
        fact_coordinates=[
            structured_list_item_coordinate(
                capability.fact_id,
                capability.field,
                "Perform heuristic PDF/A validation",
            )
        ],
        rationale="Deliberately omit the limitation fact for the negative control.",
    )

    assert (
        fact_bound_capability_candidate_claims(
            source,
            candidate.encode(),
            [candidate_claim],
            facts,
            [provenance],
        )
        == []
    )


def test_fact_richer_source_capability_supersedes_only_the_narrow_generated_row() -> None:
    facts = _facts()
    capability = facts.selected_fact("product.capabilities")
    facts = facts.model_copy(
        update={
            "facts": [
                fact.model_copy(
                    update={
                        "value": ["Build verified meshes", "Export verified scenes"],
                    }
                )
                if fact.fact_id == capability.fact_id
                else fact
                for fact in facts.facts
            ]
        }
    )

    rendered = capability_highlights_markdown(
        facts,
        source_text="- Work with build verified meshes\n",
    )

    assert rendered is not None
    assert "Build verified meshes" not in rendered
    assert "Export verified scenes" in rendered


def test_stale_claim_hash_fails_closed() -> None:
    source = "# Product\n\n## API reference\n\n- `Matrix4` — `inverse()`\n"
    facts, assessment, _ = _assurance(source)
    stale = assessment.material_claims[0].model_copy(update={"content_sha256": "0" * 64})

    with pytest.raises(ValueError, match="hash does not match immutable document bytes"):
        complete_source_claim_fact_binding(source, stale, facts)


def test_grouped_api_members_bind_as_a_union_but_unknown_members_fail_closed() -> None:
    facts = _facts()
    api = facts.selected_fact("api.public_surface")
    replacement = api.model_copy(
        update={
            "value": {
                **api.value,
                "classes": [
                    *api.value["classes"],
                    _class("Transform", "set_translation(tx, ty, tz)"),
                    _class("GlobalTransform", "translation: Vector3"),
                ],
            }
        }
    )
    facts = facts.model_copy(
        update={
            "facts": [replacement if fact.fact_id == api.fact_id else fact for fact in facts.facts]
        }
    )
    source = (
        "# Product\n\n## API reference\n\n"
        "- `Transform` / `GlobalTransform`\n"
        "  - `set_translation(tx, ty, tz)`, `translation`\n"
    )
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision=facts.selected_fact("product.identity").source.source_revision or "a" * 40,
    )
    claim = next(item for item in assessment.material_claims if item.source_byte_start > 60)

    binding = complete_source_claim_fact_binding(source, claim, facts)

    assert binding is not None
    assert binding.fact_ids == frozenset({api.fact_id})

    unsupported = source.replace("`translation`", "`imaginary_member`")
    bad_assessment = assess_readme_document(
        facts.org_repo,
        unsupported,
        facts,
        base_revision=facts.selected_fact("product.identity").source.source_revision or "a" * 40,
    )
    bad_claim = next(item for item in bad_assessment.material_claims if item.source_byte_start > 60)
    assert complete_source_claim_fact_binding(unsupported, bad_claim, facts) is None


def test_only_the_identity_derived_github_issue_route_is_fact_bound() -> None:
    facts = _facts()
    identity = facts.selected_fact("product.identity")
    replacement = identity.model_copy(
        update={"value": {**identity.value, "repository": "acme/verified-repository"}}
    )
    facts = facts.model_copy(
        update={
            "facts": [
                replacement if fact.fact_id == identity.fact_id else fact for fact in facts.facts
            ]
        }
    )
    exact = (
        "- Found a bug or have a feature request? [Open an issue]"
        "(https://github.com/acme/verified-repository/issues) on GitHub."
    )

    assert accepted_source_claim_fact_ids(exact, facts) == {identity.fact_id}
    assert not accepted_source_claim_fact_ids(
        exact.replace("acme/verified-repository", "acme/other-repository"),
        facts,
    )
    assert not accepted_source_claim_fact_ids(
        "- Read the guide at https://docs.aspose.org/3d/python/private-path/.",
        facts,
    )


def test_exact_selected_guidance_binds_across_markdown_line_wrapping() -> None:
    facts = _facts()
    identity = facts.selected_fact("product.identity")
    guidance = identity.model_copy(
        update={
            "fact_id": "repository.public_guidance:fixture",
            "field": "repository.public_guidance",
            "value": ["The package ships type information and remains in alpha while APIs evolve."],
        }
    )
    facts = facts.model_copy(
        update={
            "facts": [*facts.facts, guidance],
            "selected_fact_ids": {
                **facts.selected_fact_ids,
                "repository.public_guidance": guidance.fact_id,
            },
        }
    )
    wrapped = "The package ships type information and remains\nin alpha while APIs evolve."

    assert accepted_source_claim_fact_ids(wrapped, facts) == {guidance.fact_id}


def _format_entailment_facts() -> ProductFactsV2:
    facts = _facts()
    identity = facts.selected_fact("product.identity")
    capability = facts.selected_fact("product.capabilities").model_copy(
        update={"value": ["File format import and export for OBJ, GLTF, STL, and 3MF"]}
    )
    formats = facts.selected_fact("product.formats").model_copy(
        update={
            "value": [
                "Input format: OBJ",
                "Input format: GLTF",
                "Output format: GLTF",
                "Input format: STL",
                "Output format: STL",
                "Input format: 3MF",
                "Output format: 3MF",
            ]
        }
    )
    limitations = facts.selected_fact("product.limitations").model_copy(
        update={
            "verification_state": "verified",
            "value": [
                {
                    "kind": "collada_dispatch_blocked",
                    "statement": "COLLADA export through Scene.save is blocked.",
                }
            ],
        }
    )
    api = facts.selected_fact("api.public_surface").model_copy(
        update={
            "value": {
                **facts.selected_fact("api.public_surface").value,
                "classes": [
                    *facts.selected_fact("api.public_surface").value["classes"],
                    _class("Scene", "open(path)", "save(path)"),
                ],
            }
        }
    )
    examples = FactRecordV2(
        fact_id="repository.examples:source-assurance-test",
        field="repository.examples",
        verification_state="verified",
        value={
            "inline_examples": [
                {
                    "static_api_verified": True,
                    "code": ("options = ColladaLoadOptions()\nscene.open('model.dae', options)\n"),
                }
            ]
        },
        source=identity.source,
        authoritative_owner="repository-source",
        confidence=1.0,
        affected_surfaces=["readme"],
    )
    replacements = {
        capability.fact_id: capability,
        formats.fact_id: formats,
        limitations.fact_id: limitations,
        api.fact_id: api,
    }
    return facts.model_copy(
        update={
            "facts": [
                *[replacements.get(fact.fact_id, fact) for fact in facts.facts],
                examples,
            ],
            "selected_fact_ids": {
                **facts.selected_fact_ids,
                "repository.examples": examples.fact_id,
            },
        }
    )


def test_format_capabilities_require_the_exact_accepted_fact_union() -> None:
    facts = _format_entailment_facts()
    source = (
        "# Product\n\n## Capabilities\n\n"
        "- Import OBJ, STL, glTF / GLB, COLLADA (`.dae`), and 3MF files into a common `Scene` "
        "model with `Scene.open(...)`.\n"
        "- Export the same `Scene` model back out to OBJ, STL, glTF/GLB, or 3MF with "
        "`Scene.save(...)` (COLLADA import is supported; COLLADA export is not currently "
        "reachable through the public API).\n"
    )
    revision = facts.selected_fact("product.identity").source.source_revision or "a" * 40
    assessment = assess_readme_document(facts.org_repo, source, facts, base_revision=revision)
    source_bytes = source.encode()
    bindings = {
        source_bytes[claim.source_byte_start : claim.source_byte_end]
        .decode()
        .split()[1]: complete_source_claim_fact_binding(source, claim, facts)
        for claim in assessment.material_claims
    }

    assert bindings["Import"] is not None
    assert facts.selected_fact_ids["repository.examples"] in bindings["Import"].fact_ids
    assert bindings["Export"] is not None
    assert facts.selected_fact_ids["product.limitations"] in bindings["Export"].fact_ids

    unsupported = source.replace("OBJ, STL", "FBX, OBJ, STL", 1)
    assessment = assess_readme_document(facts.org_repo, unsupported, facts, base_revision=revision)
    unsupported_claim = assessment.material_claims[0]
    assert complete_source_claim_fact_binding(unsupported, unsupported_claim, facts) is None


def test_fact_bound_format_claim_is_corrected_when_repository_evidence_disproves_it() -> None:
    facts = _format_entailment_facts()
    identity = facts.selected_fact("product.identity")
    directions = FactRecordV2(
        fact_id="repository.format_directions:source-assurance-test",
        field="repository.format_directions",
        verification_state="verified",
        value={
            "directions": [
                {
                    "format": "OBJ",
                    "direction": "input",
                    "material_library_support": False,
                }
            ]
        },
        source=identity.source,
        authoritative_owner="repository-source",
        confidence=1.0,
        affected_surfaces=["readme"],
    )
    facts = facts.model_copy(
        update={
            "facts": [*facts.facts, directions],
            "selected_fact_ids": {
                **facts.selected_fact_ids,
                directions.field: directions.fact_id,
            },
        }
    )
    source = (
        "# Product\n\n## Capabilities\n\n"
        "- Import OBJ (with `.mtl` materials), STL, GLTF, and 3MF files into a common Scene.\n"
    )
    revision = identity.source.source_revision or "a" * 40
    assessment = assess_readme_document(facts.org_repo, source, facts, base_revision=revision)

    assurance = build_source_claim_assurance(source, facts, assessment)

    assert assurance.fact_authorized_claim_count == 0
    assert assurance.correction_candidate_count == 1
