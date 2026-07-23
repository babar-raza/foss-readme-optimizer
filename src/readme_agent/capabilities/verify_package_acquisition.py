"""Wave 11.2 (`PKG-005`/`006`): per-package-root acquisition verification --
unlike `check_install_path.py`'s single repo-wide `install_path_resolved`
boolean, this reports one outcome per `profile.schema.PackageRoot` (Wave
11.1, `ECO-004`), so a multi-root repository (a multi-module Maven tree, a
multi-`.csproj` .NET solution) gets a real verdict per module, not one
flattened answer that could silently hide a second module's broken
coordinate.

Read-only, live, opt-in -- same blast radius as `check_install_path.py`'s
existing Maven check (a `read_only_network` GET against a public registry),
just generalized across every root and every registered resolver
(`ecosystems/resolver.py`).

Outcome vocabulary deliberately narrower than the sprint plan's original
ask (`REGISTRY_VERIFIED`/`INSTALL_VERIFIED`/`SOURCE_BUILD_VERIFIED`/
`NOT_PUBLISHED`/`CAPABILITY_GAP`/`BLOCKED_NETWORK`/`NOT_APPLICABLE`) --
scope note, verified not assumed: `INSTALL_VERIFIED`/`SOURCE_BUILD_VERIFIED`
would require actually invoking a package manager (`pip install`/
`npm install`/`nuget restore`/a real C/C++ build) against arbitrary
resolved coordinates -- executing real, untrusted external commands this
project has no sandboxing story for, a materially different and larger
risk than the read-only HTTP GETs every other capability in this project
performs. Deliberately not built this pass; `PKG-006` names the gap
honestly rather than silently expanding this capability's blast radius."""

from pathlib import Path

from readme_agent import paths
from readme_agent.capabilities.schema import CapabilityManifest, OrgRepoOnlyInputV1
from readme_agent.ecosystems.registry import parse_manifest
from readme_agent.ecosystems.resolver import resolve
from readme_agent.gitsafety.clone import clone_baseline
from readme_agent.profile.detector import build_profile
from readme_agent.profile.schema import PackageRoot
from readme_agent.registry.loader import require_listed

CAPABILITY_ID = "verify_package_acquisition"

# Ecosystems `ecosystems/resolver.py` can resolve directly, one registry per
# key. `cpp` is deliberately absent -- `resolver.py`'s own docstring explains
# why (two independent, unrelated registries, no manifest evidence saying
# which one a given repo actually uses); a `cpp` root always reports
# CAPABILITY_GAP here rather than guessing Conan vs vcpkg.
_DIRECTLY_RESOLVABLE_ECOSYSTEMS = frozenset({"java", "python", "typescript", "net", "go"})

MANIFEST = CapabilityManifest(
    capability_id=CAPABILITY_ID,
    version="1",
    name="Verify package acquisition",
    purpose="Read-only, live: for every detected package root, resolve its install claim "
    "against the real public registry (Maven Central/PyPI/npm/NuGet/Go proxy) and report "
    "REGISTRY_VERIFIED/NOT_PUBLISHED/CAPABILITY_GAP/BLOCKED_NETWORK/NOT_APPLICABLE per root, "
    "not one repo-wide boolean.",
    category="ecosystem_resolution",
    owner="readme_agent.ecosystems.resolver",
    execution_type="deterministic_tool",
    required_inputs={"org_repo": "string"},
    produced_outputs={
        "org_repo": "string",
        "results": "array",
    },
    preconditions=[
        "org_repo must be listed in data/products.json (mode is irrelevant -- read-only)",
        "a root's ecosystem must be one of java/python/typescript/net/go for a real "
        "registry check to run -- cpp and any unregistered ecosystem report CAPABILITY_GAP",
    ],
    required_permissions=["read_only_local", "read_only_network"],
    side_effect_class="read_only_network",
    supported_build_systems=["maven", "pip", "npm", "msbuild", "go_modules"],
    supported_package_managers=["maven", "pip", "npm", "nuget", "go_modules"],
    supported_registries=["maven_central", "pypi", "npm_registry", "nuget", "go_proxy"],
    # Wave 11.4 (`CAP-008`): real structural validation of the one LLM-
    # visible argument, `org_repo` -- a malformed value (no slash, empty
    # segment) is now rejected by the dispatcher before this capability's
    # own `execute()` ever runs, not deep inside `require_listed()`.
    input_model=OrgRepoOnlyInputV1,
    tools_used=[
        "profile.detector.build_profile",
        "ecosystems.registry.parse_manifest",
        "ecosystems.resolver.resolve",
    ],
    failure_modes=["NotAllowlistedError if org_repo is not listed in data/products.json"],
    rollback_behavior="not applicable -- read-only, nothing to roll back",
    tests=["tests/unit/test_verify_package_acquisition.py"],
    requirement_ids=["PKG-005"],
)


def _root_outcome(root: PackageRoot, repo_root: Path) -> dict:
    if root.ecosystem not in _DIRECTLY_RESOLVABLE_ECOSYSTEMS:
        return {
            "path": root.path,
            "ecosystem": root.ecosystem,
            "outcome": "CAPABILITY_GAP",
            "detail": f"no unambiguous live resolver registered for ecosystem {root.ecosystem!r}",
        }

    root_dir = repo_root if root.path == "." else repo_root / root.path
    manifest = parse_manifest(root.ecosystem, root_dir)
    result = resolve(root.ecosystem, manifest)

    if result.blocked:
        outcome = "BLOCKED_NETWORK"
    elif result.found:
        outcome = "REGISTRY_VERIFIED"
    elif "manifest missing" in result.detail:
        outcome = "CAPABILITY_GAP"
    else:
        outcome = "NOT_PUBLISHED"

    return {
        "path": root.path,
        "ecosystem": root.ecosystem,
        "outcome": outcome,
        "detail": result.detail,
    }


def execute(org_repo: str) -> dict:
    entry = require_listed(org_repo)
    baseline_path = paths.baseline_dir(entry.org, entry.repo_name)
    clone_baseline(entry, baseline_path)
    profile = build_profile(org_repo, baseline_path)

    if not profile.package_roots:
        return {
            "org_repo": org_repo,
            "results": [
                {
                    "path": ".",
                    "ecosystem": None,
                    "outcome": "NOT_APPLICABLE",
                    "detail": "no package root detected -- nothing to verify acquisition for",
                }
            ],
        }

    return {
        "org_repo": org_repo,
        "results": [_root_outcome(root, baseline_path) for root in profile.package_roots],
    }
