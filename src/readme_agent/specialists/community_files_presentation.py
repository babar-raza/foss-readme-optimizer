"""Community-files specialist (Wave 7e) -- domain
`community_files_presentation`, the fifth domain-scoped specialist. Class 1
per `docs/github-surface-control.md` (LICENSE, CONTRIBUTING, CODE_OF_CONDUCT,
SECURITY, SUPPORT, templates): a real eventual write path exists for this
class, but this specialist stops at audit + prepared candidate content --
**no write into any work clone this wave**. Not `OWN-011` (community files
and `README.md` are verified disjoint surfaces -- `readme/renderer.py`
references no community-file name): simply don't register a second,
live-untested `local_write` capability in the same wave as the first one
(7g).

Dispatches the one new, domain-scoped `audit_community_files` capability.
The classify step fingerprints only the presence/recognition/license signals
(`present_files`/`recognized_files`/`community_profile_health_percentage`/
`detected_license`) -- not the full `details` payload, since
`prepared_candidates` carries a large constant text blob that never itself
changes and would otherwise make every run's fingerprint identical-looking
for the wrong reason (a change in the *audit signal* is what this domain
tracks, not a change in a bundled static asset). `detected_license` (Wave
7f) is what `cross_surface_validation` compares against `readme_
reconciliation`'s independently-derived `license_claim`."""

import json
import sys
from datetime import UTC, datetime

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from readme_agent.capabilities.dispatcher import dispatch_tool_call
from readme_agent.capabilities.domains import COMMUNITY_FILES_PRESENTATION
from readme_agent.capabilities.schema import PermissionClass
from readme_agent.errors import StateBackendError
from readme_agent.readme.facts import sha256_text
from readme_agent.state.backend import StateBackend
from readme_agent.state.change_detection import classify_surface
from readme_agent.state.domain_state import save_domain
from readme_agent.state.schema import DomainStateV1

DOMAIN = COMMUNITY_FILES_PRESENTATION
_READ_ONLY_PERMISSIONS: set[PermissionClass] = {"read_only_local", "read_only_network"}


def _fingerprint(audit: dict) -> str:
    signal = {
        "present_files": audit["present_files"],
        "recognized_files": audit["recognized_files"],
        "community_profile_health_percentage": audit["community_profile_health_percentage"],
        "detected_license": audit["detected_license"],
    }
    canonical = json.dumps(signal, sort_keys=True, separators=(",", ":"))
    return sha256_text(canonical)


def _classify_node(state: DomainStateV1, config: RunnableConfig) -> dict:
    org_repo = config["configurable"]["org_repo"]
    tool_call = {
        "function": {
            "name": "audit_community_files",
            "arguments": json.dumps({"org_repo": org_repo}),
        }
    }
    dispatch = dispatch_tool_call(tool_call, _READ_ONLY_PERMISSIONS, caller_domain=DOMAIN)
    if dispatch.outcome != "executed":
        return {"accepted_status": f"ERROR:{dispatch.outcome}:{dispatch.error}"}

    assert dispatch.result is not None
    audit = dispatch.result
    fingerprint = _fingerprint(audit)
    classification = classify_surface(
        current_fingerprint=fingerprint, prior_fingerprint=state.accepted_facts_hash
    )
    return {
        "accepted_facts_hash": fingerprint,
        "accepted_status": classification.classification,
        "details": audit,
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
