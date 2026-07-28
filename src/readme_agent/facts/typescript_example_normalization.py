"""Derive a minimal TypeScript consumer from the package's source entry point."""

from __future__ import annotations

import re
from pathlib import Path

from readme_agent.ecosystems.typescript_package_layout import (
    inspect_typescript_package_layout,
)
from readme_agent.registry.models import MinimalExamplePolicy

_NAMED_IMPORT = re.compile(
    r"import\s*\{(?P<names>[^}]+)\}\s*from\s*['\"](?P<specifier>[^'\"]+)['\"]"
)
_REEXPORT = re.compile(r"export\s*\{(?P<names>[^}]+)\}\s*from\s*['\"](?P<module>[^'\"]+)['\"]")


def _imported_names(source: str) -> list[str]:
    names: list[str] = []
    for match in _NAMED_IMPORT.finditer(source):
        names.extend(
            item.split(" as ", 1)[0].strip()
            for item in match.group("names").split(",")
            if item.strip()
        )
    return names


def _has_no_required_constructor_arguments(source: str, class_name: str) -> bool:
    declaration = re.search(
        rf"\bexport\s+(?:default\s+)?class\s+{re.escape(class_name)}\b",
        source,
    )
    if declaration is None:
        return False
    constructors = re.findall(r"\bconstructor\s*\(([^)]*)\)", source[declaration.end() :])
    if not constructors:
        return True
    for parameters in constructors:
        parameters = parameters.strip()
        if not parameters:
            return True
        parts = [part.strip() for part in parameters.split(",")]
        if all(
            "?" in part.split(":", 1)[0] or "=" in part or part.startswith("...") for part in parts
        ):
            return True
    return False


def _variable_name(class_name: str) -> str:
    rendered = re.sub(r"(?<!^)(?=[A-Z])", "_", class_name).casefold()
    return rendered if rendered.isidentifier() else "product"


def normalize_typescript_package_consumer(
    root: Path,
    example: MinimalExamplePolicy,
) -> MinimalExamplePolicy:
    """Replace ambiguous or stale imports with one source-proven package consumer."""

    root = root.resolve()
    try:
        layout = inspect_typescript_package_layout(root)
    except (OSError, UnicodeError, ValueError):
        return example
    canonical_import = layout.canonical_import
    canonical_entry = next(
        (
            entry
            for entry in layout.entry_points
            if entry.import_specifier == canonical_import and entry.source_entry_path
        ),
        None,
    )
    specifiers = {match.group("specifier") for match in _NAMED_IMPORT.finditer(example.code)}
    if (
        canonical_import is None
        or canonical_entry is None
        or (specifiers == {canonical_import} and len(specifiers) == 1)
    ):
        return example

    source_entry_path = canonical_entry.source_entry_path
    if source_entry_path is None:
        return example
    entry_path = root / source_entry_path
    try:
        entry_source = entry_path.read_text(encoding="utf-8", errors="strict")
    except (OSError, UnicodeError):
        return example
    reexports: dict[str, tuple[str, Path]] = {}
    for match in _REEXPORT.finditer(entry_source):
        module = match.group("module")
        module_path = (entry_path.parent / module).with_suffix(".ts")
        if not module_path.is_file():
            module_path = entry_path.parent / module / "index.ts"
        for item in match.group("names").split(","):
            source_name, _, exported_name = item.strip().partition(" as ")
            if source_name:
                reexports[exported_name or source_name] = (source_name, module_path)

    preferred_names = _imported_names(example.code)
    ordered_names = [*preferred_names, *sorted(set(reexports) - set(preferred_names))]
    for exported_name in ordered_names:
        declaration = reexports.get(exported_name)
        if declaration is None:
            continue
        source_name, declaration_path = declaration
        try:
            declaration_source = declaration_path.read_text(encoding="utf-8", errors="strict")
        except (OSError, UnicodeError):
            continue
        if not _has_no_required_constructor_arguments(declaration_source, source_name):
            continue
        variable = _variable_name(exported_name)
        code = (
            f"import {{ {exported_name} }} from '{canonical_import}';\n\n"
            f"const {variable} = new {exported_name}();\n"
            f"console.log({variable});\n"
        )
        return example.model_copy(
            update={
                "class_name": exported_name,
                "code": code,
                "evidence_paths": [
                    source_entry_path,
                    declaration_path.relative_to(root).as_posix(),
                ],
                "required_symbols": [exported_name],
            }
        )
    return example
