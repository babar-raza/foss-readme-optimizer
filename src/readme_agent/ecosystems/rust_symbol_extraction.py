"""Extract Rust definitions, public members, traits, docs, and implementations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from tree_sitter import Node

from readme_agent.ecosystems.rust_api_schema import RustSymbolKind
from readme_agent.ecosystems.rust_syntax import (
    RustSourceModule,
    bare_public,
    derives,
    node_text,
    rustdoc,
    top_level_nodes,
)

_ITEM_KINDS: dict[str, RustSymbolKind] = {
    "struct_item": "struct",
    "union_item": "union",
    "enum_item": "enum",
    "trait_item": "trait",
    "function_item": "function",
    "type_item": "type_alias",
    "const_item": "constant",
    "static_item": "static",
}


@dataclass
class RustDefinition:
    """Mutable extraction record resolved into immutable public symbols later."""

    key: tuple[str, ...]
    name: str
    kind: RustSymbolKind
    module: RustSourceModule
    node: Node
    type_text: str | None
    docs: str | None
    derive_traits: list[str]
    supertraits: list[str]
    members: list[dict[str, Any]] = field(default_factory=list)
    implemented_traits: set[str] = field(default_factory=set)


def _type_text(node: Node, module: RustSourceModule) -> str | None:
    selected = node.child_by_field_name("type") or node.child_by_field_name("return_type")
    return node_text(selected, module.source) or None


def _supertraits(node: Node, module: RustSourceModule) -> list[str]:
    bounds = node.child_by_field_name("bounds")
    if bounds is None:
        return []
    return sorted(
        {
            node_text(child, module.source)
            for child in bounds.named_children
            if child.type in {"type_identifier", "scoped_type_identifier", "generic_type"}
        }
    )


def _member(
    node: Node,
    module: RustSourceModule,
    kind: RustSymbolKind,
) -> dict[str, Any] | None:
    name = node_text(node.child_by_field_name("name"), module.source)
    if not name:
        return None
    return {
        "name": name,
        "kind": kind,
        "node": node,
        "module": module,
        "type_text": _type_text(node, module),
        "rustdoc": rustdoc(node, module.source),
    }


def _declared_members(definition: RustDefinition) -> list[dict[str, Any]]:
    body = definition.node.child_by_field_name("body")
    if body is None:
        return []
    members: list[dict[str, Any]] = []
    if definition.kind in {"struct", "union"}:
        for node in body.named_children:
            if node.type == "field_declaration" and bare_public(node, definition.module.source):
                if item := _member(node, definition.module, "field"):
                    members.append(item)
    elif definition.kind == "enum":
        for node in body.named_children:
            if node.type == "enum_variant":
                if item := _member(node, definition.module, "variant"):
                    members.append(item)
    elif definition.kind == "trait":
        for node in body.named_children:
            if node.type in {"function_item", "function_signature_item"}:
                if item := _member(node, definition.module, "method"):
                    members.append(item)
    return members


def extract_rust_definitions(
    modules: list[RustSourceModule],
) -> dict[tuple[str, ...], RustDefinition]:
    """Extract unrestricted-public declarations from every resolved module."""

    definitions: dict[tuple[str, ...], RustDefinition] = {}
    for module in modules:
        for node in top_level_nodes(module):
            kind = _ITEM_KINDS.get(node.type)
            if kind is None or not bare_public(node, module.source):
                continue
            name = node_text(node.child_by_field_name("name"), module.source)
            if not name:
                continue
            definition = RustDefinition(
                key=(*module.module, name),
                name=name,
                kind=kind,
                module=module,
                node=node,
                type_text=_type_text(node, module),
                docs=rustdoc(node, module.source),
                derive_traits=derives(node, module.source),
                supertraits=_supertraits(node, module),
            )
            definition.members.extend(_declared_members(definition))
            definitions[definition.key] = definition
    return definitions


def _bare_type_name(text: str) -> str:
    selected = text.split("<", 1)[0].lstrip("&").strip()
    return selected.rsplit("::", 1)[-1]


def associate_rust_implementations(
    modules: list[RustSourceModule],
    definitions: dict[tuple[str, ...], RustDefinition],
) -> None:
    """Attach public inherent and trait implementation methods to their types."""

    by_name: dict[str, list[RustDefinition]] = {}
    for definition in definitions.values():
        by_name.setdefault(definition.name, []).append(definition)
    for module in modules:
        for node in top_level_nodes(module):
            if node.type != "impl_item":
                continue
            target = _bare_type_name(node_text(node.child_by_field_name("type"), module.source))
            candidates = by_name.get(target, [])
            if not candidates:
                continue
            same_module = [item for item in candidates if item.module.module == module.module]
            definition = (same_module or candidates)[0]
            trait = _bare_type_name(node_text(node.child_by_field_name("trait"), module.source))
            if trait:
                definition.implemented_traits.add(trait)
            body = node.child_by_field_name("body")
            if body is None:
                continue
            for child in body.named_children:
                if child.type != "function_item":
                    continue
                if not trait and not bare_public(child, module.source):
                    continue
                if item := _member(child, module, "method"):
                    definition.members.append(item)
