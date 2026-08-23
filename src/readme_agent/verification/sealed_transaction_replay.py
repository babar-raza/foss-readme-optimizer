"""Attest from sealed evidence alone that a replay transaction was a true no-op."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from datetime import datetime
from pathlib import Path
from typing import Any, Final, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from readme_agent.evidence.file_inventory import filesystem_path
from readme_agent.evidence.redaction import redact_secret_like_values
from readme_agent.evidence.writer import sha256_file
from readme_agent.llm.call_ledger import load_llm_call_records, summarize_llm_call_records
from readme_agent.llm.call_schema import LlmAccountingSummaryV1, LlmCallRecordV1
from readme_agent.readme.document_hashing import sha256_hex

ATTESTOR_IDENTITY: Final = "sealed-transaction-replay-attestor"

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_HEX_DIGEST = re.compile(r"^[0-9a-f]{40,64}$")
_DRIVE_LETTER = re.compile(r"^[A-Za-z]:")
_CONTROL_CHARS = re.compile(r"[\x00-\x1f]")

HashModeV1 = Literal["raw_sha256", "crlf_normalized_sha256", "canonical_json_sha256"]
RequirementLevelV1 = Literal["REQUIRED", "OPTIONAL", "NOT_APPLICABLE"]
ArtifactKindV1 = Literal["json_object", "json_array", "jsonl_llm_ledger", "text", "binary"]
BundleScopeV1 = Literal["both", "first_only", "replay_only"]

# ---- vocabulary: identity components, stages, provider job axes ----

ReplayStageV1 = Literal[
    "SOURCE",
    "KNOWLEDGE",
    "CONFIGURATION",
    "AUTHORING",
    "CANDIDATE",
    "VALIDATION",
    "REVIEW",
    "ACCEPTANCE",
    "EFFECTS",
    "SEALING",
]
_STAGE_SEQUENCE: tuple[ReplayStageV1, ...] = (
    "SOURCE",
    "KNOWLEDGE",
    "CONFIGURATION",
    "AUTHORING",
    "CANDIDATE",
    "VALIDATION",
    "REVIEW",
    "ACCEPTANCE",
    "EFFECTS",
    "SEALING",
)
STAGE_ORDER: dict[ReplayStageV1, int] = {name: i for i, name in enumerate(_STAGE_SEQUENCE)}

IdentityComponentV1 = Literal[
    "repository_identity",
    "source_revision",
    "source_readme_digest",
    "source_tree_inventory_digest",
    "family_platform",
    "facts_hash",
    "knowledge_identity",
    "protected_content_hash",
    "prompt_registry_hash",
    "prompt_hashes_by_id",
    "prompt_dependency_hashes",
    "template_contract_hash",
    "presentation_contract_hash",
    "check_implementation_hash",
    "check_classification_hash",
    "validator_identity_hash",
    "reviewer_standard_hash",
    "reviewer_schema_hash",
    "provider_model_route",
    "sampling_parameters",
    "candidate_hash",
    "candidate_stage_dependency_key",
    "patch_digest",
    "document_plan_hash",
    "claim_evidence_hash",
    "disposition_evidence_hash",
    "reconciliation_evidence_hash",
    "check_evidence_hash",
    "deterministic_validation_hash",
    "factual_review_identity",
    "visitor_review_identity",
    "rubric_identity",
    "final_verdict_identity",
    "acceptance_binding",
    "effect_inventory_digest",
    "artifact_inventory_digest",
    "llm_ledger_boundary",
]

_COMPONENT_STAGE: dict[IdentityComponentV1, ReplayStageV1] = {
    "repository_identity": "SOURCE",
    "source_revision": "SOURCE",
    "source_readme_digest": "SOURCE",
    "source_tree_inventory_digest": "SOURCE",
    "family_platform": "SOURCE",
    "facts_hash": "KNOWLEDGE",
    "knowledge_identity": "KNOWLEDGE",
    "protected_content_hash": "KNOWLEDGE",
    "prompt_registry_hash": "CONFIGURATION",
    "prompt_hashes_by_id": "CONFIGURATION",
    "prompt_dependency_hashes": "CONFIGURATION",
    "template_contract_hash": "CONFIGURATION",
    "presentation_contract_hash": "CONFIGURATION",
    "check_implementation_hash": "CONFIGURATION",
    "check_classification_hash": "CONFIGURATION",
    "validator_identity_hash": "CONFIGURATION",
    "reviewer_standard_hash": "CONFIGURATION",
    "reviewer_schema_hash": "CONFIGURATION",
    "provider_model_route": "AUTHORING",
    "sampling_parameters": "AUTHORING",
    "candidate_hash": "CANDIDATE",
    "candidate_stage_dependency_key": "CANDIDATE",
    "patch_digest": "CANDIDATE",
    "document_plan_hash": "CANDIDATE",
    "claim_evidence_hash": "VALIDATION",
    "disposition_evidence_hash": "VALIDATION",
    "reconciliation_evidence_hash": "VALIDATION",
    "check_evidence_hash": "VALIDATION",
    "deterministic_validation_hash": "VALIDATION",
    "factual_review_identity": "REVIEW",
    "visitor_review_identity": "REVIEW",
    "rubric_identity": "ACCEPTANCE",
    "final_verdict_identity": "ACCEPTANCE",
    "acceptance_binding": "ACCEPTANCE",
    "effect_inventory_digest": "EFFECTS",
    "artifact_inventory_digest": "SEALING",
    "llm_ledger_boundary": "SEALING",
}

_DIGEST_COMPONENTS: frozenset[str] = frozenset(
    {
        "source_revision",
        "source_readme_digest",
        "source_tree_inventory_digest",
        "facts_hash",
        "prompt_registry_hash",
        "template_contract_hash",
        "presentation_contract_hash",
        "check_implementation_hash",
        "check_classification_hash",
        "validator_identity_hash",
        "reviewer_standard_hash",
        "reviewer_schema_hash",
        "candidate_hash",
        "candidate_stage_dependency_key",
        "patch_digest",
        "document_plan_hash",
        "deterministic_validation_hash",
        "protected_content_hash",
    }
)

# artifact_inventory_digest and llm_ledger_boundary are deliberately NOT mandatory identity
# bindings: their underlying content (the file inventory, the ever-growing ledger) legitimately
# differs between a first transaction and its replay (new inventory entries, appended cache-reuse
# ledger records), so a naive cross-bundle equality check on either would fail every true no-op.
# Their proofs are handled by dedicated mechanisms instead: inventory self-declaration
# cross-checking (ReplayArtifactInventoryV1.hash_declaration_mismatches) and the provider-ledger
# superset/temporal/scope coherence checks (ProviderLedgerDeltaV1), both far more precise than a
# whole-file digest comparison.
_MANDATORY_REQUIRED_COMPONENTS: frozenset[str] = frozenset(
    {
        "repository_identity",
        "source_revision",
        "facts_hash",
        "candidate_hash",
    }
)

# Requirement 3 of the attestation contract: deliberately not caller-extensible. A caller-supplied
# exemption would be a drift-laundering hole. Precedent: local_poc_snapshot_evidence's
# _stable_snapshot_identity pops exactly captured_at + snapshot_root -- "this local capture, not the
# immutable object".
ALLOWED_DIFFERENCE_KEYS: frozenset[str] = frozenset(
    {
        "run_id",
        "campaign_run_id",
        "receipt_id",
        "started_at",
        "finished_at",
        "completed_at",
        "promoted_at",
        "sealed_at",
        "captured_at",
        "emitted_at",
        "observed_at",
        "timestamp",
        "last_run_timestamp",
        "snapshot_root",
        "bundle_root",
        "ledger_path",
        "process_id",
        "pid",
    }
)

DEFAULT_NON_SEMANTIC_PATHS: frozenset[str] = frozenset({"sha256sums.txt"})
DEFAULT_NON_SEMANTIC_BASENAMES: frozenset[str] = frozenset(
    {".gitkeep", ".gitignore", ".gitattributes", ".DS_Store", "Thumbs.db", "desktop.ini"}
)
DEFAULT_NON_SEMANTIC_SUFFIXES: frozenset[str] = frozenset(
    {".tmp", ".lock", ".pid", ".log", ".swp", ".bak", ".pyc"}
)
DEFAULT_NON_SEMANTIC_DIRECTORIES: frozenset[str] = frozenset(
    {"__pycache__", ".git", ".pytest_cache"}
)
DEFAULT_LIFECYCLE_EFFECT_DIRECTORIES: tuple[str, ...] = (
    "superseded",
    "receipts",
    "intake/receipts",
)

ProviderCallAxisV1 = Literal["authoring", "factual_review", "visitor_review", "repair", "other"]

# Real job strings observed in real ledgers (runs/readme-poc/*/*/llm-call-ledger.jsonl) plus every
# job= call site in src/. Extend via ProviderProofContractV1.additional_known_jobs, never by
# loosening the unknown-job failure.
KNOWN_PROVIDER_JOB_AXES: dict[str, tuple[ProviderCallAxisV1, ...]] = {
    "section_cluster_authoring": ("authoring",),
    "plan_readme_composition": ("authoring",),
    "trusted_readme_section_transform": ("authoring",),
    "relationship_explained": ("authoring",),
    "factual_readme_plan_review": ("factual_review",),
    "trusted_readme_fidelity_review": ("factual_review",),
    "claim_disposition_check": ("factual_review",),
    "blind_readme_quality_review": ("visitor_review",),
    "prose_quality_check": ("visitor_review",),
    "presentation_standard_compliance": ("visitor_review",),
    "visual_asset_accuracy": ("visitor_review",),
    "merged_readme_review": ("factual_review", "visitor_review"),
    "independent_readme_review": ("factual_review", "visitor_review"),
    "repair_capability_selection": ("repair",),
    "supervisor_planning": ("other",),
    "specialist_selection": ("other",),
    "draft_product_truth": ("other",),
    "embeddings": ("other",),
    "local_poc_approved_bundle": ("other",),
    "local_poc_complete_bundle": ("other",),
    "local_poc_blocked_decision": ("other",),
}
_ZERO_BUDGET_AXES: frozenset[str] = frozenset(
    {"authoring", "factual_review", "visitor_review", "repair"}
)

ProductEffectV1 = Literal[
    "readme_write",
    "commit",
    "branch",
    "push",
    "pull_request",
    "publication",
    "duplicate_lifecycle_effect",
    "target_tree_change",
]


# ---- contract models ----


class _Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


def _validate_relative_path(value: str) -> str:
    if not value:
        raise ValueError("relative_path must not be empty")
    if len(value) > 1024:
        raise ValueError("relative_path exceeds 1024 characters")
    if "\\" in value:
        raise ValueError("relative_path must not contain a backslash")
    if _CONTROL_CHARS.search(value):
        raise ValueError("relative_path must not contain control characters")
    if value.startswith("/"):
        raise ValueError("relative_path must not be absolute")
    if _DRIVE_LETTER.match(value):
        raise ValueError("relative_path must not contain a drive letter")
    if value.endswith("/"):
        raise ValueError("relative_path must not have a trailing slash")
    segments = value.split("/")
    if len(segments) > 32:
        raise ValueError("relative_path has too many segments")
    for segment in segments:
        if segment in ("", ".", ".."):
            raise ValueError(f"relative_path has an unsafe segment: {segment!r}")
    return value


def _validate_json_pointer(value: str) -> str:
    if value == "":
        return value
    if not value.startswith("/"):
        raise ValueError("json_pointer must be empty or start with '/'")
    if len(value) > 512:
        raise ValueError("json_pointer exceeds 512 characters")
    return value


def _sorted_unique(value: Any) -> tuple[str, ...]:
    return tuple(sorted(set(value)))


class DeclaredArtifactV1(_Frozen):
    artifact_id: str = Field(min_length=1, max_length=128, pattern=r"^[a-z0-9_]+$")
    relative_path: str = Field(min_length=1, max_length=1024)
    hash_mode: HashModeV1
    kind: ArtifactKindV1
    level: RequirementLevelV1
    stage: ReplayStageV1
    scope: BundleScopeV1 = "both"
    # False for artifacts that legitimately gain bookkeeping content during a true no-op (manifest
    # lifecycle-status progression, an appended ledger, a new NO_OP_PROVEN receipt) -- their
    # specific stable fields are checked via identity_bindings / the provider-ledger proof instead
    # of requiring the whole artifact to be semantically frozen.
    compare_for_delta: bool = True
    max_bytes: int = Field(default=8_388_608, ge=1, le=268_435_456)
    self_declared_in_inventory: bool = True

    @field_validator("relative_path", mode="after")
    @classmethod
    def _check_relative_path(cls, value: str) -> str:
        return _validate_relative_path(value)


class IdentityBindingSpecV1(_Frozen):
    component: IdentityComponentV1
    level: RequirementLevelV1
    artifact_id: str = Field(min_length=1)
    json_pointer: str = ""

    @field_validator("json_pointer", mode="after")
    @classmethod
    def _check_pointer(cls, value: str) -> str:
        return _validate_json_pointer(value)


class LedgerDeclarationSpecV1(_Frozen):
    artifact_id: str = Field(min_length=1)
    status_pointer: str = "/llm_accounting_status"
    call_count_pointer: str = "/llm_call_count"
    call_ids_pointer: str = "/llm_call_ids"
    calls_by_job_pointer: str = "/llm_calls_by_job"
    ledger_sha256_pointer: str = "/llm_ledger_sha256"
    ledger_sha256_mode: HashModeV1 = "crlf_normalized_sha256"


class ProviderProofContractV1(_Frozen):
    first_ledger_artifact_id: str = Field(min_length=1)
    replay_ledger_artifact_id: str = Field(min_length=1)
    first_declaration: LedgerDeclarationSpecV1
    replay_declaration: LedgerDeclarationSpecV1
    replay_ledger_scope: Literal["cumulative", "current_transaction"] = "cumulative"
    require_non_empty_first_ledger: bool = True
    require_ledger_superset: bool = True
    require_temporal_coherence: bool = True
    allowed_replay_dispositions: tuple[Literal["fixture", "cache_reuse"], ...] = ("cache_reuse",)
    additional_known_jobs: tuple[tuple[str, tuple[ProviderCallAxisV1, ...]], ...] = ()

    @field_validator("additional_known_jobs", mode="after")
    @classmethod
    def _sort_additional_jobs(
        cls, value: tuple[tuple[str, tuple[ProviderCallAxisV1, ...]], ...]
    ) -> tuple[tuple[str, tuple[ProviderCallAxisV1, ...]], ...]:
        return tuple(sorted(value, key=lambda item: item[0]))


class ProductEffectExpectationV1(_Frozen):
    effect: ProductEffectV1
    level: RequirementLevelV1
    artifact_id: str = Field(min_length=1)
    json_pointer: str = ""
    comparison: Literal["equals_expected", "equal_across_bundles", "absent"]
    expected_value: bool | int | str | None = None

    @field_validator("json_pointer", mode="after")
    @classmethod
    def _check_pointer(cls, value: str) -> str:
        return _validate_json_pointer(value)


class ReplayAttestationContractV1(_Frozen):
    schema_version: Literal[1] = 1
    contract_id: str = Field(min_length=1, max_length=128)
    org_repo: str
    expected_source_revision: str

    artifacts: tuple[DeclaredArtifactV1, ...] = Field(min_length=1)
    identity_bindings: tuple[IdentityBindingSpecV1, ...] = Field(min_length=1)
    output_equivalence_artifact_ids: tuple[str, ...] = ()

    provider_proof: ProviderProofContractV1
    product_effects: tuple[ProductEffectExpectationV1, ...] = Field(min_length=1)

    non_semantic_paths: tuple[str, ...] = tuple(sorted(DEFAULT_NON_SEMANTIC_PATHS))
    non_semantic_basenames: tuple[str, ...] = tuple(sorted(DEFAULT_NON_SEMANTIC_BASENAMES))
    non_semantic_suffixes: tuple[str, ...] = tuple(sorted(DEFAULT_NON_SEMANTIC_SUFFIXES))
    non_semantic_directories: tuple[str, ...] = tuple(sorted(DEFAULT_NON_SEMANTIC_DIRECTORIES))
    lifecycle_effect_directories: tuple[str, ...] = DEFAULT_LIFECYCLE_EFFECT_DIRECTORIES

    max_inventory_files: int = Field(default=5_000, ge=1, le=200_000)
    max_inventory_bytes: int = Field(default=1_073_741_824, ge=1)
    max_artifact_bytes: int = Field(default=33_554_432, ge=1)

    @field_validator("expected_source_revision", mode="after")
    @classmethod
    def _check_revision(cls, value: str) -> str:
        if not _HEX_DIGEST.match(value):
            raise ValueError("expected_source_revision must be a 40-64 char lowercase hex digest")
        return value

    @field_validator("org_repo", mode="after")
    @classmethod
    def _check_org_repo(cls, value: str) -> str:
        parts = value.split("/")
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise ValueError("org_repo must be exactly one '<org>/<repo>' pair")
        return value

    @field_validator(
        "output_equivalence_artifact_ids",
        "non_semantic_paths",
        "non_semantic_basenames",
        "non_semantic_suffixes",
        "non_semantic_directories",
        "lifecycle_effect_directories",
        mode="after",
    )
    @classmethod
    def _normalize_string_tuples(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _sorted_unique(value)

    @model_validator(mode="after")
    def _check_consistency(self) -> ReplayAttestationContractV1:
        artifact_ids = [artifact.artifact_id for artifact in self.artifacts]
        if len(artifact_ids) != len(set(artifact_ids)):
            raise ValueError("duplicate artifact_id declared in contract")
        paths = [artifact.relative_path for artifact in self.artifacts]
        if len(paths) != len(set(paths)):
            raise ValueError("duplicate relative_path declared in contract")
        known_ids = set(artifact_ids)

        component_ids = [binding.component for binding in self.identity_bindings]
        if len(component_ids) != len(set(component_ids)):
            raise ValueError("duplicate identity component declared in contract")

        for binding in self.identity_bindings:
            if binding.artifact_id not in known_ids:
                raise ValueError(
                    f"identity binding references undeclared artifact: {binding.artifact_id}"
                )

        required_components = {
            binding.component for binding in self.identity_bindings if binding.level == "REQUIRED"
        }
        missing_mandatory = _MANDATORY_REQUIRED_COMPONENTS - required_components
        if missing_mandatory:
            raise ValueError(
                f"contract omits mandatory required components: {sorted(missing_mandatory)}"
            )

        for artifact_id in self.output_equivalence_artifact_ids:
            if artifact_id not in known_ids:
                raise ValueError(
                    f"output equivalence references undeclared artifact: {artifact_id}"
                )
            artifact = next(a for a in self.artifacts if a.artifact_id == artifact_id)
            if artifact.level == "NOT_APPLICABLE":
                raise ValueError(f"output equivalence artifact is NOT_APPLICABLE: {artifact_id}")
            if artifact.scope != "both":
                raise ValueError(f"output equivalence artifact must be scope=both: {artifact_id}")
            if not artifact.compare_for_delta:
                raise ValueError(
                    f"output equivalence artifact must have compare_for_delta=True: {artifact_id}"
                )

        for effect in self.product_effects:
            if effect.artifact_id not in known_ids:
                raise ValueError(
                    f"product effect references undeclared artifact: {effect.artifact_id}"
                )

        for ledger_id in (
            self.provider_proof.first_ledger_artifact_id,
            self.provider_proof.replay_ledger_artifact_id,
        ):
            if ledger_id not in known_ids:
                raise ValueError(
                    f"provider proof references undeclared ledger artifact: {ledger_id}"
                )
            ledger_artifact = next(a for a in self.artifacts if a.artifact_id == ledger_id)
            if ledger_artifact.kind != "jsonl_llm_ledger":
                raise ValueError(
                    f"provider proof ledger artifact must be kind=jsonl_llm_ledger: {ledger_id}"
                )

        for declaration in (
            self.provider_proof.first_declaration,
            self.provider_proof.replay_declaration,
        ):
            if declaration.artifact_id not in known_ids:
                raise ValueError(
                    "provider proof declaration references undeclared artifact: "
                    f"{declaration.artifact_id}"
                )
        return self


# ---- proof models ----


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


# ---- canonical hashing ----


def canonical_json_sha256(value: object) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _canonical_contract_digest(contract: ReplayAttestationContractV1) -> str:
    # sort_keys=True canonicalizes JSON OBJECT key order but never touches ARRAY element order --
    # artifacts/identity_bindings/product_effects are declarations, not sequences, so their
    # declared order must not affect the digest (requirement 8, "stable output ordering/hash").
    payload = contract.model_dump(mode="json")
    payload["artifacts"] = sorted(payload["artifacts"], key=lambda item: item["artifact_id"])
    payload["identity_bindings"] = sorted(
        payload["identity_bindings"], key=lambda item: item["component"]
    )
    payload["product_effects"] = sorted(payload["product_effects"], key=lambda item: item["effect"])
    return canonical_json_sha256(payload)


def _mode_digest(path: Path, data: bytes, mode: HashModeV1, parsed: Any) -> str:
    if mode == "raw_sha256":
        return sha256_hex(data)
    if mode == "crlf_normalized_sha256":
        return sha256_file(path)[0]
    return canonical_json_sha256(parsed)


# ---- json pointer and semantic projection ----

_SCALAR_TYPES = (str, int, float, bool, type(None))
_MISSING = object()


def _pointer_escape(token: str) -> str:
    return token.replace("~", "~0").replace("/", "~1")


def _resolve_pointer(document: Any, pointer: str) -> tuple[bool, Any]:
    if pointer == "":
        return True, document
    if not pointer.startswith("/"):
        return False, None
    node = document
    for raw_token in pointer.split("/")[1:]:
        token = raw_token.replace("~1", "/").replace("~0", "~")
        if isinstance(node, dict):
            if token not in node:
                return False, None
            node = node[token]
        elif isinstance(node, list):
            if not re.fullmatch(r"0|[1-9][0-9]*", token):
                return False, None
            index = int(token)
            if index >= len(node):
                return False, None
            node = node[index]
        else:
            return False, None
    return True, node


def _project_semantic(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _project_semantic(sub)
            for key, sub in sorted(value.items())
            if not (key in ALLOWED_DIFFERENCE_KEYS and isinstance(sub, _SCALAR_TYPES))
        }
    if isinstance(value, list):
        return [_project_semantic(item) for item in value]
    return value


def _diff_allowed_pointers(first: Any, replay: Any, *, path: str = "") -> list[str]:
    observed: list[str] = []
    if isinstance(first, dict) and isinstance(replay, dict):
        for key in sorted(set(first) | set(replay)):
            child = f"{path}/{_pointer_escape(key)}"
            f_val = first.get(key, _MISSING)
            r_val = replay.get(key, _MISSING)
            if f_val == r_val:
                continue
            if (
                key in ALLOWED_DIFFERENCE_KEYS
                and (f_val is _MISSING or isinstance(f_val, _SCALAR_TYPES))
                and (r_val is _MISSING or isinstance(r_val, _SCALAR_TYPES))
            ):
                observed.append(child)
            elif f_val is not _MISSING and r_val is not _MISSING:
                observed.extend(_diff_allowed_pointers(f_val, r_val, path=child))
    elif isinstance(first, list) and isinstance(replay, list) and len(first) == len(replay):
        for index, (f_item, r_item) in enumerate(zip(first, replay, strict=True)):
            observed.extend(_diff_allowed_pointers(f_item, r_item, path=f"{path}/{index}"))
    return observed


# ---- path safety ----


def _resolve_declared_path(root: Path, relative_posix: str) -> Path | None:
    """Resolve a declared relative path beneath root, rejecting any symlink in the chain."""

    current = root
    parts = relative_posix.split("/")
    for part in parts[:-1]:
        current = current / part
        try:
            entry_stat = os.lstat(current)
        except OSError:
            return None
        if stat.S_ISLNK(entry_stat.st_mode) or not stat.S_ISDIR(entry_stat.st_mode):
            return None
    final = current / parts[-1]
    try:
        final_stat = os.lstat(final)
    except OSError:
        return None
    if stat.S_ISLNK(final_stat.st_mode) or not stat.S_ISREG(final_stat.st_mode):
        return None
    try:
        resolved_root = root.resolve()
        resolved_final = final.resolve()
        resolved_final.relative_to(resolved_root)
    except (OSError, ValueError):
        return None
    return final


def _is_non_semantic(
    relative_posix: str,
    *,
    non_semantic_paths: frozenset[str],
    non_semantic_basenames: frozenset[str],
    non_semantic_suffixes: frozenset[str],
    non_semantic_directories: frozenset[str],
) -> bool:
    if relative_posix in non_semantic_paths:
        return True
    segments = relative_posix.split("/")
    basename = segments[-1]
    if basename in non_semantic_basenames:
        return True
    if any(basename.endswith(suffix) for suffix in non_semantic_suffixes):
        return True
    return any(segment in non_semantic_directories for segment in segments[:-1])


def _under_lifecycle_directory(
    relative_posix: str, lifecycle_directories: tuple[str, ...]
) -> str | None:
    for directory in lifecycle_directories:
        prefix = directory.rstrip("/") + "/"
        if relative_posix.startswith(prefix):
            return directory
    return None


# ---- filesystem walk and inventory ----


class _WalkResult:
    __slots__ = ("regular_files", "unsafe_paths", "file_count", "total_bytes", "walk_error")

    def __init__(self) -> None:
        self.regular_files: list[str] = []
        self.unsafe_paths: list[str] = []
        self.file_count = 0
        self.total_bytes = 0
        self.walk_error: str | None = None


def _walk_bundle(root: Path, *, max_files: int, max_bytes: int) -> _WalkResult:
    result = _WalkResult()
    physical_root = filesystem_path(root)
    root_str = str(physical_root)
    try:
        for dirpath, dirnames, filenames in os.walk(root_str, topdown=True, followlinks=False):
            dirnames.sort()
            safe_dirnames: list[str] = []
            for name in dirnames:
                full = os.path.join(dirpath, name)
                rel = os.path.relpath(full, root_str).replace(os.sep, "/")
                try:
                    entry_stat = os.lstat(full)
                except OSError as exc:
                    result.walk_error = str(exc)
                    return result
                if stat.S_ISLNK(entry_stat.st_mode):
                    result.unsafe_paths.append(rel)
                    continue
                safe_dirnames.append(name)
            dirnames[:] = safe_dirnames
            for name in sorted(filenames):
                full = os.path.join(dirpath, name)
                rel = os.path.relpath(full, root_str).replace(os.sep, "/")
                try:
                    entry_stat = os.lstat(full)
                except OSError as exc:
                    result.walk_error = str(exc)
                    return result
                if stat.S_ISLNK(entry_stat.st_mode) or not stat.S_ISREG(entry_stat.st_mode):
                    result.unsafe_paths.append(rel)
                    continue
                result.file_count += 1
                result.total_bytes += entry_stat.st_size
                if result.file_count > max_files or result.total_bytes > max_bytes:
                    result.walk_error = "inventory_bounds_exceeded"
                    return result
                result.regular_files.append(rel)
    except OSError as exc:
        result.walk_error = str(exc)
    result.regular_files.sort()
    result.unsafe_paths.sort()
    return result


def _parse_sha256sums(path: Path) -> tuple[dict[str, str], list[str]]:
    entries: dict[str, str] = {}
    duplicates: list[str] = []
    if not path.is_file():
        return entries, duplicates
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return entries, duplicates
    for line in text.splitlines():
        if not line.strip() or "  " not in line:
            continue
        digest, relpath = line.split("  ", 1)
        if not _HEX64.match(digest) or not relpath:
            continue
        if relpath in entries:
            duplicates.append(relpath)
            continue
        entries[relpath] = digest
    return entries, sorted(set(duplicates))


def _build_inventory(
    root: Path,
    contract: ReplayAttestationContractV1,
    *,
    label: Literal["first", "replay"],
    scopes: tuple[BundleScopeV1, ...],
) -> tuple[ReplayArtifactInventoryV1, dict[str, Any], dict[str, str]]:
    walk = _walk_bundle(
        root, max_files=contract.max_inventory_files, max_bytes=contract.max_inventory_bytes
    )
    on_disk = set(walk.regular_files)

    declared = [artifact for artifact in contract.artifacts if artifact.scope in scopes]
    missing_required: list[str] = []
    missing_optional: list[str] = []
    unsafe_paths = list(walk.unsafe_paths)
    mode_digests: dict[str, str] = {}
    raw_digests: dict[str, str] = {}
    sizes: dict[str, int] = {}
    schema_invalid: list[str] = []
    parsed_by_id: dict[str, Any] = {}
    path_by_id: dict[str, str] = {}

    if walk.walk_error is not None:
        inventory = ReplayArtifactInventoryV1(
            bundle_label=label,
            declared_count=len(declared),
            present_count=0,
            file_count=walk.file_count,
            total_bytes=walk.total_bytes,
            missing_required=tuple(a.artifact_id for a in declared if a.level == "REQUIRED"),
            walk_error=walk.walk_error,
            inventory_digest=canonical_json_sha256({"walk_error": walk.walk_error}),
        )
        return inventory, {}, {}

    for artifact in declared:
        resolved = _resolve_declared_path(root, artifact.relative_path)
        if resolved is None:
            if artifact.relative_path in on_disk:
                unsafe_paths.append(artifact.relative_path)
            if artifact.level == "REQUIRED":
                missing_required.append(artifact.artifact_id)
            elif artifact.level == "OPTIONAL":
                missing_optional.append(artifact.artifact_id)
            continue
        try:
            data = resolved.read_bytes()
        except OSError:
            if artifact.level == "REQUIRED":
                missing_required.append(artifact.artifact_id)
            continue
        effective_cap = min(artifact.max_bytes, contract.max_artifact_bytes)
        if len(data) > effective_cap:
            unsafe_paths.append(artifact.relative_path)
            if artifact.level == "REQUIRED":
                missing_required.append(artifact.artifact_id)
            continue

        parsed: Any = None
        valid = True
        if artifact.kind == "json_object":
            try:
                parsed = json.loads(data.decode("utf-8"))
                valid = isinstance(parsed, dict)
            except (json.JSONDecodeError, UnicodeDecodeError):
                valid = False
        elif artifact.kind == "json_array":
            try:
                parsed = json.loads(data.decode("utf-8"))
                valid = isinstance(parsed, list)
            except (json.JSONDecodeError, UnicodeDecodeError):
                valid = False
        elif artifact.kind == "jsonl_llm_ledger":
            if not resolved.is_file():
                valid = False
            else:
                try:
                    parsed = load_llm_call_records(resolved)
                except (RuntimeError, ValueError, OSError, UnicodeError):
                    valid = False

        if not valid:
            schema_invalid.append(artifact.artifact_id)
            continue

        # Raw byte digests are only meaningful (and stored) for hash modes where byte identity is
        # the actual semantic identity. A canonical_json_sha256 artifact's raw bytes are, by
        # design, allowed to reformat/reorder without changing its identity -- storing a raw
        # digest for it would make the proof (and proof_hash) sensitive to formatting noise that
        # requirement 8 ("stable output ordering/hash") explicitly says must not matter.
        if artifact.hash_mode != "canonical_json_sha256":
            raw_digests[artifact.artifact_id] = sha256_hex(data)
        mode_digests[artifact.artifact_id] = _mode_digest(
            resolved, data, artifact.hash_mode, parsed
        )
        sizes[artifact.artifact_id] = len(data)
        parsed_by_id[artifact.artifact_id] = parsed
        path_by_id[artifact.artifact_id] = artifact.relative_path

    inventory_entries, duplicate_declared_paths = _parse_sha256sums(root / "sha256sums.txt")
    uncovered_paths: list[str] = []
    orphan_inventory_paths: list[str] = []
    hash_declaration_mismatches: list[str] = []
    if inventory_entries or (root / "sha256sums.txt").is_file():
        covered = set(inventory_entries)
        uncovered_paths = sorted((on_disk - {"sha256sums.txt"}) - covered)
        orphan_inventory_paths = sorted(covered - on_disk)
        for relpath, expected_digest in inventory_entries.items():
            candidate = root / relpath
            resolved_candidate = (
                _resolve_declared_path(root, relpath) if "/" in relpath or relpath else None
            )
            target = (
                resolved_candidate
                if resolved_candidate is not None
                else (candidate if candidate.is_file() else None)
            )
            if target is None:
                continue
            try:
                actual_digest, _ = sha256_file(target)
            except OSError:
                continue
            if actual_digest != expected_digest:
                hash_declaration_mismatches.append(relpath)

    lifecycle_effect_children: dict[str, tuple[str, ...]] = {}
    undeclared_semantic_paths: list[str] = []
    declared_paths = {artifact.relative_path for artifact in declared}
    for relpath in walk.regular_files:
        lifecycle_dir = _under_lifecycle_directory(relpath, contract.lifecycle_effect_directories)
        if lifecycle_dir is not None:
            children = lifecycle_effect_children.setdefault(lifecycle_dir, ())
            remainder = relpath[len(lifecycle_dir) + 1 :]
            child = remainder.split("/", 1)[0]
            if child not in children:
                lifecycle_effect_children[lifecycle_dir] = tuple(sorted({*children, child}))
            continue
        if relpath in declared_paths:
            continue
        if _is_non_semantic(
            relpath,
            non_semantic_paths=frozenset(contract.non_semantic_paths),
            non_semantic_basenames=frozenset(contract.non_semantic_basenames),
            non_semantic_suffixes=frozenset(contract.non_semantic_suffixes),
            non_semantic_directories=frozenset(contract.non_semantic_directories),
        ):
            continue
        undeclared_semantic_paths.append(relpath)

    inventory = ReplayArtifactInventoryV1(
        bundle_label=label,
        declared_count=len(declared),
        present_count=len(mode_digests),
        file_count=walk.file_count,
        total_bytes=walk.total_bytes,
        mode_digests=mode_digests,
        raw_digests=raw_digests,
        sizes=sizes,
        missing_required=tuple(sorted(set(missing_required))),
        missing_optional=tuple(sorted(set(missing_optional))),
        unsafe_paths=tuple(sorted(set(unsafe_paths))),
        duplicate_declared_paths=tuple(duplicate_declared_paths),
        hash_declaration_mismatches=tuple(sorted(set(hash_declaration_mismatches))),
        undeclared_semantic_paths=tuple(sorted(set(undeclared_semantic_paths))),
        uncovered_paths=tuple(uncovered_paths),
        orphan_inventory_paths=tuple(orphan_inventory_paths),
        schema_invalid=tuple(sorted(set(schema_invalid))),
        lifecycle_effect_children=lifecycle_effect_children,
        walk_error=None,
        inventory_digest=canonical_json_sha256(
            {
                "mode": sorted(mode_digests.items()),
                "raw": sorted(raw_digests.items()),
                "undeclared": sorted(set(undeclared_semantic_paths)),
                "lifecycle": sorted(lifecycle_effect_children.items()),
            }
        ),
    )
    return inventory, parsed_by_id, path_by_id


# ---- identity extraction ----


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


# ---- artifact delta ----


def _build_artifact_delta(
    contract: ReplayAttestationContractV1,
    first_parsed: dict[str, Any],
    replay_parsed: dict[str, Any],
    first_inventory: ReplayArtifactInventoryV1,
    replay_inventory: ReplayArtifactInventoryV1,
    first_walk: _WalkResult,
    replay_walk: _WalkResult,
) -> ReplayArtifactDeltaV1:
    both_artifacts = [
        artifact
        for artifact in contract.artifacts
        if artifact.scope == "both" and artifact.compare_for_delta
    ]
    compared: list[str] = []
    byte_identical: list[str] = []
    semantically_identical: list[str] = []
    changed: list[str] = []
    missing_in_first: list[str] = []
    missing_in_replay: list[str] = []
    allowed_diffs: list[str] = []
    promised_failures: list[str] = []

    def _comparison_digest(inventory: ReplayArtifactInventoryV1, artifact_id: str) -> str | None:
        # raw_digests is the byte-identity signal; for canonical_json_sha256 artifacts (which are
        # deliberately reorder/formatting-invariant) it is never populated, so the canonical
        # mode_digest -- itself already order-independent -- is the correct identity surrogate.
        return inventory.raw_digests.get(artifact_id) or inventory.mode_digests.get(artifact_id)

    for artifact in both_artifacts:
        artifact_id = artifact.artifact_id
        in_first = artifact_id in first_inventory.mode_digests
        in_replay = artifact_id in replay_inventory.mode_digests
        if not in_first and not in_replay:
            continue
        if not in_first:
            missing_in_first.append(artifact_id)
            continue
        if not in_replay:
            missing_in_replay.append(artifact_id)
            continue
        compared.append(artifact_id)
        raw_equal = _comparison_digest(first_inventory, artifact_id) == _comparison_digest(
            replay_inventory, artifact_id
        )
        if artifact_id in contract.output_equivalence_artifact_ids:
            if not raw_equal:
                promised_failures.append(artifact_id)
                changed.append(artifact_id)
            else:
                byte_identical.append(artifact_id)
            continue
        if raw_equal:
            byte_identical.append(artifact_id)
            continue
        if artifact.kind in ("json_object", "json_array"):
            first_doc = first_parsed.get(artifact_id)
            replay_doc = replay_parsed.get(artifact_id)
            first_projection = _project_semantic(first_doc)
            replay_projection = _project_semantic(replay_doc)
            if canonical_json_sha256(first_projection) == canonical_json_sha256(replay_projection):
                semantically_identical.append(artifact_id)
                allowed_diffs.extend(
                    f"{artifact_id}#{pointer}"
                    for pointer in _diff_allowed_pointers(first_doc, replay_doc)
                )
            else:
                changed.append(artifact_id)
        else:
            changed.append(artifact_id)

    # Any declared artifact's presence/absence is already governed precisely by its own
    # level (REQUIRED/OPTIONAL/NOT_APPLICABLE) via missing_required/missing_optional -- the raw
    # file-set diff below exists only to catch UNDECLARED files appearing asymmetrically, so every
    # declared path (any scope, any level) is exempt from it regardless of which side it's on.
    declared_paths = {a.relative_path for a in contract.artifacts}
    non_semantic_kwargs = {
        "non_semantic_paths": frozenset(contract.non_semantic_paths),
        "non_semantic_basenames": frozenset(contract.non_semantic_basenames),
        "non_semantic_suffixes": frozenset(contract.non_semantic_suffixes),
        "non_semantic_directories": frozenset(contract.non_semantic_directories),
    }
    first_only_paths = sorted(
        path
        for path in set(first_walk.regular_files) - set(replay_walk.regular_files) - declared_paths
        if not _is_non_semantic(path, **non_semantic_kwargs)
    )
    replay_only_paths = sorted(
        path
        for path in set(replay_walk.regular_files) - set(first_walk.regular_files) - declared_paths
        if not _is_non_semantic(path, **non_semantic_kwargs)
    )

    return ReplayArtifactDeltaV1(
        compared_artifact_ids=tuple(sorted(compared)),
        byte_identical_artifact_ids=tuple(sorted(byte_identical)),
        semantically_identical_artifact_ids=tuple(sorted(semantically_identical)),
        changed_artifact_ids=tuple(sorted(changed)),
        missing_in_first=tuple(sorted(missing_in_first)),
        missing_in_replay=tuple(sorted(missing_in_replay)),
        first_only_paths=tuple(first_only_paths),
        replay_only_paths=tuple(replay_only_paths),
        allowed_differences_observed=tuple(sorted(set(allowed_diffs))),
        promised_byte_identity_failures=tuple(sorted(promised_failures)),
        delta_digest=canonical_json_sha256(
            {
                "changed": sorted(changed),
                "missing_first": sorted(missing_in_first),
                "missing_replay": sorted(missing_in_replay),
                "promised_failures": sorted(promised_failures),
            }
        ),
    )


# ---- provider ledger recomputation ----


def _classify_job(
    job: str, extra: dict[str, tuple[ProviderCallAxisV1, ...]]
) -> tuple[ProviderCallAxisV1, ...] | None:
    if job in extra:
        return extra[job]
    return KNOWN_PROVIDER_JOB_AXES.get(job)


def _load_ledger(
    root: Path, contract: ReplayAttestationContractV1, artifact_id: str
) -> tuple[list[LlmCallRecordV1] | None, Path | None, str | None]:
    artifact = next((a for a in contract.artifacts if a.artifact_id == artifact_id), None)
    if artifact is None:
        return None, None, "ledger_artifact_undeclared"
    resolved = _resolve_declared_path(root, artifact.relative_path)
    if resolved is None or not resolved.is_file():
        return None, None, "ledger_file_missing"
    try:
        records = load_llm_call_records(resolved)
    except (RuntimeError, ValueError, OSError, UnicodeError) as exc:
        return None, resolved, str(exc)
    return records, resolved, None


def _build_provider_delta(
    contract: ReplayAttestationContractV1,
    first_root: Path,
    replay_root: Path,
    first_parsed: dict[str, Any],
    replay_parsed: dict[str, Any],
) -> ProviderLedgerDeltaV1:
    proof = contract.provider_proof
    extra_jobs = dict(proof.additional_known_jobs)

    first_records, first_path, first_error = _load_ledger(
        first_root, contract, proof.first_ledger_artifact_id
    )
    replay_records, replay_path, replay_error = _load_ledger(
        replay_root, contract, proof.replay_ledger_artifact_id
    )

    ledger_load_error = first_error or replay_error
    if first_records is None or replay_records is None:
        return ProviderLedgerDeltaV1(
            ledger_load_error=ledger_load_error,
            accounting_certain=False,
            delta_digest=canonical_json_sha256({"error": ledger_load_error}),
        )

    if proof.require_non_empty_first_ledger and not first_records:
        return ProviderLedgerDeltaV1(
            ledger_load_error="first_ledger_empty",
            accounting_certain=False,
            delta_digest=canonical_json_sha256({"error": "first_ledger_empty"}),
        )

    recomputed_first = summarize_llm_call_records(first_records, ledger_path=first_path)
    recomputed_replay = summarize_llm_call_records(replay_records, ledger_path=replay_path)
    first_relative = next(
        a.relative_path
        for a in contract.artifacts
        if a.artifact_id == proof.first_ledger_artifact_id
    )
    replay_relative = next(
        a.relative_path
        for a in contract.artifacts
        if a.artifact_id == proof.replay_ledger_artifact_id
    )
    recomputed_first = recomputed_first.model_copy(update={"ledger_path": first_relative})
    recomputed_replay = recomputed_replay.model_copy(update={"ledger_path": replay_relative})

    first_declaration_doc = first_parsed.get(proof.first_declaration.artifact_id)
    replay_declaration_doc = replay_parsed.get(proof.replay_declaration.artifact_id)
    _, first_declared_status = (
        _resolve_pointer(first_declaration_doc, proof.first_declaration.status_pointer)
        if first_declaration_doc is not None
        else (False, None)
    )
    _, replay_declared_status = (
        _resolve_pointer(replay_declaration_doc, proof.replay_declaration.status_pointer)
        if replay_declaration_doc is not None
        else (False, None)
    )

    accounting_certain = (
        recomputed_first.status == "EXACT"
        and recomputed_replay.status == "EXACT"
        and first_declared_status == "EXACT"
        and replay_declared_status == "EXACT"
    )

    declared_accounting_consistent = True
    if accounting_certain and first_declaration_doc is not None:
        _, declared_count = _resolve_pointer(
            first_declaration_doc, proof.first_declaration.call_count_pointer
        )
        if declared_count is not None and declared_count != recomputed_first.provider_call_count:
            declared_accounting_consistent = False
    if accounting_certain and replay_declaration_doc is not None:
        _, declared_count = _resolve_pointer(
            replay_declaration_doc, proof.replay_declaration.call_count_pointer
        )
        if declared_count is not None and declared_count != recomputed_replay.provider_call_count:
            declared_accounting_consistent = False
    accounting_certain = accounting_certain and declared_accounting_consistent

    first_by_id = {record.call_id: record for record in first_records}
    replay_by_id = {record.call_id: record for record in replay_records}

    ledger_superset_ok = True
    model_drift_axes: set[ProviderCallAxisV1] = set()
    sampling_drift_axes: set[ProviderCallAxisV1] = set()
    missing_reused_call_ids: list[str] = []
    if proof.require_ledger_superset:
        for call_id, record in first_by_id.items():
            other = replay_by_id.get(call_id)
            if other is None:
                ledger_superset_ok = False
                missing_reused_call_ids.append(call_id)
                continue
            if other.model_dump(mode="json") == record.model_dump(mode="json"):
                continue
            ledger_superset_ok = False
            reused_axes = _classify_job(record.job, extra_jobs) or ()
            if record.prompt_sha256 == other.prompt_sha256 and record.model != other.model:
                model_drift_axes.update(reused_axes)
            elif (
                record.prompt_sha256 == other.prompt_sha256
                and record.model == other.model
                and record.request_sha256 != other.request_sha256
            ):
                sampling_drift_axes.update(reused_axes)

    new_ids = sorted(set(replay_by_id) - set(first_by_id))
    disallowed_dispositions: list[str] = []
    for call_id in new_ids:
        record = replay_by_id[call_id]
        if record.disposition not in proof.allowed_replay_dispositions:
            disallowed_dispositions.append(call_id)

    ledger_scope_ok = True
    for call_id in new_ids:
        record = replay_by_id[call_id]
        if (
            record.org_repo != contract.org_repo
            or record.source_revision != contract.expected_source_revision
        ):
            ledger_scope_ok = False

    ledger_temporal_ok = True
    if proof.require_temporal_coherence and first_records:
        try:
            latest_first_finish = max(
                datetime.fromisoformat(record.finished_at) for record in first_records
            )
            for call_id in new_ids:
                started = datetime.fromisoformat(replay_by_id[call_id].started_at)
                if started < latest_first_finish:
                    ledger_temporal_ok = False
                    break
        except (ValueError, TypeError):
            ledger_temporal_ok = False

    axis_counts: dict[ProviderCallAxisV1, int] = {
        "authoring": 0,
        "factual_review": 0,
        "visitor_review": 0,
        "repair": 0,
        "other": 0,
    }
    unclassified: list[str] = []
    for call_id in new_ids:
        record = replay_by_id[call_id]
        axes = _classify_job(record.job, extra_jobs)
        if axes is None:
            # An unrecognized job is unaccounted evidence regardless of disposition -- even a
            # cache_reuse/fixture record with an unmapped job fails closed, never a free pass.
            unclassified.append(record.job)
            continue
        if record.disposition != "provider_call":
            continue
        for axis in axes:
            axis_counts[axis] += 1

    # A disallowed disposition (e.g. a new provider_call where only cache_reuse is expected) is a
    # CERTAIN, fully-classified violation -- it must not be folded into "uncertain", or the
    # specific new_provider_call:<axis> finding below would never fire, replaced by a generic
    # "accounting is not certain" failure that hides which role actually made the new call. An
    # unmapped job is different: it genuinely IS uncertainty (we cannot classify what happened).
    accounting_certain = (
        accounting_certain
        and ledger_superset_ok
        and ledger_scope_ok
        and ledger_temporal_ok
        and not unclassified
    )

    new_provider_call_ids = sorted(
        call_id for call_id in new_ids if replay_by_id[call_id].disposition == "provider_call"
    )
    new_cache_reuse_count = sum(
        1 for call_id in new_ids if replay_by_id[call_id].disposition == "cache_reuse"
    )

    return ProviderLedgerDeltaV1(
        first_declared_status=first_declared_status
        if isinstance(first_declared_status, str)
        else None,
        replay_declared_status=replay_declared_status
        if isinstance(replay_declared_status, str)
        else None,
        recomputed_first=recomputed_first if accounting_certain else None,
        recomputed_replay=recomputed_replay if accounting_certain else None,
        first_provider_call_count=recomputed_first.provider_call_count
        if accounting_certain
        else None,
        replay_provider_call_count=recomputed_replay.provider_call_count
        if accounting_certain
        else None,
        replay_new_provider_call_ids=tuple(new_provider_call_ids) if accounting_certain else (),
        replay_new_cache_reuse_count=new_cache_reuse_count if accounting_certain else None,
        replay_authoring_calls=axis_counts["authoring"] if accounting_certain else 0,
        replay_factual_review_calls=axis_counts["factual_review"] if accounting_certain else 0,
        replay_visitor_review_calls=axis_counts["visitor_review"] if accounting_certain else 0,
        replay_repair_calls=axis_counts["repair"] if accounting_certain else 0,
        replay_other_calls=axis_counts["other"] if accounting_certain else 0,
        replay_unclassified_jobs=tuple(sorted(set(unclassified))),
        replay_disallowed_dispositions=tuple(sorted(set(disallowed_dispositions))),
        ledger_superset_ok=ledger_superset_ok,
        ledger_temporal_ok=ledger_temporal_ok,
        ledger_scope_ok=ledger_scope_ok,
        declared_accounting_consistent=declared_accounting_consistent,
        model_drift_axes=tuple(sorted(model_drift_axes)),
        sampling_drift_axes=tuple(sorted(sampling_drift_axes)),
        missing_reused_call_ids=tuple(sorted(set(missing_reused_call_ids))),
        ledger_load_error=None,
        accounting_certain=accounting_certain,
        delta_digest=canonical_json_sha256(
            {
                "new_ids": new_ids,
                "axis_counts": sorted(axis_counts.items()),
                "unclassified": sorted(set(unclassified)),
                "certain": accounting_certain,
                "model_drift": sorted(model_drift_axes),
                "sampling_drift": sorted(sampling_drift_axes),
            }
        ),
    )


# ---- product effect evidence ----


def _build_effect_delta(
    contract: ReplayAttestationContractV1,
    first_parsed: dict[str, Any],
    replay_parsed: dict[str, Any],
    first_inventory: ReplayArtifactInventoryV1,
    replay_inventory: ReplayArtifactInventoryV1,
) -> ProductEffectDeltaV1:
    checked: list[ProductEffectV1] = []
    proven_absent: list[ProductEffectV1] = []
    unproven: list[ProductEffectV1] = []
    violated: list[ProductEffectV1] = []

    for expectation in contract.product_effects:
        if expectation.level == "NOT_APPLICABLE":
            continue
        checked.append(expectation.effect)
        replay_document = replay_parsed.get(expectation.artifact_id)
        first_document = first_parsed.get(expectation.artifact_id)

        if expectation.comparison == "equal_across_bundles":
            first_found, first_value = (
                _resolve_pointer(first_document, expectation.json_pointer)
                if first_document is not None
                else (False, None)
            )
            replay_found, replay_value = (
                _resolve_pointer(replay_document, expectation.json_pointer)
                if replay_document is not None
                else (False, None)
            )
            if not first_found or not replay_found:
                unproven.append(expectation.effect)
            elif first_value != replay_value:
                violated.append(expectation.effect)
            else:
                proven_absent.append(expectation.effect)
        elif expectation.comparison == "equals_expected":
            document = replay_document if replay_document is not None else first_document
            found, value = (
                _resolve_pointer(document, expectation.json_pointer)
                if document is not None
                else (False, None)
            )
            if not found:
                unproven.append(expectation.effect)
            elif value != expectation.expected_value:
                violated.append(expectation.effect)
            else:
                proven_absent.append(expectation.effect)
        else:  # absent
            document = replay_document if replay_document is not None else first_document
            found, value = (
                _resolve_pointer(document, expectation.json_pointer)
                if document is not None
                else (False, None)
            )
            if found and value not in (None, [], {}, ""):
                violated.append(expectation.effect)
            else:
                proven_absent.append(expectation.effect)

    duplicate_lifecycle_paths: list[str] = []
    for directory, first_children in {
        d: set(c) for d, c in first_inventory.lifecycle_effect_children.items()
    }.items():
        replay_children = set(replay_inventory.lifecycle_effect_children.get(directory, ()))
        for child in sorted(replay_children - first_children):
            duplicate_lifecycle_paths.append(f"{directory}/{child}")
    for directory, replay_only_children in replay_inventory.lifecycle_effect_children.items():
        if directory not in first_inventory.lifecycle_effect_children:
            for child in replay_only_children:
                path = f"{directory}/{child}"
                if path not in duplicate_lifecycle_paths:
                    duplicate_lifecycle_paths.append(path)
    if duplicate_lifecycle_paths and "duplicate_lifecycle_effect" not in violated:
        if "duplicate_lifecycle_effect" in checked:
            violated.append("duplicate_lifecycle_effect")
            if "duplicate_lifecycle_effect" in proven_absent:
                proven_absent.remove("duplicate_lifecycle_effect")

    def _tree_digest(artifact_id: str, parsed: dict[str, Any], pointer: str) -> str | None:
        document = parsed.get(artifact_id)
        if document is None:
            return None
        found, value = _resolve_pointer(document, pointer)
        return value if found and isinstance(value, str) else None

    readme_write = next((e for e in contract.product_effects if e.effect == "readme_write"), None)
    tree_change = next(
        (e for e in contract.product_effects if e.effect == "target_tree_change"), None
    )

    return ProductEffectDeltaV1(
        checked_effects=tuple(sorted(set(checked))),
        proven_absent=tuple(sorted(set(proven_absent))),
        unproven=tuple(sorted(set(unproven))),
        violated=tuple(sorted(set(violated))),
        target_readme_digest_first=(
            _tree_digest(readme_write.artifact_id, first_parsed, readme_write.json_pointer)
            if readme_write is not None
            else None
        ),
        target_readme_digest_replay=(
            _tree_digest(readme_write.artifact_id, replay_parsed, readme_write.json_pointer)
            if readme_write is not None
            else None
        ),
        target_tree_digest_first=(
            _tree_digest(tree_change.artifact_id, first_parsed, tree_change.json_pointer)
            if tree_change is not None
            else None
        ),
        target_tree_digest_replay=(
            _tree_digest(tree_change.artifact_id, replay_parsed, tree_change.json_pointer)
            if tree_change is not None
            else None
        ),
        duplicate_lifecycle_paths=tuple(sorted(set(duplicate_lifecycle_paths))),
        delta_digest=canonical_json_sha256(
            {
                "proven_absent": sorted(set(proven_absent)),
                "unproven": sorted(set(unproven)),
                "violated": sorted(set(violated)),
                "duplicate": sorted(set(duplicate_lifecycle_paths)),
            }
        ),
    )


# ---- drift classification ----


def _earliest_affected_stage(findings: tuple[ReplayDriftFindingV1, ...]) -> ReplayStageV1 | None:
    if not findings:
        return None
    return min((finding.stage for finding in findings), key=STAGE_ORDER.__getitem__)


# ---- public entrypoint ----


def _empty_proof(
    contract: ReplayAttestationContractV1, *, checks: dict[str, bool], failures: list[str]
) -> CompleteTransactionNoOpProofV1:
    empty_identity_first = SealedTransactionIdentityV1(
        bundle_label="first", identity_digest=canonical_json_sha256({})
    )
    empty_identity_replay = SealedTransactionIdentityV1(
        bundle_label="replay", identity_digest=canonical_json_sha256({})
    )
    empty_inventory_first = ReplayArtifactInventoryV1(
        bundle_label="first",
        declared_count=len(contract.artifacts),
        present_count=0,
        file_count=0,
        total_bytes=0,
        walk_error="bundle_root_invalid",
        inventory_digest=canonical_json_sha256({"walk_error": "bundle_root_invalid"}),
    )
    empty_inventory_replay = empty_inventory_first.model_copy(update={"bundle_label": "replay"})
    empty_delta = ReplayArtifactDeltaV1(delta_digest=canonical_json_sha256({}))
    empty_provider = ProviderLedgerDeltaV1(
        ledger_load_error="bundle_root_invalid",
        accounting_certain=False,
        delta_digest=canonical_json_sha256({"error": "bundle_root_invalid"}),
    )
    empty_effect = ProductEffectDeltaV1(delta_digest=canonical_json_sha256({}))
    finding = ReplayDriftFindingV1(code="bundle_root_invalid", stage="SEALING", detail="")
    proof = CompleteTransactionNoOpProofV1(
        contract_id=contract.contract_id,
        org_repo=contract.org_repo,
        expected_source_revision=contract.expected_source_revision,
        contract_digest=_canonical_contract_digest(contract),
        passed=False,
        checks=checks,
        failures=tuple(failures),
        findings=(finding,),
        earliest_affected_stage="SEALING",
        affected_stages=("SEALING",),
        first_identity=empty_identity_first,
        replay_identity=empty_identity_replay,
        first_inventory=empty_inventory_first,
        replay_inventory=empty_inventory_replay,
        artifact_delta=empty_delta,
        provider_delta=empty_provider,
        effect_delta=empty_effect,
        proof_hash="0" * 64,
    )
    return _stamp_proof_hash(proof)


def _stamp_proof_hash(proof: CompleteTransactionNoOpProofV1) -> CompleteTransactionNoOpProofV1:
    payload = proof.model_dump(mode="json")
    payload.pop("proof_hash", None)
    return proof.model_copy(update={"proof_hash": canonical_json_sha256(payload)})


def canonical_proof_hash(proof: CompleteTransactionNoOpProofV1) -> str:
    payload = proof.model_dump(mode="json")
    payload.pop("proof_hash", None)
    return canonical_json_sha256(payload)


def attest_complete_transaction_noop(
    *,
    first_bundle_root: Path,
    replay_bundle_root: Path,
    expected_contract: ReplayAttestationContractV1,
) -> CompleteTransactionNoOpProofV1:
    """Independently verify, from sealed evidence alone, that a replay was a true no-op."""

    checks: dict[str, bool] = {}
    failures: list[str] = []

    def record(name: str, ok: bool, detail: str = "") -> bool:
        checks[name] = bool(ok)
        if not ok:
            failures.append(redact_secret_like_values(detail or name)[:400])
        return bool(ok)

    first_root_ok = first_bundle_root.is_dir() and not first_bundle_root.is_symlink()
    replay_root_ok = replay_bundle_root.is_dir() and not replay_bundle_root.is_symlink()
    record(
        "first_bundle_root_valid", first_root_ok, f"invalid first bundle root: {first_bundle_root}"
    )
    record(
        "replay_bundle_root_valid",
        replay_root_ok,
        f"invalid replay bundle root: {replay_bundle_root}",
    )
    distinct = (
        first_root_ok
        and replay_root_ok
        and first_bundle_root.resolve() != replay_bundle_root.resolve()
    )
    if first_root_ok and replay_root_ok:
        record("distinct_bundle_roots", distinct, "first and replay bundle roots must be distinct")
    if not (first_root_ok and replay_root_ok and distinct):
        return _empty_proof(expected_contract, checks=checks, failures=failures)

    first_inventory, first_parsed, _first_paths = _build_inventory(
        first_bundle_root, expected_contract, label="first", scopes=("both", "first_only")
    )
    replay_inventory, replay_parsed, _replay_paths = _build_inventory(
        replay_bundle_root, expected_contract, label="replay", scopes=("both", "replay_only")
    )
    record(
        "first_inventory_walkable",
        first_inventory.walk_error is None,
        str(first_inventory.walk_error),
    )
    record(
        "replay_inventory_walkable",
        replay_inventory.walk_error is None,
        str(replay_inventory.walk_error),
    )
    record(
        "inventory_bounds_respected",
        first_inventory.walk_error != "inventory_bounds_exceeded"
        and replay_inventory.walk_error != "inventory_bounds_exceeded",
    )
    record(
        "no_escaping_symlinks",
        not first_inventory.unsafe_paths and not replay_inventory.unsafe_paths,
        f"unsafe paths: first={first_inventory.unsafe_paths} "
        f"replay={replay_inventory.unsafe_paths}",
    )
    record(
        "no_duplicate_declared_paths",
        not first_inventory.duplicate_declared_paths
        and not replay_inventory.duplicate_declared_paths,
        "duplicate self-declared inventory path",
    )
    record(
        "required_artifacts_present",
        not first_inventory.missing_required and not replay_inventory.missing_required,
        f"missing required: first={first_inventory.missing_required} "
        f"replay={replay_inventory.missing_required}",
    )
    record(
        "artifact_hashes_recomputed",
        not first_inventory.hash_declaration_mismatches
        and not replay_inventory.hash_declaration_mismatches,
        "recomputed hash disagrees with bundle self-declaration",
    )
    record(
        "bundle_self_declarations_match",
        not first_inventory.orphan_inventory_paths and not replay_inventory.orphan_inventory_paths,
        "sha256sums.txt lists a file that no longer exists",
    )
    record(
        "inventory_covers_every_file",
        not first_inventory.uncovered_paths and not replay_inventory.uncovered_paths,
        "a file on disk is not covered by sha256sums.txt",
    )
    record(
        "no_undeclared_semantic_artifacts",
        not first_inventory.undeclared_semantic_paths
        and not replay_inventory.undeclared_semantic_paths,
        f"undeclared: first={first_inventory.undeclared_semantic_paths} "
        f"replay={replay_inventory.undeclared_semantic_paths}",
    )
    record(
        "artifact_schemas_valid",
        not first_inventory.schema_invalid and not replay_inventory.schema_invalid,
        f"schema invalid: first={first_inventory.schema_invalid} "
        f"replay={replay_inventory.schema_invalid}",
    )

    first_identity = _extract_identity(expected_contract, first_parsed, label="first")
    replay_identity = _extract_identity(expected_contract, replay_parsed, label="replay")
    record(
        "repository_identity_matches_contract",
        first_identity.org_repo == expected_contract.org_repo
        and replay_identity.org_repo == expected_contract.org_repo,
        "bundle org_repo does not match contract",
    )
    record(
        "source_revision_matches_contract",
        first_identity.source_revision == expected_contract.expected_source_revision
        and replay_identity.source_revision == expected_contract.expected_source_revision,
        "bundle source_revision does not match contract",
    )
    first_bad_identity = (
        first_identity.missing_required_components + first_identity.malformed_components
    )
    replay_bad_identity = (
        replay_identity.missing_required_components + replay_identity.malformed_components
    )
    record(
        "required_identity_components_resolved",
        not first_bad_identity and not replay_bad_identity,
        f"missing/malformed identity: first={first_bad_identity} replay={replay_bad_identity}",
    )

    findings: list[ReplayDriftFindingV1] = []
    for component in sorted(
        set(first_identity.component_digests) & set(replay_identity.component_digests)
    ):
        if (
            first_identity.component_digests[component]
            != replay_identity.component_digests[component]
        ):
            findings.append(
                ReplayDriftFindingV1(
                    code=f"identity_drift:{component}",
                    stage=_COMPONENT_STAGE[component],  # type: ignore[index]
                    detail=f"identity component drifted: {component}",
                )
            )
    record(
        "identity_components_match_across_bundles",
        not findings,
        "identity component drift detected",
    )

    first_walk = _walk_bundle(
        first_bundle_root,
        max_files=expected_contract.max_inventory_files,
        max_bytes=expected_contract.max_inventory_bytes,
    )
    replay_walk = _walk_bundle(
        replay_bundle_root,
        max_files=expected_contract.max_inventory_files,
        max_bytes=expected_contract.max_inventory_bytes,
    )
    artifact_delta = _build_artifact_delta(
        expected_contract,
        first_parsed,
        replay_parsed,
        first_inventory,
        replay_inventory,
        first_walk,
        replay_walk,
    )
    record(
        "promised_outputs_byte_identical",
        not artifact_delta.promised_byte_identity_failures,
        "promised byte-identical artifacts differ: "
        f"{artifact_delta.promised_byte_identity_failures}",
    )
    record(
        "non_promised_artifacts_semantically_identical",
        not artifact_delta.changed_artifact_ids,
        f"artifacts changed beyond allowed differences: {artifact_delta.changed_artifact_ids}",
    )
    for artifact_id in artifact_delta.changed_artifact_ids:
        artifact = next(a for a in expected_contract.artifacts if a.artifact_id == artifact_id)
        findings.append(
            ReplayDriftFindingV1(
                code="semantic_artifact_changed",
                stage=artifact.stage,
                detail=f"artifact changed: {artifact_id}",
            )
        )
    only_allowed = not artifact_delta.first_only_paths and not artifact_delta.replay_only_paths
    record(
        "only_allowed_differences_observed",
        only_allowed,
        f"unmatched file sets: first_only={artifact_delta.first_only_paths} "
        f"replay_only={artifact_delta.replay_only_paths}",
    )
    if not only_allowed:
        findings.append(
            ReplayDriftFindingV1(
                code="undeclared_difference", stage="SEALING", detail="bundle file sets differ"
            )
        )

    provider_delta = _build_provider_delta(
        expected_contract, first_bundle_root, replay_bundle_root, first_parsed, replay_parsed
    )
    record(
        "ledger_files_present",
        provider_delta.ledger_load_error is None,
        str(provider_delta.ledger_load_error),
    )
    record(
        "ledger_records_parse",
        provider_delta.ledger_load_error is None,
        str(provider_delta.ledger_load_error),
    )
    record(
        "ledger_accounting_status_exact",
        provider_delta.first_declared_status == "EXACT"
        and provider_delta.replay_declared_status == "EXACT",
        f"non-EXACT accounting: first={provider_delta.first_declared_status} "
        f"replay={provider_delta.replay_declared_status}",
    )
    record(
        "declared_accounting_matches_recomputed",
        provider_delta.declared_accounting_consistent,
        "declared accounting fields disagree with independently recomputed ledger",
    )
    record(
        "ledger_boundaries_coherent",
        provider_delta.ledger_superset_ok
        and provider_delta.ledger_temporal_ok
        and provider_delta.ledger_scope_ok
        and not provider_delta.replay_disallowed_dispositions,
        "replay ledger is not a coherent, temporally-consistent superset of the first ledger",
    )
    record(
        "no_unclassified_provider_jobs",
        not provider_delta.replay_unclassified_jobs,
        f"unclassified provider job(s): {provider_delta.replay_unclassified_jobs}",
    )
    record(
        "no_reused_call_drift",
        not provider_delta.model_drift_axes and not provider_delta.sampling_drift_axes,
        f"model_drift={provider_delta.model_drift_axes} "
        f"sampling_drift={provider_delta.sampling_drift_axes}",
    )
    for axis in provider_delta.model_drift_axes:
        findings.append(
            ReplayDriftFindingV1(
                code=f"model_drift:{axis}",
                stage="AUTHORING" if axis == "authoring" else "REVIEW",
                detail=f"reused ledger record's model changed for axis {axis}",
            )
        )
    for axis in provider_delta.sampling_drift_axes:
        findings.append(
            ReplayDriftFindingV1(
                code=f"sampling_drift:{axis}",
                stage="AUTHORING" if axis == "authoring" else "REVIEW",
                detail=f"reused ledger record's request changed for axis {axis}",
            )
        )
    if provider_delta.accounting_certain:
        record("replay_provider_calls_zero", provider_delta.first_provider_call_count is not None)
        for axis, count, code in (
            ("authoring", provider_delta.replay_authoring_calls, "AUTHORING"),
            ("factual_review", provider_delta.replay_factual_review_calls, "REVIEW"),
            ("visitor_review", provider_delta.replay_visitor_review_calls, "REVIEW"),
            ("repair", provider_delta.replay_repair_calls, "REVIEW"),
        ):
            ok = count == 0
            record(
                f"replay_{axis}_calls_zero", ok, f"replay made {count} new {axis} provider call(s)"
            )
            if not ok:
                findings.append(
                    ReplayDriftFindingV1(
                        code=f"new_provider_call:{axis}",
                        stage=code,  # type: ignore[arg-type]
                        detail=f"replay made {count} new {axis} provider call(s)",
                    )
                )
    else:
        for axis in ("authoring", "factual_review", "visitor_review", "repair"):
            record(f"replay_{axis}_calls_zero", False, "provider accounting is not certain")
        findings.append(
            ReplayDriftFindingV1(
                code="provider_ledger_missing",
                stage="SEALING",
                detail="ledger accounting is not certain",
            )
        )
    if provider_delta.replay_unclassified_jobs:
        findings.append(
            ReplayDriftFindingV1(
                code="unmapped_job",
                stage="AUTHORING",
                detail=f"unmapped job(s): {provider_delta.replay_unclassified_jobs}",
            )
        )
    if provider_delta.declared_accounting_consistent is False:
        findings.append(
            ReplayDriftFindingV1(
                code="provider_accounting_not_exact",
                stage="SEALING",
                detail="declared accounting inconsistent",
            )
        )
    if not provider_delta.accounting_certain and provider_delta.ledger_load_error:
        findings.append(
            ReplayDriftFindingV1(
                code="provider_accounting_not_exact",
                stage="SEALING",
                detail=str(provider_delta.ledger_load_error),
            )
        )

    effect_delta = _build_effect_delta(
        expected_contract, first_parsed, replay_parsed, first_inventory, replay_inventory
    )
    record(
        "product_effects_proven_absent",
        not effect_delta.violated and not effect_delta.unproven,
        f"effects violated={effect_delta.violated} unproven={effect_delta.unproven}",
    )
    record(
        "no_duplicate_lifecycle_effect",
        "duplicate_lifecycle_effect" not in effect_delta.violated,
        f"duplicate lifecycle paths: {effect_delta.duplicate_lifecycle_paths}",
    )
    record(
        "target_tree_unchanged",
        effect_delta.target_tree_digest_first == effect_delta.target_tree_digest_replay
        or effect_delta.target_tree_digest_first is None
        or effect_delta.target_tree_digest_replay is None,
        "target tree digest changed between transactions",
    )
    for effect in effect_delta.violated:
        findings.append(
            ReplayDriftFindingV1(
                code="product_effect_observed", stage="EFFECTS", detail=f"effect observed: {effect}"
            )
        )
    for effect in effect_delta.unproven:
        findings.append(
            ReplayDriftFindingV1(
                code="effect_evidence_missing",
                stage="EFFECTS",
                detail=f"effect evidence missing: {effect}",
            )
        )

    for label, unsafe in (
        ("first", first_inventory.unsafe_paths),
        ("replay", replay_inventory.unsafe_paths),
    ):
        for path in unsafe:
            findings.append(
                ReplayDriftFindingV1(
                    code="escaping_symlink", stage="SEALING", detail=f"{label}: {path}"
                )
            )
    for label, missing in (
        ("first", first_inventory.missing_required),
        ("replay", replay_inventory.missing_required),
    ):
        for artifact_id in missing:
            findings.append(
                ReplayDriftFindingV1(
                    code=f"missing_required_artifact:{artifact_id}",
                    stage="SEALING",
                    detail=f"{label}: {artifact_id}",
                )
            )
    for label, undeclared in (
        ("first", first_inventory.undeclared_semantic_paths),
        ("replay", replay_inventory.undeclared_semantic_paths),
    ):
        for path in undeclared:
            findings.append(
                ReplayDriftFindingV1(
                    code=f"unexpected_semantic_artifact:{path}",
                    stage="SEALING",
                    detail=f"{label}: {path}",
                )
            )
    for label, dup in (
        ("first", first_inventory.duplicate_declared_paths),
        ("replay", replay_inventory.duplicate_declared_paths),
    ):
        for path in dup:
            findings.append(
                ReplayDriftFindingV1(
                    code="duplicate_declaration", stage="SEALING", detail=f"{label}: {path}"
                )
            )
    for path in artifact_delta.promised_byte_identity_failures:
        artifact = next(a for a in expected_contract.artifacts if a.artifact_id == path)
        findings.append(
            ReplayDriftFindingV1(
                code="artifact_hash_mismatch",
                stage=artifact.stage,
                detail=f"byte identity failed: {path}",
            )
        )
    for label, mismatches in (
        ("first", first_inventory.hash_declaration_mismatches),
        ("replay", replay_inventory.hash_declaration_mismatches),
    ):
        for path in mismatches:
            findings.append(
                ReplayDriftFindingV1(
                    code="artifact_hash_mismatch", stage="SEALING", detail=f"{label}: {path}"
                )
            )
    for label, invalid in (
        ("first", first_inventory.schema_invalid),
        ("replay", replay_inventory.schema_invalid),
    ):
        for artifact_id in invalid:
            findings.append(
                ReplayDriftFindingV1(
                    code="inventory_incomplete", stage="SEALING", detail=f"{label}: {artifact_id}"
                )
            )

    earliest = _earliest_affected_stage(tuple(findings))
    affected_stages = tuple(sorted({f.stage for f in findings}, key=STAGE_ORDER.__getitem__))
    record("no_drift_detected", not findings, f"{len(findings)} drift finding(s)")

    passed = (
        not failures
        and all(checks.values())
        and provider_delta.accounting_certain
        and not effect_delta.unproven
        and not effect_delta.violated
    )

    proof = CompleteTransactionNoOpProofV1(
        contract_id=expected_contract.contract_id,
        org_repo=expected_contract.org_repo,
        expected_source_revision=expected_contract.expected_source_revision,
        contract_digest=_canonical_contract_digest(expected_contract),
        passed=passed,
        checks=checks,
        failures=tuple(failures),
        findings=tuple(findings),
        earliest_affected_stage=earliest,
        affected_stages=affected_stages,
        first_identity=first_identity,
        replay_identity=replay_identity,
        first_inventory=first_inventory,
        replay_inventory=replay_inventory,
        artifact_delta=artifact_delta,
        provider_delta=provider_delta,
        effect_delta=effect_delta,
        proof_hash="0" * 64,
    )
    return _stamp_proof_hash(proof)


__all__ = [
    "ATTESTOR_IDENTITY",
    "STAGE_ORDER",
    "ALLOWED_DIFFERENCE_KEYS",
    "KNOWN_PROVIDER_JOB_AXES",
    "HashModeV1",
    "RequirementLevelV1",
    "ArtifactKindV1",
    "BundleScopeV1",
    "ReplayStageV1",
    "IdentityComponentV1",
    "ProviderCallAxisV1",
    "ProductEffectV1",
    "DeclaredArtifactV1",
    "IdentityBindingSpecV1",
    "LedgerDeclarationSpecV1",
    "ProviderProofContractV1",
    "ProductEffectExpectationV1",
    "ReplayAttestationContractV1",
    "SealedTransactionIdentityV1",
    "ReplayArtifactInventoryV1",
    "ReplayArtifactDeltaV1",
    "ProviderLedgerDeltaV1",
    "ProductEffectDeltaV1",
    "ReplayDriftFindingV1",
    "CompleteTransactionNoOpProofV1",
    "canonical_json_sha256",
    "canonical_proof_hash",
    "attest_complete_transaction_noop",
]
