"""Intent-aware product-registry access gates."""

from readme_agent.errors import NotAllowlistedError
from readme_agent.registry.loader import find_entry
from readme_agent.registry.models import ProductEntry


def require_permitted(org_repo: str) -> ProductEntry:
    """Require an enabled registry entry for a write-capable operation."""

    entry = find_entry(org_repo)
    if entry is None or entry.mode == "disabled":
        raise NotAllowlistedError(
            f"{org_repo} is not in data/products.json with an enabled mode -- "
            "refusing to touch it. This is the hard allow-list gate."
        )
    return entry
