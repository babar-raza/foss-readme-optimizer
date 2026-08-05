"""Promote isolated Python distribution metadata into compatibility facts."""

from pathlib import Path

from readme_agent.facts.migration import SURFACE_DEPENDENCIES
from readme_agent.facts.python_distribution_metadata import (
    verify_python_distribution_metadata,
)
from readme_agent.facts.root_role_schema import PackageRootRoleInventoryV1
from readme_agent.facts.schema_v2 import (
    FactRecordV2,
    FactSourceV2,
    descriptive_fact_id,
)
from readme_agent.repository_snapshot import (
    RepositorySnapshotV1,
    local_fact_verification_allowed,
)


def _compatibility_fact(
    qualifier: str,
    value: object,
    *,
    source: FactSourceV2,
    verified: bool,
) -> FactRecordV2:
    return FactRecordV2(
        fact_id=descriptive_fact_id("product.compatibility", qualifier),
        field="product.compatibility",
        value=value,
        source=source,
        verification_state="verified" if verified else "blocked",
        authoritative_owner="repository-owner",
        confidence=1.0 if verified else 0.0,
        affected_surfaces=SURFACE_DEPENDENCIES["product.compatibility"],
    )


def python_setup_compatibility_candidate(
    root_roles: PackageRootRoleInventoryV1,
    snapshot: RepositorySnapshotV1 | None,
    observed_at: str | None,
) -> FactRecordV2 | None:
    """Promote setup.py compatibility only through isolated generated metadata."""

    selected = next(
        (
            root
            for root in root_roles.roots
            if root.role == "product"
            and root.manifest_path == root_roles.selected_product_manifest_path
            and root.ecosystem == "python"
            and Path(root.manifest_path).name == "setup.py"
        ),
        None,
    )
    if selected is None:
        return None
    source_revision = (
        snapshot.source_revision if snapshot is not None else root_roles.source_revision
    )
    source = FactSourceV2(
        source_type="mechanical_test",
        location=f"repository://{selected.manifest_path}#isolated-generated-PKG-INFO",
        source_revision=source_revision,
        retrieved_at=observed_at,
    )
    if snapshot is None:
        return _compatibility_fact(
            "blocked-isolated-python-metadata",
            {"reason": "immutable_snapshot_required", "manifest_path": selected.manifest_path},
            source=source,
            verified=False,
        )
    blocked_reason = None
    if root_roles.source_revision not in {None, snapshot.source_revision}:
        blocked_reason = "root_role_source_revision_mismatch"
    elif not local_fact_verification_allowed():
        blocked_reason = "isolated_local_fact_verification_not_enabled"
    if blocked_reason:
        return _compatibility_fact(
            "blocked-isolated-python-metadata",
            {"reason": blocked_reason, "manifest_path": selected.manifest_path},
            source=source,
            verified=False,
        )
    try:
        proof = verify_python_distribution_metadata(snapshot, selected)
    except Exception as exc:
        return _compatibility_fact(
            "blocked-isolated-python-metadata",
            {
                "reason": "isolated_metadata_verification_failed",
                "error_type": type(exc).__name__,
                "manifest_path": selected.manifest_path,
            },
            source=source,
            verified=False,
        )
    proof_summary = {
        "truth_eligible": proof.truth_eligible,
        "snapshot_inventory_sha256": proof.snapshot_inventory_sha256,
        "manifest_sha256": proof.manifest_sha256,
        "driver_sha256": proof.driver_sha256,
        "input_sha256": proof.execution.input_sha256,
        "container_image": proof.execution.policy.immutable_image,
        "pkg_info_sha256": proof.metadata.pkg_info_sha256 if proof.metadata else None,
        "cleanup_complete": proof.execution.cleanup.complete,
    }
    if not proof.truth_eligible or proof.metadata is None:
        return _compatibility_fact(
            "blocked-isolated-python-metadata",
            {
                "reason": proof.failure_reason,
                "manifest_path": selected.manifest_path,
                "metadata_proof": proof_summary,
            },
            source=source,
            verified=False,
        )
    source = source.model_copy(
        update={
            "location": (
                f"repository://{selected.manifest_path}#isolated-generated-PKG-INFO:"
                f"{proof.metadata.pkg_info_sha256}"
            )
        }
    )
    return _compatibility_fact(
        "isolated-generated-python-metadata",
        [
            {
                key: value
                for key, value in {
                    "ecosystem": "python",
                    "runtime_label": "Python",
                    "minimum_runtime": proof.metadata.requires_python,
                    "supported_runtime_versions": (
                        proof.metadata.python_classifier_versions or None
                    ),
                    "compatibility_kind": "minimum_runtime",
                    "manifest_path": selected.manifest_path,
                    "root_role": "product",
                    "metadata_proof": proof_summary,
                }.items()
                if value is not None
            }
        ],
        source=source,
        verified=True,
    )
