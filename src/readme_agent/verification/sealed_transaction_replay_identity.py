"""Stable transaction identity extraction for replay attestation."""

from __future__ import annotations

from typing import Any, Literal

from readme_agent.verification.sealed_transaction_replay_contracts import (
    ReplayAttestationContractV1,
)
from readme_agent.verification.sealed_transaction_replay_json import (
    _resolve_pointer,
    canonical_json_sha256,
)
from readme_agent.verification.sealed_transaction_replay_results import (
    SealedTransactionIdentityV1,
)
from readme_agent.verification.sealed_transaction_replay_vocabulary import (
    _DIGEST_COMPONENTS,
    _HEX_DIGEST,
)


def _extract_identity(
    contract: ReplayAttestationContractV1,
    parsed_by_id: dict[str, Any],
    *,
    label: Literal["first", "replay"],
) -> SealedTransactionIdentityV1:
    component_digests: dict[str, str] = {}
    resolved: list[str] = []
    missing_required: list[str] = []
    malformed: list[str] = []

    for binding in contract.identity_bindings:
        if binding.level == "NOT_APPLICABLE":
            continue
        document = parsed_by_id.get(binding.artifact_id)
        if document is None:
            if binding.level == "REQUIRED":
                missing_required.append(binding.component)
            continue
        found, value = _resolve_pointer(document, binding.json_pointer)
        if not found:
            if binding.level == "REQUIRED":
                missing_required.append(binding.component)
            continue
        if binding.component in _DIGEST_COMPONENTS and not (
            isinstance(value, str) and _HEX_DIGEST.match(value)
        ):
            malformed.append(binding.component)
            continue
        component_digests[binding.component] = canonical_json_sha256(value)
        resolved.append(binding.component)

    identity_binding = next(
        (b for b in contract.identity_bindings if b.component == "repository_identity"), None
    )
    org_repo = None
    source_revision = None
    lifecycle_status = None
    if identity_binding is not None:
        document = parsed_by_id.get(identity_binding.artifact_id)
        if document is not None:
            _, org_repo = _resolve_pointer(document, "/org_repo")
            _, source_revision = _resolve_pointer(document, "/source_revision")
            _, lifecycle_status = _resolve_pointer(document, "/lifecycle_status")

    return SealedTransactionIdentityV1(
        bundle_label=label,
        org_repo=org_repo if isinstance(org_repo, str) else None,
        source_revision=source_revision if isinstance(source_revision, str) else None,
        lifecycle_status=lifecycle_status if isinstance(lifecycle_status, str) else None,
        component_digests=component_digests,
        resolved_components=tuple(sorted(set(resolved))),
        missing_required_components=tuple(sorted(set(missing_required))),
        malformed_components=tuple(sorted(set(malformed))),
        identity_digest=canonical_json_sha256(dict(sorted(component_digests.items()))),
    )
