"""Bind PF04 runner phases to current fact receipts and the canonical supervisor."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path

from readme_agent.facts.acceptance_contract import current_fact_acceptance_contract
from readme_agent.facts.external_fact_block_adapters import (
    ExternalFactResolutionDecisionV1,
    resolve_fact_record_block,
)
from readme_agent.facts.external_fact_block_contracts import ExternalFactBlockResolutionV1
from readme_agent.registry.loader import require_listed
from readme_agent.supervisor.proven_transaction_runner.contracts import (
    ProvenTransactionActionInputV1,
    ProvenTransactionActionResultV1,
    ProvenTransactionActionV1,
    canonical_sha256,
)
from readme_agent.supervisor.proven_transaction_runner.pf04_case_evidence import (
    ExternalFactReplayCaseV1,
    build_pf04_case_bindings,
    load_pf04_case,
    resolve_current_case,
)

ActionHandler = Callable[[ProvenTransactionActionInputV1], ProvenTransactionActionResultV1]
SealedReplay = Callable[[], dict]


def _decision_record(decision: ExternalFactResolutionDecisionV1) -> dict:
    return {
        "org_repo": decision.block.org_repo,
        "source_revision": decision.block.source_revision,
        "fact_id": decision.fact_id,
        "fact_surface": decision.block.fact_surface,
        "diagnostic_code": decision.block.diagnostic_code,
        "block_class": decision.resolution.block_class,
        "wording_mode": decision.resolution.wording_mode,
        "resolution_hash": decision.resolution.resolution_hash,
        "retry_recommended": decision.resolution.retry_recommended,
        "recovery_action": decision.recovery_action,
        "blocked_category": decision.blocked_category,
        "responsible_owner": decision.responsible_owner,
        "affected_scope": decision.affected_scope,
        "missing_evidence": decision.missing_evidence,
        "resume_predicate": decision.resolution.resume_predicate,
    }


def build_pf04_handlers(
    cases: tuple[ExternalFactReplayCaseV1, ...],
    *,
    runs_root: Path,
    sealed_replay: SealedReplay,
    case_bindings: dict[str, dict] | None = None,
    recovery_proof: dict | None = None,
    recovery_proof_path: Path | None = None,
) -> Mapping[ProvenTransactionActionV1, ActionHandler]:
    """Return the four exact PF04 handlers; no arbitrary command handler is accepted."""

    loaded_cases = tuple(load_pf04_case(case, runs_root) for case in cases)
    current_bindings = case_bindings or build_pf04_case_bindings(cases, runs_root=runs_root)
    first_decisions: dict[str, ExternalFactResolutionDecisionV1] = {}

    def observe(_action_input: ProvenTransactionActionInputV1) -> ProvenTransactionActionResultV1:
        blocks: list[dict] = []
        evidence_refs: list[str] = []
        for loaded in loaded_cases:
            decisions = resolve_current_case(loaded)
            blocks.extend(_decision_record(decision) for decision in decisions)
            evidence_refs.extend(
                (
                    str(loaded.bundle_dir / "source" / "revision.json"),
                    str(loaded.bundle_dir / "facts" / "product-facts.json"),
                    str(loaded.bundle_dir / "facts" / "findings.json"),
                    str(loaded.bundle_dir / "manifest.json"),
                )
            )
        if recovery_proof_path is not None:
            evidence_refs.append(str(recovery_proof_path))
        return ProvenTransactionActionResultV1(
            status="COMPLETED",
            output={
                "case_count": len(loaded_cases),
                "block_count": len(blocks),
                "blocks": blocks,
                "case_receipt_bindings": current_bindings,
                "canonical_recovery_proof": recovery_proof,
            },
            evidence_refs=tuple(evidence_refs),
        )

    def adapt(_action_input: ProvenTransactionActionInputV1) -> ProvenTransactionActionResultV1:
        records = []
        for loaded in loaded_cases:
            for decision in resolve_current_case(loaded):
                if decision.resolution.wording_mode in {"assert", "omit", "not_applicable"}:
                    raise ValueError(
                        "PF04 must not assert or silently omit a currently blocked external fact"
                    )
                first_decisions[decision.block.block_id] = decision
                records.append(_decision_record(decision))
        return ProvenTransactionActionResultV1(
            status="COMPLETED",
            output={
                "case_count": len(loaded_cases),
                "decision_count": len(records),
                "decision_matrix_sha256": canonical_sha256(records),
                "decisions": records,
            },
        )

    def replay(_action_input: ProvenTransactionActionInputV1) -> ProvenTransactionActionResultV1:
        records = []
        for loaded in loaded_cases:
            current_by_block = {
                decision.block.block_id: decision for decision in resolve_current_case(loaded)
            }
            entry = require_listed(loaded.case.org_repo)
            contract = current_fact_acceptance_contract(
                entry.ecosystem,
                getattr(entry, "family", None),
            )
            for field in loaded.case.expected_surfaces:
                fact = loaded.facts.selected_fact(field)
                block_id = f"{loaded.case.org_repo}@{loaded.case.source_revision}:{fact.fact_id}"
                previous = first_decisions.get(block_id) or current_by_block[block_id]
                repeated = resolve_fact_record_block(
                    fact,
                    facts=loaded.facts,
                    snapshot=loaded.snapshot,
                    contract=contract,
                    previous_resolution=ExternalFactBlockResolutionV1.model_validate(
                        previous.resolution.model_dump(mode="json")
                    ),
                )
                if repeated.resolution.fingerprint_changed_since_previous_resolution is not False:
                    raise ValueError("unchanged PF04 dependency fingerprint was not recognized")
                if repeated.resolution.retry_recommended:
                    raise ValueError("unchanged PF04 external block scheduled a duplicate retry")
                records.append(_decision_record(repeated))
        return ProvenTransactionActionResultV1(
            status="COMPLETED",
            output={
                "replayed_count": len(records),
                "unchanged_retry_count": sum(
                    1 for record in records if record["retry_recommended"]
                ),
                "replays": records,
            },
        )

    def replay_sealed(
        _action_input: ProvenTransactionActionInputV1,
    ) -> ProvenTransactionActionResultV1:
        output = sealed_replay()
        return ProvenTransactionActionResultV1(status="COMPLETED", output=output)

    return {
        "observe_current_external_blocks": observe,
        "adapt_smallest_resolver_seam": adapt,
        "replay_affected_fact_stages": replay,
        "replay_sealed_transaction": replay_sealed,
    }


__all__ = [
    "ExternalFactReplayCaseV1",
    "build_pf04_handlers",
]
