"""Vocabulary and constants for sealed transaction replay attestation."""

from __future__ import annotations

import re
from typing import Final, Literal

ATTESTOR_IDENTITY: Final = "sealed-transaction-replay-attestor"

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_HEX_DIGEST = re.compile(r"^[0-9a-f]{40,64}$")
_DRIVE_LETTER = re.compile(r"^[A-Za-z]:")
_CONTROL_CHARS = re.compile(r"[\x00-\x1f]")

HashModeV1 = Literal["raw_sha256", "crlf_normalized_sha256", "canonical_json_sha256"]
RequirementLevelV1 = Literal["REQUIRED", "OPTIONAL", "NOT_APPLICABLE"]
ArtifactKindV1 = Literal["json_object", "json_array", "jsonl_llm_ledger", "text", "binary"]
BundleScopeV1 = Literal["both", "first_only", "replay_only"]

# A scoped artifact is a claim that its presence on only one side is expected, so the allow-list
# cannot be derived from the two observed file sets. These are the only lifecycle products that
# the current complete-transaction protocol intentionally adds during an immediate no-op replay.
# Everything else must exist in both sealed bundles and be compared.
EXPECTED_LIFECYCLE_DELTA_SCOPES: Final[dict[str, BundleScopeV1]] = {
    "effects/product-effect-ledger.json": "replay_only",
    "receipts/NO_OP_PROVEN.json": "replay_only",
    "review/benchmark-acceptance.json": "replay_only",
    "review/no-op-proof.json": "replay_only",
    "review/rubric-evaluation.json": "replay_only",
}

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
