"""AGT-008/Wave 8.5 -- on-demand, full-detail drill-down for one specialist
domain's durably-recorded findings, complementing the bounded per-turn
dossier summary (`supervisor/dossier.py`) every domain now gets.

Real, deliberate exception to decision #26(b)'s "capabilities are stateless"
rule, named explicitly rather than silently bent (mirroring how
`readme_presentation.py` is already documented as "the one deliberate
exception to one-module-one-domain-identity"): this capability's whole
purpose is reading live durable state on demand, which no wiring code has
pre-loaded for it. Resolved via `dispatch_tool_call()`'s `extra_kwargs`
parameter -- wiring code (never the LLM) supplies `state_backend` alongside
the LLM's own `org_repo`/`domain` arguments.
"""

from readme_agent.capabilities.schema import CapabilityManifest
from readme_agent.state.backend import StateBackend

CAPABILITY_ID = "get_domain_findings"

MANIFEST = CapabilityManifest(
    capability_id=CAPABILITY_ID,
    version="1",
    name="Get domain findings",
    purpose="Read-only: full, untruncated specialist findings for one domain from durable "
    "state, for on-demand drill-down when a dossier summary hints at something worth "
    "investigating further -- the per-turn dossier itself only ever carries a bounded "
    "(<=400 char) summary per domain.",
    category="observability",
    owner="readme_agent.state.backend",
    execution_type="deterministic_tool",
    required_inputs={"org_repo": "string", "domain": "string"},
    produced_outputs={"found": "boolean", "accepted_status": "string", "details": "object"},
    preconditions=["a durable state backend must be configured for this run (--durable-state)"],
    required_permissions=["read_only_network"],
    side_effect_class="read_only_network",
    allowed_domains=[],  # unscoped -- general-planner-visible
    tools_used=["state.backend.StateBackend.load"],
    failure_modes=["found=False when no durable backend is configured or the domain never ran"],
    rollback_behavior="not applicable -- read-only, nothing to roll back",
    tests=["tests/unit/test_capabilities.py"],
    requirement_ids=["AGT-008"],
)


def execute(org_repo: str, domain: str, *, state_backend: StateBackend | None = None) -> dict:
    if state_backend is None:
        return {"found": False, "reason": "no durable state backend configured for this run"}
    state = state_backend.load(org_repo)
    domain_state = state.domain_states.get(domain) if state is not None else None
    if domain_state is None:
        return {"found": False, "reason": f"no recorded state for domain {domain!r}"}
    return {
        "found": True,
        "accepted_status": domain_state.accepted_status,
        "details": domain_state.details,
    }
