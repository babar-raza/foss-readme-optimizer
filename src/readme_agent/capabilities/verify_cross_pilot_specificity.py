"""Capability wrapper for `verification/readme_proposal_bundle.py::verify_
cross_pilot_specificity()` (RPOC-052, `VAL-016`/`PIL-002`) -- the one
portfolio-level check in this pair: confirms a batch of candidates are
product-specific, not template clones of one another (byte-distinctness,
each candidate carries its own product token, no candidate leaks another
pilot's token).

Deliberately unscoped (`allowed_domains=[]`): unlike `verify_readme_
proposal_bundle` (dispatched per-repo, in-graph, under `caller_domain=
independent_verification`), this check is inherently cross-repository --
nothing in `capabilities/domains.py::KNOWN_DOMAINS` owns "a completed batch
of repos," and inventing a domain identity for a check with no single-repo
specialist caller would misrepresent it as something `specialists/registry.
py`'s completeness gate expects to have a matching per-repo specialist,
which this does not and should not have. Its real production caller is
portfolio batch tooling (today: `plans/investigations/tools/collect_
portfolio_readme_proposal_evidence.py`, dispatching this capability instead
of importing the bare function -- RPOC-052; later: whatever runs RPOC-081's
full-registry batches), never a per-repo graph node.

Same "no `precheck()`" reasoning as `verify_readme_proposal_bundle.py`'s own
module docstring: this is a plain `dispatch_tool_call()` capability
(`side_effect_class="read_only_local"`), never routed through `capabilities/
effect_ledger.py::dispatch_gated_effect()`, so a `precheck()` defined here
would never actually run.
"""

from readme_agent.capabilities.schema import CapabilityManifest
from readme_agent.verification.readme_proposal_bundle import verify_cross_pilot_specificity

CAPABILITY_ID = "verify_cross_pilot_specificity"

MANIFEST = CapabilityManifest(
    capability_id=CAPABILITY_ID,
    version="1",
    name="Verify cross-pilot specificity",
    purpose="Read-only, in-memory, portfolio-level: given a batch of (org_repo, candidate_text) "
    "pairs, rejects duplicate/byte-identical candidates, a candidate missing its own product "
    "token, and a candidate that leaks another pilot's product token (a lazy name-substituted "
    "clone) -- the real cross-repository half of author != verifier that a single-repo check "
    "structurally cannot perform.",
    category="independent_verification",
    owner="readme_agent.verification.readme_proposal_bundle",
    execution_type="validator",
    required_inputs={"pilots": "array"},
    produced_outputs={
        "verified": "boolean",
        "checks": "object",
        "failures": "array",
    },
    preconditions=[
        "pilots must be a list of [org_repo, candidate_text] pairs -- fewer than 2 pairs makes "
        "the cross-pilot comparison vacuous (nothing to compare against), but is not itself a "
        "dispatch error: the underlying check simply reports no failures",
    ],
    required_permissions=["read_only_local"],
    side_effect_class="read_only_local",
    tools_used=["verification.readme_proposal_bundle.verify_cross_pilot_specificity"],
    failure_modes=[
        "a real (non-exception) verified=False verdict on duplicate or cross-identity-leaking "
        "candidates -- this capability never raises for an ordinary verification failure",
    ],
    rollback_behavior="not applicable -- read-only, nothing to roll back",
    tests=["tests/unit/test_readme_proposal_bundle_verifier.py"],
    requirement_ids=["VAL-016", "PIL-002"],
)


def execute(pilots: list[list[str]]) -> dict:
    verdict = verify_cross_pilot_specificity([(org_repo, text) for org_repo, text in pilots])
    return verdict.model_dump(mode="json")
