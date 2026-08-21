"""Verify cited non-Python source regions with the vendored tree-sitter parsers."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from tree_sitter import Tree

from readme_agent.vendored_asposeorg.scripts.pipeline.extraction.tree_helpers import (
    collect_nodes,
    get_parser,
    node_text,
)

SourcePolarity = Literal["positive", "negative", "unresolved"]

_LANGUAGE_BY_SUFFIX = {
    ".cs": "csharp",
    ".java": "java",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".h": "cpp",
    ".hpp": "cpp",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".go": "go",
    ".rs": "rust",
}
_METHOD_TYPES = {
    "constructor_declaration",
    "function_declaration",
    "function_definition",
    "function_item",
    "method_declaration",
    "method_definition",
}
_CLASS_TYPES = {
    "class_declaration",
    "class_specifier",
    "impl_item",
    "interface_declaration",
    "struct_item",
    "struct_specifier",
}
_BODY_TYPES = {
    "block",
    "compound_statement",
    "function_body",
    "statement_block",
}
_NEGATIVE_NODE_TYPES = {
    "call_expression",
    "expression_statement",
    "macro_invocation",
    "raise_statement",
    "throw_statement",
}
_CONCRETE_DECLARATION_TYPES = {
    "enum_declaration",
    "enum_item",
    "enum_member_declaration",
    "enumerator",
}
_NOT_IMPLEMENTED_RE = re.compile(
    r"(?:NotImplemented(?:Exception|Error)?|UnsupportedOperationException|"
    r"NotSupported(?:Operation)?Exception|not\s+(?:implemented|supported)|"
    r"unimplemented!\s*\(|todo!\s*\(|panic!\s*\(\s*['\"]not implemented)",
    re.IGNORECASE,
)


class TreeSitterEvidenceCache:
    """Snapshot-scoped bytes and syntax trees for non-Python evidence."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.sources: dict[Path, bytes | None] = {}
        self.trees: dict[Path, Tree | None] = {}
        self.line_signals: dict[tuple[Path, int], SourcePolarity] = {}
        self.declaration_signals: dict[tuple[Path, str, int, int], SourcePolarity] = {}

    def source_and_tree(self, path: Path) -> tuple[bytes | None, Tree | None]:
        if path not in self.sources:
            try:
                self.sources[path] = path.read_bytes()
            except OSError:
                self.sources[path] = None
        source = self.sources[path]
        if path not in self.trees:
            language = _LANGUAGE_BY_SUFFIX.get(path.suffix.casefold())
            if source is None or language is None:
                self.trees[path] = None
            else:
                try:
                    self.trees[path] = get_parser(language).parse(source)
                except (ImportError, LookupError, RuntimeError, ValueError):
                    self.trees[path] = None
        return source, self.trees[path]


def _ancestor(node, types: set[str]):
    current = node
    while current is not None:
        if current.type in types:
            return current
        current = current.parent
    return None


def _nested_declaration_on_row(node, types: set[str], row: int):
    """Return the narrowest wrapped declaration that contains ``row``.

    TypeScript and JavaScript expose exported declarations through an
    ``export_statement`` wrapper.  A point lookup on the declaration line can
    therefore return the wrapper even though its child is the concrete class,
    interface, or function carrying the evidence.  Search only descendants of
    the point node that still contain the cited row; this preserves exact-line
    accountability instead of accepting an unrelated declaration elsewhere in
    the wrapper.
    """

    matches = [
        candidate
        for candidate in collect_nodes(node, types)
        if candidate.start_point.row <= row <= candidate.end_point.row
    ]
    return min(
        matches, key=lambda candidate: candidate.end_byte - candidate.start_byte, default=None
    )


def _method_body(method):
    body = method.child_by_field_name("body")
    if body is not None:
        return body
    for child in method.named_children:
        if child.type in _BODY_TYPES:
            return child
    return None


def _method_signal(method) -> SourcePolarity:
    body = _method_body(method)
    if body is None:
        return "unresolved"
    negative_nodes = collect_nodes(body, _NEGATIVE_NODE_TYPES)
    if any(_NOT_IMPLEMENTED_RE.search(node_text(node)) for node in negative_nodes):
        return "negative"
    substantive = [child for child in body.named_children if child.type != "comment"]
    if not substantive:
        return "negative"
    return "positive"


def _declaration_key(path: Path, node) -> tuple[Path, str, int, int]:
    return path, node.type, node.start_byte, node.end_byte


def _cached_method_signal(
    path: Path,
    method,
    cache: TreeSitterEvidenceCache,
) -> SourcePolarity:
    key = _declaration_key(path, method)
    if key not in cache.declaration_signals:
        cache.declaration_signals[key] = _method_signal(method)
    return cache.declaration_signals[key]


def _cached_container_signal(
    path: Path,
    container,
    cache: TreeSitterEvidenceCache,
) -> SourcePolarity:
    key = _declaration_key(path, container)
    if key in cache.declaration_signals:
        return cache.declaration_signals[key]
    methods = collect_nodes(container, _METHOD_TYPES)
    signals = [_cached_method_signal(path, method, cache) for method in methods]
    resolved = [signal for signal in signals if signal != "unresolved"]
    if resolved and all(signal == "negative" for signal in resolved):
        result: SourcePolarity = "negative"
    elif resolved and all(signal == "positive" for signal in resolved):
        result = "positive"
    else:
        result = "unresolved"
    cache.declaration_signals[key] = result
    return result


def source_line_signal(
    path: Path,
    line: int,
    *,
    cache: TreeSitterEvidenceCache,
) -> SourcePolarity:
    """Classify the exact syntax declaration containing a one-based cited line."""

    key = (path, line)
    if key in cache.line_signals:
        return cache.line_signals[key]
    signal = _uncached_source_line_signal(path, line, cache=cache)
    cache.line_signals[key] = signal
    return signal


def _uncached_source_line_signal(
    path: Path,
    line: int,
    *,
    cache: TreeSitterEvidenceCache,
) -> SourcePolarity:
    if line < 1 or _LANGUAGE_BY_SUFFIX.get(path.suffix.casefold()) is None:
        return "unresolved"
    source, tree = cache.source_and_tree(path)
    if source is None or tree is None:
        return "unresolved"
    rows = source.splitlines()
    if line > len(rows):
        return "unresolved"
    row = line - 1
    end_column = max(1, len(rows[row]))
    node = tree.root_node.descendant_for_point_range((row, 0), (row, end_column))
    method = _ancestor(node, _METHOD_TYPES) or _nested_declaration_on_row(node, _METHOD_TYPES, row)
    if method is not None:
        return _cached_method_signal(path, method, cache)
    container = _ancestor(node, _CLASS_TYPES) or _nested_declaration_on_row(node, _CLASS_TYPES, row)
    if container is not None:
        return _cached_container_signal(path, container, cache)
    if (
        _ancestor(node, _CONCRETE_DECLARATION_TYPES) is not None
        or _nested_declaration_on_row(node, _CONCRETE_DECLARATION_TYPES, row) is not None
    ):
        return "positive"
    return "unresolved"


__all__ = ["TreeSitterEvidenceCache", "source_line_signal"]
