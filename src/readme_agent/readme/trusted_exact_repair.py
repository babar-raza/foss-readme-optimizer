"""Apply grounded exact trusted-candidate repairs without another author call."""

from __future__ import annotations

import hashlib
import re

from readme_agent.errors import LLMError
from readme_agent.evidence.writer import unified_diff
from readme_agent.facts.trusted_readme_schema import TrustedReadmeFactGraphV1
from readme_agent.readme.trusted_candidate_ownership import (
    build_candidate_span_ownership_map,
    records_covering_range,
)
from readme_agent.readme.trusted_candidate_ownership_models import (
    TrustedRepairActionV1,
    sha256_bytes,
    stable_action_id,
)
from readme_agent.readme.trusted_composition_candidate_validation import (
    normalize_trusted_candidate,
    validate_trusted_candidate_contract,
)
from readme_agent.readme.trusted_composition_models import TrustedReadmeCompositionOutputV1


def apply_grounded_exact_removal(
    graph: TrustedReadmeFactGraphV1,
    source_text: str,
    prior: TrustedReadmeCompositionOutputV1,
    *,
    finding_id: str,
    quoted_candidate_span: str,
    instruction: str,
) -> tuple[TrustedReadmeCompositionOutputV1, TrustedRepairActionV1]:
    """Remove one unique grounded span and preserve every unaffected owned block."""

    _validate_inputs(graph, source_text, prior)
    candidate = prior.candidate_markdown
    if candidate.count(quoted_candidate_span) != 1:
        raise LLMError("grounded exact removal requires one unique literal candidate span")
    removal_range = exact_prose_paragraph_range(candidate, quoted_candidate_span)
    if removal_range is None:
        raise LLMError("grounded exact removal requires one complete prose paragraph")
    char_start, char_end = removal_range
    candidate_bytes = candidate.encode("utf-8")
    byte_start = len(candidate[:char_start].encode("utf-8"))
    byte_end = len(candidate[:char_end].encode("utf-8"))
    owners = records_covering_range(prior.ownership_map, byte_start, byte_end)
    if not owners:
        raise LLMError("grounded exact removal has no candidate ownership record")
    old_bytes = candidate_bytes[byte_start:byte_end]
    repaired_bytes = candidate_bytes[:byte_start] + candidate_bytes[byte_end:]
    repaired = normalize_trusted_candidate(repaired_bytes.decode("utf-8"), graph)
    validate_trusted_candidate_contract(source_text, repaired, graph)
    repaired_hash = hashlib.sha256(repaired.encode("utf-8")).hexdigest()
    if repaired_hash == prior.candidate_sha256:
        raise LLMError("grounded exact removal returned byte-identical candidate")
    protected = _protected_content_hashes(prior, owners)
    _verify_protected_content(prior, repaired, owners)
    action_payload = {
        "org_repo": graph.org_repo,
        "source_revision": graph.source_revision,
        "finding_id": finding_id,
        "candidate_sha256_before": prior.candidate_sha256,
        "byte_start": byte_start,
        "byte_end": byte_end,
        "expected_old_sha256": sha256_bytes(old_bytes),
    }
    action = TrustedRepairActionV1(
        action_id=stable_action_id(action_payload),
        org_repo=graph.org_repo,
        source_revision=graph.source_revision,
        finding_id=finding_id,
        action="remove_exact",
        instruction=instruction,
        quoted_candidate_span=quoted_candidate_span,
        candidate_sha256_before=prior.candidate_sha256,
        candidate_sha256_after=repaired_hash,
        ownership_map_sha256=prior.ownership_map.canonical_hash(),
        owner_record_ids=tuple(record.record_id for record in owners),
        byte_start=byte_start,
        byte_end=byte_end,
        expected_old_sha256=sha256_bytes(old_bytes),
        replacement_text="",
        replacement_sha256=sha256_bytes(b""),
        protected_record_sha256s=protected,
        llm_author_calls=0,
    )
    actions = (*prior.plan.repair_actions, action)
    plan = prior.plan.model_copy(
        update={
            "repair_actions": actions,
            "candidate_sha256": repaired_hash,
        }
    )
    ownership = build_candidate_span_ownership_map(
        graph,
        repaired,
        plan.section_drafts,
    )
    result = TrustedReadmeCompositionOutputV1(
        org_repo=prior.org_repo,
        plan=plan,
        plan_hash=plan.canonical_hash(),
        candidate_markdown=repaired,
        candidate_patch=unified_diff(source_text, repaired),
        candidate_sha256=repaired_hash,
        ownership_map=ownership,
        llm_call_count=prior.llm_call_count,
    )
    return result, action


def exact_prose_paragraph_range(candidate: str, quote: str) -> tuple[int, int] | None:
    """Return a safe complete-paragraph removal range, excluding Markdown structure."""

    if not quote.strip() or candidate.count(quote) != 1:
        return None
    start = candidate.index(quote)
    end = start + len(quote)
    paragraph_start = candidate.rfind("\n\n", 0, start)
    paragraph_start = 0 if paragraph_start < 0 else paragraph_start + 2
    paragraph_end = candidate.find("\n\n", end)
    paragraph_end = len(candidate) if paragraph_end < 0 else paragraph_end
    paragraph = candidate[paragraph_start:paragraph_end]
    if paragraph.strip() != quote.strip():
        return None
    lines = tuple(line.lstrip() for line in paragraph.strip().splitlines())
    structural_prefixes = ("#", "-", "*", "+", ">", "|", "```", "~~~")
    if any(
        line.startswith(structural_prefixes) or re.match(r"^\d+[.)]\s", line)
        for line in lines
        if line
    ):
        return None
    if paragraph_end < len(candidate):
        paragraph_end += 2
    return paragraph_start, paragraph_end


def _validate_inputs(
    graph: TrustedReadmeFactGraphV1,
    source_text: str,
    prior: TrustedReadmeCompositionOutputV1,
) -> None:
    if graph.org_repo != prior.org_repo or graph.source_revision != prior.plan.source_revision:
        raise LLMError("trusted exact repair inputs belong to different repository snapshots")
    source_hash = hashlib.sha256(source_text.encode("utf-8")).hexdigest()
    if source_hash != graph.readme_sha256 or source_hash != prior.plan.source_sha256:
        raise LLMError("trusted exact repair source bytes are stale")
    if prior.ownership_map.candidate_sha256 != prior.candidate_sha256:
        raise LLMError("trusted exact repair ownership map is stale")


def _protected_content_hashes(
    prior: TrustedReadmeCompositionOutputV1,
    affected: tuple,
) -> tuple[str, ...]:
    affected_ids = {record.record_id for record in affected}
    return tuple(
        record.text_sha256
        for record in prior.ownership_map.records
        if record.record_id not in affected_ids and record.owner_kind in {"authored", "preserved"}
    )


def _verify_protected_content(
    prior: TrustedReadmeCompositionOutputV1,
    repaired: str,
    affected: tuple,
) -> None:
    affected_ids = {record.record_id for record in affected}
    before = prior.candidate_markdown.encode("utf-8")
    after = repaired.encode("utf-8")
    for record in prior.ownership_map.records:
        if record.record_id in affected_ids or record.owner_kind not in {"authored", "preserved"}:
            continue
        block = before[record.byte_start : record.byte_end]
        if block not in after:
            raise LLMError(f"trusted exact repair changed protected span {record.record_id}")
