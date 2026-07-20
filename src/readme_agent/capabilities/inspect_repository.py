"""Wraps orchestrator.inspect_repo(check_install=False) -- basic repo facts,
read-only, no network beyond the baseline clone itself. Same function Wave
1's spike proved live (plans/investigations/agentic-loop-proof.md)."""

from readme_agent.capabilities.schema import CapabilityManifest
from readme_agent.orchestrator import inspect_repo

CAPABILITY_ID = "inspect_repository"

MANIFEST = CapabilityManifest(
    capability_id=CAPABILITY_ID,
    version="1",
    name="Inspect repository",
    purpose="Read-only: fetch basic repository facts (README presence/length, license file "
    "presence, manifest keys). No network beyond the baseline clone.",
    category="repository_profiling",
    owner="readme_agent.orchestrator",
    execution_type="deterministic_tool",
    required_inputs={"org_repo": "string"},
    produced_outputs={
        "org_repo": "string",
        "has_readme": "boolean",
        "has_license_file": "boolean",
        "readme_length_chars": "integer",
        "manifest_keys": "array",
    },
    preconditions=["org_repo must be allow-listed in data/products.json with a non-disabled mode"],
    required_permissions=["read_only_local"],
    side_effect_class="read_only_local",
    tools_used=["orchestrator.inspect_repo"],
    failure_modes=["NotAllowlistedError if org_repo is not permitted"],
    rollback_behavior="not applicable -- read-only, nothing to roll back",
    tests=["tests/unit/test_capabilities.py"],
)


def execute(org_repo: str) -> dict:
    r = inspect_repo(org_repo, check_install=False)
    return {
        "org_repo": r["org_repo"],
        "has_readme": r["has_readme"],
        "has_license_file": r["has_license_file"],
        "readme_length_chars": r["readme_length_chars"],
        "manifest_keys": sorted(r["manifest"].keys()) if r["manifest"] else [],
    }
