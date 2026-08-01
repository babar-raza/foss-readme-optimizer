"""Discover Python distribution metadata, source roots, and canonical imports."""

from __future__ import annotations

import ast
import configparser
import hashlib
import tomllib
from pathlib import Path
from typing import Any

from readme_agent.ecosystems.python_api_schema import PythonPackageLayoutV1

_EXCLUDED_ROOTS = {
    "build",
    "dist",
    "doc",
    "docs",
    "example",
    "examples",
    "test",
    "tests",
}


def _literal(value: ast.AST) -> Any:
    try:
        return ast.literal_eval(value)
    except (ValueError, TypeError):
        return None


def _setup_py_metadata(path: Path) -> dict[str, Any]:
    tree = ast.parse(path.read_text(encoding="utf-8-sig", errors="replace"), filename=str(path))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        function = node.func
        name = (
            function.id
            if isinstance(function, ast.Name)
            else (function.attr if isinstance(function, ast.Attribute) else "")
        )
        if name != "setup":
            continue
        return {keyword.arg: _literal(keyword.value) for keyword in node.keywords if keyword.arg}
    return {}


def _setup_cfg_metadata(path: Path) -> dict[str, Any]:
    parser = configparser.ConfigParser()
    parser.read(path, encoding="utf-8-sig")
    metadata = dict(parser["metadata"]) if parser.has_section("metadata") else {}
    options = dict(parser["options"]) if parser.has_section("options") else {}
    package_dir = options.get("package_dir", "")
    source_root = "."
    for line in package_dir.splitlines():
        key, separator, value = line.partition("=")
        if separator and not key.strip():
            source_root = value.strip() or "."
    return {
        "name": metadata.get("name"),
        "version": metadata.get("version"),
        "python_requires": options.get("python_requires"),
        "source_root": source_root,
        "namespace_packages": options.get("namespace_packages", ""),
    }


def _pyproject_metadata(path: Path) -> dict[str, Any]:
    data = tomllib.loads(path.read_text(encoding="utf-8-sig", errors="replace"))
    project = data.get("project", {})
    tools = data.get("tool", {})
    setuptools = tools.get("setuptools", {})
    package_dir = setuptools.get("package-dir", {})
    source_root = package_dir.get("", ".") if isinstance(package_dir, dict) else "."
    packages = setuptools.get("packages", [])
    find = packages.get("find", {}) if isinstance(packages, dict) else {}
    where = find.get("where", [])
    if isinstance(where, list) and where:
        source_root = where[0]
    includes = find.get("include", []) if isinstance(find, dict) else []
    if isinstance(packages, list):
        includes = packages
    hatch_packages = (
        tools.get("hatch", {})
        .get("build", {})
        .get("targets", {})
        .get("wheel", {})
        .get("packages", [])
    )
    if not includes and isinstance(hatch_packages, list):
        includes = hatch_packages
    return {
        "name": project.get("name"),
        "version": project.get("version"),
        "requires_python": project.get("requires-python"),
        "source_root": source_root,
        "declared_packages": includes,
        "namespaces": find.get("namespaces", True) if isinstance(find, dict) else True,
    }


def _manifest_metadata(root: Path) -> tuple[Path, dict[str, Any]]:
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        return pyproject, _pyproject_metadata(pyproject)
    setup_cfg = root / "setup.cfg"
    if setup_cfg.is_file():
        return setup_cfg, _setup_cfg_metadata(setup_cfg)
    setup_py = root / "setup.py"
    if setup_py.is_file():
        metadata = _setup_py_metadata(setup_py)
        package_dir = metadata.get("package_dir")
        metadata["source_root"] = package_dir.get("", ".") if isinstance(package_dir, dict) else "."
        return setup_py, metadata
    raise ValueError("Python package has no pyproject.toml, setup.cfg, or setup.py")


def _package_directories(source_root: Path) -> list[Path]:
    packages: set[Path] = set()
    candidate_directories = {
        path.parent for path in source_root.rglob("*.py") if path.parent != source_root
    }
    for directory in candidate_directories:
        relative = directory.relative_to(source_root)
        if not relative.parts or relative.parts[0].casefold() in _EXCLUDED_ROOTS:
            continue
        if any(part.startswith(".") for part in relative.parts):
            continue
        packages.add(relative)
    return sorted(packages, key=lambda item: (len(item.parts), item.as_posix()))


def _namespace_parents(packages: list[Path], source_root: Path) -> list[str]:
    namespaces: set[str] = set()
    for package in packages:
        for length in range(1, len(package.parts)):
            parent = Path(*package.parts[:length])
            if not (source_root / parent / "__init__.py").is_file():
                namespaces.add(".".join(parent.parts))
    return sorted(namespaces)


def _module_all(path: Path) -> list[str]:
    if not path.is_file():
        return []
    tree = ast.parse(path.read_text(encoding="utf-8-sig", errors="replace"), filename=str(path))
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)) and any(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in (node.targets if isinstance(node, ast.Assign) else [node.target])
        ):
            value = _literal(node.value) if node.value is not None else None
            if isinstance(value, (list, tuple, set)):
                return [item for item in value if isinstance(item, str)]
    return []


def _declared_package_paths(declared: list[str]) -> list[Path]:
    normalized: list[Path] = []
    for item in declared:
        if not isinstance(item, str) or not item:
            continue
        value = item.replace("\\", "/").strip("./")
        value = value.removesuffix("*").removesuffix(".").replace(".", "/")
        if any(character in value for character in "?[]"):
            continue
        if value:
            normalized.append(Path(value))
    return sorted(set(normalized), key=lambda item: (len(item.parts), item.as_posix()))


def _canonical_import(packages: list[Path], source_root: Path, declared: list[str]) -> str:
    explicit_paths = _declared_package_paths(declared)
    dotted_explicit = [".".join(item.parts) for item in explicit_paths if len(item.parts) > 1]
    if dotted_explicit:
        return dotted_explicit[0]
    if len(explicit_paths) == 1 and explicit_paths[0] in packages:
        root_package = explicit_paths[0]
        exported = _module_all(source_root / root_package / "__init__.py")
        direct_children = {
            package.parts[-1]: package
            for package in packages
            if len(package.parts) == len(root_package.parts) + 1
            and package.parts[: len(root_package.parts)] == root_package.parts
        }
        public_children = [direct_children[name] for name in exported if name in direct_children]
        if len(public_children) == 1:
            return ".".join(public_children[0].parts)
        if len(direct_children) == 1 and root_package.name.casefold() == "aspose":
            return ".".join(next(iter(direct_children.values())).parts)
        return ".".join(root_package.parts)
    shallow = [package for package in packages if len(package.parts) == 1]
    if len(shallow) == 1:
        root_package = shallow[0]
        exported = _module_all(source_root / root_package / "__init__.py")
        child_packages = {
            package.parts[-1]: package
            for package in packages
            if len(package.parts) == 2 and package.parts[0] == root_package.name
        }
        public_children = [child_packages[name] for name in exported if name in child_packages]
        if len(public_children) == 1:
            return ".".join(public_children[0].parts)
        return root_package.name
    if packages:
        return ".".join(packages[0].parts)
    raise ValueError("Python package manifest has no discoverable distributed package")


def inspect_python_package_layout(repository_root: Path) -> PythonPackageLayoutV1:
    """Return deterministic distribution roots for common setuptools layouts."""

    manifest, metadata = _manifest_metadata(repository_root)
    relative_source = str(metadata.get("source_root") or ".").replace("\\", "/")
    source_root = (repository_root / relative_source).resolve()
    try:
        source_root.relative_to(repository_root.resolve())
    except ValueError as exc:
        raise ValueError("Python package source root escapes the repository") from exc
    if not source_root.is_dir():
        raise ValueError(f"Python package source root does not exist: {relative_source}")
    packages = _package_directories(source_root)
    declared = metadata.get("declared_packages") or []
    if isinstance(declared, str):
        declared = [item.strip() for item in declared.splitlines() if item.strip()]
    declared_paths = _declared_package_paths(list(declared))
    if declared_paths:
        packages = [
            package
            for package in packages
            if any(
                package == declared_path or package.is_relative_to(declared_path)
                for declared_path in declared_paths
            )
        ]
    canonical = _canonical_import(packages, source_root, list(declared))
    digest = hashlib.sha256()
    digest.update(manifest.relative_to(repository_root).as_posix().encode("utf-8"))
    digest.update(b"\0")
    digest.update(manifest.read_bytes())
    digest.update(b"\0")
    for package in packages:
        path = source_root / package / "__init__.py"
        digest.update(package.as_posix().encode("utf-8"))
        digest.update(b"\0")
        if path.is_file():
            digest.update(path.read_bytes())
        digest.update(b"\0")
    distribution_name = metadata.get("name")
    if not isinstance(distribution_name, str) or not distribution_name:
        raise ValueError("Python package manifest has no literal distribution name")
    return PythonPackageLayoutV1(
        manifest_path=manifest.relative_to(repository_root).as_posix(),
        distribution_name=distribution_name,
        version=str(metadata["version"]) if metadata.get("version") else None,
        requires_python=(
            str(metadata.get("requires_python") or metadata.get("python_requires"))
            if metadata.get("requires_python") or metadata.get("python_requires")
            else None
        ),
        source_root=Path(relative_source).as_posix(),
        package_paths=[package.as_posix() for package in packages],
        canonical_import=canonical,
        namespace_packages=_namespace_parents(packages, source_root),
        source_sha256=digest.hexdigest(),
    )
