"""Read-and-report join over existing receipts, rubric results, and evidence bundles.

Never a second scoring system: acceptance re-derives from `rubric.py`/`rubric_criteria.py`'s
30-criterion evaluation and `evidence_bundle.py`'s already-loaded artifacts on every build, so a
stale or historical "ACCEPTED"-labeled receipt can never stand in for fresh proof (the task's own
"never treat historical facts, a generated candidate, internal ACCEPT, or a successful LLM call as
portfolio proof" rule). No new receipt model, evidence schema, scheduler, or scoring system is
added here -- this module only joins what already exists into one report row per registry entry.

Self-contained by design: reads only already-exported symbols from the sibling modules (never
edits them), so this file plus its test is the entire diff for this deliverable.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal, get_args

from pydantic import BaseModel, ConfigDict, Field

from readme_agent import paths
from readme_agent.registry.models import ProductEntry
from readme_agent.supervisor.blocked_decision_cache import load_blocked_decision
from readme_agent.supervisor.portfolio_proof_engine.contracts import (
    STAGE_ORDER,
    ProofModeV1,
    ProofStageReceiptV1,
    ProofStageV1,
    campaign_id_for_mode,
)
from readme_agent.supervisor.portfolio_proof_engine.evidence_bundle import (
    EvidenceBundleV1,
    load_evidence_bundle,
)
from readme_agent.supervisor.portfolio_proof_engine.receipt_store import (
    default_output_root,
    read_receipt,
)
from readme_agent.supervisor.portfolio_proof_engine.registry_cohort import load_portfolio_entries
from readme_agent.supervisor.portfolio_proof_engine.rubric import RubricScoreV1, score_candidate
from readme_agent.supervisor.portfolio_proof_engine.rubric_criteria import (
    knowledge_application_final,
)
from readme_agent.supervisor.portfolio_proof_engine.rubric_evidence import (
    benchmark_acceptance_proven,
    reconciliation_integrity,
    replay_attestation_proven,
    rubric_acceptance_binding_current,
)

DashboardStateV1 = Literal[
    "SKIPPED_NON_SUBSTANTIVE",
    "BLOCKED_FACTS",
    "CANDIDATE_INCOMPLETE",
    "CANDIDATE_REJECTED",
    "ACCEPTED_30_OF_30",
]

_FACTS_LEVEL_STAGES: frozenset[ProofStageV1] = frozenset(
    {"INTAKE", "SOURCE_BOUND", "FACTS_READY", "SECTION_PACKETS_READY", "SECTIONS_AUTHORED"}
)
_CANDIDATE_LEVEL_STAGES: frozenset[ProofStageV1] = frozenset(
    {
        "CANDIDATE_ASSEMBLED",
        "DETERMINISTIC_VALIDATED",
        "FACTUAL_REVIEWED",
        "VISITOR_REVIEWED",
        "RUBRIC_SCORED",
        "ACCEPTED",
    }
)


class PortfolioDashboardRowV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    org_repo: str
    family: str
    platform: str
    processability: Literal["PROCESSABLE", "TERMINAL_SKIP"]
    source_revision: str | None
    facts_ready: bool = False
    state: DashboardStateV1
    candidate_hash: str | None
    score: int | None = Field(default=None, ge=0, le=30)
    hard_disqualifier_count: int = 0
    factual_review_result: str | None = None
    visitor_review_result: str | None = None
    blocked_surface: str | None = None
    failed_gates: tuple[str, ...] = ()
    retry_count: int = 0
    provider_calls: int = 0
    elapsed_seconds: float = 0.0
    next_causal_action: str


class PortfolioDashboardSummaryV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    total: int
    terminal_skipped: int
    processable: int
    facts_ready: int
    candidates_generated: int
    accepted_30_of_30: int
    candidate_rejected: int
    blocked_facts: int
    candidate_incomplete: int
    provider_calls: int
    elapsed_seconds: float


class PortfolioDashboardV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    rows: tuple[PortfolioDashboardRowV1, ...]
    summary: PortfolioDashboardSummaryV1


def _all_receipts_flat(output_root: Path, org_repo: str) -> list[ProofStageReceiptV1]:
    """Every receipt on file for this repository, across all five fixed per-mode campaigns and
    every stage -- unfiltered, possibly incoherent (see `_coherent_receipts_for_repo`)."""

    flat: list[ProofStageReceiptV1] = []
    for mode in get_args(ProofModeV1):
        campaign_id = campaign_id_for_mode(mode)
        for stage in STAGE_ORDER:
            receipt = read_receipt(output_root, campaign_id, org_repo, stage)
            if receipt is not None:
                flat.append(receipt)
    return flat


def _coherent_receipts_for_repo(
    output_root: Path, org_repo: str
) -> dict[ProofStageV1, ProofStageReceiptV1]:
    """Merge receipts across all five per-mode campaigns into one *coherent* chain -- never
    combining evidence merely because each is the newest timestamp for its own stage.

    A receipt survives only if it is compatible with the repository's current identity: the same
    source revision as the most recently observed receipt; the same facts hash as the newest
    facts-bearing receipt; the same candidate hash as the newest candidate-bound receipt; and (for
    a receipt that records one) a `predecessor_receipt_hash` that actually resolves to another
    surviving receipt. An incompatible receipt is dropped entirely rather than silently kept --
    "missing compatible stages must produce CANDIDATE_INCOMPLETE, never acceptance."
    """

    flat = _all_receipts_flat(output_root, org_repo)
    if not flat:
        return {}

    # 1. Current source revision: the revision of the most recently generated receipt that
    #    carries one. Receipts bound to any other revision are stale and excluded outright.
    revisioned = [r for r in flat if r.source_revision]
    current_revision = (
        max(revisioned, key=lambda r: r.generated_at).source_revision if revisioned else None
    )
    survivors = (
        [r for r in flat if r.source_revision in (None, current_revision)]
        if current_revision is not None
        else list(flat)
    )

    # 2. Keep only the most recent surviving receipt per stage.
    by_stage: dict[ProofStageV1, ProofStageReceiptV1] = {}
    for receipt in survivors:
        existing = by_stage.get(receipt.stage)
        if existing is None or receipt.generated_at >= existing.generated_at:
            by_stage[receipt.stage] = receipt

    # 3. Facts-hash coherence: every facts-bearing receipt must agree with the newest one.
    facts_bearing = [stage for stage, r in by_stage.items() if r.facts_hash]
    if facts_bearing:
        current_facts_hash = max(
            (by_stage[stage] for stage in facts_bearing), key=lambda r: r.generated_at
        ).facts_hash
        for stage in facts_bearing:
            if by_stage[stage].facts_hash != current_facts_hash:
                del by_stage[stage]

    # 4. Candidate-hash coherence: every candidate-bound-stage receipt must agree with the
    #    newest one -- two candidates with different hashes can never both stand.
    candidate_bearing = [
        stage
        for stage, r in by_stage.items()
        if stage in _CANDIDATE_LEVEL_STAGES and r.candidate_hash
    ]
    if candidate_bearing:
        current_candidate_hash = max(
            (by_stage[stage] for stage in candidate_bearing), key=lambda r: r.generated_at
        ).candidate_hash
        for stage in candidate_bearing:
            if by_stage[stage].candidate_hash != current_candidate_hash:
                del by_stage[stage]

    # 5. Predecessor continuity: a receipt that names a predecessor hash must find it among the
    #    survivors, or its own lineage is unverifiable and it cannot stand either. Iterate to a
    #    fixed point since dropping one receipt can break a later one's chain in turn; bounded by
    #    the number of stages, so this always terminates.
    for _ in range(len(STAGE_ORDER)):
        retained_hashes = {r.canonical_hash() for r in by_stage.values()}
        broken = [
            stage
            for stage, r in by_stage.items()
            if r.predecessor_receipt_hash is not None
            and r.predecessor_receipt_hash not in retained_hashes
        ]
        if not broken:
            break
        for stage in broken:
            del by_stage[stage]

    return by_stage


def _latest_by_stage_order(
    receipts: dict[ProofStageV1, ProofStageReceiptV1],
) -> ProofStageReceiptV1 | None:
    for stage in reversed(STAGE_ORDER):
        if stage in receipts:
            return receipts[stage]
    return None


def _deterministic_ok(bundle: EvidenceBundleV1) -> bool:
    validation = bundle.deterministic_validation
    if validation is None:
        return False
    verdict = validation.get("verdict")
    if isinstance(verdict, str):
        return verdict.casefold() == "accept" and not validation.get("reason")
    return validation.get("valid") is True and not validation.get("errors")


def _review_verdict(record: dict | None) -> str | None:
    if not record:
        return None
    nested = record.get("result")
    result = nested if isinstance(nested, dict) else record
    verdict = result.get("verdict")
    return str(verdict) if verdict is not None else None


def _candidate_hash_agrees_everywhere(bundle: EvidenceBundleV1) -> bool | None:
    """ "candidate hash matches every candidate-bound artifact" -- checked across every artifact
    that independently records its own candidate identity, not only the manifest."""

    if not bundle.candidate_hash:
        return None
    checks: list[bool] = []
    if bundle.manifest is not None:
        recorded = bundle.manifest.get("candidate_hash")
        if recorded is None:
            return None
        checks.append(recorded == bundle.candidate_hash)
    else:
        return None
    if bundle.knowledge_application is not None:
        recorded_k3 = bundle.knowledge_application.get("candidate_sha256")
        if recorded_k3 is None:
            return None
        checks.append(recorded_k3 == bundle.candidate_hash)
    return all(checks) if checks else None


def _source_revision_matches(bundle: EvidenceBundleV1) -> bool | None:
    if bundle.manifest is None or not bundle.source_revision:
        return None
    recorded = bundle.manifest.get("source_revision")
    if recorded is None:
        return None
    return recorded == bundle.source_revision


def _first_present(source: dict, *keys: str) -> object | None:
    """First key that actually exists, distinguishing a valid `0`/`False` value from an absent
    key -- `dict.get(a) or dict.get(b)` incorrectly treats a genuine `0` count as "try the next
    key," silently losing a clean (zero-count) signal."""

    for key in keys:
        if key in source:
            return source[key]
    return None


def _disposition_ledger_clean(bundle: EvidenceBundleV1) -> bool | None:
    """RUBRIC_30.md's "unexplained dropped content" concern -- read from the same reconciliation
    artifact the B-category rubric criteria already use (see `rubric_criteria.py`'s own note that
    the canonical `local_poc` bundle carries this inside `reconciliation`, not a second ledger)."""

    return reconciliation_integrity(bundle)


def _blocking_checks_clean(bundle: EvidenceBundleV1) -> bool | None:
    coverage = bundle.check_coverage
    if coverage is None:
        return None
    skipped = _first_present(coverage, "skipped", "skipped_count")
    errored = _first_present(coverage, "errored", "error_count")
    failed = _first_present(coverage, "failed", "failed_count")
    if skipped is None and errored is None and failed is None:
        return None
    return not skipped and not errored and not failed


def _no_op_passes(bundle: EvidenceBundleV1) -> bool | None:
    proof = bundle.no_op_proof
    if proof is None:
        return None
    verdict = proof.get("verdict")
    if verdict is not None:
        return str(verdict) in {"RENDER_REPRODUCIBLE", "NO_OP_PROVEN", "PASS"}
    if "reproducible" in proof:
        return bool(proof.get("reproducible"))
    return None


def _claim_map_valid(bundle: EvidenceBundleV1) -> bool | None:
    claim_map = bundle.claim_map
    if claim_map is None:
        return None
    if "valid" in claim_map:
        return bool(claim_map.get("valid"))
    errors = claim_map.get("errors")
    return errors is None or not errors


def _extra_acceptance_checks(bundle: EvidenceBundleV1) -> dict[str, bool | None]:
    """Every ACCEPTED_30_OF_30 prerequisite the 30-point rubric does not itself already require
    as a scored criterion: hash/revision cross-binding, and the finer disposition/blocking/no-op
    signals. `None` means "not enough evidence to resolve this one," never a guess either way."""

    return {
        "source_revision_matches_proof_run": _source_revision_matches(bundle),
        "candidate_hash_matches_every_artifact": _candidate_hash_agrees_everywhere(bundle),
        "disposition_ledger_no_unexplained_drops": _disposition_ledger_clean(bundle),
        "claim_accountability_map_valid": _claim_map_valid(bundle),
        "knowledge_application_final_and_bound": knowledge_application_final(bundle),
        "blocking_checks_ran_and_passed": _blocking_checks_clean(bundle),
        "factual_review_accepts": (
            None
            if bundle.factual_review is None
            else _review_verdict(bundle.factual_review) == "ACCEPT"
        ),
        "visitor_review_accepts": (
            None
            if bundle.visitor_review is None
            else _review_verdict(bundle.visitor_review) == "ACCEPT"
        ),
        "no_op_reproducibility_passes": _no_op_passes(bundle),
        "deterministic_verdict_accepts": (
            None if bundle.deterministic_validation is None else _deterministic_ok(bundle)
        ),
        "benchmark_acceptance_proven_and_current": benchmark_acceptance_proven(bundle),
        "complete_transaction_replay_proven_and_current": replay_attestation_proven(bundle),
        "terminal_rubric_acceptance_binding_current": rubric_acceptance_binding_current(bundle),
    }


def _classify_candidate(
    bundle: EvidenceBundleV1,
) -> tuple[DashboardStateV1, RubricScoreV1 | None, tuple[str, ...]]:
    """A candidate exists (CANDIDATE_ASSEMBLED or later was reached) -- decide
    ACCEPTED_30_OF_30 / CANDIDATE_REJECTED / CANDIDATE_INCOMPLETE from fresh evidence, never a
    trusted prior label."""

    if bundle.deterministic_validation is None or bundle.manifest is None:
        return "CANDIDATE_INCOMPLETE", None, ()

    score = score_candidate(bundle)
    failed_gates = [
        f"criterion {c.criterion_id} ({c.evidence_key})"
        for c in score.criteria
        if c.awarded_points == 0
    ]
    failed_gates.extend(f"hard disqualifier: {d}" for d in score.hard_disqualifiers)

    if score.total_score != 30 or score.hard_disqualifiers:
        return "CANDIDATE_REJECTED", score, tuple(failed_gates)

    extra = _extra_acceptance_checks(bundle)
    unresolved = [name for name, outcome in extra.items() if outcome is None]
    failed = [name for name, outcome in extra.items() if outcome is False]
    if failed:
        return "CANDIDATE_REJECTED", score, tuple(failed_gates + [f"unmet: {n}" for n in failed])
    if unresolved:
        return "CANDIDATE_INCOMPLETE", score, ()
    return "ACCEPTED_30_OF_30", score, ()


def _next_causal_action(state: DashboardStateV1, blocked_surface: str | None) -> str:
    return {
        "SKIPPED_NON_SUBSTANTIVE": "none -- terminally out of scope under the generic "
        "no-substantive-content rule",
        "BLOCKED_FACTS": f"resolve the blocked facts surface ({blocked_surface}) then retry "
        "via failed-only",
        "CANDIDATE_INCOMPLETE": "run the missing stage(s) to completion before re-scoring",
        "CANDIDATE_REJECTED": "repair the named failed gate(s) then retry via failed-only",
        "ACCEPTED_30_OF_30": "none -- accepted",
    }[state]


def _build_row(entry: ProductEntry, output_root: Path) -> PortfolioDashboardRowV1:
    receipts = _coherent_receipts_for_repo(output_root, entry.org_repo)
    latest = _latest_by_stage_order(receipts)

    org, repo = entry.org_repo.split("/", maxsplit=1)
    blocked_decision = load_blocked_decision(paths.readme_poc_blocked_decision_path(org, repo))
    retry_count = blocked_decision.consecutive_count if blocked_decision is not None else 0
    # An unresolved (None) per-receipt count contributes nothing countable to the row total --
    # it is never treated as a known 0 either; see contracts.py's provider_call_count docstring.
    provider_calls = sum(r.provider_call_count or 0 for r in receipts.values())
    elapsed_seconds = sum(r.elapsed_seconds for r in receipts.values())
    source_revision = latest.source_revision if latest is not None else None
    candidate_hash = latest.candidate_hash if latest is not None else None
    reached_candidate = any(stage in receipts for stage in _CANDIDATE_LEVEL_STAGES)
    facts_ready = (
        reached_candidate
        or "FACTS_READY" in receipts
        or bool({"SECTION_PACKETS_READY", "SECTIONS_AUTHORED"} & set(receipts))
    )

    if "TERMINAL_SKIPPED" in receipts:
        return PortfolioDashboardRowV1(
            org_repo=entry.org_repo,
            family=entry.family,
            platform=entry.platform,
            processability="TERMINAL_SKIP",
            source_revision=source_revision,
            facts_ready=False,
            state="SKIPPED_NON_SUBSTANTIVE",
            candidate_hash=None,
            retry_count=retry_count,
            provider_calls=provider_calls,
            elapsed_seconds=elapsed_seconds,
            next_causal_action=_next_causal_action("SKIPPED_NON_SUBSTANTIVE", None),
        )

    if latest is None:
        return PortfolioDashboardRowV1(
            org_repo=entry.org_repo,
            family=entry.family,
            platform=entry.platform,
            processability="PROCESSABLE",
            source_revision=None,
            facts_ready=False,
            state="CANDIDATE_INCOMPLETE",
            candidate_hash=None,
            retry_count=retry_count,
            provider_calls=provider_calls,
            elapsed_seconds=elapsed_seconds,
            next_causal_action=_next_causal_action("CANDIDATE_INCOMPLETE", None),
        )

    if not reached_candidate:
        if latest.status == "FAILED" and (
            latest.stage in _FACTS_LEVEL_STAGES or latest.stage == "BLOCKED_INPUT"
        ):
            return PortfolioDashboardRowV1(
                org_repo=entry.org_repo,
                family=entry.family,
                platform=entry.platform,
                processability="PROCESSABLE",
                source_revision=source_revision,
                facts_ready=facts_ready,
                state="BLOCKED_FACTS",
                candidate_hash=None,
                blocked_surface=latest.failure_reason,
                retry_count=retry_count,
                provider_calls=provider_calls,
                elapsed_seconds=elapsed_seconds,
                next_causal_action=_next_causal_action("BLOCKED_FACTS", latest.failure_reason),
            )
        return PortfolioDashboardRowV1(
            org_repo=entry.org_repo,
            family=entry.family,
            platform=entry.platform,
            processability="PROCESSABLE",
            source_revision=source_revision,
            facts_ready=facts_ready,
            state="CANDIDATE_INCOMPLETE",
            candidate_hash=candidate_hash,
            retry_count=retry_count,
            provider_calls=provider_calls,
            elapsed_seconds=elapsed_seconds,
            next_causal_action=_next_causal_action("CANDIDATE_INCOMPLETE", None),
        )

    bundle = load_evidence_bundle(entry.org_repo, source_revision, candidate_hash=candidate_hash)
    state, score, failed_gates = _classify_candidate(bundle)
    return PortfolioDashboardRowV1(
        org_repo=entry.org_repo,
        family=entry.family,
        platform=entry.platform,
        processability="PROCESSABLE",
        source_revision=source_revision,
        facts_ready=facts_ready,
        state=state,
        candidate_hash=candidate_hash,
        score=score.total_score if score is not None else None,
        hard_disqualifier_count=len(score.hard_disqualifiers) if score is not None else 0,
        factual_review_result=_review_verdict(bundle.factual_review),
        visitor_review_result=_review_verdict(bundle.visitor_review),
        failed_gates=failed_gates,
        retry_count=retry_count,
        provider_calls=provider_calls,
        elapsed_seconds=elapsed_seconds,
        next_causal_action=_next_causal_action(state, None),
    )


def build_dashboard(
    *,
    registry_path: Path | None = None,
    output_root: Path | None = None,
) -> PortfolioDashboardV1:
    """One row per registry entry -- all 33 preserved, denominator derived from the registry
    itself, never a stale `RESULTS.md`."""

    entries = load_portfolio_entries(registry_path)
    resolved_output_root = output_root or default_output_root()
    rows = tuple(_build_row(entry, resolved_output_root) for entry in entries)

    by_state: dict[DashboardStateV1, int] = dict.fromkeys(get_args(DashboardStateV1), 0)
    for row in rows:
        by_state[row.state] += 1

    summary = PortfolioDashboardSummaryV1(
        total=len(rows),
        terminal_skipped=by_state["SKIPPED_NON_SUBSTANTIVE"],
        processable=len(rows) - by_state["SKIPPED_NON_SUBSTANTIVE"],
        facts_ready=sum(1 for row in rows if row.facts_ready),
        candidates_generated=sum(1 for row in rows if row.candidate_hash is not None),
        accepted_30_of_30=by_state["ACCEPTED_30_OF_30"],
        candidate_rejected=by_state["CANDIDATE_REJECTED"],
        blocked_facts=by_state["BLOCKED_FACTS"],
        candidate_incomplete=by_state["CANDIDATE_INCOMPLETE"],
        provider_calls=sum(row.provider_calls for row in rows),
        elapsed_seconds=sum(row.elapsed_seconds for row in rows),
    )
    return PortfolioDashboardV1(rows=rows, summary=summary)
