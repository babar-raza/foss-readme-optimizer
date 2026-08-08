"""Collect checksum-bound Python implementation components for public claim accountability."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

_PARSER_FILE = re.compile(r"(?:^|_)(?:parser|reader|loader)(?:_|$)", re.IGNORECASE)
_IGNORED_PARTS = {".git", ".venv", "build", "dist", "tests", "test"}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _public_label(token: str) -> str:
    normalized = token.strip("_-").casefold()
    if normalized in {"ms_one", "ms-one"}:
        return "MS-ONE"
    if normalized == "onestore":
        return "OneStore"
    return token.strip("_-")


def python_implementation_components(root: Path) -> tuple[object, list[str]] | None:
    """Return source-backed parser components without interpreting README prose."""

    source_root = root / "src"
    if not source_root.is_dir():
        return None
    components: list[dict[str, object]] = []
    locations: list[str] = []
    for path in sorted(source_root.rglob("*.py")):
        relative = path.relative_to(root).as_posix()
        parts = path.relative_to(source_root).parts
        if any(part.casefold() in _IGNORED_PARTS for part in parts):
            continue
        stem_tokens = [part for part in (*parts[:-1], path.stem) if part != "_internal"]
        if not _PARSER_FILE.search(path.stem):
            continue
        labels = sorted(
            {
                label
                for token in stem_tokens
                if (label := _public_label(token)) in {"MS-ONE", "OneStore"}
            }
        )
        if not labels:
            continue
        components.append(
            {
                "kind": "parser",
                "labels": labels,
                "path": relative,
                "source_sha256": _sha256(path),
            }
        )
        locations.append(relative)
    if not components:
        return None
    return {"components": components}, locations


__all__ = ["python_implementation_components"]
