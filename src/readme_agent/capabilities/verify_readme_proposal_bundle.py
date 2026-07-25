"""Capability wrapper for `verification/readme_proposal_bundle.py::verify_
readme_proposal_bundle()` (RPOC-050/051, `PRODSYS-P2-T1`/`VERIFIER-BUILT-
NOT-WIRED`) -- the deterministic, author != verifier bundle-completeness
re-check: schema/checksum/citation/protected-content/independent-
reconstruction, all re-derived from disk, never trusting a producer's own
claim.

Before this module existed, `verify_readme_proposal_bundle()` had zero call
sites inside `src/readme_agent/` -- reachable only from a test or one of the
standalone `plans/investigations/tools/*.py` scripts, exactly the recurring
failure mode `scripts/governance/check_verifiers_are_wired.py` exists to
flag (that function was itself built once, in commit `ff77c5f`, and stayed
unwired until `de7ff3d`). `execute()` below is a real call site inside
`src/`, and this module's own registration in `capabilities/registry.py`
makes the underlying verifier genuinely capability-dispatched -- reachable
by domain-scoped `dispatch_tool_call()`, not just importable as a bare
function -- for its one real production caller,
`specialists/readme_presentation.py::_review_node` (RPOC-051).

Deliberately no module-level `precheck()`: that hook (`capabilities/
registry.py::PrecheckFn`) is resolved and called only by `capabilities/
effect_ledger.py::dispatch_gated_effect()`, immediately before it would
otherwise write a pending ledger entry -- machinery that exists purely for
`local_write`/`remote_write` (mutating) capabilities. This capability's own
`side_effect_class` is `read_only_network` (see below); it is dispatched via
plain `dispatch_tool_call()`, which never looks `precheck()` up at all. A
`precheck()` defined here would be dead code -- never invoked by any real
call path -- which is a worse trap for a future reader than its absence: it
would read as an enforced gate that structurally cannot fire. The manifest's
own `preconditions` below states the same real precondition in plain text
instead.
"""

from pathlib import Path

from readme_agent.capabilities.domains import INDEPENDENT_VERIFICATION
from readme_agent.capabilities.schema import CapabilityManifest
from readme_agent.verification.readme_proposal_bundle import verify_readme_proposal_bundle

CAPABILITY_ID = "verify_readme_proposal_bundle"

MANIFEST = CapabilityManifest(
    capability_id=CAPABILITY_ID,
    version="1",
    name="Verify README proposal bundle",
    purpose="Independently re-verify a materialized 8-artifact README-proposal evidence bundle "
    "(original/candidate/patch/facts/plan/validation/checksums) from scratch: rebuilds the "
    "candidate from the original README and facts, re-applies the patch with native Git, "
    "recomputes validation, and re-checks package-acquisition ground truth live -- never trusts "
    "the producer's own stored candidate, plan, or validation result.",
    category="independent_verification",
    owner="readme_agent.verification.readme_proposal_bundle",
    execution_type="validator",
    required_inputs={"bundle_dir": "string"},
    produced_outputs={
        "org_repo": "string",
        "verified": "boolean",
        "checks": "object",
        "failures": "array",
    },
    preconditions=[
        "bundle_dir must be an existing directory containing all 8 required artifacts "
        "(original-readme.md, candidate-readme.md, proposal.patch, product-facts-v2.json, "
        "readme-document-plan-v1.json, repository-presentation-plan-v1.json, "
        "document-validation.json, artifact-sha256.json) -- a missing artifact is reported as "
        "a real verification failure (all_artifacts_present), never a dispatch error",
    ],
    required_permissions=["read_only_local", "read_only_network"],
    # Highest real blast radius this capability reaches: `_verify_acquisition_ground_truth`
    # performs a live, read-only registry lookup (Maven Central/PyPI/npm/NuGet/Go proxy) as
    # part of the independent re-check, mirroring `verify_package_acquisition`'s own posture.
    side_effect_class="read_only_network",
    allowed_domains=[INDEPENDENT_VERIFICATION],
    tools_used=["verification.readme_proposal_bundle.verify_readme_proposal_bundle"],
    failure_modes=[
        "a real (non-exception) verified=False verdict on any tampered, incomplete, or "
        "internally-inconsistent bundle -- this capability never raises for an ordinary "
        "verification failure, only for a genuinely broken dispatch (e.g. bundle_dir missing)",
    ],
    rollback_behavior="not applicable -- read-only, nothing to roll back",
    tests=[
        "tests/unit/test_readme_proposal_bundle_verifier.py",
        "tests/unit/test_specialists.py",
    ],
    requirement_ids=["VER-001"],
)


def execute(bundle_dir: str) -> dict:
    verdict = verify_readme_proposal_bundle(Path(bundle_dir))
    return verdict.model_dump(mode="json")
