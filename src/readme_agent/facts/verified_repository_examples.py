"""Select one revision-bound repository example through the real verifier."""

from __future__ import annotations

import re
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from readme_agent.facts.example_quality import generated_example_quality_failures
from readme_agent.facts.example_value import assess_minimal_example_value
from readme_agent.facts.example_verification_schema import LocalProductVerificationV1
from readme_agent.facts.policy_evidence import evidence_failures
from readme_agent.facts.repository_examples import (
    repository_readme_example_candidates,
    repository_source_example_candidates,
)
from readme_agent.registry.models import MinimalExamplePolicy

_REVISION = re.compile(r"[0-9a-f]{40}")
MAX_VERIFIED_REPOSITORY_EXAMPLE_ATTEMPTS = 8
VerifyExampleFn = Callable[[MinimalExamplePolicy], LocalProductVerificationV1 | None]


class RepositoryExampleSelectionV2(BaseModel):
    """Typed terminal result from bounded repository-example selection."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[2] = 2
    outcome: Literal[
        "VERIFIED",
        "TERMINAL_PRODUCT_FAILURE",
        "NO_VERIFIED_CANDIDATE",
        "REVISION_MISMATCH",
    ]
    example: MinimalExamplePolicy | None = None
    verification: LocalProductVerificationV1 | None = None
    candidate_count: int = Field(ge=0)
    attempted_count: int = Field(ge=0)
    selected_rank: int | None = Field(default=None, ge=1)
    last_attempted_example: MinimalExamplePolicy | None = None
    last_attempted_verification: LocalProductVerificationV1 | None = None

    @model_validator(mode="after")
    def selected_outcomes_require_consistent_verification(self) -> RepositoryExampleSelectionV2:
        if self.attempted_count > self.candidate_count:
            raise ValueError("attempted_count cannot exceed candidate_count")
        selected = self.outcome in {"VERIFIED", "TERMINAL_PRODUCT_FAILURE"}
        selection_complete = (
            self.example is not None
            and self.verification is not None
            and self.selected_rank is not None
        )
        if selected and not selection_complete:
            raise ValueError("selected outcomes require example, verification, and selected_rank")
        if not selected and any(
            value is not None for value in (self.example, self.verification, self.selected_rank)
        ):
            raise ValueError("non-selected outcomes cannot carry a partial selection")
        retained_failure = (
            self.last_attempted_example is not None and self.last_attempted_verification is not None
        )
        if (self.last_attempted_example is None) != (self.last_attempted_verification is None):
            raise ValueError("retained failed example and verification must be paired")
        if retained_failure and self.outcome != "NO_VERIFIED_CANDIDATE":
            raise ValueError("only NO_VERIFIED_CANDIDATE may retain its last failed attempt")
        if self.selected_rank is not None and self.selected_rank > self.candidate_count:
            raise ValueError("selected_rank cannot exceed candidate_count")
        if self.outcome == "VERIFIED" and not (
            self.verification is not None
            and self.verification.outcome in {"SOURCE_BUILD_VERIFIED", "SOURCE_TREE_VERIFIED"}
            and self.verification.truth_eligible
            and self.verification.isolated_execution is not None
            and self.verification.isolated_execution.truth_eligible
            and self.verification.isolated_execution.return_code == 0
        ):
            raise ValueError("VERIFIED requires a truth-eligible isolated verification")
        if self.outcome == "TERMINAL_PRODUCT_FAILURE" and not _product_owned_install_failure(
            self.verification
        ):
            raise ValueError("TERMINAL_PRODUCT_FAILURE requires Python isolated return code 20/21")
        return self


def select_verified_repository_example(
    root: Path,
    *,
    source_revision: str | None,
    requested: MinimalExamplePolicy,
    verify_example_fn: VerifyExampleFn,
) -> RepositoryExampleSelectionV2:
    """Return the first verified candidate or terminal product-source failure."""

    repository_root = root.resolve()
    expected_revision = (
        source_revision
        if source_revision is not None and _REVISION.fullmatch(source_revision)
        else None
    )
    if expected_revision is not None and not _revision_matches(repository_root, expected_revision):
        return RepositoryExampleSelectionV2(
            outcome="REVISION_MISMATCH",
            candidate_count=0,
            attempted_count=0,
        )
    readme_examples = repository_readme_example_candidates(
        repository_root,
        requested.language,
        supporting_paths=requested.evidence_paths,
    )
    source_examples = repository_source_example_candidates(repository_root, requested.language)
    indexed = list(enumerate([*readme_examples, *source_examples]))
    indexed.sort(key=lambda item: _preference(item[1], requested, item[0]))
    attempted = 0
    last_attempted_example: MinimalExamplePolicy | None = None
    last_attempted_verification: LocalProductVerificationV1 | None = None
    for selected_rank, (_position, candidate) in enumerate(
        indexed[:MAX_VERIFIED_REPOSITORY_EXAMPLE_ATTEMPTS], start=1
    ):
        if _precheck_failures(repository_root, candidate):
            continue
        attempted += 1
        verification = verify_example_fn(candidate)
        if verification is not None:
            last_attempted_example = candidate
            last_attempted_verification = verification
        if (
            verification is not None
            and expected_revision is not None
            and verification.source_revision.casefold() != expected_revision.casefold()
        ):
            return RepositoryExampleSelectionV2(
                outcome="REVISION_MISMATCH",
                candidate_count=len(indexed),
                attempted_count=attempted,
            )
        if (
            verification is not None
            and verification.truth_eligible
            and verification.outcome in {"SOURCE_BUILD_VERIFIED", "SOURCE_TREE_VERIFIED"}
        ):
            if expected_revision is not None and not _revision_matches(
                repository_root, expected_revision
            ):
                return RepositoryExampleSelectionV2(
                    outcome="REVISION_MISMATCH",
                    candidate_count=len(indexed),
                    attempted_count=attempted,
                )
            return RepositoryExampleSelectionV2(
                outcome="VERIFIED",
                example=candidate,
                verification=verification,
                candidate_count=len(indexed),
                attempted_count=attempted,
                selected_rank=selected_rank,
            )
        if _product_owned_install_failure(verification):
            assert verification is not None
            return RepositoryExampleSelectionV2(
                outcome="TERMINAL_PRODUCT_FAILURE",
                example=candidate,
                verification=verification,
                candidate_count=len(indexed),
                attempted_count=attempted,
                selected_rank=selected_rank,
            )
    return RepositoryExampleSelectionV2(
        outcome="NO_VERIFIED_CANDIDATE",
        candidate_count=len(indexed),
        attempted_count=attempted,
        last_attempted_example=last_attempted_example,
        last_attempted_verification=last_attempted_verification,
    )


def bounded_local_verification_detail(result: LocalProductVerificationV1 | None) -> str:
    """Return bounded redacted compiler feedback suitable for fact evidence."""

    if result is None:
        return "local build/example verification was not executed for this draft"
    execution = getattr(result, "example_compile", None) or getattr(result, "build", None)
    if execution is None or execution.return_code == 0:
        return result.detail
    diagnostic = "\n".join(part.strip() for part in (execution.stderr, execution.stdout) if part)
    if not diagnostic:
        return result.detail
    return f"{result.detail}; compiler diagnostic:\n{diagnostic[:2000]}"


def _preference(
    candidate: MinimalExamplePolicy,
    requested: MinimalExamplePolicy,
    repository_position: int,
) -> tuple[bool, bool, int, int, int, str]:
    if candidate.language == "python":
        value = assess_minimal_example_value(candidate.language, candidate.code)
        incomplete = not value.approval_eligible
        score = -value.score
    else:
        incomplete = False
        score = 0
    return (
        candidate.class_name.casefold() != requested.class_name.casefold(),
        incomplete,
        score,
        repository_position,
        len(candidate.code),
        candidate.evidence_paths[0],
    )


def _precheck_failures(root: Path, example: MinimalExamplePolicy) -> list[str]:
    failures = evidence_failures(
        root,
        example.evidence_paths,
        example.required_symbols,
        allow_partial_symbols=True,
    )
    failures.extend(generated_example_quality_failures(example.language, example.code))
    if example.language == "python" and not failures:
        value = assess_minimal_example_value(example.language, example.code)
        if not value.approval_eligible:
            failures.append(f"minimal Python example is {value.classification}")
    return failures


def _product_owned_install_failure(result: LocalProductVerificationV1 | None) -> bool:
    return bool(
        result is not None
        and not result.truth_eligible
        and result.outcome == "BUILD_FAILED"
        and result.ecosystem == "python"
        and result.isolated_execution is not None
        and result.isolated_execution.return_code in {20, 21}
    )


def _revision_matches(root: Path, expected: str) -> bool:
    if _REVISION.fullmatch(expected) is None or not (root / ".git").is_dir():
        return False
    try:
        revision = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        status = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain", "--untracked-files=all"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return revision.stdout.strip().casefold() == expected.casefold() and not status.stdout.strip()
