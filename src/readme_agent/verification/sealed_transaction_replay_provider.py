"""Provider-ledger delta proof for sealed transaction replay attestation."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from readme_agent.llm.call_ledger import load_llm_call_records, summarize_llm_call_records
from readme_agent.llm.call_schema import LlmCallRecordV1
from readme_agent.verification.sealed_transaction_replay_contracts import (
    ReplayAttestationContractV1,
)
from readme_agent.verification.sealed_transaction_replay_json import (
    _resolve_pointer,
    canonical_json_sha256,
)
from readme_agent.verification.sealed_transaction_replay_paths import _resolve_declared_path
from readme_agent.verification.sealed_transaction_replay_results import ProviderLedgerDeltaV1
from readme_agent.verification.sealed_transaction_replay_vocabulary import (
    KNOWN_PROVIDER_JOB_AXES,
    ProviderCallAxisV1,
)


def _classify_job(
    job: str, extra: dict[str, tuple[ProviderCallAxisV1, ...]]
) -> tuple[ProviderCallAxisV1, ...] | None:
    if job in extra:
        return extra[job]
    return KNOWN_PROVIDER_JOB_AXES.get(job)


def _load_ledger(
    root: Path, contract: ReplayAttestationContractV1, artifact_id: str
) -> tuple[list[LlmCallRecordV1] | None, Path | None, str | None]:
    artifact = next((a for a in contract.artifacts if a.artifact_id == artifact_id), None)
    if artifact is None:
        return None, None, "ledger_artifact_undeclared"
    resolved = _resolve_declared_path(root, artifact.relative_path)
    if resolved is None or not resolved.is_file():
        return None, None, "ledger_file_missing"
    try:
        records = load_llm_call_records(resolved)
    except (RuntimeError, ValueError, OSError, UnicodeError) as exc:
        return None, resolved, str(exc)
    return records, resolved, None


def _build_provider_delta(
    contract: ReplayAttestationContractV1,
    first_root: Path,
    replay_root: Path,
    first_parsed: dict[str, Any],
    replay_parsed: dict[str, Any],
) -> ProviderLedgerDeltaV1:
    proof = contract.provider_proof
    extra_jobs = dict(proof.additional_known_jobs)

    first_records, first_path, first_error = _load_ledger(
        first_root, contract, proof.first_ledger_artifact_id
    )
    replay_records, replay_path, replay_error = _load_ledger(
        replay_root, contract, proof.replay_ledger_artifact_id
    )

    ledger_load_error = first_error or replay_error
    if first_records is None or replay_records is None:
        return ProviderLedgerDeltaV1(
            ledger_load_error=ledger_load_error,
            accounting_certain=False,
            delta_digest=canonical_json_sha256({"error": ledger_load_error}),
        )

    if proof.require_non_empty_first_ledger and not first_records:
        return ProviderLedgerDeltaV1(
            ledger_load_error="first_ledger_empty",
            accounting_certain=False,
            delta_digest=canonical_json_sha256({"error": "first_ledger_empty"}),
        )

    recomputed_first = summarize_llm_call_records(first_records, ledger_path=first_path)
    recomputed_replay = summarize_llm_call_records(replay_records, ledger_path=replay_path)
    first_relative = next(
        a.relative_path
        for a in contract.artifacts
        if a.artifact_id == proof.first_ledger_artifact_id
    )
    replay_relative = next(
        a.relative_path
        for a in contract.artifacts
        if a.artifact_id == proof.replay_ledger_artifact_id
    )
    recomputed_first = recomputed_first.model_copy(update={"ledger_path": first_relative})
    recomputed_replay = recomputed_replay.model_copy(update={"ledger_path": replay_relative})

    first_declaration_doc = first_parsed.get(proof.first_declaration.artifact_id)
    replay_declaration_doc = replay_parsed.get(proof.replay_declaration.artifact_id)
    _, first_declared_status = (
        _resolve_pointer(first_declaration_doc, proof.first_declaration.status_pointer)
        if first_declaration_doc is not None
        else (False, None)
    )
    _, replay_declared_status = (
        _resolve_pointer(replay_declaration_doc, proof.replay_declaration.status_pointer)
        if replay_declaration_doc is not None
        else (False, None)
    )

    accounting_certain = (
        recomputed_first.status == "EXACT"
        and recomputed_replay.status == "EXACT"
        and first_declared_status == "EXACT"
        and replay_declared_status == "EXACT"
    )

    declared_accounting_consistent = True
    if accounting_certain and first_declaration_doc is not None:
        _, declared_count = _resolve_pointer(
            first_declaration_doc, proof.first_declaration.call_count_pointer
        )
        if declared_count is not None and declared_count != recomputed_first.provider_call_count:
            declared_accounting_consistent = False
    if accounting_certain and replay_declaration_doc is not None:
        _, declared_count = _resolve_pointer(
            replay_declaration_doc, proof.replay_declaration.call_count_pointer
        )
        if declared_count is not None and declared_count != recomputed_replay.provider_call_count:
            declared_accounting_consistent = False
    accounting_certain = accounting_certain and declared_accounting_consistent

    first_by_id = {record.call_id: record for record in first_records}
    replay_by_id = {record.call_id: record for record in replay_records}

    ledger_superset_ok = True
    model_drift_axes: set[ProviderCallAxisV1] = set()
    sampling_drift_axes: set[ProviderCallAxisV1] = set()
    missing_reused_call_ids: list[str] = []
    if proof.require_ledger_superset:
        for call_id, record in first_by_id.items():
            other = replay_by_id.get(call_id)
            if other is None:
                ledger_superset_ok = False
                missing_reused_call_ids.append(call_id)
                continue
            if other.model_dump(mode="json") == record.model_dump(mode="json"):
                continue
            ledger_superset_ok = False
            reused_axes = _classify_job(record.job, extra_jobs) or ()
            if record.prompt_sha256 == other.prompt_sha256 and record.model != other.model:
                model_drift_axes.update(reused_axes)
            elif (
                record.prompt_sha256 == other.prompt_sha256
                and record.model == other.model
                and record.request_sha256 != other.request_sha256
            ):
                sampling_drift_axes.update(reused_axes)

    new_ids = sorted(set(replay_by_id) - set(first_by_id))
    disallowed_dispositions: list[str] = []
    for call_id in new_ids:
        record = replay_by_id[call_id]
        if record.disposition not in proof.allowed_replay_dispositions:
            disallowed_dispositions.append(call_id)

    ledger_scope_ok = True
    for call_id in new_ids:
        record = replay_by_id[call_id]
        if (
            record.org_repo != contract.org_repo
            or record.source_revision != contract.expected_source_revision
        ):
            ledger_scope_ok = False

    ledger_temporal_ok = True
    if proof.require_temporal_coherence and first_records:
        try:
            latest_first_finish = max(
                datetime.fromisoformat(record.finished_at) for record in first_records
            )
            for call_id in new_ids:
                started = datetime.fromisoformat(replay_by_id[call_id].started_at)
                if started < latest_first_finish:
                    ledger_temporal_ok = False
                    break
        except (ValueError, TypeError):
            ledger_temporal_ok = False

    axis_counts: dict[ProviderCallAxisV1, int] = {
        "authoring": 0,
        "factual_review": 0,
        "visitor_review": 0,
        "repair": 0,
        "other": 0,
    }
    unclassified: list[str] = []
    for call_id in new_ids:
        record = replay_by_id[call_id]
        axes = _classify_job(record.job, extra_jobs)
        if axes is None:
            # An unrecognized job is unaccounted evidence regardless of disposition -- even a
            # cache_reuse/fixture record with an unmapped job fails closed, never a free pass.
            unclassified.append(record.job)
            continue
        if record.disposition != "provider_call":
            continue
        for axis in axes:
            axis_counts[axis] += 1

    # A disallowed disposition (e.g. a new provider_call where only cache_reuse is expected) is a
    # CERTAIN, fully-classified violation -- it must not be folded into "uncertain", or the
    # specific new_provider_call:<axis> finding below would never fire, replaced by a generic
    # "accounting is not certain" failure that hides which role actually made the new call. An
    # unmapped job is different: it genuinely IS uncertainty (we cannot classify what happened).
    accounting_certain = (
        accounting_certain
        and ledger_superset_ok
        and ledger_scope_ok
        and ledger_temporal_ok
        and not unclassified
    )

    new_provider_call_ids = sorted(
        call_id for call_id in new_ids if replay_by_id[call_id].disposition == "provider_call"
    )
    new_cache_reuse_count = sum(
        1 for call_id in new_ids if replay_by_id[call_id].disposition == "cache_reuse"
    )

    return ProviderLedgerDeltaV1(
        first_declared_status=first_declared_status
        if isinstance(first_declared_status, str)
        else None,
        replay_declared_status=replay_declared_status
        if isinstance(replay_declared_status, str)
        else None,
        recomputed_first=recomputed_first if accounting_certain else None,
        recomputed_replay=recomputed_replay if accounting_certain else None,
        first_provider_call_count=recomputed_first.provider_call_count
        if accounting_certain
        else None,
        replay_provider_call_count=recomputed_replay.provider_call_count
        if accounting_certain
        else None,
        replay_new_provider_call_ids=tuple(new_provider_call_ids) if accounting_certain else (),
        replay_new_cache_reuse_count=new_cache_reuse_count if accounting_certain else None,
        replay_authoring_calls=axis_counts["authoring"] if accounting_certain else 0,
        replay_factual_review_calls=axis_counts["factual_review"] if accounting_certain else 0,
        replay_visitor_review_calls=axis_counts["visitor_review"] if accounting_certain else 0,
        replay_repair_calls=axis_counts["repair"] if accounting_certain else 0,
        replay_other_calls=axis_counts["other"] if accounting_certain else 0,
        replay_unclassified_jobs=tuple(sorted(set(unclassified))),
        replay_disallowed_dispositions=tuple(sorted(set(disallowed_dispositions))),
        ledger_superset_ok=ledger_superset_ok,
        ledger_temporal_ok=ledger_temporal_ok,
        ledger_scope_ok=ledger_scope_ok,
        declared_accounting_consistent=declared_accounting_consistent,
        model_drift_axes=tuple(sorted(model_drift_axes)),
        sampling_drift_axes=tuple(sorted(sampling_drift_axes)),
        missing_reused_call_ids=tuple(sorted(set(missing_reused_call_ids))),
        ledger_load_error=None,
        accounting_certain=accounting_certain,
        delta_digest=canonical_json_sha256(
            {
                "new_ids": new_ids,
                "axis_counts": sorted(axis_counts.items()),
                "unclassified": sorted(set(unclassified)),
                "certain": accounting_certain,
                "model_drift": sorted(model_drift_axes),
                "sampling_drift": sorted(sampling_drift_axes),
            }
        ),
    )
