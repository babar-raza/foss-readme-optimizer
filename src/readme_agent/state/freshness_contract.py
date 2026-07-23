"""Wave 9.7 (`FRESH-001`-`006`): behavior around `state/schema.py::
SurfaceFreshnessContractV1`. README/community files are git-tracked -- a
real upstream commit IS their freshness signal, already handled by
`supervisor/convergence.py::is_fresh()`'s revision comparison. Description/
homepage/topics (`METADATA_PRESENTATION`), package/release state
(`PACKAGE_RELEASE_AUDIT`), GitHub-generated audits
(`GITHUB_GENERATED_SURFACE_AUDIT`), and the visual/social-preview surface
(`VISUAL_PREPARATION`) are not git-tracked at all -- each is only ever
observed by that domain's own specialist actually running a live query.

Before this fix, `supervisor/loop.py`'s pre-specialist-tier coarse shortcut
could return `CONVERGED_NO_CHANGE` from a git-SHA/control-plane/domain-
coverage match alone, permanently skipping the entire specialist tier --
including these four domains' own live checks -- for as long as upstream
stayed unchanged, even though e.g. a package publish or a topics edit would
have been caught immediately had the tier actually run. This is the literal
"repository-level no-op based only on Git SHA" prohibited outcome the Wave
9.7 sprint plan names.

Open proposals (`PRL-002`) are a separate condition
(`supervisor/convergence.py::has_open_proposal_needing_reconciliation()`),
not a TTL contract here -- there is nothing to periodically re-check via a
live query until a real one exists (`PRL-002` is still `PARTIAL`: no
specialist populates `RunStateV1.open_proposals` yet).

Deliberately conservative default TTLs -- a live pilot re-checks each
surface regularly enough to actually observe drift, per `GOVERNANCE.md`
rule 10, rather than being tuned for minimum specialist-tier cost."""

from datetime import datetime

from readme_agent.capabilities.domains import (
    GITHUB_GENERATED_SURFACE_AUDIT,
    METADATA_PRESENTATION,
    PACKAGE_RELEASE_AUDIT,
    VISUAL_PREPARATION,
)
from readme_agent.state.schema import SurfaceFreshnessContractV1

# (domain, authoritative_source, ttl_seconds) for the four non-git-tracked
# surfaces this phase covers.
_SURFACE_DEFAULTS: tuple[tuple[str, str, int], ...] = (
    (GITHUB_GENERATED_SURFACE_AUDIT, "github_api", 24 * 3600),
    (PACKAGE_RELEASE_AUDIT, "registry_api", 6 * 3600),
    (METADATA_PRESENTATION, "github_api", 24 * 3600),
    (VISUAL_PREPARATION, "local_filesystem", 24 * 3600),
)

DEFAULT_SURFACE_CONTRACTS: dict[str, SurfaceFreshnessContractV1] = {
    surface_id: SurfaceFreshnessContractV1(
        surface_id=surface_id, authoritative_source=source, ttl_seconds=ttl_seconds
    )
    for surface_id, source, ttl_seconds in _SURFACE_DEFAULTS
}


def is_due_for_recheck(contract: SurfaceFreshnessContractV1 | None, now: datetime) -> bool:
    """No recorded contract (or one that has never actually been checked)
    is always due -- the correct conservative default for a surface this
    project has never observed live."""
    if contract is None or contract.last_checked_at is None:
        return True
    elapsed = (now - datetime.fromisoformat(contract.last_checked_at)).total_seconds()
    return elapsed >= contract.ttl_seconds


def any_surface_due_for_recheck(
    contracts: dict[str, SurfaceFreshnessContractV1], now: datetime
) -> bool:
    return any(
        is_due_for_recheck(contracts.get(surface_id), now)
        for surface_id in DEFAULT_SURFACE_CONTRACTS
    )


def refresh_surface_contracts(
    prior_contracts: dict[str, SurfaceFreshnessContractV1],
    observed_hashes: dict[str, str | None],
    now: datetime,
) -> dict[str, SurfaceFreshnessContractV1]:
    """Called once the specialist tier has actually run this turn: stamps
    every tracked non-git surface as freshly checked `now`, carrying
    forward each surface's own configured `ttl_seconds`/
    `authoritative_source` from its prior contract (if any) rather than
    resetting it to the default every time."""
    refreshed = {}
    for surface_id, default_contract in DEFAULT_SURFACE_CONTRACTS.items():
        base = prior_contracts.get(surface_id, default_contract)
        refreshed[surface_id] = base.model_copy(
            update={
                "last_checked_at": now.isoformat(),
                "observed_hash": observed_hashes.get(surface_id),
            }
        )
    return refreshed
