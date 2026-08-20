"""Atomic, resumable, repository-relative storage for `ProofStageReceiptV1` records.

Output root defaults to `runs/portfolio_proof/` (git-ignored, matching every other `runs/`
subtree) but is fully configurable -- the GitHub-runner readiness requirement -- and every path
this module produces is relative to that root, never an absolute `D:\\` path.
"""

from __future__ import annotations

from pathlib import Path
from typing import get_args

from readme_agent import paths
from readme_agent.evidence.writer import refresh_sha256sums, write_redacted_json
from readme_agent.supervisor.portfolio_proof_engine.contracts import (
    STAGE_ORDER,
    ProofModeV1,
    ProofStageReceiptV1,
    ProofStageV1,
    campaign_id_for_mode,
)

DEFAULT_OUTPUT_ROOT_NAME = "portfolio_proof"


def default_output_root() -> Path:
    return paths.runs_dir() / DEFAULT_OUTPUT_ROOT_NAME


def _repo_alias(org_repo: str) -> str:
    org, repo = org_repo.split("/", maxsplit=1)
    return f"{org}__{repo}"


def repository_receipt_dir(output_root: Path, campaign_id: str, org_repo: str) -> Path:
    return output_root / campaign_id / _repo_alias(org_repo) / "receipts"


def receipt_path(output_root: Path, campaign_id: str, org_repo: str, stage: ProofStageV1) -> Path:
    return repository_receipt_dir(output_root, campaign_id, org_repo) / f"{stage}.json"


def write_receipt(output_root: Path, campaign_id: str, receipt: ProofStageReceiptV1) -> Path:
    """Write one receipt atomically. Overwriting the same stage with a byte-identical
    observation is a no-op in effect (same canonical_hash); a differing observation replaces it,
    since a receipt records the *current* observation of a repository's stage, not a history."""

    path = receipt_path(output_root, campaign_id, receipt.org_repo, receipt.stage)
    write_redacted_json(path, receipt.model_dump(mode="json"))
    refresh_sha256sums(path.parent)
    return path


def read_receipt(
    output_root: Path,
    campaign_id: str,
    org_repo: str,
    stage: ProofStageV1,
) -> ProofStageReceiptV1 | None:
    path = receipt_path(output_root, campaign_id, org_repo, stage)
    if not path.is_file():
        return None
    return ProofStageReceiptV1.model_validate_json(path.read_text(encoding="utf-8"))


def all_receipts_for_repo(
    output_root: Path,
    campaign_id: str,
    org_repo: str,
) -> dict[ProofStageV1, ProofStageReceiptV1]:
    result: dict[ProofStageV1, ProofStageReceiptV1] = {}
    for stage in STAGE_ORDER:
        receipt = read_receipt(output_root, campaign_id, org_repo, stage)
        if receipt is not None:
            result[stage] = receipt
    return result


def latest_receipt(
    output_root: Path,
    campaign_id: str,
    org_repo: str,
) -> ProofStageReceiptV1 | None:
    """Latest by `STAGE_ORDER` precedence (deterministic), not file mtime."""

    receipts = all_receipts_for_repo(output_root, campaign_id, org_repo)
    for stage in reversed(STAGE_ORDER):
        if stage in receipts:
            return receipts[stage]
    return None


_ALL_MODE_CAMPAIGN_IDS: tuple[str, ...] = tuple(
    campaign_id_for_mode(mode) for mode in get_args(ProofModeV1)
)


def find_accepted_receipt(output_root: Path, org_repo: str) -> ProofStageReceiptV1 | None:
    """ACCEPTED may have been recorded by any prior mode pass (a canary accepted during
    CANARIES must not be re-run by a later FLEET pass) -- checked across all five fixed
    per-mode campaigns, never only the caller's own."""

    for campaign_id in _ALL_MODE_CAMPAIGN_IDS:
        receipt = read_receipt(output_root, campaign_id, org_repo, "ACCEPTED")
        if receipt is not None:
            return receipt
    return None


def all_repos_in_campaign(output_root: Path, campaign_id: str) -> list[str]:
    """Repository aliases recorded so far, resolved back to `org/repo` from any one receipt."""

    campaign_dir = output_root / campaign_id
    if not campaign_dir.is_dir():
        return []
    org_repos: list[str] = []
    for repo_dir in sorted(campaign_dir.iterdir()):
        receipts_dir = repo_dir / "receipts"
        if not receipts_dir.is_dir():
            continue
        for receipt_file in sorted(receipts_dir.glob("*.json")):
            try:
                receipt = ProofStageReceiptV1.model_validate_json(
                    receipt_file.read_text(encoding="utf-8")
                )
            except ValueError:
                continue
            org_repos.append(receipt.org_repo)
            break
    return org_repos
