"""Facts-only portfolio readiness: loop the full registry, recompute genuine
freshness live, and report per-repository section readiness -- never a
candidate, never an authoring/review call, never a product-repository write.

Facts collection itself (`capabilities/get_product_facts.py`) is
deliberately not invoked from here: this module's own boundary is
read-only, network-cheap (`git ls-remote` only, via `remote_head_sha`) --
full fact collection can involve a real clone and, for some policy
profiles, local build/example verification, which belongs to the
supervisor's own bounded lifecycle stages, not a facts-only readiness
sweep. Callers that already hold a repository's `ProductFactsV2` (from the
existing `local_poc`/`get_product_facts` path) pass it through
`facts_by_org_repo`; a repository with no facts supplied is reported
`BLOCKED_FACTS` honestly, never silently skipped or fabricated.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from readme_agent.facts.aspose_knowledge_claims import (
    assess_bundle_freshness,
    load_bundle_provenance,
)
from readme_agent.facts.readme_facts_readiness import (
    RepositoryFactsReadinessV1,
    build_repository_facts_readiness,
)
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.gitsafety.clone import remote_head_sha
from readme_agent.registry.loader import PRODUCTS_PATH, load_products
from readme_agent.registry.models import ProductEntry

_KNOWLEDGE_DATA_ROOT = Path("data") / "imported"


class RepositoryFreshnessV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    org_repo: str
    family: str
    platform: str
    live_source_revision: str | None
    knowledge_repo_sha: str | None
    freshness: str
    live_probe_succeeded: bool


def _org_repo(entry: ProductEntry) -> str:
    return f"{entry.repo_url.rsplit('/', 2)[-2]}/{entry.repo_name}"


def processable_registry_entries(products_path: Path = PRODUCTS_PATH) -> tuple[ProductEntry, ...]:
    """The 31 processable entries out of the full 33-entry registry: every
    entry except `mode == "disabled"` (PSD/.NET and PSD/Python -- README-only
    products with no code, per plans/idea.md's P1 boundary). `mode` never
    means "excluded from read-only work" beyond that one literal value --
    `dry_run`/`full` are both processable for facts-readiness purposes."""

    return tuple(entry for entry in load_products(products_path) if entry.mode != "disabled")


def repository_live_freshness(entry: ProductEntry, *, timeout: float = 15) -> RepositoryFreshnessV1:
    """Recompute freshness live -- never trust a prior snapshot's claim.
    `remote_head_sha` is a `git ls-remote` probe only (no clone); a failed
    probe is an honest `unavailable` freshness, never guessed current or
    stale."""

    live_sha = remote_head_sha(entry.clone_url, timeout=timeout)
    provenance = load_bundle_provenance(
        entry.family, entry.platform, data_root=_KNOWLEDGE_DATA_ROOT
    )
    if live_sha is None:
        freshness = "unavailable"
    else:
        freshness = assess_bundle_freshness(provenance, current_repo_sha=live_sha)
    return RepositoryFreshnessV1(
        org_repo=_org_repo(entry),
        family=entry.family,
        platform=entry.platform,
        live_source_revision=live_sha,
        knowledge_repo_sha=provenance.repo_sha if provenance else None,
        freshness=freshness,
        live_probe_succeeded=live_sha is not None,
    )


class PortfolioFactsReadinessV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    total_processable: int
    readiness: tuple[RepositoryFactsReadinessV1, ...]
    freshness: tuple[RepositoryFreshnessV1, ...]
    facts_not_collected: tuple[str, ...]

    def stale_org_repos(self) -> tuple[str, ...]:
        return tuple(
            sorted(row.org_repo for row in self.freshness if row.freshness == "stale_revision")
        )


def portfolio_facts_readiness(
    *,
    products_path: Path = PRODUCTS_PATH,
    facts_by_org_repo: Mapping[str, ProductFactsV2] | None = None,
    knowledge_revision_by_org_repo: Mapping[str, str | None] | None = None,
    freshness_probe: Callable[[ProductEntry], RepositoryFreshnessV1] | None = None,
) -> PortfolioFactsReadinessV1:
    """Facts-only readiness across the full processable registry.

    `facts_by_org_repo` is an explicit, honest dependency: this function
    never collects facts itself (see module docstring). A repository absent
    from it is reported in `facts_not_collected`, never silently dropped
    from `total_processable` or given a fabricated READY/BLOCKED verdict.
    `freshness_probe` defaults to the real live `git ls-remote` recompute;
    tests inject a stub to stay offline and deterministic.
    """

    probe = freshness_probe or repository_live_freshness
    provided_facts = facts_by_org_repo or {}
    knowledge_revisions = knowledge_revision_by_org_repo or {}
    entries = processable_registry_entries(products_path)

    freshness_rows: list[RepositoryFreshnessV1] = []
    readiness_rows: list[RepositoryFactsReadinessV1] = []
    not_collected: list[str] = []
    for entry in entries:
        org_repo = _org_repo(entry)
        freshness_row = probe(entry)
        freshness_rows.append(freshness_row)
        facts = provided_facts.get(org_repo)
        if facts is None:
            not_collected.append(org_repo)
            continue
        readiness_rows.append(
            build_repository_facts_readiness(
                facts,
                family=entry.family,
                platform=entry.platform,
                source_revision=freshness_row.live_source_revision,
                knowledge_revision=knowledge_revisions.get(
                    org_repo, freshness_row.knowledge_repo_sha
                ),
                freshness=freshness_row.freshness,
            )
        )

    return PortfolioFactsReadinessV1(
        total_processable=len(entries),
        readiness=tuple(readiness_rows),
        freshness=tuple(freshness_rows),
        facts_not_collected=tuple(sorted(not_collected)),
    )


__all__ = [
    "PortfolioFactsReadinessV1",
    "RepositoryFreshnessV1",
    "portfolio_facts_readiness",
    "processable_registry_entries",
    "repository_live_freshness",
]
