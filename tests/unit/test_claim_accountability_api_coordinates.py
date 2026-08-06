"""Constrained structured coordinates for repository-extracted Python API claims."""

from __future__ import annotations

import hashlib
import json

import pytest

from readme_agent.readme.claim_accountability_api_coordinates import (
    api_structured_fact_coordinates,
)

FACT_ID = "api.public_surface:repository-source"


def _class(
    name: str,
    *surfaces: str,
    bases: tuple[str, ...] = (),
    constructor: str | None = None,
    returns: dict[str, str] | None = None,
    declared_by: str | None = None,
) -> dict:
    return {
        "name": name,
        "module": "package",
        "qualified_name": f"package.{name}",
        "bases": list(bases),
        "constructor": (
            {"surface": constructor, "source_path": f"package/{name}.py"} if constructor else None
        ),
        "source_path": f"package/{name}.py",
        "source_sha256": "a" * 64,
        "members": [
            {
                "name": surface.split("(", 1)[0].split(":", 1)[0],
                "surface": surface,
                "return_annotation": (returns or {}).get(surface.split("(", 1)[0]),
                "declared_by": declared_by or name,
                "source_path": f"package/{name}.py",
                "source_sha256": "a" * 64,
            }
            for surface in surfaces
        ],
    }


API_VALUE = {
    "classes": [
        _class("Material", "get_texture(slot_name)", "set_texture(slot_name, texture)"),
        _class(
            "Mesh",
            "control_points: Vector4",
            "create_polygon(*args)",
            "triangulate()",
            constructor="Mesh(name=None, height_map=None)",
        ),
        *[_class(name, "to_mesh()") for name in ("Box", "Cylinder", "Sphere")],
        _class("LoadOptions", "scale: float", "flip_coordinate_system: bool"),
        _class(
            "SaveOptions",
            "binary_mode: bool",
            "scale: float",
            "flip_coordinate_system: bool",
        ),
        _class("Entity", "excluded: bool", "parent_node", "parent_nodes"),
        _class("Transform", "translation: Vector3", "scaling: Vector3"),
        _class("GlobalTransform", "translation: Vector3", "scale: Vector3"),
        _class("Camera", "near_plane: float", "far_plane: float"),
        _class("Light"),
        _class("Vector2", "x: float", "y: float", "length: float"),
        _class(
            "Vector3",
            "x: float",
            "y: float",
            "z: float",
            "length: float",
            "normalize()",
            "dot(rhs)",
            "cross(rhs)",
        ),
        _class("Vector4", "x: float", "y: float", "z: float", "w: float"),
        _class("KeyframeSequence", "pre_behavior: Extrapolation", "post_behavior: Extrapolation"),
        _class("FbxLoadOptions", "compatible_mode: bool"),
        _class("FbxSaveOptions", "export_textures: bool", "embed_textures: bool"),
        _class(
            "Matrix4",
            "translate(tx, ty=None, tz=None)",
            "scale(sx, sy=None, sz=None)",
            "rotate(angle, axis=None)",
            "decompose(translation, scaling, rotation)",
            "inverse()",
            "get_identity()",
        ),
        _class(
            "Quaternion",
            "slerp(t, v1, v2)",
            "to_matrix(translation=None)",
            "from_euler_angle(pitch, yaw, roll)",
            "from_angle_axis(a, axis)",
        ),
        _class(
            "BoundingBox", "minimum", "maximum", "center", "size", "merge(*args)", "contains(arg)"
        ),
        _class(
            "KeyFrame",
            "time: float",
            "value: float",
            "interpolation: Interpolation",
            "tangent_weight_mode: WeightedMode",
            "step_mode: StepMode",
            "tension: float",
            "continuity: float",
            "bias: float",
        ),
        _class(
            "Node",
            "create_child_node(node_name=None, entity=None, material=None)",
            returns={"create_child_node": "'Node'"},
        ),
        _class("LambertMaterial"),
        _class(
            "PhongMaterial",
            "specular_color",
            "specular_factor",
            "shininess",
            "reflection_color",
            bases=("LambertMaterial",),
        ),
        _class("AnimationChannel", "component_type", bases=("KeyframeSequence",)),
        _class("Extrapolation"),
        _class("Interpolation"),
    ],
    "modules": [],
}


def _paths(text: str, context: str = "API reference", value: dict | None = None) -> set[str]:
    return {
        item.path
        for item in api_structured_fact_coordinates(
            text, context, FACT_ID, value if value is not None else API_VALUE
        )
    }


def test_class_and_member_dash_shape_requires_every_member() -> None:
    assert _paths("- `Material` — `get_texture(slot_name)`, `set_texture(slot_name, texture)`") == {
        "/classes/Material",
        "/classes/Material/members/get_texture",
        "/classes/Material/members/set_texture",
    }


def test_unproved_base_role_label_does_not_invent_inheritance() -> None:
    assert (
        _paths("- `Material` (base) — `get_texture(slot_name)`, `set_texture(slot_name, texture)`")
        == set()
    )


def test_source_confirmed_parent_class_binds_contextual_child_members() -> None:
    assert _paths(
        "  - `control_points: Vector4`, `triangulate()`",
        "API reference\nMeshes\n`Mesh`",
    ) == {
        "/classes/Mesh/members/control_points",
        "/classes/Mesh/members/triangulate",
    }


def test_constructor_syntax_identifies_context_without_approving_constructor_claim() -> None:
    assert _paths(
        "  - `control_points: Vector4`",
        "API reference\n`Mesh(name)`",
    ) == {"/classes/Mesh/members/control_points"}
    assert _paths("- `Mesh(name)`") == {
        "/classes/Mesh",
        "/classes/Mesh/constructor",
    }


def test_structured_return_annotation_and_inheritance_shapes_bind_exactly() -> None:
    assert _paths("- `Node` — `create_child_node(node_name, entity, material) -> 'Node'`") == {
        "/classes/Node",
        "/classes/Node/members/create_child_node",
    }
    assert _paths(
        "- `PhongMaterial(LambertMaterial)` — adds `specular_color`, `specular_factor`, "
        "`shininess`, `reflection_color`"
    ) == {
        "/classes/LambertMaterial",
        "/classes/PhongMaterial",
        "/classes/PhongMaterial/bases/LambertMaterial",
        "/classes/PhongMaterial/members/reflection_color",
        "/classes/PhongMaterial/members/shininess",
        "/classes/PhongMaterial/members/specular_color",
        "/classes/PhongMaterial/members/specular_factor",
    }
    assert _paths("- `AnimationChannel` (extends `KeyframeSequence`) — `component_type`") == {
        "/classes/AnimationChannel",
        "/classes/AnimationChannel/bases/KeyframeSequence",
        "/classes/AnimationChannel/members/component_type",
        "/classes/KeyframeSequence",
    }


def test_inspectable_coordinate_catalog_is_hash_bound_and_path_prefixed() -> None:
    catalog = {
        "schema_version": 1,
        "public_api_source_sha256": "b" * 64,
        "modules": [
            {
                "module": "package",
                "exports": [item["name"] for item in API_VALUE["classes"]],
                "source_path": "package/__init__.py",
            }
        ],
        "classes": API_VALUE["classes"],
        "functions": [],
    }
    payload = json.dumps(catalog, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )
    wrapped = {
        "public_api_source_sha256": "b" * 64,
        "coordinate_catalog": {
            **catalog,
            "content_sha256": hashlib.sha256(payload).hexdigest(),
        },
    }

    assert _paths("- `Mesh(name)`", value=wrapped) == {
        "/coordinate_catalog/classes/Mesh",
        "/coordinate_catalog/classes/Mesh/constructor",
    }
    wrapped["coordinate_catalog"]["content_sha256"] = "0" * 64
    assert _paths("- `Mesh(name)`", value=wrapped) == set()


def test_every_contextual_primitive_must_expose_to_mesh() -> None:
    claim = (
        "  - each exposes `to_mesh() -> 'Mesh'` to convert the parameterized primitive "
        "into a concrete mesh"
    )
    assert _paths(claim, "API reference\n`Box`, `Cylinder`, `Sphere`") == {
        "/classes/Box/members/to_mesh",
        "/classes/Cylinder/members/to_mesh",
        "/classes/Sphere/members/to_mesh",
    }
    assert _paths(claim, "API reference\n`Box`, `Material`") == set()


def test_grouped_classes_require_common_members_except_explicit_scope_qualifier() -> None:
    assert _paths(
        "- `LoadOptions` / `SaveOptions` — `binary_mode` (save only), `scale`, "
        "`flip_coordinate_system`"
    ) == {
        "/classes/LoadOptions",
        "/classes/LoadOptions/members/flip_coordinate_system",
        "/classes/LoadOptions/members/scale",
        "/classes/SaveOptions",
        "/classes/SaveOptions/members/binary_mode",
        "/classes/SaveOptions/members/flip_coordinate_system",
        "/classes/SaveOptions/members/scale",
    }


def test_grouped_load_save_options_bind_only_each_members_exact_owner() -> None:
    assert _paths(
        "- `FbxLoadOptions` / `FbxSaveOptions` — `compatible_mode`, `export_textures`, "
        "`embed_textures` (see [Scope and limitations](#scope-and-limitations))"
    ) == {
        "/classes/FbxLoadOptions",
        "/classes/FbxLoadOptions/members/compatible_mode",
        "/classes/FbxSaveOptions",
        "/classes/FbxSaveOptions/members/embed_textures",
        "/classes/FbxSaveOptions/members/export_textures",
    }


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "- `Matrix4` — `translate()`, `scale()`, `rotate()`, `decompose()`, "
            "`inverse()`, `get_identity()`",
            {
                "/classes/Matrix4",
                "/classes/Matrix4/members/decompose",
                "/classes/Matrix4/members/get_identity",
                "/classes/Matrix4/members/inverse",
                "/classes/Matrix4/members/rotate",
                "/classes/Matrix4/members/scale",
                "/classes/Matrix4/members/translate",
            },
        ),
        (
            "- `Quaternion` — `slerp(t, v1, v2)`, `to_matrix()`, "
            "`from_euler_angle()`, `from_angle_axis()`",
            {
                "/classes/Quaternion",
                "/classes/Quaternion/members/from_angle_axis",
                "/classes/Quaternion/members/from_euler_angle",
                "/classes/Quaternion/members/slerp",
                "/classes/Quaternion/members/to_matrix",
            },
        ),
        (
            "- `BoundingBox` — `minimum`, `maximum`, `center`, `size`, `merge()`, `contains()`",
            {
                "/classes/BoundingBox",
                "/classes/BoundingBox/members/center",
                "/classes/BoundingBox/members/contains",
                "/classes/BoundingBox/members/maximum",
                "/classes/BoundingBox/members/merge",
                "/classes/BoundingBox/members/minimum",
                "/classes/BoundingBox/members/size",
            },
        ),
        (
            "- `KeyFrame` — `time`, `value`, `interpolation` (`Interpolation`), "
            "tangent/weight fields (`tangent_weight_mode`, `step_mode`, `tension`, "
            "`continuity`, `bias`)",
            {
                "/classes/Interpolation",
                "/classes/KeyFrame",
                "/classes/KeyFrame/members/bias",
                "/classes/KeyFrame/members/continuity",
                "/classes/KeyFrame/members/interpolation",
                "/classes/KeyFrame/members/step_mode",
                "/classes/KeyFrame/members/tangent_weight_mode",
                "/classes/KeyFrame/members/tension",
                "/classes/KeyFrame/members/time",
                "/classes/KeyFrame/members/value",
            },
        ),
    ],
)
def test_exact_repository_proved_utility_and_keyframe_shapes(text: str, expected: set[str]) -> None:
    assert _paths(text) == expected


def test_parenthesized_class_reference_is_allowed_only_as_a_resolved_type() -> None:
    assert _paths("- `KeyframeSequence` — `pre_behavior`/`post_behavior` (`Extrapolation`)") == {
        "/classes/Extrapolation",
        "/classes/KeyframeSequence",
        "/classes/KeyframeSequence/members/post_behavior",
        "/classes/KeyframeSequence/members/pre_behavior",
    }


@pytest.mark.parametrize(
    ("text", "context"),
    [
        (
            "  - `parent_node`, `parent_nodes`, `excluded`, `name`",
            "API reference\n`Entity`",
        ),
        (
            "- `Entity` (base of `Mesh` and the primitive shapes)",
            "API reference",
        ),
        (
            "  - `translation`, `scaling`",
            "API reference\n`Transform` / `GlobalTransform`",
        ),
        (
            "  - `near_plane`, `far_plane`",
            "API reference\n`Camera`, `Light`",
        ),
        (
            "- `Vector2`, `Vector3`, `Vector4` — `x`/`y`/`z`/`w`, `length`, "
            "`normalize()`, `dot()`, `cross()`",
            "API reference",
        ),
        ("  - `create_polygon(*indices)`", "API reference\n`Mesh(name)`"),
        ("- `Material` — `get_texture(slot_name)`, `missing_member`", "API reference"),
        (
            "- `FbxLoadOptions` / `SaveOptions` — `compatible_mode`, `binary_mode`",
            "API reference",
        ),
        ("- `OtherProductClass` — `open()`", "API reference"),
        ("  - `near_plane`", "API reference\n`Camera`, `Light`"),
    ],
    ids=[
        "entity-name",
        "global-transform-scaling",
        "light-inherited-camera-members",
        "vector2-vector4-unsupported-operations",
        "unproved-base-prose",
        "wrong-signature",
        "partial-list",
        "mismatched-load-save-pair",
        "cross-product",
        "ambiguous-context",
    ],
)
def test_unverified_or_ambiguous_api_claims_remain_unbound(text: str, context: str) -> None:
    assert _paths(text, context) == set()


def test_class_only_list_requires_every_reference_to_exist() -> None:
    assert _paths("- `Material`, `Mesh`") == {"/classes/Material", "/classes/Mesh"}
    assert _paths("- `Material`, `MissingClass`") == set()
