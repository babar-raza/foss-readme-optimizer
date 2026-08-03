"""Inventory inherited and generated README claims against facts and ownership."""

from __future__ import annotations

import hashlib
from collections import Counter

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.assessment_claims import assess_material_claims
from readme_agent.readme.claim_accountability_coordinates import structured_fact_coordinates
from readme_agent.readme.claim_accountability_helpers import (
    accepted_literal_facts,
    accountability_record,
    candidate_provenance_for_claim,
    claim_text,
    expected_disposition,
    overlapping_candidate_fact_ids,
)
from readme_agent.readme.claim_accountability_models import (
    ClaimOrigin,
    EquivalentCandidateClaimV1,
    ReadmeClaimAccountabilityMapV1,
    ReadmeClaimAccountabilityV1,
    StructuredFactCoordinateV1,
)
from readme_agent.readme.claim_map import ReadmeClaimMapV1
from readme_agent.readme.document_plan import CandidateContentProvenanceV1, SourceClaimResolutionV1
from readme_agent.readme.fact_grounding import literal_fact_ids


def _validated_source_resolutions(
    source_claims,
    resolutions: list[SourceClaimResolutionV1],
) -> dict[str, SourceClaimResolutionV1]:
    by_id = {resolution.claim_id: resolution for resolution in resolutions}
    if len(by_id) != len(resolutions):
        raise ValueError("source claim resolutions contain duplicate claim IDs")
    unknown = sorted(set(by_id) - {claim.claim_id for claim in source_claims})
    if unknown:
        raise ValueError(f"source claim resolutions reference unknown claims: {unknown}")
    return by_id


def _coordinate_key(coordinate: StructuredFactCoordinateV1) -> tuple[str, str, str, str]:
    return (coordinate.fact_id, coordinate.field, coordinate.path, coordinate.value_sha256)


def _structured_equivalence_groups(
    source_records: list[ReadmeClaimAccountabilityV1],
    candidate_records: list[ReadmeClaimAccountabilityV1],
    *,
    excluded_source_claim_ids: set[str],
) -> dict[str, tuple[str, list[str], list[EquivalentCandidateClaimV1]]]:
    eligible_sources = {
        record.claim_id: record
        for record in source_records
        if record.claim_id.removeprefix("source:") not in excluded_source_claim_ids
        and record.current_disposition == "preserve"
        and record.survives_in_candidate is False
        and record.accepted_fact_coordinates
    }
    eligible_candidates = {
        record.claim_id: record
        for record in candidate_records
        if record.currently_accountable and record.accepted_fact_coordinates
    }
    coordinate_nodes: dict[tuple[str, str, str, str], set[str]] = {}
    records = {**eligible_sources, **eligible_candidates}
    for record in records.values():
        for coordinate in record.accepted_fact_coordinates:
            coordinate_nodes.setdefault(_coordinate_key(coordinate), set()).add(record.claim_id)

    adjacency: dict[str, set[str]] = {claim_id: set() for claim_id in records}
    for nodes in coordinate_nodes.values():
        sources = {node for node in nodes if node.startswith("source:")}
        candidates = {node for node in nodes if node.startswith("candidate:")}
        if not sources or not candidates:
            continue
        for source_id in sources:
            adjacency[source_id].update(candidates)
        for candidate_id in candidates:
            adjacency[candidate_id].update(sources)

    result: dict[str, tuple[str, list[str], list[EquivalentCandidateClaimV1]]] = {}
    visited: set[str] = set()
    for starting_id in sorted(eligible_sources):
        if starting_id in visited or not adjacency[starting_id]:
            continue
        pending = [starting_id]
        component: set[str] = set()
        while pending:
            claim_id = pending.pop()
            if claim_id in component:
                continue
            component.add(claim_id)
            pending.extend(adjacency[claim_id] - component)
        visited.update(component)
        source_ids = sorted(item for item in component if item.startswith("source:"))
        candidate_ids = sorted(item for item in component if item.startswith("candidate:"))
        source_coordinates = {
            _coordinate_key(coordinate)
            for claim_id in source_ids
            for coordinate in records[claim_id].accepted_fact_coordinates
        }
        candidate_coordinates = {
            _coordinate_key(coordinate)
            for claim_id in candidate_ids
            for coordinate in records[claim_id].accepted_fact_coordinates
        }
        if not candidate_ids or source_coordinates != candidate_coordinates:
            continue
        group_payload = "\n".join(
            [*source_ids, *candidate_ids, *map(repr, sorted(source_coordinates))]
        )
        group_hash = hashlib.sha256(group_payload.encode("utf-8")).hexdigest()
        group_id = f"fact-equivalence:{group_hash[:16]}"
        candidate_bindings = [
            EquivalentCandidateClaimV1(
                claim_id=claim_id.removeprefix("candidate:"),
                candidate_byte_start=records[claim_id].source_byte_start,
                candidate_byte_end=records[claim_id].source_byte_end,
                content_sha256=records[claim_id].content_sha256,
                fact_coordinates=records[claim_id].accepted_fact_coordinates,
            )
            for claim_id in candidate_ids
        ]
        raw_source_ids = [claim_id.removeprefix("source:") for claim_id in source_ids]
        for claim_id in source_ids:
            result[claim_id.removeprefix("source:")] = (
                group_id,
                raw_source_ids,
                candidate_bindings,
            )
    return result


def build_readme_claim_accountability_map(
    *,
    org_repo: str,
    source_text: str,
    candidate_text: str,
    facts: ProductFactsV2,
    generated_claim_map: ReadmeClaimMapV1,
    candidate_content_provenance: list[CandidateContentProvenanceV1] | None = None,
    source_claim_resolutions: list[SourceClaimResolutionV1] | None = None,
) -> ReadmeClaimAccountabilityMapV1:
    """Return one explicit expected disposition for every material claim."""

    source_claims = assess_material_claims(source_text)
    candidate_claims = assess_material_claims(candidate_text)
    source_bytes = source_text.encode("utf-8")
    raw_candidate_occurrences = Counter(
        {
            claim.content_sha256: candidate_text.count(
                source_bytes[claim.source_byte_start : claim.source_byte_end].decode("utf-8")
            )
            for claim in source_claims
        }
    )
    remaining_inherited = Counter(claim.content_sha256 for claim in source_claims)
    candidate_origins: dict[str, ClaimOrigin] = {}
    for claim in candidate_claims:
        if remaining_inherited[claim.content_sha256] > 0:
            candidate_origins[claim.claim_id] = "inherited"
            remaining_inherited[claim.content_sha256] -= 1
        else:
            candidate_origins[claim.claim_id] = "generated"
    candidate_hashes = Counter(claim.content_sha256 for claim in candidate_claims)
    provenance = candidate_content_provenance or []
    resolutions = _validated_source_resolutions(source_claims, source_claim_resolutions or [])
    candidate_records = []
    for claim in candidate_claims:
        text = claim_text(candidate_text, claim)
        bindings = candidate_provenance_for_claim(claim, candidate_text, provenance)
        provenance_fact_ids = sorted(
            {fact_id for binding in bindings for fact_id in binding.fact_ids}
        )
        fact_ids = (
            accepted_literal_facts(text, facts)
            | overlapping_candidate_fact_ids(claim, candidate_text, generated_claim_map)
            | set(literal_fact_ids(text, facts, provenance_fact_ids))
        )
        fact_coordinates = structured_fact_coordinates(
            candidate_text,
            claim,
            facts,
            fact_ids,
        )
        fact_ids.update(coordinate.fact_id for coordinate in fact_coordinates)
        candidate_standard_ids = {
            standard_id for binding in bindings for standard_id in binding.configured_standard_ids
        }
        origin = candidate_origins[claim.claim_id]
        expected, accountable, rationale = expected_disposition(
            stage="candidate",
            origin=origin,
            current=claim.disposition,
            accepted_fact_ids=fact_ids,
            configured_standard_ids=candidate_standard_ids,
            survives_in_candidate=None,
            variable_fact_binding_required=bool(provenance_fact_ids),
        )
        candidate_records.append(
            accountability_record(
                claim,
                facts,
                stage="candidate",
                origin=origin,
                fact_ids=fact_ids,
                fact_coordinates=fact_coordinates,
                configured_standard_ids=candidate_standard_ids,
                survives=None,
                expected=expected,
                accountable=accountable,
                rationale=rationale,
            )
        )
    source_records = []
    for claim in source_claims:
        text = claim_text(source_text, claim)
        fact_ids = accepted_literal_facts(text, facts)
        source_standard_ids: set[str] = set()
        if source_text == candidate_text:
            exact_bindings = candidate_provenance_for_claim(claim, candidate_text, provenance)
            provenance_fact_ids = sorted(
                {fact_id for binding in exact_bindings for fact_id in binding.fact_ids}
            )
            fact_ids.update(literal_fact_ids(text, facts, provenance_fact_ids))
            source_standard_ids.update(
                standard_id
                for binding in exact_bindings
                for standard_id in binding.configured_standard_ids
            )
        resolution = resolutions.get(claim.claim_id)
        if resolution is not None:
            if (
                resolution.source_byte_start != claim.source_byte_start
                or resolution.source_byte_end != claim.source_byte_end
                or resolution.content_sha256 != claim.content_sha256
            ):
                raise ValueError(f"source claim resolution is stale: {claim.claim_id}")
            for fact_id in resolution.fact_ids:
                fact = facts.fact_by_id(fact_id)
                if (
                    facts.selected_fact_ids.get(fact.field) != fact_id
                    or fact.verification_state not in {"verified", "policy_approved"}
                    or fact.has_unresolved_conflict
                ):
                    raise ValueError(f"source claim resolution cites ineligible fact {fact_id!r}")
                fact_ids.add(fact_id)
        fact_coordinates = structured_fact_coordinates(source_text, claim, facts)
        fact_ids.update(coordinate.fact_id for coordinate in fact_coordinates)
        survives = raw_candidate_occurrences[claim.content_sha256] > 0
        if survives:
            raw_candidate_occurrences[claim.content_sha256] -= 1
            if candidate_hashes[claim.content_sha256] > 0:
                candidate_hashes[claim.content_sha256] -= 1
        expected, accountable, rationale = expected_disposition(
            stage="source",
            origin="inherited",
            current=claim.disposition,
            accepted_fact_ids=fact_ids,
            configured_standard_ids=source_standard_ids,
            survives_in_candidate=survives,
            source_resolution=resolution,
        )
        source_records.append(
            accountability_record(
                claim,
                facts,
                stage="source",
                origin="inherited",
                fact_ids=fact_ids,
                fact_coordinates=fact_coordinates,
                configured_standard_ids=source_standard_ids,
                survives=survives,
                expected=expected,
                accountable=accountable,
                rationale=rationale,
            )
        )
    equivalence_groups = _structured_equivalence_groups(
        source_records,
        candidate_records,
        excluded_source_claim_ids=set(resolutions),
    )
    reconciled_sources = []
    for record in source_records:
        claim_id = record.claim_id.removeprefix("source:")
        equivalence = equivalence_groups.get(claim_id)
        if equivalence is None:
            reconciled_sources.append(record)
            continue
        group_id, source_claim_ids, candidate_bindings = equivalence
        reconciled_sources.append(
            record.model_copy(
                update={
                    "expected_disposition": "verified_equivalence",
                    "currently_accountable": True,
                    "rationale": (
                        "The exact source claim belongs to a complete structured-fact coordinate "
                        "group represented by exact independently accountable candidate claims."
                    ),
                    "equivalence_group_id": group_id,
                    "equivalent_source_claim_ids": source_claim_ids,
                    "equivalent_candidate_claims": candidate_bindings,
                    "equivalence_normalization_version": "structured-fact-coordinate-v1",
                }
            )
        )
    return ReadmeClaimAccountabilityMapV1(
        org_repo=org_repo,
        facts_hash=facts.canonical_hash(),
        source_sha256=hashlib.sha256(source_text.encode("utf-8")).hexdigest(),
        candidate_sha256=hashlib.sha256(candidate_text.encode("utf-8")).hexdigest(),
        claims=[*reconciled_sources, *candidate_records],
    )
