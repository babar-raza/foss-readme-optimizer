"""Visuals specialist (Wave 7h) -- domain `visual_preparation`, the eighth
and (per the approved Wave 7 plan) final specialist of this wave.
Prepare-only: validates an existing image asset if one exists, or prepares a
real, freshly-generated candidate banner from product facts if none does --
**no embed-write into README.md this wave**, deliberately deferred (see
`capabilities/prepare_visual_asset.py`'s module docstring for the real
precedent this defers against: the retired `callout` span's confirmed
link-duplication bug).

Dispatches the existing, unscoped `get_product_facts` (family/platform) then
the new, domain-scoped `prepare_visual_asset` -- the same two-capability
pattern `metadata_presentation.py` already established, rather than one
capability reaching into another's dispatch path (decision #26(b))."""

import json
import sys
from datetime import UTC, datetime

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from readme_agent.capabilities.dispatcher import dispatch_tool_call
from readme_agent.capabilities.domains import VISUAL_PREPARATION
from readme_agent.capabilities.schema import PermissionClass
from readme_agent.errors import StateBackendError
from readme_agent.readme.facts import sha256_text
from readme_agent.state.backend import StateBackend
from readme_agent.state.change_detection import classify_surface
from readme_agent.state.domain_state import merge_details, save_domain
from readme_agent.state.schema import DomainStateV1

DOMAIN = VISUAL_PREPARATION
_READ_ONLY_PERMISSIONS: set[PermissionClass] = {"read_only_local", "read_only_network"}


def _fingerprint(result: dict) -> str:
    canonical = json.dumps(result, sort_keys=True, separators=(",", ":"))
    return sha256_text(canonical)


def _classify_node(state: DomainStateV1, config: RunnableConfig) -> dict:
    org_repo = config["configurable"]["org_repo"]

    facts_tool_call = {
        "function": {"name": "get_product_facts", "arguments": json.dumps({"org_repo": org_repo})}
    }
    facts_dispatch = dispatch_tool_call(
        facts_tool_call, _READ_ONLY_PERMISSIONS, caller_domain=DOMAIN
    )
    if facts_dispatch.outcome != "executed":
        return {"accepted_status": f"ERROR:{facts_dispatch.outcome}:{facts_dispatch.error}"}
    assert facts_dispatch.result is not None
    facts = facts_dispatch.result

    visual_tool_call = {
        "function": {
            "name": "prepare_visual_asset",
            "arguments": json.dumps(
                {
                    "org_repo": org_repo,
                    "family": facts.get("family"),
                    "platform": facts.get("platform"),
                }
            ),
        }
    }
    visual_dispatch = dispatch_tool_call(
        visual_tool_call, _READ_ONLY_PERMISSIONS, caller_domain=DOMAIN
    )
    if visual_dispatch.outcome != "executed":
        return {"accepted_status": f"ERROR:{visual_dispatch.outcome}:{visual_dispatch.error}"}
    assert visual_dispatch.result is not None
    result = visual_dispatch.result

    fingerprint = _fingerprint(result)
    classification = classify_surface(
        current_fingerprint=fingerprint, prior_fingerprint=state.accepted_facts_hash
    )
    return {
        "accepted_facts_hash": fingerprint,
        "accepted_status": classification.classification,
        "details": result,
    }


def _review_node(state: DomainStateV1, config: RunnableConfig) -> dict:
    """Wave 8.6 (item H): additive, advisory-only vision-model accuracy
    review of whatever asset `_classify_node` just found/prepared -- never
    gates any write path (`commit_readme_write` stays exclusively `VER-001`'s
    territory). Short-circuits on a classify-stage error, protecting
    `VER-003`'s "no unnecessary work"."""
    if (state.accepted_status or "").startswith("ERROR:"):
        return {}

    org_repo = config["configurable"]["org_repo"]
    review_tool_call = {
        "function": {
            "name": "review_visual_asset_accuracy",
            "arguments": json.dumps({"org_repo": org_repo}),
        }
    }
    dispatch = dispatch_tool_call(review_tool_call, _READ_ONLY_PERMISSIONS, caller_domain=DOMAIN)
    if dispatch.outcome != "executed":
        # Advisory only -- a review failure never escalates to blocking the
        # domain's own accepted classification, unlike a real gate failure.
        return {"details": merge_details(state, visual_accuracy_review={"error": dispatch.error})}

    assert dispatch.result is not None
    return {"details": merge_details(state, visual_accuracy_review=dispatch.result)}


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
    graph.add_node("review", _review_node)
    graph.add_node("record", _record_node)
    graph.add_edge(START, "classify")
    graph.add_edge("classify", "review")
    graph.add_edge("review", "record")
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
