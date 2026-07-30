"""Run bounded grounded repair and both independent trusted rereview roles."""

from __future__ import annotations

from readme_agent.errors import LLMError
from readme_agent.facts.trusted_readme_schema import TrustedReadmeFactGraphV1
from readme_agent.llm.verifier_client import ForcedToolClient
from readme_agent.readme.trusted_composition_models import (
    TrustedReadmeCompositionOutputV1,
    TrustedReadmeSectionRepairRequestV1,
)
from readme_agent.readme.trusted_composition_repair import repair_trusted_composition_section
from readme_agent.specialists.review_role_execution import AnalysisClientLike
from readme_agent.specialists.trusted_transform_review import run_trusted_transform_review
from readme_agent.specialists.trusted_transform_review_models import (
    TrustedRepairAttemptV1,
    TrustedReviewExecutionV1,
    TrustedReviewLoopResultV1,
    TrustedTransformReviewV1,
)

_MAX_REPAIR_ATTEMPTS = 2


def run_trusted_review_with_repair(
    graph: TrustedReadmeFactGraphV1,
    source_text: str,
    composition: TrustedReadmeCompositionOutputV1,
    *,
    blind_client: AnalysisClientLike,
    fidelity_client: AnalysisClientLike,
    repair_client: ForcedToolClient,
    initial_execution: TrustedReviewExecutionV1 | None = None,
    enable_fidelity_batch_cache: bool = False,
) -> TrustedReviewLoopResultV1:
    """Review, repair one responsible batch at a time, and fail on unchanged bytes.

    Canonical wiring may dispatch and persist the first independent review
    before entering repair. Supplying that exact execution avoids paying for
    and recording a duplicate pair of reviewer calls.
    """

    current = composition
    history: list[TrustedRepairAttemptV1] = []
    if (
        initial_execution is not None
        and initial_execution.review.candidate_sha256 != composition.candidate_sha256
    ):
        raise ValueError("initial trusted review belongs to different candidate bytes")
    execution = initial_execution or run_trusted_transform_review(
        graph,
        source_text,
        current,
        blind_client=blind_client,
        fidelity_client=fidelity_client,
        enable_fidelity_batch_cache=enable_fidelity_batch_cache,
    )
    for attempt in range(1, _MAX_REPAIR_ATTEMPTS + 1):
        verdict = execution.review.verdict
        if verdict == "TRUSTED_TRANSFORM_APPROVED":
            return TrustedReviewLoopResultV1(
                outcome="accepted",
                final_composition=current,
                final_execution=execution,
                repair_history=tuple(history),
            )
        if verdict == "SYSTEM_FAILURE":
            return _system_failure(
                current,
                execution,
                history,
                "independent reviewer system failure",
            )
        try:
            request = _repair_request(graph, current, execution.review, attempt)
            repaired = repair_trusted_composition_section(
                graph,
                source_text,
                current,
                request,
                client=repair_client,
            )
        except (LLMError, ValueError) as exc:
            return _system_failure(current, execution, history, f"trusted repair failed: {exc}")
        changed = repaired.candidate_sha256 != current.candidate_sha256
        receipt = TrustedRepairAttemptV1(
            attempt=attempt,
            request=request,
            candidate_sha256_before=current.candidate_sha256,
            candidate_sha256_after=repaired.candidate_sha256,
            candidate_changed=changed,
        )
        if not changed:
            return _system_failure(
                current,
                execution,
                [*history, receipt],
                "trusted repair returned byte-identical candidate",
            )
        current = repaired
        execution = run_trusted_transform_review(
            graph,
            source_text,
            current,
            blind_client=blind_client,
            fidelity_client=fidelity_client,
            enable_fidelity_batch_cache=enable_fidelity_batch_cache,
        )
        history.append(receipt.model_copy(update={"rereview_verdict": execution.review.verdict}))
    if execution.review.verdict == "TRUSTED_TRANSFORM_APPROVED":
        return TrustedReviewLoopResultV1(
            outcome="accepted",
            final_composition=current,
            final_execution=execution,
            repair_history=tuple(history),
        )
    if execution.review.verdict == "SYSTEM_FAILURE":
        return _system_failure(
            current,
            execution,
            history,
            "independent reviewer system failure after repair",
        )
    return TrustedReviewLoopResultV1(
        outcome="rejected",
        final_composition=current,
        final_execution=execution,
        repair_history=tuple(history),
    )


def _repair_request(
    graph: TrustedReadmeFactGraphV1,
    composition: TrustedReadmeCompositionOutputV1,
    review: TrustedTransformReviewV1,
    attempt: int,
) -> TrustedReadmeSectionRepairRequestV1:
    owned_findings: dict[str, list[tuple[str, str]]] = {}

    def assign(batch_id: str, finding_id: str, instruction: str) -> None:
        if instruction.strip():
            owned_findings.setdefault(batch_id, []).append((finding_id, instruction))

    def batches_containing_quote(quote: str) -> tuple[str, ...]:
        if not quote:
            return ()
        return tuple(
            draft.batch_id
            for draft in composition.plan.section_drafts
            if any(quote in segment.markdown for segment in draft.segments)
        )

    fact_to_batch = {
        fact_id: draft.batch_id
        for draft in composition.plan.section_drafts
        for segment in draft.segments
        for fact_id in segment.inherited_fact_ids
    }
    blind = review.blind_quality.result
    for finding in blind.get("findings", []):
        if finding.get("disposition") == "requires_repair":
            finding_id = str(finding["finding_id"])
            instruction = str(finding["required_repair"])
            quote = str(finding.get("quoted_candidate_span", ""))
            for batch_id in batches_containing_quote(quote):
                assign(batch_id, finding_id, instruction)
    fidelity = review.inheritance_fidelity.result
    for check in fidelity.get("source_checks", []):
        if check.get("outcome") == "lost_or_distorted":
            fact_id = str(check["fact_id"])
            owner_batch_id = fact_to_batch.get(fact_id)
            if owner_batch_id is not None:
                assign(
                    owner_batch_id,
                    f"fidelity.{fact_id.split(':')[-1]}",
                    str(check["required_repair"]),
                )
    for finding in fidelity.get("unsupported_additions", []):
        finding_id = str(finding["finding_id"])
        instruction = str(finding["required_repair"])
        quote = str(finding["quoted_candidate_span"])
        for batch_id in batches_containing_quote(quote):
            assign(batch_id, finding_id, instruction)
    target = next(
        (draft for draft in composition.plan.section_drafts if draft.batch_id in owned_findings),
        None,
    )
    if target is None:
        raise ValueError("grounded findings do not identify a responsible repair batch")
    target_findings = owned_findings[target.batch_id]
    return TrustedReadmeSectionRepairRequestV1(
        org_repo=graph.org_repo,
        source_revision=graph.source_revision,
        rejected_batch_id=target.batch_id,
        rejected_draft_sha256=target.canonical_hash(),
        finding_ids=tuple(dict.fromkeys(item[0] for item in target_findings)),
        repair_instructions=tuple(dict.fromkeys(item[1] for item in target_findings)),
        accepted_section_sha256s=tuple(
            draft.canonical_hash()
            for draft in composition.plan.section_drafts
            if draft.batch_id != target.batch_id
        ),
    )


def _system_failure(
    composition: TrustedReadmeCompositionOutputV1,
    execution: TrustedReviewExecutionV1,
    history: list[TrustedRepairAttemptV1],
    reason: str,
) -> TrustedReviewLoopResultV1:
    return TrustedReviewLoopResultV1(
        outcome="system_failure",
        final_composition=composition,
        final_execution=execution,
        repair_history=tuple(history),
        system_failure_reason=reason,
    )
