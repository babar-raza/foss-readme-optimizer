"""Collect duplicate Python package exports whose final binding changes inheritance."""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path

_IGNORED = {".git", ".venv", "__pycache__", "node_modules"}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_path(initializer: Path, node: ast.ImportFrom, imported_name: str) -> Path | None:
    if node.level < 1:
        return None
    base = initializer.parent
    for _ in range(node.level - 1):
        base = base.parent
    module = Path(*(node.module or "").split("."))
    candidate = base / module
    return next(
        (
            path
            for path in (candidate.with_suffix(".py"), candidate / "__init__.py")
            if path.is_file()
        ),
        None,
    )


def _class_bases(path: Path, name: str) -> list[str] | None:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return None
    matching = [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == name]
    if len(matching) != 1:
        return None
    return [ast.unparse(base).rsplit(".", 1)[-1] for base in matching[0].bases]


def python_import_shadowing(root: Path) -> tuple[object, list[str]] | None:
    """Return hash-bound duplicate exports only when source proves their final class binding."""

    entries: list[dict[str, object]] = []
    locations: set[str] = set()
    for initializer in sorted(root.rglob("__init__.py")):
        relative_initializer = initializer.relative_to(root)
        if any(part in _IGNORED for part in relative_initializer.parts):
            continue
        try:
            tree = ast.parse(initializer.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        bindings: dict[str, list[dict[str, object]]] = {}
        for node in tree.body:
            if not isinstance(node, ast.ImportFrom):
                continue
            for alias in node.names:
                local_name = alias.asname or alias.name
                source = _source_path(initializer, node, alias.name)
                if source is None:
                    continue
                bases = _class_bases(source, alias.name)
                if bases is None:
                    continue
                relative_source = source.relative_to(root).as_posix()
                bindings.setdefault(local_name, []).append(
                    {
                        "source_path": relative_source,
                        "source_sha256": _sha256(source),
                        "class_name": alias.name,
                        "bases": bases,
                        "line": node.lineno,
                    }
                )
                locations.add(relative_source)
        for symbol, history in sorted(bindings.items()):
            unique_sources = {str(item["source_path"]) for item in history}
            if len(history) < 2 or len(unique_sources) < 2:
                continue
            prior, final = history[-2], history[-1]
            if prior["bases"] == final["bases"]:
                continue
            entries.append(
                {
                    "package_initializer": relative_initializer.as_posix(),
                    "package_initializer_sha256": _sha256(initializer),
                    "symbol": symbol,
                    "binding_history": history,
                    "final_source_path": final["source_path"],
                    "final_bases": final["bases"],
                    "inheritance_changed": True,
                }
            )
            locations.add(relative_initializer.as_posix())
    if not entries:
        return None
    return {"schema_version": 1, "entries": entries}, sorted(locations)


__all__ = ["python_import_shadowing"]
