"""Wraps `readme.reconciliation.classify()` -- the first capability scoped to
a real domain (`README_RECONCILIATION`, decision #34/`CAP-006`). Deliberately
stateless/pure like every other capability here: it clones the baseline,
reads the current README, and classifies -- it does NOT read or write
durable state itself. The caller (the `readme_reconciliation` specialist,
`specialists/readme_reconciliation.py`) is the deterministic wiring code that
loads the prior accepted domain state and supplies it as arguments, then
separately records the new result via `save_domain()`. This keeps state
persistence exclusively owned by deterministic wiring code (decision
#26(b)), never by a capability a planner could call arbitrarily."""

from readme_agent.capabilities.domains import README_RECONCILIATION
from readme_agent.capabilities.schema import CapabilityManifest
from readme_agent.gitsafety.clone import clone_baseline
from readme_agent.inspection import file_inventory
from readme_agent.inspection.git_metadata import get_git_metadata
from readme_agent.license.auditor import classify_license_text
from readme_agent.paths import baseline_dir
from readme_agent.readme.reconciliation import classify
from readme_agent.registry.loader import require_listed

CAPABILITY_ID = "classify_upstream_change"

MANIFEST = CapabilityManifest(
    capability_id=CAPABILITY_ID,
    version="1",
    name="Classify upstream README change",
    purpose="Read-only: compare the freshly-cloned upstream README (owned spans stripped) "
    "against a caller-supplied prior accepted fingerprint, classifying the result as "
    "FIRST_OBSERVATION/NO_CHANGE/UPSTREAM_CHANGED/OWNED_SPAN_LOST/MIXED_CHANGE. Never reads "
    "or writes durable state itself -- the caller supplies the prior fingerprint and owns "
    "persisting the new one.",
    category="drift_detection",
    owner="readme_agent.readme.reconciliation",
    execution_type="deterministic_tool",
    required_inputs={"org_repo": "string"},
    optional_inputs={
        "prior_stripped_text_hash": "string",
        "prior_owned_span_present": "boolean",
    },
    produced_outputs={
        "classification": "string",
        "stripped_text_hash": "string",
        "owned_span_present_now": "boolean",
        "current_revision": "string",
        "license_claim": "string",
    },
    preconditions=[
        "org_repo must be listed in data/products.json (mode is irrelevant -- read-only)",
        "absence of a prior fingerprint means FIRST_OBSERVATION, not an error",
    ],
    required_permissions=["read_only_local"],
    side_effect_class="read_only_local",
    allowed_domains=[README_RECONCILIATION],
    tools_used=["gitsafety.clone.clone_baseline", "readme.reconciliation.classify"],
    failure_modes=["NotAllowlistedError if org_repo is not listed in data/products.json"],
    rollback_behavior="not applicable -- read-only, nothing to roll back",
    tests=["tests/unit/test_capabilities.py", "tests/unit/test_reconciliation.py"],
    # Wave 8c (requirement mapping): the first domain-scoped capability
    # (Wave 6, decision #39).
    requirement_ids=["CAP-006"],
)


def execute(
    org_repo: str,
    prior_stripped_text_hash: str | None = None,
    prior_owned_span_present: bool = False,
) -> dict:
    entry = require_listed(org_repo)

    path = baseline_dir(entry.org, entry.repo_name)
    clone_baseline(entry, path)

    inventory = file_inventory.scan(path)
    readme_text = inventory.readme_path.read_text(encoding="utf-8") if inventory.readme_path else ""
    result = classify(
        current_readme_text=readme_text,
        prior_stripped_text_hash=prior_stripped_text_hash,
        prior_owned_span_present=prior_owned_span_present,
    )
    current_revision = get_git_metadata(path).commit_sha

    return {
        "classification": result.classification,
        "stripped_text_hash": result.stripped_text_hash,
        "owned_span_present_now": result.owned_span_present_now,
        "current_revision": current_revision,
        # Wave 7f: what the README's own text currently claims about its
        # license, via the same regex classifier `license.auditor.detect_
        # license()` uses for LICENSE-file content -- feeds
        # `cross_surface_validation`'s comparison against `community_files_
        # presentation`'s independently-detected LICENSE file classification.
        # `None` both when the README says nothing recognizable and when
        # there's no README at all -- not itself a gap this capability flags.
        "license_claim": classify_license_text(readme_text),
    }
