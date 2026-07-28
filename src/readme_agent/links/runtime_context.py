"""Load the sole governed catalog and allocation inputs for one repository."""

from __future__ import annotations

from urllib.parse import urlparse

from readme_agent.links.catalog import load_aspose_link_catalogs
from readme_agent.links.catalog_models import AsposeLinkCatalogSetV1
from readme_agent.registry.loader import load_policy, require_listed
from readme_agent.registry.models import LinkAllocationPolicyV1


def load_runtime_link_inputs(
    org_repo: str,
) -> tuple[AsposeLinkCatalogSetV1 | None, LinkAllocationPolicyV1 | None]:
    """Resolve Aspose catalogs only for a policy that explicitly owns Aspose targets."""

    entry = require_listed(org_repo)
    if entry.policy_profile is None:
        raise ValueError(f"{org_repo!r} has no policy_profile")
    policy = load_policy(entry.policy_profile)
    org_host = (urlparse(policy.required_elements.products_org_link.url).hostname or "").casefold()
    com_host = (urlparse(policy.required_elements.products_com_link.url).hostname or "").casefold()
    if org_host != "products.aspose.org" or com_host != "products.aspose.com":
        return None, None
    return load_aspose_link_catalogs(), policy.link_allocation
