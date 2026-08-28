"""Greedy factual and visitor packet builders for bounded README review."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Sequence
from dataclasses import replace
from typing import Any

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.presentation.verified_template_api_members import select_summary_api_members
from readme_agent.readme.agentic_composition_inputs import composition_fact_payloads
from readme_agent.readme.document_plan import CandidateContentProvenanceV1
from readme_agent.readme.fact_grounding_views import fact_strings
from readme_agent.specialists.bounded_review_contracts import (
    BoundedFactualPacketV1,
    UnpacketizableRecordV1,
)
from readme_agent.specialists.bounded_review_hashing import _packet_id_slug, _packet_sha256
from readme_agent.specialists.bounded_review_structure import _MutableUnit
from readme_agent.specialists.bounded_review_visitor_packers import build_visitor_packets
from readme_agent.specialists.factual_review_projection import (
    compact_repository_examples_for_review,
)

_API_NAMESPACE = re.compile(r"Namespace \(`([^`]+)`\)")
_BOUNDED_FACT_PROJECTION_CONTRACT_VERSION = "bounded-fact-projection-v1"
_MAX_REVIEW_SOURCE_LOCATION_CHARS = 512
_MAX_REVIEW_PROTECTED_LITERALS = 24
_MAX_SCOPED_API_ITEMS = 24


def _compact_bounded_review_fact(payload: dict[str, Any]) -> dict[str, Any]:
    """Remove verifier-only bulk while retaining a hash-bound evidence identity."""

    projected = dict(payload)
    changed = False
    value = projected.get("value")
    if projected.get("field") == "repository.examples" and isinstance(value, dict):
        compacted_value = compact_repository_examples_for_review(value)
        projected["value"] = compacted_value
        projected["protected_literals"] = fact_strings(compacted_value)[
            :_MAX_REVIEW_PROTECTED_LITERALS
        ]
        changed = compacted_value != value

    source = projected.get("source")
    if isinstance(source, dict):
        location = str(source.get("location") or "")
        if len(location) > _MAX_REVIEW_SOURCE_LOCATION_CHARS:
            location_sha256 = hashlib.sha256(location.encode("utf-8")).hexdigest()
            compacted_source = dict(source)
            compacted_source["location"] = (
                f"fact-source://{projected.get('fact_id')}/{location_sha256}"
            )
            compacted_source["full_location_sha256"] = location_sha256
            compacted_source["location_entry_count"] = (
                len(location.removeprefix("repository://").split(","))
                if location.startswith("repository://")
                else 1
            )
            projected["source"] = compacted_source
            changed = True

    if changed:
        projected["review_projection_contract_version"] = _BOUNDED_FACT_PROJECTION_CONTRACT_VERSION
    return projected


def _bounded_fact_payloads(
    product_facts: ProductFactsV2, fact_ids: set[str], unit_text: str, section_text: str = ""
) -> list[dict[str, Any]]:
    """Keep exact API evidence for the namespace rendered in one bounded packet.

    ``section_text`` (when given) spans from the unit's owning heading through
    the unit itself: the namespace regex needs the heading, since a table
    unit's own text never repeats it (see RDM-032 evidence). Falls back to
    ``unit_text`` alone so existing single-argument callers/fixtures that
    already inline a heading into their synthetic unit text keep working.
    Classes/functions in the scoped projection are capped at
    ``_MAX_SCOPED_API_ITEMS`` -- an uncapped "complete for this namespace"
    projection can itself exceed the packet budget for a large namespace,
    which defeats the budget the scoping exists to fit (confirmed live:
    this made a real repository's oversized-unit failure worse, not
    better). ``projection_complete_for_namespace`` reflects truncation
    truthfully rather than always claiming completeness.
    """

    payloads = composition_fact_payloads(product_facts, fact_ids)
    generic = [_compact_bounded_review_fact(payload) for payload in payloads]
    namespace_match = _API_NAMESPACE.search(section_text or unit_text)
    if namespace_match is None:
        return generic
    namespace = namespace_match.group(1)
    by_id = {fact.fact_id: fact for fact in product_facts.facts}
    scoped_payloads = [dict(payload) for payload in payloads]
    scoped_any = False
    for payload in scoped_payloads:
        if payload.get("field") != "api.public_surface":
            continue
        fact = by_id.get(str(payload.get("fact_id")))
        value = fact.value if fact is not None and isinstance(fact.value, dict) else {}
        catalog = value.get("coordinate_catalog")
        if not isinstance(catalog, dict):
            catalog = value
        modules = [
            item
            for item in catalog.get("modules") or []
            if isinstance(item, dict) and item.get("module") == namespace
        ]
        exported_names = {
            str(export)
            for module in modules
            for export in module.get("exports") or []
            if str(export).strip()
        }
        classes = []
        for item in catalog.get("classes") or []:
            if not isinstance(item, dict) or str(item.get("name")) not in exported_names:
                continue
            constructor = item.get("constructor")
            summary_member_keys = {
                (
                    member.get("name"),
                    member.get("surface"),
                    member.get("declared_by"),
                    member.get("inherited"),
                )
                for member in select_summary_api_members(item)
                if isinstance(member, dict)
            }
            members = [
                {
                    "name": member.get("name"),
                    "kind": member.get("kind"),
                    "surface": member.get("surface"),
                    "implemented": member.get("implemented"),
                    "declared_by": member.get("declared_by"),
                    "inherited": member.get("inherited"),
                    "return_annotation": member.get("return_annotation"),
                    "writable": member.get("writable"),
                }
                for member in item.get("members") or []
                if isinstance(member, dict)
                and (
                    (
                        member.get("name"),
                        member.get("surface"),
                        member.get("declared_by"),
                        member.get("inherited"),
                    )
                    in summary_member_keys
                    or (
                        bool(str(member.get("name") or "").strip())
                        and re.search(
                            rf"(?<![A-Za-z0-9_]){re.escape(str(member.get('name')))}"
                            r"(?![A-Za-z0-9_])",
                            unit_text,
                        )
                        is not None
                    )
                )
            ]
            classes.append(
                {
                    "name": item.get("name"),
                    "module": item.get("module"),
                    "qualified_name": item.get("qualified_name"),
                    "bases": item.get("bases") or [],
                    "constructor_surface": (
                        constructor.get("surface") if isinstance(constructor, dict) else None
                    ),
                    "public_members": members,
                    "source_path": item.get("source_path"),
                    "source_sha256": item.get("source_sha256"),
                }
            )
        functions = [
            item
            for item in catalog.get("functions") or []
            if isinstance(item, dict) and item.get("module") == namespace
        ]
        classes_truncated = len(classes) > _MAX_SCOPED_API_ITEMS
        functions_truncated = len(functions) > _MAX_SCOPED_API_ITEMS
        payload["value"] = {
            "namespace": namespace,
            "modules": modules,
            "classes": classes[:_MAX_SCOPED_API_ITEMS],
            "functions": functions[:_MAX_SCOPED_API_ITEMS],
            "projection_contextual": True,
            "projection_complete_for_namespace": not (classes_truncated or functions_truncated),
        }
        scoped_any = True
    if not scoped_any:
        return generic
    return [_compact_bounded_review_fact(payload) for payload in scoped_payloads]


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


def _split_oversized_table_unit(
    unit: _MutableUnit,
    *,
    candidate_text: str,
    budget_chars: int,
    size_fn: Callable[[list[_MutableUnit]], int],
) -> tuple[_MutableUnit, ...]:
    """Split one oversized table at row boundaries without changing candidate bytes.

    A Markdown table is normally one atomic review unit. Large generated API inventories can,
    however, exceed the packet budget even after fact projection. Table rows are already natural
    factual boundaries, so preserve the original unit identity for accountability while exposing
    contiguous, exhaustive row ranges to the packetizer. A single over-budget row remains
    unsplittable and therefore fails closed through the existing oversized-unit record.
    """

    if unit.kind != "table":
        return ()
    visible = candidate_text[unit.char_start : unit.char_end]
    lines = visible.splitlines(keepends=True)
    if len(lines) < 3:
        return ()

    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))

    def part(start_line: int, end_line: int) -> _MutableUnit:
        return replace(
            unit,
            char_start=unit.char_start + offsets[start_line],
            char_end=unit.char_start + offsets[end_line],
            line_start=unit.line_start + start_line,
            line_end=unit.line_start + end_line - 1,
            claim_ids=list(unit.claim_ids),
            provenance_ids=list(unit.provenance_ids),
        )

    parts: list[_MutableUnit] = []
    chunk_start = 0
    accepted: _MutableUnit | None = None
    for line_end in range(1, len(lines) + 1):
        trial = part(chunk_start, line_end)
        if size_fn([trial]) <= budget_chars:
            accepted = trial
            continue
        if accepted is None:
            return ()
        parts.append(accepted)
        chunk_start = line_end - 1
        accepted = part(chunk_start, line_end)
        if size_fn([accepted]) > budget_chars:
            return ()
    if accepted is not None:
        parts.append(accepted)
    return tuple(parts) if len(parts) > 1 else ()


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

        def group_size(units: list[_MutableUnit], *, _section_start: int = section_start) -> int:
            text_len = units[-1].char_end - units[0].char_start
            fact_ids: set[str] = set()
            for unit in units:
                fact_ids.update(unit_fact_ids(unit))
            unit_text = candidate_text[units[0].char_start : units[-1].char_end]
            section_text = candidate_text[_section_start : units[-1].char_end]
            facts_payload = _bounded_fact_payloads(product_facts, fact_ids, unit_text, section_text)
            return text_len + len(
                json.dumps(facts_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            )

        packable_units: list[_MutableUnit] = []
        unsplittable: list[_MutableUnit] = []
        for unit in factual_units:
            if group_size([unit]) <= budget_chars:
                packable_units.append(unit)
                continue
            table_parts = _split_oversized_table_unit(
                unit,
                candidate_text=candidate_text,
                budget_chars=budget_chars,
                size_fn=group_size,
            )
            if table_parts:
                packable_units.extend(table_parts)
            else:
                unsplittable.append(unit)
        groups_of_units, oversized_after_split = _greedy_group_units(
            packable_units, budget_chars=budget_chars, size_fn=group_size
        )
        oversized = [*unsplittable, *oversized_after_split]
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
                    _bounded_fact_payloads(
                        product_facts,
                        fact_ids,
                        candidate_text[group_units[0].char_start : group_units[-1].char_end],
                        candidate_text[section_start : group_units[-1].char_end],
                    ),
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
            covered_unit_ids = tuple(dict.fromkeys(unit.unit_id for unit in group_units))
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
