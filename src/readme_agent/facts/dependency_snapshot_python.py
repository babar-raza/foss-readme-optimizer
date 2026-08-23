"""Collect Python dependency declarations without executing repository code."""

from __future__ import annotations

import ast
import tomllib
from pathlib import Path

from readme_agent.facts.dependency_snapshot_contracts import (
    DependencyEntryV1,
    DependencyRole,
    DependencySnapshotV1,
)
from readme_agent.facts.python_dependency_acquisition import (
    declared_python_build_dependencies,
    declared_python_runtime_dependencies,
)


def _split_name_and_constraint(requirement: str) -> tuple[str, str | None]:
    for index, char in enumerate(requirement):
        if not (char.isalnum() or char in "-_."):
            return requirement[:index].strip(), requirement[index:].strip() or None
    return requirement.strip(), None


def _dependency_entry(
    requirement: str, *, dev_only: bool, role: DependencyRole
) -> DependencyEntryV1:
    name, constraint = _split_name_and_constraint(requirement)
    return DependencyEntryV1(
        name=name,
        ecosystem="python",
        version_constraint=constraint,
        category="package",
        dev_only=dev_only,
        role=role,
    )


def _literal_requirement_list(node: ast.AST, field: str) -> tuple[list[str], list[str]]:
    try:
        value = ast.literal_eval(node)
    except (TypeError, ValueError):
        return [], [f"{field}: value is not a literal dependency declaration"]
    if not isinstance(value, (list, tuple)) or not all(isinstance(item, str) for item in value):
        return [], [f"{field}: expected a literal string list"]
    return [item.strip() for item in value if item.strip()], []


def _setup_py_snapshot(manifest: Path) -> DependencySnapshotV1:
    try:
        tree = ast.parse(manifest.read_text(encoding="utf-8-sig"))
    except (OSError, SyntaxError, UnicodeDecodeError) as exc:
        return DependencySnapshotV1(
            ecosystem="python",
            applicable=True,
            source_manifest_path="setup.py",
            parse_errors=(f"setup.py: {exc}",),
        )
    setup_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and (
            (isinstance(node.func, ast.Name) and node.func.id == "setup")
            or (isinstance(node.func, ast.Attribute) and node.func.attr == "setup")
        )
    ]
    if len(setup_calls) != 1:
        return DependencySnapshotV1(
            ecosystem="python",
            applicable=True,
            source_manifest_path="setup.py",
            parse_errors=(f"setup.py: expected one setup() call, found {len(setup_calls)}",),
        )
    keywords = {item.arg: item.value for item in setup_calls[0].keywords if item.arg is not None}
    errors: list[str] = []
    required_values, parse_errors = _literal_requirement_list(
        keywords.get("install_requires", ast.List(elts=[], ctx=ast.Load())),
        "install_requires",
    )
    errors.extend(parse_errors)
    test_values, parse_errors = _literal_requirement_list(
        keywords.get("tests_require", ast.List(elts=[], ctx=ast.Load())),
        "tests_require",
    )
    errors.extend(parse_errors)
    optional: list[DependencyEntryV1] = []
    development = [_dependency_entry(item, dev_only=True, role="dev") for item in test_values]
    extras_node = keywords.get("extras_require", ast.Dict(keys=[], values=[]))
    try:
        extras = ast.literal_eval(extras_node)
    except (TypeError, ValueError):
        extras = None
        errors.append("extras_require: value is not a literal dependency declaration")
    if isinstance(extras, dict):
        for group, requirements in extras.items():
            if (
                not isinstance(group, str)
                or not isinstance(requirements, (list, tuple))
                or not all(isinstance(item, str) for item in requirements)
            ):
                errors.append("extras_require: expected string groups with literal string lists")
                continue
            target = development if group.casefold() in {"dev", "test", "tests"} else optional
            target.extend(
                _dependency_entry(item.strip(), dev_only=target is development, role="dev")
                for item in requirements
                if item.strip()
            )
    elif extras is not None:
        errors.append("extras_require: expected a literal mapping")
    required = [_dependency_entry(item, dev_only=False, role="runtime") for item in required_values]
    return DependencySnapshotV1(
        ecosystem="python",
        applicable=True,
        source_manifest_path="setup.py",
        parse_errors=tuple(errors),
        required=tuple(sorted(required, key=lambda entry: entry.name)),
        optional=tuple(sorted(optional, key=lambda entry: entry.name)),
        development=tuple(sorted(development, key=lambda entry: entry.name)),
    )


def python_dependency_snapshot(root: Path) -> DependencySnapshotV1:
    """Read PEP 621/517 or literal setup.py dependency declarations."""

    manifest = root / "pyproject.toml"
    if not manifest.is_file():
        setup_manifest = root / "setup.py"
        if setup_manifest.is_file():
            return _setup_py_snapshot(setup_manifest)
        return DependencySnapshotV1(
            ecosystem="python",
            applicable=False,
            not_applicable_reason="no pyproject.toml or setup.py at the repository root",
        )
    parse_errors: list[str] = []
    required: list[DependencyEntryV1] = []
    optional: list[DependencyEntryV1] = []
    development: list[DependencyEntryV1] = []
    try:
        required.extend(
            _dependency_entry(requirement, dev_only=False, role="runtime")
            for requirement in declared_python_runtime_dependencies(root, "pyproject.toml")
        )
    except ValueError as exc:
        parse_errors.append(f"project.dependencies: {exc}")
    try:
        development.extend(
            _dependency_entry(requirement, dev_only=True, role="build")
            for requirement in declared_python_build_dependencies(root, "pyproject.toml")
        )
    except ValueError as exc:
        parse_errors.append(f"build-system.requires: {exc}")
    try:
        data = tomllib.loads(manifest.read_text(encoding="utf-8-sig", errors="replace"))
        extras = data.get("project", {}).get("optional-dependencies", {})
        if not isinstance(extras, dict):
            raise ValueError("project.optional-dependencies must be a table of extras")
        for group_requirements in extras.values():
            if not isinstance(group_requirements, list):
                raise ValueError("each optional-dependencies group must be a literal string list")
            for requirement in group_requirements:
                if not isinstance(requirement, str):
                    raise ValueError("each optional-dependencies entry must be a literal string")
                entry = _dependency_entry(requirement.strip(), dev_only=False, role="runtime")
                if entry.name:
                    optional.append(entry)
    except (tomllib.TOMLDecodeError, ValueError, OSError) as exc:
        parse_errors.append(f"project.optional-dependencies: {exc}")
    deduplicated_optional = {(entry.name, entry.version_constraint): entry for entry in optional}
    return DependencySnapshotV1(
        ecosystem="python",
        applicable=True,
        source_manifest_path="pyproject.toml",
        parse_errors=tuple(parse_errors),
        required=tuple(sorted(required, key=lambda entry: entry.name)),
        optional=tuple(sorted(deduplicated_optional.values(), key=lambda entry: entry.name)),
        development=tuple(sorted(development, key=lambda entry: entry.name)),
    )


__all__ = ["python_dependency_snapshot"]
