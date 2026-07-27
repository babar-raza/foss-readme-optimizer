"""Extract bounded, repository-authored README examples for local verification."""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from typing import Literal

from markdown_it import MarkdownIt

from readme_agent.inspection.file_inventory import scan
from readme_agent.registry.models import MinimalExamplePolicy

# Repository-authored examples may include the imports and C/C++ scaffolding a real
# compiler needs. Keep the agent-drafted contract at 600 characters, but allow a still
# bounded source example large enough to preserve one complete, already-maintained usage.
_MAX_EXAMPLE_CHARS = 2_400
ExampleLanguage = Literal["java", "dotnet", "python", "typescript", "go", "cpp", "rust"]
_LANGUAGE_ALIASES = {
    "cpp": {"c++", "cpp", "cxx"},
    "dotnet": {"c#", "csharp", "cs", "dotnet"},
    "go": {"go", "golang"},
    "java": {"java"},
    "python": {"py", "python"},
    "rust": {"rs", "rust"},
    "typescript": {"ts", "typescript"},
}


def _class_name(source: str, fallback: str) -> str:
    match = re.search(r"\bclass\s+([A-Za-z_][A-Za-z0-9_]*)", source)
    return match.group(1) if match else fallback


_CLASS_NAMES: dict[str, Callable[[str], str]] = {
    "cpp": lambda source: _class_name(source, "readme_example"),
    "dotnet": lambda source: _class_name(source, "ReadmeExample"),
    "go": lambda _source: "readme_example",
    "java": lambda source: _class_name(source, "ReadmeExample"),
    "python": lambda _source: "readme_example",
    "rust": lambda _source: "readme_example",
    "typescript": lambda source: _class_name(source, "readmeExample"),
}


def _evidence_anchor(source: str) -> str | None:
    for line in source.splitlines():
        anchor = line.strip()
        if len(anchor) >= 4 and not anchor.startswith(("//", "#", "/*", "*")):
            return anchor
    return None


def _imported_symbol_anchors(language: ExampleLanguage, source: str) -> list[str]:
    """Extract exact README anchors that downstream public-API gates can resolve."""

    if language == "python":
        python_names = [
            item.strip().split(" as ", 1)[0]
            for group in re.findall(
                r"(?m)^\s*from\s+aspose(?:\.[A-Za-z_]\w*)*\s+import\s+([^\n#]+)",
                source,
            )
            for item in group.split(",")
            if item.strip()
        ]
        return sorted(set(python_names))
    if language == "typescript":
        typescript_names = [
            item.strip().split(" as ", 1)[0]
            for group in re.findall(r"import\s*\{([^}]+)\}\s*from", source)
            for item in group.split(",")
            if item.strip()
        ]
        return sorted(set(typescript_names))
    if language == "rust":
        rust_names: list[str] = []
        use_pattern = r"(?m)^\s*use\s+[A-Za-z_]\w*(?:::\{([^}]+)\}|::([A-Z]\w*))"
        for group in re.findall(use_pattern, source):
            braced, single = group
            rust_names.extend(
                item.strip().split(" as ", 1)[0] for item in braced.split(",") if item.strip()
            )
            if single:
                rust_names.append(single)
        return sorted(set(rust_names))
    return []


def repository_readme_example_candidates(
    root: Path,
    language: ExampleLanguage,
    *,
    supporting_paths: list[str] | None = None,
) -> list[MinimalExamplePolicy]:
    """Return bounded language-matched code blocks as untrusted candidates.

    Extraction never verifies a README claim. The product-truth orchestrator
    still applies exact evidence checks, public-API quality checks, and the
    real ecosystem compiler/executor before promoting any candidate.
    """

    aliases = _LANGUAGE_ALIASES.get(language)
    class_name = _CLASS_NAMES.get(language)
    if aliases is None or class_name is None:
        return []
    readme = scan(root).readme_path
    if readme is None:
        return []
    text = readme.read_text(encoding="utf-8-sig", errors="replace")
    readme_path = readme.relative_to(root).as_posix()
    evidence_paths = list(dict.fromkeys([readme_path, *(supporting_paths or [])]))
    candidates: list[MinimalExamplePolicy] = []
    for token in MarkdownIt("commonmark").parse(text):
        info = token.info.strip().split(maxsplit=1)[0].lower() if token.info.strip() else ""
        code = token.content.strip()
        anchor = _evidence_anchor(code)
        if (
            token.type != "fence"
            or info not in aliases
            or not code
            or len(code) > _MAX_EXAMPLE_CHARS
            or anchor is None
        ):
            continue
        required_symbols = _imported_symbol_anchors(language, code) or [anchor]
        candidates.append(
            MinimalExamplePolicy(
                language=language,
                class_name=class_name(code),
                code=code + "\n",
                evidence_paths=evidence_paths,
                required_symbols=required_symbols,
            )
        )
    return candidates
