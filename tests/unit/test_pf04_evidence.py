"""PF04 evidence must promote, independently accept, then replay the sealed transaction."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from readme_agent.llm.call_schema import LlmAccountingSummaryV1
from readme_agent.supervisor.portfolio_proof_engine.contracts import RubricAcceptanceOutcome
from readme_agent.supervisor.proven_transaction_runner import pf04_evidence


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def test_mission_guard_uses_the_supplied_observer_and_closes_its_backend(monkeypatch):
    calls: list[dict] = []

    class Backend:
        closed = False

        def close(self) -> None:
            self.closed = True

    backend = Backend()
    monkeypatch.setattr(
        "readme_agent.state.git_backend.default_state_backend",
        lambda: backend,
    )
    monkeypatch.setattr(
        pf04_evidence,
        "require_visible_execution_binding",
        lambda _backend, **kwargs: calls.append(kwargs),
    )

    pf04_evidence._mission_admission_guard("coordinator-7")()

    assert backend.closed is True
    assert calls == [
        {
            "task_id": pf04_evidence.TASK_ID,
            "repository": pf04_evidence.SEALED_REPOSITORY,
            "observer": "coordinator-7",
            "graph_path": pf04_evidence.MISSION_GRAPH,
        }
    ]


def test_sealed_replay_promotes_then_accepts_before_zero_call_replay(tmp_path: Path, monkeypatch):
    bundle = tmp_path / "bundle"
    candidate = bundle / "candidate" / "README.md"
    candidate.parent.mkdir(parents=True)
    candidate.write_text("# Candidate\n", encoding="utf-8")
    candidate_hash = hashlib.sha256(candidate.read_bytes()).hexdigest()
    (candidate.parent / "candidate-hash.txt").write_text(candidate_hash, encoding="utf-8")

    calls: list[tuple[str, ...]] = []

    def fake_cli(argv: list[str]) -> int:
        calls.append(tuple(argv))
        _write_json(
            bundle / "manifest.json",
            {"lifecycle_status": "NO_OP_PROVEN", "candidate_hash": candidate_hash},
        )
        _write_json(
            bundle / "review" / "no-op-proof.json",
            {
                "new_provider_call_count": 0,
                "patch_created": False,
                "duplicate_bundle_created": False,
            },
        )
        return 0

    def fake_evaluate(_org_repo: str, _backend) -> RubricAcceptanceOutcome:
        assert len(calls) == 1
        _write_json(
            bundle / "review" / "rubric-evaluation.json",
            {
                "outcome": {
                    "accepted": True,
                    "score": 30,
                    "hard_disqualifier_count": 0,
                    "benchmark_acceptance_proven": True,
                    "replay_attestation_proven": True,
                }
            },
        )
        return RubricAcceptanceOutcome(
            org_repo=pf04_evidence.SEALED_REPOSITORY,
            accepted=True,
            score=30,
            hard_disqualifier_count=0,
            benchmark_acceptance_proven=True,
            replay_attestation_proven=True,
        )

    accounting = iter(
        (
            LlmAccountingSummaryV1(status="EXACT", provider_call_count=1),
            LlmAccountingSummaryV1(status="EXACT", provider_call_count=0),
        )
    )
    monkeypatch.setattr(pf04_evidence, "_sealed_bundle", lambda: bundle)
    monkeypatch.setattr(pf04_evidence, "cli_main", fake_cli)
    monkeypatch.setattr(
        pf04_evidence,
        "current_llm_accounting_summary",
        lambda: next(accounting),
    )
    monkeypatch.setattr(
        "readme_agent.state.local_poc_backend.default_local_poc_state_backend",
        lambda: object(),
    )
    monkeypatch.setattr(
        "readme_agent.supervisor.portfolio_proof_engine.rubric.evaluate_repository",
        fake_evaluate,
    )

    output = pf04_evidence._sealed_replay()

    assert len(calls) == 2
    assert calls[0] == calls[1]
    assert output["candidate_hash"] == candidate_hash
    assert output["promotion_provider_call_counts"] == [1]
    assert output["no_op_provider_call_count"] == 0
    assert output["rubric_score"] == 30
    assert output["benchmark_acceptance_proven"] is True
    assert output["replay_attestation_proven"] is True
