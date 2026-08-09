"""Match constrained API claim shapes to exact public-surface fact coordinates."""

from __future__ import annotations

import hashlib
import json
import re

from readme_agent.readme.claim_accountability_api_index import api_coordinate_index
from readme_agent.readme.claim_accountability_api_shapes import (
    class_headers,
    coded_references,
    compatible_member_reference,
    context_classes,
    has_only_api_punctuation,
    is_matching_load_save_pair,
    is_primitive_to_mesh_claim,
    member_surfaces,
    right_side_is_constrained,
)
from readme_agent.readme.claim_accountability_models import StructuredFactCoordinateV1

_LIST_ITEM = re.compile(r"(?s)^\s*[-+*]\s+(?P<body>.+?)\s*$")


def _coordinate(*, fact_id: str, path: str, value: object) -> StructuredFactCoordinateV1:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return StructuredFactCoordinateV1(
        fact_id=fact_id,
        field="api.public_surface",
        path=path,
        value_sha256=hashlib.sha256(payload.encode("utf-8")).hexdigest(),
    )


def api_module_export_fact_coordinates(
    fact_id: str,
    value: object,
    export_names: set[str],
) -> list[StructuredFactCoordinateV1]:
    """Bind requested module exports to exact public-surface coordinates."""

    if not isinstance(value, dict) or not export_names:
        return []
    modules = value.get("modules")
    if not isinstance(modules, list):
        return []
    requested = {name.casefold() for name in export_names}
    coordinates: list[StructuredFactCoordinateV1] = []
    matched: set[str] = set()
    for module in modules:
        if not isinstance(module, dict) or not isinstance(module.get("module"), str):
            continue
        module_name = module["module"]
        exports = module.get("exports")
        if not isinstance(exports, list):
            continue
        for export in exports:
            if not isinstance(export, str) or export.casefold() not in requested:
                continue
            matched.add(export.casefold())
            coordinates.append(
                _coordinate(
                    fact_id=fact_id,
                    path=f"/modules/{module_name}/exports/{export}",
                    value={"module": module_name, "export": export},
                )
            )
    if matched != requested:
        return []
    return sorted(set(coordinates), key=lambda item: (item.path, item.value_sha256))


def api_mcp_server_fact_coordinates(
    fact_id: str,
    value: object,
    *,
    include_factory: bool = False,
    include_runner: bool = False,
    tool_names: set[str] | None = None,
) -> list[StructuredFactCoordinateV1]:
    """Bind requested MCP factory, runner, and tools to exact coordinates."""

    if not isinstance(value, dict) or not isinstance(value.get("mcp_server"), dict):
        return []
    mcp = value["mcp_server"]
    coordinates: list[StructuredFactCoordinateV1] = []
    requested_tools = {name.casefold() for name in tool_names or set()}
    if include_factory:
        factory = mcp.get("factory")
        if not isinstance(factory, str):
            return []
        coordinates.append(_coordinate(fact_id=fact_id, path="/mcp_server/factory", value=factory))
    if include_runner:
        runner = mcp.get("runner")
        if not isinstance(runner, str):
            return []
        coordinates.append(_coordinate(fact_id=fact_id, path="/mcp_server/runner", value=runner))
    if requested_tools:
        tools = mcp.get("tools")
        if not isinstance(tools, list):
            return []
        matched = {
            tool.casefold(): tool
            for tool in tools
            if isinstance(tool, str) and tool.casefold() in requested_tools
        }
        if set(matched) != requested_tools:
            return []
        coordinates.extend(
            _coordinate(
                fact_id=fact_id,
                path=f"/mcp_server/tools/{tool}",
                value=tool,
            )
            for tool in matched.values()
        )
    return sorted(set(coordinates), key=lambda item: (item.path, item.value_sha256))


def _class_coordinate(
    fact_id: str, class_name: str, class_item: dict, *, prefix: str = ""
) -> StructuredFactCoordinateV1:
    return _coordinate(
        fact_id=fact_id,
        path=f"{prefix}/classes/{class_name}",
        value={
            "name": class_name,
            "module": class_item.get("module"),
            "qualified_name": class_item.get("qualified_name"),
            "bases": class_item.get("bases"),
            "source_path": class_item.get("source_path"),
            "source_sha256": class_item.get("source_sha256"),
        },
    )


def _member_groups(class_item: dict) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    members = class_item.get("members")
    if not isinstance(members, list):
        return groups
    for member in members:
        if isinstance(member, dict) and isinstance(member.get("name"), str):
            groups.setdefault(member["name"], []).append(member)
    return groups


def _member_coordinate(
    fact_id: str,
    class_name: str,
    member_name: str,
    group: list[dict],
    *,
    prefix: str = "",
) -> StructuredFactCoordinateV1:
    return _coordinate(
        fact_id=fact_id,
        path=f"{prefix}/classes/{class_name}/members/{member_name}",
        value={"class": class_name, "members": group},
    )


def _constructor_coordinate(
    fact_id: str,
    class_name: str,
    constructor: dict,
    *,
    prefix: str = "",
) -> StructuredFactCoordinateV1:
    return _coordinate(
        fact_id=fact_id,
        path=f"{prefix}/classes/{class_name}/constructor",
        value={"class": class_name, "constructor": constructor},
    )


def _base_coordinate(
    fact_id: str,
    class_name: str,
    claimed_base: str,
    bases: list,
    *,
    prefix: str = "",
) -> StructuredFactCoordinateV1:
    return _coordinate(
        fact_id=fact_id,
        path=f"{prefix}/classes/{class_name}/bases/{claimed_base}",
        value={"class": class_name, "claimed_base": claimed_base, "bases": bases},
    )


def _direct_constructor_coordinates(
    body: str,
    fact_id: str,
    classes_by_name: dict[str, dict],
    *,
    prefix: str,
    public_class_names: frozenset[str],
) -> list[StructuredFactCoordinateV1] | None:
    references = coded_references(body)
    if len(references) != 1 or not has_only_api_punctuation(body):
        return None
    reference, _ = references[0]
    match = re.fullmatch(r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)\([^)]*\)", reference)
    if match is None:
        return None
    class_name = match.group("name")
    if prefix and class_name not in public_class_names:
        return []
    class_item = classes_by_name.get(class_name)
    constructor = class_item.get("constructor") if isinstance(class_item, dict) else None
    if not isinstance(class_item, dict) or not isinstance(constructor, dict):
        return []
    surface = constructor.get("surface")
    if not isinstance(surface, str) or not compatible_member_reference(reference, [surface]):
        return []
    return [
        _class_coordinate(fact_id, class_name, class_item, prefix=prefix),
        _constructor_coordinate(fact_id, class_name, constructor, prefix=prefix),
    ]


def _primitive_group_coordinates(
    body: str,
    context: str,
    fact_id: str,
    classes_by_name: dict[str, dict],
    *,
    prefix: str = "",
) -> list[StructuredFactCoordinateV1] | None:
    if not is_primitive_to_mesh_claim(body):
        return None
    class_names = context_classes(context, classes_by_name)
    if not class_names or "Mesh" not in classes_by_name:
        return []
    coordinates = []
    for class_name in class_names:
        group = _member_groups(classes_by_name[class_name]).get("to_mesh", [])
        surfaces = member_surfaces(group)
        if not group or not compatible_member_reference("to_mesh()", surfaces):
            return []
        coordinates.append(_member_coordinate(fact_id, class_name, "to_mesh", group, prefix=prefix))
    return coordinates


def api_structured_fact_coordinates(
    text: str,
    context: str,
    fact_id: str,
    value: object,
) -> list[StructuredFactCoordinateV1]:
    """Return coordinates only for a completely recognized API list-item shape."""

    if not isinstance(value, dict) or (item := _LIST_ITEM.fullmatch(text.strip())) is None:
        return []
    index = api_coordinate_index(value)
    if not index.classes_by_name:
        return []
    body = item.group("body")
    primitive_coordinates = _primitive_group_coordinates(
        body,
        context,
        fact_id,
        index.classes_by_name,
        prefix=index.coordinate_prefix,
    )
    if primitive_coordinates is not None:
        return primitive_coordinates
    constructor_coordinates = _direct_constructor_coordinates(
        body,
        fact_id,
        index.classes_by_name,
        prefix=index.coordinate_prefix,
        public_class_names=index.package_export_names,
    )
    if constructor_coordinates is not None:
        return constructor_coordinates
    headers: list[tuple[str, str | None, bool]] = []
    if "—" in body:
        left, right = body.split("—", 1)
        parsed_headers = class_headers(left)
        if parsed_headers is None:
            return []
        headers = parsed_headers
        class_names = [name for name, _, _ in headers]
        if any(
            name not in index.classes_by_name
            or (index.coordinate_prefix and name not in index.package_export_names)
            for name in class_names
        ):
            return []
        for class_name, claimed_base, base_role in headers:
            if base_role and not any(
                isinstance(item.get("bases"), list) and class_name in item["bases"]
                for item in index.classes_by_name.values()
            ):
                return []
            if claimed_base is None:
                continue
            bases = index.classes_by_name[class_name].get("bases")
            if (
                claimed_base not in index.classes_by_name
                or not isinstance(bases, list)
                or claimed_base not in bases
            ):
                return []
        if not right_side_is_constrained(right, class_names):
            return []
        references = coded_references(right)
        declared_members_only = right.strip().casefold().startswith("adds ")
    else:
        references = coded_references(body)
        declared_members_only = False
        direct = [reference for reference, _ in references]
        if (
            has_only_api_punctuation(body)
            and direct
            and all(
                reference in index.classes_by_name
                and (not index.coordinate_prefix or reference in index.package_export_names)
                for reference in direct
            )
        ):
            return [
                _class_coordinate(
                    fact_id,
                    name,
                    index.classes_by_name[name],
                    prefix=index.coordinate_prefix,
                )
                for name in direct
            ]
        class_names = context_classes(context, index.classes_by_name)
        if (
            not class_names
            or not has_only_api_punctuation(body)
            or any(
                index.coordinate_prefix and name not in index.package_export_names
                for name in class_names
            )
        ):
            return []
    if (
        not class_names
        or not references
        or any(class_name not in index.classes_by_name for class_name in class_names)
    ):
        return []
    coordinates = (
        [
            _class_coordinate(
                fact_id,
                name,
                index.classes_by_name[name],
                prefix=index.coordinate_prefix,
            )
            for name in class_names
        ]
        if "—" in body
        else []
    )
    if "—" in body:
        for class_name, claimed_base, _ in headers:
            if claimed_base is None:
                continue
            bases = index.classes_by_name[class_name]["bases"]
            coordinates.extend(
                [
                    _class_coordinate(
                        fact_id,
                        claimed_base,
                        index.classes_by_name[claimed_base],
                        prefix=index.coordinate_prefix,
                    ),
                    _base_coordinate(
                        fact_id,
                        class_name,
                        claimed_base,
                        bases,
                        prefix=index.coordinate_prefix,
                    ),
                ]
            )
    for reference, tail in references:
        if reference in index.classes_by_name:
            coordinates.append(
                _class_coordinate(
                    fact_id,
                    reference,
                    index.classes_by_name[reference],
                    prefix=index.coordinate_prefix,
                )
            )
            continue
        targets = class_names
        folded_tail = tail.casefold()
        if "save only" in folded_tail:
            targets = [name for name in class_names if "save" in name.casefold()]
        elif "load only" in folded_tail:
            targets = [name for name in class_names if "load" in name.casefold()]
        if not targets:
            return []
        member_name_match = re.match(r"[A-Za-z_][A-Za-z0-9_]*", reference)
        if member_name_match is None:
            return []
        member_name = member_name_match.group(0)
        compatible_targets = []
        target_groups = {}
        for class_name in targets:
            group = _member_groups(index.classes_by_name[class_name]).get(member_name, [])
            surfaces = member_surfaces(group)
            if (
                group
                and compatible_member_reference(reference, surfaces)
                and (
                    not declared_members_only
                    or all(member.get("declared_by") == class_name for member in group)
                )
            ):
                compatible_targets.append(class_name)
                target_groups[class_name] = group
        scoped_targets = compatible_targets
        if not ("save only" in folded_tail or "load only" in folded_tail):
            if len(compatible_targets) != len(targets) and not (
                is_matching_load_save_pair(class_names) and len(compatible_targets) == 1
            ):
                return []
        if not scoped_targets:
            return []
        for class_name in scoped_targets:
            coordinates.append(
                _member_coordinate(
                    fact_id,
                    class_name,
                    member_name,
                    target_groups[class_name],
                    prefix=index.coordinate_prefix,
                )
            )
    return coordinates


def api_class_fact_coordinates(
    fact_id: str,
    value: object,
    class_names: list[str],
) -> list[StructuredFactCoordinateV1]:
    """Return exact coordinates for unambiguous public class names."""

    if not isinstance(value, dict):
        return []
    index = api_coordinate_index(value)
    requested = list(dict.fromkeys(class_names))
    if not requested or any(name not in index.classes_by_name for name in requested):
        return []
    if index.coordinate_prefix and any(
        name not in index.package_export_names for name in requested
    ):
        return []
    return [
        _class_coordinate(
            fact_id,
            name,
            index.classes_by_name[name],
            prefix=index.coordinate_prefix,
        )
        for name in requested
    ]
