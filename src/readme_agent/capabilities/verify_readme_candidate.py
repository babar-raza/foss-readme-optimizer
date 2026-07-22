"""Wave 8b -- the independent verifier's pre-apply gate for the one real
write this project has. Domain-scoped to `independent_verification`, never
`readme_presentation`: `verify_readme_candidate` (the author, via `render_
readme_candidate`) and this capability (the verifier) are deliberately
distinct registered capabilities under distinct, dispatcher-enforced
`caller_domain` identities -- `VER-001`'s own acceptance text ("verifier and
author are distinct capability invocations").

Wraps `verification/checks.py::independently_verify_readme_candidate()`,
which never trusts the caller's claimed `status`/`needs_write`/`final_text`
at face value -- it re-derives ground truth from a fresh on-disk read of the
work clone and the repo's own configured policy. The first real use of
`execution_type="validator"` since it entered the closed enum at `CAP-004`.
"""

from readme_agent.capabilities.domains import INDEPENDENT_VERIFICATION
from readme_agent.capabilities.schema import CapabilityManifest
from readme_agent.verification.checks import independently_verify_readme_candidate

CAPABILITY_ID = "verify_readme_candidate"

MANIFEST = CapabilityManifest(
    capability_id=CAPABILITY_ID,
    version="1",
    name="Verify README candidate",
    purpose="Read-only: independently re-derives whether a rendered README candidate's claimed "
    "status/needs_write are actually true, by freshly re-reading the current on-disk work clone "
    "and re-running validation against the repo's own configured policy -- never trusting the "
    "caller's claimed values. The sole authority accepting a README candidate before "
    "commit_readme_write ever dispatches (VER-001).",
    category="independent_verification",
    owner="readme_agent.verification.checks",
    execution_type="validator",
    required_inputs={
        "org_repo": "string",
        "facts_hash": "string",
        "fresh_fingerprint": "string",
        "status": "string",
        "needs_write": "boolean",
        "final_text": "string",
    },
    produced_outputs={
        "verdict": "string",
        "reason": "string",
        "checks": "object",
        "requirement_map": "object",
    },
    preconditions=[
        "org_repo must be listed in data/products.json with a policy_profile configured",
        "final_text/facts_hash/status/needs_write are the candidate under review -- this "
        "capability never re-renders, only independently re-validates",
    ],
    required_permissions=["read_only_local"],
    side_effect_class="read_only_local",
    allowed_domains=[INDEPENDENT_VERIFICATION],
    tools_used=["verification.checks.independently_verify_readme_candidate"],
    failure_modes=[
        "NotAllowlistedError if org_repo is not listed in data/products.json or has no "
        "policy_profile configured"
    ],
    rollback_behavior="not applicable -- read-only, nothing to roll back",
    tests=["tests/unit/test_capabilities.py", "tests/unit/test_verification_checks.py"],
    # Wave 8c (requirement mapping): the independent verifier itself.
    requirement_ids=["VER-001", "VER-002"],
)


def execute(
    org_repo: str,
    facts_hash: str,
    fresh_fingerprint: str,
    status: str,
    needs_write: bool,
    final_text: str,
) -> dict:
    return independently_verify_readme_candidate(org_repo, final_text, status, needs_write)
