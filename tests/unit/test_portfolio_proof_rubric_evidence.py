"""Regression tests for current-schema portfolio rubric evidence."""

from __future__ import annotations

import json

from readme_agent.supervisor.portfolio_proof_engine import replay_gate
from readme_agent.supervisor.portfolio_proof_engine.evidence_bundle import (
    CompleteTransactionReplayAttestationV1,
    EvidenceBundleV1,
)
from readme_agent.supervisor.portfolio_proof_engine.rubric_evidence import (
    accepted_fact,
    checks_complete,
    reconciliation_integrity,
    repeatable_acceptance,
    replay_bound_rubric_evaluation,
)
from readme_agent.verification.sealed_transaction_replay import (
    CompleteTransactionNoOpProofV1,
    ReplayAttestationContractV1,
)
from tests.unit.test_portfolio_proof_engine_dashboard import (
    _CANDIDATE_HASH,
    _REV,
    _terminal_acceptance_artifacts,
)


def _bundle(**overrides: object) -> EvidenceBundleV1:
    return EvidenceBundleV1(
        org_repo="acme/widget",
        source_revision="a" * 40,
        candidate_hash="b" * 64,
        bundle_dir="runs/readme-poc/acme__widget/revision",
        **overrides,
    )


def _facts(*, conflict_status: str | None) -> dict:
    conflicts = [] if conflict_status is None else [{"status": conflict_status}]
    return {
        "selected_fact_ids": {"product.formats": "fact-formats"},
        "facts": [
            {
                "fact_id": "fact-formats",
                "field": "product.formats",
                "verification_state": "verified",
                "conflicts": conflicts,
            }
        ],
    }


def test_resolved_fact_conflict_is_accepted_but_unresolved_conflict_is_not() -> None:
    assert accepted_fact(_bundle(facts=_facts(conflict_status="resolved")), "product.formats")
    assert not accepted_fact(_bundle(facts=_facts(conflict_status="unresolved")), "product.formats")


def test_blocking_check_skip_cannot_satisfy_check_coverage() -> None:
    coverage = {
        "entries": [
            {"check_id": "check_banner_present", "blocking": True, "outcome": "skip"},
            {"check_id": "check_links", "blocking": True, "outcome": "pass"},
        ]
    }

    assert checks_complete(_bundle(check_coverage=coverage)) is False


def test_reconciliation_requires_evidence_for_changed_source_bytes() -> None:
    source = "Original source sentence."
    reconciliation = {
        "source_bytes": len(source.encode("utf-8")),
        "entries": [
            {
                "source_byte_start": 0,
                "source_byte_end": len(source.encode("utf-8")),
                "disposition": "corrected",
                "rationale": "The verified fact supersedes the source claim.",
                "evidence": [],
            }
        ],
    }

    assert (
        reconciliation_integrity(_bundle(source_readme=source, reconciliation=reconciliation))
        is False
    )
    reconciliation["entries"][0]["evidence"] = [{"fact_id": "fact-1"}]
    assert (
        reconciliation_integrity(_bundle(source_readme=source, reconciliation=reconciliation))
        is True
    )


def test_no_op_requires_exact_zero_provider_call_accounting() -> None:
    proof = {
        "verdict": "NO_OP_PROVEN",
        "candidate_hash": "b" * 64,
        "patch_created": False,
        "duplicate_bundle_created": False,
        "llm_accounting_status": "EXACT",
        "new_provider_call_count": 1,
        "acceptance_binding": {"contract_hash": "c" * 64},
    }

    assert repeatable_acceptance(_bundle(no_op_proof=proof)) is False
    proof["new_provider_call_count"] = 0
    assert repeatable_acceptance(_bundle(no_op_proof=proof)) is True


def test_replay_result_is_persisted_into_terminal_rubric_outcome() -> None:
    artifacts, _ = _terminal_acceptance_artifacts("acme/widget", _REV, _CANDIDATE_HASH)
    attestation = CompleteTransactionReplayAttestationV1.model_validate(
        artifacts["replay_attestation"]
    )
    proof: CompleteTransactionNoOpProofV1 = attestation.proof
    evaluation = {
        "rubric": {"total_score": 30},
        "outcome": {
            "org_repo": "acme/widget",
            "accepted": True,
            "score": 30,
            "hard_disqualifier_count": 0,
            "missing_evidence_criteria": [],
            "benchmark_acceptance_proven": True,
            "benchmark_acceptance_hash": "a" * 64,
        },
    }

    updated = replay_bound_rubric_evaluation(evaluation, proof)

    assert updated["outcome"]["accepted"] is True
    assert updated["outcome"]["replay_attestation_proven"] is True
    assert updated["outcome"]["replay_attestation_hash"] == proof.proof_hash
    assert updated["outcome"]["acceptance_contract_hash"] is not None


def test_replay_gate_rewrites_the_persisted_rubric_with_terminal_evidence(
    tmp_path, monkeypatch
) -> None:
    artifacts, manifest_bindings = _terminal_acceptance_artifacts(
        "acme/widget", _REV, _CANDIDATE_HASH
    )
    attestation = CompleteTransactionReplayAttestationV1.model_validate(
        artifacts["replay_attestation"]
    )
    contract = ReplayAttestationContractV1.model_validate(artifacts["replay_contract"])
    bundle_dir = tmp_path / "bundle"
    review_dir = bundle_dir / "review"
    review_dir.mkdir(parents=True)
    rubric = artifacts["rubric_evaluation"]
    rubric["outcome"]["replay_attestation_proven"] = None
    rubric["outcome"]["replay_attestation_hash"] = None
    (review_dir / "rubric-evaluation.json").write_text(json.dumps(rubric), encoding="utf-8")
    (bundle_dir / "manifest.json").write_text(
        json.dumps(
            {
                **manifest_bindings,
                "completed_stages": ["RUBRIC_SCORED", "BENCHMARK_ACCEPTED"],
            }
        ),
        encoding="utf-8",
    )
    first = tmp_path / "first"
    replay = tmp_path / "replay"
    first.mkdir()
    replay.mkdir()
    monkeypatch.setattr(replay_gate, "first_snapshot_path", lambda _: first)
    monkeypatch.setattr(replay_gate, "materialize_transaction_snapshot", lambda *_a, **_k: replay)
    monkeypatch.setattr(replay_gate, "derive_local_poc_replay_contract", lambda **_k: contract)
    monkeypatch.setattr(
        replay_gate, "attest_complete_transaction_noop", lambda **_k: attestation.proof
    )
    monkeypatch.setattr(replay_gate, "refresh_sha256sums", lambda _path: None)

    replay_gate.attest_and_persist_replay_gate(bundle_dir)

    persisted = json.loads((review_dir / "rubric-evaluation.json").read_text(encoding="utf-8"))
    assert persisted["outcome"]["accepted"] is True
    assert persisted["outcome"]["replay_attestation_proven"] is True
    assert persisted["outcome"]["replay_attestation_hash"] == attestation.proof.proof_hash
