"""Extract deterministic public Python symbols and re-export provenance."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
from pathlib import Path

from readme_agent.ecosystems.python_api_schema import (
    PublicApiSurfaceV1,
    PublicSymbolV1,
    PythonPackageLayoutV1,
)
from readme_agent.ecosystems.python_package_layout import inspect_python_package_layout
from readme_agent.ecosystems.python_symbol_members import (
    annotation,
    class_symbols,
    decorators,
    python_symbol,
)


def _literal_all(tree: ast.Module) -> set[str] | None:
    names: set[str] = set()
    found = False
    for node in tree.body:
        value: ast.AST | None = None
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "__all__" for target in node.targets
        ):
            value = node.value
            found = True
        elif (
            isinstance(node, ast.AugAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "__all__"
            and isinstance(node.op, ast.Add)
        ):
            value = node.value
            found = True
        if value is None:
            continue
        try:
            resolved = ast.literal_eval(value)
        except (ValueError, TypeError):
            continue
        if isinstance(resolved, (list, tuple, set)):
            names.update(item for item in resolved if isinstance(item, str))
    return names if found else None


def _public_name(name: str, explicit: set[str] | None) -> tuple[bool, str]:
    if name.startswith("_"):
        return False, "name"
    if explicit is not None:
        return name in explicit, "__all__"
    return True, "name"


def _module_name(path: Path, source_root: Path) -> tuple[str, bool]:
    relative = path.relative_to(source_root)
    is_package = path.name == "__init__.py"
    parts = relative.parent.parts if is_package else relative.with_suffix("").parts
    return ".".join(parts), is_package


def _resolved_relative(module: str, is_package: bool, node: ast.ImportFrom) -> str | None:
    if node.level == 0:
        return node.module
    package = module if is_package else module.rpartition(".")[0]
    try:
        return importlib.util.resolve_name("." * node.level + (node.module or ""), package)
    except (ImportError, ValueError):
        return None


def _module_symbols(
    path: Path,
    source_root: Path,
    repository_root: Path,
) -> tuple[list[PublicSymbolV1], list[str]]:
    tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"), filename=str(path))
    module, is_package = _module_name(path, source_root)
    if not module or any(part.startswith("_") for part in module.split(".")):
        return [], []
    explicit = _literal_all(tree)
    symbols: list[PublicSymbolV1] = [
        python_symbol(
            module=module,
            name="",
            kind="module",
            path=path,
            repository_root=repository_root,
            line=1,
            public_by="name",
        )
    ]
    unresolved: list[str] = []
    for node in tree.body:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            public, public_by = _public_name(node.name, explicit)
            if not public:
                continue
            if isinstance(node, ast.ClassDef):
                members = class_symbols(node, module, path, repository_root)
                members[0] = members[0].model_copy(update={"public_by": public_by})
                symbols.extend(members)
            else:
                symbols.append(
                    python_symbol(
                        module=module,
                        name=node.name,
                        kind="function",
                        path=path,
                        repository_root=repository_root,
                        line=node.lineno,
                        public_by=public_by,
                        decorators_=decorators(node),
                        annotation_=annotation(node.returns),
                    )
                )
        elif isinstance(node, ast.ImportFrom) and (is_package or explicit is not None):
            origin = _resolved_relative(module, is_package, node)
            if origin is None or any(alias.name == "*" for alias in node.names):
                unresolved.append(f"{module}:{node.lineno}:{ast.unparse(node)}")
                continue
            for alias in node.names:
                exposed = alias.asname or alias.name
                public, _ = _public_name(exposed, explicit)
                if not public:
                    continue
                origin_name = f"{origin}.{alias.name}" if node.module else f"{origin}.{alias.name}"
                symbols.append(
                    python_symbol(
                        module=module,
                        name=exposed,
                        kind="module" if node.module is None else "class",
                        path=path,
                        repository_root=repository_root,
                        line=node.lineno,
                        public_by="reexport",
                        reexported_from=origin_name,
                    )
                )
    return symbols, unresolved


def inspect_python_public_api(
    repository_root: Path,
    *,
    org_repo: str,
    source_revision: str,
    package: PythonPackageLayoutV1 | None = None,
) -> PublicApiSurfaceV1:
    """Inspect public definitions and package-level re-exports without importing code."""

    layout = package or inspect_python_package_layout(repository_root)
    source_root = (repository_root / layout.source_root).resolve()
    digest = hashlib.sha256()
    symbols: dict[str, PublicSymbolV1] = {}
    unresolved: list[str] = []
    for path in sorted(source_root.rglob("*.py")):
        relative = path.relative_to(repository_root).as_posix()
        if any(part in _EXCLUDED_PARTS for part in path.relative_to(source_root).parts):
            continue
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
        module_symbols, module_unresolved = _module_symbols(path, source_root, repository_root)
        for symbol in module_symbols:
            current = symbols.get(symbol.qualified_name)
            priority = (symbol.public_by == "reexport", symbol.kind != "module")
            current_priority = (
                (current.public_by == "reexport", current.kind != "module")
                if current is not None
                else (False, False)
            )
            if current is None or priority > current_priority:
                symbols[symbol.qualified_name] = symbol
        unresolved.extend(module_unresolved)
    reexports = [symbol for symbol in symbols.values() if symbol.reexported_from]
    for reexport in reexports:
        origin_prefix = f"{reexport.reexported_from}."
        for origin in list(symbols.values()):
            if not origin.qualified_name.startswith(origin_prefix):
                continue
            member_suffix = origin.qualified_name.removeprefix(origin_prefix)
            alias_name = f"{reexport.name}.{member_suffix}"
            alias = origin.model_copy(
                update={
                    "qualified_name": f"{reexport.import_module}.{alias_name}",
                    "import_module": reexport.import_module,
                    "name": alias_name,
                    "reexported_from": origin.qualified_name,
                    "public_by": "reexport",
                }
            )
            symbols.setdefault(alias.qualified_name, alias)
    return PublicApiSurfaceV1(
        org_repo=org_repo,
        source_revision=source_revision,
        package=layout,
        symbols=[symbols[name] for name in sorted(symbols)],
        unresolved_reexports=sorted(set(unresolved)),
        source_sha256=digest.hexdigest(),
    )


_EXCLUDED_PARTS = {"__pycache__", "build", "dist", "tests"}
