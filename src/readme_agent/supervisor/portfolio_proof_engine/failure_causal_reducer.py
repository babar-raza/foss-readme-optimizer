"""Read-only fleet-wide reduction of FAILED proof-stage observations into causal clusters.

Pure and stateless: `reduce_fleet_failures` never writes a receipt, never retries, never transitions
lifecycle state, and never promotes anything -- it only groups already-collected
`ProofStageReceiptV1`-backed failures by shared cause, classifies each group, and ranks them so a
repair effort can fix one shared cause instead of rerunning every affected repository. Distinct from
`portfolio_scheduler/reducer.py` ("Sole promoter for sealed stage artifacts, receipts, and lifecycle
state" -- a *mutating*, single-attempt promotion reducer): this module shares no type or
responsibility with it, and reduces *many* observations rather than promoting one sealed attempt.
Never a second scoring system either -- classification and priority are derived structurally from
caller-supplied evidence, never re-derived from rubric/review internals.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import datetime
from typing import Any, Literal, get_args

from pydantic import BaseModel, ConfigDict, Field, field_validator

from readme_agent.evidence.redaction import redact_secret_like_values
from readme_agent.supervisor.portfolio_proof_engine.contracts import (
    STAGE_ORDER,
    ProofStageReceiptV1,
    ProofStageV1,
)
from readme_agent.supervisor.portfolio_scheduler.contracts import canonical_sha256, utc_now_iso
from readme_agent.supervisor.task import BlockedCategory

# --- Literal aliases -----------------------------------------------------------------------

FailureClassificationV1 = Literal[
    "shared_code_defect",
    "ecosystem_adapter_defect",
    "repository_evidence_defect",
    "infra_external",
    "transient_provider",
    "corrupt_or_stale_evidence",
    "input_contract_mismatch",
    "candidate_specific_rejection",
    "unknown",
]

FingerprintLevelV1 = Literal[
    "corrupt_or_stale_evidence",
    "error_gate_check_code",
    "stage_causal_component",
    "structured_semantic_args",
    "ecosystem_toolchain_provider",
    "dependency_fingerprint",
    "normalized_diagnostic",
]

ConfidenceV1 = Literal["high", "medium", "low"]

ReproducibilityVerdictV1 = Literal[
    "RENDER_REPRODUCIBLE",
    "RENDER_REPRODUCIBILITY_FAILED",
    "NO_OP_PROVEN",
    "TRANSACTION_NO_OP_PROVEN",
    "UNKNOWN",
]

EvidenceCompletenessV1 = Literal["complete", "partial", "none"]

RecommendedRepairScopeV1 = Literal[
    "shared_module",
    "ecosystem_adapter",
    "single_repository_evidence",
    "external_dependency_wait",
    "provider_retry_after_change",
    "manual_classification_required",
]

# --- constants -------------------------------------------------------------------------------

# Deliberately conservative and tunable: motivated by a real 10-member, zero-structured-signal
# `validation_rejected` bucket found in this repo's own PF-01 evidence. Under-tuning (too high)
# risks a false-confident opaque merge slipping through; over-tuning (too low) risks needlessly
# demoting small, plausibly-real clusters to `unknown`.
_OPAQUE_BULK_THRESHOLD = 5

_INPUT_CONTRACT_MARKERS = frozenset(
    {
        "validation_rejected",
        "schema_mismatch",
        "contract_hash_mismatch",
        "facts_hash_mismatch",
        "candidate_hash_mismatch",
    }
)

_INFRA_EXCEPTION_MARKERS = ("LLMInfrastructureError",)
_TRANSIENT_PROVIDER_EXCEPTION_MARKERS = (
    "LLMTruncatedResponseError",
    "TimeoutError",
    "RateLimitError",
    "ProviderTimeoutError",
)

# Redeclared locally rather than imported: dashboard.py's equivalent stage-family sets are
# leading-underscore private, and AGENTS.md forbids depending on a sibling module's private seam.
_FACTS_OR_INPUT_STAGES: frozenset[str] = frozenset(
    {
        "INTAKE",
        "SOURCE_BOUND",
        "FACTS_READY",
        "SECTION_PACKETS_READY",
        "SECTIONS_AUTHORED",
        "BLOCKED_INPUT",
    }
)
_CANDIDATE_OR_REVIEW_STAGES: frozenset[str] = frozenset(
    {
        "CANDIDATE_ASSEMBLED",
        "DETERMINISTIC_VALIDATED",
        "FACTUAL_REVIEWED",
        "VISITOR_REVIEWED",
        "RUBRIC_SCORED",
        "ACCEPTED",
    }
)

# The fleet-shared subset of local_poc_cache.py's dependency-fingerprint key set: excludes
# per-repo-identity keys (source_revision, content_assurance, fact_acceptance_component_hashes,
# candidate_stage_dependency_key) so tier 5 never merges unrelated repos on a purely-identity key.
_FLEET_SHARED_DEPENDENCY_KEYS = frozenset(
    {
        "fact_acceptance_contract_hash",
        "local_verification_contract_hash",
        "prompt_registry_content_hash",
        "template_hash",
        "composition_prompt_hash",
        "reviewer_standard_hash",
        "control_plane_fingerprint",
    }
)

_CLEAN_REPRODUCIBILITY_VERDICTS: frozenset[str] = frozenset(
    {"NO_OP_PROVEN", "TRANSACTION_NO_OP_PROVEN", "RENDER_REPRODUCIBLE"}
)

_STRUCTURED_TIERS: frozenset[str] = frozenset(
    {"error_gate_check_code", "stage_causal_component", "structured_semantic_args"}
)
_UNSTRUCTURED_SIGNAL_TIERS: frozenset[str] = frozenset(
    {"ecosystem_toolchain_provider", "dependency_fingerprint", "normalized_diagnostic"}
)

_ACTIONABILITY_RANK: dict[str, int] = {
    "shared_code_defect": 0,
    "ecosystem_adapter_defect": 0,
    "input_contract_mismatch": 0,
    "repository_evidence_defect": 1,
    "candidate_specific_rejection": 1,
    "transient_provider": 2,
    "infra_external": 3,
    "corrupt_or_stale_evidence": 4,
    "unknown": 4,
}

_TIER_CONFIDENCE: dict[str, ConfidenceV1] = {
    "corrupt_or_stale_evidence": "low",
    "error_gate_check_code": "high",
    "stage_causal_component": "high",
    "structured_semantic_args": "high",
    "ecosystem_toolchain_provider": "medium",
    "dependency_fingerprint": "medium",
    "normalized_diagnostic": "low",
}

_TIER_REASONS: dict[str, tuple[str, str]] = {
    "corrupt_or_stale_evidence": (
        "all corrupt/stale observations share one fleet-wide cluster regardless of stage or repo",
        "any observation that passed the soft-corruption plausibility check was excluded",
    ),
    "error_gate_check_code": (
        "members share an identical structured_error_code/gate_or_check_id at the same stage",
        "observations with a different code/gate id, or at a different stage, were excluded "
        "even if their free-text diagnostic looked similar",
    ),
    "stage_causal_component": (
        "members share an identical causal_component at the same stage, with no structured code",
        "observations with a different causal_component, a structured code, or a different "
        "stage were excluded",
    ),
    "structured_semantic_args": (
        "members share identical structured_error_args at the same stage, with no code/component",
        "observations with different structured_error_args, a code/component, or a different "
        "stage were excluded",
    ),
    "ecosystem_toolchain_provider": (
        "members share ecosystem/blocked_category/exception_type/pipeline_source at the same "
        "stage, with no structured code/component/args",
        "observations differing in any of those fields, or carrying any structured signal, "
        "were excluded",
    ),
    "dependency_fingerprint": (
        "members share the same set of changed fleet-shared dependency keys at the same stage, "
        "with no other structured signal",
        "observations with a different changed-key set, any structured signal, or a different "
        "stage were excluded",
    ),
    "normalized_diagnostic": (
        "members share an identical normalized free-text diagnostic at the same stage -- the "
        "last-resort fallback used only when no structured signal exists",
        "observations whose normalized diagnostic differs even slightly, or that carry any "
        "structured signal, were excluded",
    ),
}

_NORMALIZE_MAX_LEN = 500
_REASON_MAX_LEN = 500

_TIMESTAMP_RE = re.compile(
    r"\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?\b"
)
_UUID_RE = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.IGNORECASE
)
_RUN_ID_RE = re.compile(r"\brun-[0-9a-f-]{8,}\b", re.IGNORECASE)
_TMPDIR_RE = re.compile(r"(?:/tmp|/var/folders|[A-Za-z]:\\Users\\[^\\]+\\AppData\\Local\\Temp)\S*")
_HOMEDIR_RE = re.compile(r"(?:/home/[^/\s]+|/Users/[^/\s]+)")
_ATTEMPT_RE = re.compile(r"\b(?:attempt|retry|try)\s*#?\d+\b", re.IGNORECASE)
_DURATION_RE = re.compile(r"\b\d+(?:\.\d+)?s\b")
_WHITESPACE_RE = re.compile(r"\s+")


# --- models ------------------------------------------------------------------------------------


class FailureObservationV1(BaseModel):
    """One repository-level FAILED proof-stage observation, plus causal-identity context the
    embedded receipt alone does not carry. Embeds `ProofStageReceiptV1` wholesale rather than
    re-declaring org_repo/stage/status/failure_reason/hashes -- never a second receipt model."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    receipt: ProofStageReceiptV1
    family: str | None = None
    blocked_category: BlockedCategory | None = None
    causal_component: str | None = None
    structured_error_code: str | None = None
    gate_or_check_id: str | None = None
    structured_error_args: tuple[tuple[str, str], ...] = ()
    dependency_fingerprint: dict[str, Any] | None = None
    exception_type: str | None = None
    evidence_ref: str | None = None
    observed_at: str | None = None
    last_observed_at: str | None = None
    attempt_count: int = Field(default=1, ge=1)
    pipeline_source: str | None = None
    known_reproducibility_verdict: ReproducibilityVerdictV1 | None = None

    @field_validator("receipt")
    @classmethod
    def _receipt_must_be_failed(cls, value: ProofStageReceiptV1) -> ProofStageReceiptV1:
        if value.status != "FAILED":
            raise ValueError("FailureObservationV1 requires a FAILED receipt")
        return value

    @field_validator("structured_error_args")
    @classmethod
    def _args_sorted_unique(cls, value: tuple[tuple[str, str], ...]) -> tuple[tuple[str, str], ...]:
        keys = [key for key, _ in value]
        if keys != sorted(keys):
            raise ValueError("structured_error_args keys must be sorted")
        if len(keys) != len(set(keys)):
            raise ValueError("structured_error_args keys must be unique")
        return value

    @field_validator("evidence_ref")
    @classmethod
    def _evidence_ref_no_traversal(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.replace("\\", "/")
        first_segment = normalized.split("/")[0]
        if normalized.startswith("/") or ":" in first_segment:
            raise ValueError("evidence_ref must be a relative path")
        if any(part == ".." for part in normalized.split("/")):
            raise ValueError("evidence_ref must not contain '..' segments")
        return value

    @property
    def org_repo(self) -> str:
        return self.receipt.org_repo

    @property
    def stage(self) -> ProofStageV1:
        return self.receipt.stage

    @property
    def ecosystem(self) -> str | None:
        return self.receipt.ecosystem


class DependencyFingerprintSnapshotV1(BaseModel):
    """Caller-supplied 'current' dependency fingerprints, keyed by org_repo. Used only to diff
    against an observation's own captured `dependency_fingerprint` -- never computed here, since
    this module has no filesystem/network access and stays pure."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    captured_at: str = Field(default_factory=utc_now_iso)
    by_org_repo: dict[str, dict[str, Any]] = Field(default_factory=dict)
    global_dependencies: dict[str, Any] | None = None

    def current_for(self, org_repo: str) -> dict[str, Any]:
        merged: dict[str, Any] = dict(self.global_dependencies or {})
        merged.update(self.by_org_repo.get(org_repo, {}))
        return merged


class CausalFailureFingerprintV1(BaseModel):
    """The clustering key for one observation, built by the first-available-wins cascade in
    `_build_fingerprint`. Structured fields are always copied here regardless of which tier fired,
    so classification has full visibility even when a field wasn't part of the hash."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    level: FingerprintLevelV1
    stage: ProofStageV1
    causal_component: str | None = None
    structured_error_code: str | None = None
    gate_or_check_id: str | None = None
    structured_error_args: tuple[tuple[str, str], ...] = ()
    ecosystem: str | None = None
    blocked_category: BlockedCategory | None = None
    exception_type: str | None = None
    pipeline_source: str | None = None
    dependency_changed_keys: tuple[str, ...] = ()
    normalized_diagnostic: str | None = None
    fingerprint_hash: str


class RepresentativeProofCaseV1(BaseModel):
    """One selected proof case: an observation chosen to stand in for its cluster (or, for
    `unknown` clusters, every member individually)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    org_repo: str
    observation: FailureObservationV1
    selection_reason: str = Field(max_length=_REASON_MAX_LEN)
    evidence_completeness_score: int = Field(ge=0)


class CausalFailureClusterV1(BaseModel):
    """One causal cluster: a group of observations sharing one `CausalFailureFingerprintV1`,
    classified, scored, and ranked."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    cluster_id: str
    fingerprint: CausalFailureFingerprintV1
    classification: FailureClassificationV1
    classification_reason: str = Field(max_length=_REASON_MAX_LEN)
    confidence: ConfidenceV1
    member_org_repos: tuple[str, ...]
    member_count: int = Field(ge=1)
    distinct_ecosystems: tuple[str, ...]
    distinct_pipeline_sources: tuple[str, ...]
    earliest_shared_stage: ProofStageV1
    earliest_shared_stage_rank: int = Field(ge=0)
    evidence_completeness: EvidenceCompletenessV1
    changed_dependency_keys: tuple[str, ...]
    dependency_changed: bool
    repos_blocked: int = Field(ge=1)
    single_repair_multi_repo: bool
    deterministic: bool
    minimal_proof_possible: bool
    classification_actionability_rank: int = Field(ge=0, le=4)
    recommended_repair_scope: RecommendedRepairScopeV1
    required_closure_evidence: str = Field(max_length=_REASON_MAX_LEN)
    inclusion_reason: str = Field(max_length=_REASON_MAX_LEN)
    exclusion_reason: str = Field(max_length=_REASON_MAX_LEN)
    estimated_retries_avoided: int = Field(ge=0)
    priority_rank: int = Field(ge=0)
    representative: RepresentativeProofCaseV1


class FleetCausalReductionV1(BaseModel):
    """The top-level reduction result. `clusters` tuple order IS the priority ranking."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    generated_at: str = Field(default_factory=utc_now_iso)
    input_observation_count: int = Field(ge=0)
    input_org_repo_count: int = Field(ge=0)
    clusters: tuple[CausalFailureClusterV1, ...]
    minimal_proof_cohort: tuple[RepresentativeProofCaseV1, ...]
    unresolved_org_repos: tuple[str, ...]
    classification_counts: dict[str, int]
    total_estimated_retries_avoided: int = Field(ge=0)


# --- normalization -------------------------------------------------------------------------


def _normalize_diagnostic_text(text: str) -> str:
    """Narrow, last-resort normalizer. Strips only volatile noise (timestamps, run/UUID-shaped
    IDs, temp/home-dir prefixes, attempt counters, bare durations) -- never error/gate codes,
    stage names, exception/module/function identifiers, ecosystem strings, or hex hashes, since
    none of those match these patterns in the first place."""

    result = redact_secret_like_values(text)
    result = result.replace("\r\n", "\n").replace("\r", "\n")
    result = _TIMESTAMP_RE.sub("<TIMESTAMP>", result)
    result = _UUID_RE.sub("<UUID>", result)
    result = _RUN_ID_RE.sub("<RUN_ID>", result)
    result = _TMPDIR_RE.sub("<TMPDIR>", result)
    result = _HOMEDIR_RE.sub("<HOMEDIR>", result)
    result = _ATTEMPT_RE.sub("<ATTEMPT>", result)
    result = _DURATION_RE.sub("<DURATION>", result)
    result = _WHITESPACE_RE.sub(" ", result).strip()
    return result[:_NORMALIZE_MAX_LEN]


def _is_soft_corrupt(observation: FailureObservationV1) -> bool:
    """Semantically-implausible-but-shape-valid evidence Pydantic can't catch: an unparseable
    timestamp, or a `dependency_fingerprint` present but empty (wired up but produced nothing)."""

    timestamp = observation.observed_at or observation.receipt.generated_at
    try:
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return True
    if observation.dependency_fingerprint is not None and not observation.dependency_fingerprint:
        return True
    return False


# --- fingerprint cascade -------------------------------------------------------------------


def _fleet_shared_dependency_changed_keys(
    observation: FailureObservationV1, snapshot: DependencyFingerprintSnapshotV1 | None
) -> tuple[str, ...]:
    if observation.dependency_fingerprint is None or snapshot is None:
        return ()
    current = snapshot.current_for(observation.org_repo)
    if not current:
        return ()
    observed = observation.dependency_fingerprint
    return tuple(
        sorted(
            key for key in _FLEET_SHARED_DEPENDENCY_KEYS if observed.get(key) != current.get(key)
        )
    )


def _full_dependency_changed_keys(
    observation: FailureObservationV1, snapshot: DependencyFingerprintSnapshotV1 | None
) -> tuple[str, ...]:
    """Mirrors retry_policy.py's own union-of-sorted-keys diff exactly, over the full key set
    (not just the fleet-shared subset) -- used for the cluster-level `dependency_changed` signal."""

    if observation.dependency_fingerprint is None or snapshot is None:
        return ()
    current = snapshot.current_for(observation.org_repo)
    if not current:
        return ()
    observed = observation.dependency_fingerprint
    keys = set(observed) | set(current)
    return tuple(sorted(key for key in keys if observed.get(key) != current.get(key)))


def _build_fingerprint(
    observation: FailureObservationV1, dependency_snapshot: DependencyFingerprintSnapshotV1 | None
) -> CausalFailureFingerprintV1:
    stage = observation.stage
    mirrored: dict[str, Any] = {
        "stage": stage,
        "causal_component": observation.causal_component,
        "structured_error_code": observation.structured_error_code,
        "gate_or_check_id": observation.gate_or_check_id,
        "structured_error_args": observation.structured_error_args,
        "ecosystem": observation.ecosystem,
        "blocked_category": observation.blocked_category,
        "exception_type": observation.exception_type,
        "pipeline_source": observation.pipeline_source,
    }

    if _is_soft_corrupt(observation):
        payload: dict[str, Any] = {"level": "corrupt_or_stale_evidence"}
        return CausalFailureFingerprintV1(
            level="corrupt_or_stale_evidence",
            fingerprint_hash=canonical_sha256(payload),
            **mirrored,
        )

    if observation.structured_error_code is not None or observation.gate_or_check_id is not None:
        payload = {
            "level": "error_gate_check_code",
            "stage": stage,
            "structured_error_code": observation.structured_error_code,
            "gate_or_check_id": observation.gate_or_check_id,
        }
        return CausalFailureFingerprintV1(
            level="error_gate_check_code", fingerprint_hash=canonical_sha256(payload), **mirrored
        )

    if observation.causal_component is not None:
        payload = {
            "level": "stage_causal_component",
            "stage": stage,
            "causal_component": observation.causal_component,
        }
        return CausalFailureFingerprintV1(
            level="stage_causal_component", fingerprint_hash=canonical_sha256(payload), **mirrored
        )

    if observation.structured_error_args:
        payload = {
            "level": "structured_semantic_args",
            "stage": stage,
            "structured_error_args": [list(pair) for pair in observation.structured_error_args],
        }
        return CausalFailureFingerprintV1(
            level="structured_semantic_args",
            fingerprint_hash=canonical_sha256(payload),
            **mirrored,
        )

    if (
        observation.ecosystem is not None
        or observation.blocked_category is not None
        or observation.exception_type is not None
    ):
        payload = {
            "level": "ecosystem_toolchain_provider",
            "stage": stage,
            "ecosystem": observation.ecosystem,
            "blocked_category": observation.blocked_category,
            "exception_type": observation.exception_type,
            "pipeline_source": observation.pipeline_source,
        }
        return CausalFailureFingerprintV1(
            level="ecosystem_toolchain_provider",
            fingerprint_hash=canonical_sha256(payload),
            **mirrored,
        )

    changed_keys = _fleet_shared_dependency_changed_keys(observation, dependency_snapshot)
    if changed_keys:
        payload = {
            "level": "dependency_fingerprint",
            "stage": stage,
            "changed_dependencies": list(changed_keys),
            "pipeline_source": observation.pipeline_source,
        }
        return CausalFailureFingerprintV1(
            level="dependency_fingerprint",
            dependency_changed_keys=changed_keys,
            fingerprint_hash=canonical_sha256(payload),
            **mirrored,
        )

    normalized = _normalize_diagnostic_text(observation.receipt.failure_reason or "")
    payload = {
        "level": "normalized_diagnostic",
        "stage": stage,
        "normalized_diagnostic": normalized,
        "pipeline_source": observation.pipeline_source,
    }
    return CausalFailureFingerprintV1(
        level="normalized_diagnostic",
        normalized_diagnostic=normalized,
        fingerprint_hash=canonical_sha256(payload),
        **mirrored,
    )


# --- classification --------------------------------------------------------------------------


def _is_infra_signal(observation: FailureObservationV1) -> bool:
    exception_type = observation.exception_type or ""
    return observation.blocked_category == "infra_external" or any(
        marker in exception_type for marker in _INFRA_EXCEPTION_MARKERS
    )


def _is_transient_signal(observation: FailureObservationV1) -> bool:
    exception_type = observation.exception_type or ""
    return any(marker in exception_type for marker in _TRANSIENT_PROVIDER_EXCEPTION_MARKERS)


def _has_no_structured_signal(observation: FailureObservationV1) -> bool:
    return (
        observation.structured_error_code is None
        and observation.gate_or_check_id is None
        and not observation.structured_error_args
        and observation.causal_component is None
    )


def _classify(
    fingerprint: CausalFailureFingerprintV1,
    members: tuple[FailureObservationV1, ...],
    distinct_ecosystems: tuple[str, ...],
    dependency_changed: bool,
) -> tuple[FailureClassificationV1, str, RecommendedRepairScopeV1]:
    level = fingerprint.level
    member_count = len(members)

    if level == "normalized_diagnostic" and member_count >= _OPAQUE_BULK_THRESHOLD:
        if all(_has_no_structured_signal(m) for m in members):
            return (
                "unknown",
                "high-volume cluster formed from unstructured diagnostics only -- upstream "
                "evidence lacks per-check granularity; not a proven shared cause",
                "manual_classification_required",
            )

    if level == "corrupt_or_stale_evidence":
        return (
            "corrupt_or_stale_evidence",
            "observation evidence failed a soft-corruption plausibility check (unparseable "
            "timestamp or an empty dependency-fingerprint dict)",
            "manual_classification_required",
        )

    code_marker = (fingerprint.gate_or_check_id or "").lower()
    error_marker = (fingerprint.structured_error_code or "").lower()
    if code_marker in _INPUT_CONTRACT_MARKERS or error_marker in _INPUT_CONTRACT_MARKERS:
        return (
            "input_contract_mismatch",
            "gate/check/error code matches a known input-contract marker",
            "shared_module" if len(distinct_ecosystems) >= 2 else "single_repository_evidence",
        )

    if members and all(_is_infra_signal(m) for m in members) and not dependency_changed:
        return (
            "infra_external",
            "unanimous infra/provider exception or blocked_category=infra_external, with no "
            "dependency fingerprint change since last observed",
            "external_dependency_wait",
        )

    if members and all(
        _is_transient_signal(m) or (_is_infra_signal(m) and dependency_changed) for m in members
    ):
        return (
            "transient_provider",
            "provider/timeout-shaped exception, or an infra signal whose dependency fingerprint "
            "has since changed",
            "provider_retry_after_change",
        )

    if level in _STRUCTURED_TIERS:
        if len(distinct_ecosystems) >= 2:
            return (
                "shared_code_defect",
                "identical structured error/gate/component/args signature spans multiple "
                "ecosystems -- pipeline-agnostic evidence of one shared cause",
                "shared_module",
            )
        return (
            "ecosystem_adapter_defect",
            "identical structured error/gate/component/args signature confined to one ecosystem",
            "ecosystem_adapter",
        )

    if level in _UNSTRUCTURED_SIGNAL_TIERS:
        if fingerprint.stage in _FACTS_OR_INPUT_STAGES:
            return (
                "repository_evidence_defect",
                "unstructured signal at a facts/input-family stage -- repository-scoped "
                "evidence gap",
                "single_repository_evidence",
            )
        if fingerprint.stage in _CANDIDATE_OR_REVIEW_STAGES and member_count == 1:
            return (
                "candidate_specific_rejection",
                "unstructured signal at a candidate/review-family stage, single repository",
                "single_repository_evidence",
            )

    return (
        "unknown",
        "no structured signal and no decision-table row matched -- fails closed rather than "
        "guessing a cause",
        "manual_classification_required",
    )


def _confidence_for(fingerprint: CausalFailureFingerprintV1) -> ConfidenceV1:
    return _TIER_CONFIDENCE[fingerprint.level]


# --- evidence completeness / representative selection ---------------------------------------


def _is_evidence_complete(observation: FailureObservationV1) -> bool:
    return observation.evidence_ref is not None and (
        observation.structured_error_code is not None
        or observation.gate_or_check_id is not None
        or bool(observation.dependency_fingerprint)
    )


def _evidence_completeness(members: tuple[FailureObservationV1, ...]) -> EvidenceCompletenessV1:
    complete_count = sum(1 for m in members if _is_evidence_complete(m))
    if complete_count == len(members):
        return "complete"
    if complete_count == 0:
        return "none"
    return "partial"


def _evidence_completeness_score(observation: FailureObservationV1) -> int:
    score = 0
    if observation.evidence_ref is not None:
        score += 3
    if observation.structured_error_code is not None:
        score += 2
    if observation.gate_or_check_id is not None:
        score += 2
    if observation.dependency_fingerprint:
        score += 2
    if observation.structured_error_args:
        score += 1
    if observation.exception_type is not None:
        score += 1
    if observation.known_reproducibility_verdict in _CLEAN_REPRODUCIBILITY_VERDICTS:
        score += 2
    return score


def _observed_at_key(observation: FailureObservationV1) -> str:
    return observation.observed_at or observation.receipt.generated_at


def _select_representative(
    members: tuple[FailureObservationV1, ...], reason_suffix: str = ""
) -> RepresentativeProofCaseV1:
    best = min(
        members,
        key=lambda m: (-_evidence_completeness_score(m), _observed_at_key(m), m.org_repo),
    )
    score = _evidence_completeness_score(best)
    reason = (
        f"highest evidence-completeness score ({score}) among {len(members)} member(s), "
        "tie-broken by earliest observation then org_repo"
    )
    if reason_suffix:
        reason = f"{reason}; {reason_suffix}"
    return RepresentativeProofCaseV1(
        org_repo=best.org_repo,
        observation=best,
        selection_reason=reason[:_REASON_MAX_LEN],
        evidence_completeness_score=score,
    )


def _select_cluster_representatives(
    members: tuple[FailureObservationV1, ...],
) -> tuple[RepresentativeProofCaseV1, list[RepresentativeProofCaseV1]]:
    """One primary representative, plus one extra per additional distinct ecosystem beyond the
    primary's own -- never claim one repository proves a cross-ecosystem fix."""

    primary = _select_representative(members)
    primary_ecosystem = primary.observation.ecosystem

    by_ecosystem: dict[str, list[FailureObservationV1]] = {}
    for member in members:
        if member.ecosystem is None or member.ecosystem == primary_ecosystem:
            continue
        by_ecosystem.setdefault(member.ecosystem, []).append(member)

    extra: list[RepresentativeProofCaseV1] = []
    for ecosystem in sorted(by_ecosystem):
        extra.append(
            _select_representative(
                tuple(by_ecosystem[ecosystem]),
                reason_suffix=f"additional ecosystem coverage: {ecosystem}",
            )
        )
    return primary, extra


def _all_members_as_representatives(
    members: tuple[FailureObservationV1, ...],
) -> list[RepresentativeProofCaseV1]:
    result = []
    for member in sorted(members, key=lambda m: m.org_repo):
        result.append(
            RepresentativeProofCaseV1(
                org_repo=member.org_repo,
                observation=member,
                selection_reason=(
                    "unresolved/unknown cluster -- every member preserved individually, never "
                    "claim one repair closes an unproven shared cause"
                )[:_REASON_MAX_LEN],
                evidence_completeness_score=_evidence_completeness_score(member),
            )
        )
    return result


def _required_closure_evidence(
    members: tuple[FailureObservationV1, ...], classification: FailureClassificationV1
) -> str:
    if classification == "unknown":
        return (
            "insufficient structured evidence to define closure criteria -- classify manually "
            "before proposing a repair"
        )[:_REASON_MAX_LEN]
    has_clean_reproduction = any(
        m.known_reproducibility_verdict in _CLEAN_REPRODUCIBILITY_VERDICTS for m in members
    )
    if not has_clean_reproduction:
        return (
            "a genuine zero-new-provider-call replay (NO_OP_PROVEN/TRANSACTION_NO_OP_PROVEN), "
            "not merely byte- or hash-equality, for at least one representative member"
        )[:_REASON_MAX_LEN]
    return (
        "re-run the representative's replay and confirm it remains NO_OP_PROVEN/"
        "RENDER_REPRODUCIBLE after the repair lands"
    )[:_REASON_MAX_LEN]


# --- deduplication -------------------------------------------------------------------------


def _dedup_key(observation: FailureObservationV1) -> tuple[Any, ...]:
    dependency_fingerprint = observation.dependency_fingerprint or {}
    dep_items = tuple(sorted((key, repr(value)) for key, value in dependency_fingerprint.items()))
    return (
        observation.receipt.canonical_hash(),
        observation.family,
        observation.blocked_category,
        observation.causal_component,
        observation.structured_error_code,
        observation.gate_or_check_id,
        observation.structured_error_args,
        dep_items,
        observation.exception_type,
        observation.evidence_ref,
        observation.pipeline_source,
        observation.known_reproducibility_verdict,
    )


def _deduplicate(observations: Sequence[FailureObservationV1]) -> list[FailureObservationV1]:
    """Exact-duplicate observations (identical on every causal field, differing only in
    attempt_count/observed_at) merge into one, summing attempt_count and tracking first/last
    observation -- never silently dropping attempt accounting."""

    merged: dict[tuple[Any, ...], FailureObservationV1] = {}
    for obs in observations:
        key = _dedup_key(obs)
        existing = merged.get(key)
        if existing is None:
            merged[key] = obs
            continue
        first = min(_observed_at_key(existing), _observed_at_key(obs))
        last = max(
            existing.last_observed_at or _observed_at_key(existing),
            obs.last_observed_at or _observed_at_key(obs),
        )
        merged[key] = existing.model_copy(
            update={
                "attempt_count": existing.attempt_count + obs.attempt_count,
                "observed_at": first,
                "last_observed_at": last,
            }
        )
    return list(merged.values())


# --- cluster assembly ------------------------------------------------------------------------


def _sort_key(cluster: CausalFailureClusterV1) -> tuple[int, int, int, int, int, int, int, str]:
    return (
        cluster.classification_actionability_rank,
        -cluster.repos_blocked,
        cluster.earliest_shared_stage_rank,
        0 if cluster.single_repair_multi_repo else 1,
        0 if cluster.deterministic else 1,
        0 if cluster.minimal_proof_possible else 1,
        0 if cluster.dependency_changed else 1,
        cluster.fingerprint.fingerprint_hash,
    )


def _build_cluster(
    pairs: list[tuple[FailureObservationV1, CausalFailureFingerprintV1]],
    dependency_snapshot: DependencyFingerprintSnapshotV1 | None,
) -> tuple[CausalFailureClusterV1, tuple[RepresentativeProofCaseV1, ...]]:
    fingerprint = pairs[0][1]
    members = tuple(obs for obs, _ in pairs)
    member_org_repos = tuple(sorted({m.org_repo for m in members}))
    member_count = len(member_org_repos)

    distinct_ecosystems = tuple(sorted({m.ecosystem for m in members if m.ecosystem is not None}))
    distinct_pipeline_sources = tuple(
        sorted({m.pipeline_source for m in members if m.pipeline_source is not None})
    )

    earliest_member = min(members, key=lambda m: STAGE_ORDER.index(m.receipt.stage))
    earliest_shared_stage = earliest_member.receipt.stage
    earliest_shared_stage_rank = STAGE_ORDER.index(earliest_shared_stage)

    changed_per_member = [_full_dependency_changed_keys(m, dependency_snapshot) for m in members]
    changed_dependency_keys = tuple(sorted({key for keys in changed_per_member for key in keys}))
    dependency_changed = bool(changed_dependency_keys)

    deterministic = all(m.receipt.provider_call_count == 0 for m in members)

    classification, classification_reason, recommended_scope = _classify(
        fingerprint, members, distinct_ecosystems, dependency_changed
    )
    confidence = _confidence_for(fingerprint)
    evidence_completeness = _evidence_completeness(members)
    minimal_proof_possible = any(_is_evidence_complete(m) for m in members)
    inclusion_reason, exclusion_reason = _TIER_REASONS[fingerprint.level]
    required_closure_evidence = _required_closure_evidence(members, classification)
    estimated_retries_avoided = max(0, member_count - 1)
    single_repair_multi_repo = member_count > 1

    if classification == "unknown":
        primary, _extra = _select_cluster_representatives(members)
        cohort: tuple[RepresentativeProofCaseV1, ...] = tuple(
            _all_members_as_representatives(members)
        )
    else:
        primary, extra = _select_cluster_representatives(members)
        cohort = (primary, *extra)

    cluster = CausalFailureClusterV1(
        cluster_id=fingerprint.fingerprint_hash,
        fingerprint=fingerprint,
        classification=classification,
        classification_reason=classification_reason[:_REASON_MAX_LEN],
        confidence=confidence,
        member_org_repos=member_org_repos,
        member_count=member_count,
        distinct_ecosystems=distinct_ecosystems,
        distinct_pipeline_sources=distinct_pipeline_sources,
        earliest_shared_stage=earliest_shared_stage,
        earliest_shared_stage_rank=earliest_shared_stage_rank,
        evidence_completeness=evidence_completeness,
        changed_dependency_keys=changed_dependency_keys,
        dependency_changed=dependency_changed,
        repos_blocked=member_count,
        single_repair_multi_repo=single_repair_multi_repo,
        deterministic=deterministic,
        minimal_proof_possible=minimal_proof_possible,
        classification_actionability_rank=_ACTIONABILITY_RANK[classification],
        recommended_repair_scope=recommended_scope,
        required_closure_evidence=required_closure_evidence,
        inclusion_reason=inclusion_reason[:_REASON_MAX_LEN],
        exclusion_reason=exclusion_reason[:_REASON_MAX_LEN],
        estimated_retries_avoided=estimated_retries_avoided,
        priority_rank=0,
        representative=primary,
    )
    return cluster, cohort


# --- public entry point ----------------------------------------------------------------------


def reduce_fleet_failures(
    *,
    observations: Sequence[FailureObservationV1],
    dependency_snapshot: DependencyFingerprintSnapshotV1 | None = None,
) -> FleetCausalReductionV1:
    """Pure, deterministic reduction of many FAILED proof-stage observations into causal
    clusters. Never writes a receipt, never retries, never transitions lifecycle state, never
    schedules anything -- read-only end to end."""

    raise NotImplementedError(
        "reduce_fleet_failures: contracts committed, reduction algorithm not yet implemented"
    )
