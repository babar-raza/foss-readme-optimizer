"""`_structured_equivalence_groups_are_exact` must accept exactly what
`build_readme_claim_accountability_map`'s authoring pass produces.

PWD-008, live on aspose-words-foss/Aspose.Words-FOSS-for-Python: a real, valid equivalence
group -- one source claim naming 1 fact coordinate, matched to 3 candidate claims whose
combined coordinates total 5 -- failed `structured_equivalence_groups_are_exact` even
though every individual field matched exactly. Root-caused by direct measurement (not
inference): recomputing the group hash using the validator's own formula against the real
recorded data never matched the real, recorded `group_id`, but recomputing it using the
*authoring* function's formula (`claim_accountability.py`) matched exactly. Two
independent bugs in the validator, both stricter than what authoring actually guarantees:

1. `source_coordinates != candidate_coordinates` demanded exact equality, but authoring's
   own acceptance test is `source_coordinates.issubset(candidate_coordinates)` -- its own
   comment documents this as the normal, expected case ("a canonical candidate claim may
   add other independently accountable facts"), not a corner one.
2. The recomputed hash payload omitted `candidate_coordinates` entirely, while authoring's
   payload always includes it as a fourth component.

Both fixed to mirror the authoring formula exactly, since the validator's whole job is to
confirm authoring was done correctly -- it cannot use a different formula than the one
that produced the data.
"""

from __future__ import annotations

import hashlib

from readme_agent.readme.claim_accountability_models import (
    EquivalentCandidateClaimV1,
    ReadmeClaimAccountabilityV1,
    StructuredFactCoordinateV1,
)
from readme_agent.readme.claim_accountability_validation import (
    _structured_equivalence_groups_are_exact,
)


def _coordinate(path: str) -> StructuredFactCoordinateV1:
    return StructuredFactCoordinateV1(
        fact_id="repository.implementation_components:python-implementation-components",
        field="repository.implementation_components",
        path=path,
        value_sha256=hashlib.sha256(path.encode("utf-8")).hexdigest(),
    )


def _group_id(
    source_ids: list[str],
    candidate_ids: list[str],
    source_coordinates: set[tuple[str, str, str, str]],
    candidate_coordinates: set[tuple[str, str, str, str]],
) -> str:
    """The exact formula `build_readme_claim_accountability_map` uses -- the ground truth
    the validator must reproduce, not a hand-picked test value."""

    payload = "\n".join(
        [
            *sorted(source_ids),
            *sorted(candidate_ids),
            *map(repr, sorted(source_coordinates)),
            *map(repr, sorted(candidate_coordinates)),
        ]
    )
    return f"fact-equivalence:{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:16]}"


def _coordinate_key(coordinate: StructuredFactCoordinateV1) -> tuple[str, str, str, str]:
    return (coordinate.fact_id, coordinate.field, coordinate.path, coordinate.value_sha256)


def _build_group(
    *,
    source_coordinate_paths: list[str],
    candidate_coordinate_paths_by_claim: dict[str, list[str]],
) -> tuple[list[ReadmeClaimAccountabilityV1], list[ReadmeClaimAccountabilityV1]]:
    source_coordinates = [_coordinate(path) for path in source_coordinate_paths]
    candidate_bindings = []
    candidate_records = []
    for claim_suffix, paths in candidate_coordinate_paths_by_claim.items():
        coordinates = [_coordinate(path) for path in paths]
        content_sha = hashlib.sha256(claim_suffix.encode("utf-8")).hexdigest()
        candidate_bindings.append(
            EquivalentCandidateClaimV1(
                claim_id=claim_suffix,
                candidate_byte_start=100,
                candidate_byte_end=200,
                content_sha256=content_sha,
                fact_coordinates=coordinates,
            )
        )
        candidate_records.append(
            ReadmeClaimAccountabilityV1(
                claim_id=f"candidate:{claim_suffix}",
                stage="candidate",
                origin="generated",
                source_byte_start=100,
                source_byte_end=200,
                content_sha256=content_sha,
                current_disposition="preserve",
                accepted_fact_coordinates=coordinates,
                currently_accountable=True,
                expected_disposition="accepted_fact",
                rationale="test fixture",
            )
        )

    source_ids = ["claim:source-1"]
    candidate_ids = [f"candidate:{binding.claim_id}" for binding in candidate_bindings]
    all_source_coordinates = {_coordinate_key(c) for c in source_coordinates}
    all_candidate_coordinates = {
        _coordinate_key(c) for binding in candidate_bindings for c in binding.fact_coordinates
    }
    group_id = _group_id(
        [f"source:{claim_id}" for claim_id in source_ids],
        candidate_ids,
        all_source_coordinates,
        all_candidate_coordinates,
    )
    source_record = ReadmeClaimAccountabilityV1(
        claim_id="source:claim:source-1",
        stage="source",
        origin="inherited",
        source_byte_start=0,
        source_byte_end=50,
        content_sha256=hashlib.sha256(b"source-1").hexdigest(),
        current_disposition="preserve",
        accepted_fact_coordinates=source_coordinates,
        equivalence_group_id=group_id,
        equivalent_source_claim_ids=source_ids,
        equivalent_candidate_claims=candidate_bindings,
        equivalence_normalization_version="structured-fact-coordinate-v1",
        survives_in_candidate=False,
        expected_disposition="verified_equivalence",
        currently_accountable=True,
        rationale="test fixture",
    )
    return [source_record], candidate_records


def test_candidate_superset_of_source_coordinates_is_accepted():
    """The real live shape: 1 source coordinate, 3 candidate claims whose combined
    coordinates total 5 (a proper superset) -- authoring's own documented, expected case."""

    source_records, candidate_records = _build_group(
        source_coordinate_paths=["/capability_groups/a"],
        candidate_coordinate_paths_by_claim={
            "claim:cand-1": ["/capability_groups/a"],
            "claim:cand-2": [
                "/capability_groups/a",
                "/capability_groups/b",
                "/capability_groups/c",
                "/capability_groups/d",
            ],
            "claim:cand-3": ["/capability_groups/a"],
        },
    )

    assert _structured_equivalence_groups_are_exact(source_records, candidate_records, set())


def test_exact_matching_coordinates_are_still_accepted():
    """The simpler case (source coordinates == candidate coordinates exactly) must remain
    accepted -- the fix widens acceptance, it must never narrow it."""

    source_records, candidate_records = _build_group(
        source_coordinate_paths=["/capability_groups/a"],
        candidate_coordinate_paths_by_claim={"claim:cand-1": ["/capability_groups/a"]},
    )

    assert _structured_equivalence_groups_are_exact(source_records, candidate_records, set())


def test_candidate_missing_a_source_coordinate_is_still_rejected():
    """Negative control: if the candidate side does NOT cover every source coordinate
    (not a superset), the group must still be rejected -- the fix only relaxes exact
    equality to subset, never drops the coverage requirement entirely."""

    source_records, candidate_records = _build_group(
        source_coordinate_paths=["/capability_groups/a", "/capability_groups/z"],
        candidate_coordinate_paths_by_claim={"claim:cand-1": ["/capability_groups/a"]},
    )

    assert not _structured_equivalence_groups_are_exact(source_records, candidate_records, set())


def test_tampered_group_id_is_still_rejected():
    """Negative control: a group_id that doesn't match the recomputed hash at all
    (neither formula) must still be rejected -- the hash check itself still functions."""

    source_records, candidate_records = _build_group(
        source_coordinate_paths=["/capability_groups/a"],
        candidate_coordinate_paths_by_claim={"claim:cand-1": ["/capability_groups/a"]},
    )
    tampered = source_records[0].model_copy(
        update={"equivalence_group_id": "fact-equivalence:0000000000000000"}
    )

    assert not _structured_equivalence_groups_are_exact([tampered], candidate_records, set())
