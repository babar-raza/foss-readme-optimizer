"""Bounded UTF-8 source edits rendered and checked by native Git."""

from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path, PurePosixPath

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from readme_agent.errors import ValidationFailure
from readme_agent.gitsafety._git import run_git


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class SourceSpanEditV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str
    byte_start: int = Field(ge=0)
    byte_end: int = Field(ge=0)
    expected_sha256: str
    replacement: str
    purpose: str = Field(min_length=1)

    @field_validator("path")
    @classmethod
    def _safe_relative_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if not value or "\\" in value or path.is_absolute() or ".." in path.parts:
            raise ValueError("source-span path must be a safe repository-relative POSIX path")
        return value

    @model_validator(mode="after")
    def _ordered(self) -> SourceSpanEditV1:
        if self.byte_end < self.byte_start:
            raise ValueError("source span byte_end must be >= byte_start")
        return self


class BoundedSourcePatchV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str
    source_sha256: str
    edits: list[SourceSpanEditV1] = Field(min_length=1)

    @field_validator("path")
    @classmethod
    def _safe_relative_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if not value or "\\" in value or path.is_absolute() or ".." in path.parts:
            raise ValueError("patch path must be a safe repository-relative POSIX path")
        return value


class GitPatchProofV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str
    source_sha256: str
    candidate_sha256: str
    patch_sha256: str
    patch: str
    git_apply_check_passed: bool
    outside_spans_preserved: bool


def apply_bounded_source_patch(source: str, patch: BoundedSourcePatchV1) -> str:
    source_bytes = source.encode("utf-8")
    if hashlib.sha256(source_bytes).hexdigest() != patch.source_sha256:
        raise ValidationFailure("source changed after planning; refusing stale source-span patch")
    ordered = sorted(patch.edits, key=lambda edit: (edit.byte_start, edit.byte_end))
    previous_end = -1
    previous_start = -1
    for edit in ordered:
        if edit.path != patch.path:
            raise ValidationFailure("source-span edit path does not match patch path")
        if edit.byte_end > len(source_bytes):
            raise ValidationFailure("source-span edit exceeds source byte length")
        if edit.byte_start < previous_end or edit.byte_start == previous_start:
            raise ValidationFailure("source-span edits overlap or share an insertion point")
        current = source_bytes[edit.byte_start : edit.byte_end]
        if hashlib.sha256(current).hexdigest() != edit.expected_sha256:
            raise ValidationFailure("source-span expected hash does not match current bytes")
        previous_start = edit.byte_start
        previous_end = edit.byte_end

    candidate = source_bytes
    for edit in reversed(ordered):
        replacement = edit.replacement.encode("utf-8")
        candidate = candidate[: edit.byte_start] + replacement + candidate[edit.byte_end :]
    try:
        return candidate.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValidationFailure("source-span patch produced invalid UTF-8") from exc


def create_git_patch_proof(
    source: str, candidate: str, bounded_patch: BoundedSourcePatchV1
) -> GitPatchProofV1:
    """Generate a real Git patch and prove `git apply --check` accepts it."""

    reconstructed = apply_bounded_source_patch(source, bounded_patch)
    if reconstructed != candidate:
        raise ValidationFailure("bounded source edits do not reconstruct the candidate")
    with tempfile.TemporaryDirectory(prefix="readme-agent-patch-") as temporary:
        repo = Path(temporary)
        target = repo / bounded_patch.path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source, encoding="utf-8", newline="")
        for args in (
            ["init", "--quiet"],
            ["add", "--", bounded_patch.path],
            [
                "-c",
                "user.name=readme-agent",
                "-c",
                "user.email=readme-agent@invalid",
                "commit",
                "--quiet",
                "-m",
                "patch base",
            ],
        ):
            result = run_git(args, cwd=repo)
            if result.returncode != 0:
                raise ValidationFailure(f"Git patch setup failed: {result.stderr.strip()}")
        target.write_text(candidate, encoding="utf-8", newline="")
        diff = run_git(["diff", "--binary", "--", bounded_patch.path], cwd=repo)
        if diff.returncode != 0 or not diff.stdout:
            raise ValidationFailure(f"Git did not produce a candidate patch: {diff.stderr.strip()}")
        target.write_text(source, encoding="utf-8", newline="")
        check = run_git(["apply", "--check", "-"], cwd=repo, input_text=diff.stdout)
        if check.returncode != 0:
            raise ValidationFailure(f"git apply --check rejected candidate: {check.stderr.strip()}")
    return GitPatchProofV1(
        path=bounded_patch.path,
        source_sha256=sha256_text(source),
        candidate_sha256=sha256_text(candidate),
        patch_sha256=sha256_text(diff.stdout),
        patch=diff.stdout,
        git_apply_check_passed=True,
        outside_spans_preserved=True,
    )
