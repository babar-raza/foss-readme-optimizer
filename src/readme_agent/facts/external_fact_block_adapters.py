"""Adapt current ProductFactsV2 failures to the external-block resolver seam."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from readme_agent.facts.acceptance_contract import FactAcceptanceContractV1
from readme_agent.facts.external_fact_block_contracts import (
    AvailableFactEvidenceCatalogV1,
    ExternalDependencyFingerprintV1,
    ExternalFactBlockResolutionV1,
    ExternalFactBlockV1,
    FactClaimKindV1,
)
from readme_agent.facts.external_fact_block_resolution import resolve_external_fact_block
from readme_agent.facts.external_fact_evidence_adapters import (
    build_available_fact_evidence_catalog,
    build_external_dependency_fingerprint,
)
from readme_agent.facts.schema_v2 import FactRecordV2, ProductFactsV2
from readme_agent.repository_snapshot import RepositorySnapshotV1

ExternalFactRecoveryActionV1 = Literal[
    "RESELECT_REPOSITORY_EXAMPLE",
    "RETRY_DECLARED_DEPENDENCY_VERIFICATION",
    "PROVISION_DECLARED_TOOLCHAIN",
    "RETRY_EXTERNAL_READ",
    "ADD_ECOSYSTEM_VERIFIER",
    "WAIT_FOR_SOURCE_REVISION",
    "TRIAGE_UNKNOWN_DIAGNOSTIC",
]


class ExternalFactResolutionDecisionV1(BaseModel):
    """One current fact block, its evidence, and the narrowest permitted recovery."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    fact_id: str
    block: ExternalFactBlockV1
    evidence_catalog: AvailableFactEvidenceCatalogV1
    dependency_fingerprint: ExternalDependencyFingerprintV1
    resolution: ExternalFactBlockResolutionV1
    recovery_action: ExternalFactRecoveryActionV1
    blocked_category: Literal["agent_fixable", "infra_external"]


_CLAIM_KIND_BY_FIELD: dict[str, FactClaimKindV1] = {
    "installation.coordinates": "identity_coordinates",
    "installation.verified_acquisition": "runtime_behavior",
    "example.minimal": "example_execution",
}
EXTERNAL_FACT_FIELDS = frozenset(_CLAIM_KIND_BY_FIELD)


def _fact_detail(fact: FactRecordV2) -> str:
    if not isinstance(fact.value, dict):
        return f"{fact.field} has verification_state={fact.verification_state}"
    return str(
        fact.value.get("verification_detail")
        or fact.value.get("detail")
        or f"{fact.field} has verification_state={fact.verification_state}"
    )


def _diagnostic_code(detail: str) -> str | None:
    folded = detail.casefold()
    if "undeclared or inaccessible package subpath" in folded:
        return "SOURCE_PACKAGE_MISMATCH"
    if "includes no repository public header" in folded:
        return "SOURCE_PACKAGE_MISMATCH"
    if "required executable is not available" in folded:
        return "TOOLCHAIN_UNAVAILABLE"
    if "no such file or directory" in folded or "dependency resolution" in folded:
        return "DEPENDENCY_RESOLUTION_FAILED"
    if "indentationerror" in folded or "source or exact consumer compilation failed" in folded:
        return "PRODUCT_SOURCE_FAILED"
    if "registry unavailable" in folded:
        return "REGISTRY_UNAVAILABLE"
    if "version not found" in folded or "not found (404)" in folded:
        return "PACKAGE_VERSION_NOT_FOUND"
    return None


def _package_identity(fact: FactRecordV2) -> str | None:
    if not isinstance(fact.value, dict):
        return None
    coordinate = fact.value.get("coordinate")
    if isinstance(coordinate, dict):
        name = str(coordinate.get("name") or "").strip()
        version = str(coordinate.get("version") or "").strip()
        if name:
            return f"{name}=={version}" if version else name
    return None


def external_fact_block_from_record(
    fact: FactRecordV2,
    *,
    org_repo: str,
    source_revision: str,
) -> ExternalFactBlockV1:
    """Translate only the current supported fact surfaces; never infer a new claim kind."""

    claim_kind = _CLAIM_KIND_BY_FIELD.get(fact.field)
    if claim_kind is None:
        raise ValueError(f"fact surface {fact.field!r} has no external-block claim mapping")
    detail = _fact_detail(fact)
    return ExternalFactBlockV1(
        block_id=f"{org_repo}@{source_revision}:{fact.fact_id}",
        fact_surface=fact.field,
        claim_kind=claim_kind,
        diagnostic_code=_diagnostic_code(detail),
        detail=detail,
        org_repo=org_repo,
        source_revision=source_revision,
        package_identity=_package_identity(fact),
    )


def _recovery_action(
    resolution: ExternalFactBlockResolutionV1,
) -> tuple[ExternalFactRecoveryActionV1, Literal["agent_fixable", "infra_external"]]:
    block_class = resolution.block_class
    if block_class == "source_package_mismatch":
        return "RESELECT_REPOSITORY_EXAMPLE", "agent_fixable"
    if block_class == "dependency_resolution_failure":
        return "RETRY_DECLARED_DEPENDENCY_VERIFICATION", "agent_fixable"
    if block_class == "toolchain_unavailable":
        return "PROVISION_DECLARED_TOOLCHAIN", "agent_fixable"
    if block_class in {
        "package_registry_unavailable",
        "network_rate_limited",
        "external_authentication_unavailable",
        "repository_clone_failure",
        "git_lfs_object_unavailable",
    }:
        return "RETRY_EXTERNAL_READ", "infra_external"
    if block_class == "product_source_failure":
        return "WAIT_FOR_SOURCE_REVISION", "infra_external"
    if block_class == "unsupported_platform_verifier":
        return "ADD_ECOSYSTEM_VERIFIER", "agent_fixable"
    return "TRIAGE_UNKNOWN_DIAGNOSTIC", "agent_fixable"


def resolve_fact_record_block(
    fact: FactRecordV2,
    *,
    facts: ProductFactsV2,
    snapshot: RepositorySnapshotV1,
    contract: FactAcceptanceContractV1,
    previous_resolution: ExternalFactBlockResolutionV1 | None = None,
) -> ExternalFactResolutionDecisionV1:
    """Resolve one current blocked fact and choose its smallest recovery action."""

    block = external_fact_block_from_record(
        fact,
        org_repo=facts.org_repo,
        source_revision=snapshot.source_revision,
    )
    if fact.field == "installation.verified_acquisition":
        try:
            example = facts.selected_fact("example.minimal")
        except KeyError:
            example = None
        if (
            example is not None
            and example.verification_state not in {"verified", "policy_approved"}
            and example.source.source_revision == snapshot.source_revision
        ):
            dependent_detail = _fact_detail(example)
            block = block.model_copy(
                update={
                    "diagnostic_code": _diagnostic_code(dependent_detail),
                    "detail": dependent_detail,
                }
            )
    catalog = build_available_fact_evidence_catalog(facts, block=block)
    dependencies = build_external_dependency_fingerprint(
        fact,
        snapshot=snapshot,
        contract=contract,
    )
    resolution = resolve_external_fact_block(
        block=block,
        available_evidence=catalog,
        current_dependencies=dependencies,
        previous_resolution=previous_resolution,
    )
    action, category = _recovery_action(resolution)
    return ExternalFactResolutionDecisionV1(
        fact_id=fact.fact_id,
        block=block,
        evidence_catalog=catalog,
        dependency_fingerprint=dependencies,
        resolution=resolution,
        recovery_action=action,
        blocked_category=category,
    )


def resolve_selected_external_fact_blocks(
    facts: ProductFactsV2,
    *,
    snapshot: RepositorySnapshotV1,
    contract: FactAcceptanceContractV1,
) -> tuple[ExternalFactResolutionDecisionV1, ...]:
    """Resolve selected supported blocks without touching unrelated fact surfaces."""

    decisions: list[ExternalFactResolutionDecisionV1] = []
    for field in sorted(EXTERNAL_FACT_FIELDS):
        try:
            fact = facts.selected_fact(field)
        except KeyError:
            continue
        if fact.verification_state != "blocked":
            continue
        decisions.append(
            resolve_fact_record_block(
                fact,
                facts=facts,
                snapshot=snapshot,
                contract=contract,
            )
        )
    return tuple(decisions)


__all__ = [
    "EXTERNAL_FACT_FIELDS",
    "ExternalFactRecoveryActionV1",
    "ExternalFactResolutionDecisionV1",
    "build_available_fact_evidence_catalog",
    "build_external_dependency_fingerprint",
    "external_fact_block_from_record",
    "resolve_fact_record_block",
    "resolve_selected_external_fact_blocks",
]
