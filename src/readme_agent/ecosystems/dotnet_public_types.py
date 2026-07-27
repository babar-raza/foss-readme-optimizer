"""Indexes unambiguous public .NET types from immutable repository source."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from pygments import lex
from pygments.lexers.dotnet import CSharpLexer
from pygments.token import Comment, Literal

_EXCLUDED_PARTS = {"bin", "obj", "sample", "samples", "test", "tests"}
_NAMESPACE_RE = re.compile(r"(?m)^\s*namespace\s+(Aspose(?:\.[A-Za-z_]\w*)+)\s*[;{]")
_PUBLIC_TYPE_RE = re.compile(
    r"\bpublic\s+(?:(?:abstract|partial|readonly|ref|sealed|static|unsafe)\s+)*"
    r"(?:class|enum|interface|record(?:\s+(?:class|struct))?|struct)\s+([A-Za-z_]\w*)\b"
)


@dataclass(frozen=True)
class DotnetPublicType:
    """One source-declared public type with its exact namespace and path."""

    name: str
    namespace: str
    source_path: Path

    @property
    def qualified_name(self) -> str:
        return f"{self.namespace}.{self.name}"


def _structural_source(source: str) -> str:
    """Blank comments and strings while preserving source positions and lines."""

    parts: list[str] = []
    for token_type, value in lex(source, CSharpLexer()):
        if token_type in Comment or token_type in Literal.String:
            parts.append("".join("\n" if character == "\n" else " " for character in value))
        else:
            parts.append(value)
    return "".join(parts)


def public_dotnet_type_index(root: Path) -> dict[str, DotnetPublicType]:
    """Return only uniquely declared production types from a source tree."""

    candidates: dict[str, list[DotnetPublicType]] = {}
    for path in sorted(root.rglob("*.cs")):
        if _EXCLUDED_PARTS & {part.lower() for part in path.relative_to(root).parts}:
            continue
        source = _structural_source(path.read_text(encoding="utf-8-sig", errors="replace"))
        namespaces = sorted(set(_NAMESPACE_RE.findall(source)))
        if len(namespaces) != 1:
            continue
        declared = sorted(set(_PUBLIC_TYPE_RE.findall(source)))
        for name in declared:
            candidates.setdefault(name, []).append(
                DotnetPublicType(name=name, namespace=namespaces[0], source_path=path)
            )

    return {
        name: declarations[0]
        for name, declarations in candidates.items()
        if len({item.qualified_name for item in declarations}) == 1
    }


def normalize_dotnet_public_type_usings(root: Path, source: str) -> str:
    """Add source-proven namespaces needed by unqualified public type uses."""

    structural = _structural_source(source)
    imported = set(re.findall(r"(?m)^\s*using\s+(Aspose(?:\.[A-Za-z_]\w*)+)\s*;", structural))
    index = public_dotnet_type_index(root)
    needed: set[str] = set()
    for name, declaration in index.items():
        if declaration.namespace in imported:
            continue
        if re.search(rf"(?<![\w.]){re.escape(name)}\b", structural):
            needed.add(declaration.namespace)
    if not needed:
        return source
    prefix = "".join(f"using {namespace};\n" for namespace in sorted(needed))
    return prefix + source
