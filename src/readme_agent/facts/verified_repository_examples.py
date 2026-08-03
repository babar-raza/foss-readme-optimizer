"""Select one revision-bound repository example through the real verifier."""

from __future__ import annotations

import re
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

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


class VerifiedRepositoryExampleSelectionV1(NamedTuple):
    """One repository-authored candidate accepted by isolated verification."""

    example: MinimalExamplePolicy
    verification: LocalProductVerificationV1
    candidate_count: int
    attempted_count: int


def select_verified_repository_example(
    root: Path,
    *,
    source_revision: str | None,
    requested: MinimalExamplePolicy,
    verify_example_fn: VerifyExampleFn,
) -> VerifiedRepositoryExampleSelectionV1 | None:
    """Rank bounded repository candidates and return the first truth-eligible result."""

    repository_root = root.resolve()
    expected_revision = (
        source_revision
        if source_revision is not None and _REVISION.fullmatch(source_revision)
        else None
    )
    if expected_revision is not None and not _revision_matches(repository_root, expected_revision):
        return None
    readme_examples = repository_readme_example_candidates(
        repository_root,
        requested.language,
        supporting_paths=requested.evidence_paths,
    )
    source_examples = repository_source_example_candidates(repository_root, requested.language)
    indexed = list(enumerate([*readme_examples, *source_examples]))
    indexed.sort(key=lambda item: _preference(item[1], requested, item[0]))
    attempted = 0
    for _position, candidate in indexed[:MAX_VERIFIED_REPOSITORY_EXAMPLE_ATTEMPTS]:
        if _precheck_failures(repository_root, candidate):
            continue
        attempted += 1
        verification = verify_example_fn(candidate)
        if (
            verification is not None
            and verification.truth_eligible
            and verification.outcome == "SOURCE_BUILD_VERIFIED"
        ):
            if expected_revision is not None and not _revision_matches(
                repository_root, expected_revision
            ):
                return None
            return VerifiedRepositoryExampleSelectionV1(
                example=candidate,
                verification=verification,
                candidate_count=len(indexed),
                attempted_count=attempted,
            )
        if _product_owned_install_failure(verification):
            break
    return None


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
