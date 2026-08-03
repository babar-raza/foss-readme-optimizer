"""Verify curated Python README examples against the repository API surface."""

from __future__ import annotations

import ast
import hashlib
import re
from pathlib import Path

from readme_agent.readme.document_structure import code_blocks_in_span, parse_headings

_IMAGE = re.compile(r"!\[(?P<alt>[^]]*)\]\((?P<path>[^)\s]+)(?:\s+[^)]*)?\)")
_SAFE_BUILTIN_CALLS = {"open", "print"}
_UNSAFE_CALLS = {"compile", "eval", "exec", "__import__"}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _module_from_source(path: str) -> str | None:
    if not path.startswith("src/") or not path.endswith(".py"):
        return None
    module = path.removeprefix("src/").removesuffix(".py").replace("/", ".")
    return module.removesuffix(".__init__")


def _public_contract(
    value: object,
) -> tuple[dict[str, set[str]], dict[str, set[str]], dict[str, str]]:
    if not isinstance(value, dict):
        return {}, {}, {}
    modules: dict[str, set[str]] = {}
    for row in value.get("modules", []):
        if not isinstance(row, dict) or not isinstance(row.get("module"), str):
            continue
        exports = row.get("exports")
        if isinstance(exports, list):
            modules[row["module"]] = {str(item) for item in exports}
    classes: dict[str, set[str]] = {}
    for row in value.get("classes", []):
        if not isinstance(row, dict) or not isinstance(row.get("name"), str):
            continue
        module = _module_from_source(str(row.get("source_path") or ""))
        if module is None:
            continue
        members = row.get("members")
        names = {
            str(item["name"])
            for item in members or []
            if isinstance(item, dict) and isinstance(item.get("name"), str)
        }
        classes[f"{module}:{row['name']}"] = names
    functions = {
        f"{row['module']}:{row['name']}": str(row["return_class"])
        for row in value.get("functions", [])
        if isinstance(row, dict)
        and isinstance(row.get("module"), str)
        and isinstance(row.get("name"), str)
        and isinstance(row.get("return_class"), str)
        and row["return_class"] in classes
    }
    return modules, classes, functions


def _validated_python_example(
    code: str,
    public_surface: object,
) -> tuple[bool, list[str]]:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return False, []
    modules, classes, functions = _public_contract(public_surface)
    imported_classes: dict[str, tuple[str, set[str]]] = {}
    imported_functions: dict[str, tuple[str, set[str]]] = {}
    evidence_modules: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom) or node.module is None:
            continue
        for name in node.names:
            alias = name.asname or name.name
            class_key = f"{node.module}:{name.name}"
            if class_key in classes:
                imported_classes[alias] = (name.name, classes[class_key])
                evidence_modules.add(node.module)
                continue
            return_class = functions.get(class_key)
            if return_class is not None:
                imported_functions[alias] = (return_class, classes[return_class])
                evidence_modules.add(node.module)
                continue
            if name.name in modules.get(node.module, set()):
                evidence_modules.add(node.module)
                continue
            return False, []
    if not evidence_modules:
        return False, []
    instances: dict[str, tuple[str, set[str]]] = {}
    file_handles: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.withitem):
            continue
        if (
            isinstance(node.context_expr, ast.Call)
            and isinstance(node.context_expr.func, ast.Name)
            and node.context_expr.func.id == "open"
            and isinstance(node.optional_vars, ast.Name)
        ):
            file_handles.add(node.optional_vars.id)
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        value = node.value
        if value is None or not isinstance(value, ast.Call):
            continue
        target_names = [target.id for target in targets if isinstance(target, ast.Name)]
        if isinstance(value.func, ast.Name) and value.func.id == "open":
            file_handles.update(target_names)
            continue
        if isinstance(value.func, ast.Name) and value.func.id in imported_functions:
            instances.update({target: imported_functions[value.func.id] for target in target_names})
            continue
        if not isinstance(value.func, ast.Attribute) or not isinstance(value.func.value, ast.Name):
            continue
        assigned_owner = imported_classes.get(value.func.value.id)
        if assigned_owner is not None and value.func.attr in assigned_owner[1]:
            instances.update({target: assigned_owner for target in target_names})
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            if node.func.id in _UNSAFE_CALLS:
                return False, []
            if (
                node.func.id not in imported_classes
                and node.func.id not in imported_functions
                and node.func.id not in _SAFE_BUILTIN_CALLS
            ):
                return False, []
            continue
        if not isinstance(node.func, ast.Attribute):
            return False, []
        call_owner: tuple[str, set[str]] | None = None
        owner_name = ""
        if isinstance(node.func.value, ast.Name):
            owner_name = node.func.value.id
            call_owner = imported_classes.get(owner_name) or instances.get(owner_name)
        elif isinstance(node.func.value, ast.Call) and isinstance(node.func.value.func, ast.Name):
            call_owner = imported_functions.get(node.func.value.func.id)
        if call_owner is not None and node.func.attr not in call_owner[1]:
            return False, []
        if call_owner is None and owner_name not in file_handles:
            return False, []
    return True, sorted(evidence_modules)


def _quick_start_examples(
    readme: str,
    public_surface: object,
) -> list[dict[str, object]]:
    headings = parse_headings(readme)
    quick_start = next(
        (
            heading
            for heading in headings
            if heading.level == 2 and heading.title.strip().casefold() in {"quick start", "usage"}
        ),
        None,
    )
    if quick_start is None:
        return []
    examples: list[dict[str, object]] = []
    first_child = min(
        (
            heading.start
            for heading in headings
            if heading.start >= quick_start.heading_end
            and heading.start < quick_start.section_end
            and heading.level > 2
        ),
        default=quick_start.section_end,
    )
    sections = [(quick_start.title.strip(), quick_start.heading_end, first_child)]
    for heading in headings:
        if (
            heading.level != 3
            or heading.start < quick_start.heading_end
            or heading.start >= quick_start.section_end
        ):
            continue
        sections.append((heading.title.strip(), heading.heading_end, heading.section_end))
    for title, start, end in sections:
        blocks = code_blocks_in_span(readme, start, end)
        for block in blocks:
            valid, modules = _validated_python_example(block.content, public_surface)
            if not valid:
                continue
            examples.append(
                {
                    "title": title,
                    "code": block.content.rstrip(),
                    "language": "python",
                    "static_api_verified": True,
                    "execution_verified": False,
                    "evidence_modules": modules,
                }
            )
    return examples


def _result_assets(root: Path, readme: str) -> list[dict[str, str]]:
    section = next(
        (
            heading
            for heading in parse_headings(readme)
            if heading.level == 2 and heading.title.strip().casefold() == "example results"
        ),
        None,
    )
    if section is None:
        return []
    body = readme[section.heading_end : section.section_end]
    assets: list[dict[str, str]] = []
    for match in _IMAGE.finditer(body):
        relative = match.group("path").replace("\\", "/")
        path = root / relative
        try:
            path.resolve().relative_to(root.resolve())
        except ValueError:
            continue
        if not path.is_file():
            continue
        source_sha256 = _sha256(path)
        evidence_path = next(
            (
                candidate
                for candidate in sorted((root / "testdata").rglob(path.name))
                if candidate.is_file() and _sha256(candidate) == source_sha256
            ),
            None,
        )
        if evidence_path is None:
            continue
        assets.append(
            {
                "alt": match.group("alt").strip() or path.stem,
                "path": relative,
                "sha256": source_sha256,
                "evidence_path": evidence_path.relative_to(root).as_posix(),
                "evidence_sha256": source_sha256,
            }
        )
    return assets


def verified_readme_examples(
    root: Path,
    public_surface: object,
) -> tuple[dict[str, object], list[str]] | None:
    """Return README detail only when repository files corroborate every retained item."""

    readme_path = root / "README.md"
    if not readme_path.is_file() or not public_surface:
        return None
    try:
        readme = readme_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    inline_examples = _quick_start_examples(readme, public_surface)
    result_assets = _result_assets(root, readme)
    if not inline_examples and not result_assets:
        return None
    locations = ["README.md"]
    if isinstance(public_surface, dict):
        for rows in public_surface.values():
            if not isinstance(rows, list):
                continue
            locations.extend(
                str(row["source_path"])
                for row in rows
                if isinstance(row, dict) and isinstance(row.get("source_path"), str)
            )
    locations.extend(str(item["path"]) for item in result_assets)
    locations.extend(str(item["evidence_path"]) for item in result_assets)
    return (
        {
            "inline_examples": inline_examples,
            "result_assets": result_assets,
            "readme_sha256": _sha256(readme_path),
        },
        sorted(set(locations)),
    )
