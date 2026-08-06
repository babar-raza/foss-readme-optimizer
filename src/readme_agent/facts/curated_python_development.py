"""Derive Python source roots and development commands from distribution metadata."""

from __future__ import annotations

import ast
import hashlib
import tomllib
from pathlib import Path

from readme_agent.ecosystems.python_package_layout import inspect_python_package_layout


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def distributed_python_source_roots(root: Path) -> list[Path]:
    """Return the minimal distributed package roots declared by the Python manifest."""

    try:
        layout = inspect_python_package_layout(root)
    except (OSError, SyntaxError, UnicodeDecodeError, ValueError):
        if any((root / name).is_file() for name in ("pyproject.toml", "setup.cfg", "setup.py")):
            return []
        legacy = root / "src"
        return [legacy] if legacy.is_dir() else []
    source_root = root / layout.source_root
    candidates = [source_root / package for package in layout.package_paths]
    existing = sorted({path for path in candidates if path.is_dir()})
    return [path for path in existing if not any(parent in existing for parent in path.parents)]


def _imports_module(path: Path, module: str) -> bool:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return False
    return any(
        (
            isinstance(node, ast.Import)
            and any(item.name.split(".")[0] == module for item in node.names)
        )
        or (isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] == module)
        for node in ast.walk(tree)
    )


def _pyproject_declares_pytest(path: Path) -> bool:
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, tomllib.TOMLDecodeError, UnicodeDecodeError):
        return False
    project = data.get("project", {})
    dependencies = list(project.get("dependencies", [])) if isinstance(project, dict) else []
    optional = project.get("optional-dependencies", {}) if isinstance(project, dict) else {}
    if isinstance(optional, dict):
        dependencies.extend(
            item for values in optional.values() if isinstance(values, list) for item in values
        )
    return any(str(item).casefold().startswith("pytest") for item in dependencies)


def _setup_declares_pytest(path: Path) -> bool:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return False
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        for keyword in node.keywords:
            if keyword.arg not in {"extras_require", "install_requires", "tests_require"}:
                continue
            try:
                value = ast.literal_eval(keyword.value)
            except (TypeError, ValueError):
                continue
            rendered = repr(value).casefold()
            if "pytest" in rendered:
                return True
    return False


def _source_record(root: Path, path: Path) -> dict[str, str]:
    return {"path": path.relative_to(root).as_posix(), "sha256": _sha256(path)}


def repository_development_commands(root: Path) -> tuple[object, list[str]] | None:
    """Return exact source-derived Python setup and test commands without executing them."""

    try:
        layout = inspect_python_package_layout(root)
    except (OSError, SyntaxError, UnicodeDecodeError, ValueError):
        return None
    manifest = root / layout.manifest_path
    entries: list[dict[str, object]] = []
    locations: list[str] = []
    mcp_tests = sorted(path for path in (root / "tests/mcp").glob("test_*.py") if path.is_file())
    if mcp_tests:
        sources = [_source_record(root, path) for path in mcp_tests]
        modules = [str(item["path"]).removesuffix(".py").replace("/", ".") for item in sources]
        entries.append(
            {
                "kind": "focused_test",
                "scope": "MCP",
                "command": "python -m unittest " + " ".join(modules),
                "sources": sources,
                "evidence_kind": "source_derived",
                "execution_verified": False,
            }
        )
        locations.extend(str(item["path"]) for item in sources)
    scripts = root / "scripts"
    for path in sorted(scripts.glob("*.sh")) if scripts.is_dir() else []:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        commands = [
            line.strip() for line in text.splitlines() if line.strip().startswith("python -m ")
        ]
        if commands:
            relative = path.relative_to(root).as_posix()
            entries.append(
                {
                    "kind": "repository_script",
                    "command": relative,
                    "embedded_commands": commands,
                    "path": relative,
                    "source_sha256": _sha256(path),
                    "evidence_kind": "source_derived",
                    "execution_verified": False,
                }
            )
            locations.append(relative)
    entries.append(
        {
            "kind": "editable_install",
            "command": "python -m pip install -e .",
            "sources": [_source_record(root, manifest)],
            "evidence_kind": "source_derived",
            "execution_verified": False,
        }
    )
    locations.append(layout.manifest_path)
    tests_root = root / "tests"
    tests = sorted(tests_root.glob("test_*.py")) if tests_root.is_dir() else []
    valid_tests = [path for path in tests if _imports_module(path, "unittest")]
    pytest_declared = (
        _pyproject_declares_pytest(manifest)
        if manifest.name == "pyproject.toml"
        else (_setup_declares_pytest(manifest) if manifest.name == "setup.py" else False)
    )
    if tests and pytest_declared:
        sources = [_source_record(root, manifest), *(_source_record(root, path) for path in tests)]
        entries.append(
            {
                "kind": "test_suite",
                "runner": "pytest",
                "command": "python -m pytest tests",
                "sources": sources,
                "evidence_kind": "source_derived",
                "execution_verified": False,
            }
        )
        locations.extend(str(item["path"]) for item in sources)
    elif valid_tests:
        sources = [_source_record(root, path) for path in valid_tests]
        entries.append(
            {
                "kind": "test_suite",
                "runner": "unittest",
                "command": 'python -m unittest discover -s tests -p "test_*.py"',
                "sources": sources,
                "evidence_kind": "source_derived",
                "execution_verified": False,
            }
        )
        locations.extend(str(item["path"]) for item in sources)
    return {"entries": entries}, sorted(set(locations))
