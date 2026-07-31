"""Run bounded grounded repair and both independent trusted rereview roles."""

from __future__ import annotations

import hashlib
import json
import re
from time import monotonic
from typing import Literal

from readme_agent.errors import LLMError, LLMInfrastructureError
from readme_agent.facts.trusted_readme_schema import TrustedReadmeFactGraphV1
from readme_agent.llm.verifier_client import ForcedToolClient
from readme_agent.readme.trusted_candidate_ownership import records_covering_range
from readme_agent.readme.trusted_composition_models import (
    TrustedReadmeCompositionOutputV1,
    TrustedReadmeSectionRepairRequestV1,
)
from readme_agent.readme.trusted_composition_repair import repair_trusted_composition_section
from readme_agent.readme.trusted_exact_repair import (
    apply_grounded_exact_removal,
    exact_prose_paragraph_range,
)
from readme_agent.specialists.review_role_execution import AnalysisClientLike
from readme_agent.specialists.trusted_transform_review import run_trusted_transform_review
from readme_agent.specialists.trusted_transform_review_models import (
    TrustedRepairApproachV1,
    TrustedRepairAttemptV1,
    TrustedReviewExecutionV1,
    TrustedReviewLoopResultV1,
    TrustedTransformReviewV1,
)

_MAX_REPAIR_ATTEMPTS = 2
_MAX_REPAIR_LOOP_SECONDS = 15 * 60


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

    started_at = monotonic()
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
        elapsed = monotonic() - started_at
        if elapsed >= _MAX_REPAIR_LOOP_SECONDS:
            return _system_failure(
                current,
                execution,
                history,
                "trusted repair exceeded the 15-minute approach budget",
            )
        try:
            exact_finding = _grounded_exact_removal(
                execution.review,
                current.candidate_markdown,
            )
            approach: TrustedRepairApproachV1 = (
                "grounded_exact_removal"
                if exact_finding is not None
                else "bounded_llm_section_rewrite"
            )
            boundary_fingerprint = _repair_boundary_fingerprint(execution.review)
            if any(
                item.approach == approach and item.boundary_fingerprint == boundary_fingerprint
                for item in history
            ):
                return _system_failure(
                    current,
                    execution,
                    history,
                    "trusted repair approach repeated without resolving the same boundary; "
                    "an upstream resolver or materially different mechanism is required",
                )
            if exact_finding is not None:
                repaired, action = apply_grounded_exact_removal(
                    graph,
                    source_text,
                    current,
                    finding_id=exact_finding[0],
                    quoted_candidate_span=exact_finding[1],
                    instruction=exact_finding[2],
                )
                request = None
            else:
                request = _repair_request(graph, current, execution.review, attempt)
                repaired = repair_trusted_composition_section(
                    graph,
                    source_text,
                    current,
                    request,
                    client=repair_client,
                )
                action = None
        except LLMInfrastructureError as exc:
            return _system_failure(
                current,
                execution,
                history,
                f"trusted repair failed: {exc}",
                category="infra_external",
            )
        except (LLMError, ValueError) as exc:
            return _system_failure(current, execution, history, f"trusted repair failed: {exc}")
        changed = repaired.candidate_sha256 != current.candidate_sha256
        receipt = TrustedRepairAttemptV1(
            attempt=attempt,
            approach=approach,
            boundary_fingerprint=boundary_fingerprint,
            elapsed_seconds=monotonic() - started_at,
            request=request,
            action=action,
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
        try:
            execution = run_trusted_transform_review(
                graph,
                source_text,
                current,
                blind_client=blind_client,
                fidelity_client=fidelity_client,
                enable_fidelity_batch_cache=enable_fidelity_batch_cache,
                prior_fidelity_record=(
                    execution.review.inheritance_fidelity if action is not None else None
                ),
                exact_repair_action=action,
            )
        except LLMInfrastructureError as exc:
            return _system_failure(
                current,
                execution,
                [*history, receipt],
                f"trusted rereview failed: {exc}",
                category="infra_external",
            )
        except (LLMError, ValueError) as exc:
            return _system_failure(
                current,
                execution,
                [*history, receipt],
                f"trusted rereview failed: {exc}",
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


def _repair_boundary_fingerprint(review: TrustedTransformReviewV1) -> str:
    """Identify one grounded repair boundary without binding it to candidate bytes."""

    blind = [
        {
            "finding_id": finding.get("finding_id"),
            "section": finding.get("section"),
            "quoted_candidate_span": finding.get("quoted_candidate_span"),
            "required_repair": finding.get("required_repair"),
        }
        for finding in review.blind_quality.result.get("findings", [])
        if finding.get("disposition") == "requires_repair"
    ]
    fidelity_checks = [
        {
            "fact_id": check.get("fact_id"),
            "required_repair": check.get("required_repair"),
        }
        for check in review.inheritance_fidelity.result.get("source_checks", [])
        if check.get("outcome") == "lost_or_distorted"
    ]
    additions = [
        {
            "finding_id": finding.get("finding_id"),
            "section": finding.get("section"),
            "quoted_candidate_span": finding.get("quoted_candidate_span"),
            "required_repair": finding.get("required_repair"),
        }
        for finding in review.inheritance_fidelity.result.get("unsupported_additions", [])
    ]
    payload = json.dumps(
        {
            "blind": blind,
            "fidelity_checks": fidelity_checks,
            "unsupported_additions": additions,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _grounded_exact_removal(
    review: TrustedTransformReviewV1,
    candidate: str,
) -> tuple[str, str, str] | None:
    """Select one unique complete prose paragraph without editorial inference."""

    findings: list[tuple[str, str, str]] = []
    for finding in review.blind_quality.result.get("findings", []):
        instruction = str(finding.get("required_repair", "")).strip()
        if finding.get("disposition") == "requires_repair" and _is_removal_instruction(instruction):
            findings.append(
                (
                    str(finding["finding_id"]),
                    str(finding.get("quoted_candidate_span", "")),
                    instruction,
                )
            )
    for finding in review.inheritance_fidelity.result.get("unsupported_additions", []):
        instruction = str(finding.get("required_repair", "")).strip()
        if _is_removal_instruction(instruction):
            findings.append(
                (
                    str(finding["finding_id"]),
                    str(finding.get("quoted_candidate_span", "")),
                    instruction,
                )
            )
    return next(
        (
            finding
            for finding in findings
            if exact_prose_paragraph_range(candidate, finding[1]) is not None
        ),
        None,
    )


def _is_removal_instruction(instruction: str) -> bool:
    return bool(re.search(r"(?i)\b(?:remove|delete|omit)\b", instruction))


def _repair_request(
    graph: TrustedReadmeFactGraphV1,
    composition: TrustedReadmeCompositionOutputV1,
    review: TrustedTransformReviewV1,
    attempt: int,
) -> TrustedReadmeSectionRepairRequestV1:
    owned_findings: dict[str, list[tuple[str, str]]] = {}
    owned_segments: dict[str, set[str]] = {}

    def assign(batch_id: str, segment_id: str, finding_id: str, instruction: str) -> None:
        if instruction.strip():
            owned_findings.setdefault(batch_id, []).append((finding_id, instruction))
            owned_segments.setdefault(batch_id, set()).add(segment_id)

    def segments_containing_quote(quote: str) -> tuple[tuple[str, str], ...]:
        if not quote:
            return ()
        exact = tuple(
            (draft.batch_id, segment.segment_id)
            for draft in composition.plan.section_drafts
            for segment in draft.segments
            if quote in segment.markdown
        )
        if exact:
            return exact
        if composition.candidate_markdown.count(quote) != 1:
            return ()
        char_start = composition.candidate_markdown.index(quote)
        byte_start = len(composition.candidate_markdown[:char_start].encode("utf-8"))
        byte_end = byte_start + len(quote.encode("utf-8"))
        owners = records_covering_range(composition.ownership_map, byte_start, byte_end)
        resolved = {
            (record.batch_id, record.producer_segment_id)
            for record in owners
            if record.batch_id is not None and record.producer_segment_id is not None
        }
        return tuple((batch_id, segment_id) for batch_id, segment_id in sorted(resolved))

    fact_to_owner = {
        fact_id: (draft.batch_id, segment.segment_id)
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
            for batch_id, segment_id in segments_containing_quote(quote):
                assign(batch_id, segment_id, finding_id, instruction)
    fidelity = review.inheritance_fidelity.result
    for check in fidelity.get("source_checks", []):
        if check.get("outcome") == "lost_or_distorted":
            fact_id = str(check["fact_id"])
            owner = fact_to_owner.get(fact_id)
            if owner is not None:
                assign(
                    owner[0],
                    owner[1],
                    f"fidelity.{fact_id.split(':')[-1]}",
                    str(check["required_repair"]),
                )
    for finding in fidelity.get("unsupported_additions", []):
        finding_id = str(finding["finding_id"])
        instruction = str(finding["required_repair"])
        quote = str(finding["quoted_candidate_span"])
        for batch_id, segment_id in segments_containing_quote(quote):
            assign(batch_id, segment_id, finding_id, instruction)
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
        rejected_segment_ids=tuple(
            segment.segment_id
            for segment in target.segments
            if segment.segment_id in owned_segments[target.batch_id]
        ),
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
    *,
    category: Literal["infra_external", "agent_fixable"] = "agent_fixable",
) -> TrustedReviewLoopResultV1:
    return TrustedReviewLoopResultV1(
        outcome="system_failure",
        final_composition=composition,
        final_execution=execution,
        repair_history=tuple(history),
        system_failure_reason=reason,
        system_failure_category=category,
    )
