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
) -> TrustedReviewLoopResultV1:
    """Review, repair one responsible batch at a time, and fail on unchanged bytes."""

    current = composition
    history: list[TrustedRepairAttemptV1] = []
    execution = run_trusted_transform_review(
        graph,
        source_text,
        current,
        blind_client=blind_client,
        fidelity_client=fidelity_client,
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
    target_fact_ids: list[str] = []
    target_batch_ids: list[str] = []
    instructions: list[str] = []
    finding_ids: list[str] = []
    blind = review.blind_quality.result
    for finding in blind.get("findings", []):
        if finding.get("disposition") == "requires_repair":
            finding_ids.append(str(finding["finding_id"]))
            instructions.append(str(finding["required_repair"]))
            quote = str(finding.get("quoted_candidate_span", ""))
            for draft in composition.plan.section_drafts:
                if any(quote and quote in segment.markdown for segment in draft.segments):
                    target_batch_ids.append(draft.batch_id)
                    target_fact_ids.extend(
                        fact_id
                        for segment in draft.segments
                        for fact_id in segment.inherited_fact_ids
                    )
    fidelity = review.inheritance_fidelity.result
    for check in fidelity.get("source_checks", []):
        if check.get("outcome") == "lost_or_distorted":
            target_fact_ids.append(str(check["fact_id"]))
            finding_ids.append(f"fidelity.{check['fact_id'].split(':')[-1]}")
            instructions.append(str(check["required_repair"]))
    for finding in fidelity.get("unsupported_additions", []):
        finding_ids.append(str(finding["finding_id"]))
        instructions.append(str(finding["required_repair"]))
        quote = str(finding["quoted_candidate_span"])
        for draft in composition.plan.section_drafts:
            if any(quote in segment.markdown for segment in draft.segments):
                target_batch_ids.append(draft.batch_id)
                target_fact_ids.extend(
                    fact_id for segment in draft.segments for fact_id in segment.inherited_fact_ids
                )
    target = next(
        (
            draft
            for draft in composition.plan.section_drafts
            if (
                draft.batch_id in target_batch_ids
                or any(
                    fact_id in target_fact_ids
                    for segment in draft.segments
                    for fact_id in segment.inherited_fact_ids
                )
            )
        ),
        None,
    )
    if target is None or not instructions:
        raise ValueError("grounded findings do not identify a responsible repair batch")
    return TrustedReadmeSectionRepairRequestV1(
        org_repo=graph.org_repo,
        source_revision=graph.source_revision,
        rejected_batch_id=target.batch_id,
        rejected_draft_sha256=target.canonical_hash(),
        finding_ids=tuple(dict.fromkeys(finding_ids)),
        repair_instructions=tuple(dict.fromkeys(instructions)),
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
