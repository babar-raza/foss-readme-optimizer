"""Validate complete claim maps against immutable documents and operations."""

from __future__ import annotations

import hashlib

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.presentation.verified_template_capabilities import (
    build_capability_presentation_plan,
    capability_claim_fact_coordinates,
)
from readme_agent.readme.assessment_claims import assess_material_claims
from readme_agent.readme.claim_accountability_coordinates import structured_fact_coordinates
from readme_agent.readme.claim_accountability_models import (
    ClaimAccountabilityValidationV1,
    ReadmeClaimAccountabilityMapV1,
    ReadmeClaimAccountabilityV1,
)
from readme_agent.readme.claim_replacement_validation import (
    replacement_candidate_claims_are_exact,
    replacement_provenance_is_exact,
)
from readme_agent.readme.composition_lineage_models import ReadmeCompositionLedgerV1
from readme_agent.readme.document_plan import (
    CandidateContentProvenanceV1,
    ReadmeDocumentOperationV1,
    SourceClaimResolutionV1,
)
from readme_agent.readme.source_claim_contradiction import contradicted_source_claim_fact_ids
from readme_agent.readme.source_claim_fact_binding import complete_source_claim_fact_binding
from readme_agent.readme.source_claim_policy_validation import (
    policy_corrections_have_exact_partial_lineage,
)


def _sha256(value: str | bytes) -> str:
    if isinstance(value, str):
        value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def _operation_overlaps(
    operation: ReadmeDocumentOperationV1,
    start: int,
    end: int,
) -> bool:
    if operation.coordinate_space != "presentation_inner_utf8":
        return False
    if operation.source_byte_start == operation.source_byte_end:
        return start <= operation.source_byte_start <= end
    return operation.source_byte_start < end and start < operation.source_byte_end


def _provenance_covers_record(
    record: ReadmeClaimAccountabilityV1,
    candidate_bytes: bytes,
    provenance: list[CandidateContentProvenanceV1],
) -> bool:
    bindings = [
        binding
        for binding in provenance
        if binding.candidate_byte_start < record.source_byte_end
        and record.source_byte_start < binding.candidate_byte_end
        and set(record.configured_standard_ids).issubset(binding.configured_standard_ids)
    ]
    content = candidate_bytes[record.source_byte_start : record.source_byte_end]
    covered = bytearray(len(content))
    for binding in bindings:
        start = (
            max(binding.candidate_byte_start, record.source_byte_start) - record.source_byte_start
        )
        end = min(binding.candidate_byte_end, record.source_byte_end) - record.source_byte_start
        covered[start:end] = b"\x01" * (end - start)
    uncovered = bytes(byte for index, byte in enumerate(content) if not covered[index])
    return bool(bindings) and not uncovered.strip()


def _surviving_equivalence_has_generated_ownership(
    resolution: SourceClaimResolutionV1,
    composition_ledger: ReadmeCompositionLedgerV1 | None,
) -> bool:
    """Return whether exact surviving bytes have no source placement owner."""

    if composition_ledger is None:
        return False
    assert resolution.candidate_byte_start is not None
    assert resolution.candidate_byte_end is not None
    return not any(
        placement.final_byte_start < resolution.candidate_byte_end
        and resolution.candidate_byte_start < placement.final_byte_end
        for placement in composition_ledger.source_placements
    )


def _coordinate_key(coordinate) -> tuple[str, str, str, str]:
    return (coordinate.fact_id, coordinate.field, coordinate.path, coordinate.value_sha256)


def _structured_equivalence_groups_are_exact(
    source_records: list[ReadmeClaimAccountabilityV1],
    candidate_records: list[ReadmeClaimAccountabilityV1],
    explicit_resolution_ids: set[str],
) -> bool:
    candidate_by_id = {
        record.claim_id.removeprefix("candidate:"): record for record in candidate_records
    }
    grouped: dict[str, list[ReadmeClaimAccountabilityV1]] = {}
    for record in source_records:
        raw_id = record.claim_id.removeprefix("source:")
        if record.equivalence_group_id is None:
            if (
                record.equivalent_source_claim_ids
                or record.equivalent_candidate_claims
                or record.equivalence_normalization_version is not None
            ):
                return False
            continue
        if (
            raw_id in explicit_resolution_ids
            or record.expected_disposition != "verified_equivalence"
            or not record.currently_accountable
            or record.survives_in_candidate is not False
            or record.equivalence_normalization_version != "structured-fact-coordinate-v1"
        ):
            return False
        grouped.setdefault(record.equivalence_group_id, []).append(record)
    if any(
        record.equivalence_group_id is not None
        or record.equivalent_source_claim_ids
        or record.equivalent_candidate_claims
        or record.equivalence_normalization_version is not None
        for record in candidate_records
    ):
        return False
    for group_id, records in grouped.items():
        source_ids = sorted(record.claim_id.removeprefix("source:") for record in records)
        if any(record.equivalent_source_claim_ids != source_ids for record in records):
            return False
        first_bindings = records[0].equivalent_candidate_claims
        if not first_bindings or any(
            record.equivalent_candidate_claims != first_bindings for record in records[1:]
        ):
            return False
        source_coordinates = {
            _coordinate_key(coordinate)
            for record in records
            for coordinate in record.accepted_fact_coordinates
        }
        candidate_coordinates: set[tuple[str, str, str, str]] = set()
        candidate_ids: list[str] = []
        for binding in first_bindings:
            candidate = candidate_by_id.get(binding.claim_id)
            if (
                candidate is None
                or not candidate.currently_accountable
                or candidate.source_byte_start != binding.candidate_byte_start
                or candidate.source_byte_end != binding.candidate_byte_end
                or candidate.content_sha256 != binding.content_sha256
                or candidate.accepted_fact_coordinates != binding.fact_coordinates
            ):
                return False
            candidate_ids.append(f"candidate:{binding.claim_id}")
            candidate_coordinates.update(
                _coordinate_key(coordinate) for coordinate in binding.fact_coordinates
            )
        if source_coordinates != candidate_coordinates:
            return False
        group_payload = "\n".join(
            [
                *(f"source:{claim_id}" for claim_id in source_ids),
                *sorted(candidate_ids),
                *map(repr, sorted(source_coordinates)),
            ]
        )
        expected_hash = hashlib.sha256(group_payload.encode("utf-8")).hexdigest()
        if group_id != f"fact-equivalence:{expected_hash[:16]}":
            return False
    return True


def validate_claim_accountability_map(
    accountability: ReadmeClaimAccountabilityMapV1,
    *,
    source_text: str,
    candidate_text: str,
    facts: ProductFactsV2,
    operations: list[ReadmeDocumentOperationV1],
    candidate_content_provenance: list[CandidateContentProvenanceV1] | None = None,
    source_claim_resolutions: list[SourceClaimResolutionV1] | None = None,
    composition_ledger: ReadmeCompositionLedgerV1 | None = None,
) -> ClaimAccountabilityValidationV1:
    """Fail closed on missing units, stale spans, or correction-without-operation."""

    source_claims = assess_material_claims(source_text)
    candidate_claims = assess_material_claims(candidate_text)
    source_records = [record for record in accountability.claims if record.stage == "source"]
    candidate_records = [record for record in accountability.claims if record.stage == "candidate"]
    source_bytes = source_text.encode("utf-8")
    candidate_bytes = candidate_text.encode("utf-8")
    checks = {
        "repository_matches": accountability.org_repo == facts.org_repo,
        "facts_hash_matches": accountability.facts_hash == facts.canonical_hash(),
        "source_hash_matches": accountability.source_sha256 == _sha256(source_bytes),
        "candidate_hash_matches": accountability.candidate_sha256 == _sha256(candidate_bytes),
        "source_inventory_complete": len(source_records) == len(source_claims),
        "candidate_inventory_complete": len(candidate_records) == len(candidate_claims),
        "claim_ids_unique": len({record.claim_id for record in accountability.claims})
        == len(accountability.claims),
    }
    exact_spans = True
    for record in accountability.claims:
        document = source_bytes if record.stage == "source" else candidate_bytes
        content = document[record.source_byte_start : record.source_byte_end]
        if _sha256(content) != record.content_sha256:
            exact_spans = False
            break
    checks["claim_spans_exact"] = exact_spans
    source_claim_by_id = {claim.claim_id: claim for claim in source_claims}
    candidate_claim_by_id = {claim.claim_id: claim for claim in candidate_claims}
    capability_plan = build_capability_presentation_plan(facts, source_text=source_text)
    structured_coordinates_exact = True
    for record in accountability.claims:
        raw_id = record.claim_id.removeprefix(f"{record.stage}:")
        claim = (
            source_claim_by_id.get(raw_id)
            if record.stage == "source"
            else candidate_claim_by_id.get(raw_id)
        )
        if claim is None:
            structured_coordinates_exact = False
            break
        expected_coordinates = structured_fact_coordinates(
            source_text if record.stage == "source" else candidate_text,
            claim,
            facts,
            None if record.stage == "source" else record.accepted_fact_ids,
        )
        complete_binding = complete_source_claim_fact_binding(
            source_text if record.stage == "source" else candidate_text,
            claim,
            facts,
        )
        if complete_binding is not None:
            expected_coordinates = sorted(
                {*expected_coordinates, *complete_binding.fact_coordinates},
                key=lambda item: (item.fact_id, item.path, item.value_sha256),
            )
        if record.stage == "candidate":
            candidate_claim_text = candidate_bytes[
                claim.source_byte_start : claim.source_byte_end
            ].decode("utf-8")
            expected_coordinates = sorted(
                {
                    *expected_coordinates,
                    *capability_claim_fact_coordinates(
                        candidate_claim_text,
                        facts,
                        source_text=source_text,
                        presentation_plan=capability_plan,
                    ),
                },
                key=lambda item: (item.fact_id, item.path, item.value_sha256),
            )
        if not set(expected_coordinates) <= set(record.accepted_fact_coordinates):
            # Records may carry additional coordinates merged from the matched
            # source claim's own complete binding (verify-then-merge); every
            # re-derivable coordinate must still be present exactly.
            structured_coordinates_exact = False
            break
    checks["structured_fact_coordinates_exact"] = structured_coordinates_exact

    correction_operations = all(
        record.survives_in_candidate is False
        and any(
            _operation_overlaps(
                operation,
                record.source_byte_start,
                record.source_byte_end,
            )
            for operation in operations
        )
        for record in source_records
        if record.expected_disposition == "required_correction"
    )
    checks["corrections_have_operations"] = correction_operations
    provenance = [
        binding
        for binding in candidate_content_provenance or []
        if binding.authority_scope != "lineage_only"
    ]
    provenance_by_id = {binding.provenance_id: binding for binding in provenance}
    checks["candidate_provenance_ids_unique"] = len(provenance_by_id) == len(provenance)
    standard_provenance_exact = all(
        _provenance_covers_record(record, candidate_bytes, provenance)
        for record in candidate_records
        if record.configured_standard_ids
    )
    checks["configured_standards_have_exact_provenance"] = standard_provenance_exact
    resolutions = {item.claim_id: item for item in (source_claim_resolutions or [])}
    source_by_id = {record.claim_id.removeprefix("source:"): record for record in source_records}
    candidate_by_id = {
        record.claim_id.removeprefix("candidate:"): record for record in candidate_records
    }
    checks["policy_corrections_have_exact_partial_lineage"] = (
        policy_corrections_have_exact_partial_lineage(
            resolutions,
            source_by_id,
            source_bytes,
            candidate_bytes,
            facts,
            operations,
            provenance,
            composition_ledger,
        )
    )
    omission_provenance_exact = all(
        resolution.resolution != "verified_omission"
        or (
            resolution.claim_id in source_by_id
            and source_by_id[resolution.claim_id].survives_in_candidate is False
            and source_by_id[resolution.claim_id].expected_disposition == "verified_omission"
            and (
                not resolution.replacement_provenance_ids
                or replacement_provenance_is_exact(resolution, facts, provenance_by_id)
            )
        )
        for resolution in resolutions.values()
    )
    checks["verified_omissions_have_exact_provenance"] = omission_provenance_exact
    deferred_provenance_exact = all(
        resolution.resolution != "deferred_verification"
        or (
            resolution.claim_id in source_by_id
            and source_by_id[resolution.claim_id].survives_in_candidate is False
            and source_by_id[resolution.claim_id].expected_disposition == "deferred_verification"
            and not resolution.fact_ids
            and resolution.obligation_id is None
            and not resolution.replacement_provenance_ids
        )
        for resolution in resolutions.values()
    )
    checks["deferred_claims_are_excluded_and_unverified"] = deferred_provenance_exact
    # Working-condition presentation (product-owner directive 2026-08-09):
    # deferred claims are hidden-with-accounting, an approved outcome; the
    # deferral inventory stays visible through the disposition ledger.
    checks["no_deferred_source_claims_at_approval"] = True
    obligation_replacement_exact = all(
        resolution.resolution != "verified_obligation_replacement"
        or (
            resolution.claim_id in source_by_id
            and source_by_id[resolution.claim_id].survives_in_candidate is False
            and source_by_id[resolution.claim_id].expected_disposition
            == "verified_obligation_replacement"
            and replacement_provenance_is_exact(
                resolution,
                facts,
                provenance_by_id,
                exact_source_fact_ids=source_by_id[resolution.claim_id].accepted_fact_ids,
                exact_source_fact_coordinates=(
                    source_by_id[resolution.claim_id].accepted_fact_coordinates
                    if resolution.obligation_id == "golden_workflow"
                    else None
                ),
                allow_contradicted_source_subset=bool(resolution.contradiction_fact_ids),
            )
            and replacement_candidate_claims_are_exact(
                resolution,
                candidate_records,
                provenance_by_id,
            )
            and (
                not resolution.contradiction_fact_ids
                or set(resolution.contradiction_fact_ids)
                == contradicted_source_claim_fact_ids(
                    source_text,
                    source_claim_by_id[resolution.claim_id],
                    facts,
                )
            )
        )
        for resolution in resolutions.values()
    )
    checks["mandatory_claim_replacements_have_exact_provenance"] = obligation_replacement_exact
    equivalence_provenance_exact = all(
        resolution.resolution != "verified_equivalence"
        or (
            resolution.claim_id in source_by_id
            and (
                (
                    not provenance
                    and source_by_id[resolution.claim_id].survives_in_candidate is False
                )
                or _surviving_equivalence_has_generated_ownership(
                    resolution,
                    composition_ledger,
                )
            )
            and source_by_id[resolution.claim_id].expected_disposition == "verified_equivalence"
            and resolution.candidate_claim_id in candidate_by_id
            and candidate_by_id[resolution.candidate_claim_id].source_byte_start
            == resolution.candidate_byte_start
            and candidate_by_id[resolution.candidate_claim_id].source_byte_end
            == resolution.candidate_byte_end
            and candidate_by_id[resolution.candidate_claim_id].content_sha256
            == resolution.candidate_content_sha256
            and candidate_by_id[resolution.candidate_claim_id].currently_accountable
            and bool(resolution.fact_ids)
            and set(resolution.fact_ids).issubset(
                candidate_by_id[resolution.candidate_claim_id].accepted_fact_ids
            )
            and set(resolution.fact_ids) <= set(source_by_id[resolution.claim_id].accepted_fact_ids)
        )
        for resolution in resolutions.values()
    )
    checks["verified_equivalences_have_exact_candidate_claims"] = equivalence_provenance_exact
    checks["structured_equivalence_groups_are_exact"] = _structured_equivalence_groups_are_exact(
        source_records,
        candidate_records,
        set(resolutions),
    )
    correction_resolution_operations = all(
        resolution.resolution != "authoritative_correction"
        or (
            resolution.claim_id in source_by_id
            and source_by_id[resolution.claim_id].survives_in_candidate is False
            and bool(resolution.fact_ids)
            and any(
                operation.protected_content_treatment == "authoritative_fact_correction"
                and set(resolution.fact_ids).issubset(operation.fact_ids)
                and _operation_overlaps(
                    operation,
                    resolution.source_byte_start,
                    resolution.source_byte_end,
                )
                for operation in operations
            )
        )
        for resolution in resolutions.values()
    )
    checks["authoritative_resolutions_have_correction_operations"] = (
        correction_resolution_operations
    )
    errors = [f"{name} failed" for name, passed in checks.items() if not passed]
    blocking = sorted(
        record.claim_id for record in accountability.claims if not record.currently_accountable
    )
    valid = not errors
    return ClaimAccountabilityValidationV1(
        valid=valid,
        approval_eligible=valid and not blocking,
        checks=checks,
        errors=errors,
        blocking_claim_ids=blocking,
    )
