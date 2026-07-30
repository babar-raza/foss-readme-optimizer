"""Stable-branch draft-PR creation, update, and reconciliation mechanics."""

from __future__ import annotations

import base64
import hashlib
from pathlib import Path

import requests

from readme_agent import paths
from readme_agent.errors import GitSafetyError
from readme_agent.github_api.client import get_branch, get_file_content, repo_summary
from readme_agent.github_api.write_client import create_pull_request, find_open_pr
from readme_agent.gitsafety._git import run_git
from readme_agent.gitsafety.clone import force_rmtree, push_branch
from readme_agent.state.proposal_schema import OpenProposalV2, TrustedTransformationProposalV1

BRANCH_NAME = "readme-agent/presentation-update"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _head(repo_path: Path) -> str:
    result = run_git(["rev-parse", "HEAD"], cwd=repo_path)
    if result.returncode:
        raise GitSafetyError(f"cannot resolve proposal head: {result.stderr}")
    return result.stdout.strip()


def _prepare_clone(target_repository: str, branch_exists: bool, token: str) -> Path:
    org, repo = target_repository.split("/", maxsplit=1)
    work = paths.pr_work_dir(org, f"staging-{repo}")
    if work.exists():
        force_rmtree(work)
    work.parent.mkdir(parents=True, exist_ok=True)
    basic_auth = base64.b64encode(f"x-access-token:{token}".encode()).decode()
    clone_args = [
        "-c",
        f"http.extraheader=AUTHORIZATION: basic {basic_auth}",
        "clone",
        "--no-tags",
    ]
    if branch_exists:
        clone_args.extend(["--branch", BRANCH_NAME])
    clone_args.extend([f"https://github.com/{target_repository}.git", str(work)])
    clone = run_git(clone_args)
    if clone.returncode:
        raise GitSafetyError(f"proposal clone failed: {clone.stderr}")
    for key, value in (
        ("user.name", "readme-agent"),
        ("user.email", "readme-agent@users.noreply.github.com"),
    ):
        configured = run_git(["config", "--local", key, value], cwd=work)
        if configured.returncode:
            raise GitSafetyError(f"proposal git identity failed: {configured.stderr}")
    if not branch_exists:
        checkout = run_git(["checkout", "-b", BRANCH_NAME], cwd=work)
        if checkout.returncode:
            raise GitSafetyError(f"proposal branch checkout failed: {checkout.stderr}")
    return work


def apply_trusted_proposal(
    proposal: TrustedTransformationProposalV1,
    final_text: str,
    token: str,
) -> dict:
    """Apply one immutable request to one stable draft-PR branch."""

    summary = repo_summary(proposal.target_repository, token)
    current_base = summary["default_branch"]
    current_base_revision = get_branch(proposal.target_repository, current_base, token)["commit"][
        "sha"
    ]
    if current_base_revision != proposal.target_base_revision:
        raise GitSafetyError(
            "target base drifted; discard the stale request and rebuild from the new snapshot"
        )
    if _sha256(final_text.encode("utf-8")) != proposal.candidate_hash:
        raise GitSafetyError("candidate bytes do not match TrustedTransformationProposalV1")

    existing = find_open_pr(proposal.target_repository, BRANCH_NAME, token)
    try:
        get_branch(proposal.target_repository, BRANCH_NAME, token)
        branch_exists = True
    except requests.HTTPError as exc:
        if exc.response is None or exc.response.status_code != 404:
            raise
        branch_exists = False
    work = _prepare_clone(proposal.target_repository, branch_exists, token)
    readme = work / "README.md"
    if readme.is_file() and _sha256(readme.read_bytes()) == proposal.candidate_hash:
        changed = False
    else:
        readme.write_bytes(final_text.encode("utf-8"))
        add = run_git(["add", "README.md"], cwd=work)
        if add.returncode:
            raise GitSafetyError(f"git add failed: {add.stderr}")
        commit = run_git(
            ["commit", "-m", f"docs: refresh trusted README ({proposal.candidate_hash[:12]})"],
            cwd=work,
        )
        if commit.returncode:
            raise GitSafetyError(f"git commit failed: {commit.stderr}")
        push = push_branch(work, BRANCH_NAME, token)
        if push.returncode:
            raise GitSafetyError(f"proposal branch push failed: {push.stderr}")
        changed = True

    head_revision = _head(work)
    opened = False
    if existing is None:
        pr = create_pull_request(
            proposal.target_repository,
            head=BRANCH_NAME,
            base=current_base,
            title="docs: trusted README presentation POC",
            body=(
                "Trusted README transformation POC. Existing README claims were inherited and "
                "were not independently verified against repository source.\n\n"
                f"Proposal: `{proposal.proposal_id}`\n"
                f"Candidate: `{proposal.candidate_hash}`"
            ),
            token=token,
            draft=True,
        )
        existing = pr
        opened = True

    state = OpenProposalV2(
        proposal_id=proposal.proposal_id,
        source_repository=proposal.source_repository,
        target_repository=proposal.target_repository,
        content_assurance="trusted_inherited",
        proposal_kind="trusted_readme_transform",
        base_revision=current_base_revision,
        head_revision=head_revision,
        candidate_hash=proposal.candidate_hash,
        branch_name=BRANCH_NAME,
        pr_number=existing["number"],
        pr_url=existing["html_url"],
        drift_status="candidate_changed" if changed and not opened else "current",
        authorization_id=proposal.authorization_id,
    )
    return {
        "opened": opened,
        "already_open": not opened,
        "updated": changed and not opened,
        "unchanged": not changed,
        "pr_number": state.pr_number,
        "pr_url": state.pr_url,
        "branch_name": state.branch_name,
        "open_proposal": state.model_dump(mode="json"),
    }


def reconcile_trusted_proposal(
    proposal: TrustedTransformationProposalV1, token: str
) -> dict | None:
    existing = find_open_pr(proposal.target_repository, BRANCH_NAME, token)
    if existing is None:
        return None
    try:
        candidate = get_file_content(
            proposal.target_repository, "README.md", token, ref=BRANCH_NAME
        )
    except Exception:  # noqa: BLE001 - absence is an unresolved effect, never success
        return None
    if _sha256(candidate) != proposal.candidate_hash:
        return None
    summary = repo_summary(proposal.target_repository, token)
    current_base_revision = get_branch(
        proposal.target_repository, summary["default_branch"], token
    )["commit"]["sha"]
    state = OpenProposalV2(
        proposal_id=proposal.proposal_id,
        source_repository=proposal.source_repository,
        target_repository=proposal.target_repository,
        content_assurance="trusted_inherited",
        proposal_kind="trusted_readme_transform",
        base_revision=proposal.target_base_revision,
        head_revision=existing["head"]["sha"],
        candidate_hash=proposal.candidate_hash,
        branch_name=BRANCH_NAME,
        pr_number=existing["number"],
        pr_url=existing["html_url"],
        drift_status=(
            "current" if current_base_revision == proposal.target_base_revision else "base_moved"
        ),
        authorization_id=proposal.authorization_id,
    )
    return {
        "opened": False,
        "already_open": True,
        "updated": False,
        "unchanged": True,
        "pr_number": state.pr_number,
        "pr_url": state.pr_url,
        "branch_name": state.branch_name,
        "open_proposal": state.model_dump(mode="json"),
    }
