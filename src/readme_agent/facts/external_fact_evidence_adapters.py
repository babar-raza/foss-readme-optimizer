"""Project accepted facts and immutable inputs into external-block evidence contracts."""

from __future__ import annotations

import hashlib
import json

from readme_agent.facts.acceptance_contract import FactAcceptanceContractV1
from readme_agent.facts.external_fact_block_contracts import (
    AvailableFactEvidenceCatalogV1,
    AvailableFactEvidenceV1,
    ExternalDependencyFingerprintV1,
    ExternalFactBlockV1,
    FactClaimKindV1,
    FactEvidenceKindV1,
)
from readme_agent.facts.schema_v2 import FactRecordV2, ProductFactsV2
from readme_agent.repository_snapshot import RepositorySnapshotV1


def _canonical_sha256(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _coordinate_identities(fact: FactRecordV2) -> tuple[str | None, ...]:
    values = fact.value if isinstance(fact.value, list) else [fact.value]
    identities: list[str] = []
    for value in values:
        if not isinstance(value, dict):
            continue
        name = str(value.get("name") or "").strip()
        version = str(value.get("version") or "").strip()
        if name:
            identities.append(f"{name}=={version}" if version else name)
    return tuple(dict.fromkeys(identities)) or (None,)


def _evidence_kind(fact: FactRecordV2) -> FactEvidenceKindV1 | None:
    if fact.field == "installation.coordinates" and fact.source.source_type in {
        "mechanical_manifest",
        "mechanical_repository",
    }:
        return "current_source_or_manifest"
    if fact.field == "api.public_surface":
        return (
            "static_public_api_or_source"
            if fact.source.source_type == "mechanical_repository"
            else "verified_imported_knowledge"
        )
    return None


def build_available_fact_evidence_catalog(
    facts: ProductFactsV2,
    *,
    block: ExternalFactBlockV1,
) -> AvailableFactEvidenceCatalogV1:
    """Build a bounded catalog from already-accepted same-revision fact records."""

    items: list[AvailableFactEvidenceV1] = []
    for fact in facts.facts:
        if fact.verification_state not in {"verified", "policy_approved"}:
            continue
        kind = _evidence_kind(fact)
        if kind is None:
            continue
        competent: tuple[FactClaimKindV1, ...]
        if kind == "current_source_or_manifest":
            competent = ("identity_coordinates", "static_existence")
        else:
            competent = ("static_existence", "example_execution", "runtime_behavior")
        identities = (
            _coordinate_identities(fact) if kind == "current_source_or_manifest" else (None,)
        )
        for index, package_identity in enumerate(identities):
            suffix = f":{index}" if len(identities) > 1 else ""
            items.append(
                AvailableFactEvidenceV1(
                    evidence_id=f"{fact.fact_id}{suffix}",
                    evidence_kind=kind,
                    competent_claim_kinds=competent,
                    org_repo=facts.org_repo,
                    source_revision=(
                        fact.source.source_revision
                        if kind != "verified_imported_knowledge"
                        else block.source_revision
                    ),
                    package_identity=package_identity,
                    detail=f"{fact.field} from {fact.source.location}",
                )
            )
    return AvailableFactEvidenceCatalogV1(
        org_repo=facts.org_repo,
        source_revision=block.source_revision,
        items=tuple(sorted(items, key=lambda item: item.evidence_id)),
    )


def build_external_dependency_fingerprint(
    fact: FactRecordV2,
    *,
    snapshot: RepositorySnapshotV1,
    contract: FactAcceptanceContractV1,
) -> ExternalDependencyFingerprintV1:
    """Project existing source, receipt, contract, and verifier identities."""

    value = fact.value if isinstance(fact.value, dict) else {}
    registry = value.get("registry_receipt")
    registry = registry if isinstance(registry, dict) else {}
    pins = value.get("acquisition_dependency_pins")
    pins = pins if isinstance(pins, list) else []
    component_hashes = contract.component_hashes
    return ExternalDependencyFingerprintV1(
        source_revision=snapshot.source_revision,
        repository_remote_fingerprint=snapshot.provenance.git_tree_sha256,
        package_registry_snapshot_hash=(
            str(registry.get("response_sha256")) if registry.get("response_sha256") else None
        ),
        dependency_manifest_hash=_canonical_sha256(
            {
                "package_roots": [root.model_dump(mode="json") for root in snapshot.package_roots],
                "dependency_evidence": component_hashes.get("dependency_evidence"),
            }
        ),
        toolchain_fingerprint=_canonical_sha256(pins) if pins else None,
        execution_environment_fingerprint=_canonical_sha256(
            {
                "pins": pins,
                "drafting_and_example_selection": component_hashes.get(
                    "drafting_and_example_selection"
                ),
            }
        ),
        network_policy_fingerprint=component_hashes.get("acquisition_truth"),
        imported_knowledge_revision=component_hashes.get("imported_knowledge"),
    )


__all__ = [
    "build_available_fact_evidence_catalog",
    "build_external_dependency_fingerprint",
]
