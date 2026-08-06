"""Collect static Python package facts used by optional README sections."""

from __future__ import annotations

import ast
import hashlib
import tomllib
from pathlib import Path

from readme_agent.facts.curated_python_fixture_inventory import snapshot_fixture_inventory
from readme_agent.facts.curated_python_public_surface import python_public_surface
from readme_agent.facts.curated_python_readme import verified_readme_examples

_IGNORED_DIRECTORIES = {".git", ".venv", "__pycache__", "node_modules"}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _format_name(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str | None:
    """Derive one importer format only from its exact supports_format implementation."""

    for child in ast.walk(node):
        if (
            isinstance(child, ast.Call)
            and isinstance(child.func, ast.Name)
            and child.func.id == "isinstance"
            and len(child.args) == 2
            and isinstance(child.args[0], ast.Name)
            and child.args[0].id == "file_format"
            and isinstance(child.args[1], ast.Name)
            and child.args[1].id.endswith("Format")
        ):
            stem = child.args[1].id.removesuffix("Format").casefold()
            return {"gltf": "GLTF", "obj": "OBJ", "stl": "STL", "threemf": "3MF"}.get(
                stem, stem.upper()
            )
    return None


def _implemented(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    statements = [
        child
        for child in node.body
        if not isinstance(child, ast.Pass)
        and not (
            isinstance(child, ast.Expr)
            and isinstance(child.value, ast.Constant)
            and isinstance(child.value.value, str)
        )
    ]
    return bool(statements) and not all(isinstance(child, ast.Raise) for child in statements)


def _implemented_keyword_branch(tree: ast.AST, keyword: str) -> bool:
    for child in ast.walk(tree):
        if not isinstance(child, ast.If) or keyword not in ast.unparse(child.test).casefold():
            continue
        if any(not isinstance(statement, ast.Pass) for statement in child.body):
            return True
    return False


def python_source_format_directions(root: Path) -> tuple[object, list[str]] | None:
    """Collect source-implemented Python import and export directions without execution claims."""

    directions: list[dict[str, object]] = []
    locations: list[str] = []
    roles = {
        "Importer": ("import_scene", "input"),
        "Exporter": ("export", "output"),
    }
    paths = sorted({path for role in roles for path in root.rglob(f"*{role}.py")})
    for path in paths:
        relative = path.relative_to(root)
        if any(part in _IGNORED_DIRECTORIES for part in relative.parts):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        role = next((name for name in roles if path.stem.endswith(name)), None)
        if role is None:
            continue
        implementation_name, direction = roles[role]
        for definition in (node for node in tree.body if isinstance(node, ast.ClassDef)):
            methods = {
                node.name: node
                for node in definition.body
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
            support = methods.get("supports_format")
            implementation = methods.get(implementation_name)
            if support is None or implementation is None or not _implemented(implementation):
                continue
            format_name = _format_name(support)
            if format_name is None:
                continue
            calls = {
                node.func.attr
                for node in ast.walk(implementation)
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            }
            item: dict[str, object] = {
                "format": format_name,
                "direction": direction,
                "implementation_symbol": f"{definition.name}.{implementation_name}",
                "supports_format_symbol": f"{definition.name}.supports_format",
                "source_path": relative.as_posix(),
                "source_sha256": _sha256(path),
                "execution_verified": False,
            }
            if format_name == "STL" and direction == "input":
                item["variants"] = sorted(
                    variant
                    for variant, method in (
                        ("ascii", "_read_ascii_stl"),
                        ("binary", "_read_binary_stl"),
                    )
                    if method in calls
                )
            if format_name == "OBJ" and direction == "input":
                item["material_library_support"] = all(
                    _implemented_keyword_branch(tree, keyword) for keyword in ("mtllib", "usemtl")
                )
            directions.append(item)
            locations.append(relative.as_posix())
    if not directions:
        return None
    return (
        {
            "schema_version": 1,
            "assurance": "repository_source_implementation",
            "execution_verified": False,
            "directions": directions,
        },
        sorted(set(locations)),
    )


def python_optional_extras(root: Path) -> tuple[object, list[str]] | None:
    manifest = root / "pyproject.toml"
    if not manifest.is_file():
        return None
    data = tomllib.loads(manifest.read_text(encoding="utf-8"))
    project = data.get("project")
    if not isinstance(project, dict):
        return None
    extras = project.get("optional-dependencies")
    if not isinstance(extras, dict) or not extras:
        return None
    normalized = {
        str(name): [str(requirement) for requirement in requirements]
        for name, requirements in sorted(extras.items())
        if isinstance(requirements, list)
    }
    return {"manifest_path": "pyproject.toml", "extras": normalized}, ["pyproject.toml"]


def example_inventory(
    root: Path,
    source_revision: str | None = None,
) -> tuple[object, list[str]] | None:
    base = root / "examples"
    files = sorted(
        path
        for path in (base.rglob("*.py") if base.is_dir() else [])
        if path.is_file()
        and not any(part in _IGNORED_DIRECTORIES for part in path.relative_to(root).parts)
    )
    entries = [
        {
            "path": path.relative_to(root).as_posix(),
            "sha256": _sha256(path),
            "execution_verified": False,
        }
        for path in files
    ]
    locations = [str(entry["path"]) for entry in entries]
    index_path = root / "examples" / "README.md"
    if index_path.is_file():
        entries.append(
            {
                "path": "examples/README.md",
                "sha256": _sha256(index_path),
                "execution_verified": False,
            }
        )
        locations.append("examples/README.md")
    public_surface = python_public_surface(root)
    curated = verified_readme_examples(root, public_surface[0] if public_surface else None)
    value: dict[str, object] = {
        "files": entries,
        "execution_policy": "inventory_only",
    }
    if curated is not None:
        value.update(curated[0])
        locations.extend(curated[1])
    if not entries and curated is None:
        return None
    fixture_inventory = snapshot_fixture_inventory(root, source_revision)
    value["fixture_inventory"] = fixture_inventory.model_dump(mode="json")
    if fixture_inventory.tree_id is not None:
        locations.append(f"git-tree:{fixture_inventory.tree_id}")
    return value, sorted(set(locations))
