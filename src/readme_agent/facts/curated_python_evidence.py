"""Collect static Python package facts used by optional README sections."""

from __future__ import annotations

import ast
import hashlib
import tomllib
from pathlib import Path

from readme_agent.facts.curated_python_mcp import python_mcp_server
from readme_agent.facts.curated_python_readme import verified_readme_examples

_IGNORED_DIRECTORIES = {".git", ".venv", "__pycache__", "node_modules"}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _module_from_source(path: str) -> str | None:
    if not path.startswith("src/") or not path.endswith(".py"):
        return None
    module = path.removeprefix("src/").removesuffix(".py").replace("/", ".")
    return module.removesuffix(".__init__")


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


def _literal_string_list(node: ast.AST) -> list[str] | None:
    if not isinstance(node, (ast.List, ast.Tuple)):
        return None
    values: list[str] = []
    for element in node.elts:
        if not isinstance(element, ast.Constant) or not isinstance(element.value, str):
            return None
        values.append(element.value)
    return values


def python_public_surface(root: Path) -> tuple[object, list[str]] | None:
    candidates = sorted((root / "src").glob("**/__init__.py")) if (root / "src").is_dir() else []
    surfaces: list[dict[str, object]] = []
    locations: list[str] = []
    exported_names: set[str] = set()
    export_origins: dict[tuple[str, str], str] = {}
    for path in candidates:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        exports: list[str] | None = None
        for node in tree.body:
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if not any(
                isinstance(target, ast.Name) and target.id == "__all__" for target in targets
            ):
                continue
            exports = _literal_string_list(node.value) if node.value is not None else None
            break
        if not exports:
            continue
        relative = path.relative_to(root).as_posix()
        package_parts = path.relative_to(root / "src").parts[:-1]
        if any(part.startswith("_") for part in package_parts):
            continue
        surfaces.append(
            {
                "module": ".".join(package_parts),
                "exports": exports,
                "source_path": relative,
                "source_sha256": _sha256(path),
            }
        )
        exported_names.update(exports)
        module = ".".join(package_parts)
        for node in tree.body:
            if not isinstance(node, ast.ImportFrom) or node.level or node.module is None:
                continue
            for imported in node.names:
                exposed = imported.asname or imported.name
                if exposed in exports:
                    export_origins[(module, exposed)] = f"{node.module}:{imported.name}"
        locations.append(relative)
    if not surfaces:
        return None
    classes: list[dict[str, object]] = []
    class_keys: set[str] = set()
    pending_functions: list[
        tuple[str, Path, ast.FunctionDef | ast.AsyncFunctionDef, dict[str, str]]
    ] = []
    for path in sorted((root / "src").rglob("*.py")):
        relative = path.relative_to(root).as_posix()
        if any(part.startswith("_") for part in path.relative_to(root / "src").parts):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        source_module = _module_from_source(relative)
        if source_module is None:
            continue
        imports = {
            imported.asname or imported.name: f"{node.module}:{imported.name}"
            for node in tree.body
            if isinstance(node, ast.ImportFrom) and not node.level and node.module is not None
            for imported in node.names
        }
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                pending_functions.append((source_module, path, node, imports))
                continue
            if not isinstance(node, ast.ClassDef) or node.name not in exported_names:
                continue
            members = _class_public_members(node)
            if not members:
                continue
            classes.append(
                {
                    "name": node.name,
                    "members": members,
                    "source_path": relative,
                    "source_sha256": _sha256(path),
                    "line": node.lineno,
                }
            )
            class_keys.add(f"{source_module}:{node.name}")
            locations.append(relative)
    functions: list[dict[str, object]] = []
    for row in surfaces:
        exposed_module = str(row["module"])
        surface_exports = row.get("exports")
        if not isinstance(surface_exports, list):
            continue
        for exported in surface_exports:
            origin = export_origins.get((exposed_module, str(exported)))
            for module, path, node, imports in pending_functions:
                if origin != f"{module}:{node.name}" or not isinstance(node.returns, ast.Name):
                    continue
                return_class = imports.get(node.returns.id, f"{module}:{node.returns.id}")
                if return_class not in class_keys:
                    continue
                functions.append(
                    {
                        "module": exposed_module,
                        "name": str(exported),
                        "return_class": return_class,
                        "source_path": path.relative_to(root).as_posix(),
                        "source_sha256": _sha256(path),
                    }
                )
                locations.append(path.relative_to(root).as_posix())
    value: dict[str, object] = {
        "modules": surfaces,
        "classes": classes,
        "functions": functions,
    }
    mcp = python_mcp_server(root)
    if mcp is not None:
        value["mcp_server"] = mcp[0]
        locations.extend(mcp[1])
    return value, sorted(set(locations))


def _annotation(node: ast.AST | None) -> str | None:
    return ast.unparse(node) if node is not None else None


def _method_call(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    positional = [*node.args.posonlyargs, *node.args.args]
    if positional and positional[0].arg in {"self", "cls"}:
        positional = positional[1:]
    defaults = [None] * (len(positional) - len(node.args.defaults)) + list(node.args.defaults)
    rendered: list[str] = []
    for argument, default in zip(positional, defaults, strict=True):
        value = argument.arg
        if default is not None:
            value += "=" + ast.unparse(default)
        rendered.append(value)
    if node.args.vararg is not None:
        rendered.append("*" + node.args.vararg.arg)
    rendered.extend(argument.arg for argument in node.args.kwonlyargs)
    if node.args.kwarg is not None:
        rendered.append("**" + node.args.kwarg.arg)
    return f"{node.name}({', '.join(rendered)})"


def _class_public_members(node: ast.ClassDef) -> list[dict[str, object]]:
    members: list[dict[str, object]] = []
    for child in node.body:
        if isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name):
            if child.target.id.startswith("_"):
                continue
            annotation = _annotation(child.annotation)
            surface = f"{child.target.id}: {annotation}" if annotation else child.target.id
            members.append({"name": child.target.id, "kind": "attribute", "surface": surface})
            continue
        if not isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if child.name.startswith("_"):
            continue
        decorators = {ast.unparse(decorator) for decorator in child.decorator_list}
        annotation = _annotation(child.returns)
        if "property" in decorators:
            surface = f"{child.name}: {annotation}" if annotation else child.name
            kind = "property"
        else:
            surface = _method_call(child)
            if annotation:
                surface += f" -> {annotation}"
            kind = "method"
        members.append({"name": child.name, "kind": kind, "surface": surface})
    return members


def example_inventory(root: Path) -> tuple[object, list[str]] | None:
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
    return value, sorted(set(locations))
