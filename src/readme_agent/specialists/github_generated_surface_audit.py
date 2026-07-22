"""GitHub-generated-surface auditor (Wave 7b) -- domain `github_generated_
surface_audit`, the second domain-scoped specialist after `readme_
reconciliation.py`, whose exact two-node (`classify` -> `record`) LangGraph
pattern this mirrors precisely.

Class E per `docs/github-surface-control.md`/`repository-presentation-
surface-model.md` (contributors, languages, stargazers/forks/watchers/open
issues): audit-only, forever -- `OWN-005`/`OWN-012` forbid any renderer or
write path for a GitHub-generated surface, and none exists here, by design.

The classify step uses `state/change_detection.py::classify_surface()`
(Wave 7a's shared primitive) over a fingerprint of the whole audit snapshot,
with no owned-marker concept (this domain has none) -- degrading cleanly to
a plain FIRST_OBSERVATION/NO_CHANGE/CHANGED classification. Expected to read
CHANGED on almost every run for any repo with real star/fork/watcher
activity, since those counts genuinely do change constantly -- not a defect;
the underlying audit work is already cheap (a few GitHub API GETs), so the
classify gate's main value here is avoiding a duplicate `specialist_results`
entry on a genuinely-identical rerun, not a large cost saving. The full
snapshot lives in `DomainStateV1.details` (Wave 7a's generic
structured-payload field) regardless of classification, so the actual
counts are always in evidence, not just the change/no-change verdict."""

import json
import sys
from datetime import UTC, datetime

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from readme_agent.capabilities.dispatcher import dispatch_tool_call
from readme_agent.capabilities.domains import GITHUB_GENERATED_SURFACE_AUDIT
from readme_agent.capabilities.schema import PermissionClass
from readme_agent.errors import StateBackendError
from readme_agent.readme.facts import sha256_text
from readme_agent.state.backend import StateBackend
from readme_agent.state.change_detection import classify_surface
from readme_agent.state.domain_state import save_domain
from readme_agent.state.schema import DomainStateV1

DOMAIN = GITHUB_GENERATED_SURFACE_AUDIT
_READ_ONLY_PERMISSIONS: set[PermissionClass] = {"read_only_local", "read_only_network"}


def _audit_fingerprint(audit: dict) -> str:
    canonical = json.dumps(audit, sort_keys=True, separators=(",", ":"))
    return sha256_text(canonical)


def _classify_node(state: DomainStateV1, config: RunnableConfig) -> dict:
    org_repo = config["configurable"]["org_repo"]
    tool_call = {
        "function": {
            "name": "audit_github_generated_surfaces",
            "arguments": json.dumps({"org_repo": org_repo}),
        }
    }
    dispatch = dispatch_tool_call(tool_call, _READ_ONLY_PERMISSIONS, caller_domain=DOMAIN)
    if dispatch.outcome != "executed":
        return {"accepted_status": f"ERROR:{dispatch.outcome}:{dispatch.error}"}

    assert dispatch.result is not None
    audit = dispatch.result
    fingerprint = _audit_fingerprint(audit)
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
