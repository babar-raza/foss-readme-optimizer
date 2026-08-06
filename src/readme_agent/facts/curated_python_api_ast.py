"""Render Python API signatures and resolve source-level return annotations."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
from functools import lru_cache
from pathlib import Path

from readme_agent.ecosystems.python_api_schema import PublicSymbolV1


def source_sha256(path: Path) -> str:
    """Hash exact source bytes used by a projected symbol."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def module_from_source(path: str, source_root: str) -> str | None:
    """Resolve a source path to its import module inside one package layout."""

    prefix = "" if source_root == "." else f"{source_root.rstrip('/')}/"
    if not path.startswith(prefix) or not path.endswith(".py"):
        return None
    return path.removeprefix(prefix).removesuffix(".py").replace("/", ".").removesuffix(".__init__")


@lru_cache(maxsize=256)
def _source_tree(path: Path, modified_ns: int, size: int) -> ast.Module:
    del modified_ns, size
    return ast.parse(path.read_text(encoding="utf-8-sig", errors="replace"))


def _method_call(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    positional = [*node.args.posonlyargs, *node.args.args]
    if positional and positional[0].arg in {"self", "cls"}:
        positional = positional[1:]
    defaults = [None] * (len(positional) - len(node.args.defaults)) + list(node.args.defaults)
    rendered = [
        arg.arg + ("=" + ast.unparse(default) if default is not None else "")
        for arg, default in zip(positional, defaults, strict=True)
    ]
    if node.args.vararg:
        rendered.append("*" + node.args.vararg.arg)
    rendered.extend(argument.arg for argument in node.args.kwonlyargs)
    if node.args.kwarg:
        rendered.append("**" + node.args.kwarg.arg)
    return f"{node.name}({', '.join(rendered)})"


def _parameters(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[dict[str, object]]:
    positional = [*node.args.posonlyargs, *node.args.args]
    if positional and positional[0].arg in {"self", "cls"}:
        positional = positional[1:]
    defaults = [None] * (len(positional) - len(node.args.defaults)) + list(node.args.defaults)
    rows: list[dict[str, object]] = [
        {
            "name": argument.arg,
            "kind": "positional",
            "annotation": ast.unparse(argument.annotation) if argument.annotation else None,
            "default": ast.unparse(default) if default is not None else None,
        }
        for argument, default in zip(positional, defaults, strict=True)
    ]
    if node.args.vararg:
        rows.append(
            {
                "name": node.args.vararg.arg,
                "kind": "var_positional",
                "annotation": (
                    ast.unparse(node.args.vararg.annotation)
                    if node.args.vararg.annotation
                    else None
                ),
                "default": None,
            }
        )
    rows.extend(
        {
            "name": argument.arg,
            "kind": "keyword_only",
            "annotation": ast.unparse(argument.annotation) if argument.annotation else None,
            "default": ast.unparse(default) if default is not None else None,
        }
        for argument, default in zip(node.args.kwonlyargs, node.args.kw_defaults, strict=True)
    )
    if node.args.kwarg:
        rows.append(
            {
                "name": node.args.kwarg.arg,
                "kind": "var_keyword",
                "annotation": (
                    ast.unparse(node.args.kwarg.annotation) if node.args.kwarg.annotation else None
                ),
                "default": None,
            }
        )
    return rows


def member_surface(root: Path, symbol: PublicSymbolV1) -> str:
    """Render one exact source-bound public member surface."""

    name = symbol.name.rsplit(".", 1)[-1]
    path = root / symbol.source_path
    try:
        stat = path.stat()
        tree = _source_tree(path, stat.st_mtime_ns, stat.st_size)
    except (OSError, SyntaxError, UnicodeDecodeError):
        return name
    node = next(
        (
            item
            for item in ast.walk(tree)
            if getattr(item, "lineno", None) == symbol.source_line
            and getattr(item, "name", None) == name
        ),
        None,
    )
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        if symbol.kind == "property":
            return f"{name}: {ast.unparse(node.returns)}" if node.returns else name
        return _method_call(node)
    return f"{name}: {symbol.annotation}" if symbol.annotation else name


def _symbol_node(root: Path, symbol: PublicSymbolV1) -> ast.AST | None:
    path = root / symbol.source_path
    try:
        stat = path.stat()
        tree = _source_tree(path, stat.st_mtime_ns, stat.st_size)
    except (OSError, SyntaxError, UnicodeDecodeError):
        return None
    name = symbol.name.rsplit(".", 1)[-1]
    return next(
        (
            item
            for item in ast.walk(tree)
            if getattr(item, "lineno", None) == symbol.source_line
            and getattr(item, "name", None) == name
        ),
        None,
    )


def member_return_annotation(root: Path, symbol: PublicSymbolV1) -> str | None:
    """Return only an annotation explicitly declared on the source member."""

    node = _symbol_node(root, symbol)
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or node.returns is None:
        return None
    return ast.unparse(node.returns)


def class_source_semantics(root: Path, symbol: PublicSymbolV1) -> dict[str, object]:
    """Extract exact class bases and a directly declared constructor signature."""

    node = _symbol_node(root, symbol)
    if not isinstance(node, ast.ClassDef):
        return {}
    value: dict[str, object] = {
        "bases": [ast.unparse(base) for base in node.bases],
    }
    constructor = next(
        (
            item
            for item in node.body
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == "__init__"
        ),
        None,
    )
    if constructor is not None:
        value["constructor"] = {
            "surface": _method_call(constructor).replace("__init__", symbol.name, 1),
            "line": constructor.lineno,
            "source_path": symbol.source_path,
            "source_sha256": source_sha256(root / symbol.source_path),
            "parameters": _parameters(constructor),
            "return_annotation": (
                ast.unparse(constructor.returns) if constructor.returns is not None else None
            ),
        }
    return value


def function_imports(path: Path, module: str) -> dict[str, str]:
    """Resolve direct and relative imports used by a function return annotation."""

    try:
        tree = ast.parse(path.read_text(encoding="utf-8-sig", errors="replace"))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return {}
    imports, package = {}, module.rpartition(".")[0]
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        origin = node.module
        if node.level:
            try:
                origin = importlib.util.resolve_name(
                    "." * node.level + (node.module or ""), package
                )
            except (ImportError, ValueError):
                continue
        if origin:
            imports.update(
                {item.asname or item.name: f"{origin}:{item.name}" for item in node.names}
            )
    return imports
