"""Collect bounded repository resource inventories for README navigation."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

_IGNORED_DIRECTORIES = {".git", ".venv", "__pycache__", "node_modules"}
_MAX_REPRESENTATIVES = 8

_PROJECT_STRUCTURE_HEADING = re.compile(r"(?m)^##[ \t]+Project Structure[ \t]*$")
_FENCED_BLOCK = re.compile(r"```[^\n]*\n(?P<body>.*?)```", re.DOTALL)
_TREE_LINE = re.compile(r"^(?P<indent>(?:│[ ]{3}|[ ]{4})*)(?P<marker>[├└]── )(?P<rest>\S.*)$")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _relative_files(root: Path, directory: str, *, suffix: str | None = None) -> list[Path]:
    base = root / directory
    if not base.is_dir():
        return []
    return sorted(
        (
            path
            for path in base.rglob("*")
            if path.is_file()
            and not any(part in _IGNORED_DIRECTORIES for part in path.relative_to(root).parts)
            and (suffix is None or path.suffix == suffix)
        ),
        key=lambda path: path.relative_to(root).as_posix(),
    )


def development_assets(root: Path) -> tuple[object, list[str]] | None:
    groups = {
        "tests": _relative_files(root, "tests", suffix=".py"),
        "tools": _relative_files(root, "tools", suffix=".py"),
        "goldens": _relative_files(root, "tests/goldens"),
    }
    value: dict[str, dict[str, object]] = {}
    locations: list[str] = []
    for name, paths in groups.items():
        if not paths:
            continue
        rows = [
            {"path": path.relative_to(root).as_posix(), "sha256": _sha256(path)} for path in paths
        ]
        canonical = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
        representatives = rows[:_MAX_REPRESENTATIVES]
        value[name] = {
            "count": len(rows),
            "inventory_sha256": hashlib.sha256(canonical).hexdigest(),
            "representative_paths": representatives,
        }
        locations.extend(row["path"] for row in representatives)
    makefile = root / "Makefile"
    if makefile.is_file():
        text = makefile.read_text(encoding="utf-8")
        targets = {
            match.group("target")
            for match in re.finditer(r"(?m)^(?P<target>[A-Za-z0-9_.-]+):(?:\s|$)", text)
        }
        commands = [
            {"target": target, "command": f"make {target}", "path": "Makefile"}
            for target in ("sync", "test", "build", "check")
            if target in targets
        ]
        if commands:
            value["commands"] = {
                "count": len(commands),
                "makefile_sha256": _sha256(makefile),
                "entries": commands,
            }
            locations.append("Makefile")
    if not value:
        return None
    return value, locations


def third_party_notices(root: Path) -> tuple[object, list[str]] | None:
    for name in ("THIRD_PARTY_NOTICES.md", "THIRD-PARTY-NOTICES.md", "NOTICE"):
        path = root / name
        if path.is_file():
            return {"path": name, "sha256": _sha256(path)}, [name]
    return None


def repository_ci(root: Path) -> tuple[object, list[str]] | None:
    for relative in (".github/workflows/ci.yml", ".github/workflows/ci.yaml"):
        path = root / relative
        if path.is_file():
            return {"path": relative, "sha256": _sha256(path)}, [relative]
    return None


def repository_project_structure(root: Path) -> tuple[object, list[str]] | None:
    """Return the maintainer's own directory-tree diagram, verified path-by-path.

    Every entry the diagram names must resolve to a real file or directory under
    ``root``; a single unverifiable or unparseable line drops the whole fact rather
    than risk rendering an invented or stale layout.
    """
    readme = root / "README.md"
    if not readme.is_file():
        return None
    text = readme.read_text(encoding="utf-8", errors="replace")
    heading = _PROJECT_STRUCTURE_HEADING.search(text)
    if heading is None:
        return None
    block = _FENCED_BLOCK.search(text, heading.end())
    if block is None:
        return None
    intro = text[heading.end() : block.start()].strip()
    stack: dict[int, str] = {}
    verified_any = False
    for line in block.group("body").splitlines():
        if not line.strip():
            continue
        line_match = _TREE_LINE.match(line)
        if line_match is None:
            return None
        depth = len(line_match.group("indent")) // 4
        fragment = re.split(r"\s{2,}", line_match.group("rest"), maxsplit=1)[0].strip().rstrip("/")
        if not fragment:
            return None
        stack[depth] = fragment
        try:
            full_path = "/".join(stack[level] for level in range(depth + 1))
        except KeyError:
            return None
        if not (root / full_path).exists():
            return None
        verified_any = True
    if not verified_any:
        return None
    value: dict[str, str] = {"tree": block.group("body").rstrip("\n")}
    if intro:
        value["intro"] = intro
    return value, ["README.md"]
