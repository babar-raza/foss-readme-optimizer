"""Resolve syntax-parsed Rust `pub use` trees into source paths and aliases."""

from __future__ import annotations

from dataclasses import dataclass

from tree_sitter import Node

from readme_agent.ecosystems.rust_syntax import node_text


@dataclass(frozen=True)
class RustUseLeaf:
    """One concrete or wildcard import exposed by a use tree."""

    source_parts: tuple[str, ...]
    exported_name: str
    wildcard: bool = False


def _path_parts(node: Node | None, source: bytes) -> tuple[str, ...]:
    if node is None:
        return ()
    if node.type in {"identifier", "type_identifier", "self", "super", "crate"}:
        return (node_text(node, source),)
    if node.type in {"scoped_identifier", "scoped_type_identifier"}:
        path = node.child_by_field_name("path")
        name = node.child_by_field_name("name")
        return (*_path_parts(path, source), *_path_parts(name, source))
    text = node_text(node, source).strip()
    return tuple(part for part in text.split("::") if part)


def _leaves(node: Node, source: bytes, prefix: tuple[str, ...]) -> list[RustUseLeaf]:
    if node.type in {"identifier", "type_identifier", "self"}:
        name = node_text(node, source)
        return [RustUseLeaf((*prefix, name), name)]
    if node.type == "use_as_clause":
        path = node.child_by_field_name("path")
        alias = node.child_by_field_name("alias")
        return [
            RustUseLeaf(
                (*prefix, *_path_parts(path, source)),
                node_text(alias, source),
            )
        ]
    if node.type == "use_wildcard":
        named = [child for child in node.named_children if child.type != "super"]
        parts: tuple[str, ...] = ()
        for child in named:
            parts = (*parts, *_path_parts(child, source))
        if not parts and any(child.type == "super" for child in node.named_children):
            parts = ("super",)
        return [RustUseLeaf((*prefix, *parts), "*", wildcard=True)]
    if node.type == "scoped_use_list":
        path = node.child_by_field_name("path")
        use_list = next(
            (child for child in node.named_children if child.type == "use_list"),
            None,
        )
        base = (*prefix, *_path_parts(path, source))
        if use_list is None:
            return []
        leaves: list[RustUseLeaf] = []
        for child in use_list.named_children:
            leaves.extend(_leaves(child, source, base))
        return leaves
    if node.type == "use_list":
        leaves = []
        for child in node.named_children:
            leaves.extend(_leaves(child, source, prefix))
        return leaves
    parts = _path_parts(node, source)
    if not parts:
        return []
    return [RustUseLeaf((*prefix, *parts), parts[-1])]


def public_use_leaves(node: Node, source: bytes) -> list[RustUseLeaf]:
    """Return leaves only for an unrestricted public use declaration."""

    visibility = next(
        (child for child in node.children if child.type == "visibility_modifier"),
        None,
    )
    if node_text(visibility, source).strip() != "pub":
        return []
    argument = next(
        (child for child in node.named_children if child.type != "visibility_modifier"),
        None,
    )
    return _leaves(argument, source, ()) if argument is not None else []


def absolute_source_parts(
    current_module: tuple[str, ...],
    source_parts: tuple[str, ...],
) -> tuple[str, ...]:
    """Resolve crate/self/super and relative use paths to an absolute module path."""

    remaining = list(source_parts)
    if remaining and remaining[0] == "crate":
        base: list[str] = []
        remaining.pop(0)
    elif remaining and remaining[0] == "self":
        base = list(current_module)
        remaining.pop(0)
    else:
        base = list(current_module)
    while remaining and remaining[0] == "super":
        if base:
            base.pop()
        remaining.pop(0)
    return (*base, *remaining)
