"""Collect Rust dependency declarations from Cargo manifests."""

from __future__ import annotations

import tomllib
from pathlib import Path

from readme_agent.facts.dependency_snapshot_contracts import (
    DependencyEntryV1,
    DependencyRole,
    DependencySnapshotV1,
)


def rust_dependency_snapshot(root: Path) -> DependencySnapshotV1:
    """Read Cargo runtime, build, and development dependency tables."""

    manifest = root / "Cargo.toml"
    if not manifest.is_file():
        return DependencySnapshotV1(
            ecosystem="rust",
            applicable=False,
            not_applicable_reason="no Cargo.toml at the repository root",
        )
    parse_errors: list[str] = []
    buckets: dict[str, list[DependencyEntryV1]] = {"required": [], "development": []}
    table_to_bucket: dict[str, tuple[str, bool, DependencyRole]] = {
        "dependencies": ("required", False, "runtime"),
        "build-dependencies": ("development", True, "build"),
        "dev-dependencies": ("development", True, "dev"),
    }
    try:
        data = tomllib.loads(manifest.read_text(encoding="utf-8-sig", errors="replace"))
        for table_name, (bucket, dev_only, role) in table_to_bucket.items():
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


__all__ = ["rust_dependency_snapshot"]
