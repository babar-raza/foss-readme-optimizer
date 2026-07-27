"""Tree-sitter Rust parsing, visibility, documentation, and module helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import tree_sitter_rust
from tree_sitter import Language, Node, Parser, Tree

_RUST_LANGUAGE = Language(tree_sitter_rust.language())
_PARSER = Parser(_RUST_LANGUAGE)
_PATH_ATTRIBUTE = re.compile(r'#\s*\[\s*path\s*=\s*"([^"]+)"\s*\]')
_DOC_ATTRIBUTE = re.compile(r'#\s*\[\s*doc\s*=\s*"([^"]*)"\s*\]')
_DERIVE_ATTRIBUTE = re.compile(r"#\s*\[\s*derive\s*\(([^)]*)\)\s*\]")


@dataclass(frozen=True)
class RustSourceModule:
    """One parsed source module and its Rust path-resolution directory."""

    module: tuple[str, ...]
    source_path: Path
    source: bytes
    tree: Tree
    body: Node
    search_directory: Path
    public_from_parent: bool
    path_attribute: str | None


def node_text(node: Node | None, source: bytes) -> str:
    """Decode one syntax node from its immutable source bytes."""

    if node is None:
        return ""
    return source[node.start_byte : node.end_byte].decode("utf-8", errors="strict")


def top_level_nodes(module: RustSourceModule) -> list[Node]:
    """Return named declarations in a source-file or inline-module body."""

    return list(module.body.named_children)


def bare_public(node: Node, source: bytes) -> bool:
    """Accept only unrestricted `pub`, never `pub(crate)`/`pub(super)`/`pub(in)`."""

    visibility = next(
        (child for child in node.children if child.type == "visibility_modifier"),
        None,
    )
    return node_text(visibility, source).strip() == "pub"


def _preceding_outer_nodes(node: Node, source: bytes) -> list[Node]:
    """Return contiguous comments and attributes belonging to an item."""

    outer: list[Node] = []
    current = node.prev_named_sibling
    following_start = node.start_byte
    while current is not None and current.type in {
        "attribute_item",
        "line_comment",
        "block_comment",
    }:
        if source[current.end_byte : following_start].strip():
            break
        outer.insert(0, current)
        following_start = current.start_byte
        current = current.prev_named_sibling
    return outer


def preceding_attributes(node: Node, source: bytes) -> list[str]:
    """Return contiguous outer attributes immediately preceding an item."""

    return [
        node_text(current, source)
        for current in _preceding_outer_nodes(node, source)
        if current.type == "attribute_item"
    ]


def rustdoc(node: Node, source: bytes) -> str | None:
    """Return the first paragraph of contiguous outer rustdoc."""

    outer = _preceding_outer_nodes(node, source)
    attributes = [
        node_text(current, source) for current in outer if current.type == "attribute_item"
    ]
    attribute_docs = [
        match.group(1) for text in attributes if (match := _DOC_ATTRIBUTE.search(text)) is not None
    ]
    lines = [
        text[3:].strip()
        for current in outer
        if current.type == "line_comment"
        and (text := node_text(current, source).lstrip()).startswith("///")
    ]
    selected = lines or attribute_docs
    paragraph: list[str] = []
    for line in selected:
        if not line and paragraph:
            break
        if line:
            paragraph.append(line)
    return " ".join(paragraph) or None


def derives(node: Node, source: bytes) -> list[str]:
    """Return stable derive trait names from outer attributes."""

    values: set[str] = set()
    for text in preceding_attributes(node, source):
        match = _DERIVE_ATTRIBUTE.search(text)
        if match:
            values.update(part.strip() for part in match.group(1).split(",") if part.strip())
    return sorted(values)


def _path_attribute(node: Node, source: bytes) -> str | None:
    for text in preceding_attributes(node, source):
        match = _PATH_ATTRIBUTE.search(text)
        if match:
            return match.group(1)
    return None


def _external_module_path(
    parent: RustSourceModule,
    name: str,
    path_attribute: str | None,
) -> tuple[Path, Path]:
    if path_attribute:
        path = (parent.source_path.parent / path_attribute).resolve()
        search_directory = path.parent / path.stem if path.name != "mod.rs" else path.parent
        return path, search_directory
    direct = parent.search_directory / f"{name}.rs"
    nested = parent.search_directory / name / "mod.rs"
    if direct.is_file():
        return direct.resolve(), (parent.search_directory / name).resolve()
    if nested.is_file():
        return nested.resolve(), nested.parent.resolve()
    raise ValueError(
        f"Rust module {('::'.join((*parent.module, name)))} has no source file "
        f"at {direct} or {nested}"
    )


def parse_rust_source_file(
    source_path: Path,
    *,
    module: tuple[str, ...],
    search_directory: Path,
    public_from_parent: bool,
    path_attribute: str | None,
) -> RustSourceModule:
    source = source_path.read_bytes()
    tree = _PARSER.parse(source)
    if tree.root_node.has_error:
        raise ValueError(f"Rust syntax parse error: {source_path}")
    return RustSourceModule(
        module=module,
        source_path=source_path.resolve(),
        source=source,
        tree=tree,
        body=tree.root_node,
        search_directory=search_directory.resolve(),
        public_from_parent=public_from_parent,
        path_attribute=path_attribute,
    )


def load_rust_modules(lib_path: Path) -> list[RustSourceModule]:
    """Resolve external, inline, and `#[path]` modules from one crate root."""

    root = parse_rust_source_file(
        lib_path.resolve(),
        module=(),
        search_directory=lib_path.parent,
        public_from_parent=True,
        path_attribute=None,
    )
    modules: list[RustSourceModule] = []
    pending = [root]
    seen: set[tuple[tuple[str, ...], Path]] = set()
    while pending:
        current = pending.pop()
        identity = (current.module, current.source_path)
        if identity in seen:
            continue
        seen.add(identity)
        modules.append(current)
        for node in top_level_nodes(current):
            if node.type != "mod_item":
                continue
            name = node_text(node.child_by_field_name("name"), current.source)
            if not name:
                continue
            module_path = (*current.module, name)
            path_attribute = _path_attribute(node, current.source)
            body = node.child_by_field_name("body")
            is_public = bare_public(node, current.source)
            if body is not None:
                pending.append(
                    RustSourceModule(
                        module=module_path,
                        source_path=current.source_path,
                        source=current.source,
                        tree=current.tree,
                        body=body,
                        search_directory=current.search_directory / name,
                        public_from_parent=is_public,
                        path_attribute=path_attribute,
                    )
                )
                continue
            path, search_directory = _external_module_path(
                current,
                name,
                path_attribute,
            )
            pending.append(
                parse_rust_source_file(
                    path,
                    module=module_path,
                    search_directory=search_directory,
                    public_from_parent=is_public,
                    path_attribute=path_attribute,
                )
            )
    return sorted(modules, key=lambda item: (item.module, item.source_path.as_posix()))
