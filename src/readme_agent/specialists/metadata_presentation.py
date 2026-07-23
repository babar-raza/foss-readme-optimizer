"""Metadata specialist (Wave 7d) -- domain `metadata_presentation`, the
fourth domain-scoped specialist. Class B per `docs/github-surface-control.md`
(description, homepage, topics): `OWN-006` permits only a dry-run-first,
explicitly gated proposal workflow -- **no GitHub API PATCH is attempted
this wave, or anywhere in this specialist**; the real write-scoped apply
gate is a later phase's job.

Dispatches the domain-scoped `propose_metadata_changes`, whose registered
boundary independently re-derives ProductFactsV2 through the shared facts
provider before reading current metadata or emitting a proposal. It accepts
no caller-supplied facts, eligibility, or citations."""

import json
import sys
from datetime import UTC, datetime

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from readme_agent.capabilities.dispatcher import dispatch_tool_call
from readme_agent.capabilities.domains import METADATA_PRESENTATION
from readme_agent.capabilities.schema import PermissionClass
from readme_agent.errors import StateBackendError
from readme_agent.readme.facts import sha256_text
from readme_agent.state.backend import StateBackend
from readme_agent.state.change_detection import classify_surface
from readme_agent.state.domain_state import save_domain
from readme_agent.state.schema import DomainStateV1

DOMAIN = METADATA_PRESENTATION
_READ_ONLY_PERMISSIONS: set[PermissionClass] = {"read_only_local", "read_only_network"}


def _fingerprint(current_metadata: dict) -> str:
    canonical = json.dumps(current_metadata, sort_keys=True, separators=(",", ":"))
    return sha256_text(canonical)


def _classify_node(state: DomainStateV1, config: RunnableConfig) -> dict:
    org_repo = config["configurable"]["org_repo"]

    proposal_tool_call = {
        "function": {
            "name": "propose_metadata_changes",
            "arguments": json.dumps({"org_repo": org_repo}),
        }
    }
    proposal_dispatch = dispatch_tool_call(
        proposal_tool_call, _READ_ONLY_PERMISSIONS, caller_domain=DOMAIN
    )
    if proposal_dispatch.outcome != "executed":
        return {"accepted_status": f"ERROR:{proposal_dispatch.outcome}:{proposal_dispatch.error}"}
    assert proposal_dispatch.result is not None
    proposal = proposal_dispatch.result

    current_metadata = {
        "current_description": proposal["current_description"],
        "current_homepage": proposal["current_homepage"],
        "current_topics": proposal["current_topics"],
    }
    fingerprint = _fingerprint(current_metadata)
    classification = classify_surface(
        current_fingerprint=fingerprint, prior_fingerprint=state.accepted_facts_hash
    )
    # `accepted_status` deliberately stays the generic change/no-change
    # verdict, not "is there still an open proposal" -- the convergence
    # shortcut (supervisor/loop.py) depends on NO_CHANGE meaning "nothing
    # new happened," not "nothing is wrong." A persistently unaddressed
    # proposal (e.g. a description a human hasn't filled in yet) must still
    # let an otherwise-unchanged rerun short-circuit; the proposal itself
    # stays fully visible in `details` regardless of status, every run.
    return {
        "accepted_facts_hash": fingerprint,
        "accepted_status": classification.classification,
        "details": proposal,
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
    through to `_record_node()`'s own `save_domain()` call -- see
    `state/domain_state.py::save_domain()`'s own docstring."""
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
