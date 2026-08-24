"""Declarative contract models for sealed transaction replay attestation."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from readme_agent.verification.sealed_transaction_replay_vocabulary import (
    _CONTROL_CHARS,
    _DRIVE_LETTER,
    _HEX_DIGEST,
    _MANDATORY_REQUIRED_COMPONENTS,
    DEFAULT_LIFECYCLE_EFFECT_DIRECTORIES,
    DEFAULT_NON_SEMANTIC_BASENAMES,
    DEFAULT_NON_SEMANTIC_DIRECTORIES,
    DEFAULT_NON_SEMANTIC_PATHS,
    DEFAULT_NON_SEMANTIC_SUFFIXES,
    EXPECTED_LIFECYCLE_DELTA_SCOPES,
    ArtifactKindV1,
    BundleScopeV1,
    HashModeV1,
    IdentityComponentV1,
    ProductEffectV1,
    ProviderCallAxisV1,
    ReplayStageV1,
    RequirementLevelV1,
)


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
    lifecycle_effect_directories: tuple[str, ...] = tuple(
        sorted(DEFAULT_LIFECYCLE_EFFECT_DIRECTORIES)
    )

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

        scoped_artifacts = {
            artifact.relative_path: artifact.scope
            for artifact in self.artifacts
            if artifact.scope != "both"
        }
        invalid_scoped_artifacts = {
            relative_path: scope
            for relative_path, scope in scoped_artifacts.items()
            if EXPECTED_LIFECYCLE_DELTA_SCOPES.get(relative_path) != scope
        }
        if invalid_scoped_artifacts:
            raise ValueError(
                "artifact scope is not an explicitly allowed lifecycle delta: "
                f"{sorted(invalid_scoped_artifacts.items())}"
            )

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
