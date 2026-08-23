"""Result models for sealed transaction replay attestation."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from readme_agent.llm.call_schema import LlmAccountingSummaryV1
from readme_agent.verification.sealed_transaction_replay_contracts import _Frozen
from readme_agent.verification.sealed_transaction_replay_vocabulary import (
    ATTESTOR_IDENTITY,
    ProductEffectV1,
    ProviderCallAxisV1,
    ReplayStageV1,
)


class SealedTransactionIdentityV1(_Frozen):
    schema_version: Literal[1] = 1
    bundle_label: Literal["first", "replay"]
    org_repo: str | None = None
    source_revision: str | None = None
    lifecycle_status: str | None = None
    component_digests: dict[str, str] = {}
    resolved_components: tuple[str, ...] = ()
    missing_required_components: tuple[str, ...] = ()
    malformed_components: tuple[str, ...] = ()
    identity_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


class ReplayArtifactInventoryV1(_Frozen):
    schema_version: Literal[1] = 1
    bundle_label: Literal["first", "replay"]
    declared_count: int = Field(ge=0)
    present_count: int = Field(ge=0)
    file_count: int = Field(ge=0)
    total_bytes: int = Field(ge=0)
    mode_digests: dict[str, str] = {}
    raw_digests: dict[str, str] = {}
    sizes: dict[str, int] = {}
    missing_required: tuple[str, ...] = ()
    missing_optional: tuple[str, ...] = ()
    unsafe_paths: tuple[str, ...] = ()
    duplicate_declared_paths: tuple[str, ...] = ()
    hash_declaration_mismatches: tuple[str, ...] = ()
    undeclared_semantic_paths: tuple[str, ...] = ()
    uncovered_paths: tuple[str, ...] = ()
    orphan_inventory_paths: tuple[str, ...] = ()
    schema_invalid: tuple[str, ...] = ()
    lifecycle_effect_children: dict[str, tuple[str, ...]] = {}
    walk_error: str | None = None
    inventory_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


class ReplayArtifactDeltaV1(_Frozen):
    schema_version: Literal[1] = 1
    compared_artifact_ids: tuple[str, ...] = ()
    byte_identical_artifact_ids: tuple[str, ...] = ()
    semantically_identical_artifact_ids: tuple[str, ...] = ()
    changed_artifact_ids: tuple[str, ...] = ()
    missing_in_first: tuple[str, ...] = ()
    missing_in_replay: tuple[str, ...] = ()
    first_only_paths: tuple[str, ...] = ()
    replay_only_paths: tuple[str, ...] = ()
    allowed_differences_observed: tuple[str, ...] = ()
    promised_byte_identity_failures: tuple[str, ...] = ()
    delta_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


class ProviderLedgerDeltaV1(_Frozen):
    schema_version: Literal[1] = 1
    first_declared_status: str | None = None
    replay_declared_status: str | None = None
    recomputed_first: LlmAccountingSummaryV1 | None = None
    recomputed_replay: LlmAccountingSummaryV1 | None = None
    first_provider_call_count: int | None = None
    replay_provider_call_count: int | None = None
    replay_new_provider_call_ids: tuple[str, ...] = ()
    replay_new_cache_reuse_count: int | None = None
    replay_authoring_calls: int = Field(default=0, ge=0)
    replay_factual_review_calls: int = Field(default=0, ge=0)
    replay_visitor_review_calls: int = Field(default=0, ge=0)
    replay_repair_calls: int = Field(default=0, ge=0)
    replay_other_calls: int = Field(default=0, ge=0)
    replay_unclassified_jobs: tuple[str, ...] = ()
    replay_disallowed_dispositions: tuple[str, ...] = ()
    ledger_superset_ok: bool = False
    ledger_temporal_ok: bool = False
    ledger_scope_ok: bool = False
    declared_accounting_consistent: bool = False
    model_drift_axes: tuple[ProviderCallAxisV1, ...] = ()
    sampling_drift_axes: tuple[ProviderCallAxisV1, ...] = ()
    missing_reused_call_ids: tuple[str, ...] = ()
    ledger_load_error: str | None = None
    accounting_certain: bool = False
    delta_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


class ProductEffectDeltaV1(_Frozen):
    schema_version: Literal[1] = 1
    checked_effects: tuple[ProductEffectV1, ...] = ()
    proven_absent: tuple[ProductEffectV1, ...] = ()
    unproven: tuple[ProductEffectV1, ...] = ()
    violated: tuple[ProductEffectV1, ...] = ()
    target_readme_digest_first: str | None = None
    target_readme_digest_replay: str | None = None
    target_tree_digest_first: str | None = None
    target_tree_digest_replay: str | None = None
    target_revision_first: str | None = None
    target_revision_replay: str | None = None
    duplicate_lifecycle_paths: tuple[str, ...] = ()
    delta_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


class ReplayDriftFindingV1(_Frozen):
    code: str = Field(min_length=1, max_length=200)
    stage: ReplayStageV1
    detail: str = Field(default="", max_length=400)


class CompleteTransactionNoOpProofV1(_Frozen):
    schema_version: Literal[1] = 1
    attestor_identity: Literal["sealed-transaction-replay-attestor"] = ATTESTOR_IDENTITY
    contract_id: str
    org_repo: str
    expected_source_revision: str
    contract_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    passed: bool
    checks: dict[str, bool]
    failures: tuple[str, ...]
    findings: tuple[ReplayDriftFindingV1, ...]
    earliest_affected_stage: ReplayStageV1 | None
    affected_stages: tuple[ReplayStageV1, ...]
    first_identity: SealedTransactionIdentityV1
    replay_identity: SealedTransactionIdentityV1
    first_inventory: ReplayArtifactInventoryV1
    replay_inventory: ReplayArtifactInventoryV1
    artifact_delta: ReplayArtifactDeltaV1
    provider_delta: ProviderLedgerDeltaV1
    effect_delta: ProductEffectDeltaV1
    proof_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
