"""Normalize recoverable trusted composition defects before strict validation."""

from __future__ import annotations

import re
from collections import Counter

from readme_agent.readme.trusted_composition_batching import TrustedCompositionBatch
from readme_agent.readme.trusted_composition_models import (
    TrustedReadmeDraftSegmentV1,
    TrustedReadmeSectionToolDraftV1,
    TrustedSourceInventoryDecisionV1,
)

_H1 = re.compile(r"^(?P<prefix>\s*)# (?P<title>.+?)\s*(?P<ending>\r?\n)?$")


def normalize_tool_arguments(arguments: dict, batch: TrustedCompositionBatch) -> dict:
    """Drop unbound prose and reconcile model-declared operations to emitted bytes."""

    normalized = dict(arguments)
    segments: list[dict] = []
    for value in arguments.get("segments", []):
        segment = dict(value)
        standards = (
            list(segment.get("configured_standard_ids", [])) if batch.configured_standards else []
        )
        standards = [item for item in standards if item != "__none__"]
        facts = list(segment.get("inherited_fact_ids", []))
        segment["configured_standard_ids"] = standards
        if str(segment.get("markdown", "")).strip() and segment.get("kind") == "preserve_exact":
            segment["kind"] = "authored"
        if facts or standards:
            segments.append(segment)
    if not segments:
        segments = [
            {
                "segment_id": f"fallback-preserve-{index:03d}",
                "kind": "preserve_exact",
                "markdown": "",
                "inherited_fact_ids": [item.fact_id],
                "configured_standard_ids": [],
            }
            for index, item in enumerate(batch.source_items, start=1)
        ]
        normalized["source_inventory"] = [
            {
                "fact_id": item.fact_id,
                "action": "preserve_exact",
                "rationale": "Preserve source when no provenance-bound model segment remains.",
            }
            for item in batch.source_items
        ]
    normalized["segments"] = segments
    return normalized


def normalize_configured_header(
    draft: TrustedReadmeSectionToolDraftV1,
    batch: TrustedCompositionBatch,
) -> TrustedReadmeSectionToolDraftV1:
    """Materialize one configured H1 while preserving every non-heading line."""

    header = next(
        (
            standard
            for standard in batch.configured_standards
            if standard.standard_id == "readme.header"
        ),
        None,
    )
    if header is None:
        return draft
    source_by_id = {item.fact_id: item.text for item in batch.source_items}
    preserved_titles = [
        match.group("title").strip()
        for segment in draft.segments
        if segment.kind == "preserve_exact"
        for match in re.finditer(
            r"(?m)^# (.+?)\s*$",
            source_by_id[segment.inherited_fact_ids[0]],
        )
    ]
    first_title = preserved_titles[0] if preserved_titles else None
    updated_segments: list[TrustedReadmeDraftSegmentV1] = []
    for segment in draft.segments:
        if segment.kind != "authored":
            updated_segments.append(segment)
            continue
        rendered_lines: list[str] = []
        for line in segment.markdown.splitlines(keepends=True):
            match = _H1.fullmatch(line)
            if match is None:
                rendered_lines.append(line)
                continue
            title = match.group("title").strip()
            ending = match.group("ending") or ""
            if first_title is None:
                first_title = title
                rendered_lines.append(line)
            elif title.casefold() == first_title.casefold():
                continue
            else:
                rendered_lines.append(f"{match.group('prefix')}## {title}{ending}")
        updated_segments.append(segment.model_copy(update={"markdown": "".join(rendered_lines)}))
    if first_title is None:
        configured_title = str(
            header.parameters.get("repository_name")
            or header.parameters.get("product_name")
            or "Repository"
        ).strip()
        target = next(
            (
                index
                for index, segment in enumerate(updated_segments)
                if segment.kind == "authored" and "readme.header" in segment.configured_standard_ids
            ),
            None,
        )
        if target is None:
            return draft
        segment = updated_segments[target]
        updated_segments[target] = segment.model_copy(
            update={"markdown": f"# {configured_title}\n\n{segment.markdown.lstrip()}"}
        )
    return draft.model_copy(update={"segments": tuple(updated_segments)})


def preserve_omitted_source_facts(
    draft: TrustedReadmeSectionToolDraftV1,
    batch: TrustedCompositionBatch,
) -> TrustedReadmeSectionToolDraftV1:
    """Reconcile declared actions and fail-safe omitted facts as exact copies."""

    expected = [item.fact_id for item in batch.source_items]
    expected_set = set(expected)
    expected_standards = [item.standard_id for item in batch.configured_standards]
    expected_standard_set = set(expected_standards)
    seen: set[str] = set()
    seen_standards: set[str] = set()
    deduplicated_segments: list[TrustedReadmeDraftSegmentV1] = []
    for segment in draft.segments:
        if any(fact_id not in expected_set for fact_id in segment.inherited_fact_ids):
            return draft
        if any(
            standard_id not in expected_standard_set
            for standard_id in segment.configured_standard_ids
        ):
            return draft
        unique: list[str] = []
        for fact_id in segment.inherited_fact_ids:
            if fact_id not in seen:
                seen.add(fact_id)
                unique.append(fact_id)
        unique_ids = tuple(unique)
        unique_standard_ids = tuple(
            standard_id
            for standard_id in segment.configured_standard_ids
            if standard_id not in seen_standards
        )
        seen_standards.update(unique_standard_ids)
        if not unique_ids and not unique_standard_ids:
            if segment.kind == "authored" and segment.markdown.strip():
                prior_authored = next(
                    (
                        index
                        for index in range(len(deduplicated_segments) - 1, -1, -1)
                        if deduplicated_segments[index].kind == "authored"
                    ),
                    None,
                )
                if prior_authored is None:
                    return draft
                prior = deduplicated_segments[prior_authored]
                deduplicated_segments[prior_authored] = prior.model_copy(
                    update={
                        "markdown": (prior.markdown.rstrip() + "\n\n" + segment.markdown.lstrip())
                    }
                )
            continue
        deduplicated_segments.append(
            segment.model_copy(
                update={
                    "inherited_fact_ids": unique_ids,
                    "configured_standard_ids": unique_standard_ids,
                }
            )
        )
    missing_standards = [
        standard_id for standard_id in expected_standards if standard_id not in seen_standards
    ]
    if missing_standards:
        target = next(
            (
                index
                for index, segment in enumerate(deduplicated_segments)
                if segment.kind == "authored"
            ),
            None,
        )
        if target is not None:
            segment = deduplicated_segments[target]
            deduplicated_segments[target] = segment.model_copy(
                update={
                    "configured_standard_ids": (
                        *segment.configured_standard_ids,
                        *missing_standards,
                    )
                }
            )
    draft = draft.model_copy(update={"segments": tuple(deduplicated_segments)})
    rendered = [fact_id for segment in draft.segments for fact_id in segment.inherited_fact_ids]
    counts = Counter(rendered)
    if any(fact_id not in expected or count > 1 for fact_id, count in counts.items()):
        return draft
    missing = [fact_id for fact_id in expected if counts[fact_id] == 0]
    inventory_by_id = {item.fact_id: item for item in draft.source_inventory}
    source_by_id = {item.fact_id: item for item in batch.source_items}
    rendered_kind = {
        fact_id: segment.kind
        for segment in draft.segments
        for fact_id in segment.inherited_fact_ids
    }
    inventory = [
        (
            TrustedSourceInventoryDecisionV1(
                fact_id=fact_id,
                action="preserve_exact",
                rationale="Deterministic loss-prevention fallback for omitted inherited content.",
            )
            if fact_id in missing
            else (
                TrustedSourceInventoryDecisionV1(
                    fact_id=fact_id,
                    action="rewrite",
                    rationale=(
                        "The authored segment represents this inherited source unit; "
                        "the durable plan records the operation actually emitted."
                    ),
                )
                if rendered_kind.get(fact_id) == "authored"
                and not source_by_id[fact_id].text_truncated_for_context
                else inventory_by_id.get(
                    fact_id,
                    TrustedSourceInventoryDecisionV1(
                        fact_id=fact_id,
                        action="preserve_exact",
                        rationale="Preserve inherited content not inventoried by the author.",
                    ),
                )
            )
        )
        for fact_id in expected
    ]
    segments = list(draft.segments)
    for index, fact_id in enumerate(missing, start=1):
        segments.append(
            TrustedReadmeDraftSegmentV1(
                segment_id=f"fallback-preserve-{index:03d}",
                kind="preserve_exact",
                markdown="",
                inherited_fact_ids=(fact_id,),
            )
        )
    return draft.model_copy(
        update={"source_inventory": tuple(inventory), "segments": tuple(segments)}
    )
