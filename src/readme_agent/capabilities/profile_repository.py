"""Wraps profile.detector.build_profile() -- read-only, multi-ecosystem
repository profiling (Wave 3). Gated by require_listed(), not the mutating
pipeline's require_permitted()/is_permitted() (decision #40): mode encodes
push/full-cycle readiness, never read eligibility, so this runs against every
registry entry regardless of mode -- including a `mode: "disabled"` one."""

from readme_agent.capabilities.schema import CapabilityManifest
from readme_agent.profile.cached import get_or_build_profile
from readme_agent.registry.loader import require_listed
from readme_agent.state.backend import StateBackend

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
    preconditions=[
        "org_repo must be listed in data/products.json (mode is irrelevant -- read-only)"
    ],
    required_permissions=["read_only_local"],
    side_effect_class="read_only_local",
    tools_used=["profile.cached.get_or_build_profile"],
    failure_modes=["NotAllowlistedError if org_repo is not listed in data/products.json"],
    rollback_behavior="not applicable -- read-only, nothing to roll back",
    tests=["tests/unit/test_capabilities.py"],
)


def execute(org_repo: str, *, state_backend: StateBackend | None = None) -> dict:
    """state_backend is never populated by the planner/dispatcher path
    (arguments come only from the tool-call JSON) -- it exists so a future
    direct caller with a durable backend (e.g. a scheduled registry sweep)
    gets the decision #40/Part B freshness-cache benefit; today's calls
    always clone+profile fresh, exactly as before."""
    entry = require_listed(org_repo)
    profile = get_or_build_profile(entry, state_backend)
    return profile.model_dump()
