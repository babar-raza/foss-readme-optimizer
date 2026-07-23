"""Wraps profile.detector.build_profile() -- read-only, multi-ecosystem
repository profiling (Wave 3). Gated by require_listed(), not the mutating
pipeline's require_permitted()/is_permitted() (decision #40): mode encodes
push/full-cycle readiness, never read eligibility, so this runs against every
registry entry regardless of mode -- including a `mode: "disabled"` one.

No live `state_backend` object here (decision #26(b), matching
render_readme_candidate.py's own established convention) -- accepts the
same durable-skip signal as plain values (`prior_upstream_revision`/
`prior_profile_result`) instead. `orchestrator.profile_repo_with_cache()` is
the deterministic wiring code that loads those from a real StateBackend and
persists the fresh result back; this capability never touches one itself."""

from readme_agent.capabilities.schema import CapabilityManifest, OrgRepoOnlyInputV1
from readme_agent.profile.cached import get_or_build_profile
from readme_agent.registry.loader import require_listed

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
    # Wave 11.4 (`CAP-008`): real structural validation of the one
    # LLM-visible argument, `org_repo`.
    input_model=OrgRepoOnlyInputV1,
    tools_used=["profile.cached.get_or_build_profile"],
    failure_modes=["NotAllowlistedError if org_repo is not listed in data/products.json"],
    rollback_behavior="not applicable -- read-only, nothing to roll back",
    tests=["tests/unit/test_capabilities.py"],
)


def execute(
    org_repo: str,
    prior_upstream_revision: str | None = None,
    prior_profile_result: dict | None = None,
) -> dict:
    """prior_upstream_revision/prior_profile_result are accepted but
    deliberately NOT declared in required_inputs/optional_inputs -- like
    render_readme_candidate.py's prior_facts_hash/prior_content_fingerprint/
    prior_status, they must never appear in the tool schema offered to a
    planner (an LLM has no business asserting its own prior-run facts);
    they exist only for deterministic wiring callers
    (profile_repo_with_cache()). Never populated by the planner/dispatcher
    path (arguments there come only from the tool-call JSON), so a
    planner-driven call always clones+profiles fresh, exactly as before."""
    entry = require_listed(org_repo)
    profile = get_or_build_profile(
        entry,
        prior_upstream_revision=prior_upstream_revision,
        prior_profile_result=prior_profile_result,
    )
    return profile.model_dump()
