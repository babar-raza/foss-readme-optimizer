"""Persist and validate trusted README composition and review evidence."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from readme_agent import paths
from readme_agent.evidence.writer import (
    refresh_sha256sums,
    verify_sha256sums,
    write_redacted_json,
    write_redacted_text,
)
from readme_agent.facts.trusted_readme_schema import TrustedReadmeFactGraphV1
from readme_agent.readme.trusted_composition_candidate_validation import (
    TRUSTED_CANDIDATE_NORMALIZATION_VERSION,
)
from readme_agent.readme.trusted_composition_models import TrustedReadmeCompositionOutputV1
from readme_agent.repository_snapshot import RepositorySnapshotV1
from readme_agent.specialists.trusted_transform_review_models import (
    TrustedRepairAttemptV1,
    TrustedReviewExecutionV1,
)
from readme_agent.supervisor.local_poc_evidence import write_local_poc_manifest


class TrustedReadmeEvidenceCacheV1(BaseModel):
    """Checksum-validated reusable trusted candidate and optional approval."""

    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    bundle_dir: Path
    composition: TrustedReadmeCompositionOutputV1
    review_execution: TrustedReviewExecutionV1 | None = None
    lifecycle_status: str


def trusted_readme_bundle_dir(snapshot: RepositorySnapshotV1) -> Path:
    """Return the assurance-isolated evidence root for one immutable README."""

    org, repo = snapshot.org_repo.split("/", maxsplit=1)
    return (
        paths.readme_poc_repository_dir(org, repo, snapshot.source_revision)
        / "assurance"
        / "trusted_inherited"
    )


def write_trusted_composition_evidence(
    snapshot: RepositorySnapshotV1,
    graph: TrustedReadmeFactGraphV1,
    composition: TrustedReadmeCompositionOutputV1,
) -> Path:
    """Write the exact LLM plan, candidate, and native patch."""

    _require_bindings(snapshot, graph, composition)
    bundle_dir = trusted_readme_bundle_dir(snapshot)
    planning_dir = bundle_dir / "planning"
    candidate_dir = bundle_dir / "candidate"
    write_redacted_json(planning_dir / "transform-plan.json", composition.plan)
    write_redacted_json(planning_dir / "composition-output.json", composition)
    write_redacted_text(candidate_dir / "README.md", composition.candidate_markdown)
    write_redacted_text(candidate_dir / "README.patch", composition.candidate_patch)
    write_redacted_text(candidate_dir / "candidate-hash.txt", composition.candidate_sha256 + "\n")
    prior = _manifest(bundle_dir)
    write_local_poc_manifest(
        bundle_dir,
        {
            **prior,
            "schema_version": 1,
            "org_repo": snapshot.org_repo,
            "source_revision": snapshot.source_revision,
            "readme_sha256": snapshot.readme_sha256,
            "lifecycle_status": "TRUSTED_CANDIDATE_GENERATED",
            "facts_hash": graph.canonical_hash(),
            "plan_hash": composition.plan_hash,
            "candidate_hash": composition.candidate_sha256,
            "candidate_normalization_version": TRUSTED_CANDIDATE_NORMALIZATION_VERSION,
            "complete": False,
            "completed_stages": _merge_stages(
                prior,
                "TRUSTED_PLAN_READY",
                "TRUSTED_CANDIDATE_GENERATED",
            ),
        },
        content_assurance="trusted_inherited",
    )
    refresh_sha256sums(bundle_dir)
    return bundle_dir


def write_trusted_review_evidence(
    snapshot: RepositorySnapshotV1,
    graph: TrustedReadmeFactGraphV1,
    composition: TrustedReadmeCompositionOutputV1,
    execution: TrustedReviewExecutionV1,
    *,
    repair_history: tuple[TrustedRepairAttemptV1, ...] = (),
    no_op_proven: bool = False,
) -> Path:
    """Write deterministic, two-role, repair, accounting, and no-op proof."""

    _require_bindings(snapshot, graph, composition)
    if execution.review.candidate_sha256 != composition.candidate_sha256:
        raise ValueError("trusted review evidence belongs to different candidate bytes")
    bundle_dir = write_trusted_composition_evidence(snapshot, graph, composition)
    review_dir = bundle_dir / "review"
    write_redacted_json(
        review_dir / "deterministic-validation.json",
        execution.review.validation,
    )
    write_redacted_json(review_dir / "blind-quality-review.json", execution.review.blind_quality)
    write_redacted_json(
        review_dir / "inheritance-fidelity-review.json",
        execution.review.inheritance_fidelity,
    )
    write_redacted_json(review_dir / "independent-review.json", execution.review)
    write_redacted_json(review_dir / "review-execution.json", execution)
    write_redacted_json(
        review_dir / "repair-history.json",
        [attempt.model_dump(mode="json") for attempt in repair_history],
    )
    if no_op_proven:
        write_redacted_json(
            review_dir / "no-op-proof.json",
            {
                "schema_version": 1,
                "org_repo": snapshot.org_repo,
                "source_revision": snapshot.source_revision,
                "candidate_sha256": composition.candidate_sha256,
                "cache_identity_sha256": execution.review.cache_identity_sha256,
                "review_cache_reused": execution.cache_reused,
                "new_provider_call_count": execution.new_provider_call_count,
                "reused_candidate_sha256": composition.candidate_sha256,
                "passed": (
                    execution.cache_reused
                    and execution.new_provider_call_count == 0
                    and execution.review.verdict == "TRUSTED_TRANSFORM_APPROVED"
                ),
            },
        )
    approved = execution.review.verdict == "TRUSTED_TRANSFORM_APPROVED"
    lifecycle_status = (
        "TRUSTED_NO_OP_PROVEN"
        if no_op_proven and approved
        else ("TRUSTED_TRANSFORM_APPROVED" if approved else execution.review.verdict)
    )
    prior = _manifest(bundle_dir)
    stages = ["TRUSTED_DETERMINISTIC_VALIDATED", "TRUSTED_REVIEWING"]
    if approved:
        stages.append("TRUSTED_TRANSFORM_APPROVED")
    if no_op_proven and approved:
        stages.append("TRUSTED_NO_OP_PROVEN")
    write_local_poc_manifest(
        bundle_dir,
        {
            **prior,
            "lifecycle_status": lifecycle_status,
            "reviewer_standard_hash": execution.review.cache_identity.review_contract_sha256,
            "review_cache_identity_hash": execution.review.cache_identity_sha256,
            "review_verdict": execution.review.verdict,
            "repair_attempts": len(repair_history),
            "review_ledger_path": execution.ledger_path,
            "review_ledger_sha256": execution.ledger_sha256,
            "complete": no_op_proven and approved,
            "completed_stages": _merge_stages(prior, *stages),
        },
        content_assurance="trusted_inherited",
    )
    refresh_sha256sums(bundle_dir)
    return bundle_dir


def load_trusted_readme_evidence(
    snapshot: RepositorySnapshotV1,
    graph: TrustedReadmeFactGraphV1,
) -> TrustedReadmeEvidenceCacheV1 | None:
    """Load only an exact, checksum-complete composition/review cache."""

    bundle_dir = trusted_readme_bundle_dir(snapshot)
    manifest_path = bundle_dir / "manifest.json"
    composition_path = bundle_dir / "planning" / "composition-output.json"
    if (
        not manifest_path.is_file()
        or not composition_path.is_file()
        or not verify_sha256sums(bundle_dir)
    ):
        return None
    try:
        manifest = _manifest(bundle_dir)
        composition = TrustedReadmeCompositionOutputV1.model_validate_json(
            composition_path.read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
        return None
    if (
        manifest.get("content_assurance") != "trusted_inherited"
        or manifest.get("org_repo") != snapshot.org_repo
        or manifest.get("source_revision") != snapshot.source_revision
        or manifest.get("readme_sha256") != snapshot.readme_sha256
        or manifest.get("facts_hash") != graph.canonical_hash()
        or manifest.get("plan_hash") != composition.plan_hash
        or manifest.get("candidate_hash") != composition.candidate_sha256
        or manifest.get("candidate_normalization_version")
        != TRUSTED_CANDIDATE_NORMALIZATION_VERSION
    ):
        return None
    try:
        _require_bindings(snapshot, graph, composition)
    except ValueError:
        return None
    review_path = bundle_dir / "review" / "review-execution.json"
    review: TrustedReviewExecutionV1 | None = None
    if review_path.is_file():
        try:
            review = TrustedReviewExecutionV1.model_validate_json(
                review_path.read_text(encoding="utf-8")
            )
        except (OSError, UnicodeError, ValueError):
            return None
        if (
            review.review.candidate_sha256 != composition.candidate_sha256
            or manifest.get("review_cache_identity_hash") != review.review.cache_identity_sha256
        ):
            return None
    return TrustedReadmeEvidenceCacheV1(
        bundle_dir=bundle_dir,
        composition=composition,
        review_execution=review,
        lifecycle_status=str(manifest.get("lifecycle_status", "")),
    )


def _require_bindings(
    snapshot: RepositorySnapshotV1,
    graph: TrustedReadmeFactGraphV1,
    composition: TrustedReadmeCompositionOutputV1,
) -> None:
    if graph.org_repo != snapshot.org_repo or composition.org_repo != snapshot.org_repo:
        raise ValueError("trusted evidence repository binding mismatch")
    if graph.source_revision != snapshot.source_revision:
        raise ValueError("trusted evidence source revision mismatch")
    if graph.readme_sha256 != snapshot.readme_sha256:
        raise ValueError("trusted evidence README checksum mismatch")
    if composition.plan.fact_graph_hash != graph.canonical_hash():
        raise ValueError("trusted composition uses a different fact graph")


def _manifest(bundle_dir: Path) -> dict:
    path = bundle_dir / "manifest.json"
    if not path.is_file():
        return {}
    loaded = json.loads(path.read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, dict) else {}


def _merge_stages(manifest: dict, *stages: str) -> list[str]:
    merged = [stage for stage in manifest.get("completed_stages", []) if isinstance(stage, str)]
    for stage in stages:
        if stage not in merged:
            merged.append(stage)
    return merged
