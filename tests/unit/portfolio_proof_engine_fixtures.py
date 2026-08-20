"""Shared, non-test-collected fixture builders for portfolio_proof_engine tests.

Not named `test_*.py` on purpose -- pytest must never collect this module as a test file.
"""

from __future__ import annotations

from readme_agent.registry.models import ProductEntry
from readme_agent.supervisor.portfolio_proof_engine.contracts import ProofStageReceiptV1


def make_entry(
    *,
    org_repo: str = "acme/widget",
    family: str = "widgets",
    platform: str = "python",
    mode: str = "dry_run",
    active: bool = True,
    ecosystem: str | None = "python",
    policy_profile: str | None = "acme-widgets",
    repository_id: int = 1,
) -> ProductEntry:
    org, repo_name = org_repo.split("/", maxsplit=1)
    return ProductEntry(
        registry_schema_version=2,
        provider_identity={
            "provider": "github",
            "repository_id": repository_id,
            "node_id": f"R_{repository_id}",
        },
        family=family,
        platform=platform,
        repo_name=repo_name,
        repo_url=f"https://github.com/{org}/{repo_name}",
        clone_url=f"https://github.com/{org}/{repo_name}.git",
        active=active,
        discovered_via="test",
        mode=mode,
        ecosystem=ecosystem,
        policy_profile=policy_profile,
    )


def make_receipt(
    *,
    org_repo: str = "acme/widget",
    stage: str = "INTAKE",
    status: str = "OK",
    failure_reason: str | None = None,
    facts_hash: str | None = None,
    elapsed_seconds: float = 0.1,
    provider_call_count: int = 0,
    **overrides: object,
) -> ProofStageReceiptV1:
    payload: dict[str, object] = {
        "org_repo": org_repo,
        "stage": stage,
        "status": status,
        "failure_reason": failure_reason,
        "facts_hash": facts_hash,
        "elapsed_seconds": elapsed_seconds,
        "provider_call_count": provider_call_count,
        **overrides,
    }
    return ProofStageReceiptV1.model_validate(payload)
