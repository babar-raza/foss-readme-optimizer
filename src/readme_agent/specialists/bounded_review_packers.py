"""Greedy factual and visitor packet builders for bounded README review."""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from typing import Any

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.agentic_composition_inputs import composition_fact_payloads
from readme_agent.readme.document_plan import CandidateContentProvenanceV1
from readme_agent.specialists.bounded_review_contracts import (
    BoundedFactualPacketV1,
    UnpacketizableRecordV1,
)
from readme_agent.specialists.bounded_review_hashing import _packet_id_slug, _packet_sha256
from readme_agent.specialists.bounded_review_structure import _MutableUnit
from readme_agent.specialists.bounded_review_visitor_packers import build_visitor_packets


def _greedy_group_units(
    units: Sequence[_MutableUnit],
    *,
    budget_chars: int,
    size_fn: Callable[[list[_MutableUnit]], int],
) -> tuple[list[list[_MutableUnit]], list[_MutableUnit]]:
    """Greedily accumulate units, in order, never splitting a unit across groups."""

    groups: list[list[_MutableUnit]] = []
    oversized: list[_MutableUnit] = []
    current: list[_MutableUnit] = []
    for unit in units:
        if size_fn([unit]) > budget_chars:
            if current:
                groups.append(current)
                current = []
            oversized.append(unit)
            continue
        trial = [*current, unit]
        if current and size_fn(trial) > budget_chars:
            groups.append(current)
            current = [unit]
        else:
            current = trial
    if current:
        groups.append(current)
    return groups, oversized


def _build_factual_packets(
    *,
    sections: list[list[_MutableUnit]],
    candidate_text: str,
    candidate_sha256: str,
    product_facts: ProductFactsV2,
    accepted_fact_ids_by_claim: dict[str, tuple[str, ...]],
    do_not_claim_sorted: tuple[dict[str, Any], ...],
    valid_provenance: list[CandidateContentProvenanceV1],
    provenance_char_spans: dict[str, tuple[int, int]],
    budget_chars: int,
    factual_prompt_sha256: str,
    input_contract_hash: str,
    algorithm_contract_version: str,
) -> tuple[list[BoundedFactualPacketV1], list[UnpacketizableRecordV1]]:
    packets: list[BoundedFactualPacketV1] = []
    unpacketizable: list[UnpacketizableRecordV1] = []
    order = 0

    for group in sections:
        section_path = group[0].section_path
        section_start = group[0].char_start
        section_end = group[-1].char_end
        section_provenance = [
            entry
            for entry in valid_provenance
            if section_start <= provenance_char_spans[entry.provenance_id][0] < section_end
        ]

        def overlapping_provenance(
            unit: _MutableUnit,
            *,
            _section_provenance: list[CandidateContentProvenanceV1] = section_provenance,
        ) -> list[CandidateContentProvenanceV1]:
            return [
                entry
                for entry in _section_provenance
                if unit.char_start < provenance_char_spans[entry.provenance_id][1]
                and provenance_char_spans[entry.provenance_id][0] < unit.char_end
            ]

        def unit_fact_ids(unit: _MutableUnit) -> set[str]:
            ids: set[str] = set()
            for claim_id in unit.claim_ids:
                ids.update(accepted_fact_ids_by_claim.get(claim_id, ()))
            for entry in overlapping_provenance(unit):
                ids.update(entry.fact_ids)
            return ids

        factual_units = [unit for unit in group if unit_fact_ids(unit)]
        if not factual_units:
            continue

        def group_size(units: list[_MutableUnit]) -> int:
            text_len = units[-1].char_end - units[0].char_start
            fact_ids: set[str] = set()
            for unit in units:
                fact_ids.update(unit_fact_ids(unit))
            facts_payload = composition_fact_payloads(product_facts, fact_ids)
            return text_len + len(
                json.dumps(facts_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            )

        groups_of_units, oversized = _greedy_group_units(
            factual_units, budget_chars=budget_chars, size_fn=group_size
        )
        for unit in oversized:
            unpacketizable.append(
                UnpacketizableRecordV1(
                    record_id=f"unpacketizable-oversized-factual-{unit.unit_id}",
                    reason="oversized_unit",
                    section_path=section_path,
                    char_start=unit.char_start,
                    char_end=unit.char_end,
                    unit_kind=unit.kind,
                    required_min_budget=group_size([unit]),
                    detail=(
                        f"unit {unit.unit_id!r} in section {section_path!r} exceeds budget_chars "
                        "for factual packing even alone"
                    ),
                )
            )

        for local_index, group_units in enumerate(groups_of_units):
            claim_id_set = {cid for unit in group_units for cid in unit.claim_ids}
            claim_ids_sorted = tuple(sorted(claim_id_set))
            fact_ids: set[str] = set()
            for unit in group_units:
                fact_ids.update(unit_fact_ids(unit))
            facts_payload = tuple(
                sorted(
                    composition_fact_payloads(product_facts, fact_ids),
                    key=lambda item: str(item.get("fact_id", "")),
                )
            )
            provenance_ids_sorted = tuple(
                sorted(
                    {
                        entry.provenance_id
                        for unit in group_units
                        for entry in overlapping_provenance(unit)
                    }
                )
            )
            unit_text = candidate_text[group_units[0].char_start : group_units[-1].char_end]
            covered_unit_ids = tuple(unit.unit_id for unit in group_units)
            # Deliberately excludes candidate_sha256 AND absolute position (char/line
            # start/end): packet_sha256 must depend only on this packet's own local content so
            # that an edit elsewhere in the document cannot invalidate every packet -- either
            # through a whole-document hash embedded in each one, or (subtler) through every
            # downstream packet's absolute offsets shifting when upstream text changes length,
            # even though their own text is byte-identical. Both would defeat selective
            # invalidation by construction. Both are still stored as ordinary fields on the
            # packet itself (below) for echo/staleness validation and human inspection.
            substantive: dict[str, Any] = {
                "facet": "factual",
                "section_path": section_path,
                "unit_text": unit_text,
                "covered_unit_ids": covered_unit_ids,
                "claim_ids": claim_ids_sorted,
                "accepted_fact_ids": tuple(sorted(fact_ids)),
                "facts": facts_payload,
                "do_not_claim": do_not_claim_sorted,
                "provenance_ids": provenance_ids_sorted,
                "prompt_contract_hash": factual_prompt_sha256,
                "input_contract_hash": input_contract_hash,
            }
            packet_sha256 = _packet_sha256(
                substantive, algorithm_contract_version=algorithm_contract_version
            )
            slug = _packet_id_slug(section_path)
            packet_id = f"pkt-factual-{order:04d}-{slug}-{packet_sha256[:12]}"
            stable_slot_id = f"factual:{section_path}:{local_index:02d}"
            packets.append(
                BoundedFactualPacketV1(
                    packet_id=packet_id,
                    stable_slot_id=stable_slot_id,
                    order=order,
                    candidate_sha256=candidate_sha256,
                    char_start=group_units[0].char_start,
                    char_end=group_units[-1].char_end,
                    line_start=group_units[0].line_start,
                    line_end=group_units[-1].line_end,
                    packet_sha256=packet_sha256,
                    **substantive,
                )
            )
            order += 1

    return packets, unpacketizable


_build_visitor_packets = build_visitor_packets
