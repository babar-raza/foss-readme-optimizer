"""Collect checksum-bound Python implementation components for public claim accountability."""

from __future__ import annotations

import ast
import hashlib
import re
import sys
import tomllib
from collections import defaultdict
from pathlib import Path

_PARSER_FILE = re.compile(r"(?:^|_)(?:parser|reader|loader)(?:_|$)", re.IGNORECASE)
_IGNORED_PARTS = {".git", ".venv", "build", "dist", "tests", "test"}
_FORMAT_ROLE = re.compile(
    r"^(?P<format>[a-z0-9]+)_(?P<role>reader|writer|parser|loader)$",
    re.IGNORECASE,
)
_ROLE_NAMES = {"loader": "read", "parser": "read", "reader": "read", "writer": "write"}
_FORMAT_ALIASES = {"markdown": "MD", "text": "TXT"}
_NON_FORMAT_TOKENS = {
    "content",
    "document",
    "file",
    "font",
    "image",
    "list",
    "metadata",
    "numbering",
    "paragraph",
    "shape",
    "style",
    "table",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _public_label(token: str) -> str:
    normalized = token.strip("_-").casefold()
    if normalized in {"ms_one", "ms-one"}:
        return "MS-ONE"
    if normalized == "onestore":
        return "OneStore"
    return token.strip("_-")


def _string_values(value: object) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def _declared_dependency_names(root: Path) -> set[str]:
    manifest = root / "pyproject.toml"
    if not manifest.is_file():
        return set()
    try:
        project = tomllib.loads(manifest.read_text(encoding="utf-8")).get("project", {})
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return set()
    dependencies = project.get("dependencies", []) if isinstance(project, dict) else []
    return {
        match.group(0).casefold().replace("-", "").replace("_", "")
        for item in dependencies
        if isinstance(item, str)
        if (match := re.match(r"[A-Za-z0-9_.-]+", item)) is not None
    }


def _local_import_names(root: Path) -> set[str]:
    names: set[str] = set()
    for base in (root, root / "src"):
        if not base.is_dir():
            continue
        names.update(
            child.name.casefold()
            for child in base.iterdir()
            if child.is_dir() and (child / "__init__.py").is_file()
        )
    return names


def _component_role(parts: tuple[str, ...]) -> tuple[str, str] | None:
    for token in (*reversed(parts[:-1]), parts[-1]):
        match = _FORMAT_ROLE.fullmatch(Path(token).stem)
        if match is not None:
            raw_format = match.group("format").casefold()
            if raw_format in _NON_FORMAT_TOKENS:
                continue
            format_name = _FORMAT_ALIASES.get(raw_format, raw_format.upper())
            return format_name, _ROLE_NAMES[match.group("role").casefold()]
    return None


def _module_details(
    path: Path,
    *,
    local_imports: set[str],
    declared_dependencies: set[str],
) -> dict[str, object] | None:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, SyntaxError):
        return None
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported.update(
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module and node.level == 0
    )
    stdlib = sorted(name for name in imported if name.split(".", 1)[0] in sys.stdlib_module_names)
    external = sorted(
        name
        for name in imported
        if name.split(".", 1)[0] not in sys.stdlib_module_names
        and name.split(".", 1)[0].casefold() not in local_imports
    )
    runtime = sorted(
        name
        for name in external
        if name.split(".", 1)[0].casefold().replace("_", "") in declared_dependencies
    )
    docstrings = [ast.get_docstring(tree) or ""]
    docstrings.extend(
        ast.get_docstring(node) or "" for node in tree.body if isinstance(node, ast.ClassDef)
    )
    return {
        "classes": sorted(
            node.name
            for node in tree.body
            if isinstance(node, ast.ClassDef) and not node.name.startswith("_")
        ),
        "stdlib_imports": stdlib,
        "runtime_imports": runtime,
        "external_imports": external,
        "source_summary": " ".join(" ".join(item.split()) for item in docstrings if item)[:1200],
    }


def _format_components(root: Path) -> list[dict[str, object]]:
    declared_dependencies = _declared_dependency_names(root)
    local_imports = _local_import_names(root)
    components: list[dict[str, object]] = []
    for path in sorted(root.rglob("*.py")):
        relative_path = path.relative_to(root)
        if any(part.casefold() in _IGNORED_PARTS for part in relative_path.parts):
            continue
        role = _component_role(relative_path.parts)
        if role is None:
            continue
        details = _module_details(
            path,
            local_imports=local_imports,
            declared_dependencies=declared_dependencies,
        )
        if details is None or not details["classes"]:
            continue
        format_name, operation = role
        components.append(
            {
                "kind": "python_format_io",
                "labels": [format_name],
                "roles": [operation],
                "path": relative_path.as_posix(),
                "source_sha256": _sha256(path),
                **details,
            }
        )
    return components


def _capability_groups(components: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[str, list[tuple[int, dict[str, object]]]] = defaultdict(list)
    for index, component in enumerate(components):
        if component.get("kind") != "python_format_io":
            continue
        labels = component.get("labels")
        if isinstance(labels, list) and labels:
            grouped[str(labels[0])].append((index, component))
    groups: list[dict[str, object]] = []
    for format_name, entries in sorted(grouped.items()):
        roles = sorted(
            {role for _index, item in entries for role in _string_values(item.get("roles"))}
        )
        runtime = sorted(
            {
                name
                for _index, item in entries
                for name in _string_values(item.get("runtime_imports"))
            }
        )
        stdlib = sorted(
            {
                name
                for _index, item in entries
                for name in _string_values(item.get("stdlib_imports"))
            }
        )
        evidence_text = " ".join(str(item.get("source_summary") or "") for _index, item in entries)
        actions = "Read and write" if roles == ["read", "write"] else roles[0].title()
        label = f"{actions} {format_name} documents"
        if (
            format_name == "DOC"
            and "97-2003" in evidence_text
            and "binary" in evidence_text.casefold()
        ):
            label = f"{actions} Word 97-2003 {format_name} binary documents"
        if runtime:
            label += " with " + ", ".join(runtime)
        elif stdlib and all(not item.get("external_imports") for _index, item in entries):
            label += " using Python standard-library components"
        groups.append(
            {
                "label": label,
                "format": format_name,
                "roles": roles,
                "component_indexes": [index for index, _item in entries],
                "stdlib_imports": stdlib,
                "runtime_imports": runtime,
                "source_summary": evidence_text[:1600],
            }
        )
    return groups


def python_implementation_components(root: Path) -> tuple[object, list[str]] | None:
    """Return source-backed parser components without interpreting README prose."""

    components: list[dict[str, object]] = []
    locations: list[str] = []
    source_root = root / "src"
    if source_root.is_dir():
        for path in sorted(source_root.rglob("*.py")):
            relative = path.relative_to(root).as_posix()
            parts = path.relative_to(source_root).parts
            if any(part.casefold() in _IGNORED_PARTS for part in parts):
                continue
            stem_tokens = [part for part in (*parts[:-1], path.stem) if part != "_internal"]
            if not _PARSER_FILE.search(path.stem):
                continue
            labels = sorted(
                {
                    label
                    for token in stem_tokens
                    if (label := _public_label(token)) in {"MS-ONE", "OneStore"}
                }
            )
            if not labels:
                continue
            components.append(
                {
                    "kind": "parser",
                    "labels": labels,
                    "path": relative,
                    "source_sha256": _sha256(path),
                }
            )
            locations.append(relative)
    format_components = _format_components(root)
    components.extend(format_components)
    locations.extend(str(item["path"]) for item in format_components)
    if not components:
        return None
    return {
        "components": components,
        "capability_groups": _capability_groups(components),
    }, sorted(set(locations))


__all__ = ["python_implementation_components"]
