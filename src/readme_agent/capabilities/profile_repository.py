"""Wraps profile.detector.build_profile() -- read-only, multi-ecosystem
repository profiling (Wave 3). Same allow-list-gated clone pattern as
detect_readme_gaps.py -- decision #4's hard allow-list applies unconditionally
to every actual git/network operation; decision 24/PIL-011's "regardless of
mode" carve-out is about analysis *scope* for research/survey work, not a
license to clone a disabled entry through a live capability."""

from readme_agent.capabilities.schema import CapabilityManifest
from readme_agent.gitsafety.clone import clone_baseline
from readme_agent.paths import baseline_dir
from readme_agent.profile.detector import build_profile
from readme_agent.registry.loader import find_entry

CAPABILITY_ID = "profile_repository"

MANIFEST = CapabilityManifest(
    capability_id=CAPABILITY_ID,
    version="1",
    name="Profile repository",
    purpose="Read-only: detect every registered platform's manifest present in the repository "
    "(not a single ecosystem string) and report parsed identity facts plus any "
    "manifest-shaped file matching no registered platform.",
    category="repository_profiling",
    owner="readme_agent.profile.detector",
    execution_type="deterministic_tool",
    required_inputs={"org_repo": "string"},
    produced_outputs={
        "org_repo": "string",
        "detected_ecosystems": "array",
        "unresolved_manifests": "array",
    },
    preconditions=["org_repo must be allow-listed in data/products.json with a non-disabled mode"],
    required_permissions=["read_only_local"],
    side_effect_class="read_only_local",
    tools_used=["gitsafety.clone.clone_baseline", "profile.detector.build_profile"],
    failure_modes=["PermissionError if org_repo is not allow-listed with an enabled mode"],
    rollback_behavior="not applicable -- read-only, nothing to roll back",
    tests=["tests/unit/test_capabilities.py"],
)


def execute(org_repo: str) -> dict:
    entry = find_entry(org_repo)
    if entry is None or entry.mode == "disabled":
        raise PermissionError(f"{org_repo} is not allow-listed with an enabled mode")
    path = baseline_dir(entry.org, entry.repo_name)
    clone_baseline(entry, path)
    profile = build_profile(org_repo, path)
    return profile.model_dump()
