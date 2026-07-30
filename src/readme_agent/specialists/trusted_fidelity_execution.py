"""Execute bounded trusted fidelity review batches and reduce them deterministically."""

from __future__ import annotations

from pathlib import Path

from readme_agent import env
from readme_agent.errors import LLMError
from readme_agent.facts.trusted_readme_schema import TrustedReadmeFactGraphV1
from readme_agent.llm import prompt_registry
from readme_agent.llm.call_ledger import record_non_provider_call
from readme_agent.llm.verification_prompts import build_trusted_fidelity_review_messages
from readme_agent.readme.trusted_composition_candidate_validation import (
    normalize_trusted_candidate,
)
from readme_agent.readme.trusted_composition_models import (
    TrustedReadmeCompositionOutputV1,
)
from readme_agent.readme.trusted_composition_validation import join_trusted_markdown_parts
from readme_agent.specialists.review_role_execution import AnalysisClientLike
from readme_agent.specialists.trusted_fidelity_cache import (
    load_trusted_fidelity_cache,
    trusted_fidelity_cache_key,
    write_trusted_fidelity_cache,
)
from readme_agent.specialists.trusted_fidelity_context import build_trusted_fidelity_context
from readme_agent.specialists.trusted_fidelity_validation import (
    TrustedFidelityRoleFailure,
    run_trusted_fidelity_role,
    validate_trusted_fidelity_result,
)
from readme_agent.specialists.trusted_transform_review_models import (
    TrustedFidelityReviewResultV1,
    TrustedRoleVerdictV1,
)

MAX_FIDELITY_FACTS_PER_CALL = 8
MAX_FIDELITY_SOURCE_CHARACTERS_PER_CALL = 6_000
_BOUNDARY_PREFIX = "# README_AGENT_FIDELITY_BOUNDARY_"


def run_batched_trusted_fidelity_review(
    *,
    client: AnalysisClientLike,
    graph: TrustedReadmeFactGraphV1,
    composition: TrustedReadmeCompositionOutputV1,
    cache_dir: Path | None = None,
) -> tuple[TrustedFidelityReviewResultV1, tuple[dict, ...]]:
    """Review at the authoring-batch bound, then prove full-graph coverage."""

    facts_by_id = {fact.fact_id: fact for fact in graph.inherited_facts}
    results: list[TrustedFidelityReviewResultV1] = []
    history: list[dict] = []
    review_candidates = _render_review_candidates(composition, graph)
    for draft in composition.plan.section_drafts:
        draft_fact_ids = tuple(item.fact_id for item in draft.source_inventory)
        review_candidate = review_candidates[draft.batch_id]
        fact_chunks = partition_fidelity_fact_ids(
            draft_fact_ids,
            {fact_id: facts_by_id[fact_id].value for fact_id in draft_fact_ids},
        )
        for part_number, fact_ids in enumerate(fact_chunks, start=1):
            review_batch_id = f"{draft.batch_id}.part-{part_number:04d}"
            batch_graph = graph.model_copy(
                update={
                    "inherited_facts": tuple(facts_by_id[fact_id] for fact_id in fact_ids),
                    "configured_standards": tuple(
                        standard
                        for standard in graph.configured_standards
                        if any(
                            standard.standard_id in segment.configured_standard_ids
                            for segment in draft.segments
                        )
                    ),
                }
            )
            fact_context, plan_context = build_trusted_fidelity_context(
                graph,
                composition.plan,
                batch_id=draft.batch_id,
                selected_fact_ids=fact_ids,
                addition_evidence_fact_ids=draft_fact_ids if part_number == 1 else (),
            )
            cache_key = trusted_fidelity_cache_key(
                graph,
                plan_hash=composition.plan_hash,
                candidate_sha256=composition.candidate_sha256,
                review_batch_id=review_batch_id,
                fact_ids=fact_ids,
                fact_context=fact_context,
                plan_context=plan_context,
                prompt_sha256=prompt_registry.prompt_hash("trusted_readme_fidelity_review"),
                model=env.llm_model_for_job("trusted_readme_fidelity_review"),
            )
            cached = (
                load_trusted_fidelity_cache(cache_dir, review_batch_id, cache_key)
                if cache_dir is not None
                else None
            )
            if cached is not None:
                result = cached.result
                batch_history = cached.retry_history
                record_non_provider_call(
                    job="trusted_readme_fidelity_review",
                    prompt_id="trusted_readme_fidelity_review",
                    prompt_sha256=prompt_registry.prompt_hash("trusted_readme_fidelity_review"),
                    model=env.llm_model_for_job("trusted_readme_fidelity_review"),
                    disposition="cache_reuse",
                    request={
                        "review_batch_id": review_batch_id,
                        "cache_key": cache_key,
                    },
                )
            else:
                try:
                    result, batch_history = run_trusted_fidelity_role(
                        client=client,
                        messages=build_trusted_fidelity_review_messages(
                            graph.org_repo,
                            _canonical_json(fact_context),
                            _canonical_json(plan_context),
                            review_candidate,
                        ),
                        graph=batch_graph,
                        candidate_text=review_candidate,
                        allow_unsupported_additions=part_number == 1,
                        authorization_graph=graph,
                    )
                except TrustedFidelityRoleFailure as exc:
                    failed_history = [
                        *history,
                        *({"batch_id": review_batch_id, **item} for item in exc.retry_history),
                    ]
                    raise TrustedFidelityRoleFailure(
                        str(exc),
                        retry_history=tuple(failed_history),
                    ) from exc
                if cache_dir is not None:
                    write_trusted_fidelity_cache(
                        cache_dir,
                        cache_key=cache_key,
                        graph=graph,
                        review_batch_id=review_batch_id,
                        result=result,
                        retry_history=batch_history,
                    )
            results.append(result)
            history.extend({"batch_id": review_batch_id, **item} for item in batch_history)
    reduced = _reduce_fidelity_results(results)
    errors = validate_trusted_fidelity_result(
        reduced,
        graph,
        composition.candidate_markdown,
    )
    if errors:
        raise TrustedFidelityRoleFailure(
            f"batched fidelity reduction violated full-graph coverage: {errors}",
            retry_history=tuple(history),
        )
    return reduced, tuple(history)


def _render_review_candidates(
    composition: TrustedReadmeCompositionOutputV1,
    graph: TrustedReadmeFactGraphV1,
) -> dict[str, str]:
    """Render batch excerpts through the final candidate's global normalizers."""

    facts_by_id = {fact.fact_id: fact for fact in graph.inherited_facts}
    rendered: list[str] = []
    markers: list[str] = []
    drafts = composition.plan.section_drafts
    for index, draft in enumerate(drafts):
        if index:
            marker = f"{_BOUNDARY_PREFIX}{index:04d}"
            if marker in composition.candidate_markdown:
                raise LLMError("trusted fidelity boundary marker collides with candidate content")
            markers.append(marker)
            rendered.append(marker + "\n")
        for segment in draft.segments:
            if segment.kind == "preserve_exact":
                rendered.append(facts_by_id[segment.inherited_fact_ids[0]].value)
            else:
                rendered.append(segment.markdown.rstrip() + "\n")
    marked_candidate = join_trusted_markdown_parts(rendered)
    normalized = normalize_trusted_candidate(
        marked_candidate,
        graph,
        navigation_boundary_prefix=_BOUNDARY_PREFIX,
    )
    excerpts: list[str] = []
    start = 0
    for marker in markers:
        marker_start = normalized.find(marker, start)
        if marker_start < 0:
            raise LLMError("trusted fidelity boundary marker was lost during normalization")
        excerpts.append(normalized[start:marker_start].strip("\n"))
        start = marker_start + len(marker)
    excerpts.append(normalized[start:].strip("\n"))
    if len(excerpts) != len(drafts):
        raise LLMError("trusted fidelity candidate partition count is inconsistent")
    if any(not excerpt or excerpt not in composition.candidate_markdown for excerpt in excerpts):
        raise LLMError("trusted fidelity candidate excerpt is absent from the final candidate")
    return dict(zip((draft.batch_id for draft in drafts), excerpts, strict=True))


def partition_fidelity_fact_ids(
    fact_ids: tuple[str, ...],
    values_by_id: dict[str, str],
) -> tuple[tuple[str, ...], ...]:
    """Bound each fidelity call by both inventory size and source characters."""

    chunks: list[tuple[str, ...]] = []
    current: list[str] = []
    current_characters = 0
    for fact_id in fact_ids:
        value_characters = len(values_by_id[fact_id])
        exceeds_bound = current and (
            len(current) >= MAX_FIDELITY_FACTS_PER_CALL
            or current_characters + value_characters > MAX_FIDELITY_SOURCE_CHARACTERS_PER_CALL
        )
        if exceeds_bound:
            chunks.append(tuple(current))
            current = []
            current_characters = 0
        current.append(fact_id)
        current_characters += value_characters
    if current:
        chunks.append(tuple(current))
    return tuple(chunks)


def _reduce_fidelity_results(
    results: list[TrustedFidelityReviewResultV1],
) -> TrustedFidelityReviewResultV1:
    if not results:
        raise LLMError("trusted fidelity review requires at least one source batch")
    verdict: TrustedRoleVerdictV1
    if any(result.verdict == "SYSTEM_FAILURE" for result in results):
        verdict = "SYSTEM_FAILURE"
    elif any(result.verdict == "REJECT_REPAIRABLE" for result in results):
        verdict = "REJECT_REPAIRABLE"
    else:
        verdict = "ACCEPT"
    additions = {
        addition.finding_id: addition
        for result in results
        for addition in result.unsupported_additions
    }
    failed_criteria = tuple(
        dict.fromkeys(criterion for result in results for criterion in result.failed_criteria)
    )
    sections = tuple(
        dict.fromkeys(section for result in results for section in result.sections_affected)
    )
    repairs = tuple(
        dict.fromkeys(
            result.required_repair for result in results if result.required_repair.strip()
        )
    )
    reasoning = " | ".join(result.reasoning for result in results)
    if verdict == "ACCEPT":
        reasoning = (
            "All bounded fidelity shards passed deterministic grounding; every required "
            "source fact is preserved or represented and no in-scope unsupported addition remains."
        )
    return TrustedFidelityReviewResultV1(
        verdict=verdict,
        reasoning=reasoning,
        source_checks=tuple(check for result in results for check in result.source_checks),
        unsupported_additions=tuple(additions.values()),
        failed_criteria=failed_criteria,
        sections_affected=sections,
        required_repair="; ".join(repairs),
    )


def _canonical_json(value: object) -> str:
    import json

    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
