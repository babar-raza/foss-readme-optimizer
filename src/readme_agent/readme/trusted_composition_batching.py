"""Split trusted README facts into deterministic context-bounded batches."""

from __future__ import annotations

from dataclasses import dataclass

from readme_agent.facts.trusted_readme_schema import (
    ConfiguredStandardAdditionV1,
    InheritedReadmeFactV1,
    TrustedReadmeFactGraphV1,
)
from readme_agent.readme.trusted_composition_models import (
    TrustedCompositionEnvelopeV1,
    TrustedCompositionSourceItemV1,
)


@dataclass(frozen=True)
class TrustedCompositionBatch:
    batch_id: str
    source_items: tuple[TrustedCompositionSourceItemV1, ...]
    configured_standards: tuple[ConfiguredStandardAdditionV1, ...]
    global_structures_allowed: bool


def _context_text(
    fact: InheritedReadmeFactV1,
    envelope: TrustedCompositionEnvelopeV1,
) -> tuple[str, bool]:
    value = fact.value
    if len(value) <= envelope.max_input_characters:
        return value, False
    limit = envelope.oversize_fact_preview_characters
    half = max(128, limit // 2)
    return (
        value[:half]
        + "\n\n[CONTEXT PREVIEW OMITTED; EXACT SOURCE WILL BE PRESERVED]\n\n"
        + value[-half:],
        True,
    )


def _source_item(
    fact: InheritedReadmeFactV1,
    envelope: TrustedCompositionEnvelopeV1,
) -> TrustedCompositionSourceItemV1:
    text, truncated = _context_text(fact, envelope)
    span = fact.source_span
    return TrustedCompositionSourceItemV1(
        fact_id=fact.fact_id,
        material_kind=fact.material_kind,
        heading_path=fact.heading_path,
        source_byte_start=span.byte_start,
        source_byte_end=span.byte_end,
        source_sha256=span.content_sha256,
        text=text,
        text_truncated_for_context=truncated,
    )


def build_trusted_composition_batches(
    graph: TrustedReadmeFactGraphV1,
    envelope: TrustedCompositionEnvelopeV1,
) -> tuple[TrustedCompositionBatch, ...]:
    """Partition in source order without splitting a bounded H2 section."""

    batches: list[list[TrustedCompositionSourceItemV1]] = []
    current: list[TrustedCompositionSourceItemV1] = []
    current_characters = 0
    items = [_source_item(fact, envelope) for fact in graph.inherited_facts]
    for section in _contiguous_h2_sections(items):
        section_characters = sum(len(item.text) for item in section)
        section_fits = (
            not any(item.text_truncated_for_context for item in section)
            and len(section) <= envelope.max_facts_per_batch
            and section_characters <= envelope.max_input_characters
        )
        current_would_overflow = current and (
            len(current) + len(section) > envelope.max_facts_per_batch
            or current_characters + section_characters > envelope.max_input_characters
        )
        if section_fits and current_would_overflow:
            batches.append(current)
            current = []
            current_characters = 0
        if section_fits:
            current.extend(section)
            current_characters += section_characters
            continue
        if current:
            batches.append(current)
            current = []
            current_characters = 0
        for item in section:
            item_characters = len(item.text)
            would_overflow = current and (
                item.text_truncated_for_context
                or len(current) >= envelope.max_facts_per_batch
                or current_characters + item_characters > envelope.max_input_characters
            )
            if would_overflow:
                batches.append(current)
                current = []
                current_characters = 0
            current.append(item)
            current_characters += item_characters
            if item.text_truncated_for_context:
                batches.append(current)
                current = []
                current_characters = 0
    if current:
        batches.append(current)
    return tuple(
        TrustedCompositionBatch(
            batch_id=f"batch-{index:04d}",
            source_items=tuple(items),
            configured_standards=graph.configured_standards if index == 1 else (),
            global_structures_allowed=index == 1,
        )
        for index, items in enumerate(batches, start=1)
    )


def _contiguous_h2_sections(
    items: list[TrustedCompositionSourceItemV1],
) -> tuple[tuple[TrustedCompositionSourceItemV1, ...], ...]:
    """Group the preamble and each H2 subtree while retaining source order."""

    grouped: list[list[TrustedCompositionSourceItemV1]] = []
    current: list[TrustedCompositionSourceItemV1] = []
    current_key: str | None = None
    for item in items:
        key = item.heading_path[1] if len(item.heading_path) > 1 else ""
        if current and key != current_key:
            grouped.append(current)
            current = []
        current.append(item)
        current_key = key
    if current:
        grouped.append(current)
    return tuple(tuple(group) for group in grouped)
