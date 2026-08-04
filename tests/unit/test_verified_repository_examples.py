"""Repository-example selection preserves verified and terminal source outcomes."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from readme_agent.facts import verified_repository_examples as subject
from readme_agent.facts.example_verification_schema import LocalProductVerificationV1
from readme_agent.registry.models import MinimalExamplePolicy


def _example(class_name: str, path: str) -> MinimalExamplePolicy:
    return MinimalExamplePolicy(
        language="python",
        class_name=class_name,
        code=f"from package import {class_name}\nprint({class_name})",
        evidence_paths=[path],
    )


def _verification(
    *,
    return_code: int,
    truth_eligible: bool = False,
    source_revision: str = "a" * 40,
    stderr: str = "",
):
    return LocalProductVerificationV1.model_construct(
        schema_version=1,
        org_repo="acme/widget",
        source_revision=source_revision,
        ecosystem="python",
        outcome="SOURCE_BUILD_VERIFIED" if truth_eligible else "BUILD_FAILED",
        detail="controlled result",
        build=SimpleNamespace(return_code=return_code, stdout="", stderr=stderr),
        example_compile=None,
        truth_eligible=truth_eligible,
        isolated_execution=SimpleNamespace(return_code=return_code, truth_eligible=truth_eligible),
    )


def test_returns_terminal_product_source_failure_instead_of_discarding_candidate(
    tmp_path, monkeypatch
) -> None:
    requested = _example("Draft", "README.md")
    repository_example = _example("RepositoryExample", "README.md")
    later_example = _example("LaterExample", "examples/later.py")
    monkeypatch.setattr(subject, "_revision_matches", lambda *_args: True)
    monkeypatch.setattr(
        subject,
        "repository_readme_example_candidates",
        lambda *_args, **_kwargs: [repository_example, later_example],
    )
    monkeypatch.setattr(subject, "repository_source_example_candidates", lambda *_args: [])
    monkeypatch.setattr(subject, "_precheck_failures", lambda *_args: [])

    calls = 0

    def verify(_example):
        nonlocal calls
        calls += 1
        return _verification(return_code=21)

    selection = subject.select_verified_repository_example(
        tmp_path,
        source_revision="a" * 40,
        requested=requested,
        verify_example_fn=verify,
    )

    assert selection is not None
    assert selection.example == repository_example
    assert selection.outcome == "TERMINAL_PRODUCT_FAILURE"
    assert selection.verification.truth_eligible is False
    assert selection.attempted_count == 1
    assert selection.candidate_count == 2
    assert calls == 1


def test_ordinary_candidate_failure_does_not_hide_later_verified_candidate(
    tmp_path, monkeypatch
) -> None:
    first = _example("First", "README.md")
    second = _example("Second", "examples/use.py")
    monkeypatch.setattr(subject, "_revision_matches", lambda *_args: True)
    monkeypatch.setattr(
        subject, "repository_readme_example_candidates", lambda *_args, **_kwargs: [first, second]
    )
    monkeypatch.setattr(subject, "repository_source_example_candidates", lambda *_args: [])
    monkeypatch.setattr(subject, "_precheck_failures", lambda *_args: [])
    outcomes = iter(
        [
            _verification(return_code=22, source_revision="b" * 40),
            _verification(return_code=0, truth_eligible=True, source_revision="b" * 40),
        ]
    )

    selection = subject.select_verified_repository_example(
        tmp_path,
        source_revision="b" * 40,
        requested=first,
        verify_example_fn=lambda _example: next(outcomes),
    )

    assert selection is not None
    assert selection.example == second
    assert selection.outcome == "VERIFIED"
    assert selection.attempted_count == 2


def test_revision_mismatch_and_no_candidate_are_distinct_results(tmp_path, monkeypatch) -> None:
    requested = _example("Draft", "README.md")
    monkeypatch.setattr(subject, "_revision_matches", lambda *_args: False)
    mismatch = subject.select_verified_repository_example(
        tmp_path,
        source_revision="c" * 40,
        requested=requested,
        verify_example_fn=lambda _example: pytest.fail("revision mismatch must not verify"),
    )
    assert mismatch.outcome == "REVISION_MISMATCH"

    monkeypatch.setattr(subject, "_revision_matches", lambda *_args: True)
    monkeypatch.setattr(
        subject, "repository_readme_example_candidates", lambda *_args, **_kwargs: []
    )
    monkeypatch.setattr(subject, "repository_source_example_candidates", lambda *_args: [])
    empty = subject.select_verified_repository_example(
        tmp_path,
        source_revision="c" * 40,
        requested=requested,
        verify_example_fn=lambda _example: pytest.fail("empty candidate set must not verify"),
    )
    assert empty.outcome == "NO_VERIFIED_CANDIDATE"
    assert empty.candidate_count == 0
    assert empty.attempted_count == 0


def test_typed_result_rejects_terminal_failure_as_verified() -> None:
    with pytest.raises(ValueError, match="truth-eligible isolated verification"):
        subject.RepositoryExampleSelectionV2(
            outcome="VERIFIED",
            example=_example("RepositoryExample", "README.md"),
            verification=_verification(return_code=21),
            candidate_count=1,
            attempted_count=1,
            selected_rank=1,
        )


def test_bounded_detail_keeps_the_first_redacted_diagnostic_only() -> None:
    result = _verification(
        return_code=21,
        stderr="IndentationError in catcode.py line 66\n" + "x" * 2500,
    )

    detail = subject.bounded_local_verification_detail(result)

    assert "IndentationError in catcode.py line 66" in detail
    assert detail.startswith("controlled result; compiler diagnostic:\n")
    assert len(detail.removeprefix("controlled result; compiler diagnostic:\n")) == 2000
