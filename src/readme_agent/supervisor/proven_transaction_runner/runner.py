"""Execute registered PF04 phases with durable, idempotent checkpoint reuse."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from pathlib import Path

from readme_agent.evidence.writer import refresh_sha256sums, write_redacted_json
from readme_agent.supervisor.proven_transaction_runner.contracts import (
    PHASE_ORDER,
    ProvenTransactionActionInputV1,
    ProvenTransactionActionResultV1,
    ProvenTransactionActionV1,
    ProvenTransactionCheckpointV1,
    ProvenTransactionContextV1,
    ProvenTransactionReceiptV1,
    canonical_sha256,
    utc_now_iso,
)
from readme_agent.supervisor.proven_transaction_runner.registry import (
    action_for_phase,
    registered_action_ids,
    registry_hash,
)

ActionHandler = Callable[[ProvenTransactionActionInputV1], ProvenTransactionActionResultV1]
AdmissionGuard = Callable[[], None]


def _receipt_path(output_root: Path, context: ProvenTransactionContextV1) -> Path:
    return output_root / context.context_hash / "receipt.json"


def _phase_output_path(
    output_root: Path,
    context: ProvenTransactionContextV1,
    phase: str,
) -> Path:
    return output_root / context.context_hash / "phase-outputs" / f"{phase}.json"


def _load_receipt(
    output_root: Path,
    context: ProvenTransactionContextV1,
) -> ProvenTransactionReceiptV1:
    path = _receipt_path(output_root, context)
    if not path.is_file():
        return ProvenTransactionReceiptV1(
            transaction_id=context.context_hash,
            context=context,
            registry_hash=registry_hash(),
        )
    receipt = ProvenTransactionReceiptV1.model_validate_json(path.read_text(encoding="utf-8"))
    if receipt.context != context:
        raise ValueError("stored proven-transaction receipt has context drift")
    if receipt.registry_hash != registry_hash():
        raise ValueError("stored proven-transaction receipt has action-registry drift")
    for checkpoint in receipt.checkpoints:
        if checkpoint.status != "COMPLETED":
            continue
        output_path = _phase_output_path(output_root, context, checkpoint.phase)
        if not output_path.is_file():
            raise ValueError(f"completed phase output is missing: {checkpoint.phase}")
        output = json.loads(output_path.read_text(encoding="utf-8"))
        if canonical_sha256(output) != checkpoint.output_hash:
            raise ValueError(f"completed phase output is corrupt: {checkpoint.phase}")
    return receipt


def _write_receipt(output_root: Path, receipt: ProvenTransactionReceiptV1) -> None:
    bundle = output_root / receipt.transaction_id
    write_redacted_json(bundle / "receipt.json", receipt)
    refresh_sha256sums(bundle)


def _write_phase_output(
    output_root: Path,
    action_input: ProvenTransactionActionInputV1,
    result: ProvenTransactionActionResultV1,
) -> tuple[str, dict]:
    output_path = _phase_output_path(output_root, action_input.context, action_input.phase)
    write_redacted_json(output_path, result.output)
    persisted_output = json.loads(output_path.read_text(encoding="utf-8"))
    return str(output_path), persisted_output


def _completed_by_phase(receipt: ProvenTransactionReceiptV1) -> dict[str, str]:
    return {
        checkpoint.phase: checkpoint.output_hash
        for checkpoint in receipt.checkpoints
        if checkpoint.status == "COMPLETED" and checkpoint.output_hash is not None
    }


def _attempt_for(receipt: ProvenTransactionReceiptV1, phase: str) -> int:
    return 1 + sum(1 for checkpoint in receipt.checkpoints if checkpoint.phase == phase)


def _checkpoint(
    *,
    action_input: ProvenTransactionActionInputV1,
    status: str,
    started_at: str,
    result: ProvenTransactionActionResultV1 | None = None,
    reason: str | None = None,
) -> ProvenTransactionCheckpointV1:
    output_hash = (
        canonical_sha256(result.output) if result and result.status == "COMPLETED" else None
    )
    return ProvenTransactionCheckpointV1.model_validate(
        {
            "phase": action_input.phase,
            "action_id": action_input.action_id,
            "attempt": action_input.attempt,
            "context_hash": action_input.context.context_hash,
            "input_hash": canonical_sha256(action_input.model_dump(mode="json")),
            "output_hash": output_hash,
            "status": status,
            "evidence_refs": result.evidence_refs if result else (),
            "reason": reason or (result.reason if result else None),
            "started_at": started_at,
            "completed_at": utc_now_iso(),
        }
    )


def run_proven_transaction(
    context: ProvenTransactionContextV1,
    *,
    handlers: Mapping[ProvenTransactionActionV1, ActionHandler],
    output_root: Path,
    admission_guard: AdmissionGuard | None = None,
) -> ProvenTransactionReceiptV1:
    """Resume at the first incomplete phase; never dispatch an unregistered action."""

    if admission_guard is not None:
        admission_guard()
    unknown = set(handlers) - set(registered_action_ids())
    if unknown:
        raise ValueError(f"unregistered proven-transaction handlers: {sorted(unknown)}")
    receipt = _load_receipt(output_root, context)
    completed = _completed_by_phase(receipt)
    if receipt.terminal_status == "COMPLETED":
        return receipt

    for phase in PHASE_ORDER:
        if phase in completed:
            continue
        action = action_for_phase(phase)
        handler = handlers.get(action.action_id)
        if handler is None:
            raise ValueError(f"missing handler for registered action {action.action_id}")
        action_input = ProvenTransactionActionInputV1(
            context=context,
            phase=phase,
            action_id=action.action_id,
            attempt=_attempt_for(receipt, phase),
            prior_output_hashes=dict(completed),
        )
        if admission_guard is not None:
            admission_guard()
        started_at = utc_now_iso()
        try:
            result = handler(action_input)
            if admission_guard is not None:
                admission_guard()
        except BaseException as exc:
            status = "INTERRUPTED" if isinstance(exc, (KeyboardInterrupt, SystemExit)) else "FAILED"
            checkpoint = _checkpoint(
                action_input=action_input,
                status=status,
                started_at=started_at,
                reason=f"{type(exc).__name__}: {exc}",
            )
            receipt = receipt.model_copy(update={"checkpoints": (*receipt.checkpoints, checkpoint)})
            _write_receipt(output_root, receipt)
            raise
        completed_result = result
        if result.status == "COMPLETED":
            output_path, persisted_output = _write_phase_output(output_root, action_input, result)
            completed_result = result.model_copy(
                update={
                    "output": persisted_output,
                    "evidence_refs": (*result.evidence_refs, output_path),
                }
            )
        checkpoint = _checkpoint(
            action_input=action_input,
            status=result.status,
            started_at=started_at,
            result=completed_result,
        )
        terminal_status = "BLOCKED" if result.status == "BLOCKED" else "IN_PROGRESS"
        receipt = receipt.model_copy(
            update={
                "checkpoints": (*receipt.checkpoints, checkpoint),
                "terminal_status": terminal_status,
            }
        )
        _write_receipt(output_root, receipt)
        if result.status == "BLOCKED":
            return receipt
        assert checkpoint.output_hash is not None
        completed[phase] = checkpoint.output_hash

    receipt = receipt.model_copy(update={"terminal_status": "COMPLETED"})
    receipt = ProvenTransactionReceiptV1.model_validate(receipt.model_dump(mode="json"))
    _write_receipt(output_root, receipt)
    return receipt


__all__ = ["ActionHandler", "AdmissionGuard", "run_proven_transaction"]
