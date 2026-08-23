"""Provider and effect phases for sealed transaction replay attestation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from readme_agent.verification.sealed_transaction_replay_attestor_state import _AttestationState
from readme_agent.verification.sealed_transaction_replay_contracts import (
    ReplayAttestationContractV1,
)
from readme_agent.verification.sealed_transaction_replay_effects import _build_effect_delta
from readme_agent.verification.sealed_transaction_replay_provider import _build_provider_delta
from readme_agent.verification.sealed_transaction_replay_results import (
    ProductEffectDeltaV1,
    ProviderLedgerDeltaV1,
    ReplayArtifactInventoryV1,
    ReplayDriftFindingV1,
)


def _attest_provider_and_effects(
    state: _AttestationState,
    expected_contract: ReplayAttestationContractV1,
    first_bundle_root: Path,
    replay_bundle_root: Path,
    first_parsed: dict[str, Any],
    replay_parsed: dict[str, Any],
    first_inventory: ReplayArtifactInventoryV1,
    replay_inventory: ReplayArtifactInventoryV1,
) -> tuple[ProviderLedgerDeltaV1, ProductEffectDeltaV1]:
    provider_delta = _build_provider_delta(
        expected_contract, first_bundle_root, replay_bundle_root, first_parsed, replay_parsed
    )
    state.record(
        "ledger_files_present",
        provider_delta.ledger_load_error is None,
        str(provider_delta.ledger_load_error),
    )
    state.record(
        "ledger_records_parse",
        provider_delta.ledger_load_error is None,
        str(provider_delta.ledger_load_error),
    )
    state.record(
        "ledger_accounting_status_exact",
        provider_delta.first_declared_status == "EXACT"
        and provider_delta.replay_declared_status == "EXACT",
        f"non-EXACT accounting: first={provider_delta.first_declared_status} "
        f"replay={provider_delta.replay_declared_status}",
    )
    state.record(
        "declared_accounting_matches_recomputed",
        provider_delta.declared_accounting_consistent,
        "declared accounting fields disagree with independently recomputed ledger",
    )
    state.record(
        "ledger_boundaries_coherent",
        provider_delta.ledger_superset_ok
        and provider_delta.ledger_temporal_ok
        and provider_delta.ledger_scope_ok
        and not provider_delta.replay_disallowed_dispositions,
        "replay ledger is not a coherent, temporally-consistent superset of the first ledger",
    )
    state.record(
        "no_unclassified_provider_jobs",
        not provider_delta.replay_unclassified_jobs,
        f"unclassified provider job(s): {provider_delta.replay_unclassified_jobs}",
    )
    state.record(
        "no_reused_call_drift",
        not provider_delta.model_drift_axes and not provider_delta.sampling_drift_axes,
        f"model_drift={provider_delta.model_drift_axes} "
        f"sampling_drift={provider_delta.sampling_drift_axes}",
    )
    for axis in provider_delta.model_drift_axes:
        state.findings.append(
            ReplayDriftFindingV1(
                code=f"model_drift:{axis}",
                stage="AUTHORING" if axis == "authoring" else "REVIEW",
                detail=f"reused ledger record's model changed for axis {axis}",
            )
        )
    for axis in provider_delta.sampling_drift_axes:
        state.findings.append(
            ReplayDriftFindingV1(
                code=f"sampling_drift:{axis}",
                stage="AUTHORING" if axis == "authoring" else "REVIEW",
                detail=f"reused ledger record's request changed for axis {axis}",
            )
        )
    if provider_delta.accounting_certain:
        state.record(
            "replay_provider_calls_zero", provider_delta.first_provider_call_count is not None
        )
        for axis, count, code in (
            ("authoring", provider_delta.replay_authoring_calls, "AUTHORING"),
            ("factual_review", provider_delta.replay_factual_review_calls, "REVIEW"),
            ("visitor_review", provider_delta.replay_visitor_review_calls, "REVIEW"),
            ("repair", provider_delta.replay_repair_calls, "REVIEW"),
        ):
            ok = count == 0
            state.record(
                f"replay_{axis}_calls_zero", ok, f"replay made {count} new {axis} provider call(s)"
            )
            if not ok:
                state.findings.append(
                    ReplayDriftFindingV1(
                        code=f"new_provider_call:{axis}",
                        stage=code,  # type: ignore[arg-type]
                        detail=f"replay made {count} new {axis} provider call(s)",
                    )
                )
    else:
        for axis in ("authoring", "factual_review", "visitor_review", "repair"):
            state.record(f"replay_{axis}_calls_zero", False, "provider accounting is not certain")
        state.findings.append(
            ReplayDriftFindingV1(
                code="provider_ledger_missing",
                stage="SEALING",
                detail="ledger accounting is not certain",
            )
        )
    if provider_delta.replay_unclassified_jobs:
        state.findings.append(
            ReplayDriftFindingV1(
                code="unmapped_job",
                stage="AUTHORING",
                detail=f"unmapped job(s): {provider_delta.replay_unclassified_jobs}",
            )
        )
    if provider_delta.declared_accounting_consistent is False:
        state.findings.append(
            ReplayDriftFindingV1(
                code="provider_accounting_not_exact",
                stage="SEALING",
                detail="declared accounting inconsistent",
            )
        )
    if not provider_delta.accounting_certain and provider_delta.ledger_load_error:
        state.findings.append(
            ReplayDriftFindingV1(
                code="provider_accounting_not_exact",
                stage="SEALING",
                detail=str(provider_delta.ledger_load_error),
            )
        )

    effect_delta = _build_effect_delta(
        expected_contract, first_parsed, replay_parsed, first_inventory, replay_inventory
    )
    state.record(
        "product_effects_proven_absent",
        not effect_delta.violated and not effect_delta.unproven,
        f"effects violated={effect_delta.violated} unproven={effect_delta.unproven}",
    )
    state.record(
        "no_duplicate_lifecycle_effect",
        "duplicate_lifecycle_effect" not in effect_delta.violated,
        f"duplicate lifecycle paths: {effect_delta.duplicate_lifecycle_paths}",
    )
    state.record(
        "target_tree_unchanged",
        effect_delta.target_tree_digest_first == effect_delta.target_tree_digest_replay
        or effect_delta.target_tree_digest_first is None
        or effect_delta.target_tree_digest_replay is None,
        "target tree digest changed between transactions",
    )
    for effect in effect_delta.violated:
        state.findings.append(
            ReplayDriftFindingV1(
                code="product_effect_observed", stage="EFFECTS", detail=f"effect observed: {effect}"
            )
        )
    for effect in effect_delta.unproven:
        state.findings.append(
            ReplayDriftFindingV1(
                code="effect_evidence_missing",
                stage="EFFECTS",
                detail=f"effect evidence missing: {effect}",
            )
        )
    return provider_delta, effect_delta
