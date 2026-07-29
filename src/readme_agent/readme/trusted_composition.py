"""Orchestrate bounded LLM-first composition for README-trusted evidence."""

from __future__ import annotations

import hashlib
import json

from pydantic import ValidationError

from readme_agent import env
from readme_agent.errors import LLMError
from readme_agent.evidence.writer import unified_diff
from readme_agent.facts.trusted_readme_schema import TrustedReadmeFactGraphV1
from readme_agent.llm.generation_prompts import (
    build_trusted_readme_section_messages,
    build_trusted_readme_section_tool_schema,
)
from readme_agent.llm.prompt_registry import prompt_hash
from readme_agent.llm.verifier_client import ForcedToolClient, LiveForcedToolClient
from readme_agent.readme.trusted_composition_batching import (
    TrustedCompositionBatch,
    build_trusted_composition_batches,
)
from readme_agent.readme.trusted_composition_candidate_validation import (
    validate_trusted_candidate_contract,
)
from readme_agent.readme.trusted_composition_models import (
    TrustedCompositionEnvelopeV1,
    TrustedReadmeCompositionOutputV1,
    TrustedReadmeSectionDraftV1,
    TrustedReadmeSectionToolDraftV1,
    TrustedReadmeTransformPlanV1,
)
from readme_agent.readme.trusted_composition_validation import (
    assemble_trusted_candidate,
    validate_trusted_section_tool_draft,
)

_JOB = "trusted_readme_section_transform"
_MAX_ATTEMPTS = 3


def _canonical_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _batch_payload(batch: TrustedCompositionBatch) -> dict:
    return {
        "batch_id": batch.batch_id,
        "source_items": [item.model_dump(mode="json") for item in batch.source_items],
        "configured_standards": [
            standard.model_dump(mode="json") for standard in batch.configured_standards
        ],
    }


def _compose_batch(
    org_repo: str,
    batch: TrustedCompositionBatch,
    envelope: TrustedCompositionEnvelopeV1,
    client: ForcedToolClient,
) -> tuple[TrustedReadmeSectionToolDraftV1, TrustedReadmeSectionDraftV1]:
    payload = _batch_payload(batch)
    tool_schema = build_trusted_readme_section_tool_schema(
        fact_ids=[item.fact_id for item in batch.source_items],
        configured_standard_ids=[item.standard_id for item in batch.configured_standards],
    )
    schema_hash = _canonical_hash(tool_schema)
    repair_hint = ""
    last_error: Exception | None = None
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        call_input = {
            "org_repo": org_repo,
            "batch": payload,
            "envelope": envelope.model_dump(mode="json"),
            "repair_hint": repair_hint,
        }
        messages = build_trusted_readme_section_messages(
            org_repo=org_repo,
            batch_json=json.dumps(payload, sort_keys=True, ensure_ascii=False),
            envelope_json=json.dumps(envelope.model_dump(mode="json"), sort_keys=True),
            repair_hint=repair_hint,
        )
        result = client.call(messages, tool_schema)
        try:
            draft = TrustedReadmeSectionToolDraftV1.model_validate(result.arguments)
            validate_trusted_section_tool_draft(draft, batch, envelope)
        except (LLMError, ValidationError) as exc:
            last_error = exc
            if attempt == _MAX_ATTEMPTS:
                raise LLMError(
                    f"trusted composition batch {batch.batch_id} failed after "
                    f"{_MAX_ATTEMPTS} attempts: {exc}"
                ) from exc
            repair_hint = (
                f"Your prior output was rejected: {exc}. Return all enumerated source facts and "
                "configured standards exactly once. Preserve context-truncated facts exactly."
            )
            continue
        bound = TrustedReadmeSectionDraftV1(
            batch_id=batch.batch_id,
            editorial_summary=draft.editorial_summary,
            source_inventory=draft.source_inventory,
            segments=draft.segments,
            prompt_sha256=prompt_hash(_JOB),
            tool_schema_sha256=schema_hash,
            input_sha256=_canonical_hash(call_input),
            model=result.meta.model or env.llm_model_for_job(_JOB),
            attempt_count=attempt,
        )
        return draft, bound
    assert last_error is not None
    raise LLMError(str(last_error))


def compose_trusted_readme(
    graph: TrustedReadmeFactGraphV1,
    source_text: str,
    *,
    client: ForcedToolClient | None = None,
    envelope: TrustedCompositionEnvelopeV1 | None = None,
) -> TrustedReadmeCompositionOutputV1:
    """Compose one candidate through as many bounded LLM section calls as needed."""

    source_hash = hashlib.sha256(source_text.encode("utf-8")).hexdigest()
    if source_hash != graph.readme_sha256:
        raise LLMError("trusted composition source bytes do not match the inherited fact graph")
    resolved_envelope = envelope or TrustedCompositionEnvelopeV1()
    resolved_client = client or LiveForcedToolClient(
        base_url=env.llm_base_url(),
        api_key=env.llm_api_key(),
        model=env.llm_model_for_job(_JOB),
        timeout=env.llm_timeout_seconds(),
        max_tokens=8_000,
        job=_JOB,
        prompt_id=_JOB,
    )
    tool_drafts: list[TrustedReadmeSectionToolDraftV1] = []
    section_drafts: list[TrustedReadmeSectionDraftV1] = []
    for batch in build_trusted_composition_batches(graph, resolved_envelope):
        tool_draft, bound_draft = _compose_batch(
            graph.org_repo,
            batch,
            resolved_envelope,
            resolved_client,
        )
        tool_drafts.append(tool_draft)
        section_drafts.append(bound_draft)
    candidate = assemble_trusted_candidate(graph, tool_drafts)
    validate_trusted_candidate_contract(source_text, candidate, graph)
    candidate_hash = hashlib.sha256(candidate.encode("utf-8")).hexdigest()
    plan = TrustedReadmeTransformPlanV1(
        org_repo=graph.org_repo,
        source_revision=graph.source_revision,
        source_sha256=source_hash,
        fact_graph_hash=graph.canonical_hash(),
        envelope=resolved_envelope,
        section_drafts=tuple(section_drafts),
        inherited_fact_ids=tuple(fact.fact_id for fact in graph.inherited_facts),
        configured_standard_ids=tuple(
            standard.standard_id for standard in graph.configured_standards
        ),
        candidate_sha256=candidate_hash,
    )
    return TrustedReadmeCompositionOutputV1(
        org_repo=graph.org_repo,
        plan=plan,
        plan_hash=plan.canonical_hash(),
        candidate_markdown=candidate,
        candidate_patch=unified_diff(source_text, candidate),
        candidate_sha256=candidate_hash,
        llm_call_count=sum(draft.attempt_count for draft in section_drafts),
    )
