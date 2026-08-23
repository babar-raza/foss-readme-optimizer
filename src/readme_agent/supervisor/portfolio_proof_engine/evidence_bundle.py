"""Load the raw, already-written candidate-bound evidence a rubric evaluation needs.

Every field here is read from the *canonical* `local_poc` compatibility bundle
(`paths.readme_poc_repository_dir()`), never `runs/share/poc/` (the diagnostic straight-line
runner's own separate, non-lifecycle-bound output the task explicitly says must never be
authoritative). Reads are best-effort and defensive: a missing or malformed artifact leaves its
field `None` rather than raising, so a rubric criterion that depends on it fails closed to "not
proven" instead of crashing the whole evaluation -- exactly the fail-closed contract the 30-point
rubric requires.

Field-to-file mapping is grounded in the producers confirmed during this task's research
(`supervisor/local_poc_evidence.py`, `supervisor/local_poc_review_evidence.py`,
`readme/document_validation.py::DocumentCandidateValidationV1`,
`facts/knowledge_application_evidence.py::KnowledgeApplicationV1`,
`specialists/readme_review_roles.py::FactualPlanReviewResultV1`/`BlindQualityReviewResultV1`).
Where this task could not independently confirm an exact nested key inside a real generated
artifact (never having run the live pipeline, per the task's own instruction not to), the readers
below check the most likely key paths rather than assuming one -- `rubric.py`'s criteria treat an
absent value as unproven, never as a guess. Recalibrate the key paths here against one real
generated bundle before the first live rubric run.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, TypeVar

from pydantic import BaseModel, ConfigDict

from readme_agent import paths
from readme_agent.evidence.writer import verify_sha256sums
from readme_agent.presentation.candidate_benchmark_acceptance import (
    CandidateBenchmarkAcceptanceV1,
)
from readme_agent.presentation.candidate_benchmark_comparison import (
    CandidateBenchmarkComparisonV1,
)
from readme_agent.verification.sealed_transaction_replay import (
    CompleteTransactionNoOpProofV1,
    ReplayAttestationContractV1,
)


class CompleteTransactionReplayAttestationV1(BaseModel):
    """Typed envelope persisted by the local-POC replay gate."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    attestation_type: Literal["CompleteTransactionReplayAttestationV1"]
    first_bundle_root: str
    replay_bundle_root: str
    proof: CompleteTransactionNoOpProofV1


_ModelT = TypeVar("_ModelT", bound=BaseModel)


class EvidenceBundleV1(BaseModel):
    """Raw (loosely-typed) evidence for one candidate-bound rubric evaluation."""

    model_config = ConfigDict(extra="forbid")

    org_repo: str
    source_revision: str | None
    candidate_hash: str | None
    bundle_dir: str | None

    manifest: dict | None = None
    deterministic_validation: dict | None = None
    knowledge_application: dict | None = None
    factual_review: dict | None = None
    visitor_review: dict | None = None
    combined_review: dict | None = None
    claim_map: dict | None = None
    reconciliation: dict | None = None
    no_op_proof: dict | None = None
    check_coverage: dict | None = None
    facts: dict | None = None
    snapshot_revision: dict | None = None
    document_plan: dict | None = None
    benchmark_acceptance: CandidateBenchmarkAcceptanceV1 | None = None
    benchmark_comparison: CandidateBenchmarkComparisonV1 | None = None
    replay_contract: ReplayAttestationContractV1 | None = None
    replay_attestation: CompleteTransactionReplayAttestationV1 | None = None
    rubric_evaluation: dict | None = None
    source_readme: str | None = None
    candidate_readme: str | None = None


def _read_json(path: Path) -> dict | None:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return loaded if isinstance(loaded, dict) else None


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None


def _read_model(path: Path, model_type: type[_ModelT]) -> _ModelT | None:
    value = _read_json(path)
    if value is None:
        return None
    try:
        return model_type.model_validate(value)
    except ValueError:
        return None


def comparison_evidence_paths_are_bound(
    bundle_dir: Path, comparison: CandidateBenchmarkComparisonV1
) -> bool:
    """Require every applicable benchmark path inside a checksum-complete bundle."""

    resolved_root = bundle_dir.resolve()
    evidence_paths = {
        relative
        for dimension in comparison.dimensions
        if dimension.applicable
        for relative in dimension.evidence_paths
    }
    if not evidence_paths or not verify_sha256sums(resolved_root):
        return False
    for relative in evidence_paths:
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts:
            return False
        resolved = (resolved_root / path).resolve()
        try:
            resolved.relative_to(resolved_root)
        except ValueError:
            return False
        if not resolved.is_file():
            return False
    return True


def load_evidence_bundle(
    org_repo: str,
    source_revision: str | None,
    *,
    candidate_hash: str | None = None,
) -> EvidenceBundleV1:
    if not source_revision:
        return EvidenceBundleV1(
            org_repo=org_repo,
            source_revision=None,
            candidate_hash=candidate_hash,
            bundle_dir=None,
        )
    org, repo = org_repo.split("/", maxsplit=1)
    bundle_dir = paths.readme_poc_repository_dir(org, repo, source_revision)
    return EvidenceBundleV1(
        org_repo=org_repo,
        source_revision=source_revision,
        candidate_hash=candidate_hash,
        bundle_dir=str(bundle_dir),
        manifest=_read_json(bundle_dir / "manifest.json"),
        deterministic_validation=_read_json(
            bundle_dir / "review" / "deterministic-validation.json"
        ),
        knowledge_application=_read_json(bundle_dir / "knowledge-application.json"),
        factual_review=_read_json(bundle_dir / "review" / "factual-plan-review.json"),
        visitor_review=_read_json(bundle_dir / "review" / "blind-quality-review.json"),
        combined_review=_read_json(bundle_dir / "review" / "combined-review.json"),
        claim_map=_read_json(bundle_dir / "candidate" / "claim-map.json"),
        reconciliation=_read_json(bundle_dir / "candidate" / "readme-reconciliation.json"),
        no_op_proof=_read_json(bundle_dir / "review" / "no-op-proof.json"),
        check_coverage=_read_json(bundle_dir / "candidate" / "check-coverage.json"),
        facts=_read_json(bundle_dir / "facts" / "product-facts.json"),
        snapshot_revision=_read_json(bundle_dir / "source" / "revision.json"),
        document_plan=_read_json(bundle_dir / "planning" / "readme-document-plan.json"),
        benchmark_acceptance=_read_model(
            bundle_dir / "review" / "benchmark-acceptance.json",
            CandidateBenchmarkAcceptanceV1,
        ),
        benchmark_comparison=_read_model(
            bundle_dir / "planning" / "candidate-benchmark-comparison.json",
            CandidateBenchmarkComparisonV1,
        ),
        replay_contract=_read_model(
            bundle_dir / "review" / "complete-transaction-replay-contract.json",
            ReplayAttestationContractV1,
        ),
        replay_attestation=_read_model(
            bundle_dir / "review" / "complete-transaction-replay-attestation.json",
            CompleteTransactionReplayAttestationV1,
        ),
        rubric_evaluation=_read_json(bundle_dir / "review" / "rubric-evaluation.json"),
        source_readme=_read_text(bundle_dir / "source" / "README.md"),
        candidate_readme=_read_text(bundle_dir / "candidate" / "README.md"),
    )
