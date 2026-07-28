"""Load the sole governed catalog and allocation inputs for one repository."""

from __future__ import annotations

from readme_agent.links.catalog import load_aspose_link_catalogs
from readme_agent.links.catalog_models import AsposeLinkCatalogSetV1
from readme_agent.registry.loader import load_policy, require_listed
from readme_agent.registry.models import LinkAllocationPolicyV1


def load_runtime_link_inputs(
    org_repo: str,
) -> tuple[AsposeLinkCatalogSetV1, LinkAllocationPolicyV1]:
    """Resolve checksum-validated catalogs and the repository's typed ceilings."""

    entry = require_listed(org_repo)
    if entry.policy_profile is None:
        raise ValueError(f"{org_repo!r} has no policy_profile")
    policy = load_policy(entry.policy_profile)
    return load_aspose_link_catalogs(), policy.link_allocation
