"""Pure registry-derived cohort resolution -- never a manually constructed repository URL.

Every function here only reads `data/products.json` (via the existing
`registry.loader.load_products`/`registry.priority.order_entries_by_platform_priority`) and plain
in-memory filtering. No network, no clone, no state mutation.
"""

from __future__ import annotations

from pathlib import Path

from readme_agent.registry.loader import load_products
from readme_agent.registry.models import ProductEntry
from readme_agent.registry.priority import order_entries_by_platform_priority

# The fixed seven-ecosystem canary cohort, resolved by (family, platform) -- see the task's own
# "SEVEN CANARIES" section. Never resolved by hard-coded org/repo names or URLs.
SEVEN_CANARY_PAIRS: tuple[tuple[str, str], ...] = (
    ("3d", "python"),
    ("3d", "net"),
    ("cells", "java"),
    ("cells", "cpp"),
    ("pdf", "go"),
    ("cells", "rust"),
    ("3d", "typescript"),
)


class CanaryResolutionError(ValueError):
    """A configured (family, platform) canary pair has no matching registry row."""


def load_portfolio_entries(registry_path: Path | None = None) -> tuple[ProductEntry, ...]:
    entries = load_products(registry_path) if registry_path is not None else load_products()
    return tuple(order_entries_by_platform_priority(entries))


def resolve_seven_canaries(entries: tuple[ProductEntry, ...]) -> list[ProductEntry]:
    """Resolve the fixed seven-ecosystem cohort strictly from registry rows.

    Fails loudly (never silently drops a member) if any configured pair has no match -- a missing
    canary is a registry/config problem to surface, not a smaller cohort to proceed with quietly.
    """

    by_pair = {(entry.family, entry.platform): entry for entry in entries}
    missing = [pair for pair in SEVEN_CANARY_PAIRS if pair not in by_pair]
    if missing:
        raise CanaryResolutionError(
            "seven-canary cohort is missing registry rows for: "
            + ", ".join(f"{family}/{platform}" for family, platform in missing)
        )
    return [by_pair[pair] for pair in SEVEN_CANARY_PAIRS]


def filter_entries(
    entries: tuple[ProductEntry, ...] | list[ProductEntry],
    *,
    only: list[str] | None = None,
    platform: str | None = None,
    family: str | None = None,
) -> list[ProductEntry]:
    """Repository include/exclude plus platform/family filters (EXECUTION BOUNDS section)."""

    result = list(entries)
    if only:
        wanted = set(only)
        result = [entry for entry in result if entry.org_repo in wanted]
    if platform:
        result = [entry for entry in result if entry.platform == platform]
    if family:
        result = [entry for entry in result if entry.family == family]
    return result


def resolve_fleet_remaining(
    entries: tuple[ProductEntry, ...] | list[ProductEntry],
    already_accepted_org_repos: set[str],
) -> list[ProductEntry]:
    """ "Run only repositories not already accepted" (FLEET mode)."""

    return [entry for entry in entries if entry.org_repo not in already_accepted_org_repos]
