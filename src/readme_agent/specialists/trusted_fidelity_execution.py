"""Execute bounded trusted fidelity review batches and reduce them deterministically."""

from __future__ import annotations

import hashlib
from pathlib import Path

from readme_agent import env
from readme_agent.errors import LLMError
from readme_agent.facts.trusted_readme_schema import TrustedReadmeFactGraphV1
from readme_agent.llm import prompt_registry
from readme_agent.llm.call_ledger import record_non_provider_call
from readme_agent.llm.verification_prompts import build_trusted_fidelity_review_messages
from readme_agent.readme.trusted_composition_models import (
    TrustedReadmeCompositionOutputV1,
)
from readme_agent.specialists.review_role_execution import AnalysisClientLike
from readme_agent.specialists.trusted_fidelity_cache import (
    LEGACY_FIDELITY_BATCH_CONTRACT_VERSION,
    load_trusted_fidelity_cache,
    trusted_fidelity_cache_key,
    write_trusted_fidelity_cache,
)
from readme_agent.specialists.trusted_fidelity_context import build_trusted_fidelity_context
from readme_agent.specialists.trusted_fidelity_validation import (
    TrustedFidelityRoleFailure,
    normalize_trusted_fidelity_output,
    run_trusted_fidelity_role,
    validate_trusted_fidelity_result,
)
from readme_agent.specialists.trusted_transform_review_models import (
    TrustedFidelityReviewResultV1,
    TrustedRoleVerdictV1,
)

MAX_FIDELITY_FACTS_PER_CALL = 8
MAX_FIDELITY_SOURCE_CHARACTERS_PER_CALL = 6_000


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
            legacy_global_plan_context = plan_context
            candidate_projection_sha256 = hashlib.sha256(
                review_candidate.encode("utf-8")
            ).hexdigest()
            plan_context = {
                **{key: value for key, value in plan_context.items() if key != "candidate_sha256"},
                "candidate_projection_sha256": candidate_projection_sha256,
            }
            prompt_sha256 = prompt_registry.prompt_hash("trusted_readme_fidelity_review")
            model = env.llm_model_for_job("trusted_readme_fidelity_review")
            cache_key = trusted_fidelity_cache_key(
                graph,
                plan_hash=draft.canonical_hash(),
                candidate_sha256=candidate_projection_sha256,
                review_batch_id=review_batch_id,
                fact_ids=fact_ids,
                fact_context=fact_context,
                plan_context=plan_context,
                prompt_sha256=prompt_sha256,
                model=model,
            )
            cached = (
                load_trusted_fidelity_cache(cache_dir, review_batch_id, cache_key)
                if cache_dir is not None
                else None
            )
            migrated = False
            if cached is None and cache_dir is not None:
                legacy_keys = (
                    trusted_fidelity_cache_key(
                        graph,
                        plan_hash=draft.canonical_hash(),
                        candidate_sha256=candidate_projection_sha256,
                        review_batch_id=review_batch_id,
                        fact_ids=fact_ids,
                        fact_context=fact_context,
                        plan_context=plan_context,
                        prompt_sha256=prompt_sha256,
                        model=model,
                        contract_version=LEGACY_FIDELITY_BATCH_CONTRACT_VERSION,
                    ),
                    trusted_fidelity_cache_key(
                        graph,
                        plan_hash=composition.plan_hash,
                        candidate_sha256=composition.candidate_sha256,
                        review_batch_id=review_batch_id,
                        fact_ids=fact_ids,
                        fact_context=fact_context,
                        plan_context=legacy_global_plan_context,
                        prompt_sha256=prompt_sha256,
                        model=model,
                        contract_version=LEGACY_FIDELITY_BATCH_CONTRACT_VERSION,
                    ),
                )
                legacy = next(
                    (
                        candidate
                        for legacy_key in legacy_keys
                        if (
                            candidate := load_trusted_fidelity_cache(
                                cache_dir,
                                review_batch_id,
                                legacy_key,
                            )
                        )
                        is not None
                    ),
                    None,
                )
                if legacy is not None:
                    migrated_value = normalize_trusted_fidelity_output(
                        legacy.result.model_dump(mode="json"),
                        graph=graph,
                        candidate_text=review_candidate,
                        allow_unsupported_additions=part_number == 1,
                    )
                    migrated_result = TrustedFidelityReviewResultV1.model_validate(migrated_value)
                    if not validate_trusted_fidelity_result(
                        migrated_result,
                        batch_graph,
                        review_candidate,
                        allow_unsupported_additions=part_number == 1,
                        authorization_graph=graph,
                    ):
                        cached = write_trusted_fidelity_cache(
                            cache_dir,
                            cache_key=cache_key,
                            graph=graph,
                            review_batch_id=review_batch_id,
                            result=migrated_result,
                            retry_history=legacy.retry_history,
                        )
                        migrated = True
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
                        "migrated_from_previous_contract": migrated,
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
    reduced = TrustedFidelityReviewResultV1.model_validate(
        normalize_trusted_fidelity_output(
            reduced.model_dump(mode="json"),
            graph=graph,
            candidate_text=composition.candidate_markdown,
        )
    )
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
    """Project each review onto its batch-owned final candidate byte range."""

    del graph
    candidate = composition.candidate_markdown.encode("utf-8")
    projected: dict[str, str] = {}
    for draft in composition.plan.section_drafts:
        records = [
            record
            for record in composition.ownership_map.records
            if record.batch_id == draft.batch_id
        ]
        if records:
            start = min(record.byte_start for record in records)
            end = max(record.byte_end for record in records)
            projected[draft.batch_id] = candidate[start:end].decode("utf-8")
            continue
        fallback = "\n\n".join(
            segment.markdown.strip() for segment in draft.segments if segment.markdown.strip()
        )
        if not fallback:
            raise LLMError(f"trusted fidelity batch {draft.batch_id} has no owned candidate bytes")
        projected[draft.batch_id] = fallback
    return projected


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
