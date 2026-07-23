"""Bounded source-span and native Git patch checks."""

import hashlib

import pytest
from pydantic import ValidationError

from readme_agent.errors import ValidationFailure
from readme_agent.presentation.git_patch import (
    BoundedSourcePatchV1,
    SourceSpanEditV1,
    apply_bounded_source_patch,
    create_git_patch_proof,
    sha256_text,
)


def _edit(source: str, start: int, end: int, replacement: str) -> SourceSpanEditV1:
    source_bytes = source.encode()
    return SourceSpanEditV1(
        path="README.md",
        byte_start=start,
        byte_end=end,
        expected_sha256=hashlib.sha256(source_bytes[start:end]).hexdigest(),
        replacement=replacement,
        purpose="bounded test edit",
    )


def test_utf8_span_preserves_every_byte_outside_edit_and_git_accepts_patch():
    source = "# Café\n\nKeep α exactly.\n\nOld line.\n"
    source_bytes = source.encode()
    start = source_bytes.index(b"Old line.")
    edit = _edit(source, start, start + len(b"Old line."), "New line.")
    bounded = BoundedSourcePatchV1(
        path="README.md",
        source_sha256=sha256_text(source),
        edits=[edit],
    )

    candidate = apply_bounded_source_patch(source, bounded)
    proof = create_git_patch_proof(source, candidate, bounded)

    assert candidate == "# Café\n\nKeep α exactly.\n\nNew line.\n"
    assert proof.git_apply_check_passed is True
    assert proof.outside_spans_preserved is True
    assert "diff --git a/README.md b/README.md" in proof.patch


def test_stale_source_hash_fails_before_edit():
    source = "# Widget\n"
    bounded = BoundedSourcePatchV1(
        path="README.md",
        source_sha256="0" * 64,
        edits=[_edit(source, 0, 1, "##")],
    )

    with pytest.raises(ValidationFailure, match="source changed after planning"):
        apply_bounded_source_patch(source, bounded)


def test_overlapping_spans_fail_closed():
    source = "abcdef"
    bounded = BoundedSourcePatchV1(
        path="README.md",
        source_sha256=sha256_text(source),
        edits=[_edit(source, 1, 4, "x"), _edit(source, 3, 5, "y")],
    )

    with pytest.raises(ValidationFailure, match="overlap"):
        apply_bounded_source_patch(source, bounded)


def test_repository_relative_path_cannot_escape_temporary_git_workspace():
    with pytest.raises(ValidationError, match="safe repository-relative"):
        SourceSpanEditV1(
            path="../README.md",
            byte_start=0,
            byte_end=0,
            expected_sha256=hashlib.sha256(b"").hexdigest(),
            replacement="unsafe",
            purpose="must fail",
        )
