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
    # Wave 11.2 (`PKG-001`-`004`): `orchestrator.inspect_repo()` dispatches
    # `ecosystems.resolver.resolve(entry.ecosystem, manifest)` generically --
    # no ecosystem-specific code in this capability or `inspect_repo()`
    # itself -- so this list reflects every ecosystem `resolver.py` now
    # registers, not just Maven. `cpp` is deliberately absent: it resolves
    # under `"cpp_conan"`/`"cpp_vcpkg"`, not a direct `"cpp"` key
    # (`resolver.py`'s own docstring explains why), so this generic
    # ecosystem-keyed dispatch path cannot reach it without a caller first
    # picking one -- a real, honest gap, not this capability's to close.
    supported_build_systems=["maven", "pip", "npm", "msbuild", "go_modules"],
    supported_package_managers=["maven", "pip", "npm", "nuget", "go_modules"],
    supported_registries=["maven_central", "pypi", "npm_registry", "nuget", "go_proxy"],
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
