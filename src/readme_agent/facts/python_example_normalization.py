"""Repairs import-inventory Python drafts into source-proven minimal consumers."""

from __future__ import annotations

import ast
import re
from pathlib import Path

from readme_agent.ecosystems.python_public_api import inspect_python_public_api
from readme_agent.registry.models import MinimalExamplePolicy


def _has_no_required_constructor_arguments(path: Path, class_name: str) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"), filename=str(path))
    declaration = next(
        (node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name),
        None,
    )
    if declaration is None:
        return False
    initializer = next(
        (
            node
            for node in declaration.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "__init__"
        ),
        None,
    )
    if initializer is None:
        return True
    positional = [*initializer.args.posonlyargs, *initializer.args.args]
    if positional and positional[0].arg in {"self", "cls"}:
        positional = positional[1:]
    required_positional = len(positional) - len(initializer.args.defaults)
    required_keyword_only = sum(default is None for default in initializer.args.kw_defaults)
    return required_positional == 0 and required_keyword_only == 0


def _variable_name(class_name: str) -> str:
    words = re.sub(r"(?<!^)(?=[A-Z])", "_", class_name).casefold()
    return words if words.isidentifier() else "product"


def normalize_python_import_inventory(
    root: Path,
    example: MinimalExamplePolicy,
) -> MinimalExamplePolicy:
    """Replace an import-only inventory with one verifiable public construction."""

    root = root.resolve()
    try:
        tree = ast.parse(example.code)
    except SyntaxError:
        return example
    import_statements = [
        node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))
    ]
    if not import_statements:
        return example
    imported_modules = {
        node.module if isinstance(node, ast.ImportFrom) else alias.name
        for node in import_statements
        for alias in (node.names if isinstance(node, ast.Import) else [node.names[0]])
        if (isinstance(node, ast.Import) or node.module is not None)
    }
    has_executable_statement = len(import_statements) != len(tree.body)
    if has_executable_statement and len(imported_modules) == 1:
        return example

    try:
        surface = inspect_python_public_api(
            root,
            org_repo="local/source",
            source_revision="local-source",
        )
    except (OSError, SyntaxError, ValueError):
        return example
    symbols = {symbol.qualified_name: symbol for symbol in surface.symbols}
    for statement in import_statements:
        if not isinstance(statement, ast.ImportFrom) or statement.module is None:
            continue
        for alias in statement.names:
            if alias.name == "*":
                continue
            qualified_name = f"{statement.module}.{alias.name}"
            symbol = symbols.get(qualified_name)
            if symbol is None or symbol.kind != "class":
                continue
            declaration = (
                symbols.get(symbol.reexported_from)
                if symbol.reexported_from is not None
                else symbol
            )
            if declaration is None or declaration.kind != "class":
                continue
            declaration_name = (
                symbol.reexported_from.rsplit(".", 1)[-1]
                if symbol.reexported_from
                else symbol.name.rsplit(".", 1)[-1]
            )
            declaration_path = root / declaration.source_path
            if not _has_no_required_constructor_arguments(declaration_path, declaration_name):
                continue
            local_name = alias.asname or alias.name
            import_alias = f" as {alias.asname}" if alias.asname else ""
            code = (
                f"from {statement.module} import {alias.name}{import_alias}\n\n"
                f"{_variable_name(local_name)} = {local_name}()\n"
            )
            return example.model_copy(
                update={
                    "class_name": local_name,
                    "code": code,
                    "evidence_paths": [declaration.source_path],
                    "required_symbols": [declaration_name],
                }
            )
    return example
