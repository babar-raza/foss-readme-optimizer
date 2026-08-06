"""Prove exact source contradictions without treating missing evidence as falsity."""

import hashlib
import json

from readme_agent.facts.schema_v2 import FactRecordV2, FactSourceV2, ProductFactsV2
from readme_agent.readme.assessment_claims import assess_material_claims
from readme_agent.readme.source_claim_contradiction import contradicted_source_claim_fact_ids

HASH = "a" * 64


def _facts(*, complete_catalog: bool = True) -> ProductFactsV2:
    source = FactSourceV2(
        source_type="mechanical_repository",
        location="repository://package",
        source_revision="b" * 40,
    )
    catalog = {
        "schema_version": 1,
        "public_api_source_sha256": HASH,
        "modules": [
            {
                "module": "acme",
                "exports": ["Entity", "Mesh", "AnimationClip", "ImportException"],
                "source_path": "acme/__init__.py",
                "source_sha256": HASH,
            }
        ],
        "classes": [
            {"name": "Entity", "bases": ["SceneObject"], "members": []},
            {
                "name": "Mesh",
                "bases": ["Geometry"],
                "members": [{"name": "create_polygon", "surface": "create_polygon(*args)"}],
            },
            {
                "name": "AnimationClip",
                "bases": ["SceneObject"],
                "members": [
                    {
                        "name": "create_animation_node",
                        "surface": "create_animation_node(node_name)",
                    }
                ],
            },
            {"name": "ImportException", "bases": ["Exception"], "members": []},
            {"name": "InternalException", "bases": ["Exception"], "members": []},
        ],
        "functions": [],
    }
    payload = json.dumps(catalog, sort_keys=True, separators=(",", ":")).encode()
    api_value = {
        "public_api_source_sha256": HASH,
        "unresolved_reexports": [] if complete_catalog else ["acme.missing"],
        "coordinate_catalog": {
            **catalog,
            "content_sha256": hashlib.sha256(payload).hexdigest(),
        },
    }
    api = FactRecordV2(
        fact_id="api.public_surface:test",
        field="api.public_surface",
        value=api_value,
        source=source,
        verification_state="verified",
        authoritative_owner="repository-owner",
        confidence=1.0,
        affected_surfaces=["readme"],
    )
    directions = FactRecordV2(
        fact_id="repository.format_directions:test",
        field="repository.format_directions",
        value={
            "directions": [
                {
                    "format": "OBJ",
                    "direction": "input",
                    "material_library_support": False,
                }
            ]
        },
        source=source,
        verification_state="verified",
        authoritative_owner="repository-owner",
        confidence=1.0,
        affected_surfaces=["readme"],
    )
    limitations = FactRecordV2(
        fact_id="product.limitations:test",
        field="product.limitations",
        value=[{"kind": "collada_dispatch_blocked"}],
        source=source,
        verification_state="verified",
        authoritative_owner="repository-owner",
        confidence=1.0,
        affected_surfaces=["readme"],
    )
    shadowing = FactRecordV2(
        fact_id="repository.python_import_shadowing:test",
        field="repository.python_import_shadowing",
        value={
            "entries": [
                {
                    "symbol": "FbxLoadOptions",
                    "inheritance_changed": True,
                }
            ]
        },
        source=source,
        verification_state="verified",
        authoritative_owner="repository-owner",
        confidence=1.0,
        affected_surfaces=["readme"],
    )
    return ProductFactsV2.model_construct(
        schema_version=2,
        content_assurance="repository_verified",
        org_repo="acme/widget",
        facts=[api, directions, limitations, shadowing],
        selected_fact_ids={
            fact.field: fact.fact_id for fact in (api, directions, limitations, shadowing)
        },
        package_root_roles=None,
    )


def _contradictions(source: str, facts: ProductFactsV2 | None = None) -> set[str]:
    claim = assess_material_claims(source)[-1]
    return contradicted_source_claim_fact_ids(source, claim, facts or _facts())


def test_proves_member_signature_public_export_relationship_and_format_contradictions() -> None:
    assert _contradictions("# API reference\n\n- `Mesh` — `create_polygon(*indices)`\n") == {
        "api.public_surface:test"
    }
    assert _contradictions(
        "# API reference\n\n- `Mesh`\n"
        "  - `control_points`, `polygons`\n"
        "  - `create_polygon(*indices)`\n"
    ) == {"api.public_surface:test"}
    assert _contradictions(
        "# API reference\n\n- `AnimationClip` — `create_animation_node(name)`\n"
    ) == {"api.public_surface:test"}
    assert _contradictions(
        "# API reference\n\n- `Entity` (base of `Mesh` and the primitive shapes)\n"
    ) == {"api.public_surface:test"}
    assert _contradictions("# API reference\n\n- `ImportException`, `InternalException`\n") == {
        "api.public_surface:test"
    }
    assert _contradictions(
        "# Capabilities\n\n- Import OBJ (with `.mtl` materials) into a scene.\n"
    ) == {"repository.format_directions:test"}
    assert _contradictions(
        "# Product\n\nThe library moves data in and out of OBJ and COLLADA files.\n"
    ) == {"product.limitations:test"}
    assert _contradictions(
        "# API reference\n\n`FbxLoadOptions` is unaffected by the top-level shadowing.\n"
    ) == {"repository.python_import_shadowing:test"}


def test_exact_supported_claims_and_incomplete_catalog_do_not_claim_contradiction() -> None:
    exact = "# API reference\n\n- `Mesh` — `create_polygon(*args)`\n"
    unsupported = "# API reference\n\n- `Mesh` — `unsupported()`\n"

    assert _contradictions(exact) == set()
    assert _contradictions(unsupported, _facts(complete_catalog=False)) == set()
