"""Wraps orchestrator.inspect_repo(check_install=True) -- live, opt-in
resolution of the repository's install path against the real package
registry (e.g. Maven Central). The one Wave 2 capability with a real network
side effect beyond the baseline clone; side_effect_class=read_only_network
makes this observable in the dispatcher's permission gate."""

from readme_agent.capabilities.schema import CapabilityManifest
from readme_agent.orchestrator import inspect_repo

CAPABILITY_ID = "check_install_path"

MANIFEST = CapabilityManifest(
    capability_id=CAPABILITY_ID,
    version="1",
    name="Check install path",
    purpose="Read-only, live: resolve the repository's install path against the real package "
    "registry (e.g. Maven Central) if the ecosystem supports it.",
    category="ecosystem_resolution",
    owner="readme_agent.ecosystems.resolver",
    execution_type="deterministic_tool",
    required_inputs={"org_repo": "string"},
    produced_outputs={
        "install_path_resolved": "boolean",
        "evidence": "string",
    },
    preconditions=[
        "org_repo must be allow-listed in data/products.json with a non-disabled mode",
        "resolution only runs if the repository's ecosystem has a registered resolver "
        "(ecosystems/resolver.py) -- otherwise install_path_resolved stays null",
    ],
    required_permissions=["read_only_local", "read_only_network"],
    side_effect_class="read_only_network",
    # Wave 3: statable now that RepositoryProfile's platform vocabulary exists --
    # true today (only ecosystems/resolver.py's Maven Central resolver is
    # implemented), not deferred further.
    supported_build_systems=["maven"],
    supported_package_managers=["maven"],
    supported_registries=["maven_central"],
    tools_used=["orchestrator.inspect_repo", "ecosystems.resolver.resolve"],
    failure_modes=["NotAllowlistedError if org_repo is not permitted", "package-registry timeout"],
    rollback_behavior="not applicable -- read-only, nothing to roll back",
    tests=["tests/unit/test_capabilities.py"],
)


def execute(org_repo: str) -> dict:
    r = inspect_repo(org_repo, check_install=True)
    pres = r["presentation_report"]
    return {
        "install_path_resolved": pres.install_path_resolved,
        "evidence": pres.evidence.get("install_path_resolved"),
    }
