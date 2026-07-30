"""Validate one trusted cohort member against its complete evidence bundle."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from readme_agent import paths
from readme_agent.evidence.writer import sha256_file, verify_sha256sums
from readme_agent.facts.trusted_readme_schema import TrustedReadmeFactGraphV1
from readme_agent.readme.trusted_composition_candidate_validation import (
    TRUSTED_CANDIDATE_NORMALIZATION_VERSION,
)
from readme_agent.readme.trusted_composition_models import TrustedReadmeCompositionOutputV1
from readme_agent.registry.models import ProductEntry
from readme_agent.repository_snapshot import RepositorySnapshotV1
from readme_agent.specialists.trusted_transform_review_models import TrustedReviewExecutionV1
from readme_agent.state.lifecycle_schema import ReadmePocLifecycleStateV2
from readme_agent.state.schema import RunStateV2
from readme_agent.state.trusted_cohort_schema import QualifiedTrustedCohortMemberV1


def validate_trusted_cohort_member(
    entry: ProductEntry,
    state: RunStateV2,
    bundle_dir: Path,
    *,
    reviewer_standard: str,
    prompt_content: str,
    prompt_dependencies: dict[str, str],
    prompt_hashes: dict[str, str],
) -> tuple[QualifiedTrustedCohortMemberV1 | None, list[str]]:
    """Return a typed member only when every current binding agrees."""

    lifecycle = state.readme_poc_lifecycle
    assert isinstance(lifecycle, ReadmePocLifecycleStateV2)
    reasons: list[str] = []
    if not verify_sha256sums(bundle_dir):
        return None, ["trusted_bundle_checksum_inventory_invalid"]
    try:
        manifest = _json_object(bundle_dir / "manifest.json")
        snapshot = RepositorySnapshotV1.model_validate(
            _json_object(bundle_dir.parent.parent / "source" / "revision.json")
        )
        graph = TrustedReadmeFactGraphV1.model_validate(
            _json_object(bundle_dir / "facts" / "readme-inherited-facts.json")
        )
        composition = TrustedReadmeCompositionOutputV1.model_validate(
            _json_object(bundle_dir / "planning" / "composition-output.json")
        )
        execution = TrustedReviewExecutionV1.model_validate(
            _json_object(bundle_dir / "review" / "review-execution.json")
        )
        no_op = _json_object(bundle_dir / "review" / "no-op-proof.json")
    except (OSError, UnicodeError, ValueError, ValidationError, json.JSONDecodeError):
        return None, ["trusted_bundle_contract_invalid"]
    review = execution.review

    expected_pairs = (
        (snapshot.org_repo, entry.org_repo, "snapshot_repository_mismatch"),
        (snapshot.source_revision, lifecycle.source_revision, "snapshot_revision_mismatch"),
        (graph.org_repo, entry.org_repo, "fact_graph_repository_mismatch"),
        (graph.source_revision, lifecycle.source_revision, "fact_graph_revision_mismatch"),
        (graph.readme_sha256, snapshot.readme_sha256, "fact_graph_readme_mismatch"),
        (composition.org_repo, entry.org_repo, "composition_repository_mismatch"),
        (composition.plan.fact_graph_hash, graph.canonical_hash(), "composition_facts_mismatch"),
        (manifest.get("org_repo"), entry.org_repo, "manifest_repository_mismatch"),
        (manifest.get("source_revision"), lifecycle.source_revision, "manifest_revision_mismatch"),
        (manifest.get("content_assurance"), "trusted_inherited", "manifest_assurance_mismatch"),
        (manifest.get("lifecycle_status"), "TRUSTED_NO_OP_PROVEN", "manifest_status_mismatch"),
        (manifest.get("complete"), True, "manifest_incomplete"),
        (manifest.get("facts_hash"), lifecycle.facts_hash, "lifecycle_facts_mismatch"),
        (manifest.get("candidate_hash"), lifecycle.candidate_hash, "lifecycle_candidate_mismatch"),
        (manifest.get("candidate_hash"), composition.candidate_sha256, "candidate_hash_mismatch"),
        (manifest.get("review_verdict"), "TRUSTED_TRANSFORM_APPROVED", "review_not_approved"),
        (review.verdict, "TRUSTED_TRANSFORM_APPROVED", "typed_review_not_approved"),
        (review.content_assurance, "trusted_inherited", "review_assurance_mismatch"),
        (review.factual_truth_verified, False, "review_truth_scope_mismatch"),
        (
            manifest.get("reviewer_standard_hash"),
            reviewer_standard,
            "reviewer_standard_changed",
        ),
        (
            review.cache_identity.review_contract_sha256,
            reviewer_standard,
            "review_contract_changed",
        ),
        (
            manifest.get("prompt_registry_content_hash"),
            prompt_content,
            "prompt_registry_changed",
        ),
        (
            manifest.get("prompt_dependency_hashes"),
            prompt_dependencies,
            "prompt_dependencies_changed",
        ),
        (manifest.get("prompt_hashes_by_id"), prompt_hashes, "prompt_hashes_changed"),
        (
            manifest.get("candidate_normalization_version"),
            TRUSTED_CANDIDATE_NORMALIZATION_VERSION,
            "candidate_normalization_changed",
        ),
        (no_op.get("passed"), True, "no_op_not_passed"),
        (no_op.get("review_cache_reused"), True, "no_op_review_not_reused"),
        (no_op.get("new_provider_call_count"), 0, "no_op_provider_call_detected"),
        (no_op.get("candidate_sha256"), composition.candidate_sha256, "no_op_candidate_mismatch"),
        (
            no_op.get("cache_identity_sha256"),
            review.cache_identity_sha256,
            "no_op_review_identity_mismatch",
        ),
        (lifecycle.prompt_hash, review.cache_identity_sha256, "lifecycle_review_identity_mismatch"),
    )
    reasons.extend(reason for actual, expected, reason in expected_pairs if actual != expected)
    candidate_path = bundle_dir / "candidate" / "README.md"
    if (
        not candidate_path.is_file()
        or sha256_file(candidate_path)[0] != composition.candidate_sha256
    ):
        reasons.append("candidate_bytes_mismatch")
    if reasons:
        return None, reasons

    assert entry.provider_identity is not None
    assert snapshot.readme_sha256 is not None
    return (
        QualifiedTrustedCohortMemberV1(
            org_repo=entry.org_repo,
            provider_identity=entry.provider_identity,
            source_revision=snapshot.source_revision,
            observed_target_head=snapshot.source_revision,
            state_version=state.state_version,
            readme_sha256=snapshot.readme_sha256,
            facts_sha256=graph.canonical_hash(),
            plan_sha256=composition.plan_hash,
            candidate_sha256=composition.candidate_sha256,
            deterministic_validation_sha256=sha256_file(
                bundle_dir / "review" / "deterministic-validation.json"
            )[0],
            independent_review_sha256=sha256_file(
                bundle_dir / "review" / "independent-review.json"
            )[0],
            no_op_proof_sha256=sha256_file(bundle_dir / "review" / "no-op-proof.json")[0],
            review_cache_identity_sha256=review.cache_identity_sha256,
            reviewer_standard_sha256=reviewer_standard,
            prompt_registry_sha256=prompt_content,
            prompt_dependency_hashes=prompt_dependencies,
            candidate_normalization_version=TRUSTED_CANDIDATE_NORMALIZATION_VERSION,
            bundle_manifest_sha256=sha256_file(bundle_dir / "manifest.json")[0],
            bundle_inventory_sha256=sha256_file(bundle_dir / "sha256sums.txt")[0],
            bundle_path=display_path(bundle_dir),
        ),
        [],
    )


def trusted_bundle_dir(org_repo: str, source_revision: str) -> Path:
    org, repo = org_repo.split("/", maxsplit=1)
    return (
        paths.readme_poc_repository_dir(org, repo, source_revision)
        / "assurance"
        / "trusted_inherited"
    )


def display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _json_object(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value
