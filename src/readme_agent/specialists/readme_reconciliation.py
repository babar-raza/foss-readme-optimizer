"""First real LangGraph-wrapped specialist (Wave 6, decision #39 -- executes
decision #27's Wave 6-8 commitment: "LangGraph is adopted, scoped to Wave 6-8
specialist/subgraph composition"; "LangGraph becomes a library the Wave 5
supervisor calls into for the specialist layer").

Two nodes, `classify` -> `record`, proving the state/handoff mechanism
decision #27 committed to. The graph state IS `DomainStateV1`, used
directly -- not a new, framework-specific schema, honoring decision #27's own
stated concern about importing "a second, foreign schema". `org_repo` and the
durable-state backend are invocation parameters passed via LangGraph's
`config["configurable"]`, never part of the accepted-state shape itself.

Node `classify` dispatches the `classify_upstream_change` capability via
`dispatch_tool_call(..., caller_domain=README_RECONCILIATION)` -- decision
#34's dispatch-side domain check is the actual enforcement boundary here,
unchanged and untouched by this graph; per decision #27's own clarification,
"LangGraph's per-node tool binding is a request-time reliability/UX layer,
not the enforcement boundary". Node `record` persists the result via the
already-proven `state/domain_state.py::save_domain()` (lease-primary,
version-CAS-backstop).

Best-effort like every other durable-state write in this project (mirrors
`orchestrator._record_accepted_state()`/`supervisor.loop._record_supervisor_
state()`): a write-back failure degrades to "not remembered this time," never
aborts the caller.
"""

import json
import sys
from datetime import UTC, datetime

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from readme_agent.capabilities.dispatcher import dispatch_tool_call
from readme_agent.capabilities.domains import README_RECONCILIATION
from readme_agent.capabilities.schema import PermissionClass
from readme_agent.errors import StateBackendError
from readme_agent.state.backend import StateBackend
from readme_agent.state.domain_state import save_domain
from readme_agent.state.schema import DomainStateV1

DOMAIN = README_RECONCILIATION
_READ_ONLY_PERMISSIONS: set[PermissionClass] = {"read_only_local", "read_only_network"}


def _classify_node(state: DomainStateV1, config: RunnableConfig) -> dict:
    org_repo = config["configurable"]["org_repo"]
    arguments: dict = {"org_repo": org_repo}
    if state.accepted_facts_hash is not None:
        arguments["prior_stripped_text_hash"] = state.accepted_facts_hash
        arguments["prior_owned_span_present"] = state.owned_span_present_at_accept

    tool_call = {
        "function": {"name": "classify_upstream_change", "arguments": json.dumps(arguments)}
    }
    dispatch = dispatch_tool_call(tool_call, _READ_ONLY_PERMISSIONS, caller_domain=DOMAIN)
    if dispatch.outcome != "executed":
        return {"accepted_status": f"ERROR:{dispatch.outcome}:{dispatch.error}"}

    assert dispatch.result is not None
    result = dispatch.result
    return {
        "accepted_facts_hash": result["stripped_text_hash"],
        "accepted_status": result["classification"],
        "upstream_revision_at_accept": result["current_revision"],
        "owned_span_present_at_accept": result["owned_span_present_now"],
        # Wave 7f: the one fact `cross_surface_validation` needs from this
        # domain -- what the README's own text currently claims about its
        # license, to compare against `community_files_presentation`'s
        # independently-detected LICENSE file classification.
        "details": {"license_claim": result["license_claim"]},
    }


def _record_node(state: DomainStateV1, config: RunnableConfig) -> dict:
    backend: StateBackend | None = config["configurable"].get("backend")
    org_repo = config["configurable"]["org_repo"]
    current_revision = config["configurable"].get("current_revision")
    timestamp = datetime.now(UTC).isoformat()

    if backend is not None and not (state.accepted_status or "").startswith("ERROR:"):
        try:
            save_domain(
                backend,
                org_repo,
                DOMAIN,
                state.model_copy(update={"domain": DOMAIN, "last_run_timestamp": timestamp}),
                current_revision=current_revision,
            )
        except StateBackendError as exc:
            print(
                f"warning: durable domain-state write-back failed, continuing without it: {exc}",
                file=sys.stderr,
            )
    return {"last_run_timestamp": timestamp}


def _build_graph():
    graph = StateGraph(DomainStateV1)
    graph.add_node("classify", _classify_node)
    graph.add_node("record", _record_node)
    graph.add_edge(START, "classify")
    graph.add_edge("classify", "record")
    graph.add_edge("record", END)
    return graph.compile()


_GRAPH = _build_graph()


def run(
    org_repo: str, backend: StateBackend | None, current_revision: str | None = None
) -> DomainStateV1:
    """Entry point `specialists/registry.py::run_domain()` calls. Loads the
    prior accepted state for this domain (if any), runs the two-node graph,
    and returns the resulting `DomainStateV1` -- already durably recorded by
    the `record` node when `backend` is not `None`.

    `current_revision` (Wave 8.6, `ORC-003` reversal prerequisite): threaded
    through to `_record_node()`'s own `save_domain()` call, which stamps
    `upstream_revision_at_accept` -- see `state/domain_state.py::save_
    domain()`'s own docstring for why this must happen at the persistence
    point, not here."""
    prior_domain_state = None
    if backend is not None:
        try:
            prior = backend.load(org_repo)
        except StateBackendError as exc:
            print(
                f"warning: durable state read failed, continuing without it: {exc}",
                file=sys.stderr,
            )
            prior = None
        if prior is not None:
            prior_domain_state = prior.domain_states.get(DOMAIN)

    initial_state = prior_domain_state or DomainStateV1(domain=DOMAIN)
    result = _GRAPH.invoke(
        initial_state,
        config={
            "configurable": {
                "org_repo": org_repo,
                "backend": backend,
                "current_revision": current_revision,
            }
        },
    )
    return DomainStateV1(**result)
