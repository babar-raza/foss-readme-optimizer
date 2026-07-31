"""Build conservative exact ownership maps for normalized trusted candidates."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from readme_agent.facts.trusted_readme_schema import (
    ConfiguredStandardIdV1,
    TrustedReadmeFactGraphV1,
)
from readme_agent.readme.presentation_contract import (
    PRESENTATION_CONTRACT_VERSION,
    PRESENTATION_EMOJI_POLICY,
    PRESENTATION_ENTERPRISE_LINK_SECTION,
    PRESENTATION_H2_PREFIX,
    PRESENTATION_HEADING_SUFFIX_ALIASES,
    PRESENTATION_MERMAID_GRAMMAR,
    PRESENTATION_MERMAID_MAX_LABEL_CHARACTERS,
    PRESENTATION_MERMAID_MAX_NODES,
)
from readme_agent.readme.trusted_candidate_ownership_models import (
    CandidateSpanOwnerKindV1,
    CandidateSpanOwnershipMapV1,
    CandidateSpanOwnershipRecordV1,
    sha256_bytes,
    stable_record_id,
)
from readme_agent.readme.trusted_composition_models import TrustedReadmeSectionDraftV1
from readme_agent.readme.trusted_portfolio_brand import strip_readme_emojis

_MATERIAL_BLOCK = re.compile(r"(?s).+?(?=\n{2,}|\Z)")
_BLOCK_SEPARATOR = re.compile(r"((?:\r?\n){2,})")
_NORMALIZATION_OPERATIONS = (
    "strip_readme_comments",
    "normalize_inherited_code_blocks",
    "normalize_enterprise_edition_terminology",
    "normalize_portfolio_headings",
    "normalize_portfolio_mermaid",
    "normalize_required_section_headings",
    "normalize_portfolio_header_assets",
    "normalize_key_capabilities",
    "normalize_portfolio_emojis",
    "normalize_promotional_links",
    "normalize_navigation",
    "normalize_contextual_link_budget",
    "normalize_enterprise_product_links",
)


@dataclass(frozen=True)
class _OwnedText:
    owner_id: str
    owner_kind: CandidateSpanOwnerKindV1
    text: str
    batch_id: str
    stable_segment_id: str
    producer_segment_id: str
    inherited_fact_ids: tuple[str, ...]
    configured_standard_ids: tuple[ConfiguredStandardIdV1, ...]


def build_candidate_span_ownership_map(
    graph: TrustedReadmeFactGraphV1,
    candidate: str,
    section_drafts: tuple[TrustedReadmeSectionDraftV1, ...],
) -> CandidateSpanOwnershipMapV1:
    """Map exact surviving blocks and conservatively own every transformed gap."""

    candidate_bytes = candidate.encode("utf-8")
    owned = _owned_material_blocks(graph, section_drafts)
    assigned: list[tuple[int, int, _OwnedText]] = []
    for item in owned:
        start_char = candidate.find(item.text)
        if start_char < 0 or candidate.find(item.text, start_char + 1) >= 0:
            continue
        end_char = start_char + len(item.text)
        start = len(candidate[:start_char].encode("utf-8"))
        end = len(candidate[:end_char].encode("utf-8"))
        if any(
            not (end <= prior_start or start >= prior_end) for prior_start, prior_end, _ in assigned
        ):
            continue
        assigned.append((start, end, item))
    assigned.sort(key=lambda row: row[0])

    records: list[CandidateSpanOwnershipRecordV1] = []
    cursor = 0
    for start, end, item in assigned:
        if start > cursor:
            records.extend(_generated_records(candidate_bytes, cursor, start, owned))
        records.append(
            _record(
                candidate_bytes,
                start,
                end,
                owner_id=item.owner_id,
                owner_kind=item.owner_kind,
                batch_id=item.batch_id,
                stable_segment_id=item.stable_segment_id,
                producer_segment_id=item.producer_segment_id,
                inherited_fact_ids=item.inherited_fact_ids,
                configured_standard_ids=item.configured_standard_ids,
                operations=(),
            )
        )
        cursor = end
    if cursor < len(candidate_bytes):
        records.extend(_generated_records(candidate_bytes, cursor, len(candidate_bytes), owned))

    for record in records:
        if sha256_bytes(candidate_bytes[record.byte_start : record.byte_end]) != record.text_sha256:
            raise ValueError("candidate ownership record hash does not match final bytes")
    return CandidateSpanOwnershipMapV1(
        org_repo=graph.org_repo,
        source_revision=graph.source_revision,
        source_sha256=graph.readme_sha256,
        candidate_sha256=hashlib.sha256(candidate_bytes).hexdigest(),
        presentation_contract_sha256=_presentation_contract_hash(),
        normalization_contract_sha256=_normalization_contract_hash(),
        candidate_byte_length=len(candidate_bytes),
        records=tuple(records),
    )


def records_covering_range(
    ownership: CandidateSpanOwnershipMapV1,
    byte_start: int,
    byte_end: int,
) -> tuple[CandidateSpanOwnershipRecordV1, ...]:
    """Return every exact ownership record intersecting a candidate byte range."""

    return tuple(
        record
        for record in ownership.records
        if record.byte_start < byte_end and record.byte_end > byte_start
    )


def _owned_material_blocks(
    graph: TrustedReadmeFactGraphV1,
    section_drafts: tuple[TrustedReadmeSectionDraftV1, ...],
) -> tuple[_OwnedText, ...]:
    facts = {fact.fact_id: fact.value for fact in graph.inherited_facts}
    items: list[_OwnedText] = []
    for draft in section_drafts:
        for ordinal, segment in enumerate(draft.segments, start=1):
            stable_segment_id = f"{draft.batch_id}.segment-{ordinal:03d}"
            text = (
                facts[segment.inherited_fact_ids[0]]
                if segment.kind == "preserve_exact"
                else segment.markdown.rstrip() + "\n"
            ).strip("\n")
            for block_index, match in enumerate(_MATERIAL_BLOCK.finditer(text), start=1):
                block = match.group(0).strip("\n")
                if not block.strip():
                    continue
                items.append(
                    _OwnedText(
                        owner_id=f"{stable_segment_id}.block-{block_index:03d}",
                        owner_kind=(
                            "preserved" if segment.kind == "preserve_exact" else "authored"
                        ),
                        text=block,
                        batch_id=draft.batch_id,
                        stable_segment_id=stable_segment_id,
                        producer_segment_id=segment.segment_id,
                        inherited_fact_ids=segment.inherited_fact_ids,
                        configured_standard_ids=segment.configured_standard_ids,
                    )
                )
    return tuple(items)


def _generated_records(
    candidate: bytes,
    start: int,
    end: int,
    owned: tuple[_OwnedText, ...],
) -> tuple[CandidateSpanOwnershipRecordV1, ...]:
    """Split transformed gaps and retain uniquely inferable producer lineage."""

    text = candidate[start:end].decode("utf-8")
    records: list[CandidateSpanOwnershipRecordV1] = []
    byte_cursor = start
    for part in (value for value in _BLOCK_SEPARATOR.split(text) if value):
        part_bytes = part.encode("utf-8")
        part_end = byte_cursor + len(part_bytes)
        if not part.strip():
            records.append(
                _record(
                    candidate,
                    byte_cursor,
                    part_end,
                    owner_id="assembly:separator",
                    owner_kind="assembly",
                )
            )
        else:
            lineage = _infer_normalized_lineage(part, owned)
            records.append(
                _record(
                    candidate,
                    byte_cursor,
                    part_end,
                    owner_id=(
                        "normalizer:canonical"
                        if lineage is None
                        else f"normalizer:{lineage.stable_segment_id}"
                    ),
                    owner_kind="normalizer",
                    batch_id=None if lineage is None else lineage.batch_id,
                    stable_segment_id=None if lineage is None else lineage.stable_segment_id,
                    producer_segment_id=None if lineage is None else lineage.producer_segment_id,
                    inherited_fact_ids=() if lineage is None else lineage.inherited_fact_ids,
                    configured_standard_ids=(
                        () if lineage is None else lineage.configured_standard_ids
                    ),
                    operations=_NORMALIZATION_OPERATIONS,
                )
            )
        byte_cursor = part_end
    return tuple(records)


def _infer_normalized_lineage(
    candidate_block: str,
    owned: tuple[_OwnedText, ...],
) -> _OwnedText | None:
    ranked = sorted(
        ((_lineage_score(candidate_block, item.text), item) for item in owned),
        key=lambda row: row[0],
        reverse=True,
    )
    if not ranked or ranked[0][0] < 0.58:
        return None
    if len(ranked) > 1 and ranked[0][0] - ranked[1][0] < 0.08:
        return None
    return ranked[0][1]


def _lineage_score(candidate: str, source: str) -> float:
    def canonical(value: str) -> str:
        visible = strip_readme_emojis(value)
        visible = re.sub(r"(?<!!)\[([^\]]+)\]\([^)]+\)", r"\1", visible)
        return " ".join(re.findall(r"[a-z0-9.+#-]+", visible.casefold()))

    candidate_value = canonical(candidate)
    source_value = canonical(source)
    if not candidate_value or not source_value:
        return 0.0
    if candidate_value == source_value:
        return 1.0
    sequence = SequenceMatcher(a=source_value, b=candidate_value, autojunk=False).ratio()
    candidate_tokens = set(candidate_value.split())
    source_tokens = set(source_value.split())
    overlap = len(candidate_tokens & source_tokens) / max(len(candidate_tokens | source_tokens), 1)
    suffix = (
        0.9 if source_value.endswith(candidate_value) and candidate_value.startswith("#") else 0.0
    )
    return max((0.7 * sequence) + (0.3 * overlap), suffix)


def _record(
    candidate: bytes,
    start: int,
    end: int,
    *,
    owner_id: str,
    owner_kind: CandidateSpanOwnerKindV1,
    batch_id: str | None = None,
    stable_segment_id: str | None = None,
    producer_segment_id: str | None = None,
    inherited_fact_ids: tuple[str, ...] = (),
    configured_standard_ids: tuple[ConfiguredStandardIdV1, ...] = (),
    operations: tuple[str, ...] = (),
) -> CandidateSpanOwnershipRecordV1:
    digest = sha256_bytes(candidate[start:end])
    return CandidateSpanOwnershipRecordV1(
        record_id=stable_record_id(
            {
                "owner_id": owner_id,
                "byte_start": start,
                "byte_end": end,
                "text_sha256": digest,
            }
        ),
        owner_id=owner_id,
        owner_kind=owner_kind,
        byte_start=start,
        byte_end=end,
        text_sha256=digest,
        batch_id=batch_id,
        stable_segment_id=stable_segment_id,
        producer_segment_id=producer_segment_id,
        inherited_fact_ids=inherited_fact_ids,
        configured_standard_ids=configured_standard_ids,
        normalization_operations=operations,
    )


def _presentation_contract_hash() -> str:
    return _json_hash(
        {
            "version": PRESENTATION_CONTRACT_VERSION,
            "h2_prefix": PRESENTATION_H2_PREFIX,
            "heading_suffix_aliases": PRESENTATION_HEADING_SUFFIX_ALIASES,
            "emoji_policy": PRESENTATION_EMOJI_POLICY,
            "mermaid_grammar": PRESENTATION_MERMAID_GRAMMAR,
            "mermaid_max_nodes": PRESENTATION_MERMAID_MAX_NODES,
            "mermaid_max_label_characters": PRESENTATION_MERMAID_MAX_LABEL_CHARACTERS,
            "enterprise_link_section": PRESENTATION_ENTERPRISE_LINK_SECTION,
        }
    )


def _normalization_contract_hash() -> str:
    return _json_hash(_NORMALIZATION_OPERATIONS)


def _json_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
