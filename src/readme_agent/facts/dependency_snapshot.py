"""Build structured dependency facts through ecosystem-specific collectors."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from readme_agent.facts.dependency_snapshot_contracts import (
    DependencyEntryV1,
    DependencySnapshotV1,
)
from readme_agent.facts.dependency_snapshot_python import python_dependency_snapshot
from readme_agent.facts.dependency_snapshot_rust import rust_dependency_snapshot
from readme_agent.facts.schema_v2 import FactRecordV2, FactSourceV2, descriptive_fact_id

_UNBUILT_ECOSYSTEM_REASON = (
    "manifest parsing not yet built for this ecosystem in this pass -- a real, tracked gap, "
    "not a claim of zero dependencies"
)


def build_dependency_snapshot(root: Path, ecosystem: str) -> DependencySnapshotV1:
    """Dispatch one repository snapshot to its supported dependency collector."""

    normalized = ecosystem.strip().casefold()
    if normalized == "python":
        return python_dependency_snapshot(root)
    if normalized == "rust":
        return rust_dependency_snapshot(root)
    return DependencySnapshotV1(
        ecosystem=normalized,
        applicable=False,
        not_applicable_reason=_UNBUILT_ECOSYSTEM_REASON,
    )


def dependency_snapshot_fact_record(root: Path, ecosystem: str) -> FactRecordV2:
    """Wrap a dependency snapshot in a content-addressed product-fact record."""

    snapshot = build_dependency_snapshot(root, ecosystem)
    value = snapshot.model_dump(mode="json")
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
