"""Bind benchmark acceptance to one real local-POC evidence bundle."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from readme_agent.evidence.writer import refresh_sha256sums, write_redacted_json
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.presentation.candidate_benchmark_acceptance import (
    CandidateBenchmarkAcceptanceV1,
    CandidateRubricEvidenceV1,
    evaluate_candidate_benchmark_acceptance,
)
from readme_agent.presentation.candidate_benchmark_comparison import (
    CandidateBenchmarkComparisonV1,
)
from readme_agent.readme.document_hashing import sha256_hex
from readme_agent.specialists.readme_review_roles import RoleReviewRecordV1
from readme_agent.supervisor.local_poc_snapshot_evidence import write_local_poc_manifest
from readme_agent.supervisor.portfolio_proof_engine.acceptance_contract import (
    portfolio_acceptance_contract_hash,
)
from readme_agent.supervisor.portfolio_proof_engine.contracts import RubricAcceptanceOutcome
from readme_agent.supervisor.portfolio_proof_engine.evidence_bundle import (
    EvidenceBundleV1,
    comparison_evidence_paths_are_bound,
)
from readme_agent.supervisor.portfolio_proof_engine.rubric import RubricScoreV1
from readme_agent.validation.public_quality_contracts import PublicQualityReportV1


class BenchmarkGateError(RuntimeError):
    """The current bundle cannot support candidate-bound benchmark acceptance."""


def _object(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BenchmarkGateError(f"missing or malformed benchmark input: {path}") from exc
    if not isinstance(value, dict):
        raise BenchmarkGateError(f"benchmark input must be a JSON object: {path}")
    return value


def _base_outcome(score: RubricScoreV1) -> RubricAcceptanceOutcome:
    return RubricAcceptanceOutcome(
        org_repo=score.org_repo,
        accepted=score.total_score == 30 and not score.hard_disqualifiers,
        score=score.total_score,
        hard_disqualifier_count=len(score.hard_disqualifiers),
        missing_evidence_criteria=score.missing_evidence_criteria,
    )


def _facts_identity(bundle_dir: Path, manifest: dict) -> tuple[ProductFactsV2, str]:
    try:
        facts = ProductFactsV2.model_validate(_object(bundle_dir / "facts" / "product-facts.json"))
    except ValidationError as exc:
        raise BenchmarkGateError("benchmark acceptance requires valid ProductFactsV2") from exc
    facts_hash = facts.canonical_hash()
    if manifest.get("facts_hash") != facts_hash:
        raise BenchmarkGateError("manifest facts_hash does not match ProductFactsV2")
    return facts, facts_hash


def evaluate_and_persist_benchmark_gate(
    bundle: EvidenceBundleV1,
    score: RubricScoreV1,
) -> RubricAcceptanceOutcome:
    """Evaluate the qualified comparator and persist its candidate-bound evidence.

    The existing rubric remains the only numeric score. Benchmark acceptance is a hard condition
    on that score, so a 30/30 subtotal cannot conceal an applicable benchmark failure.
    """

    if bundle.bundle_dir is None:
        raise BenchmarkGateError("benchmark acceptance requires a revision-addressed bundle")
    bundle_dir = Path(bundle.bundle_dir)
    manifest = _object(bundle_dir / "manifest.json")
    candidate_path = bundle_dir / "candidate" / "README.md"
    try:
        candidate = candidate_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise BenchmarkGateError("benchmark acceptance requires a readable candidate") from exc
    candidate_sha256 = sha256_hex(candidate)
    if candidate_sha256 != bundle.candidate_hash or candidate_sha256 != manifest.get(
        "candidate_hash"
    ):
        raise BenchmarkGateError("candidate bytes disagree with bundle identity")

    _, facts_hash = _facts_identity(bundle_dir, manifest)
    try:
        comparison = CandidateBenchmarkComparisonV1.model_validate(
            _object(bundle_dir / "planning" / "candidate-benchmark-comparison.json")
        )
        deterministic = PublicQualityReportV1.model_validate(
            (_object(bundle_dir / "review" / "deterministic-validation.json")).get(
                "public_quality_report"
            )
        )
        factual = RoleReviewRecordV1.model_validate(
            _object(bundle_dir / "review" / "factual-plan-review.json")
        )
        visitor = RoleReviewRecordV1.model_validate(
            _object(bundle_dir / "review" / "blind-quality-review.json")
        )
    except ValidationError as exc:
        raise BenchmarkGateError("benchmark acceptance input contract is invalid") from exc
    if not comparison_evidence_paths_are_bound(bundle_dir, comparison):
        raise BenchmarkGateError(
            "applicable benchmark dimension evidence is missing or not checksum-bound"
        )

    rubric_outcome = _base_outcome(score)
    prior_path = bundle_dir / "review" / "benchmark-acceptance.json"
    prior: CandidateBenchmarkAcceptanceV1 | None = None
    if prior_path.is_file():
        try:
            loaded = CandidateBenchmarkAcceptanceV1.model_validate(_object(prior_path))
        except ValidationError as exc:
            raise BenchmarkGateError("existing benchmark acceptance is malformed") from exc
        if loaded.candidate_sha256 != candidate_sha256:
            prior = loaded

    acceptance = evaluate_candidate_benchmark_acceptance(
        candidate_markdown=candidate,
        candidate_sha256=candidate_sha256,
        facts_hash=facts_hash,
        comparison=comparison,
        deterministic_evidence=deterministic,
        factual_review_evidence=factual,
        visitor_review_evidence=visitor,
        rubric_evidence=CandidateRubricEvidenceV1(
            candidate_sha256=candidate_sha256,
            outcome=rubric_outcome,
        ),
        predecessor_acceptance_sha256=prior.canonical_hash() if prior is not None else None,
        predecessor_acceptance=prior,
    )
    benchmark_proven = acceptance.acceptance_status == "BENCHMARK_ACCEPTANCE_PROVEN"
    final = rubric_outcome.model_copy(
        update={
            "accepted": rubric_outcome.accepted and benchmark_proven,
            "hard_disqualifier_count": (
                rubric_outcome.hard_disqualifier_count + (0 if benchmark_proven else 1)
            ),
            "benchmark_acceptance_proven": benchmark_proven,
            "benchmark_acceptance_hash": acceptance.canonical_hash(),
            "acceptance_contract_hash": portfolio_acceptance_contract_hash(),
        }
    )
    write_redacted_json(
        bundle_dir / "review" / "rubric-evaluation.json",
        {
            "rubric": score.model_dump(mode="json"),
            "outcome": final.model_dump(mode="json"),
        },
    )
    write_redacted_json(prior_path, acceptance.model_dump(mode="json"))
    completed = [str(item) for item in manifest.get("completed_stages", [])]
    for stage in ("RUBRIC_SCORED", "BENCHMARK_ACCEPTED"):
        if stage not in completed and (stage != "BENCHMARK_ACCEPTED" or benchmark_proven):
            completed.append(stage)
    manifest.update(
        {
            "benchmark_acceptance_hash": acceptance.canonical_hash(),
            "benchmark_acceptance_proven": benchmark_proven,
            "rubric_score": final.score,
            "rubric_hard_disqualifier_count": final.hard_disqualifier_count,
            "portfolio_acceptance_contract_hash": final.acceptance_contract_hash,
            "completed_stages": completed,
        }
    )
    write_local_poc_manifest(bundle_dir, manifest)
    refresh_sha256sums(bundle_dir)
    return final


__all__ = ["BenchmarkGateError", "evaluate_and_persist_benchmark_gate"]
