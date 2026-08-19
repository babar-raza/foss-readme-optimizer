"""Build a real, structured `DependencySnapshotV1` from a repository's own
declared package manifest -- Gate R6c of the 2026-08-19 knowledge-to-output
pipeline course-correction review.

The vendored aspose.org check battery (`readme_refresh_checks.py`) has
carried `dependency_snapshot`-parameterized checks since MT041 (the
incident that motivated them: a generated cells/rust README claimed "no
external runtime... is needed" while that product's own real Cargo.toml
declares 7 runtime crates -- a same-document contradiction a real,
structured manifest read would have caught). Those checks were universally
skipped (`checks_skipped`, never faked) because nothing in this repo ever
built the `DependencySnapshot` they expect -- confirmed by grep: the
existing `PythonDependencyBundle`/`declared_python_runtime_dependencies`/
`declared_python_build_dependencies` functions (`python_dependency_
acquisition.py`) that could have supplied it were themselves unused
anywhere in `src/` or `tests/`, real and correct (verified directly against
this portfolio's actual `pyproject.toml` files) but never wired to a
consumer.

Scope, stated honestly rather than faked: real manifest parsing is wired up
here for `python` (reusing the existing proven PEP 621/517 readers, adding
`project.optional-dependencies` extraction) and `rust` (a new, equally
small `Cargo.toml` `[dependencies]`/`[dev-dependencies]`/`[build-
dependencies]` reader -- the exact manifest shape the MT041 incident was
about). Every other registry ecosystem (java, net, cpp, go, typescript)
returns `applicable=False` with an explicit `not_applicable_reason` --
never a silently-empty snapshot that would look identical to "this product
genuinely has zero dependencies." `native_system`/`proprietary_runtime`
buckets (native OS/toolchain requirements, non-open-source runtime
dependencies) are always empty here for every ecosystem: detecting those
needs real per-ecosystem heuristics beyond manifest parsing that this pass
does not build -- an explicit, tracked gap, not a fabricated zero.
"""

from __future__ import annotations

import hashlib
import json
import tomllib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from readme_agent.facts.python_dependency_acquisition import (
    declared_python_build_dependencies,
    declared_python_runtime_dependencies,
)
from readme_agent.facts.schema_v2 import FactRecordV2, FactSourceV2, descriptive_fact_id

DependencyRole = Literal["runtime", "build", "dev"]


class DependencyEntryV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    ecosystem: str
    version_constraint: str | None
    category: str
    dev_only: bool
    role: DependencyRole


class DependencySnapshotV1(BaseModel):
    """Matches the shape `readme_refresh_checks.py`'s `dependency_snapshot`-
    parameterized checks already expect (`e["name"]`, `e["ecosystem"]`,
    `e["version_constraint"]`, `e["category"]`, `e["dev_only"]`, `e["role"]`
    per entry; `required`/`optional`/`native_system`/`proprietary_runtime`/
    `development` buckets; `applicable`/`not_applicable_reason`/
    `parse_errors`/`source_manifest_path` at the top level)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    ecosystem: str
    applicable: bool
    not_applicable_reason: str | None = None
    source_manifest_path: str | None = None
    parse_errors: tuple[str, ...] = ()
    required: tuple[DependencyEntryV1, ...] = ()
    optional: tuple[DependencyEntryV1, ...] = ()
    native_system: tuple[DependencyEntryV1, ...] = ()
    proprietary_runtime: tuple[DependencyEntryV1, ...] = ()
    development: tuple[DependencyEntryV1, ...] = ()


def _split_name_and_constraint(requirement: str) -> tuple[str, str | None]:
    """PEP 508 requirement string -> (distribution name, raw constraint tail).
    Deliberately minimal (name-only extraction is what every consumer in
    the vendored checks actually keys on): stops at the first character
    that cannot appear in a bare distribution name."""

    for index, char in enumerate(requirement):
        if not (char.isalnum() or char in "-_."):
            return requirement[:index].strip(), requirement[index:].strip() or None
    return requirement.strip(), None


def _python_snapshot(root: Path) -> DependencySnapshotV1:
    manifest = root / "pyproject.toml"
    if not manifest.is_file():
        return DependencySnapshotV1(
            ecosystem="python",
            applicable=False,
            not_applicable_reason="no pyproject.toml at the repository root",
        )
    parse_errors: list[str] = []
    required: list[DependencyEntryV1] = []
    optional: list[DependencyEntryV1] = []
    development: list[DependencyEntryV1] = []
    try:
        for requirement in declared_python_runtime_dependencies(root, "pyproject.toml"):
            name, constraint = _split_name_and_constraint(requirement)
            required.append(
                DependencyEntryV1(
                    name=name,
                    ecosystem="python",
                    version_constraint=constraint,
                    category="package",
                    dev_only=False,
                    role="runtime",
                )
            )
    except ValueError as exc:
        parse_errors.append(f"project.dependencies: {exc}")
    try:
        for requirement in declared_python_build_dependencies(root, "pyproject.toml"):
            name, constraint = _split_name_and_constraint(requirement)
            development.append(
                DependencyEntryV1(
                    name=name,
                    ecosystem="python",
                    version_constraint=constraint,
                    category="package",
                    dev_only=True,
                    role="build",
                )
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
                name, constraint = _split_name_and_constraint(requirement.strip())
                if name:
                    optional.append(
                        DependencyEntryV1(
                            name=name,
                            ecosystem="python",
                            version_constraint=constraint,
                            category="package",
                            dev_only=False,
                            role="runtime",
                        )
                    )
    except (tomllib.TOMLDecodeError, ValueError, OSError) as exc:
        parse_errors.append(f"project.optional-dependencies: {exc}")

    return DependencySnapshotV1(
        ecosystem="python",
        applicable=True,
        source_manifest_path="pyproject.toml",
        parse_errors=tuple(parse_errors),
        required=tuple(sorted(required, key=lambda entry: entry.name)),
        optional=tuple(
            sorted(
                {(e.name, e.version_constraint): e for e in optional}.values(),
                key=lambda entry: entry.name,
            )
        ),
        development=tuple(sorted(development, key=lambda entry: entry.name)),
    )


def _rust_snapshot(root: Path) -> DependencySnapshotV1:
    manifest = root / "Cargo.toml"
    if not manifest.is_file():
        return DependencySnapshotV1(
            ecosystem="rust",
            applicable=False,
            not_applicable_reason="no Cargo.toml at the repository root",
        )
    parse_errors: list[str] = []
    buckets: dict[str, list[DependencyEntryV1]] = {"required": [], "development": []}
    _TABLE_TO_BUCKET: dict[str, tuple[str, bool, DependencyRole]] = {
        "dependencies": ("required", False, "runtime"),
        "build-dependencies": ("development", True, "build"),
        "dev-dependencies": ("development", True, "dev"),
    }
    try:
        data = tomllib.loads(manifest.read_text(encoding="utf-8-sig", errors="replace"))
        for table_name, (bucket, dev_only, role) in _TABLE_TO_BUCKET.items():
            table = data.get(table_name, {})
            if not isinstance(table, dict):
                raise ValueError(f"[{table_name}] must be a table")
            for name, spec in table.items():
                if isinstance(spec, str):
                    constraint: str | None = spec.strip() or None
                elif isinstance(spec, dict):
                    version = spec.get("version")
                    constraint = str(version).strip() if isinstance(version, str) else None
                else:
                    raise ValueError(
                        f"[{table_name}].{name} has an unrecognized specification shape"
                    )
                buckets[bucket].append(
                    DependencyEntryV1(
                        name=str(name),
                        ecosystem="rust",
                        version_constraint=constraint,
                        category="crate",
                        dev_only=dev_only,
                        role=role,
                    )
                )
    except (tomllib.TOMLDecodeError, ValueError, OSError) as exc:
        parse_errors.append(str(exc))

    return DependencySnapshotV1(
        ecosystem="rust",
        applicable=True,
        source_manifest_path="Cargo.toml",
        parse_errors=tuple(parse_errors),
        required=tuple(sorted(buckets["required"], key=lambda entry: entry.name)),
        development=tuple(sorted(buckets["development"], key=lambda entry: entry.name)),
    )


_UNBUILT_ECOSYSTEM_REASON = (
    "manifest parsing not yet built for this ecosystem in this pass -- a real, tracked "
    "gap (see dependency_snapshot.py's module docstring), not a claim of zero dependencies"
)


def build_dependency_snapshot(root: Path, ecosystem: str) -> DependencySnapshotV1:
    normalized = ecosystem.strip().casefold()
    if normalized == "python":
        return _python_snapshot(root)
    if normalized == "rust":
        return _rust_snapshot(root)
    return DependencySnapshotV1(
        ecosystem=normalized,
        applicable=False,
        not_applicable_reason=_UNBUILT_ECOSYSTEM_REASON,
    )


def dependency_snapshot_fact_record(root: Path, ecosystem: str) -> FactRecordV2:
    snapshot = build_dependency_snapshot(root, ecosystem)
    value = snapshot.model_dump(mode="json")
    # Content-derived, never wall-clock: identical manifest bytes always
    # produce the same source_revision, so this fact never breaks
    # ProductFactsV2.canonical_hash() no-op-rerun stability (Gate R1).
    content_revision = (
        "content-sha256:"
        + hashlib.sha256(
            json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
    )
    return FactRecordV2(
        fact_id=descriptive_fact_id("aspose.dependency_snapshot", ecosystem),
        field="aspose.dependency_snapshot",
        value=value,
        source=FactSourceV2(
            source_type="mechanical_repository",
            location=snapshot.source_manifest_path or f"repository:{ecosystem}",
            source_revision=content_revision,
        ),
        verification_state=(
            "verified" if snapshot.applicable and not snapshot.parse_errors else "unverified"
        ),
        authoritative_owner="repository-owner",
        confidence=1.0 if snapshot.applicable and not snapshot.parse_errors else 0.5,
        affected_surfaces=["readme.dependencies"],
    )


__all__ = [
    "DependencyEntryV1",
    "DependencySnapshotV1",
    "build_dependency_snapshot",
    "dependency_snapshot_fact_record",
]
