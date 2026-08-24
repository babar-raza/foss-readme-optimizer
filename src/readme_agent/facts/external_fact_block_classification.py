"""Classify external-fact failures and their retry-relevant dependencies."""

from __future__ import annotations

from readme_agent.facts.external_fact_block_contracts import ExternalFactBlockClassV1

_DIAGNOSTIC_CODE_TO_BLOCK_CLASS: dict[str, ExternalFactBlockClassV1] = {
    "GIT_CLONE_FAILED": "repository_clone_failure",
    "GIT_LFS_OBJECT_MISSING": "git_lfs_object_unavailable",
    "REGISTRY_UNAVAILABLE": "package_registry_unavailable",
    "PACKAGE_VERSION_NOT_FOUND": "package_version_unresolved",
    "TOOLCHAIN_UNAVAILABLE": "toolchain_unavailable",
    "DEPENDENCY_RESOLUTION_FAILED": "dependency_resolution_failure",
    "EXAMPLE_RUNTIME_UNAVAILABLE": "example_runtime_unavailable",
    "PRODUCT_SOURCE_FAILED": "product_source_failure",
    "SOURCE_PACKAGE_MISMATCH": "source_package_mismatch",
    "NETWORK_RATE_LIMITED": "network_rate_limited",
    "LOCAL_CACHE_CORRUPT": "corrupt_local_cache",
    "PLATFORM_VERIFIER_UNSUPPORTED": "unsupported_platform_verifier",
    "EXTERNAL_AUTHENTICATION_UNAVAILABLE": "external_authentication_unavailable",
}

_DETAIL_SUBSTRING_TO_BLOCK_CLASS: tuple[tuple[str, ExternalFactBlockClassV1], ...] = (
    ("git lfs", "git_lfs_object_unavailable"),
    ("clone failed", "repository_clone_failure"),
    ("registry unavailable", "package_registry_unavailable"),
    ("version not found", "package_version_unresolved"),
    ("undeclared or inaccessible package subpath", "source_package_mismatch"),
    ("includes no repository public header", "source_package_mismatch"),
    ("required executable is not available", "toolchain_unavailable"),
    ("no such file or directory", "dependency_resolution_failure"),
    ("dependency resolution", "dependency_resolution_failure"),
    ("indentationerror", "product_source_failure"),
    ("source or exact consumer compilation failed", "product_source_failure"),
    ("example runtime", "example_runtime_unavailable"),
    ("package mismatch", "source_package_mismatch"),
    ("rate limit", "network_rate_limited"),
    ("cache corrupt", "corrupt_local_cache"),
    ("platform", "unsupported_platform_verifier"),
    ("authentication", "external_authentication_unavailable"),
    ("toolchain", "toolchain_unavailable"),
)

_CAUSALLY_RELEVANT_FIELDS_BY_BLOCK_CLASS: dict[ExternalFactBlockClassV1, tuple[str, ...]] = {
    "repository_clone_failure": ("source_revision", "repository_remote_fingerprint"),
    "git_lfs_object_unavailable": ("source_revision", "git_lfs_endpoint_fingerprint"),
    "package_registry_unavailable": (
        "package_registry_snapshot_hash",
        "network_policy_fingerprint",
    ),
    "package_version_unresolved": (
        "package_registry_snapshot_hash",
        "dependency_manifest_hash",
    ),
    "toolchain_unavailable": ("toolchain_fingerprint",),
    "dependency_resolution_failure": (
        "dependency_manifest_hash",
        "package_registry_snapshot_hash",
    ),
    "example_runtime_unavailable": (
        "execution_environment_fingerprint",
        "toolchain_fingerprint",
    ),
    "product_source_failure": ("source_revision", "dependency_manifest_hash"),
    "source_package_mismatch": ("source_revision", "package_registry_snapshot_hash"),
    "network_rate_limited": ("network_policy_fingerprint",),
    "corrupt_local_cache": ("local_cache_fingerprint",),
    "unsupported_platform_verifier": (
        "execution_environment_fingerprint",
        "toolchain_fingerprint",
    ),
    "external_authentication_unavailable": (
        "authentication_context_fingerprint",
        "network_policy_fingerprint",
    ),
    "unknown": (
        "source_revision",
        "repository_remote_fingerprint",
        "git_lfs_endpoint_fingerprint",
        "package_registry_snapshot_hash",
        "dependency_manifest_hash",
        "toolchain_fingerprint",
        "execution_environment_fingerprint",
        "network_policy_fingerprint",
        "local_cache_fingerprint",
        "authentication_context_fingerprint",
    ),
}


def classify_external_fact_block_class(
    *, diagnostic_code: str | None, detail: str
) -> ExternalFactBlockClassV1:
    """Prefer a typed diagnostic and otherwise use a bounded ordered detail mapping."""

    if diagnostic_code is not None and diagnostic_code in _DIAGNOSTIC_CODE_TO_BLOCK_CLASS:
        return _DIAGNOSTIC_CODE_TO_BLOCK_CLASS[diagnostic_code]
    folded = detail.casefold()
    for substring, block_class in _DETAIL_SUBSTRING_TO_BLOCK_CLASS:
        if substring in folded:
            return block_class
    return "unknown"


def causally_relevant_fingerprint_fields(
    block_class: ExternalFactBlockClassV1,
) -> tuple[str, ...]:
    """Return the semantic dependencies that can change one block's outcome."""

    return _CAUSALLY_RELEVANT_FIELDS_BY_BLOCK_CLASS[block_class]


__all__ = ["causally_relevant_fingerprint_fields", "classify_external_fact_block_class"]
