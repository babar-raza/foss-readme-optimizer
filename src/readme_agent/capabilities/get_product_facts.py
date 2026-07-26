"""Build ProductFactsV2 from one repository snapshot and approved policy.

Subjective positioning comes from policy; technical statements remain blocked
until their declared repository files and symbols exist. A local-dry-run
snapshot additionally builds the source and compiles the exact minimal example
inside a disposable, secret-free copy. Package-registry truth remains the
independently dispatched ``verify_package_acquisition`` capability.

No live `state_backend` object here (decision #26(b), matching
render_readme_candidate.py's own established convention) -- accepts the
same durable-skip signal as plain values (`prior_upstream_revision`/
`prior_profile_result`) instead; see profile_repository.py's matching
docstring for the full reasoning.
"""

from readme_agent.capabilities.schema import CapabilityManifest, OrgRepoOnlyInputV1
from readme_agent.facts.provider import collect_product_facts

CAPABILITY_ID = "get_product_facts"

MANIFEST = CapabilityManifest(
    capability_id=CAPABILITY_ID,
    version="3",
    name="Get product facts",
    purpose="Read-only: produces provenance-complete ProductFactsV2 from the bound immutable "
    "repository snapshot, mechanically parsed manifests/source/tests/license, and approved "
    "policy positioning. Technical assertions fail closed when evidence is missing. Under "
    "the local_dry_run profile it also verifies a source build and exact minimal example in "
    "a disposable secret-free copy.",
    category="product_facts",
    owner="readme_agent.registry.loader",
    execution_type="deterministic_tool",
    required_inputs={"org_repo": "string"},
    produced_outputs={
        "org_repo": "string",
        "family": "string",
        "platform": "string",
        "ecosystem": "string",
        "policy_profile": "string",
        "declared_license": "string",
        "products_org_link": "object",
        "products_com_link": "object",
        "relationship_talking_points": "array",
        "secondary_links": "array",
        "word_limit": "object",
        "prohibited_terms": "array",
        "link_whitelist_domains": "array",
        "detected_ecosystems": "array",
        "unresolved_manifests": "array",
        "package_roots": "array",
        "package_root_roles": "object",
        "surface_ownership": "object",
        "product_facts_v2": "object",
        "local_product_verification": "object",
        "source": "object",
    },
    preconditions=[
        "org_repo must be listed in data/products.json (mode is irrelevant -- read-only, "
        "same gate as profile_repository)",
    ],
    required_permissions=["read_only_local"],
    side_effect_class="read_only_local",
    # Wave 11.4 (`CAP-008`): real structural validation of the one
    # LLM-visible argument, `org_repo`.
    input_model=OrgRepoOnlyInputV1,
    tools_used=[
        "registry.loader.require_listed",
        "registry.loader.load_policy",
        "profile.cached.get_or_build_profile",
        "facts.repository_ingestion.ingest_repository_product_facts",
        "facts.local_verification.verify_local_product_example",
    ],
    failure_modes=[
        "NotAllowlistedError if org_repo is not listed in data/products.json",
        "NotAllowlistedError if the entry has no policy_profile configured",
    ],
    rollback_behavior="not applicable -- read-only, nothing to roll back",
    tests=["tests/unit/test_capabilities.py"],
)


def execute(
    org_repo: str,
    prior_upstream_revision: str | None = None,
    prior_profile_result: dict | None = None,
) -> dict:
    """prior_upstream_revision/prior_profile_result: see
    profile_repository.execute()'s matching docstring -- same deliberately
    undeclared-in-schema plain-value convention, same wiring caller
    (profile_repo_with_cache())."""
    return collect_product_facts(
        org_repo,
        prior_upstream_revision=prior_upstream_revision,
        prior_profile_result=prior_profile_result,
    )
