"""Minimal registered runner recovery, deduplication, and safety contracts."""

from __future__ import annotations

from pathlib import Path

import pytest

from readme_agent.evidence.writer import verify_sha256sums
from readme_agent.supervisor.proven_transaction_runner.contracts import (
    PHASE_ORDER,
    ProvenTransactionActionResultV1,
    ProvenTransactionContextV1,
)
from readme_agent.supervisor.proven_transaction_runner.registry import (
    action_for_phase,
    registered_action_ids,
)
from readme_agent.supervisor.proven_transaction_runner.runner import run_proven_transaction


def _context(**updates: object) -> ProvenTransactionContextV1:
    values: dict[str, object] = {
        "task_id": "L8-PF-04-MINIMAL-GRAPH-RUNNER",
        "org_repo": "aspose-3d-foss/Aspose.3D-FOSS-for-Python",
        "source_revision": "a" * 40,
        "graph_sha256": "b" * 64,
        "dependency_hashes": {"sealed_candidate": "c" * 64},
    }
    values.update(updates)
    return ProvenTransactionContextV1(**values)


def _handlers(calls: list[str]):
    def handler(action_input):
        calls.append(action_input.action_id)
        return ProvenTransactionActionResultV1(
            status="COMPLETED",
            output={"action": action_input.action_id, "attempt": action_input.attempt},
            evidence_refs=(f"runs/{action_input.action_id}.json",),
        )

    return {action_id: handler for action_id in registered_action_ids()}


def test_registry_is_exactly_ordered_and_has_no_product_effect_authority():
    assert tuple(action_for_phase(phase).action_id for phase in PHASE_ORDER) == (
        "observe_current_external_blocks",
        "adapt_smallest_resolver_seam",
        "replay_affected_fact_stages",
        "replay_sealed_transaction",
    )
    assert all(not action_for_phase(phase).product_effect_authority for phase in PHASE_ORDER)
    assert all(action_for_phase(phase).permission != "remote_write" for phase in PHASE_ORDER)


def test_runner_executes_all_phases_once_and_reuses_complete_receipt(tmp_path: Path):
    calls: list[str] = []
    context = _context()
    first = run_proven_transaction(context, handlers=_handlers(calls), output_root=tmp_path)
    replay = run_proven_transaction(context, handlers=_handlers(calls), output_root=tmp_path)
    assert first.terminal_status == replay.terminal_status == "COMPLETED"
    assert calls == list(registered_action_ids())
    assert verify_sha256sums(tmp_path / context.context_hash)


def test_admission_guard_wraps_every_phase_and_prevents_unowned_dispatch(tmp_path: Path):
    calls: list[str] = []
    guard_calls: list[str] = []

    run_proven_transaction(
        _context(),
        handlers=_handlers(calls),
        output_root=tmp_path,
        admission_guard=lambda: guard_calls.append("checked"),
    )

    assert calls == list(registered_action_ids())
    assert len(guard_calls) == 1 + (2 * len(PHASE_ORDER))

    blocked_calls: list[str] = []

    def reject() -> None:
        raise RuntimeError("expired mission claim")

    with pytest.raises(RuntimeError, match="expired mission claim"):
        run_proven_transaction(
            _context(source_revision="d" * 40),
            handlers=_handlers(blocked_calls),
            output_root=tmp_path,
            admission_guard=reject,
        )
    assert blocked_calls == []


def test_interruption_resumes_at_first_incomplete_phase(tmp_path: Path):
    calls: list[str] = []
    handlers = _handlers(calls)
    interrupted = "replay_affected_fact_stages"
    original = handlers[interrupted]

    def interrupt_once(action_input):
        calls.append(action_input.action_id)
        raise KeyboardInterrupt("injected cancellation")

    handlers[interrupted] = interrupt_once
    with pytest.raises(KeyboardInterrupt):
        run_proven_transaction(_context(), handlers=handlers, output_root=tmp_path)
    handlers[interrupted] = original
    receipt = run_proven_transaction(_context(), handlers=handlers, output_root=tmp_path)
    assert receipt.terminal_status == "COMPLETED"
    assert calls[:3] == [
        "observe_current_external_blocks",
        "adapt_smallest_resolver_seam",
        "replay_affected_fact_stages",
    ]
    assert calls.count("observe_current_external_blocks") == 1
    assert calls.count("adapt_smallest_resolver_seam") == 1
    assert calls.count("replay_affected_fact_stages") == 2


def test_blocked_phase_prevents_downstream_dispatch(tmp_path: Path):
    calls: list[str] = []
    handlers = _handlers(calls)

    def blocked(action_input):
        calls.append(action_input.action_id)
        return ProvenTransactionActionResultV1(
            status="BLOCKED",
            output={},
            reason="source revision has not changed",
        )

    handlers["replay_affected_fact_stages"] = blocked
    receipt = run_proven_transaction(_context(), handlers=handlers, output_root=tmp_path)
    assert receipt.terminal_status == "BLOCKED"
    assert "replay_sealed_transaction" not in calls


def test_changed_dependency_identity_creates_a_distinct_transaction(tmp_path: Path):
    calls: list[str] = []
    first = _context()
    second = _context(dependency_hashes={"sealed_candidate": "d" * 64})
    run_proven_transaction(first, handlers=_handlers(calls), output_root=tmp_path)
    run_proven_transaction(second, handlers=_handlers(calls), output_root=tmp_path)
    assert first.context_hash != second.context_hash
    assert len(calls) == 8


def test_unregistered_and_missing_handlers_fail_closed(tmp_path: Path):
    with pytest.raises(ValueError, match="unregistered"):
        run_proven_transaction(
            _context(),
            handlers={"not_registered": lambda _input: None},  # type: ignore[dict-item]
            output_root=tmp_path,
        )
    with pytest.raises(ValueError, match="missing handler"):
        run_proven_transaction(_context(), handlers={}, output_root=tmp_path)


def test_corrupt_receipt_is_not_silently_restarted(tmp_path: Path):
    context = _context()
    receipt = tmp_path / context.context_hash / "receipt.json"
    receipt.parent.mkdir(parents=True)
    receipt.write_text("{not-json", encoding="utf-8")
    with pytest.raises(ValueError):
        run_proven_transaction(context, handlers=_handlers([]), output_root=tmp_path)


@pytest.mark.parametrize("mutation", ["missing", "corrupt"])
def test_completed_phase_output_must_remain_available_and_hash_valid(tmp_path: Path, mutation: str):
    context = _context()
    run_proven_transaction(context, handlers=_handlers([]), output_root=tmp_path)
    output = (
        tmp_path / context.context_hash / "phase-outputs" / "OBSERVE_CURRENT_EXTERNAL_BLOCKS.json"
    )
    if mutation == "missing":
        output.unlink()
    else:
        output.write_text('{"action":"changed"}\n', encoding="utf-8")

    with pytest.raises(ValueError, match=f"completed phase output is {mutation}"):
        run_proven_transaction(context, handlers=_handlers([]), output_root=tmp_path)
