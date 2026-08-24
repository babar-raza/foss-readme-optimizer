"""Closed action registry for the four PF04 runner phases."""

from __future__ import annotations

from readme_agent.supervisor.proven_transaction_runner.contracts import (
    PHASE_ORDER,
    ProvenTransactionActionV1,
    ProvenTransactionPhaseV1,
    RegisteredTransactionActionV1,
    canonical_sha256,
)

_ACTIONS: tuple[RegisteredTransactionActionV1, ...] = (
    RegisteredTransactionActionV1(
        action_id="observe_current_external_blocks",
        phase="OBSERVE_CURRENT_EXTERNAL_BLOCKS",
        permission="read_only_local",
        input_model="ProvenTransactionActionInputV1",
        output_model="ProvenTransactionActionResultV1",
        retryable=True,
    ),
    RegisteredTransactionActionV1(
        action_id="adapt_smallest_resolver_seam",
        phase="ADAPT_SMALLEST_RESOLVER_SEAM",
        permission="read_only_local",
        input_model="ProvenTransactionActionInputV1",
        output_model="ProvenTransactionActionResultV1",
        retryable=True,
    ),
    RegisteredTransactionActionV1(
        action_id="replay_affected_fact_stages",
        phase="REPLAY_AFFECTED_FACT_STAGES",
        permission="local_write",
        input_model="ProvenTransactionActionInputV1",
        output_model="ProvenTransactionActionResultV1",
        retryable=True,
    ),
    RegisteredTransactionActionV1(
        action_id="replay_sealed_transaction",
        phase="REPLAY_SEALED_TRANSACTION",
        permission="local_write",
        input_model="ProvenTransactionActionInputV1",
        output_model="ProvenTransactionActionResultV1",
        retryable=True,
    ),
)

_BY_PHASE = {action.phase: action for action in _ACTIONS}
_BY_ID = {action.action_id: action for action in _ACTIONS}
if len(_BY_PHASE) != len(_ACTIONS) or len(_BY_ID) != len(_ACTIONS):
    raise RuntimeError("proven-transaction action IDs and phases must be unique")
if tuple(action.phase for action in _ACTIONS) != PHASE_ORDER:
    raise RuntimeError("proven-transaction registry must match the declared phase order")
if any(action.product_effect_authority for action in _ACTIONS):
    raise RuntimeError("PF04 actions cannot have product-effect authority")


def action_for_phase(phase: ProvenTransactionPhaseV1) -> RegisteredTransactionActionV1:
    return _BY_PHASE[phase]


def registered_action_ids() -> tuple[ProvenTransactionActionV1, ...]:
    return tuple(action.action_id for action in _ACTIONS)


def registry_hash() -> str:
    return canonical_sha256([action.model_dump(mode="json") for action in _ACTIONS])


__all__ = ["action_for_phase", "registered_action_ids", "registry_hash"]
