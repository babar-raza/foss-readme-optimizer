"""Extract stable technical anchors from presentation prose."""

from __future__ import annotations

import re

from markdown_it import MarkdownIt

_SKIP_IDENTIFIERS = {
    "as",
    "await",
    "const",
    "false",
    "for",
    "from",
    "import",
    "let",
    "new",
    "none",
    "null",
    "return",
    "true",
    "using",
    "var",
    "with",
}
_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_CALL = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\s*\(")
_DOTTED = re.compile(r"\.([A-Za-z_][A-Za-z0-9_]*)")


def _inline_code(text: str) -> list[str]:
    values: list[str] = []
    for token in MarkdownIt("commonmark").parse(text):
        if token.type != "inline":
            continue
        values.extend(
            child.content.strip()
            for child in token.children or []
            if child.type == "code_inline" and child.content.strip()
        )
    return values


def technical_anchors(text: str, salient_tokens: list[object] | None = None) -> list[str]:
    """Return ordered method/type anchors suitable for current-source re-verification."""

    fragments = [*_inline_code(text), *(str(value) for value in salient_tokens or [])]
    anchors: list[str] = []
    for fragment in fragments:
        candidates = [*_CALL.findall(fragment), *_DOTTED.findall(fragment)]
        candidates.extend(
            identifier
            for identifier in _IDENTIFIER.findall(fragment)
            if identifier[:1].isupper() or "_" in identifier
        )
        for candidate in candidates:
            normalized = candidate.strip()
            if (
                len(normalized) < 2
                or normalized.casefold() in _SKIP_IDENTIFIERS
                or normalized.isdigit()
            ):
                continue
            if normalized not in anchors:
                anchors.append(normalized)
    return anchors


__all__ = ["technical_anchors"]
