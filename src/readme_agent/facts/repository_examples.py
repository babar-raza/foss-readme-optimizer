"""Extract bounded, repository-authored README examples for local verification."""

from __future__ import annotations

import ast
import re
from collections.abc import Callable
from pathlib import Path
from typing import Literal

from markdown_it import MarkdownIt

from readme_agent.ecosystems.python_package_layout import inspect_python_package_layout
from readme_agent.facts.example_quality import strip_source_comments
from readme_agent.facts.python_repository_examples import (
    python_code_example_candidates,
    python_source_example_candidates,
)
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
_EXAMPLE_DIRECTORY_NAMES = frozenset(
    {"_examples", "demo", "demos", "example", "examples", "sample", "samples"}
)
_UNSUITABLE_VISITOR_EXAMPLE_PARTS = frozenset(
    {"ai", "auth", "credential", "password", "secret", "token"}
)


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
        try:
            tree = ast.parse(source)
        except SyntaxError:
            tree = None
        if tree is not None:
            package_aliases = {
                alias.asname or alias.name.split(".", 1)[0]
                for node in tree.body
                if isinstance(node, ast.Import)
                for alias in node.names
                if alias.name == "aspose" or alias.name.startswith("aspose.")
            }
            package_chains: set[tuple[str, ...]] = set()
            for node in ast.walk(tree):
                if not isinstance(node, ast.Attribute):
                    continue
                parts: list[str] = []
                current: ast.AST = node
                while isinstance(current, ast.Attribute):
                    parts.append(current.attr)
                    current = current.value
                if isinstance(current, ast.Name) and current.id in package_aliases:
                    package_chains.add((current.id, *reversed(parts)))
            outermost_chains = {
                chain
                for chain in package_chains
                if not any(
                    len(other) > len(chain) and other[: len(chain)] == chain
                    for other in package_chains
                )
            }
            if outermost_chains:
                return sorted(".".join(chain) for chain in outermost_chains)
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
        if info in aliases and language in {"python", "dotnet"}:
            code = strip_source_comments(language, code).strip()
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
        if language == "python":
            try:
                package_name = inspect_python_package_layout(root).canonical_import
            except (OSError, SyntaxError, ValueError):
                package_name = ""
            if package_name:
                candidates.extend(
                    candidate.model_copy(update={"evidence_paths": evidence_paths})
                    for candidate in python_code_example_candidates(
                        code,
                        package_name=package_name,
                        relative_path=readme_path,
                        max_chars=_MAX_EXAMPLE_CHARS,
                    )
                )
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


def _is_repository_example_source(root: Path, path: Path) -> bool:
    parts = {part.casefold() for part in path.relative_to(root).parts[:-1]}
    return bool(parts & _EXAMPLE_DIRECTORY_NAMES) or any(
        part.endswith(("example", "examples", "sample", "samples")) for part in parts
    )


def _go_source_example(root: Path, path: Path) -> MinimalExamplePolicy | None:
    try:
        module_text = (root / "go.mod").read_text(encoding="utf-8-sig")
        source = path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return None
    module_match = re.search(r"(?m)^module\s+(\S+)", module_text)
    if module_match is None:
        return None
    module = module_match.group(1)
    import_match = re.search(
        rf'(?m)^\s*(?:import\s+)?(?:(\w+)\s+)?"{re.escape(module)}"\s*$',
        source,
    )
    if import_match is None:
        return None
    alias = import_match.group(1) or Path(module).name.replace("-", "_")
    exported_symbols = sorted(set(re.findall(rf"\b{re.escape(alias)}\.([A-Z]\w*)", source)))
    code = strip_source_comments("go", source).strip()
    if (
        not exported_symbols
        or not re.search(r"(?m)^\s*package\s+main\s*$", code)
        or not re.search(r"\bfunc\s+main\s*\(\s*\)", code)
        or len(code) > _MAX_EXAMPLE_CHARS
    ):
        return None
    relative_path = path.relative_to(root).as_posix()
    return MinimalExamplePolicy(
        language="go",
        class_name="readme_example",
        code=code + "\n",
        evidence_paths=[relative_path],
        required_symbols=[f"{alias}.{name}" for name in exported_symbols],
    )


def _dotnet_source_example(root: Path, path: Path) -> MinimalExamplePolicy | None:
    try:
        source = path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return None
    code = strip_source_comments("dotnet", source).strip()
    namespaces = sorted(set(re.findall(r"(?m)^\s*using\s+(Aspose(?:\.[A-Za-z_]\w*)+)\s*;", code)))
    used_types = sorted(
        set(
            re.findall(
                r"\b(?:new\s+|typeof\s*\(\s*|(?<![.\w]))([A-Z][A-Za-z0-9_]*)\s*(?:[.(])",
                code,
            )
        )
        - {"Main", "Program"}
    )
    explicit_main = bool(
        re.search(r"\bstatic\s+(?:async\s+)?(?:void|Task|Task<int>|int)\s+Main\s*\(", code)
    )
    without_usings = re.sub(r"(?m)^\s*using\s+[^;]+;\s*$", "", code).strip()
    top_level_program = bool(without_usings) and not re.fullmatch(
        r"(?:namespace\s+[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*\s*;\s*)?",
        without_usings,
    )
    if (
        path.name.casefold() != "program.cs"
        or not namespaces
        or not used_types
        or not (explicit_main or top_level_program)
        or len(code) > _MAX_EXAMPLE_CHARS
    ):
        return None
    relative_path = path.relative_to(root).as_posix()
    return MinimalExamplePolicy(
        language="dotnet",
        class_name=_class_name(code, "ReadmeExample"),
        code=code + "\n",
        evidence_paths=[relative_path],
        required_symbols=used_types,
    )


def repository_source_example_candidates(
    root: Path,
    language: ExampleLanguage,
) -> list[MinimalExamplePolicy]:
    """Return complete repository-owned source examples as untrusted candidates.

    Source selection is deliberately narrower than README extraction. Only
    ecosystems with a deterministic complete-program recognizer participate;
    every returned candidate must still pass evidence anchoring, public-symbol
    resolution, and the disposable OS-isolated compiler before it is trusted.
    """

    if language not in {"dotnet", "go", "python"}:
        return []
    suffix = {"dotnet": "Program.cs", "go": "*.go", "python": "*.py"}[language]
    paths: list[Path] = []
    for path in root.rglob(suffix):
        relative_tokens = {
            token
            for part in path.relative_to(root).parts
            for token in re.split(r"[^a-z0-9]+", part.casefold())
            if token
        }
        if (
            not path.is_file()
            or not _is_repository_example_source(root, path)
            or relative_tokens & _UNSUITABLE_VISITOR_EXAMPLE_PARTS
        ):
            continue
        paths.append(path)
    if language == "python":
        return python_source_example_candidates(
            root,
            paths,
            max_chars=_MAX_EXAMPLE_CHARS,
        )
    if language == "dotnet":
        return sorted(
            (
                candidate
                for path in paths
                if (candidate := _dotnet_source_example(root, path)) is not None
            ),
            key=lambda candidate: (len(candidate.code), candidate.evidence_paths[0]),
        )
    if not (root / "go.mod").is_file():
        return []
    candidates: list[MinimalExamplePolicy] = []
    for path in paths:
        candidate = _go_source_example(root, path)
        if candidate is not None:
            candidates.append(candidate)
    return sorted(
        candidates,
        key=lambda candidate: (len(candidate.code), candidate.evidence_paths[0]),
    )
