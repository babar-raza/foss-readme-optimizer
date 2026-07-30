"""Disposable-staging proposal contracts and effect orchestration."""

import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from readme_agent.capabilities import presentation_pr_effect
from readme_agent.gitsafety._git import run_git
from readme_agent.state.proposal_schema import OpenProposalV2, TrustedTransformationProposalV1


def _proposal(**overrides) -> TrustedTransformationProposalV1:
    candidate = overrides.pop("candidate", "# Widget\n")
    values = {
        "proposal_id": "1" * 64,
        "source_repository": "source/widget",
        "target_repository": "staging/widget",
        "source_revision": "source-sha",
        "target_base_revision": "base-sha",
        "source_readme_hash": "2" * 64,
        "facts_hash": "3" * 64,
        "plan_hash": "4" * 64,
        "candidate_hash": hashlib.sha256(candidate.encode()).hexdigest(),
        "deterministic_validation_hash": "5" * 64,
        "independent_review_hash": "6" * 64,
        "cohort_id": "7" * 64,
        "authorization_id": "staging-auth",
        "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
        **overrides,
    }
    return TrustedTransformationProposalV1(**values)


def test_trusted_proposal_rejects_expiry():
    with pytest.raises(ValidationError):
        _proposal(expires_at=(datetime.now(UTC) - timedelta(seconds=1)).isoformat())


def test_open_proposal_v2_rejects_assurance_kind_mismatch():
    with pytest.raises(ValidationError):
        OpenProposalV2(
            proposal_id="1" * 64,
            source_repository="source/widget",
            target_repository="staging/widget",
            content_assurance="trusted_inherited",
            proposal_kind="verified_repository_presentation",
            base_revision="base",
            head_revision="head",
            candidate_hash="2" * 64,
            branch_name="readme-agent/presentation-update",
            pr_number=1,
            pr_url="https://example.invalid/1",
            authorization_id="auth",
        )


def test_effect_rejects_target_base_drift(monkeypatch):
    proposal = _proposal()
    monkeypatch.setattr(
        presentation_pr_effect,
        "repo_summary",
        lambda repo, token: {"default_branch": "main"},
    )
    monkeypatch.setattr(
        presentation_pr_effect,
        "get_branch",
        lambda repo, branch, token: {"commit": {"sha": "moved"}},
    )
    with pytest.raises(Exception, match="target base drifted"):
        presentation_pr_effect.apply_trusted_proposal(proposal, "# Widget\n", "token")


def test_reconciliation_requires_candidate_bytes(monkeypatch):
    proposal = _proposal()
    monkeypatch.setattr(
        presentation_pr_effect,
        "find_open_pr",
        lambda *args: {
            "number": 1,
            "html_url": "https://example.invalid/1",
            "head": {"sha": "head"},
        },
    )
    monkeypatch.setattr(
        presentation_pr_effect,
        "get_file_content",
        lambda *args, **kwargs: b"different",
    )
    assert presentation_pr_effect.reconcile_trusted_proposal(proposal, "token") is None


def _committed_worktree(path: Path, readme: str) -> Path:
    path.mkdir()
    assert run_git(["init"], cwd=path).returncode == 0
    assert run_git(["config", "user.name", "Test"], cwd=path).returncode == 0
    assert run_git(["config", "user.email", "test@example.invalid"], cwd=path).returncode == 0
    (path / "README.md").write_bytes(readme.encode("utf-8"))
    assert run_git(["add", "README.md"], cwd=path).returncode == 0
    assert run_git(["commit", "-m", "seed"], cwd=path).returncode == 0
    return path


def _stub_remote(monkeypatch, work: Path, *, existing_pr: dict | None) -> None:
    monkeypatch.setattr(
        presentation_pr_effect,
        "repo_summary",
        lambda repo, token: {"default_branch": "main"},
    )
    monkeypatch.setattr(
        presentation_pr_effect,
        "get_branch",
        lambda repo, branch, token: {"commit": {"sha": "base-sha"}},
    )
    monkeypatch.setattr(
        presentation_pr_effect,
        "find_open_pr",
        lambda repo, branch, token: existing_pr,
    )
    monkeypatch.setattr(
        presentation_pr_effect,
        "_prepare_clone",
        lambda repo, branch_exists, token: work,
    )


def test_existing_proposal_branch_is_fast_forward_updated(tmp_path, monkeypatch):
    candidate = "# Widget\n\nAccepted candidate.\n"
    proposal = _proposal(candidate=candidate)
    work = _committed_worktree(tmp_path / "work", "# Drifted\n")
    existing_pr = {
        "number": 1,
        "html_url": "https://example.invalid/1",
        "head": {"sha": "old-head"},
    }
    _stub_remote(monkeypatch, work, existing_pr=existing_pr)
    pushes = []
    monkeypatch.setattr(
        presentation_pr_effect,
        "push_branch",
        lambda path, branch, token: (
            pushes.append(branch) or type("Result", (), {"returncode": 0, "stderr": ""})()
        ),
    )
    monkeypatch.setattr(
        presentation_pr_effect,
        "create_pull_request",
        lambda *args, **kwargs: pytest.fail("existing PR must be updated, not duplicated"),
    )

    result = presentation_pr_effect.apply_trusted_proposal(proposal, candidate, "token")

    assert result["updated"] is True
    assert result["opened"] is False
    assert result["pr_number"] == 1
    assert pushes == [presentation_pr_effect.BRANCH_NAME]
    assert (work / "README.md").read_text(encoding="utf-8") == candidate


def test_pushed_candidate_without_pr_recovers_by_creating_draft_pr(tmp_path, monkeypatch):
    candidate = "# Widget\n"
    proposal = _proposal(candidate=candidate)
    work = _committed_worktree(tmp_path / "work", candidate)
    _stub_remote(monkeypatch, work, existing_pr=None)
    monkeypatch.setattr(
        presentation_pr_effect,
        "push_branch",
        lambda *args, **kwargs: pytest.fail("exact pushed candidate must not be pushed twice"),
    )
    created = {}

    def create_pr(repo, **kwargs):
        created.update(kwargs)
        return {
            "number": 7,
            "html_url": "https://example.invalid/7",
            "head": {"sha": "head"},
        }

    monkeypatch.setattr(presentation_pr_effect, "create_pull_request", create_pr)

    result = presentation_pr_effect.apply_trusted_proposal(proposal, candidate, "token")

    assert result["opened"] is True
    assert result["unchanged"] is True
    assert result["pr_number"] == 7
    assert created["draft"] is True
