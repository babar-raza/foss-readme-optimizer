"""Extract minimal public Python consumers from repository-owned examples."""

from __future__ import annotations

import ast
import builtins
import sys
from pathlib import Path

from readme_agent.ecosystems.python_package_layout import inspect_python_package_layout
from readme_agent.registry.models import MinimalExamplePolicy

_BUILTIN_NAMES = frozenset(dir(builtins))
_STDLIB_MODULES = frozenset(sys.stdlib_module_names)
_SUPPORTED_STATEMENTS = (ast.Assign, ast.AnnAssign, ast.Expr)


def _import_bindings(node: ast.stmt, package_name: str) -> set[str]:
    if isinstance(node, ast.ImportFrom) and node.module is not None:
        if node.module != package_name and not node.module.startswith(f"{package_name}."):
            return set()
        return {alias.asname or alias.name for alias in node.names if alias.name != "*"}
    if isinstance(node, ast.Import):
        return {
            alias.asname or alias.name.split(".", 1)[0]
            for alias in node.names
            if alias.name == package_name or alias.name.startswith(f"{package_name}.")
        }
    return set()


def _minimal_import(node: ast.stmt, used_bindings: set[str]) -> ast.stmt | None:
    if isinstance(node, ast.ImportFrom):
        aliases = [alias for alias in node.names if (alias.asname or alias.name) in used_bindings]
        return (
            ast.ImportFrom(module=node.module, names=aliases, level=node.level) if aliases else None
        )
    if isinstance(node, ast.Import):
        aliases = [
            alias
            for alias in node.names
            if (alias.asname or alias.name.split(".", 1)[0]) in used_bindings
        ]
        return ast.Import(names=aliases) if aliases else None
    return None


def _bound_names(node: ast.stmt) -> set[str]:
    if isinstance(node, ast.Import):
        return {alias.asname or alias.name.split(".", 1)[0] for alias in node.names}
    if isinstance(node, ast.ImportFrom):
        return {alias.asname or alias.name for alias in node.names if alias.name != "*"}
    targets = (
        node.targets
        if isinstance(node, ast.Assign)
        else [node.target]
        if isinstance(node, ast.AnnAssign)
        else []
    )
    return {target.id for target in targets if isinstance(target, ast.Name)}


def _loaded_names(node: ast.AST) -> set[str]:
    return {
        item.id
        for item in ast.walk(node)
        if isinstance(item, ast.Name) and isinstance(item.ctx, ast.Load)
    }


def _supported_import(node: ast.stmt, package_name: str) -> bool:
    if isinstance(node, ast.Import):
        return all(
            alias.name.split(".", 1)[0] in _STDLIB_MODULES
            or alias.name == package_name
            or alias.name.startswith(f"{package_name}.")
            for alias in node.names
        )
    if isinstance(node, ast.ImportFrom) and node.module:
        root = node.module.split(".", 1)[0]
        return (
            root in _STDLIB_MODULES
            or node.module == package_name
            or node.module.startswith(f"{package_name}.")
        )
    return True


def _attribute_chain(node: ast.AST) -> tuple[str, ...] | None:
    parts: list[str] = []
    current = node
    while isinstance(current, ast.Attribute):
        if current.attr.startswith("_"):
            return None
        parts.append(current.attr)
        current = current.value
    if not isinstance(current, ast.Name):
        return None
    parts.append(current.id)
    return tuple(reversed(parts))


def _public_package_call(statement: ast.stmt, bindings: set[str]) -> tuple[str, ...] | None:
    calls = sorted(
        (node for node in ast.walk(statement) if isinstance(node, ast.Call)),
        key=lambda node: (node.lineno, node.col_offset),
    )
    for call in calls:
        chain = _attribute_chain(call.func)
        if chain is not None and len(chain) >= 2 and chain[0] in bindings:
            return chain
    return None


def _statement_candidate(
    statement: ast.stmt,
    package_imports: list[tuple[ast.stmt, set[str]]],
    support_nodes: list[ast.stmt],
    *,
    relative_path: str,
    max_chars: int,
) -> MinimalExamplePolicy | None:
    package_bindings = set().union(*(names for _, names in package_imports))
    chain = _public_package_call(statement, package_bindings)
    if chain is None:
        return None
    available: dict[str, ast.stmt] = {}
    for node in support_nodes:
        for name in _bound_names(node):
            available[name] = node
    selected: set[ast.stmt] = set()
    selected_binding_names: set[str] = set()
    unresolved = list(_loaded_names(statement) - _BUILTIN_NAMES)
    resolved: set[str] = set()
    while unresolved:
        name = unresolved.pop()
        if name in resolved:
            continue
        dependency_node = available.get(name)
        if dependency_node is None:
            return None
        selected.add(dependency_node)
        selected_binding_names.add(name)
        resolved.update(_bound_names(dependency_node))
        unresolved.extend(_loaded_names(dependency_node) - resolved - _BUILTIN_NAMES)
    if not (resolved & package_bindings):
        return None
    ordered = sorted(selected, key=lambda node: (node.lineno, node.col_offset))
    rendered_imports: list[str] = []
    rendered_support: list[str] = []
    for node in ordered:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            minimized = _minimal_import(node, selected_binding_names)
            if minimized is not None:
                rendered_imports.append(ast.unparse(minimized))
        else:
            rendered_support.append(ast.unparse(node))
    code = "\n".join(rendered_imports)
    if rendered_imports:
        code += "\n\n"
    code += "\n".join([*rendered_support, ast.unparse(statement)]) + "\n"
    if len(code) > max_chars:
        return None
    class_name = next((part for part in chain[1:] if part[:1].isupper()), "readme_example")
    return MinimalExamplePolicy(
        language="python",
        class_name=class_name,
        code=code,
        evidence_paths=[relative_path],
        required_symbols=[".".join(chain)],
    )


def python_source_example_candidates(
    root: Path,
    paths: list[Path],
    *,
    max_chars: int,
) -> list[MinimalExamplePolicy]:
    """Return self-contained repository-evidenced public API operations."""

    try:
        package_name = inspect_python_package_layout(root).canonical_import
    except (OSError, SyntaxError, ValueError):
        return []
    candidates: list[MinimalExamplePolicy] = []
    for path in paths:
        try:
            tree = ast.parse(
                path.read_text(encoding="utf-8-sig", errors="replace"),
                filename=str(path),
            )
        except (OSError, SyntaxError):
            continue
        package_imports = [
            (node, bindings)
            for node in tree.body
            if (bindings := _import_bindings(node, package_name))
        ]
        if not package_imports:
            continue
        module_support = [
            node
            for node in tree.body
            if isinstance(node, (ast.Import, ast.ImportFrom, ast.Assign, ast.AnnAssign))
            and _supported_import(node, package_name)
        ]
        containers = [tree.body]
        containers.extend(
            node.body
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        )
        containers.extend(
            member.body
            for node in tree.body
            if isinstance(node, ast.ClassDef)
            for member in node.body
            if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
        )
        relative_path = path.relative_to(root).as_posix()
        for statements in containers:
            for index, statement in enumerate(statements):
                if not isinstance(statement, _SUPPORTED_STATEMENTS):
                    continue
                local_support = [
                    node
                    for node in statements[:index]
                    if isinstance(node, (ast.Import, ast.ImportFrom, ast.Assign, ast.AnnAssign))
                    and _supported_import(node, package_name)
                ]
                candidate = _statement_candidate(
                    statement,
                    package_imports,
                    [*module_support, *local_support],
                    relative_path=relative_path,
                    max_chars=max_chars,
                )
                if candidate is not None:
                    candidates.append(candidate)
    return sorted(candidates, key=lambda item: (len(item.code), item.evidence_paths[0]))
