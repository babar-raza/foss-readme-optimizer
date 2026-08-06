"""Prove exact claim-scoped source-policy resolution."""

from __future__ import annotations

import hashlib

import pytest

from readme_agent.presentation.verified_source_policy_resolution import source_policy_resolution
from readme_agent.readme.assessment_claims import ReadmeMaterialClaimAssessmentV1
from readme_agent.readme.source_claim_policy import SourceClaimPolicyCorrectionV1


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _claim(source: bytes, start: int, end: int) -> ReadmeMaterialClaimAssessmentV1:
    return ReadmeMaterialClaimAssessmentV1(
        claim_id=f"claim:{start}:test",
        source_byte_start=start,
        source_byte_end=end,
        content_sha256=_sha256(source[start:end]),
        disposition="preserve",
        evidence=[f"README.md:{start}:{end}"],
        rationale="Test material claim.",
    )


def _correction(
    source: bytes,
    candidate: bytes,
    start: int,
    end: int,
    *,
    disposition: str = "omit",
    candidate_start: int = 0,
    candidate_end: int = 0,
    standard_id: str = "readme.comment_free",
) -> SourceClaimPolicyCorrectionV1:
    return SourceClaimPolicyCorrectionV1(
        correction_id=f"source.policy.{start}-{end}",
        disposition=disposition,
        source_byte_start=start,
        source_byte_end=end,
        source_content_sha256=_sha256(source[start:end]),
        candidate_byte_start=candidate_start,
        candidate_byte_end=candidate_end,
        candidate_content_sha256=_sha256(candidate[candidate_start:candidate_end]),
        configured_standard_ids=[standard_id],
        replacement_provenance_id=(
            "source.policy.replacement" if candidate_end > candidate_start else None
        ),
        operation_id="readme.verified-template.compile",
    )


def test_broad_omit_is_clipped_to_the_exact_material_claim() -> None:
    source_buffer = bytearray(b"s" * 1134)
    source_buffer[950 : 950 + len(b"material navigation claim")] = b"material navigation claim"
    source = bytes(source_buffer)
    candidate = b""
    start = 950
    end = 1007
    claim = _claim(source, start, end)
    correction = _correction(source, candidate, 723, 1134)

    resolution = source_policy_resolution(
        claim,
        [correction],
        source_bytes=source,
        candidate_bytes=candidate,
    )

    assert resolution is not None
    assert len(resolution.policy_corrections) == 1
    clipped = resolution.policy_corrections[0]
    assert (clipped.source_byte_start, clipped.source_byte_end) == (start, end)
    assert clipped.source_content_sha256 == claim.content_sha256
    assert clipped.candidate_byte_start == clipped.candidate_byte_end == 0
    assert clipped.candidate_content_sha256 == _sha256(b"")
    assert clipped.operation_id == correction.operation_id
    assert clipped.configured_standard_ids == correction.configured_standard_ids
    assert clipped.correction_id.endswith(f".claim-{start}-{end}")


def test_claim_retains_exact_nonoverlapping_corrections_inside_its_span() -> None:
    source = b"before stale-link middle other-link after"
    candidate = b"replacement"
    claim = _claim(source, 0, len(source))
    first_start = source.index(b"stale-link")
    second_start = source.index(b"other-link")
    first = _correction(source, candidate, first_start, first_start + len(b"stale-link"))
    second = _correction(source, candidate, second_start, second_start + len(b"other-link"))

    resolution = source_policy_resolution(
        claim,
        [second, first],
        source_bytes=source,
        candidate_bytes=candidate,
    )

    assert resolution is not None
    assert resolution.policy_corrections == [first, second]


def test_partial_comment_omission_does_not_claim_the_unverified_example_remainder() -> None:
    source = b"```python\nvalue = 1\n# source-only explanation\nprint(value)\n```\n"
    candidate = b"```python\nvalue = 1\nprint(value)\n```\n"
    claim = _claim(source, 0, len(source))
    start = source.index(b"# source-only explanation")
    end = start + len(b"# source-only explanation\n")
    correction = _correction(
        source,
        candidate,
        start,
        end,
        standard_id="readme.no_comments",
    )

    resolution = source_policy_resolution(
        claim,
        [correction],
        source_bytes=source,
        candidate_bytes=candidate,
    )

    assert resolution is None


def test_whole_claim_comment_policy_omission_remains_exactly_resolvable() -> None:
    source = b"```python\n# comment-only example\n```\n"
    candidate = b""
    claim = _claim(source, 0, len(source))
    correction = _correction(
        source,
        candidate,
        0,
        len(source),
        standard_id="readme.no_comments",
    )

    resolution = source_policy_resolution(
        claim,
        [correction],
        source_bytes=source,
        candidate_bytes=candidate,
    )

    assert resolution is not None
    assert resolution.policy_corrections == [correction]


def test_broad_nonempty_replacement_cannot_be_clipped() -> None:
    source = b"shell before material claim shell after"
    candidate = b"Enterprise Edition"
    start = source.index(b"material")
    end = start + len(b"material claim")
    correction = _correction(
        source,
        candidate,
        0,
        len(source),
        disposition="replace",
        candidate_end=len(candidate),
    )

    with pytest.raises(ValueError, match="cannot clip a nonempty policy replacement"):
        source_policy_resolution(
            _claim(source, start, end),
            [correction],
            source_bytes=source,
            candidate_bytes=candidate,
        )


def test_partial_overlap_is_rejected_instead_of_fabricating_lineage() -> None:
    source = b"prefix material claim suffix"
    candidate = b""
    start = source.index(b"material")
    end = start + len(b"material claim")
    correction = _correction(source, candidate, 0, start + len(b"material"))

    with pytest.raises(ValueError, match="partially overlaps"):
        source_policy_resolution(
            _claim(source, start, end),
            [correction],
            source_bytes=source,
            candidate_bytes=candidate,
        )


@pytest.mark.parametrize("tampered_field", ["source_content_sha256", "candidate_content_sha256"])
def test_tampered_policy_hash_is_rejected(tampered_field: str) -> None:
    source = b"shell material claim shell"
    candidate = b""
    start = source.index(b"material")
    end = start + len(b"material claim")
    correction = _correction(source, candidate, 0, len(source)).model_copy(
        update={tampered_field: "0" * 64}
    )

    with pytest.raises(ValueError, match="hash does not match its exact span"):
        source_policy_resolution(
            _claim(source, start, end),
            [correction],
            source_bytes=source,
            candidate_bytes=candidate,
        )


def test_overlapping_policy_corrections_are_rejected() -> None:
    source = b"material claim with overlapping policy spans"
    candidate = b""
    claim = _claim(source, 0, len(source))
    first = _correction(source, candidate, 0, 20)
    second = _correction(source, candidate, 10, 30)

    with pytest.raises(ValueError, match="overlap within one material claim"):
        source_policy_resolution(
            claim,
            [first, second],
            source_bytes=source,
            candidate_bytes=candidate,
        )
