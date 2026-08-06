"""Prove complete source-claim fact binding before preservation."""

from __future__ import annotations

import pytest

from readme_agent.facts.schema_v2 import FactRecordV2, ProductFactsV2
from readme_agent.golden_set.review_fixtures import REVIEW_ARCHETYPES, build_review_facts
from readme_agent.readme.assessment import assess_readme_document
from readme_agent.readme.source_claim_assurance import build_source_claim_assurance
from readme_agent.readme.source_claim_fact_binding import (
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
