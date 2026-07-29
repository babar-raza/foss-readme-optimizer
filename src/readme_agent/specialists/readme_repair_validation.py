"""Prove a reviewer-directed repair changed the responsible candidate operations."""

from __future__ import annotations

import difflib
import hashlib
import re
from typing import Any

from readme_agent.readme.document_structure import parse_headings
from readme_agent.specialists.independent_readme_review import (
    IndependentReadmeReviewResultV1,
)
from readme_agent.specialists.readme_repair_contracts import (
    RepairAttemptReceiptV1,
    RepairFindingRequestV1,
    RepairFindingResolutionV1,
    RepairTextDeltaV1,
)


def repair_findings(review: IndependentReadmeReviewResultV1) -> list[RepairFindingRequestV1]:
    """Extract only repair-authorizing findings, with a compatibility fallback."""

    normalized: list[RepairFindingRequestV1] = []
    for record_name in ("blind_quality_review", "factual_plan_review"):
        record = getattr(review, record_name, None)
        for finding in getattr(record, "findings", []):
            if finding.disposition != "requires_repair":
                continue
            normalized.append(
                RepairFindingRequestV1(
                    finding_id=finding.finding_id,
                    section=finding.section,
                    criterion=finding.criterion,
                    quoted_candidate_span=finding.quoted_candidate_span,
                    required_repair=finding.required_repair,
                )
            )
    if normalized:
        return normalized
    return [
        RepairFindingRequestV1(
            finding_id=f"legacy.{_slug(section)}",
            section=section,
            criterion=criterion,
            quoted_candidate_span="",
            required_repair=review.required_repair,
        )
        for section, criterion in zip(
            review.sections_affected,
            review.failed_criteria,
            strict=False,
        )
    ]


def validate_repair_source_binding(
    review: IndependentReadmeReviewResultV1,
    candidate_text: str,
) -> str:
    """Reject stale reviewer instructions that target different candidate bytes."""

    candidate_sha256 = _sha256(candidate_text)
    role_hashes: set[str] = set()
    for record_name in ("blind_quality_review", "factual_plan_review"):
        record = getattr(review, record_name, None)
        record_hash = getattr(record, "candidate_sha256", None)
        if record_hash is not None:
            role_hashes.add(str(record_hash))
    combined = getattr(review, "combined_review", None)
    if combined is not None:
        role_hashes.add(str(combined.candidate_sha256))
    if role_hashes and role_hashes != {candidate_sha256}:
        raise ValueError(
            "review repair instructions are stale against the source candidate: "
            f"expected {candidate_sha256}, observed {sorted(role_hashes)}"
        )
    return candidate_sha256


def build_repair_attempt_receipt(
    *,
    prior_context: dict,
    repaired_context: dict,
    review: IndependentReadmeReviewResultV1,
    repair_attempt: int,
    reviewer_call_count: int,
) -> RepairAttemptReceiptV1:
    """Require a material, operation-bound change before another reviewer call."""

    before = str(prior_context["final_text"])
    after = str(repaired_context["final_text"])
    before_hash = _sha256(before)
    after_hash = _sha256(after)
    before_operations = _operations(prior_context)
    after_operations = _operations(repaired_context)
    changed_operation_ids = sorted(
        operation_id
        for operation_id in before_operations.keys() | after_operations.keys()
        if before_operations.get(operation_id) != after_operations.get(operation_id)
    )
    findings = repair_findings(review)
    resolutions: list[RepairFindingResolutionV1] = []
    for finding in findings:
        bound = _bound_operation_ids(finding, before_operations, after_operations)
        changed_bound = sorted(set(bound) & set(changed_operation_ids))
        section_changed = _section_text(before, finding.section) != _section_text(
            after, finding.section
        )
        addressed = before_hash != after_hash and section_changed and bool(changed_bound)
        resolutions.append(
            RepairFindingResolutionV1(
                finding_id=finding.finding_id,
                section=finding.section,
                prior_span_occurrences=(
                    before.count(finding.quoted_candidate_span)
                    if finding.quoted_candidate_span
                    else 0
                ),
                repaired_span_occurrences=(
                    after.count(finding.quoted_candidate_span)
                    if finding.quoted_candidate_span
                    else 0
                ),
                section_changed=section_changed,
                bound_operation_ids=bound,
                changed_bound_operation_ids=changed_bound,
                status=("addressed_pending_rereview" if addressed else "unresolved_unchanged"),
            )
        )
    addressed_ids = sorted(
        item.finding_id for item in resolutions if item.status == "addressed_pending_rereview"
    )
    unresolved_ids = sorted(
        item.finding_id for item in resolutions if item.status == "unresolved_unchanged"
    )
    return RepairAttemptReceiptV1(
        repair_attempt=repair_attempt,
        before_candidate_sha256=before_hash,
        after_candidate_sha256=after_hash,
        candidate_changed=before_hash != after_hash,
        changed_spans=_changed_spans(before, after),
        changed_operation_ids=changed_operation_ids,
        finding_resolutions=resolutions,
        addressed_finding_ids=addressed_ids,
        unresolved_finding_ids=unresolved_ids,
        reviewer_call_count_before_rereview=reviewer_call_count,
        rereview_authorized=bool(findings) and not unresolved_ids,
    )


def finalize_repair_receipt(
    receipt: RepairAttemptReceiptV1,
    *,
    rereview_verdict: str,
    reviewer_call_count: int,
) -> RepairAttemptReceiptV1:
    """Record final finding resolution only when the next independent review accepts."""

    resolved = receipt.addressed_finding_ids if rereview_verdict == "ACCEPT" else []
    unresolved = (
        []
        if rereview_verdict == "ACCEPT"
        else sorted(set(receipt.unresolved_finding_ids) | set(receipt.addressed_finding_ids))
    )
    return receipt.model_copy(
        update={
            "resolved_finding_ids": resolved,
            "unresolved_finding_ids": unresolved,
            "reviewer_call_count_after_rereview": reviewer_call_count,
        }
    )


def _operations(context: dict) -> dict[str, dict]:
    plan = context.get("presentation_plan") or context.get("presentation_plan_record") or {}
    document_plan = plan.get("readme_document_plan") or {}
    return {
        str(operation["operation_id"]): operation
        for operation in document_plan.get("operations", [])
        if isinstance(operation, dict) and operation.get("operation_id")
    }


def _bound_operation_ids(
    finding: RepairFindingRequestV1,
    before_operations: dict[str, dict],
    after_operations: dict[str, dict],
) -> list[str]:
    tokens = {_slug(finding.section), _slug(finding.criterion)}
    bound: set[str] = set()
    for operation_id, operation in {**before_operations, **after_operations}.items():
        haystack = " ".join(
            (
                operation_id,
                str(operation.get("rationale") or ""),
                str(operation.get("replacement_text") or ""),
            )
        ).casefold()
        if finding.quoted_candidate_span and finding.quoted_candidate_span in str(
            operation.get("replacement_text") or ""
        ):
            bound.add(operation_id)
        elif any(token and token in _slug(haystack) for token in tokens):
            bound.add(operation_id)
    return sorted(bound)


def _section_text(text: str, section: str) -> str:
    expected = _slug(section)
    for heading in parse_headings(text):
        title = _slug(heading.title)
        if title == expected or expected in title or title in expected:
            return text[heading.start : heading.section_end]
    return text


def _changed_spans(before: str, after: str) -> list[RepairTextDeltaV1]:
    before_lines = before.splitlines(keepends=True)
    after_lines = after.splitlines(keepends=True)
    before_offsets = _offsets(before_lines)
    after_offsets = _offsets(after_lines)
    spans: list[RepairTextDeltaV1] = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(
        a=before_lines,
        b=after_lines,
        autojunk=False,
    ).get_opcodes():
        if tag == "equal":
            continue
        before_text = "".join(before_lines[i1:i2])
        after_text = "".join(after_lines[j1:j2])
        spans.append(
            RepairTextDeltaV1(
                before_start=before_offsets[i1],
                before_end=before_offsets[i2],
                after_start=after_offsets[j1],
                after_end=after_offsets[j2],
                before_sha256=_sha256(before_text),
                after_sha256=_sha256(after_text),
                before_excerpt=before_text[:500],
                after_excerpt=after_text[:500],
            )
        )
    return spans


def _offsets(lines: list[str]) -> list[int]:
    result = [0]
    for line in lines:
        result.append(result[-1] + len(line))
    return result


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _slug(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(value).casefold()).strip("-")
