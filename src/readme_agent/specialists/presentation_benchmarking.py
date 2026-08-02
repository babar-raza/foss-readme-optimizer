"""Presentation-benchmarking specialist (Wave 8.6) -- domain
`presentation_benchmarking`, the tenth specialist. Dispatches only
`compare_against_presentation_standard` (the per-run comparison); the
sibling `compare_reference_repositories` capability is registered under
this same domain but deliberately NOT dispatched here -- it's a periodic,
scheduled-script capability, not a per-run one (see its own module
docstring).

Mirrors `visual_preparation.py`'s exact two-node (classify -> record)
shape."""

import hashlib
import json
import sys
from datetime import UTC, datetime

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from readme_agent import paths
from readme_agent.capabilities.dispatcher import dispatch_tool_call
from readme_agent.capabilities.domains import PRESENTATION_BENCHMARKING, README_PRESENTATION
from readme_agent.capabilities.schema import PermissionClass
from readme_agent.errors import StateBackendError
from readme_agent.readme.facts import sha256_text
from readme_agent.state.backend import StateBackend
from readme_agent.state.change_detection import classify_surface
from readme_agent.state.domain_state import save_domain
from readme_agent.state.lifecycle_schema import ReadmePocLifecycleStateV2
from readme_agent.state.schema import DomainStateV1
from readme_agent.supervisor.execution_context import proposal_only_active

DOMAIN = PRESENTATION_BENCHMARKING
DEPENDS_ON = (README_PRESENTATION,)
_READ_ONLY_PERMISSIONS: set[PermissionClass] = {"read_only_local", "read_only_network"}


def _fingerprint(result: dict) -> str:
    canonical = json.dumps(result, sort_keys=True, separators=(",", ":"))
    return sha256_text(canonical)


def _bound_candidate_text(
    org_repo: str,
    backend: StateBackend | None,
    current_revision: str | None,
) -> str | None:
    """Load the exact lifecycle-bound candidate, or signal no candidate stage."""

    if backend is None or current_revision is None:
        return None
    current = backend.load(org_repo)
    lifecycle = current.readme_poc_lifecycle if current is not None else None
    if not isinstance(lifecycle, ReadmePocLifecycleStateV2) or lifecycle.candidate_hash is None:
        return None
    if lifecycle.source_revision != current_revision:
        raise RuntimeError(
            "presentation benchmark lifecycle revision does not match current revision"
        )

    org, repo = org_repo.split("/", maxsplit=1)
    bundle_dir = paths.readme_poc_repository_dir(org, repo, current_revision)
    candidate_path = bundle_dir / "candidate" / "README.md"
    manifest_path = bundle_dir / "manifest.json"
    if not candidate_path.is_file() or not manifest_path.is_file():
        raise RuntimeError("presentation benchmark requires the lifecycle-bound candidate bundle")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_hash = manifest.get("candidate_hash")
    candidate_bytes = candidate_path.read_bytes()
    candidate_hash = hashlib.sha256(candidate_bytes).hexdigest()
    if manifest_hash != lifecycle.candidate_hash or candidate_hash != lifecycle.candidate_hash:
        raise RuntimeError(
            "presentation benchmark candidate hash does not match lifecycle/manifest"
        )
    return candidate_bytes.decode("utf-8")


def _classify_node(state: DomainStateV1, config: RunnableConfig) -> dict:
    org_repo = config["configurable"]["org_repo"]
    backend: StateBackend | None = config["configurable"].get("backend")
    current_revision = config["configurable"].get("current_revision")
    candidate_text = _bound_candidate_text(org_repo, backend, current_revision)
    if candidate_text is None and proposal_only_active():
        current = backend.load(org_repo) if backend is not None else None
        upstream = current.domain_states.get(README_PRESENTATION) if current is not None else None
        upstream_status = upstream.accepted_status if upstream is not None else None
        upstream_failure_reason = upstream.last_failure_reason if upstream is not None else None
        upstream_failed = upstream is not None and (
            upstream_failure_reason is not None
            or (upstream_status is not None and upstream_status.startswith("ERROR:"))
        )
        if upstream_failed:
            return {
                "accepted_status": "NO_CHANGE",
                "details": {
                    "status": "DEFERRED_UPSTREAM_FAILURE",
                    "upstream_domain": README_PRESENTATION,
                    "upstream_status": upstream_status,
                    "upstream_failure_reason": upstream_failure_reason,
                },
            }
        raise RuntimeError("local-POC presentation benchmark requires a lifecycle-bound candidate")
    arguments = {"org_repo": org_repo}
    if candidate_text is not None:
        arguments["candidate_text"] = candidate_text
    tool_call = {
        "function": {
            "name": "compare_against_presentation_standard",
            "arguments": json.dumps(arguments),
        }
    }
    dispatch = dispatch_tool_call(
        tool_call, _READ_ONLY_PERMISSIONS, caller_domain=DOMAIN, state_backend=backend
    )
    if dispatch.outcome != "executed":
        return {"accepted_status": f"ERROR:{dispatch.outcome}:{dispatch.error}"}

    assert dispatch.result is not None
    result = dispatch.result
    fingerprint = _fingerprint(result)
    classification = classify_surface(
        current_fingerprint=fingerprint, prior_fingerprint=state.accepted_facts_hash
    )
    return {
        "accepted_facts_hash": fingerprint,
        "accepted_status": classification.classification,
        "details": result,
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
    the `record` node when `backend` is not `None`."""
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
