"""Extract minimal public Python consumers from repository-owned examples."""

from __future__ import annotations

import ast
import builtins
from pathlib import Path

from readme_agent.ecosystems.python_package_layout import inspect_python_package_layout
from readme_agent.registry.models import MinimalExamplePolicy

_BUILTIN_NAMES = frozenset(dir(builtins))
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
    imports: list[tuple[ast.stmt, set[str]]],
    *,
    relative_path: str,
    max_chars: int,
) -> MinimalExamplePolicy | None:
    bindings = set().union(*(names for _, names in imports))
    chain = _public_package_call(statement, bindings)
    if chain is None:
        return None
    loaded_names = {
        node.id
        for node in ast.walk(statement)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
    }
    used_bindings = loaded_names & bindings
    if not used_bindings or loaded_names - used_bindings - _BUILTIN_NAMES:
        return None
    selected_imports = [
        selected
        for node, _ in imports
        if (selected := _minimal_import(node, used_bindings)) is not None
    ]
    code = "\n".join(ast.unparse(node) for node in selected_imports)
    code += "\n\n" + ast.unparse(statement) + "\n"
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
        imports = [
            (node, bindings)
            for node in tree.body
            if (bindings := _import_bindings(node, package_name))
        ]
        if not imports:
            continue
        containers = [tree.body]
        containers.extend(
            node.body
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        )
        relative_path = path.relative_to(root).as_posix()
        for statements in containers:
            for statement in statements:
                if not isinstance(statement, _SUPPORTED_STATEMENTS):
                    continue
                candidate = _statement_candidate(
                    statement,
                    imports,
                    relative_path=relative_path,
                    max_chars=max_chars,
                )
                if candidate is not None:
                    candidates.append(candidate)
    return sorted(candidates, key=lambda item: (len(item.code), item.evidence_paths[0]))
