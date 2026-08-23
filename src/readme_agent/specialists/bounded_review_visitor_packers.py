"""Build structurally complete visitor-review packets from Markdown sections."""

from __future__ import annotations

from typing import Any

from readme_agent.specialists.bounded_review_contracts import (
    BoundedVisitorPacketV1,
    SectionClassificationV1,
    UnpacketizableRecordV1,
)
from readme_agent.specialists.bounded_review_hashing import _packet_id_slug, _packet_sha256
from readme_agent.specialists.bounded_review_structure import _MutableUnit


def _coalesced_visitor_groups(
    sections: list[list[_MutableUnit]],
    section_classifications: dict[str, SectionClassificationV1],
) -> list[dict[str, Any]]:
    """Keep one H2 and its contiguous child sections in the same visitor context."""

    eligible: list[dict[str, Any]] = []
    coalescible_parent: dict[str, Any] | None = None
    for group in sections:
        section_path = group[0].section_path
        if section_classifications[section_path].classification == "mechanical_api_inventory":
            coalescible_parent = None
            continue

        root = section_path.split("/", maxsplit=1)[0]
        parent = coalescible_parent
        is_contiguous_child = False
        if parent is not None:
            is_contiguous_child = (
                parent["section_path"] == root
                and section_path.startswith(f"{root}/")
                and group[0].char_start <= parent["units"][-1].char_end + 1
            )
        if is_contiguous_child:
            assert parent is not None
            parent["units"].extend(group)
            continue

        spec = {"section_path": section_path, "units": list(group)}
        eligible.append(spec)
        coalescible_parent = spec if section_path == root else None
    return eligible


def _greedy_groups(
    units: list[_MutableUnit],
    *,
    budget_chars: int,
) -> tuple[list[list[_MutableUnit]], list[_MutableUnit]]:
    """Group complete Markdown units without exceeding the packet budget."""

    groups: list[list[_MutableUnit]] = []
    oversized: list[_MutableUnit] = []
    current: list[_MutableUnit] = []
    for unit in units:
        unit_size = unit.char_end - unit.char_start
        if unit_size > budget_chars:
            if current:
                groups.append(current)
                current = []
            oversized.append(unit)
            continue
        trial = [*current, unit]
        trial_size = trial[-1].char_end - trial[0].char_start
        if current and trial_size > budget_chars:
            groups.append(current)
            current = [unit]
        else:
            current = trial
    if current:
        groups.append(current)
    return groups, oversized


def build_visitor_packets(
    *,
    sections: list[list[_MutableUnit]],
    section_classifications: dict[str, SectionClassificationV1],
    candidate_text: str,
    candidate_sha256: str,
    budget_chars: int,
    neighbor_context_chars: int,
    visitor_prompt_sha256: str,
    input_contract_hash: str,
    algorithm_contract_version: str,
) -> tuple[list[BoundedVisitorPacketV1], list[UnpacketizableRecordV1]]:
    """Build visitor packets while preserving nested-section structural context."""

    unpacketizable: list[UnpacketizableRecordV1] = []
    eligible: list[dict[str, Any]] = []
    for spec in _coalesced_visitor_groups(sections, section_classifications):
        groups, oversized = _greedy_groups(spec["units"], budget_chars=budget_chars)
        for unit in oversized:
            unpacketizable.append(
                UnpacketizableRecordV1(
                    record_id=f"unpacketizable-oversized-visitor-{unit.unit_id}",
                    reason="oversized_unit",
                    section_path=spec["section_path"],
                    char_start=unit.char_start,
                    char_end=unit.char_end,
                    unit_kind=unit.kind,
                    required_min_budget=unit.char_end - unit.char_start,
                    detail=(
                        f"unit {unit.unit_id!r} in section {spec['section_path']!r} exceeds "
                        "budget_chars for visitor packing even alone"
                    ),
                )
            )
        if groups:
            eligible.append({"section_path": spec["section_path"], "subgroups": groups})

    packets: list[BoundedVisitorPacketV1] = []
    order = 0
    for section_index, spec in enumerate(eligible):
        subgroups = spec["subgroups"]
        for local_index, group_units in enumerate(subgroups):
            section_text = candidate_text[group_units[0].char_start : group_units[-1].char_end]
            before = ""
            after = ""
            if local_index == 0 and section_index > 0:
                previous = eligible[section_index - 1]["subgroups"][-1]
                previous_text = candidate_text[previous[0].char_start : previous[-1].char_end]
                before = (
                    previous_text[-neighbor_context_chars:] if neighbor_context_chars > 0 else ""
                )
            if local_index == len(subgroups) - 1 and section_index < len(eligible) - 1:
                following = eligible[section_index + 1]["subgroups"][0]
                following_text = candidate_text[following[0].char_start : following[-1].char_end]
                after = (
                    following_text[:neighbor_context_chars] if neighbor_context_chars > 0 else ""
                )
            covered_unit_ids = tuple(unit.unit_id for unit in group_units)
            substantive: dict[str, Any] = {
                "facet": "visitor",
                "section_path": spec["section_path"],
                "section_text": section_text,
                "neighbor_context_before": before,
                "neighbor_context_after": after,
                "covered_unit_ids": covered_unit_ids,
                "prompt_contract_hash": visitor_prompt_sha256,
                "input_contract_hash": input_contract_hash,
            }
            packet_sha256 = _packet_sha256(
                substantive,
                algorithm_contract_version=algorithm_contract_version,
            )
            slug = _packet_id_slug(spec["section_path"])
            packet_id = f"pkt-visitor-{order:04d}-{slug}-{packet_sha256[:12]}"
            stable_slot_id = f"visitor:{spec['section_path']}:{local_index:02d}"
            packets.append(
                BoundedVisitorPacketV1(
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


__all__ = ["build_visitor_packets"]
