"""Claim, provenance, and fact accountability for bounded review units."""

from __future__ import annotations

import bisect
import re
from collections.abc import Sequence
from typing import Any, Literal

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.claim_accountability_models import (
    ReadmeClaimAccountabilityMapV1,
    ReadmeClaimAccountabilityV1,
)
from readme_agent.readme.document_plan import CandidateContentProvenanceV1
from readme_agent.specialists.bounded_review_contracts import (
    AtomicUnitV1,
    SectionClassificationV1,
)
from readme_agent.specialists.bounded_review_hashing import _canonical_hash
from readme_agent.specialists.bounded_review_structure import _build_raw_units, _MutableUnit


def _byte_offset_table(text: str) -> list[int]:
    """Cumulative UTF-8 byte offset for character index ``i`` (len(text)+1 entries)."""

    offsets = [0]
    total = 0
    for ch in text:
        total += len(ch.encode("utf-8"))
        offsets.append(total)
    return offsets


def _char_span_from_byte_span(
    byte_offsets: list[int], byte_start: int, byte_end: int
) -> tuple[int, int]:
    return bisect.bisect_left(byte_offsets, byte_start), bisect.bisect_left(byte_offsets, byte_end)


def _section_path_at(raw_units: list[_MutableUnit], char_offset: int) -> str:
    starts = [u.char_start for u in raw_units]
    idx = bisect.bisect_right(starts, char_offset) - 1
    return raw_units[idx].section_path if idx >= 0 else "front-matter"


def _merge_units_for_claim_spans(
    units: list[_MutableUnit],
    claim_char_spans: list[tuple[int, int, str]],
) -> list[_MutableUnit]:
    """Merge overlapping units until no claim span straddles a unit boundary."""

    changed = True
    while changed:
        changed = False
        for char_start, char_end, _claim_id in claim_char_spans:
            if char_end <= char_start:
                continue
            overlap_indices = [
                idx
                for idx, unit in enumerate(units)
                if unit.char_start < char_end and char_start < unit.char_end
            ]
            if len(overlap_indices) > 1:
                first, last = overlap_indices[0], overlap_indices[-1]
                group = units[first : last + 1]
                kinds = {unit.kind for unit in group}
                merged = _MutableUnit(
                    kind=next(iter(kinds)) if len(kinds) == 1 else "paragraph",
                    char_start=group[0].char_start,
                    char_end=group[-1].char_end,
                    line_start=group[0].line_start,
                    line_end=group[-1].line_end,
                    section_path=group[0].section_path,
                )
                units = units[:first] + [merged] + units[last + 1 :]
                changed = True
                break
    return units


def _attach_claim_ids(
    units: list[_MutableUnit], claim_char_spans: list[tuple[int, int, str]]
) -> None:
    for char_start, char_end, claim_id in claim_char_spans:
        if char_end <= char_start:
            continue
        for unit in units:
            if unit.char_start <= char_start and char_end <= unit.char_end:
                unit.claim_ids.append(claim_id)
                break


def _attach_provenance_ids(units: list[_MutableUnit], spans: list[tuple[int, int, str]]) -> None:
    for char_start, char_end, provenance_id in spans:
        if char_end <= char_start:
            continue
        for unit in units:
            if unit.char_start < char_end and char_start < unit.char_end:
                unit.provenance_ids.append(provenance_id)


def _group_into_sections(units: Sequence[Any]) -> list[list[Any]]:
    groups: list[list[Any]] = []
    for unit in units:
        if groups and groups[-1][-1].section_path == unit.section_path:
            groups[-1].append(unit)
        else:
            groups.append([unit])
    return groups


def _dedupe_section_paths(sections: list[list[_MutableUnit]]) -> None:
    """Disambiguate non-adjacent recurrences of the same heading text/slug."""

    seen: dict[str, int] = {}
    for group in sections:
        base = group[0].section_path
        seen[base] = seen.get(base, 0) + 1
        if seen[base] > 1:
            new_path = f"{base}~{seen[base]}"
            for unit in group:
                unit.section_path = new_path


def _classify_sections(
    sections: Sequence[Sequence[Any]],
    *,
    api_inventory_heading_keywords: frozenset[str],
    api_inventory_table_fence_threshold: float,
) -> dict[str, SectionClassificationV1]:
    result: dict[str, SectionClassificationV1] = {}
    for group in sections:
        section_path = group[0].section_path
        heading_words = set(re.split(r"[/-]", section_path))
        keyword_match = bool(heading_words & api_inventory_heading_keywords)
        total_chars = sum(unit.char_end - unit.char_start for unit in group) or 1
        table_fence_chars = sum(
            unit.char_end - unit.char_start for unit in group if unit.kind in {"table", "fence"}
        )
        dominated = (table_fence_chars / total_chars) >= api_inventory_table_fence_threshold
        if keyword_match and dominated:
            classification: Literal["standard", "mechanical_api_inventory"] = (
                "mechanical_api_inventory"
            )
            justification = (
                f"section path {section_path!r} matches an API-inventory keyword and "
                f"{table_fence_chars}/{total_chars} characters "
                f"({table_fence_chars / total_chars:.0%}) are table/fence content"
            )
        else:
            classification = "standard"
            justification = (
                "does not meet the configured API-inventory heading-keyword + "
                "table/fence-dominance heuristic"
            )
        result[section_path] = SectionClassificationV1(
            section_path=section_path,
            char_start=group[0].char_start,
            char_end=group[-1].char_end,
            classification=classification,
            justification=justification,
        )
    return result


def _claim_char_spans(
    byte_offsets: list[int], claims: Sequence[ReadmeClaimAccountabilityV1]
) -> list[tuple[int, int, str]]:
    spans = []
    for claim in claims:
        char_start, char_end = _char_span_from_byte_span(
            byte_offsets, claim.source_byte_start, claim.source_byte_end
        )
        spans.append((char_start, char_end, claim.claim_id))
    return spans


def _provenance_char_spans(
    byte_offsets: list[int], entries: Sequence[CandidateContentProvenanceV1]
) -> list[tuple[int, int, str]]:
    spans = []
    for entry in entries:
        char_start, char_end = _char_span_from_byte_span(
            byte_offsets, entry.candidate_byte_start, entry.candidate_byte_end
        )
        spans.append((char_start, char_end, entry.provenance_id))
    return spans


def _order_invariant_claim_accountability_hash(
    claim_accountability: ReadmeClaimAccountabilityMapV1,
) -> str:
    """Hash a claim map's substance without depending on its ``claims`` array order.

    ``ReadmeClaimAccountabilityMapV1.canonical_hash()`` uses sorted-key JSON, but ``sort_keys``
    only sorts dict keys -- it does not reorder the ``claims`` list itself. Folding that method's
    result directly into ``plan_hash`` would make the plan's own top-level hash depend on
    caller-supplied claim order, exactly the self-inflicted nondeterminism redesign point 1/2
    exist to rule out. Sorting each claim's dumped payload by its own stable key first closes
    that gap.
    """

    payload = {
        "org_repo": claim_accountability.org_repo,
        "facts_hash": claim_accountability.facts_hash,
        "source_sha256": claim_accountability.source_sha256,
        "candidate_sha256": claim_accountability.candidate_sha256,
        "claims": sorted(
            (claim.model_dump(mode="json") for claim in claim_accountability.claims),
            key=lambda claim: (claim["source_byte_start"], claim["claim_id"]),
        ),
    }
    return _canonical_hash(payload)


def _valid_claims_and_gaps(
    claim_accountability: ReadmeClaimAccountabilityMapV1,
    product_facts: ProductFactsV2,
) -> tuple[list[ReadmeClaimAccountabilityV1], list[tuple[ReadmeClaimAccountabilityV1, str]]]:
    known_fact_ids = {fact.fact_id for fact in product_facts.facts}
    candidate_claims = [
        claim
        for claim in claim_accountability.claims
        if claim.stage == "candidate" and claim.currently_accountable
    ]
    sorted_claims = sorted(
        candidate_claims, key=lambda claim: (claim.source_byte_start, claim.claim_id)
    )
    valid: list[ReadmeClaimAccountabilityV1] = []
    gaps: list[tuple[ReadmeClaimAccountabilityV1, str]] = []
    for claim in sorted_claims:
        missing = sorted(
            fact_id for fact_id in claim.accepted_fact_ids if fact_id not in known_fact_ids
        )
        if missing:
            gaps.append((claim, missing[0]))
        else:
            valid.append(claim)
    return valid, gaps


def _valid_provenance_and_gaps(
    candidate_content_provenance: Sequence[CandidateContentProvenanceV1],
    product_facts: ProductFactsV2,
) -> tuple[list[CandidateContentProvenanceV1], list[tuple[CandidateContentProvenanceV1, str]]]:
    known_fact_ids = {fact.fact_id for fact in product_facts.facts}
    sorted_provenance = sorted(
        candidate_content_provenance,
        key=lambda entry: (entry.candidate_byte_start, entry.provenance_id),
    )
    valid: list[CandidateContentProvenanceV1] = []
    gaps: list[tuple[CandidateContentProvenanceV1, str]] = []
    for entry in sorted_provenance:
        missing = sorted(fact_id for fact_id in entry.fact_ids if fact_id not in known_fact_ids)
        if missing:
            gaps.append((entry, missing[0]))
        else:
            valid.append(entry)
    return valid, gaps


def build_atomic_units(
    candidate_text: str,
    claim_accountability: ReadmeClaimAccountabilityMapV1,
    product_facts: ProductFactsV2,
    candidate_content_provenance: Sequence[CandidateContentProvenanceV1] = (),
) -> tuple[AtomicUnitV1, ...]:
    """Parse ``candidate_text`` into stable, claim-respecting atomic units.

    Deterministic and pure: identical input always produces identical output (redesign point 1),
    and input sequences are normalized by a stable sort key before use regardless of caller-
    supplied order (redesign point 2). Referentially broken claims (an ``accepted_fact_ids`` entry
    absent from ``product_facts``) never affect unit boundaries -- they are excluded from claim-id
    attachment here exactly as they are excluded from packet claim-cluster boundaries in
    ``plan_bounded_review_packets``, since a broken claim's span cannot be trusted for merging.
    """

    raw_units = _build_raw_units(candidate_text)
    byte_offsets = _byte_offset_table(candidate_text)
    valid_claims, _claim_gaps = _valid_claims_and_gaps(claim_accountability, product_facts)
    claim_char_spans = _claim_char_spans(byte_offsets, valid_claims)
    merged = _merge_units_for_claim_spans(raw_units, claim_char_spans)
    _attach_claim_ids(merged, claim_char_spans)
    provenance_char_spans = _provenance_char_spans(byte_offsets, candidate_content_provenance)
    _attach_provenance_ids(merged, provenance_char_spans)
    sections = _group_into_sections(merged)
    _dedupe_section_paths(sections)
    for index, unit in enumerate(merged):
        unit.unit_id = f"unit-{index:04d}-{unit.kind}"
    return tuple(
        AtomicUnitV1(
            unit_id=unit.unit_id,
            kind=unit.kind,
            section_path=unit.section_path,
            char_start=unit.char_start,
            char_end=unit.char_end,
            line_start=unit.line_start,
            line_end=unit.line_end,
            claim_ids=tuple(sorted(set(unit.claim_ids))),
            provenance_ids=tuple(sorted(set(unit.provenance_ids))),
        )
        for unit in merged
    )
