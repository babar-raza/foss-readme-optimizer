"""Extract explicit executable constraints without trusting README prose."""

from __future__ import annotations

import ast
import hashlib
import re
from pathlib import Path

_CONSTRAINT_POLARITY = re.compile(
    r"\b(?:not\s+supported|only\b.+\bsupported|requires?)\b",
    flags=re.IGNORECASE,
)


def source_limitations(root: Path) -> tuple[object, list[str]] | None:
    """Extract literal constraints from raised exceptions, never README assertions."""

    found: list[dict[str, object]] = []
    locations: list[str] = []
    source_root = root / "src"
    if not source_root.is_dir():
        return None
    for path in sorted(source_root.rglob("*.py")):
        try:
            text = path.read_text(encoding="utf-8")
            tree = ast.parse(text)
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        relative = path.relative_to(root).as_posix()
        source_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Raise) or not isinstance(node.exc, ast.Call):
                continue
            if not node.exc.args:
                continue
            message = node.exc.args[0]
            if (
                not isinstance(message, ast.Constant)
                or not isinstance(message.value, str)
                or _CONSTRAINT_POLARITY.search(message.value) is None
            ):
                continue
            record = {
                "statement": message.value.strip(),
                "path": relative,
                "line": node.lineno,
                "source_sha256": source_sha256,
            }
            if any(item["statement"] == record["statement"] for item in found):
                continue
            found.append(record)
            locations.append(relative)
    if not found:
        return None
    return found, sorted(set(locations))
