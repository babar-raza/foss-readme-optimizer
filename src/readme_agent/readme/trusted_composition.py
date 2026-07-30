"""Orchestrate bounded LLM-first composition for README-trusted evidence."""

from __future__ import annotations

import hashlib
from pathlib import Path

from readme_agent import env
from readme_agent.errors import LLMError
from readme_agent.evidence.writer import unified_diff
from readme_agent.facts.trusted_readme_schema import TrustedReadmeFactGraphV1
from readme_agent.llm.call_ledger import record_non_provider_call
from readme_agent.llm.prompt_registry import prompt_hash
from readme_agent.llm.verifier_client import ForcedToolClient, LiveForcedToolClient
from readme_agent.readme.trusted_composition_batching import build_trusted_composition_batches
from readme_agent.readme.trusted_composition_cache import (
    default_trusted_batch_cache_dir,
    load_trusted_batch_cache,
    trusted_batch_cache_key,
    write_trusted_batch_cache,
)
from readme_agent.readme.trusted_composition_candidate_validation import (
    normalize_trusted_candidate,
    validate_trusted_candidate_contract,
)
from readme_agent.readme.trusted_composition_execution import (
    TRUSTED_COMPOSITION_JOB,
    compose_trusted_batch,
    trusted_batch_tool_schema_hash,
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


def compose_trusted_readme(
    graph: TrustedReadmeFactGraphV1,
    source_text: str,
    *,
    client: ForcedToolClient | None = None,
    envelope: TrustedCompositionEnvelopeV1 | None = None,
    batch_cache_dir: Path | None = None,
) -> TrustedReadmeCompositionOutputV1:
    """Compose one candidate through as many bounded LLM section calls as needed."""

    source_hash = hashlib.sha256(source_text.encode("utf-8")).hexdigest()
    if source_hash != graph.readme_sha256:
        raise LLMError("trusted composition source bytes do not match the inherited fact graph")
    resolved_envelope = envelope or TrustedCompositionEnvelopeV1()
    live_client = client is None
    resolved_model = env.llm_model_for_job(TRUSTED_COMPOSITION_JOB)
    resolved_client = client or LiveForcedToolClient(
        base_url=env.llm_base_url(),
        api_key=env.llm_api_key(),
        model=resolved_model,
        timeout=env.llm_timeout_seconds(),
        max_tokens=8_000,
        job=TRUSTED_COMPOSITION_JOB,
        prompt_id=TRUSTED_COMPOSITION_JOB,
    )
    resolved_cache_dir = (
        default_trusted_batch_cache_dir(graph)
        if live_client and batch_cache_dir is None
        else batch_cache_dir
    )
    batches = build_trusted_composition_batches(graph, resolved_envelope)
    tool_drafts: list[TrustedReadmeSectionToolDraftV1] = []
    section_drafts: list[TrustedReadmeSectionDraftV1] = []
    batch_cache_keys: list[str] = []
    for batch in batches:
        cache_key = trusted_batch_cache_key(
            graph,
            batch,
            resolved_envelope,
            prompt_sha256=prompt_hash(TRUSTED_COMPOSITION_JOB),
            tool_schema_sha256=trusted_batch_tool_schema_hash(batch),
            model=resolved_model,
        )
        batch_cache_keys.append(cache_key)
        cached = (
            load_trusted_batch_cache(resolved_cache_dir, batch.batch_id, cache_key)
            if resolved_cache_dir is not None
            else None
        )
        if cached is not None:
            tool_draft, bound_draft = cached.tool_draft, cached.bound_draft
            validate_trusted_section_tool_draft(
                tool_draft,
                batch,
                resolved_envelope,
            )
            record_non_provider_call(
                job=TRUSTED_COMPOSITION_JOB,
                prompt_id=TRUSTED_COMPOSITION_JOB,
                prompt_sha256=prompt_hash(TRUSTED_COMPOSITION_JOB),
                model=cached.model,
                disposition="cache_reuse",
                request={"batch_id": batch.batch_id, "cache_key": cache_key},
            )
        else:
            tool_draft, bound_draft = compose_trusted_batch(
                graph.org_repo,
                batch,
                resolved_envelope,
                resolved_client,
            )
            if resolved_cache_dir is not None:
                write_trusted_batch_cache(
                    resolved_cache_dir,
                    cache_key=cache_key,
                    org_repo=graph.org_repo,
                    source_revision=graph.source_revision,
                    model=resolved_model,
                    tool_draft=tool_draft,
                    bound_draft=bound_draft,
                )
        tool_drafts.append(tool_draft)
        section_drafts.append(bound_draft)
    call_count = sum(draft.attempt_count for draft in section_drafts)
    standards_batch_index = next(
        (index for index, batch in enumerate(batches) if batch.configured_standards),
        None,
    )
    pending_repaired_cache: (
        tuple[
            int,
            TrustedReadmeSectionToolDraftV1,
            TrustedReadmeSectionDraftV1,
        ]
        | None
    ) = None
    for repair_round in range(3):
        try:
            output = finalize_trusted_composition(
                graph,
                source_text,
                resolved_envelope,
                tool_drafts,
                section_drafts,
                llm_call_count=call_count,
            )
            if resolved_cache_dir is not None and pending_repaired_cache is not None:
                repaired_index, repaired_tool, repaired_bound = pending_repaired_cache
                write_trusted_batch_cache(
                    resolved_cache_dir,
                    cache_key=batch_cache_keys[repaired_index],
                    org_repo=graph.org_repo,
                    source_revision=graph.source_revision,
                    model=resolved_model,
                    tool_draft=repaired_tool,
                    bound_draft=repaired_bound,
                )
            return output
        except LLMError as exc:
            if standards_batch_index is None or repair_round == 2:
                raise
            repaired_tool, repaired_bound = compose_trusted_batch(
                graph.org_repo,
                batches[standards_batch_index],
                resolved_envelope,
                resolved_client,
                initial_repair_hint=(
                    "The complete assembled README failed deterministic presentation "
                    f"validation: {exc}. Repair this standards-bearing batch so the complete "
                    "README satisfies every configured standard."
                ),
            )
            tool_drafts[standards_batch_index] = repaired_tool
            section_drafts[standards_batch_index] = repaired_bound
            pending_repaired_cache = (
                standards_batch_index,
                repaired_tool,
                repaired_bound,
            )
            call_count += repaired_bound.attempt_count
    raise AssertionError("trusted composition final repair loop did not return")


def finalize_trusted_composition(
    graph: TrustedReadmeFactGraphV1,
    source_text: str,
    envelope: TrustedCompositionEnvelopeV1,
    tool_drafts: list[TrustedReadmeSectionToolDraftV1],
    section_drafts: list[TrustedReadmeSectionDraftV1],
    *,
    llm_call_count: int | None = None,
) -> TrustedReadmeCompositionOutputV1:
    """Bind assembled candidate bytes and plan hashes after initial work or repair."""

    source_hash = hashlib.sha256(source_text.encode("utf-8")).hexdigest()
    if source_hash != graph.readme_sha256:
        raise LLMError("trusted composition source bytes do not match the inherited fact graph")
    candidate = normalize_trusted_candidate(assemble_trusted_candidate(graph, tool_drafts), graph)
    validate_trusted_candidate_contract(source_text, candidate, graph)
    candidate_hash = hashlib.sha256(candidate.encode("utf-8")).hexdigest()
    plan = TrustedReadmeTransformPlanV1(
        org_repo=graph.org_repo,
        source_revision=graph.source_revision,
        source_sha256=source_hash,
        fact_graph_hash=graph.canonical_hash(),
        envelope=envelope,
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
        llm_call_count=(
            llm_call_count
            if llm_call_count is not None
            else sum(draft.attempt_count for draft in section_drafts)
        ),
    )
